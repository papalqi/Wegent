# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import yaml


def test_default_resources_include_pr_operator_templates():
    content = (
        Path(__file__)
        .resolve()
        .parents[2]
        .joinpath("init_data/01-default-resources.yaml")
    )
    docs = [d for d in yaml.safe_load_all(content.read_text(encoding="utf-8")) if d]

    ghost = next(
        d
        for d in docs
        if d.get("kind") == "Ghost"
        and d.get("metadata", {}).get("name") == "pr-operator-ghost"
    )
    assert "仅在策略通过时写入" in ghost["spec"]["systemPrompt"]
    assert '"idempotency_key"' in ghost["spec"]["systemPrompt"]

    assert any(
        d.get("kind") == "Bot"
        and d.get("metadata", {}).get("name") == "pr-operator-bot"
        for d in docs
    )
    assert any(
        d.get("kind") == "Team" and d.get("metadata", {}).get("name") == "pr-operator"
        for d in docs
    )
