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
from typing import Any, Dict, Optional

from executor.agents.agno.thinking_step_manager import ThinkingStepManager
from executor.agents.base import Agent
from executor.agents.claude_code.progress_state_manager import ProgressStateManager
from executor.config import config
from executor.tasks.resource_manager import ResourceManager
from executor.tasks.task_state_manager import TaskState, TaskStateManager
from executor.utils.skill_deployer import deploy_skills_from_backend
from shared.logger import setup_logger
from shared.status import TaskStatus
from shared.utils.sensitive_data_masker import mask_sensitive_data

logger = setup_logger("codex_agent")


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
                skills_dir=os.path.expanduser("~/.codex/skills"),
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
        if isinstance(api_key, str) and api_key and api_key != "***":
            os.environ["OPENAI_API_KEY"] = api_key

        base_url = env.get("base_url")
        if isinstance(base_url, str) and base_url.strip():
            os.environ["OPENAI_BASE_URL"] = base_url.strip()

        model = env.get("model_id") or env.get("model")
        if isinstance(model, str) and model.strip():
            self._model = model.strip()

        logger.info(
            "Configured Codex env (masked): %s",
            mask_sensitive_data(
                {
                    "has_api_key": bool(os.environ.get("OPENAI_API_KEY")),
                    "base_url": os.environ.get("OPENAI_BASE_URL", ""),
                    "model": self._model,
                }
            ),
        )

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
                extra_result={"value": "", "shell_type": "Codex"},
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
        if cwd:
            parts.append(f"Current working directory: {cwd}")
        if git_url:
            parts.append(f"Project url: {git_url}")

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

        # Read prompt from stdin to avoid OS arg length limits.
        cmd.append("-")
        return cmd

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

        async def _drain_stderr() -> None:
            assert process.stderr is not None
            async for raw in process.stderr:
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    stderr_lines.append(line)
                    if len(stderr_lines) > 200:
                        stderr_lines.pop(0)

        stderr_task = asyncio.create_task(_drain_stderr())

        assert process.stdout is not None
        cancelled = False
        try:
            async for raw in process.stdout:
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
                                    },
                                )
                                await asyncio.sleep(0)
                elif event_type == "turn.failed":
                    error_msg = (event.get("error") or {}).get(
                        "message"
                    ) or "Codex turn failed"
                    raise RuntimeError(error_msg)

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
                extra_result={"value": accumulated, "shell_type": "Codex"},
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
                },
            )
            return TaskStatus.FAILED
        finally:
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
        script_path = os.path.expanduser(
            f"~/.codex/skills/{skill_name}/web_ui_validator.py"
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

                line = await process.stdout.readline()
                if not line:
                    break

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
        script_path = os.path.expanduser(f"~/.codex/skills/{skill_name}/shell_smoke.py")

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

                line = await process.stdout.readline()
                if not line:
                    break

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
