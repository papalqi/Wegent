import argparse
import json
import os
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional


def _log(line: str) -> None:
    print(line, flush=True)


def _write_mcp_message(stdin, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    stdin.write(body)
    stdin.flush()


def _read_mcp_message(stdout) -> dict:
    headers = {}
    while True:
        line = stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout")
        if line in (b"\r\n", b"\n"):
            break
        key, value = line.decode("utf-8", errors="replace").split(":", 1)
        headers[key.strip().lower()] = value.strip()

    length = int(headers.get("content-length", "0") or "0")
    if length <= 0:
        raise RuntimeError("Invalid MCP Content-Length")
    body = stdout.read(length)
    return json.loads(body.decode("utf-8", errors="replace"))


def _mcp_request(
    proc: subprocess.Popen, req_id: int, method: str, params: dict
) -> dict:
    _write_mcp_message(
        proc.stdin, {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
    )
    resp = _read_mcp_message(proc.stdout)
    if resp.get("id") != req_id:
        raise RuntimeError(
            f"MCP response id mismatch: expected={req_id} got={resp.get('id')}"
        )
    if "error" in resp:
        raise RuntimeError(resp["error"].get("message") or "MCP error")
    return resp


def _mcp_tool(proc: subprocess.Popen, req_id: int, name: str, arguments: dict) -> str:
    resp = _mcp_request(
        proc, req_id, "tools/call", {"name": name, "arguments": arguments}
    )
    content = resp.get("result", {}).get("content", [])
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            return str(first.get("text", ""))
    return ""


def _load_spec(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Spec must be a JSON object")
    return data


def _build_inline_spec(
    *, url: str, assert_status: Optional[int], assert_contains: str, assert_regex: str
) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = [{"action": "open", "url": url}]
    if assert_status is not None:
        steps.append({"action": "assert_status", "status": int(assert_status)})
    if assert_contains:
        steps.append({"action": "assert_contains", "text": assert_contains})
    if assert_regex:
        steps.append({"action": "assert_contains", "regex": assert_regex})
    return {"steps": steps}


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="web_ui_validator")
    parser.add_argument("--spec", type=str, default="")
    parser.add_argument("--base-url", type=str, default="")
    parser.add_argument("--timeout", type=float, default=30.0)

    parser.add_argument("--url", type=str, default="")
    parser.add_argument("--assert-status", type=int, default=None)
    parser.add_argument("--assert-contains", type=str, default="")
    parser.add_argument("--assert-regex", type=str, default="")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    if args.spec:
        spec = _load_spec(args.spec)
    elif args.url:
        spec = _build_inline_spec(
            url=args.url,
            assert_status=args.assert_status,
            assert_contains=args.assert_contains,
            assert_regex=args.assert_regex,
        )
    else:
        _log("WEB_UI_VALIDATOR: missing --spec or --url")
        return 2

    base_url = str(spec.get("base_url") or args.base_url or "")
    steps = spec.get("steps") or []
    if not isinstance(steps, list) or not steps:
        _log("WEB_UI_VALIDATOR: spec.steps must be a non-empty array")
        return 2

    skill_dir = os.path.dirname(os.path.abspath(__file__))
    mcp_server_path = os.path.join(skill_dir, "mcp_http_ui_server.py")

    _log("WEB_UI_VALIDATOR: start")
    _log(f"WEB_UI_VALIDATOR: cwd={os.getcwd()}")
    _log(f"WEB_UI_VALIDATOR: steps={len(steps)}")

    mcp_proc = subprocess.Popen(
        ["python3", mcp_server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        _mcp_request(mcp_proc, 1, "initialize", {})
        _mcp_tool(
            mcp_proc,
            2,
            "configure",
            {"base_url": base_url, "timeout_seconds": float(args.timeout)},
        )

        req_id = 10
        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                raise ValueError(f"Invalid step type at index={idx}")
            action = str(step.get("action") or "").strip()
            if not action:
                raise ValueError(f"Missing action at step index={idx}")

            _log(f"WEB_UI_VALIDATOR: step {idx}/{len(steps)} action={action}")

            if action == "open":
                text = _mcp_tool(
                    mcp_proc, req_id, "open", {"url": str(step.get("url") or "")}
                )
                _log(f"WEB_UI_VALIDATOR: {text}")
            elif action == "click_link":
                text = _mcp_tool(
                    mcp_proc,
                    req_id,
                    "click_link",
                    {
                        "text_contains": str(step.get("text_contains") or ""),
                        "href_contains": str(step.get("href_contains") or ""),
                    },
                )
                _log(f"WEB_UI_VALIDATOR: {text}")
            elif action == "submit_form":
                fields = step.get("fields")
                text = _mcp_tool(
                    mcp_proc,
                    req_id,
                    "submit_form",
                    {
                        "action_contains": str(step.get("action_contains") or ""),
                        "method": str(step.get("method") or ""),
                        "fields": fields if isinstance(fields, dict) else {},
                    },
                )
                _log(f"WEB_UI_VALIDATOR: {text}")
            elif action == "assert_status":
                text = _mcp_tool(
                    mcp_proc,
                    req_id,
                    "assert_status",
                    {"status": int(step.get("status"))},
                )
                _log(f"WEB_UI_VALIDATOR: {text}")
            elif action == "assert_contains":
                text_val = str(step.get("text") or "")
                regex_val = str(step.get("regex") or "")
                text = _mcp_tool(
                    mcp_proc,
                    req_id,
                    "assert_contains",
                    {"text": text_val, "regex": regex_val},
                )
                _log(f"WEB_UI_VALIDATOR: {text}")
            elif action == "save_body":
                text = _mcp_tool(
                    mcp_proc,
                    req_id,
                    "save_body",
                    {"path": str(step.get("path") or "last_response.html")},
                )
                _log(f"WEB_UI_VALIDATOR: {text}")
            else:
                raise ValueError(f"Unsupported action: {action}")

            req_id += 1

        _log("WEB_UI_VALIDATOR: done")
        return 0
    except Exception as e:
        _log(f"WEB_UI_VALIDATOR: failed error={e}")
        return 1
    finally:
        try:
            if mcp_proc.poll() is None:
                mcp_proc.terminate()
                mcp_proc.wait(timeout=2)
        except Exception:
            try:
                mcp_proc.kill()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
