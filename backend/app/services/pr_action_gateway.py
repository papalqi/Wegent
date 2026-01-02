# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, status
from shared.utils.sensitive_data_masker import mask_string
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.pr_action_audit import PRActionAudit
from app.models.user import User
from app.repository.github_provider import GitHubProvider
from app.schemas.pr_actions import CreatePullRequestAction, PullRequestActionResult
from app.services.pr_policy import evaluate_create_pr_policy


def _mask_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return mask_string(value)
    if isinstance(value, list):
        return [_mask_json_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _mask_json_value(v) for k, v in value.items()}
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _get_existing_audit(
    db: Session, *, user_id: int, idempotency_key: str
) -> Optional[PRActionAudit]:
    return db.scalar(
        select(PRActionAudit).where(
            PRActionAudit.user_id == user_id,
            PRActionAudit.idempotency_key == idempotency_key,
        )
    )


def _create_audit_row(
    db: Session,
    *,
    user_id: int,
    idempotency_key: str,
    action: str,
    provider: str,
    git_domain: str,
    repo_full_name: str,
    base_branch: str,
    head_branch: str,
    request_payload: Dict[str, Any],
) -> Tuple[PRActionAudit, bool]:
    existing = _get_existing_audit(db, user_id=user_id, idempotency_key=idempotency_key)
    if existing:
        return existing, False

    masked_request_payload = _mask_json_value(request_payload)
    audit = PRActionAudit(
        user_id=user_id,
        idempotency_key=idempotency_key,
        action=action,
        provider=provider,
        git_domain=git_domain,
        repo_full_name=repo_full_name,
        base_branch=base_branch,
        head_branch=head_branch,
        decision="error",  # Will be updated to allowed/denied on completion
        request_json=_json_dumps(masked_request_payload),
    )
    db.add(audit)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = _get_existing_audit(
            db, user_id=user_id, idempotency_key=idempotency_key
        )
        if not existing:
            raise
        return existing, False

    return audit, True


def create_pull_request_action(
    db: Session,
    *,
    current_user: User,
    idempotency_key: str,
    action: CreatePullRequestAction,
) -> PullRequestActionResult:
    audit, created = _create_audit_row(
        db,
        user_id=current_user.id,
        idempotency_key=idempotency_key,
        action="create_pr",
        provider=action.provider,
        git_domain=action.git_domain,
        repo_full_name=action.repo_full_name,
        base_branch=action.base_branch,
        head_branch=action.head_branch,
        request_payload=action.model_dump(),
    )

    if not created:
        if audit.decision == "allowed" and audit.pr_number and audit.pr_url:
            return PullRequestActionResult(
                audit_id=audit.id,
                idempotency_key=audit.idempotency_key,
                provider=audit.provider,
                git_domain=audit.git_domain,
                repo_full_name=audit.repo_full_name,
                base_branch=audit.base_branch,
                head_branch=audit.head_branch,
                pr_number=audit.pr_number,
                pr_url=audit.pr_url,
            )

        if audit.decision == "denied":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": audit.policy_code or "POLICY_DENIED",
                    "message": audit.policy_message or "Denied by policy",
                    "audit_id": audit.id,
                },
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDEMPOTENCY_REPLAY_NOT_AVAILABLE",
                "message": "Previous attempt did not complete successfully",
                "audit_id": audit.id,
            },
        )

    decision = evaluate_create_pr_policy(
        repo_full_name=action.repo_full_name,
        base_branch=action.base_branch,
    )
    if not decision.allowed:
        audit.decision = "denied"
        audit.policy_code = decision.code
        audit.policy_message = decision.message
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": decision.code,
                "message": decision.message,
                "audit_id": audit.id,
            },
        )

    provider = GitHubProvider()
    try:
        pr = provider.create_pull_request(
            user=current_user,
            git_domain=action.git_domain,
            repo_full_name=action.repo_full_name,
            base_branch=action.base_branch,
            head_branch=action.head_branch,
            title=action.title,
            body=action.body,
        )
        pr_number = int(pr["number"])
        pr_url = str(pr["html_url"])
    except HTTPException as e:
        audit.decision = "error"
        audit.policy_code = "UPSTREAM_ERROR"
        audit.policy_message = mask_string(str(e.detail))
        db.commit()
        raise
    except Exception as e:
        audit.decision = "error"
        audit.policy_code = "INTERNAL_ERROR"
        audit.policy_message = mask_string(str(e))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Internal error",
                "audit_id": audit.id,
            },
        )

    audit.decision = "allowed"
    audit.policy_code = "ALLOWED"
    audit.policy_message = "Allowed by policy"
    audit.pr_number = pr_number
    audit.pr_url = pr_url
    audit.response_json = _json_dumps(_mask_json_value(pr))
    db.commit()

    return PullRequestActionResult(
        audit_id=audit.id,
        idempotency_key=audit.idempotency_key,
        provider=audit.provider,
        git_domain=audit.git_domain,
        repo_full_name=audit.repo_full_name,
        base_branch=audit.base_branch,
        head_branch=audit.head_branch,
        pr_number=pr_number,
        pr_url=pr_url,
    )
