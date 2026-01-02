# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.pr_actions import (
    CreatePullRequestAction,
    PullRequestActionResult,
    UpdatePullRequestAction,
)
from app.services.pr_action_gateway import (
    create_pull_request_action,
    update_pull_request_action,
)

router = APIRouter()


@router.post("/actions/create-pr", response_model=PullRequestActionResult)
def create_pr_action(
    payload: CreatePullRequestAction,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PullRequestActionResult:
    return create_pull_request_action(
        db,
        current_user=current_user,
        idempotency_key=idempotency_key,
        action=payload,
    )


@router.post("/actions/update-pr", response_model=PullRequestActionResult)
def update_pr_action(
    payload: UpdatePullRequestAction,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PullRequestActionResult:
    return update_pull_request_action(
        db,
        current_user=current_user,
        idempotency_key=idempotency_key,
        action=payload,
    )
