#!/usr/bin/env python

# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi.testclient import TestClient
from routers import routers


def test_callback_handler_returns_200_on_success(monkeypatch) -> None:
    def _ok(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return True, {"ok": True}

    monkeypatch.setattr(routers.api_client, "update_task_status_by_fields", _ok)

    client = TestClient(routers.app)
    resp = client.post(
        "/executor-manager/callback",
        json={
            "task_id": 1,
            "subtask_id": 1,
            "progress": 100,
            "status": "COMPLETED",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"


def test_callback_handler_returns_502_when_backend_update_fails(monkeypatch) -> None:
    def _fail(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return False, {"error_msg": "backend unavailable"}

    monkeypatch.setattr(routers.api_client, "update_task_status_by_fields", _fail)

    client = TestClient(routers.app)
    resp = client.post(
        "/executor-manager/callback",
        json={
            "task_id": 1,
            "subtask_id": 1,
            "progress": 100,
            "status": "COMPLETED",
        },
    )

    assert resp.status_code == 502


def test_callback_handler_returns_502_when_validation_forward_fails(
    monkeypatch,
) -> None:
    async def _forward_fail(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return False

    monkeypatch.setattr(routers, "_forward_validation_callback", _forward_fail)

    client = TestClient(routers.app)
    resp = client.post(
        "/executor-manager/callback",
        json={
            "task_id": 123,
            "subtask_id": 1,
            "progress": 50,
            "status": "RUNNING",
            "task_type": "validation",
            "result": {"validation_id": "test-validation-id"},
        },
    )

    assert resp.status_code == 502
