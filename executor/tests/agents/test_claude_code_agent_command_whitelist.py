# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import pytest
from executor.agents.claude_code.claude_code_agent import ClaudeCodeAgent


def test_pr_command_whitelist_rejects_non_allowlisted_command(mocker):
    agent = ClaudeCodeAgent(
        {
            "task_id": 1,
            "subtask_id": 1,
            "task_title": "t",
            "subtask_title": "st",
            "user": {"user_name": "testuser"},
            "bot": [{"api_key": "k", "model": "claude-3-5-sonnet-20241022"}],
        }
    )

    run = mocker.patch("executor.agents.claude_code.claude_code_agent.subprocess.run")
    with pytest.raises(ValueError, match="Command not allowed"):
        agent._run_pr_command(["rm", "-rf", "/"])

    run.assert_not_called()
