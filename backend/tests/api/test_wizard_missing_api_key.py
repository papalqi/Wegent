# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timedelta

from app.models.kind import Kind


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_wizard_generate_followup_missing_api_key_returns_400(
    test_client, test_db, test_user, test_token
):
    model = Kind(
        user_id=test_user.id,
        kind="Model",
        name="test-model-missing-key",
        namespace="default",
        is_active=True,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Model",
            "metadata": {"name": "test-model-missing-key", "namespace": "default"},
            "spec": {
                "modelConfig": {
                    "env": {
                        "model": "openai",
                        "base_url": "https://api.openai.com/v1",
                        "model_id": "gpt-4",
                        "api_key": "",
                    }
                }
            },
            "status": {"state": "Available"},
        },
    )
    test_db.add(model)
    test_db.commit()

    resp = test_client.post(
        "/api/wizard/generate-followup",
        headers=_auth_headers(test_token),
        json={"answers": {"purpose": "test"}, "round_number": 1},
    )

    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "API Key" in detail


def test_wizard_generate_followup_skips_custom_config_models(
    test_client, test_db, test_user, test_token
):
    now = datetime.utcnow()

    hidden_custom_model = Kind(
        user_id=test_user.id,
        kind="Model",
        name="hidden-custom-config",
        namespace="default",
        is_active=True,
        updated_at=now + timedelta(seconds=10),
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Model",
            "metadata": {"name": "hidden-custom-config", "namespace": "default"},
            "spec": {
                "isCustomConfig": True,
                # Intentionally incomplete; model_resolver will default to OpenAI gpt-4
                "modelConfig": {"env": {}},
            },
            "status": {"state": "Available"},
        },
    )

    visible_user_model = Kind(
        user_id=test_user.id,
        kind="Model",
        name="visible-user-model",
        namespace="default",
        is_active=True,
        updated_at=now,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Model",
            "metadata": {"name": "visible-user-model", "namespace": "default"},
            "spec": {
                "modelConfig": {
                    "env": {
                        "model": "openai",
                        "base_url": "https://api.openai.com/v1",
                        "model_id": "gpt-4o",
                        "api_key": "",
                    }
                }
            },
            "status": {"state": "Available"},
        },
    )

    test_db.add(hidden_custom_model)
    test_db.add(visible_user_model)
    test_db.commit()

    resp = test_client.post(
        "/api/wizard/generate-followup",
        headers=_auth_headers(test_token),
        json={"answers": {"purpose": "test"}, "round_number": 1},
    )

    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "model_id=gpt-4o" in detail
