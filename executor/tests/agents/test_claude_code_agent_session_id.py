# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from executor.agents.claude_code.claude_code_agent import ClaudeCodeAgent


def test_claude_code_agent_uses_payload_session_id() -> None:
    agent = ClaudeCodeAgent(
        {
            "task_id": 123,
            "subtask_id": 1,
            "session_id": "sess_abc",
            "prompt": "hello",
            "bot": [{}],
        }
    )
    assert agent.session_id == "sess_abc"


def test_claude_code_agent_session_id_falls_back_to_task_id() -> None:
    agent = ClaudeCodeAgent(
        {"task_id": 123, "subtask_id": 1, "prompt": "hello", "bot": [{}]}
    )
    assert agent.session_id == "123"
