# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from app.core.config import settings
from app.models.kind import Kind


def _make_public_shell(*, name: str, shell_type: str) -> Kind:
    return Kind(
        user_id=0,
        kind="Shell",
        name=name,
        namespace="default",
        is_active=True,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Shell",
            "metadata": {
                "name": name,
                "namespace": "default",
                "displayName": name,
                "labels": {"type": "local_engine"},
            },
            "spec": {
                "shellType": shell_type,
                "supportModel": ["openai"] if shell_type == "Codex" else ["anthropic"],
                "baseImage": "ghcr.io/wecode-ai/wegent-executor:local",
            },
            "status": {"state": "Available"},
        },
    )


@pytest.mark.unit
def test_codex_shell_hidden_when_disabled(
    test_client, test_db, test_token, monkeypatch
):
    test_db.add(_make_public_shell(name="ClaudeCode", shell_type="ClaudeCode"))
    test_db.add(_make_public_shell(name="Codex", shell_type="Codex"))
    test_db.commit()

    monkeypatch.setattr(settings, "CODEX_SHELL_ENABLED", False)

    resp = test_client.get(
        "/api/shells/unified", headers={"Authorization": f"Bearer {test_token}"}
    )
    assert resp.status_code == 200

    data = resp.json()["data"]
    shell_types = {item["shellType"] for item in data}
    assert "Codex" not in shell_types
    assert "ClaudeCode" in shell_types


@pytest.mark.unit
def test_create_shell_based_on_codex_forbidden_when_disabled(
    test_client, test_db, test_token, monkeypatch
):
    test_db.add(_make_public_shell(name="Codex", shell_type="Codex"))
    test_db.commit()

    monkeypatch.setattr(settings, "CODEX_SHELL_ENABLED", False)

    resp = test_client.post(
        "/api/shells",
        headers={"Authorization": f"Bearer {test_token}"},
        json={
            "name": "my-codex-shell",
            "displayName": "My Codex Shell",
            "baseShellRef": "Codex",
            "baseImage": "ghcr.io/wecode-ai/custom:latest",
        },
    )
    assert resp.status_code == 400
    assert "Codex shell is disabled" in resp.json()["detail"]
