# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import os
from typing import Iterable, Optional
from unittest.mock import MagicMock

import executor.agents.codex.codex_agent as codex_agent_module
import pytest
from executor.agents.codex.codex_agent import CodexAgent
from shared.status import TaskStatus


class _FakeAsyncStream:
    def __init__(self, lines: Iterable[bytes]):
        self._it = iter(lines)

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return next(self._it)
        except StopIteration as e:
            raise StopAsyncIteration from e


class _FakeStdin:
    def __init__(self):
        self.buffer = b""
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer += data

    async def drain(self) -> None:
        await asyncio.sleep(0)

    def close(self) -> None:
        self.closed = True


class _FakeProcess:
    def __init__(
        self,
        *,
        stdout_lines: Iterable[bytes],
        stderr_lines: Iterable[bytes] = (),
        final_returncode: int = 0,
    ):
        self.stdin = _FakeStdin()
        self.stdout = _FakeAsyncStream(stdout_lines)
        self.stderr = _FakeAsyncStream(stderr_lines)
        self._final_returncode = final_returncode
        self.returncode: Optional[int] = None
        self.terminated = False
        self.killed = False

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = self._final_returncode
        await asyncio.sleep(0)
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = self._final_returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = self._final_returncode


class _FakeStateManager:
    def __init__(self):
        self.progress_calls = []
        self.workbench_status_calls = []

    def initialize_workbench(self, status: str = "running") -> None:
        return None

    def update_workbench_status(self, status: str, result_value: str = None) -> None:
        self.workbench_status_calls.append((status, result_value))

    def report_progress(
        self,
        progress: int,
        status: str,
        message: str,
        include_thinking: bool = True,
        include_workbench: bool = True,
        extra_result=None,
    ) -> None:
        self.progress_calls.append((progress, status, message, extra_result or {}))


