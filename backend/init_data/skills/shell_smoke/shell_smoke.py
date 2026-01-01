import json
import os
import subprocess
import sys
import time
from datetime import datetime


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
        proc.stdin,
        {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params},
    )
    resp = _read_mcp_message(proc.stdout)
    if resp.get("id") != req_id:
        raise RuntimeError(
            f"MCP response id mismatch: expected={req_id} got={resp.get('id')}"
        )
    return resp


def main() -> None:
    _log("SHELL_SMOKE: start")
    _log(f"SHELL_SMOKE: cwd={os.getcwd()}")
    _log(f"SHELL_SMOKE: python={sys.version.split()[0]}")
    _log(f"SHELL_SMOKE: time={datetime.now().isoformat(timespec='seconds')}")

    output_path = os.path.join(os.getcwd(), "shell_smoke_result.txt")
    _log(f"SHELL_SMOKE: writing {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("shell_smoke ok\n")
        f.write(f"cwd={os.getcwd()}\n")
        f.write(f"time={datetime.now().isoformat(timespec='seconds')}\n")

    # MCP simulation: start a tiny stdio MCP server and "simulate" click/type.
    skill_dir = os.path.dirname(os.path.abspath(__file__))
    mcp_server_path = os.path.join(skill_dir, "mcp_smoke_server.py")
    _log("SHELL_SMOKE: starting MCP stdio server")
    mcp_proc = subprocess.Popen(
        ["python3", mcp_server_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _mcp_request(mcp_proc, 1, "initialize", {})
        tools_resp = _mcp_request(mcp_proc, 2, "tools/list", {})
        tools = tools_resp.get("result", {}).get("tools", [])
        _log(f"SHELL_SMOKE: MCP tools={len(tools)}")

        click_resp = _mcp_request(
            mcp_proc,
            3,
            "tools/call",
            {"name": "ui_click", "arguments": {"selector": "#send"}},
        )
        _log(
            f"SHELL_SMOKE: {click_resp.get('result', {}).get('content', [{}])[0].get('text', '')}"
        )

        type_resp = _mcp_request(
            mcp_proc,
            4,
            "tools/call",
            {
                "name": "ui_type",
                "arguments": {"selector": "textarea", "text": "@shell_smoke"},
            },
        )
        _log(
            f"SHELL_SMOKE: {type_resp.get('result', {}).get('content', [{}])[0].get('text', '')}"
        )
    finally:
        try:
            mcp_proc.terminate()
            mcp_proc.wait(timeout=2)
        except Exception:
            try:
                mcp_proc.kill()
            except Exception:
                pass

    for i in range(5):
        _log(f"SHELL_SMOKE: streaming line {i + 1}/5")
        time.sleep(0.4)

    _log("SHELL_SMOKE: done")


if __name__ == "__main__":
    main()
