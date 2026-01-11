# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pr_action_audit import PRActionAudit
from app.models.user import User


def _auth_headers(token: str, idempotency_key: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key}


@pytest.fixture
def test_user_with_github_token(test_db: Session, test_user: User) -> User:
    test_user.git_info = [
        {"type": "github", "git_domain": "github.com", "git_token": "test_token"}
    ]
    test_db.add(test_user)
    test_db.commit()
    test_db.refresh(test_user)
    return test_user


def test_create_pr_denied_when_write_disabled(
    mocker,
    test_client: TestClient,
    test_db: Session,
    test_user_with_github_token: User,
    test_token: str,
):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", False)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")

    resp = test_client.post(
        "/api/pr/actions/create-pr",
        headers=_auth_headers(test_token, "idem-1"),
        json={
            "provider": "github",
            "git_domain": "github.com",
            "repo_full_name": "octo/repo",
            "base_branch": "main",
            "head_branch": "wegent-123",
            "title": "Test PR",
            "body": "Hello",
        },
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "PR_WRITE_DISABLED"
    assert detail["audit_id"] is not None

    audit = (
        test_db.query(PRActionAudit)
        .filter(PRActionAudit.id == detail["audit_id"])
        .one()
    )
    assert audit.decision == "denied"
    assert audit.policy_code == "PR_WRITE_DISABLED"


def test_create_pr_denied_when_repo_not_allowed(
    mocker,
    test_client: TestClient,
    test_db: Session,
    test_user_with_github_token: User,
    test_token: str,
):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/allowed")

    resp = test_client.post(
        "/api/pr/actions/create-pr",
        headers=_auth_headers(test_token, "idem-2"),
        json={
            "provider": "github",
            "git_domain": "github.com",
            "repo_full_name": "octo/blocked",
            "base_branch": "main",
            "head_branch": "wegent-123",
            "title": "Test PR",
            "body": "Hello",
        },
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "REPO_NOT_ALLOWED"
    assert detail["audit_id"] is not None

    audit = (
        test_db.query(PRActionAudit)
        .filter(PRActionAudit.id == detail["audit_id"])
        .one()
    )
    assert audit.decision == "denied"
    assert audit.policy_code == "REPO_NOT_ALLOWED"


def test_create_pr_idempotent_replay(
    mocker,
    test_client: TestClient,
    test_db: Session,
    test_user_with_github_token: User,
    test_token: str,
):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "number": 123,
        "html_url": "https://example/pr/123",
    }
    post = mocker.patch(
        "app.repository.github_provider.requests.post", return_value=mock_response
    )

    payload = {
        "provider": "github",
        "git_domain": "github.com",
        "repo_full_name": "octo/repo",
        "base_branch": "main",
        "head_branch": "wegent-123",
        "title": "Test PR",
        "body": "Hello",
    }

    resp1 = test_client.post(
        "/api/pr/actions/create-pr",
        headers=_auth_headers(test_token, "idem-3"),
        json=payload,
    )
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["pr_number"] == 123

    resp2 = test_client.post(
        "/api/pr/actions/create-pr",
        headers=_auth_headers(test_token, "idem-3"),
        json=payload,
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["pr_number"] == 123
    assert body1["audit_id"] == body2["audit_id"]

    assert post.call_count == 1

    audits = test_db.query(PRActionAudit).all()
    assert len(audits) == 1
    assert audits[0].decision == "allowed"


def test_create_pr_audit_masks_sensitive_fields(
    mocker,
    test_client: TestClient,
    test_db: Session,
    test_user_with_github_token: User,
    test_token: str,
):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "number": 123,
        "html_url": "https://example/pr/123",
    }
    mocker.patch(
        "app.repository.github_provider.requests.post", return_value=mock_response
    )

    token_like = "ghp_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    resp = test_client.post(
        "/api/pr/actions/create-pr",
        headers=_auth_headers(test_token, "idem-mask-1"),
        json={
            "provider": "github",
            "git_domain": "github.com",
            "repo_full_name": "octo/repo",
            "base_branch": "main",
            "head_branch": "wegent-123",
            "title": f"Title {token_like}",
            "body": f"Body {token_like}",
        },
    )
    assert resp.status_code == 200

    audit = test_db.query(PRActionAudit).one()
    assert token_like not in (audit.request_json or "")
    assert token_like not in (audit.response_json or "")


def test_update_pr_idempotent_replay(
    mocker,
    test_client: TestClient,
    test_db: Session,
    test_user_with_github_token: User,
    test_token: str,
):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "number": 123,
        "html_url": "https://example/pr/123",
    }
    patch = mocker.patch(
        "app.repository.github_provider.requests.patch", return_value=mock_response
    )

    payload = {
        "provider": "github",
        "git_domain": "github.com",
        "repo_full_name": "octo/repo",
        "pr_number": 123,
        "base_branch": "main",
        "head_branch": "wegent-123",
        "title": "Updated title",
        "body": "Updated body",
    }

    resp1 = test_client.post(
        "/api/pr/actions/update-pr",
        headers=_auth_headers(test_token, "idem-upd-1"),
        json=payload,
    )
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["pr_number"] == 123

    resp2 = test_client.post(
        "/api/pr/actions/update-pr",
        headers=_auth_headers(test_token, "idem-upd-1"),
        json=payload,
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body1["audit_id"] == body2["audit_id"]

    assert patch.call_count == 1

    audits = test_db.query(PRActionAudit).all()
    assert len(audits) == 1
    assert audits[0].decision == "allowed"