class TestCodexAgent:
    def test_configure_openai_env_sets_env_and_model(self, tmp_path, monkeypatch):
        monkeypatch.setattr(codex_agent_module.config, "WORKSPACE_ROOT", str(tmp_path))

        task_data = {
            "task_id": 1,
            "subtask_id": 1,
            "prompt": "hello",
            "user": {"name": "test", "user_name": "test"},
            "bot": [
                {
                    "shell_type": "codex",
                    "agent_config": {
                        "env": {
                            "api_key": "sk-test",
                            "base_url": "https://example.com",
                            "model_id": "gpt-test",
                        }
                    },
                }
            ],
        }

        agent = CodexAgent(task_data)

        assert agent._codex_env is not None
        assert agent._codex_env["OPENAI_API_KEY"] == "sk-test"
        assert agent._codex_env["OPENAI_BASE_URL"] == "https://example.com"
        assert agent._model == "gpt-test"

    def test_configure_openai_env_writes_codex_config_and_auth(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(codex_agent_module.config, "WORKSPACE_ROOT", str(tmp_path))

        task_data = {
            "task_id": 1,
            "subtask_id": 1,
            "prompt": "hello",
            "user": {"name": "test", "user_name": "test"},
            "bot": [
                {
                    "shell_type": "codex",
                    "agent_config": {
                        "env": {
                            "api_key": "sk-test",
                            "CODEX_CONFIG_TOML": (
                                'model_provider = "cch"\\n'
                                'model = "gpt-test"\\n'
                                "\\n"
                                "[features]\\n"
                                "plan_tool = true\\n"
                            ),
                        }
                    },
                }
            ],
        }

        CodexAgent(task_data)

        codex_dir = tmp_path / "1" / ".wegent_home" / ".codex"
        auth_path = codex_dir / "auth.json"
        config_path = codex_dir / "config.toml"

        assert auth_path.exists() is True
        assert json.loads(auth_path.read_text(encoding="utf-8")) == {
            "OPENAI_API_KEY": "sk-test"
        }

        assert config_path.exists() is True
        config_text = config_path.read_text(encoding="utf-8")
        assert "\\n" not in config_text
        assert 'model_provider = "cch"' in config_text

    def test_build_command_includes_model(self):
        task_data = {
            "task_id": 1,
            "subtask_id": 1,
            "prompt": "hello",
            "user": {"name": "test", "user_name": "test"},
            "bot": [{"shell_type": "codex"}],
        }

        agent = CodexAgent(task_data)
        agent._model = "gpt-test"

        cmd = agent._build_command("/tmp/cwd")

        assert cmd[0:3] == ["codex", "exec", "--json"]
        assert "--dangerously-bypass-approvals-and-sandbox" in cmd
        assert "--skip-git-repo-check" in cmd
        assert cmd[-1] == "-"
        assert cmd[cmd.index("-C") + 1] == "/tmp/cwd"
        assert cmd[cmd.index("--model") + 1] == "gpt-test"

    def test_build_command_includes_resume_when_session_available(self):
        task_data = {
            "task_id": 1,
            "subtask_id": 1,
            "prompt": "hello",
            "resume_session_id": "thread_123",
            "retry_mode": "resume",
            "user": {"name": "test", "user_name": "test"},
            "bot": [{"shell_type": "codex"}],
        }

        agent = CodexAgent(task_data)
        cmd = agent._build_command("/tmp/cwd")

        resume_idx = cmd.index("resume")
        assert cmd[resume_idx + 1] == "thread_123"

    def test_build_command_ignores_resume_when_new_session_requested(self):
        task_data = {
            "task_id": 1,
            "subtask_id": 1,
            "prompt": "hello",
            "resume_session_id": "thread_123",
            "retry_mode": "new_session",
            "user": {"name": "test", "user_name": "test"},
            "bot": [{"shell_type": "codex"}],
        }

        agent = CodexAgent(task_data)
        cmd = agent._build_command("/tmp/cwd")

        assert "resume" not in cmd

    @pytest.mark.asyncio
    async def test_async_execute_streams_and_completes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(codex_agent_module.config, "WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.setattr(
            codex_agent_module.config, "CODEX_PERSIST_EVENT_STREAM", True
        )
        monkeypatch.setattr(
            codex_agent_module.config,
            "CODEX_EVENT_STREAM_FILENAME",
            "codex-events.jsonl",
        )
        monkeypatch.setattr(
            codex_agent_module.config, "CODEX_STDERR_FILENAME", "codex-stderr.log"
        )
        task_data = {
            "task_id": 123,
            "subtask_id": 1,
            "prompt": "hello",
            "git_domain": "github.com",
            "git_repo": "repo",
            "git_repo_id": "1",
            "branch_name": "main",
            "user": {"name": "test", "user_name": "test"},
            "bot": [
                {
                    "shell_type": "codex",
                    "cwd": str(tmp_path),
                    "agent_config": {
                        "env": {
                            "api_key": "sk-test",
                            "base_url": "https://example.com",
                            "CODEX_CONFIG_TOML": 'model_provider = "cch"\\n',
                        }
                    },
                }
            ],
        }
        agent = CodexAgent(task_data)
        agent.options["cwd"] = str(tmp_path)
        agent.state_manager = _FakeStateManager()

        thread_started = {
            "type": "thread.started",
            "thread": {"id": "thread_123"},
        }
        event = {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "hello"},
        }
        fake_proc = _FakeProcess(
            stdout_lines=[
                json.dumps(thread_started).encode("utf-8") + b"\n",
                json.dumps(event).encode("utf-8") + b"\n",
            ]
        )

        async def _fake_create_subprocess_exec(*args, **kwargs):
            assert kwargs.get("env") is not None
            assert kwargs["env"].get("OPENAI_API_KEY") == "sk-test"
            assert kwargs["env"].get("OPENAI_BASE_URL") == "https://example.com"
            assert kwargs["env"].get("HOME") == str(tmp_path / "123" / ".wegent_home")
            return fake_proc

        monkeypatch.setattr(
            "executor.agents.codex.codex_agent.asyncio.create_subprocess_exec",
            _fake_create_subprocess_exec,
        )

        status = await agent._async_execute()

        assert status == TaskStatus.COMPLETED
        events_path = tmp_path / "123" / "codex-events.jsonl"
        assert events_path.exists() is True
        assert json.dumps(event) in events_path.read_text(encoding="utf-8")
        assert any(
            p[0] == 100 and p[1] == TaskStatus.COMPLETED.value
            for p in agent.state_manager.progress_calls
        )
        assert any(
            p[3].get("resume_session_id") == "thread_123"
            for p in agent.state_manager.progress_calls
        )
        assert ("completed", "hello") in agent.state_manager.workbench_status_calls
        assert [s.title for s in agent.thinking_manager.get_thinking_steps()] == [
            "thinking.running",
            "thinking.execution_completed",
        ]
        assert fake_proc.stdin.closed is True
        assert b"hello" in fake_proc.stdin.buffer

    @pytest.mark.asyncio
    async def test_async_execute_nonzero_exit_reports_failed(
        self, tmp_path, monkeypatch
    ):
        task_data = {
            "task_id": 456,
            "subtask_id": 1,
            "prompt": "hello",
            "git_domain": "github.com",
            "git_repo": "repo",
            "git_repo_id": "1",
            "branch_name": "main",
            "user": {"name": "test", "user_name": "test"},
            "bot": [{"shell_type": "codex", "cwd": str(tmp_path)}],
        }
        agent = CodexAgent(task_data)
        agent.options["cwd"] = str(tmp_path)
        agent.state_manager = _FakeStateManager()

        fake_proc = _FakeProcess(
            stdout_lines=[],
            stderr_lines=[b"boom\n"],
            final_returncode=1,
        )

        async def _fake_create_subprocess_exec(*args, **kwargs):
            return fake_proc

        monkeypatch.setattr(
            "executor.agents.codex.codex_agent.asyncio.create_subprocess_exec",
            _fake_create_subprocess_exec,
        )

        status = await agent._async_execute()

        assert status == TaskStatus.FAILED
        assert any(
            p[1] == TaskStatus.FAILED.value for p in agent.state_manager.progress_calls
        )
        assert ("failed", None) in agent.state_manager.workbench_status_calls
        assert [s.title for s in agent.thinking_manager.get_thinking_steps()] == [
            "thinking.running",
            "thinking.execution_failed",
        ]

    def test_cancel_run_terminates_process(self, monkeypatch):
        task_data = {
            "task_id": 999,
            "subtask_id": 1,
            "prompt": "hello",
            "user": {"name": "test", "user_name": "test"},
            "bot": [{"shell_type": "codex"}],
        }
        agent = CodexAgent(task_data)

        fake_proc = _FakeProcess(stdout_lines=[])
        agent._process = fake_proc
        agent.task_state_manager.get_state = MagicMock(return_value=None)
        monkeypatch.setattr(
            "executor.agents.codex.codex_agent.config.GRACEFUL_SHUTDOWN_TIMEOUT",
            0,
        )

        assert agent.cancel_run() is True
        assert fake_proc.terminated or fake_proc.killed
