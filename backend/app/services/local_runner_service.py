# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.local_runner import LocalRunner

logger = logging.getLogger(__name__)


def _sanitize_runner_payload(value: Any) -> Any:
    """
    Remove fields that may accidentally leak local filesystem paths.
    Runner is expected to NOT send paths at all, but we defensively strip common keys.
    """

    if isinstance(value, list):
        return [_sanitize_runner_payload(item) for item in value]
    if not isinstance(value, dict):
        return value
    sanitized: Dict[str, Any] = {}
    for key, item in value.items():
        if key.lower() in {"path", "cwd", "workdir", "workspace_path"}:
            continue
        sanitized[key] = _sanitize_runner_payload(item)
    return sanitized


class LocalRunnerService:
    def upsert_heartbeat(
        self,
        db: Session,
        *,
        user_id: int,
        runner_id: str,
        name: Optional[str],
        capabilities: Dict[str, Any],
        workspaces: List[Dict[str, Any]],
    ) -> LocalRunner:
        runner = (
            db.query(LocalRunner)
            .filter(LocalRunner.id == runner_id, LocalRunner.user_id == user_id)
            .first()
        )
        safe_capabilities = _sanitize_runner_payload(capabilities) or {}
        safe_workspaces = _sanitize_runner_payload(workspaces) or []

        if runner is None:
            runner = LocalRunner(
                id=runner_id,
                user_id=user_id,
                name=name or runner_id,
                disabled=False,
                capabilities=safe_capabilities,
                workspaces=safe_workspaces,
                last_seen_at=datetime.utcnow(),
            )
            db.add(runner)
            db.commit()
            db.refresh(runner)
            logger.info("Registered local runner %s for user %s", runner_id, user_id)
            return runner

        if runner.disabled:
            return runner

        if name:
            runner.name = name
        runner.capabilities = safe_capabilities
        runner.workspaces = safe_workspaces
        runner.last_seen_at = datetime.utcnow()
        db.add(runner)
        db.commit()
        db.refresh(runner)
        return runner

    def list_for_user(self, db: Session, *, user_id: int) -> List[LocalRunner]:
        return (
            db.query(LocalRunner)
            .filter(LocalRunner.user_id == user_id)
            .order_by(LocalRunner.last_seen_at.desc())
            .all()
        )

    def get_for_user(
        self, db: Session, *, user_id: int, runner_id: str
    ) -> Optional[LocalRunner]:
        return (
            db.query(LocalRunner)
            .filter(LocalRunner.user_id == user_id, LocalRunner.id == runner_id)
            .first()
        )


local_runner_service = LocalRunnerService()
