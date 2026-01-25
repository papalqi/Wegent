#!/usr/bin/env python

# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi.testclient import TestClient
from routers import routers


class _StubExecutor:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.status_requested: list[str] = []

    def delete_executor(self, executor_name: str) -> dict[str, str]:
        self.deleted.append(executor_name)
        return {"status": "success"}

    def get_executor_status(self, executor_name: str) -> dict[str, str]:
        self.status_requested.append(executor_name)
        return {"status": "running", "executor_name": executor_name}


def test_get_executor_status_uses_dispatcher(monkeypatch) -> None:
    stub = _StubExecutor()
    captured: dict[str, str] = {}

    def _get_executor(task_type: str) -> _StubExecutor:
        captured["task_type"] = task_type
        return stub

    monkeypatch.setattr(routers.ExecutorDispatcher, "get_executor", _get_executor)

    client = TestClient(routers.app)
    resp = client.get(
        "/executor-manager/executor/status",
        params={"executor_name": "wegent-task-test-123"},
    )

    assert resp.status_code == 200
    assert captured["task_type"] == routers.EXECUTOR_DISPATCHER_MODE
    assert resp.json() == {"status": "running", "executor_name": "wegent-task-test-123"}


def test_delete_executor_uses_dispatcher(monkeypatch) -> None:
    stub = _StubExecutor()
    captured: dict[str, str] = {}

    def _get_executor(task_type: str) -> _StubExecutor:
        captured["task_type"] = task_type
        return stub

    monkeypatch.setattr(routers.ExecutorDispatcher, "get_executor", _get_executor)

    client = TestClient(routers.app)
    resp = client.post(
        "/executor-manager/executor/delete",
        json={"executor_name": "wegent-task-test-456"},
    )

    assert resp.status_code == 200
    assert captured["task_type"] == routers.EXECUTOR_DISPATCHER_MODE
    assert stub.deleted == ["wegent-task-test-456"]
    assert resp.json() == {"status": "success"}
