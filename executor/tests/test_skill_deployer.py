#!/usr/bin/env python

# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-

from __future__ import annotations

import io
import sys
import zipfile
from typing import Any, Dict, Optional

import pytest
from executor.utils.skill_deployer import deploy_skills_from_backend


class _MockResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: Optional[Any] = None,
        content: bytes = b"",
    ):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content

    def json(self) -> Any:
        return self._json_data


def _make_zip_bytes(files: Dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_deploy_skills_without_auth_token_returns_zero(tmp_path) -> None:
    target = tmp_path / "skills"
    count = deploy_skills_from_backend(
        task_data={},
        skills=["shell_smoke"],
        skills_dir=str(target),
    )
    assert count == 0


def test_deploy_skills_downloads_and_extracts_public_skill(
    monkeypatch, tmp_path
) -> None:
    api_base = "http://fake-api"
    monkeypatch.setenv("TASK_API_DOMAIN", api_base)

    zip_bytes = _make_zip_bytes({"shell_smoke/hello.txt": b"ok"})

    def _mock_get(url: str, headers=None, timeout: int = 30):  # noqa: ANN001
        if "skills/unified" in url:
            return _MockResponse(
                status_code=200,
                json_data=[{"name": "shell_smoke", "id": 123, "is_public": True}],
            )
        if "/skills/public/123/download" in url:
            return _MockResponse(status_code=200, content=zip_bytes)
        return _MockResponse(status_code=404, json_data={})

    class _MockRequests:
        get = staticmethod(_mock_get)

    monkeypatch.setitem(sys.modules, "requests", _MockRequests)

    target_dir = tmp_path / "deployed"
    count = deploy_skills_from_backend(
        task_data={"auth_token": "token"},
        skills=["shell_smoke"],
        skills_dir=str(target_dir),
    )
    assert count == 1
    assert (target_dir / "shell_smoke" / "hello.txt").read_text(
        encoding="utf-8"
    ) == "ok"


def test_deploy_skills_rejects_zip_slip(monkeypatch, tmp_path) -> None:
    api_base = "http://fake-api"
    monkeypatch.setenv("TASK_API_DOMAIN", api_base)

    zip_bytes = _make_zip_bytes({"../evil.txt": b"pwnd"})

    def _mock_get(url: str, headers=None, timeout: int = 30):  # noqa: ANN001
        if "skills/unified" in url:
            return _MockResponse(
                status_code=200,
                json_data=[{"name": "shell_smoke", "id": 123, "is_public": True}],
            )
        if "/skills/public/123/download" in url:
            return _MockResponse(status_code=200, content=zip_bytes)
        return _MockResponse(status_code=404, json_data={})

    class _MockRequests:
        get = staticmethod(_mock_get)

    monkeypatch.setitem(sys.modules, "requests", _MockRequests)

    target_dir = tmp_path / "deployed"
    count = deploy_skills_from_backend(
        task_data={"auth_token": "token"},
        skills=["shell_smoke"],
        skills_dir=str(target_dir),
    )
    assert count == 0
    assert not (target_dir / "evil.txt").exists()
