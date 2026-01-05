#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"github_pat_[A-Za-z0-9_]+"), "github_pat_[REDACTED]"),
    (re.compile(r"ghp_[A-Za-z0-9]+"), "ghp_[REDACTED]"),
    (re.compile(r"glpat-[A-Za-z0-9\\-]+"), "glpat-[REDACTED]"),
    (
        re.compile(r"(?i)authorization:\\s*bearer\\s+[A-Za-z0-9._\\-]+"),
        "Authorization: Bearer [REDACTED]",
    ),
    (re.compile(r"(?i)bearer\\s+[A-Za-z0-9._\\-]+"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)(token:)([^@\\s]+)(@github\\.com)"), r"\\1[REDACTED]\\3"),
    (
        re.compile(r"(?i)(git_token['\\\"]?\\s*[:=]\\s*['\\\"])([^'\\\"]+)(['\\\"])"),
        r"\\1[REDACTED]\\3",
    ),
]


def _redact(text: str) -> str:
    redacted = text
    for pattern, replacement in _REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


@dataclass(frozen=True)
class CmdResult:
    code: int
    stdout: str
    stderr: str


def _run(
    cmd: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 60
) -> CmdResult:
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:
        return CmdResult(127, "", f"{exc}")
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        )
        return CmdResult(124, stdout, f"timeout after {timeout_s}s\n{stderr}")

    return CmdResult(proc.returncode, proc.stdout, proc.stderr)


def _safe_print(*args: object, **kwargs: object) -> None:
    try:
        print(*args, **kwargs, flush=True)
    except BrokenPipeError:
        os._exit(0)


def _print_kv(key: str, value: str) -> None:
    _safe_print(f"{key}: {value}")


def _http_get_json(
    url: str, *, timeout_s: int = 5
) -> tuple[int | None, object | None, str]:
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body), ""
            except json.JSONDecodeError:
                return resp.status, body, ""
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(exc)
        return exc.code, None, _redact(body)
    except URLError as exc:
        return None, None, str(exc)


def _docker_ps_lines() -> list[str]:
    res = _run(
        ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"]
    )
    if res.code != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def _docker_container_exists(container_name: str) -> bool:
    for line in _docker_ps_lines():
        name = line.split("\t", 1)[0].strip()
        if name == container_name:
            return True
    return False


def _mysql_query(
    *,
    container: str,
    user: str,
    password: str,
    database: str,
    sql: str,
    timeout_s: int = 30,
) -> CmdResult:
    cmd = [
        "docker",
        "exec",
        "-i",
        container,
        "mysql",
        f"-u{user}",
        f"-p{password}",
        "-D",
        database,
        "-N",
        "-B",
        "-e",
        sql,
    ]
    res = _run(cmd, timeout_s=timeout_s)
    return CmdResult(res.code, res.stdout, res.stderr)


def _table(lines: Iterable[str], indent: str = "  ") -> None:
    for line in lines:
        _safe_print(f"{indent}{line}")


