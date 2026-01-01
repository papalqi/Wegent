import json
import os
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin


@dataclass
class Link:
    href: str
    text: str


@dataclass
class Form:
    action: str
    method: str
    fields: Dict[str, str] = field(default_factory=dict)


class _HtmlExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[Link] = []
        self.forms: List[Form] = []

        self._in_anchor = False
        self._anchor_href = ""
        self._anchor_text_parts: List[str] = []

        self._current_form: Optional[Form] = None
        self._in_textarea = False
        self._textarea_name = ""
        self._textarea_parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "a":
            self._in_anchor = True
            self._anchor_href = attrs_dict.get("href", "")
            self._anchor_text_parts = []
            return

        if tag.lower() == "form":
            action = attrs_dict.get("action", "")
            method = (attrs_dict.get("method", "post") or "post").lower()
            self._current_form = Form(action=action, method=method, fields={})
            self.forms.append(self._current_form)
            return

        if self._current_form and tag.lower() == "input":
            name = attrs_dict.get("name", "")
            if not name:
                return
            value = attrs_dict.get("value", "")
            # Keep hidden + default values; user-provided values can override later.
            self._current_form.fields[name] = value
            return

        if self._current_form and tag.lower() == "textarea":
            name = attrs_dict.get("name", "")
            if not name:
                return
            self._in_textarea = True
            self._textarea_name = name
            self._textarea_parts = []
            return

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._in_anchor:
            text = "".join(self._anchor_text_parts).strip()
            self.links.append(Link(href=self._anchor_href, text=text))
            self._in_anchor = False
            self._anchor_href = ""
            self._anchor_text_parts = []
            return

        if tag.lower() == "form":
            self._current_form = None
            return

        if tag.lower() == "textarea" and self._in_textarea and self._current_form:
            self._in_textarea = False
            value = "".join(self._textarea_parts)
            self._current_form.fields[self._textarea_name] = value
            self._textarea_name = ""
            self._textarea_parts = []
            return

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._anchor_text_parts.append(data)
        if self._in_textarea:
            self._textarea_parts.append(data)


def _read_message() -> Optional[Dict[str, Any]]:
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


def _text_result(text: str) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}


def _safe_relpath(path: str) -> str:
    if os.path.isabs(path):
        raise ValueError("path must be relative")
    if ".." in os.path.normpath(path).split(os.sep):
        raise ValueError("path must not contain '..'")
    return path


