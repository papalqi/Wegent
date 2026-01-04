# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import AsyncMock

import httpx


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_provider_models_success(test_client, test_token, mocker):
    async_get = AsyncMock(
        return_value=httpx.Response(
            200,
            request=httpx.Request("GET", "https://example.com/v1/models"),
            json={
                "data": [
                    {"id": "gpt-4o"},
                    {"id": "gpt-4o"},
                    {"id": "text-embedding-3-large"},
                ]
            },
        )
    )
    mocker.patch("httpx.AsyncClient.get", async_get)

    resp = test_client.post(
        "/api/models/provider-models",
        headers=_auth_headers(test_token),
        json={
            "provider_type": "openai",
            "base_url": "https://example.com",
            "api_key": "sk-test",
            "custom_headers": {"X-Test": "1"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["base_url_resolved"] == "https://example.com/v1"
    assert data["model_ids"] == ["gpt-4o", "text-embedding-3-large"]


def test_provider_models_invalid_base_url(test_client, test_token):
    resp = test_client.post(
        "/api/models/provider-models",
        headers=_auth_headers(test_token),
        json={
            "provider_type": "openai",
            "base_url": "example.com",
            "api_key": "sk-test",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "Invalid base_url" in data["message"]


def test_provider_models_unsupported_provider(test_client, test_token):
    resp = test_client.post(
        "/api/models/provider-models",
        headers=_auth_headers(test_token),
        json={
            "provider_type": "anthropic",
            "base_url": "https://api.anthropic.com",
            "api_key": "sk-test",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "Unsupported provider_type" in data["message"]


def test_provider_models_upstream_http_error(test_client, test_token, mocker):
    async_get = AsyncMock(
        return_value=httpx.Response(
            401,
            request=httpx.Request("GET", "https://example.com/v1/models"),
            json={"error": {"message": "unauthorized"}},
        )
    )
    mocker.patch("httpx.AsyncClient.get", async_get)

    resp = test_client.post(
        "/api/models/provider-models",
        headers=_auth_headers(test_token),
        json={
            "provider_type": "openai",
            "base_url": "https://example.com/v1",
            "api_key": "sk-test",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "HTTP 401" in data["message"]
