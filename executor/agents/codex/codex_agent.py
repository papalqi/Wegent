#!/usr/bin/env python

# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-

import asyncio
import json
import os
import shlex
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from executor.agents.agno.thinking_step_manager import ThinkingStepManager
from executor.agents.base import Agent
from executor.agents.claude_code.progress_state_manager import \
    ProgressStateManager
from executor.config import config
from executor.tasks.resource_manager import ResourceManager
from executor.tasks.task_state_manager import TaskState, TaskStateManager
from executor.utils.skill_deployer import deploy_skills_from_backend
from shared.logger import setup_logger
from shared.status import TaskStatus
from shared.utils.sensitive_data_masker import mask_sensitive_data

logger = setup_logger("codex_agent")

# Increase stream reader limit to tolerate verbose commands (e.g., pytest output).
# Keep within reasonable bounds to avoid unbounded memory growth.
STREAM_READER_LIMIT = 1024 * 1024 * 4  # 4 MiB


def _extract_thread_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    if event.get("type") != "thread.started":
        return None

    candidates: list[Any] = [
        event.get("thread_id"),
        event.get("threadId"),
    ]
    thread = event.get("thread")
    if isinstance(thread, dict):
        candidates.extend(
            [
                thread.get("id"),
                thread.get("thread_id"),
                thread.get("threadId"),
            ]
        )

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


