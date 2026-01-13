from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from local_runner.codex_exec import run_codex_exec
from local_runner.config import DEFAULT_CONFIG_PATH, load_config
from local_runner.git_ops import changed_files, diff_binary, diff_text, get_snapshot
from local_runner.http_client import ApiClient


def _build_heartbeat_payload(cfg) -> Dict[str, Any]:
    return {
        "runner_id": cfg.runner_id,
        "name": cfg.name or cfg.runner_id,
        "version": "0.1.0",
        "capabilities": {
            "codex": True,
        },
        "workspaces": [
            {
                "id": ws.id,
                "name": ws.name,
                "capabilities": {"dirty_mode": ws.policy.dirty_mode},
            }
            for ws in cfg.workspaces
        ],
    }


def _make_subtask_update(
    subtask_id: int, status: str, progress: int, result: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "subtask_id": subtask_id,
        "status": status,
        "progress": progress,
        "result": result,
    }


def _sanitize_result(base: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    # Never include local filesystem paths in result payloads.
    if "repo_dir" in out:
        out.pop("repo_dir", None)
    return out


def run_loop(config_path: Path) -> int:
    cfg = load_config(config_path)
    api = ApiClient(
        server_url=cfg.server_url, api_key=cfg.api_key, runner_id=cfg.runner_id
    )

    try:
        while True:
            api.heartbeat(_build_heartbeat_payload(cfg))
            resp = api.dispatch_task(limit=1, task_status="PENDING")
            tasks = resp.get("tasks") or []
            if not tasks:
                time.sleep(cfg.poll_interval_sec)
                continue

            task = tasks[0]
            task_id = int(task["task_id"])
            subtask_id = int(task["subtask_id"])
            prompt = task.get("prompt") or ""
            shell_type = "Codex"
            local_workspace_id = task.get("local_workspace_id")
            if not local_workspace_id:
                api.update_subtask(
                    _make_subtask_update(
                        subtask_id,
                        "FAILED",
                        100,
                        _sanitize_result(
                            {
                                "shell_type": shell_type,
                                "value": "",
                                "error": "Missing local_workspace_id in task payload",
                            }
                        ),
                    )
                )
                continue

            ws = cfg.get_workspace(str(local_workspace_id))
            if ws is None:
                api.update_subtask(
                    _make_subtask_update(
                        subtask_id,
                        "FAILED",
                        100,
                        _sanitize_result(
                            {
                                "shell_type": shell_type,
                                "value": "",
                                "error": f"Workspace '{local_workspace_id}' not configured on this runner",
                            }
                        ),
                    )
                )
                continue

            cwd = ws.resolved_path()
            pre = get_snapshot(cwd)
            if pre.dirty and ws.policy.dirty_mode == "reject":
                api.update_subtask(
                    _make_subtask_update(
                        subtask_id,
                        "FAILED",
                        100,
                        _sanitize_result(
                            {
                                "shell_type": shell_type,
                                "value": "",
                                "error": "Workspace is dirty (uncommitted changes); refusing to run",
                                "local_runner": {
                                    "runner_id": cfg.runner_id,
                                    "workspace_id": ws.id,
                                    "git_pre": pre.__dict__,
                                },
                            }
                        ),
                    )
                )
                continue

            retry_mode = task.get("retry_mode") or "resume"
            resume_session_id = task.get("resume_session_id")
            model = task.get("model") or None

            api.update_subtask(
                _make_subtask_update(
                    subtask_id,
                    "RUNNING",
                    60,
                    _sanitize_result(
                        {
                            "shell_type": shell_type,
                            "value": "",
                            **(
                                {"resume_session_id": resume_session_id}
                                if resume_session_id
                                else {}
                            ),
                        }
                    ),
                )
            )

            def on_event_batch(
                events: List[Dict[str, Any]], current_resume: Optional[str]
            ) -> None:
                if not events and not current_resume:
                    return
                result: Dict[str, Any] = {
                    "shell_type": shell_type,
                    "codex_event": events,
                    **({"resume_session_id": current_resume} if current_resume else {}),
                }
                api.update_subtask(
                    _make_subtask_update(
                        subtask_id, "RUNNING", 70, _sanitize_result(result)
                    )
                )

            def on_value_chunk(
                _chunk: str, accumulated: str, current_resume: Optional[str]
            ) -> None:
                result: Dict[str, Any] = {
                    "shell_type": shell_type,
                    "value": accumulated,
                    **({"resume_session_id": current_resume} if current_resume else {}),
                }
                api.update_subtask(
                    _make_subtask_update(
                        subtask_id, "RUNNING", 70, _sanitize_result(result)
                    )
                )

            run_home = Path("~/.wegent/runs").expanduser() / str(task_id) / ".home"
            run_home.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ)
            env["HOME"] = str(run_home)

            try:
                run = run_codex_exec(
                    codex_cmd=cfg.codex_cmd,
                    cwd=cwd,
                    prompt=prompt,
                    model=model,
                    resume_session_id=(
                        resume_session_id
                        if isinstance(resume_session_id, str)
                        else None
                    ),
                    retry_mode=str(retry_mode),
                    env=env,
                    on_event_batch=on_event_batch,
                    on_value_chunk=on_value_chunk,
                )
            except FileNotFoundError:
                api.update_subtask(
                    _make_subtask_update(
                        subtask_id,
                        "FAILED",
                        100,
                        _sanitize_result(
                            {
                                "shell_type": shell_type,
                                "value": "",
                                "error": f"codex executable not found: {cfg.codex_cmd}",
                            }
                        ),
                    )
                )
                continue
            except Exception as e:
                api.update_subtask(
                    _make_subtask_update(
                        subtask_id,
                        "FAILED",
                        100,
                        _sanitize_result(
                            {
                                "shell_type": shell_type,
                                "value": "",
                                "error": f"codex execution failed: {e}",
                            }
                        ),
                    )
                )
                continue

            post = get_snapshot(cwd)
            files = changed_files(cwd)
            patch_txt = diff_text(cwd)
            patch_bin = diff_binary(cwd)

            artifacts: List[Dict[str, Any]] = []
            patch_text_artifact = None
            patch_bin_artifact = None

            max_bytes = ws.policy.max_artifact_mb * 1024 * 1024
            patch_txt_bytes = patch_txt.encode("utf-8", errors="replace")
            if patch_txt_bytes and len(patch_txt_bytes) <= max_bytes:
                patch_text_artifact = api.upload_artifact(
                    subtask_id=subtask_id, filename="patch.diff", data=patch_txt_bytes
                )
                artifacts.append(patch_text_artifact)
            if patch_bin and len(patch_bin) <= max_bytes:
                patch_bin_artifact = api.upload_artifact(
                    subtask_id=subtask_id, filename="patch.diffbin", data=patch_bin
                )
                artifacts.append(patch_bin_artifact)

            final_result: Dict[str, Any] = {
                "shell_type": shell_type,
                "value": run.value,
                **(
                    {"resume_session_id": run.resume_session_id}
                    if run.resume_session_id
                    else {}
                ),
                "local_runner": {
                    "runner_id": cfg.runner_id,
                    "workspace_id": ws.id,
                    "git_pre": pre.__dict__,
                    "git_post": post.__dict__,
                    "changed_files": files,
                    "artifacts": artifacts,
                    "patch": {
                        "text": patch_text_artifact,
                        "binary": patch_bin_artifact,
                    },
                    "stderr_tail": run.stderr_tail,
                },
            }

            api.update_subtask(
                _make_subtask_update(
                    subtask_id,
                    "COMPLETED" if run.ok else "FAILED",
                    100,
                    _sanitize_result(final_result),
                )
            )
    except KeyboardInterrupt:
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="wegent-local-runner")
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG_PATH))
    args = parser.parse_args()
    raise SystemExit(run_loop(Path(args.config)))
