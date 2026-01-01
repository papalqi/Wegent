#!/usr/bin/env python

# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi.testclient import TestClient
from routers import routers


def test_validate_image_accepts_codex(monkeypatch) -> None:
    calls = []

    def _capture(tasks):  # noqa: ANN001
        calls.append(tasks)

    monkeypatch.setattr(routers.task_processor, "process_tasks", _capture)

    client = TestClient(routers.app)
    resp = client.post(
        "/executor-manager/images/validate",
        json={"image": "ghcr.io/example/image:latest", "shell_type": "Codex"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "submitted"
    assert "validation_task_id" in body

    assert calls, "process_tasks should be invoked for supported shells"
    validation_task = calls[0][0]
    assert validation_task["validation_params"]["shell_type"] == "Codex"


def test_validate_image_unknown_shell_returns_error(monkeypatch) -> None:
    monkeypatch.setattr(routers.task_processor, "process_tasks", lambda _: None)

    client = TestClient(routers.app)
    resp = client.post(
        "/executor-manager/images/validate",
        json={"image": "ghcr.io/example/image:latest", "shell_type": "Unknown"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert body["valid"] is False
    assert "Unknown shell type" in body["message"]