class HttpUiDriver:
    def __init__(self) -> None:
        import requests  # local import for executor environments

        self._requests = requests
        self.session = requests.Session()

        self.base_url = ""
        self.timeout_seconds = 30.0
        self.default_headers: Dict[str, str] = {}

        self.last_url = ""
        self.last_status: Optional[int] = None
        self.last_headers: Dict[str, str] = {}
        self.last_body: str = ""

    def configure(
        self,
        *,
        base_url: str = "",
        timeout_seconds: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        if base_url:
            self.base_url = base_url
        self.timeout_seconds = float(timeout_seconds or 30.0)
        if headers:
            self.default_headers.update({str(k): str(v) for k, v in headers.items()})

    def _resolve(self, url: str) -> str:
        if not url:
            raise ValueError("url is required")
        if self.base_url:
            return urljoin(self.base_url, url)
        return url

    def open(self, *, url: str) -> None:
        target = self._resolve(url)
        resp = self.session.get(
            target,
            headers=self.default_headers or None,
            timeout=self.timeout_seconds,
            allow_redirects=True,
        )
        self.last_url = resp.url
        self.last_status = resp.status_code
        self.last_headers = dict(resp.headers)
        self.last_body = resp.text or ""

    def click_link(self, *, text_contains: str = "", href_contains: str = "") -> None:
        if not self.last_body:
            raise RuntimeError("No page loaded (call open first)")
        if not text_contains and not href_contains:
            raise ValueError("Provide text_contains or href_contains")

        extractor = _HtmlExtractor()
        extractor.feed(self.last_body)
        links = extractor.links

        text_q = (text_contains or "").strip().lower()
        href_q = (href_contains or "").strip().lower()
        for link in links:
            href = (link.href or "").strip()
            if not href:
                continue
            if text_q and text_q not in (link.text or "").lower():
                continue
            if href_q and href_q not in href.lower():
                continue
            self.open(url=urljoin(self.last_url or self.base_url, href))
            return

        raise RuntimeError(
            f"No matching link found (text_contains={text_contains!r}, href_contains={href_contains!r})"
        )

    def submit_form(
        self,
        *,
        action_contains: str = "",
        method: str = "",
        fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.last_body:
            raise RuntimeError("No page loaded (call open first)")

        extractor = _HtmlExtractor()
        extractor.feed(self.last_body)
        forms = extractor.forms
        if not forms:
            raise RuntimeError("No form found on page")

        action_q = (action_contains or "").strip().lower()
        chosen: Optional[Form] = None
        for form in forms:
            if not action_q:
                chosen = form
                break
            if action_q in (form.action or "").lower():
                chosen = form
                break

        if not chosen:
            raise RuntimeError(
                f"No matching form found (action_contains={action_contains!r})"
            )

        submit_method = (method or chosen.method or "post").lower()
        submit_url = urljoin(self.last_url or self.base_url, chosen.action or "")
        payload: Dict[str, Any] = dict(chosen.fields)
        if fields:
            payload.update(
                {str(k): "" if v is None else str(v) for k, v in fields.items()}
            )

        if submit_method == "get":
            resp = self.session.get(
                submit_url,
                params=payload,
                headers=self.default_headers or None,
                timeout=self.timeout_seconds,
                allow_redirects=True,
            )
        else:
            resp = self.session.post(
                submit_url,
                data=payload,
                headers=self.default_headers or None,
                timeout=self.timeout_seconds,
                allow_redirects=True,
            )

        self.last_url = resp.url
        self.last_status = resp.status_code
        self.last_headers = dict(resp.headers)
        self.last_body = resp.text or ""

    def assert_status(self, *, status: int) -> None:
        if self.last_status is None:
            raise RuntimeError("No response available (call open first)")
        if int(self.last_status) != int(status):
            raise AssertionError(
                f"Expected status={status}, got={self.last_status} url={self.last_url}"
            )

    def assert_contains(self, *, text: str = "", regex: str = "") -> None:
        if not self.last_body:
            raise RuntimeError("No response body available (call open first)")
        if text:
            if text not in self.last_body:
                raise AssertionError(f"Body does not contain text={text!r}")
            return
        if regex:
            if not re.search(regex, self.last_body, flags=re.MULTILINE):
                raise AssertionError(f"Body does not match regex={regex!r}")
            return
        raise ValueError("Provide text or regex")

    def save_body(self, *, path: str) -> str:
        rel = _safe_relpath(path)
        abs_path = os.path.abspath(os.path.join(os.getcwd(), rel))
        if not abs_path.startswith(os.getcwd()):
            raise ValueError("Invalid path")
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(self.last_body or "")
        return abs_path


TOOLS = [
    {
        "name": "configure",
        "description": "Configure base_url/timeout/headers for the HTTP UI driver.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_url": {"type": "string"},
                "timeout_seconds": {"type": "number"},
                "headers": {"type": "object"},
            },
        },
    },
    {
        "name": "open",
        "description": "Open a URL (HTTP GET) and store it as the current page.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "click_link",
        "description": "Simulate clicking a link by following the first matching <a href> on the current page.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text_contains": {"type": "string"},
                "href_contains": {"type": "string"},
            },
        },
    },
    {
        "name": "submit_form",
        "description": "Simulate typing+submit by posting a form found on the current page.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_contains": {"type": "string"},
                "method": {"type": "string", "enum": ["get", "post"]},
                "fields": {"type": "object"},
            },
        },
    },
    {
        "name": "assert_status",
        "description": "Assert the last HTTP status code equals the expected value.",
        "inputSchema": {
            "type": "object",
            "properties": {"status": {"type": "integer"}},
            "required": ["status"],
        },
    },
    {
        "name": "assert_contains",
        "description": "Assert the last response body contains text or matches a regex.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "regex": {"type": "string"}},
        },
    },
    {
        "name": "save_body",
        "description": "Save the last response body to a relative file path.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]


def main() -> None:
    driver = HttpUiDriver()

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
                        "serverInfo": {
                            "name": "web-ui-validator-mcp",
                            "version": "0.1.0",
                        },
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
            try:
                if name == "configure":
                    driver.configure(
                        base_url=arguments.get("base_url", "") or "",
                        timeout_seconds=float(arguments.get("timeout_seconds") or 30.0),
                        headers=arguments.get("headers") or None,
                    )
                    _write_message(_result(msg_id, _text_result("[mcp] configured")))
                    continue
                if name == "open":
                    driver.open(url=str(arguments.get("url", "")))
                    _write_message(
                        _result(
                            msg_id,
                            _text_result(
                                f"[mcp] opened url={driver.last_url} status={driver.last_status}"
                            ),
                        )
                    )
                    continue
                if name == "click_link":
                    driver.click_link(
                        text_contains=str(arguments.get("text_contains", "")),
                        href_contains=str(arguments.get("href_contains", "")),
                    )
                    _write_message(
                        _result(
                            msg_id,
                            _text_result(
                                f"[mcp] clicked url={driver.last_url} status={driver.last_status}"
                            ),
                        )
                    )
                    continue
                if name == "submit_form":
                    fields = arguments.get("fields")
                    driver.submit_form(
                        action_contains=str(arguments.get("action_contains", "")),
                        method=str(arguments.get("method", "")),
                        fields=fields if isinstance(fields, dict) else None,
                    )
                    _write_message(
                        _result(
                            msg_id,
                            _text_result(
                                f"[mcp] submitted url={driver.last_url} status={driver.last_status}"
                            ),
                        )
                    )
                    continue
                if name == "assert_status":
                    driver.assert_status(status=int(arguments.get("status")))
                    _write_message(
                        _result(msg_id, _text_result("[mcp] assert_status ok"))
                    )
                    continue
                if name == "assert_contains":
                    driver.assert_contains(
                        text=str(arguments.get("text", "")),
                        regex=str(arguments.get("regex", "")),
                    )
                    _write_message(
                        _result(msg_id, _text_result("[mcp] assert_contains ok"))
                    )
                    continue
                if name == "save_body":
                    abs_path = driver.save_body(path=str(arguments.get("path", "")))
                    _write_message(
                        _result(msg_id, _text_result(f"[mcp] saved body to {abs_path}"))
                    )
                    continue

                _write_message(_error(msg_id, -32601, f"Unknown tool: {name}"))
                continue
            except AssertionError as e:
                _write_message(_error(msg_id, -32000, str(e)))
                continue
            except Exception as e:
                _write_message(_error(msg_id, -32602, str(e)))
                continue

        _write_message(_error(msg_id, -32601, f"Unknown method: {method}"))


if __name__ == "__main__":
    main()
