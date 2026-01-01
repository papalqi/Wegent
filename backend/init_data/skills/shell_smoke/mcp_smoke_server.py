import json
import sys
from typing import Any, Dict, Optional


def _read_message() -> Optional[Dict[str, Any]]:
    """
    Minimal MCP stdio server framing (LSP-style):
      Content-Length: N\r\n
      \r\n
      {jsonrpc...}
    """
    headers: Dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        try:
            key, value = line.decode("utf-8", errors="replace").split(":", 1)
        except ValueError:
            continue
        headers[key.strip().lower()] = value.strip()

    length = int(headers.get("content-length", "0") or "0")
    if length <= 0:
        return None

    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    return json.loads(body.decode("utf-8", errors="replace"))


def _write_message(payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _result(id_value: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "result": result}


def _error(id_value: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": id_value,
        "error": {"code": code, "message": message},
    }


TOOLS = [
    {
        "name": "ui_click",
        "description": "Simulate a UI click (smoke-only).",
        "inputSchema": {
            "type": "object",
            "properties": {"selector": {"type": "string"}},
            "required": ["selector"],
        },
    },
    {
        "name": "ui_type",
        "description": "Simulate typing text into an input (smoke-only).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "text": {"type": "string"},
            },
            "required": ["selector", "text"],
        },
    },
]


def main() -> None:
    while True:
        msg = _read_message()
        if msg is None:
            return

        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params") or {}

        if method == "initialize":
            _write_message(
                _result(
                    msg_id,
                    {
                        "serverInfo": {"name": "shell-smoke-mcp", "version": "0.1.0"},
                        "capabilities": {"tools": {}},
                    },
                )
            )
            continue

        if method == "tools/list":
            _write_message(_result(msg_id, {"tools": TOOLS}))
            continue

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name == "ui_click":
                selector = arguments.get("selector", "")
                _write_message(
                    _result(
                        msg_id,
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"[mcp] clicked selector={selector}",
                                }
                            ]
                        },
                    )
                )
                continue
            if name == "ui_type":
                selector = arguments.get("selector", "")
                text = arguments.get("text", "")
                _write_message(
                    _result(
                        msg_id,
                        {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"[mcp] typed selector={selector} text={text}",
                                }
                            ]
                        },
                    )
                )
                continue

            _write_message(_error(msg_id, -32601, f"Unknown tool: {name}"))
            continue

        _write_message(_error(msg_id, -32601, f"Unknown method: {method}"))


if __name__ == "__main__":
    main()