class CodexAgent(Agent):
    """
    Codex Agent that integrates with the @openai/codex CLI in non-interactive mode.

    This agent runs `codex exec --json` and maps JSONL events into Wegent's
    callback streaming contract via incremental updates to `result.value`.
    """

    def get_name(self) -> str:
        return "Codex"

    def __init__(self, task_data: Dict[str, Any]):
        super().__init__(task_data)
        self.session_id = self.task_id
        self.resume_session_id: Optional[str] = None
        self.retry_mode: str = "resume"
        self.prompt = task_data.get("prompt", "")

        self.options = self._extract_codex_options(task_data)

        self.thinking_manager = ThinkingStepManager(
            progress_reporter=self.report_progress
        )
        self.state_manager: Optional[ProgressStateManager] = None

        self.task_state_manager = TaskStateManager()
        self.resource_manager = ResourceManager()
        self.task_state_manager.set_state(self.task_id, TaskState.RUNNING)

        self._process: Optional[asyncio.subprocess.Process] = None
        self._model: Optional[str] = None
        self._codex_env: Optional[Dict[str, str]] = None
        self._codex_dir: Optional[Path] = None

        resume_session_id = task_data.get("resume_session_id")
        if isinstance(resume_session_id, str) and resume_session_id.strip():
            self.resume_session_id = resume_session_id.strip()

        retry_mode = task_data.get("retry_mode")
        if isinstance(retry_mode, str) and retry_mode.strip():
            self.retry_mode = retry_mode.strip()

        # Configure OpenAI auth for Codex CLI from bot agent_config
        self._configure_openai_env(task_data)

    def initialize(self) -> TaskStatus:
        try:
            bots = self.task_data.get("bot") or []
            if not isinstance(bots, list) or not bots:
                return TaskStatus.SUCCESS

            bot_config = bots[0] if isinstance(bots[0], dict) else {}
            skills = bot_config.get("skills", [])
            if not skills:
                return TaskStatus.SUCCESS

            logger.info("Found %s skills to deploy: %s", len(skills), skills)
            deploy_skills_from_backend(
                task_data=self.task_data,
                skills=skills,
                skills_dir=str(self._get_codex_dir() / "skills"),
            )
            return TaskStatus.SUCCESS
        except Exception as e:
            logger.warning("Codex initialize failed (skills may be unavailable): %s", e)
            return TaskStatus.SUCCESS

    def _extract_codex_options(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        bots = task_data.get("bot") or []
        if not isinstance(bots, list) or not bots:
            return {}

        bot_config = bots[0] if isinstance(bots[0], dict) else {}
        options: Dict[str, Any] = {}

        # For consistency with other agents, support overriding cwd from bot config
        cwd = bot_config.get("cwd")
        if isinstance(cwd, str) and cwd.strip():
            options["cwd"] = cwd.strip()

        return options

    def _configure_openai_env(self, task_data: Dict[str, Any]) -> None:
        bots = task_data.get("bot") or []
        if not isinstance(bots, list) or not bots:
            return

        bot_config = bots[0] if isinstance(bots[0], dict) else {}
        agent_config = bot_config.get("agent_config") or {}
        if not isinstance(agent_config, dict):
            return

        env = agent_config.get("env") or {}
        if not isinstance(env, dict):
            return

        api_key = env.get("api_key")
        base_url = env.get("base_url")
        codex_config_toml = env.get("CODEX_CONFIG_TOML")

        # Never mutate the host process environment for credentials/config.
        # We pass an isolated environment to the Codex CLI subprocess instead.
        codex_env: Dict[str, str] = dict(os.environ)
        self._codex_env = codex_env

        should_isolate_home = (
            isinstance(api_key, str) and api_key and api_key != "***"
        ) or (isinstance(codex_config_toml, str) and codex_config_toml.strip())
        if should_isolate_home:
            self._prepare_isolated_codex_dir(codex_env)

        if isinstance(api_key, str) and api_key and api_key != "***":
            codex_env["OPENAI_API_KEY"] = api_key
            if should_isolate_home:
                self._ensure_codex_auth(api_key)

        if isinstance(base_url, str) and base_url.strip():
            codex_env["OPENAI_BASE_URL"] = base_url.strip()

        if (
            should_isolate_home
            and isinstance(codex_config_toml, str)
            and codex_config_toml.strip()
        ):
            self._ensure_codex_config(codex_config_toml)

        model = env.get("model_id") or env.get("model")
        if isinstance(model, str) and model.strip():
            self._model = model.strip()

        logger.info(
            "Configured Codex env (masked): %s",
            mask_sensitive_data(
                {
                    "has_api_key": bool(codex_env.get("OPENAI_API_KEY")),
                    "base_url": codex_env.get("OPENAI_BASE_URL", ""),
                    "model": self._model,
                    "codex_dir": str(self._codex_dir) if self._codex_dir else "",
                }
            ),
        )

    def _prepare_isolated_codex_dir(self, codex_env: Dict[str, str]) -> None:
        codex_home = Path(config.WORKSPACE_ROOT) / str(self.task_id) / ".wegent_home"
        try:
            codex_home.mkdir(parents=True, exist_ok=True)
            os.chmod(codex_home, 0o700)
        except Exception as e:
            logger.warning("Failed to prepare Codex HOME directory: %s", e)

        codex_env["HOME"] = str(codex_home)
        self._codex_dir = codex_home / ".codex"
        try:
            self._codex_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(self._codex_dir, 0o700)
        except Exception as e:
            logger.warning("Failed to prepare Codex directory: %s", e)

    def _get_codex_dir(self) -> Path:
        if self._codex_dir is not None:
            return self._codex_dir
        return Path(os.path.expanduser("~/.codex"))

    def _ensure_codex_auth(self, api_key: str) -> None:
        try:
            codex_dir = self._get_codex_dir()
            codex_dir.mkdir(parents=True, exist_ok=True)

            auth_path = codex_dir / "auth.json"
            auth_path.write_text(
                json.dumps({"OPENAI_API_KEY": api_key}, ensure_ascii=False),
                encoding="utf-8",
            )
            os.chmod(auth_path, 0o600)
        except Exception as e:
            logger.warning("Failed to write Codex auth.json: %s", e)

    def _ensure_codex_config(self, codex_config_toml: str) -> None:
        try:
            codex_dir = self._get_codex_dir()
            codex_dir.mkdir(parents=True, exist_ok=True)

            decoded = self._decode_codex_config_toml(codex_config_toml)
            config_path = codex_dir / "config.toml"
            config_path.write_text(decoded, encoding="utf-8")
            os.chmod(config_path, 0o600)
        except Exception as e:
            logger.warning("Failed to write Codex config.toml: %s", e)

    def _decode_codex_config_toml(self, value: str) -> str:
        # Backend stores config in JSON and may escape newlines for transport.
        decoded = value.replace("\\r\\n", "\n").replace("\\n", "\n")
        return decoded.replace('\\"', '"')

    def _initialize_state_manager(self) -> None:
        if self.state_manager is not None:
            return

        project_path = self.options.get("cwd") or self.project_path
        self.state_manager = ProgressStateManager(
            thinking_manager=self.thinking_manager,
            task_data=self.task_data,
            report_progress_callback=self.report_progress,
            project_path=project_path,
        )

        # Allow ThinkingStepManager to report immediately through state manager.
        self.thinking_manager.set_state_manager(self.state_manager)

    def pre_execute(self) -> TaskStatus:
        try:
            repo_dir = self.task_data.get("repo_dir")
            if isinstance(repo_dir, str) and repo_dir.strip():
                repo_dir = repo_dir.strip()
                os.makedirs(repo_dir, exist_ok=True)
                try:
                    from shared.utils.persistent_repo import detect_repo_vcs

                    repo_vcs, is_p4 = detect_repo_vcs(Path(repo_dir))
                    self.task_data["repo_vcs"] = repo_vcs or ""
                    self.task_data["is_p4"] = is_p4
                    logger.info(
                        "Detected repo_vcs=%s is_p4=%s repo_dir=%s",
                        repo_vcs,
                        is_p4,
                        repo_dir,
                    )
                except Exception as e:
                    logger.warning("Failed to detect repo VCS for %s: %s", repo_dir, e)

                if not self.options.get("cwd"):
                    self.options["cwd"] = repo_dir
                    self.project_path = repo_dir
                    logger.info("Set cwd to %s", repo_dir)

            git_url = self.task_data.get("git_url")
            if git_url:
                self.download_code()

                if not self.options.get("cwd") and self.project_path:
                    self.options["cwd"] = self.project_path
                    logger.info("Set cwd to %s", self.project_path)

            return TaskStatus.SUCCESS
        except Exception as e:
            logger.exception("Codex pre_execute failed: %s", e)
            return TaskStatus.FAILED

    def execute(self) -> TaskStatus:
        try:
            self._initialize_state_manager()
            self.state_manager.initialize_workbench("running")

            self.thinking_manager.add_thinking_step_by_key(
                title_key="thinking.initialize_agent", report_immediately=False
            )

            self.state_manager.report_progress(
                60,
                TaskStatus.RUNNING.value,
                "${{thinking.initialize_agent}}",
                extra_result={
                    "value": "",
                    "shell_type": "Codex",
                    **(
                        {"resume_session_id": self.resume_session_id}
                        if self._should_use_resume()
                        else {}
                    ),
                },
            )

            try:
                asyncio.get_running_loop()
                asyncio.create_task(self._async_execute())
                return TaskStatus.RUNNING
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._async_execute())
                finally:
                    loop.close()
        except Exception as e:
            logger.exception("Codex execute failed: %s", e)
            if self.state_manager:
                self.state_manager.update_workbench_status("failed")
                self.state_manager.report_progress(
                    100,
                    TaskStatus.FAILED.value,
                    f"Codex execution failed: {e}",
                    extra_result={"error": str(e), "shell_type": "Codex"},
                )
            return TaskStatus.FAILED

    def _build_prompt(self) -> str:
        bots = self.task_data.get("bot") or []
        bot_config = (
            bots[0]
            if isinstance(bots, list) and bots and isinstance(bots[0], dict)
            else {}
        )
        system_prompt = (
            bot_config.get("system_prompt") if isinstance(bot_config, dict) else ""
        )

        parts = []
        if isinstance(system_prompt, str) and system_prompt.strip():
            parts.append(system_prompt.strip())
        parts.append(self.prompt or "")

        cwd = self.options.get("cwd") or ""
        git_url = self.task_data.get("git_url") or ""
        repo_dir = self.task_data.get("repo_dir") or ""
        repo_vcs = self.task_data.get("repo_vcs") or ""
        is_p4 = self.task_data.get("is_p4")
        if cwd:
            parts.append(f"Current working directory: {cwd}")
        if git_url:
            parts.append(f"Project url: {git_url}")
        if isinstance(repo_dir, str) and repo_dir.strip():
            parts.append(f"Persistent repo directory: {repo_dir.strip()}")
        if isinstance(repo_vcs, str) and repo_vcs.strip():
            parts.append(f"repo_vcs: {repo_vcs.strip()}")
        if isinstance(is_p4, bool):
            parts.append(f"is_p4: {is_p4}")

        return "\n\n".join(p for p in parts if p)

    def _build_command(self, cwd: str) -> list[str]:
        cmd = [
            "codex",
            "exec",
            "--json",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-C",
            cwd,
        ]
        if self._model:
            cmd.extend(["--model", self._model])

        if self._should_use_resume():
            cmd.extend(["resume", self.resume_session_id])

        # Read prompt from stdin to avoid OS arg length limits.
        cmd.append("-")
        return cmd

    def _should_use_resume(self) -> bool:
        return (
            isinstance(self.resume_session_id, str)
            and self.resume_session_id != ""
            and self.retry_mode != "new_session"
        )

    def _open_event_stream_files(
        self,
    ) -> Tuple[Optional[Path], Optional[Path], Optional[Any], Optional[Any]]:
        if not config.CODEX_PERSIST_EVENT_STREAM:
            return None, None, None, None

        task_root = Path(config.WORKSPACE_ROOT) / str(self.task_id)
        task_root.mkdir(parents=True, exist_ok=True)

        stdout_path = task_root / config.CODEX_EVENT_STREAM_FILENAME
        stderr_path = task_root / config.CODEX_STDERR_FILENAME

        stdout_fp = stdout_path.open("ab")
        stderr_fp = stderr_path.open("ab")
        return stdout_path, stderr_path, stdout_fp, stderr_fp

    async def _async_execute(self) -> TaskStatus:
        if self.task_state_manager.is_cancelled(self.task_id):
            logger.info("Task %s was cancelled before Codex execution", self.task_id)
            return TaskStatus.COMPLETED

        if self._should_run_shell_smoke():
            return await self._execute_shell_smoke()

        if self._should_run_web_ui_validator():
            return await self._execute_web_ui_validator()

        self.thinking_manager.add_thinking_step_by_key(
            title_key="thinking.running", report_immediately=False
        )

        cwd = self.options.get("cwd") or os.path.join(
            config.WORKSPACE_ROOT, str(self.task_id)
        )
        os.makedirs(cwd, exist_ok=True)

        prompt = self._build_prompt()
        cmd = self._build_command(cwd)
        logger.info(
            "Starting Codex CLI: %s", mask_sensitive_data({"cmd": cmd, "cwd": cwd})
        )

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._codex_env,
            limit=STREAM_READER_LIMIT,
        )
        self._process = process
        self.resource_manager.register_resource(
            task_id=self.task_id,
            resource_id=f"codex_proc_{self.session_id}",
            is_async=False,
        )

        assert process.stdin is not None
        process.stdin.write(prompt.encode("utf-8"))
        await process.stdin.drain()
        process.stdin.close()

        accumulated = ""
        stderr_lines: list[str] = []
        stdout_path: Optional[Path] = None
        stderr_path: Optional[Path] = None
        stdout_fp = None
        stderr_fp = None

        try:
            stdout_path, stderr_path, stdout_fp, stderr_fp = (
                self._open_event_stream_files()
            )
            if stdout_path and stderr_path:
                logger.info(
                    "Persisting Codex event stream for task %s to %s (stderr: %s)",
                    self.task_id,
                    stdout_path,
                    stderr_path,
                )
        except Exception as e:
            logger.warning("Failed to open Codex event stream files: %s", e)

        async def _drain_stderr() -> None:
            assert process.stderr is not None
            async for raw in process.stderr:
                if stderr_fp is not None:
                    try:
                        stderr_fp.write(raw)
                        stderr_fp.flush()
                    except Exception:
                        pass
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    stderr_lines.append(line)
                    if len(stderr_lines) > 200:
                        stderr_lines.pop(0)

        stderr_task = asyncio.create_task(_drain_stderr())

        assert process.stdout is not None
        cancelled = False
        codex_event_buffer: list[dict[str, Any]] = []
        last_event_flush = time.monotonic()

        async def _flush_codex_events() -> None:
            nonlocal last_event_flush, codex_event_buffer
            if not codex_event_buffer:
                return
            # Emit as a batch to avoid overwhelming the callback channel.
            batch = codex_event_buffer
            codex_event_buffer = []
            last_event_flush = time.monotonic()
            try:
                self.state_manager.report_progress(
                    70,
                    TaskStatus.RUNNING.value,
                    "${{thinking.running}}",
                    extra_result={
                        "codex_event": batch,
                        "shell_type": "Codex",
                        **(
                            {"resume_session_id": self.resume_session_id}
                            if self.resume_session_id
                            else {}
                        ),
                    },
                )
            except Exception:
                # Best-effort: event streaming should not fail the task.
                pass

        try:
            while True:
                raw = await _readline_tolerant(process.stdout)
                if not raw:
                    eof = (
                        process.stdout.at_eof()
                        if hasattr(process.stdout, "at_eof")
                        else True
                    )
                    if eof:
                        break
                    # If we truncated an overlong line, continue reading.
                    continue

                if stdout_fp is not None:
                    try:
                        stdout_fp.write(raw)
                        stdout_fp.flush()
                    except Exception:
                        pass
                if self.task_state_manager.is_cancelled(self.task_id):
                    logger.info(
                        "Task %s cancelled during Codex execution", self.task_id
                    )
                    cancelled = True
                    _terminate_process(process)
                    break

                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("Non-JSON line from Codex: %s", line[:200])
                    continue

                if isinstance(event, dict):
                    codex_event_buffer.append(event)
                    # Flush frequently enough for "like chat" UX, but bounded to reduce load.
                    if (
                        len(codex_event_buffer) >= 5
                        or (time.monotonic() - last_event_flush) >= 0.2
                    ):
                        await _flush_codex_events()

                    thread_id = _extract_thread_id_from_event(event)
                    if thread_id and thread_id != self.resume_session_id:
                        self.resume_session_id = thread_id
                        self.state_manager.report_progress(
                            70,
                            TaskStatus.RUNNING.value,
                            "${{thinking.running}}",
                            extra_result={
                                "value": accumulated,
                                "shell_type": "Codex",
                                "resume_session_id": thread_id,
                            },
                        )

                event_type = event.get("type")
                if event_type == "item.completed":
                    item = event.get("item") or {}
                    if item.get("type") == "agent_message":
                        text = item.get("text") or ""
                        if isinstance(text, str) and text:
                            # Stream in smaller chunks to trigger backend chat:chunk updates.
                            for chunk in _chunk_text(text, chunk_size=400):
                                accumulated += chunk
                                self.state_manager.report_progress(
                                    70,
                                    TaskStatus.RUNNING.value,
                                    "${{thinking.running}}",
                                    extra_result={
                                        "value": accumulated,
                                        "shell_type": "Codex",
                                        **(
                                            {
                                                "resume_session_id": self.resume_session_id
                                            }
                                            if self.resume_session_id
                                            else {}
                                        ),
                                    },
                                )
                                await asyncio.sleep(0)
                elif event_type == "turn.failed":
                    error_msg = (event.get("error") or {}).get(
                        "message"
                    ) or "Codex turn failed"
                    raise RuntimeError(error_msg)

            # Flush any remaining buffered events before process exit handling.
            await _flush_codex_events()

            # Wait for process to exit
            try:
                returncode = await asyncio.wait_for(
                    process.wait(),
                    timeout=min(config.GRACEFUL_SHUTDOWN_TIMEOUT, 2),
                )
            except asyncio.TimeoutError:
                _terminate_process(process)
                returncode = await process.wait()
            await stderr_task

            if cancelled or self.task_state_manager.is_cancelled(self.task_id):
                return TaskStatus.COMPLETED

            if returncode != 0:
                tail = "\n".join(stderr_lines[-20:])
                raise RuntimeError(
                    f"Codex CLI exited with code {returncode}. stderr_tail:\n{tail}"
                )

            self.thinking_manager.add_thinking_step_by_key(
                title_key="thinking.execution_completed", report_immediately=False
            )
            self.state_manager.update_workbench_status(
                "completed", result_value=accumulated
            )
            self.state_manager.report_progress(
                100,
                TaskStatus.COMPLETED.value,
                "${{thinking.execution_completed}}",
                extra_result={
                    "value": accumulated,
                    "shell_type": "Codex",
                    **(
                        {"resume_session_id": self.resume_session_id}
                        if self.resume_session_id
                        else {}
                    ),
                },
            )
            self.task_state_manager.set_state(self.task_id, TaskState.COMPLETED)
            return TaskStatus.COMPLETED

        except Exception as e:
            logger.exception("Codex execution error: %s", e)
            self.thinking_manager.add_thinking_step_by_key(
                title_key="thinking.execution_failed",
                report_immediately=False,
                details={"error": str(e)},
            )
            _terminate_process(process)
            self.task_state_manager.set_state(self.task_id, TaskState.FAILED)
            self.state_manager.update_workbench_status("failed")
            self.state_manager.report_progress(
                100,
                TaskStatus.FAILED.value,
                f"Codex execution failed: {e}",
                extra_result={
                    "error": str(e),
                    "value": accumulated,
                    "shell_type": "Codex",
                    **(
                        {"resume_session_id": self.resume_session_id}
                        if self.resume_session_id
                        else {}
                    ),
                },
            )
            return TaskStatus.FAILED
        finally:
            try:
                if stdout_fp is not None:
                    stdout_fp.close()
            finally:
                if stderr_fp is not None:
                    stderr_fp.close()
            self._process = None
            self.resource_manager.unregister_resource(
                self.task_id, f"codex_proc_{self.session_id}"
            )

    def _should_run_shell_smoke(self) -> bool:
        prompt = (self.prompt or "").strip()
        if "@shell_smoke" not in prompt:
            return False

        bots = self.task_data.get("bot") or []
        if not isinstance(bots, list) or not bots:
            return False

        bot_config = bots[0] if isinstance(bots[0], dict) else {}
        skills = bot_config.get("skills") or []
        if not isinstance(skills, list):
            return False

        return "shell_smoke" in skills

    def _should_run_web_ui_validator(self) -> bool:
        prompt = (self.prompt or "").strip()
        if "@web_ui_validator" not in prompt:
            return False

        bots = self.task_data.get("bot") or []
        if not isinstance(bots, list) or not bots:
            return False

        bot_config = bots[0] if isinstance(bots[0], dict) else {}
        skills = bot_config.get("skills") or []
        if not isinstance(skills, list):
            return False

        return "web_ui_validator" in skills

    def _extract_web_ui_validator_args(self) -> list[str]:
        prompt = (self.prompt or "").strip()
        token = "@web_ui_validator"
        if token not in prompt:
            return []

        for line in prompt.splitlines():
            idx = line.find(token)
            if idx == -1:
                continue
            remainder = line[idx + len(token) :].strip()
            if not remainder:
                return []
            try:
                return shlex.split(remainder)
            except ValueError:
                return []

        return []

    async def _execute_web_ui_validator(self) -> TaskStatus:
        shell_type = "Codex"
        skill_name = "web_ui_validator"
        script_path = str(
            self._get_codex_dir() / "skills" / skill_name / "web_ui_validator.py"
        )

        if not os.path.exists(script_path):
            msg = f"Web UI validator skill not deployed: missing {script_path}"
            logger.error(msg)
            if self.state_manager:
                self.state_manager.report_progress(
                    100,
                    TaskStatus.FAILED.value,
                    msg,
                    extra_result={"value": msg, "shell_type": shell_type},
                )
            else:
                self.report_progress(
                    100,
                    TaskStatus.FAILED.value,
                    msg,
                    result={"value": msg, "shell_type": shell_type},
                )
            return TaskStatus.FAILED

        work_dir = self.options.get("cwd") or os.path.join(
            config.WORKSPACE_ROOT, str(self.task_id), "web_ui_validator"
        )
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        args = self._extract_web_ui_validator_args()

        def _report(progress: int, status: str, message: str, value: str) -> None:
            if self.state_manager:
                self.state_manager.report_progress(
                    progress,
                    status,
                    message,
                    extra_result={"value": value, "shell_type": shell_type},
                )
            else:
                self.report_progress(
                    progress,
                    status,
                    message,
                    result={"value": value, "shell_type": shell_type},
                )

        logger.info(
            "Running web ui validator: script=%s args=%s cwd=%s task_id=%s",
            script_path,
            args,
            work_dir,
            self.task_id,
        )

        content = ""
        _report(70, TaskStatus.RUNNING.value, "Web UI validator started", content)

        process = await asyncio.create_subprocess_exec(
            "python3",
            script_path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=work_dir,
            env=self._codex_env,
            limit=STREAM_READER_LIMIT,
        )
        self._process = process
        self.resource_manager.register_resource(
            task_id=self.task_id,
            resource_id=f"codex_web_ui_validator_proc_{self.session_id}",
            is_async=False,
        )

        line_count = 0
        try:
            assert process.stdout is not None
            while True:
                if self.task_state_manager.is_cancelled(self.task_id):
                    logger.info("Web UI validator cancelled: task_id=%s", self.task_id)
                    _terminate_process(process)
                    await process.wait()
                    _report(
                        100,
                        TaskStatus.CANCELLED.value,
                        "Web UI validator cancelled",
                        content,
                    )
                    return TaskStatus.CANCELLED

                line = await _readline_tolerant(process.stdout)
                if not line:
                    eof = (
                        process.stdout.at_eof()
                        if hasattr(process.stdout, "at_eof")
                        else True
                    )
                    if eof:
                        break
                    continue

                text = line.decode("utf-8", errors="replace")
                content += text
                line_count += 1

                progress = min(95, 70 + line_count * 2)
                _report(
                    progress,
                    TaskStatus.RUNNING.value,
                    "Web UI validator running",
                    content,
                )

            exit_code = await process.wait()
            if exit_code != 0:
                msg = f"Web UI validator failed with exit_code={exit_code}"
                logger.error(msg)
                _report(100, TaskStatus.FAILED.value, msg, content)
                return TaskStatus.FAILED

            _report(
                100, TaskStatus.COMPLETED.value, "Web UI validator completed", content
            )
            return TaskStatus.COMPLETED
        finally:
            self._process = None
            self.resource_manager.unregister_resource(
                self.task_id, f"codex_web_ui_validator_proc_{self.session_id}"
            )

    async def _execute_shell_smoke(self) -> TaskStatus:
        shell_type = "Codex"
        skill_name = "shell_smoke"
        script_path = str(
            self._get_codex_dir() / "skills" / skill_name / "shell_smoke.py"
        )

        if not os.path.exists(script_path):
            msg = f"Shell smoke skill not deployed: missing {script_path}"
            logger.error(msg)
            if self.state_manager:
                self.state_manager.report_progress(
                    100,
                    TaskStatus.FAILED.value,
                    msg,
                    extra_result={"value": msg, "shell_type": shell_type},
                )
            else:
                self.report_progress(
                    100,
                    TaskStatus.FAILED.value,
                    msg,
                    result={"value": msg, "shell_type": shell_type},
                )
            return TaskStatus.FAILED

        work_dir = self.project_path or os.path.join(
            config.WORKSPACE_ROOT, str(self.task_id), "smoke"
        )
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        def _report(progress: int, status: str, message: str, value: str) -> None:
            if self.state_manager:
                self.state_manager.report_progress(
                    progress,
                    status,
                    message,
                    extra_result={"value": value, "shell_type": shell_type},
                )
            else:
                self.report_progress(
                    progress,
                    status,
                    message,
                    result={"value": value, "shell_type": shell_type},
                )

        logger.info(
            "Running shell smoke: script=%s cwd=%s task_id=%s",
            script_path,
            work_dir,
            self.task_id,
        )

        content = ""
        _report(70, TaskStatus.RUNNING.value, "Shell smoke started", content)

        process = await asyncio.create_subprocess_exec(
            "python3",
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=work_dir,
            env=self._codex_env,
            limit=STREAM_READER_LIMIT,
        )
        self._process = process
        self.resource_manager.register_resource(
            task_id=self.task_id,
            resource_id=f"codex_smoke_proc_{self.session_id}",
            is_async=False,
        )

        line_count = 0
        try:
            assert process.stdout is not None
            while True:
                if self.task_state_manager.is_cancelled(self.task_id):
                    logger.info("Shell smoke cancelled: task_id=%s", self.task_id)
                    _terminate_process(process)
                    await process.wait()
                    _report(
                        100,
                        TaskStatus.CANCELLED.value,
                        "Shell smoke cancelled",
                        content,
                    )
                    return TaskStatus.CANCELLED

                line = await _readline_tolerant(process.stdout)
                if not line:
                    eof = (
                        process.stdout.at_eof()
                        if hasattr(process.stdout, "at_eof")
                        else True
                    )
                    if eof:
                        break
                    continue

                text = line.decode("utf-8", errors="replace")
                content += text
                line_count += 1

                progress = min(95, 70 + line_count * 5)
                _report(
                    progress,
                    TaskStatus.RUNNING.value,
                    "Shell smoke running",
                    content,
                )

            exit_code = await process.wait()
            if exit_code != 0:
                msg = f"Shell smoke failed with exit_code={exit_code}"
                logger.error(msg)
                _report(100, TaskStatus.FAILED.value, msg, content)
                return TaskStatus.FAILED

            _report(100, TaskStatus.COMPLETED.value, "Shell smoke completed", content)
            return TaskStatus.COMPLETED
        finally:
            self._process = None
            self.resource_manager.unregister_resource(
                self.task_id, f"codex_smoke_proc_{self.session_id}"
            )

    def cancel_run(self) -> bool:
        """
        Cancel the current running Codex task.

        Note: cancellation callback is sent asynchronously by AgentService to avoid
        blocking executor_manager's cancel request.
        """
        try:
            self.task_state_manager.set_state(self.task_id, TaskState.CANCELLED)

            if self._process:
                _terminate_process(self._process)

            # Wait briefly for cleanup
            max_wait = min(config.GRACEFUL_SHUTDOWN_TIMEOUT, 2)
            waited = 0.0
            while waited < max_wait:
                if self.task_state_manager.get_state(self.task_id) is None:
                    return True
                time.sleep(0.1)
                waited += 0.1

            return True
        except Exception as e:
            logger.exception("Error cancelling Codex task %s: %s", self.task_id, e)
            self.task_state_manager.set_state(self.task_id, TaskState.CANCELLED)
            return False


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _terminate_process(proc: asyncio.subprocess.Process) -> None:
    try:
        if proc.returncode is not None:
            return
        proc.terminate()
    except ProcessLookupError:
        return
    except Exception:
        # Fall back to kill
        try:
            proc.kill()
        except Exception:
            return


async def _readline_tolerant(stream: Optional[asyncio.StreamReader]) -> bytes:
    """
    Read a line from the given stream but tolerate overlong lines.

    If asyncio raises LimitOverrunError (line longer than stream limit),
    we read a fixed-size chunk instead of failing the task.
    """
    if stream is None:
        return b""
    try:
        if hasattr(stream, "readline"):
            return await stream.readline()  # type: ignore[func-returns-value]
        # Fallback for test fakes that are async iterators.
        if hasattr(stream, "__anext__"):
            try:
                return await stream.__anext__()  # type: ignore[attr-defined]
            except StopAsyncIteration:
                return b""
        return b""
    except asyncio.LimitOverrunError:
        # Consume a chunk to move the cursor forward; caller can decide to continue.
        if hasattr(stream, "read"):
            return await stream.read(STREAM_READER_LIMIT)  # type: ignore[attr-defined]
        return b""