def _guess_repo_root(script_path: Path) -> Path:
    current = script_path.resolve()
    for parent in [current] + list(current.parents):
        if (parent / "docker-compose.yml").exists() and (parent / "backend").is_dir():
            return parent
    return Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Wegent task status across DB, executor-manager, and workspace."
    )
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--executor-manager-url", default="http://localhost:8001")
    parser.add_argument(
        "--executor-manager-container", default="wegent-executor-manager"
    )
    parser.add_argument("--mysql-container", default="wegent-mysql")
    parser.add_argument("--mysql-user", default="root")
    parser.add_argument("--mysql-password", default="123456")
    parser.add_argument("--mysql-db", default="task_manager")
    parser.add_argument(
        "--workspace-root", type=Path, default=Path.home() / "wecode-bot"
    )
    parser.add_argument("--docker-since", default="24h")
    args = parser.parse_args()

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    repo_root = args.repo_root or _guess_repo_root(Path(__file__))

    _safe_print("== Wegent Task Inspect ==")
    _print_kv("task_id", str(args.task_id))
    _print_kv("now", now)
    _print_kv("repo_root", str(repo_root))
    _print_kv("workspace_root", str(args.workspace_root))
    _safe_print()

    _safe_print("[services]")
    docker_lines = _docker_ps_lines()
    if docker_lines:
        wanted = {
            args.executor_manager_container,
            args.mysql_container,
            "wegent-redis",
            "wegent-backend",
            "wegent-frontend",
        }
        filtered = [line for line in docker_lines if line.split("\t", 1)[0] in wanted]
        if filtered:
            _table(filtered)
        else:
            _table(docker_lines[:20])
    else:
        _safe_print("  docker: unavailable (cannot read `docker ps -a`)")

    status, body, err = _http_get_json(
        f"{args.executor_manager_url.rstrip('/')}/health"
    )
    if status is not None:
        _print_kv(
            "  executor-manager /health",
            f"{status} {_redact(json.dumps(body, ensure_ascii=False)) if body is not None else ''}".strip(),
        )
    else:
        _print_kv("  executor-manager /health", f"unreachable ({err})")
    _safe_print()

    _safe_print("[db]")
    tz_res = _mysql_query(
        container=args.mysql_container,
        user=args.mysql_user,
        password=args.mysql_password,
        database=args.mysql_db,
        sql="SELECT @@global.time_zone, @@session.time_zone, NOW();",
    )
    if tz_res.code == 0 and tz_res.stdout.strip():
        _print_kv("  mysql now", tz_res.stdout.strip().replace("\t", " | "))
    else:
        _print_kv("  mysql now", f"unavailable ({_redact(tz_res.stderr.strip())})")

    task_row = _mysql_query(
        container=args.mysql_container,
        user=args.mysql_user,
        password=args.mysql_password,
        database=args.mysql_db,
        sql=(
            "SELECT id, kind, name, namespace, is_active, created_at, updated_at "
            f"FROM tasks WHERE id={args.task_id};"
        ),
    )
    if task_row.code != 0:
        _print_kv("  tasks", f"query failed ({_redact(task_row.stderr.strip())})")
        return 2
    if not task_row.stdout.strip():
        _print_kv("  tasks", "not found")
        return 3
    _print_kv("  tasks", task_row.stdout.strip().replace("\t", " | "))

    task_status = _mysql_query(
        container=args.mysql_container,
        user=args.mysql_user,
        password=args.mysql_password,
        database=args.mysql_db,
        sql=(
            "SELECT "
            "JSON_UNQUOTE(JSON_EXTRACT(json,'$.status.status')), "
            "JSON_EXTRACT(json,'$.status.progress'), "
            "JSON_UNQUOTE(JSON_EXTRACT(json,'$.status.statusPhase')), "
            "JSON_UNQUOTE(JSON_EXTRACT(json,'$.status.completedAt')), "
            "JSON_UNQUOTE(JSON_EXTRACT(json,'$.status.errorMessage')), "
            "JSON_UNQUOTE(JSON_EXTRACT(json,'$.status.updatedAt')) "
            f"FROM tasks WHERE id={args.task_id};"
        ),
    )
    if task_status.code == 0 and task_status.stdout.strip():
        fields = (task_status.stdout.strip().split("\t") + [""] * 6)[:6]
        _print_kv("  task.status", fields[0] or "null")
        _print_kv("  task.progress", fields[1] or "null")
        _print_kv("  task.phase", fields[2] or "null")
        _print_kv("  task.completedAt", fields[3] or "null")
        _print_kv("  task.errorMessage", _redact(fields[4] or ""))
        _print_kv("  task.updatedAt", fields[5] or "null")
    else:
        _print_kv(
            "  task.status", f"unavailable ({_redact(task_status.stderr.strip())})"
        )

    subtasks = _mysql_query(
        container=args.mysql_container,
        user=args.mysql_user,
        password=args.mysql_password,
        database=args.mysql_db,
        sql=(
            "SELECT id, title, status, progress, "
            "IFNULL(executor_namespace,''), IFNULL(executor_name,''), "
            "updated_at, completed_at, IFNULL(error_message,'') "
            f"FROM subtasks WHERE task_id={args.task_id} ORDER BY id;"
        ),
    )
    executor_names: list[str] = []
    running_subtask_ids: list[str] = []
    if subtasks.code == 0 and subtasks.stdout.strip():
        _safe_print("  subtasks:")
        for line in subtasks.stdout.splitlines():
            cols = line.split("\t")
            cols += [""] * (9 - len(cols))
            (
                subtask_id,
                title,
                status_s,
                progress_s,
                ex_ns,
                ex_name,
                updated_at,
                completed_at,
                err_msg,
            ) = cols[:9]
            title_short = (title[:80] + "…") if len(title) > 80 else title
            err_short = _redact(err_msg.replace("\n", " ").strip())
            if len(err_short) > 120:
                err_short = err_short[:120] + "…"
            _safe_print(
                "    - "
                f"id={subtask_id} status={status_s} progress={progress_s} "
                f"executor={ex_name or '-'} updated_at={updated_at or '-'} completed_at={completed_at or '-'} "
                f"title={title_short}"
                f"{' error=' + err_short if err_short else ''}"
            )
            if ex_name:
                executor_names.append(ex_name)
            if status_s == "RUNNING":
                running_subtask_ids.append(subtask_id)
    else:
        _print_kv("  subtasks", "none or unavailable")
    _safe_print()

    _safe_print("[executor]")
    unique_executors = sorted({name for name in executor_names if name})
    if not unique_executors:
        _safe_print("  (no executor_name in subtasks)")
    for ex_name in unique_executors:
        status, body, err = _http_get_json(
            f"{args.executor_manager_url.rstrip('/')}/executor-manager/executor/status?executor_name={ex_name}"
        )
        if status is None:
            _print_kv(f"  {ex_name}", f"executor-manager unreachable ({err})")
        else:
            exists = None
            state = None
            if isinstance(body, dict):
                exists = body.get("exists")
                state = body.get("state")
            _print_kv(f"  {ex_name}", f"exists={exists} state={state} (http {status})")
        _print_kv(
            f"  docker {ex_name}",
            "exists" if _docker_container_exists(ex_name) else "missing",
        )
    _safe_print()

    _safe_print("[workspace]")
    task_workspace = args.workspace_root / str(args.task_id)
    if not task_workspace.exists():
        _print_kv("  path", f"missing ({task_workspace})")
    else:
        _print_kv("  path", str(task_workspace))
        repo_candidates = [
            p for p in task_workspace.iterdir() if p.is_dir() and (p / ".git").exists()
        ]
        if not repo_candidates:
            _print_kv("  git", "no repo found under task workspace")
        else:
            repo_dir = repo_candidates[0]
            _print_kv("  repo", str(repo_dir))
            branch = _run(["git", "-C", str(repo_dir), "branch", "--show-current"])
            if branch.code == 0:
                _print_kv("  branch", _redact(branch.stdout.strip()))
            last_commit = _run(["git", "-C", str(repo_dir), "log", "-1", "--oneline"])
            if last_commit.code == 0:
                _print_kv("  last_commit", _redact(last_commit.stdout.strip()))
            dirty = _run(["git", "-C", str(repo_dir), "status", "--porcelain=v1"])
            if dirty.code == 0:
                _print_kv("  dirty", "yes" if bool(dirty.stdout.strip()) else "no")
    _safe_print()

    _safe_print("[logs]")
    patterns = [
        rf"\\btask_id\\b.?[:= ]{args.task_id}\\b",
        (
            rf"\\bsubtask_id\\b.?[:= ]({'|'.join(running_subtask_ids)})\\b"
            if running_subtask_ids
            else None
        ),
    ] + [re.escape(ex) for ex in unique_executors]
    patterns = [p for p in patterns if p]
    if not patterns:
        _safe_print("  (no search patterns)")
    else:
        backend_log = repo_root / "backend" / "uvicorn.log"
        frontend_log = repo_root / "frontend" / "next.log"
        for log_path in [backend_log, frontend_log]:
            if not log_path.exists():
                continue
            rg = _run(["rg", "-n", "-S", "|".join(patterns), str(log_path)])
            hits = [line for line in rg.stdout.splitlines() if line.strip()]
            if hits:
                _print_kv(f"  {log_path}", f"{len(hits)} hits (showing last 20)")
                _table([_redact(line) for line in hits[-20:]], indent="    ")
        if _docker_container_exists(args.executor_manager_container):
            docker_logs = _run(
                [
                    "docker",
                    "logs",
                    "--since",
                    args.docker_since,
                    args.executor_manager_container,
                ],
                timeout_s=60,
            )
            if docker_logs.code == 0 and docker_logs.stdout.strip():
                matched = []
                rx = re.compile("|".join(patterns))
                for line in docker_logs.stdout.splitlines():
                    if rx.search(line):
                        matched.append(line)
                if matched:
                    _print_kv(
                        f"  docker logs {args.executor_manager_container}",
                        f"{len(matched)} hits (showing last 50, since {args.docker_since})",
                    )
                    _table([_redact(line) for line in matched[-50:]], indent="    ")
                else:
                    _print_kv(
                        f"  docker logs {args.executor_manager_container}",
                        f"no hits (since {args.docker_since})",
                    )
            else:
                _print_kv(
                    f"  docker logs {args.executor_manager_container}", "unavailable"
                )
    _safe_print()

    _safe_print("[diagnosis]")
    if unique_executors:
        missing = []
        for ex_name in unique_executors:
            status, body, _err = _http_get_json(
                f"{args.executor_manager_url.rstrip('/')}/executor-manager/executor/status?executor_name={ex_name}"
            )
            if status is None or not isinstance(body, dict):
                continue
            if body.get("exists") is False:
                missing.append(ex_name)
        if missing:
            _safe_print(
                "  subtask 可能卡住：subtask=RUNNING 但 executor 已不存在（exists=false / docker missing），"
                "常见是容器退出/被清理导致最终 COMPLETED/FAILED 回调未写回 DB。"
            )
            _table([f"missing executor: {name}" for name in missing], indent="  ")
        else:
            _safe_print(
                "  executor 看起来仍存在；若仍不完成，优先查 callback/网络/超时相关日志。"
            )
    else:
        _safe_print(
            "  未发现 executor_name；如果 UI 卡住，先确认该 task 是否真的进入执行阶段。"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
