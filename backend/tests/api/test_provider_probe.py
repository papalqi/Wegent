# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import AsyncMock

import httpx


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_provider_probe_success_openai(test_client, test_token, mocker):
    async def _request(method: str, url: str, headers=None, json=None):  # noqa: ANN001
        req = httpx.Request(method, url)
        if method == "GET" and url.endswith("/v1/models"):
            return httpx.Response(200, request=req, json={"data": [{"id": "gpt-4o"}]})
        if method == "POST" and url.endswith("/v1/chat/completions"):
            return httpx.Response(
                200,
                request=req,
                json={"choices": [{"message": {"content": "OK"}}]},
            )
        if method == "POST" and url.endswith("/v1/embeddings"):
            return httpx.Response(
                200,
                request=req,
                json={"data": [{"embedding": [0.1, 0.2, 0.3]}]},
            )
        return httpx.Response(404, request=req, json={})

    mocker.patch("httpx.AsyncClient.request", AsyncMock(side_effect=_request))

    resp = test_client.post(
        "/api/models/provider-probe",
        headers=_auth_headers(test_token),
        json={
            "provider_type": "openai",
            "base_url": "https://example.com",
            "api_key": "sk-test",
            "model_id": "gpt-4o",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["base_url_resolved"] == "https://example.com/v1"
    assert data["checks"]["list_models"]["ok"] is True
    assert data["checks"]["prompt_llm"]["ok"] is True
    assert data["checks"]["embedding"]["ok"] is True


def test_provider_probe_missing_model_id(test_client, test_token):
    resp = test_client.post(
        "/api/models/provider-probe",
        headers=_auth_headers(test_token),
        json={
            "provider_type": "openai",
            "base_url": "https://example.com",
            "api_key": "sk-test",
            "probe_targets": ["prompt_llm", "embedding"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["checks"]["prompt_llm"]["ok"] is False
    assert data["checks"]["prompt_llm"]["error"] == "model_id_required"
    assert data["checks"]["embedding"]["ok"] is False
    assert data["checks"]["embedding"]["error"] == "model_id_required"


def test_provider_probe_http_error(test_client, test_token, mocker):
    async def _request(method: str, url: str, headers=None, json=None):  # noqa: ANN001
        req = httpx.Request(method, url)
        if method == "GET" and url.endswith("/v1/models"):
            return httpx.Response(200, request=req, json={"data": []})
        if method == "POST" and url.endswith("/v1/chat/completions"):
            return httpx.Response(
                401, request=req, json={"error": {"message": "unauthorized"}}
            )
        if method == "POST" and url.endswith("/v1/embeddings"):
            return httpx.Response(
                200,
                request=req,
                json={"data": [{"embedding": [0.1]}]},
            )
        return httpx.Response(404, request=req, json={})

    mocker.patch("httpx.AsyncClient.request", AsyncMock(side_effect=_request))

    resp = test_client.post(
        "/api/models/provider-probe",
        headers=_auth_headers(test_token),
        json={
            "provider_type": "openai",
            "base_url": "https://example.com",
            "api_key": "sk-test",
            "model_id": "gpt-4o",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["checks"]["prompt_llm"]["ok"] is False
    assert data["checks"]["prompt_llm"]["error"] == "http_status:401"
