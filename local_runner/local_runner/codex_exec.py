from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple


def _chunk_text(text: str, chunk_size: int = 400) -> List[str]:
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _extract_thread_id(event: Dict[str, Any]) -> Optional[str]:
    if event.get("type") != "thread.started":
        return None
    candidates: List[Any] = [event.get("thread_id"), event.get("threadId")]
    thread = event.get("thread")
    if isinstance(thread, dict):
        candidates.extend(
            [thread.get("id"), thread.get("thread_id"), thread.get("threadId")]
        )
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c.strip()
    return None


@dataclass
class CodexRunResult:
    ok: bool
    value: str
    resume_session_id: Optional[str]
    stderr_tail: List[str]


def run_codex_exec(
    *,
    codex_cmd: str,
    cwd: Path,
    prompt: str,
    model: Optional[str],
    resume_session_id: Optional[str],
    retry_mode: str,
    env: Optional[Dict[str, str]] = None,
    on_event_batch: Optional[callable] = None,
    on_value_chunk: Optional[callable] = None,
) -> CodexRunResult:
    cmd: List[str] = [
        codex_cmd,
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "-C",
        str(cwd),
    ]
    if model:
        cmd.extend(["--model", model])
    if resume_session_id and retry_mode != "new_session":
        cmd.extend(["resume", resume_session_id])
    cmd.append("-")

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        bufsize=1,
    )
    assert proc.stdin and proc.stdout and proc.stderr
    proc.stdin.write(prompt.encode("utf-8"))
    proc.stdin.flush()
    proc.stdin.close()

    value = ""
    stderr_tail: List[str] = []
    buffered_events: List[Dict[str, Any]] = []
    last_flush = time.monotonic()
    current_resume = resume_session_id

    def flush_events() -> None:
        nonlocal buffered_events, last_flush
        if not buffered_events:
            return
        batch = buffered_events
        buffered_events = []
        last_flush = time.monotonic()
        if on_event_batch:
            on_event_batch(batch, current_resume)

    while True:
        line = proc.stdout.readline()
        if not line:
            break
        try:
            event = json.loads(line.decode("utf-8", errors="replace").strip())
        except Exception:
            continue
        if isinstance(event, dict):
            buffered_events.append(event)
            if len(buffered_events) >= 5 or (time.monotonic() - last_flush) >= 0.2:
                flush_events()
            tid = _extract_thread_id(event)
            if tid and tid != current_resume:
                current_resume = tid
                if on_event_batch:
                    on_event_batch([], current_resume)

        event_type = event.get("type") if isinstance(event, dict) else None
        if event_type == "item.completed":
            item = (event.get("item") or {}) if isinstance(event, dict) else {}
            if item.get("type") == "agent_message":
                text = item.get("text") or ""
                if isinstance(text, str) and text:
                    for chunk in _chunk_text(text, chunk_size=400):
                        value += chunk
                        if on_value_chunk:
                            on_value_chunk(chunk, value, current_resume)

    flush_events()

    # Drain stderr (best-effort)
    try:
        while True:
            err = proc.stderr.readline()
            if not err:
                break
            s = err.decode("utf-8", errors="replace").rstrip("\n")
            if s:
                stderr_tail.append(s)
                if len(stderr_tail) > 200:
                    stderr_tail.pop(0)
    except Exception:
        pass

    rc = proc.wait()
    return CodexRunResult(
        ok=rc == 0,
        value=value,
        resume_session_id=current_resume,
        stderr_tail=stderr_tail,
    )
