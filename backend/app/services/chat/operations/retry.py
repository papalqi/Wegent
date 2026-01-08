# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Retry operation utilities for Chat Service.

This module provides utilities for retrying failed chat messages,
including context fetching and subtask reset.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Literal, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session, aliased, joinedload
from sqlalchemy.orm.attributes import flag_modified

from app.models.kind import Kind
from app.models.subtask import Subtask, SubtaskRole, SubtaskStatus
from app.models.task import TaskResource
from app.schemas.kind import Task

logger = logging.getLogger(__name__)


def fetch_retry_context(
    db: Session,
    task_id: int,
    subtask_id: int,
) -> Tuple[
    Optional[Subtask],
    Optional[TaskResource],
    Optional[Kind],
    Optional[Subtask],
]:
    """
    Fetch all required database entities for retry operation in a single optimized query.

    Args:
        db: Database session
        task_id: Task ID
        subtask_id: Subtask ID to retry

    Returns:
        Tuple of (failed_ai_subtask, task, team, user_subtask)
    """
    TaskKind = aliased(TaskResource)
    TeamKind = aliased(Kind)

    # Optimized query: fetch failed_ai_subtask, task, and team in one go
    query_result = (
        db.query(
            Subtask,  # failed_ai_subtask
            TaskKind,  # task
            TeamKind,  # team
        )
        .select_from(Subtask)  # Explicitly specify the main table
        .outerjoin(
            TaskKind,
            and_(
                TaskKind.id == task_id,
                TaskKind.kind == "Task",
                TaskKind.is_active,
            ),
        )
        .outerjoin(
            TeamKind,
            and_(
                TeamKind.id == Subtask.team_id,
                TeamKind.kind == "Team",
                TeamKind.is_active,
            ),
        )
        .filter(
            Subtask.id == subtask_id,
            Subtask.task_id == task_id,
            Subtask.role == SubtaskRole.ASSISTANT,
        )
        .first()
    )

    if not query_result:
        return None, None, None, None

    failed_ai_subtask, task, team = query_result

    # Fetch user subtask separately
    # Key insight: parent_id stores message_id (not subtask.id) throughout the system
    # Both in chat.py and task_kinds.py, parent_id is always set to message_id
    user_subtask = None
    if failed_ai_subtask and failed_ai_subtask.parent_id:
        # Use parent_id as message_id to find the triggering USER subtask
        # This works for both single chat and group chat
        user_subtask = (
            db.query(Subtask)
            .options(joinedload(Subtask.contexts))  # Preload contexts
            .filter(
                Subtask.task_id == failed_ai_subtask.task_id,
                Subtask.message_id == failed_ai_subtask.parent_id,
                Subtask.role == SubtaskRole.USER,
            )
            .first()
        )
        if user_subtask:
            logger.info(
                f"Found user_subtask via parent_id as message_id: "
                f"id={user_subtask.id}, message_id={user_subtask.message_id}, "
                f"prompt={user_subtask.prompt[:50] if user_subtask.prompt else ''}..."
            )
        else:
            logger.warning(
                f"Could not find USER subtask with message_id={failed_ai_subtask.parent_id}"
            )

    return failed_ai_subtask, task, team, user_subtask


def reset_subtask_for_retry(
    db: Session,
    subtask: Subtask,
    *,
    retry_mode: Literal["resume", "new_session"] = "resume",
    shell_type: Optional[str] = None,
) -> None:
    """
    Reset a failed subtask to PENDING status for retry.

    Args:
        db: Database session
        subtask: The subtask to reset
        retry_mode: Retry mode indicating whether to reuse session or start a new one
        shell_type: Optional shell type hint (e.g. "Codex", "ClaudeCode")

    Note:
        This function only mutates ORM objects in the current session. The caller
        should commit/rollback as part of its transaction boundary.
    """
    existing_result: dict[str, Any] = (
        subtask.result if isinstance(subtask.result, dict) else {}
    )
    resolved_shell_type = shell_type
    if not resolved_shell_type:
        existing_shell_type = existing_result.get("shell_type")
        if isinstance(existing_shell_type, str) and existing_shell_type:
            resolved_shell_type = existing_shell_type

    preserved_result: dict[str, Any] = {}
    if resolved_shell_type:
        preserved_result["shell_type"] = resolved_shell_type
    preserved_result["retry_mode"] = retry_mode

    if retry_mode == "resume":
        for key in ("resume_session_id", "session_id"):
            value = existing_result.get(key)
            if isinstance(value, str) and value:
                preserved_result[key] = value
    elif retry_mode == "new_session":
        if resolved_shell_type == "ClaudeCode":
            preserved_result["session_id"] = str(uuid.uuid4())

    subtask.status = SubtaskStatus.PENDING
    subtask.progress = 0
    subtask.error_message = ""
    subtask.result = preserved_result
    subtask.executor_name = None
    subtask.executor_namespace = None
    subtask.updated_at = datetime.now()

    logger.info(
        f"Reset subtask to PENDING: id={subtask.id}, message_id={subtask.message_id}"
    )


def reset_task_for_retry(db: Session, task: TaskResource) -> None:
    """
    Reset task status to PENDING so executor_manager can pick it up again.

    For non-direct chat (executor-based) tasks, executor_manager polls tasks where
    `task.status.status == 'PENDING'`. If a task remains FAILED/COMPLETED, retries
    will appear to "do nothing" because no dispatcher will fetch it.

    Note:
        This function only mutates ORM objects in the current session. The caller
        should commit/rollback as part of its transaction boundary.
    """
    now = datetime.now()
    task_crd = Task.model_validate(task.json)
    if task_crd.status:
        task_crd.status.status = "PENDING"
        task_crd.status.progress = 0
        task_crd.status.errorMessage = ""
        task_crd.status.result = None
        task_crd.status.updatedAt = now
        task_crd.status.completedAt = None

    task.json = task_crd.model_dump(mode="json")
    task.updated_at = now
    flag_modified(task, "json")


def extract_model_override_info(task: TaskResource) -> Tuple[Optional[str], bool]:
    """
    Extract model override information from task metadata.

    Reading Model Override Metadata:
    - Primary source: task.json.metadata.labels (set by on_chat_send when user overrides model)
    - Fallback source: task.json.spec (for compatibility with other shells)

    Args:
        task: The task containing metadata

    Returns:
        Tuple of (model_id, force_override)
    """
    task_spec_dict = task.json.get("spec", {})
    task_metadata = task.json.get("metadata", {})
    task_labels = task_metadata.get("labels", {})

    # Try to get model info from metadata.labels first (for direct chat)
    model_id = task_labels.get("modelId") or task_spec_dict.get("modelId")
    force_override = (
        task_labels.get("forceOverrideBotModel") == "true"
        or task_spec_dict.get("forceOverrideBotModel") == "true"
    )

    logger.info(
        f"Extracted model info: model_id={model_id}, force_override={force_override}"
    )

    return model_id, force_override
