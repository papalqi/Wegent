# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from app.models.kind import Kind


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_list_custom_config_models_returns_sanitized_items(
    test_client, test_db, test_admin_token, test_user
):
    custom_model = Kind(
        user_id=test_user.id,
        kind="Model",
        name="custom-config-model",
        namespace="default",
        is_active=True,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Model",
            "metadata": {"name": "custom-config-model", "namespace": "default"},
            "spec": {
                "isCustomConfig": True,
                "modelConfig": {
                    "env": {
                        "model": "openai",
                        "base_url": "https://api.openai.com/v1",
                        "model_id": "gpt-4o",
                        "api_key": "sk-test-should-not-leak",
                    }
                },
            },
            "status": {"state": "Available"},
        },
    )
    normal_model = Kind(
        user_id=test_user.id,
        kind="Model",
        name="normal-model",
        namespace="default",
        is_active=True,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Model",
            "metadata": {"name": "normal-model", "namespace": "default"},
            "spec": {
                "isCustomConfig": False,
                "modelConfig": {"env": {"model": "openai", "model_id": "gpt-4o"}},
            },
            "status": {"state": "Available"},
        },
    )
    test_db.add(custom_model)
    test_db.add(normal_model)
    test_db.commit()

    resp = test_client.get(
        "/api/admin/custom-config-models",
        headers=_auth_headers(test_admin_token),
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["name"] == "custom-config-model"
    assert item["user_name"] == test_user.user_name
    assert item["api_key_status"] == "SET"
    assert "api_key" not in item


def test_admin_delete_custom_config_model_requires_force_when_referenced(
    test_client, test_db, test_admin_token, test_user
):
    custom_model = Kind(
        user_id=test_user.id,
        kind="Model",
        name="custom-config-model-to-delete",
        namespace="default",
        is_active=True,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Model",
            "metadata": {
                "name": "custom-config-model-to-delete",
                "namespace": "default",
            },
            "spec": {"isCustomConfig": True, "modelConfig": {"env": {}}},
            "status": {"state": "Available"},
        },
    )
    test_db.add(custom_model)
    test_db.commit()
    test_db.refresh(custom_model)

    bot = Kind(
        user_id=test_user.id,
        kind="Bot",
        name="ref-bot",
        namespace="default",
        is_active=True,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Bot",
            "metadata": {"name": "ref-bot", "namespace": "default"},
            "spec": {
                "modelRef": {
                    "name": "custom-config-model-to-delete",
                    "namespace": "default",
                }
            },
            "status": {"state": "Available"},
        },
    )
    test_db.add(bot)
    test_db.commit()

    resp = test_client.delete(
        f"/api/admin/custom-config-models/{custom_model.id}",
        headers=_auth_headers(test_admin_token),
    )
    assert resp.status_code == 409

    resp = test_client.delete(
        f"/api/admin/custom-config-models/{custom_model.id}?force=true",
        headers=_auth_headers(test_admin_token),
    )
    assert resp.status_code == 204
