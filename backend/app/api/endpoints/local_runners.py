# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core import security
from app.core.config import settings
from app.models.subtask import Subtask
from app.models.task import TaskResource
from app.schemas.artifact import ArtifactResponse
from app.schemas.local_runner import (
    LocalRunnerHeartbeatRequest,
    LocalRunnerInDB,
    LocalRunnerListResponse,
)
from app.schemas.subtask import SubtaskExecutorUpdate
from app.services.adapters.executor_kinds import executor_kinds_service
from app.services.context import context_service
from app.services.local_runner_service import local_runner_service

logger = logging.getLogger(__name__)

router = APIRouter()

ONLINE_TTL_SECONDS = 90


def _is_runner_online(last_seen_at: datetime) -> bool:
    return datetime.utcnow() - last_seen_at <= timedelta(seconds=ONLINE_TTL_SECONDS)


@router.post("/heartbeat", response_model=LocalRunnerInDB)
async def heartbeat(
    payload: LocalRunnerHeartbeatRequest,
    db: Session = Depends(get_db),
    auth_context: security.AuthContext = Depends(security.get_auth_context),
):
    user = auth_context.user
    runner = local_runner_service.upsert_heartbeat(
        db,
        user_id=user.id,
        runner_id=payload.runner_id,
        name=payload.name,
        capabilities={
            **payload.capabilities,
            **({"version": payload.version} if payload.version else {}),
        },
        workspaces=[ws.model_dump(mode="json") for ws in payload.workspaces],
    )
    if runner.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Runner is disabled",
        )
    # Inject transient online flag into capabilities (not persisted as a separate column)
    data = LocalRunnerInDB.model_validate(runner).model_dump()
    data["capabilities"] = dict(data.get("capabilities") or {})
    data["capabilities"]["online"] = _is_runner_online(runner.last_seen_at)
    return LocalRunnerInDB.model_validate(data)


@router.get("", response_model=LocalRunnerListResponse)
async def list_runners(
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    runners = local_runner_service.list_for_user(db, user_id=current_user.id)
    items = []
    for runner in runners:
        payload = LocalRunnerInDB.model_validate(runner).model_dump()
        payload["capabilities"] = dict(payload.get("capabilities") or {})
        payload["capabilities"]["online"] = _is_runner_online(runner.last_seen_at)
        items.append(LocalRunnerInDB.model_validate(payload))
    return LocalRunnerListResponse(items=items)


@router.post("/tasks/dispatch")
async def dispatch_local_tasks(
    runner_id: str = Query(..., description="Runner ID"),
    task_status: str = Query(
        default="PENDING", description="Subtask status to filter by"
    ),
    limit: int = Query(
        default=1, ge=1, description="Maximum number of subtasks to return"
    ),
    db: Session = Depends(get_db),
    auth_context: security.AuthContext = Depends(security.get_auth_context),
):
    user = auth_context.user
    runner = local_runner_service.get_for_user(db, user_id=user.id, runner_id=runner_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="Runner not found")
    if runner.disabled:
        raise HTTPException(status_code=403, detail="Runner is disabled")
    return await executor_kinds_service.dispatch_tasks(
        db=db,
        status=task_status,
        limit=limit,
        task_ids=None,
        type="local",
        runner_id=runner_id,
    )


@router.put("/tasks")
async def update_local_subtask(
    subtask_update: SubtaskExecutorUpdate,
    runner_id: str = Query(..., description="Runner ID"),
    db: Session = Depends(get_db),
    auth_context: security.AuthContext = Depends(security.get_auth_context),
):
    user = auth_context.user
    runner = local_runner_service.get_for_user(db, user_id=user.id, runner_id=runner_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="Runner not found")
    if runner.disabled:
        raise HTTPException(status_code=403, detail="Runner is disabled")

    subtask = db.query(Subtask).filter(Subtask.id == subtask_update.subtask_id).first()
    if subtask is None:
        raise HTTPException(status_code=404, detail="Subtask not found")

    task = (
        db.query(TaskResource)
        .filter(
            TaskResource.id == subtask.task_id,
            TaskResource.kind == "Task",
            TaskResource.is_active == True,
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    labels = (task.json or {}).get("metadata", {}).get("labels", {}) or {}
    task_type = labels.get("type") or "online"
    task_runner_id = labels.get("localRunnerId")
    if task_type != "local" or task_runner_id != runner_id:
        raise HTTPException(
            status_code=403, detail="Subtask not assigned to this runner"
        )

    # Populate executor fields for traceability if not provided.
    if not subtask_update.executor_name:
        subtask_update.executor_name = runner_id
    if not subtask_update.executor_namespace:
        subtask_update.executor_namespace = "local-runner"

    return await executor_kinds_service.update_subtask(
        db=db, subtask_update=subtask_update
    )


@router.post("/artifacts/upload", response_model=ArtifactResponse)
async def upload_artifact(
    runner_id: str = Query(..., description="Runner ID"),
    subtask_id: int = Form(
        ..., description="Assistant subtask ID to attach artifact to"
    ),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth_context: security.AuthContext = Depends(security.get_auth_context),
):
    user = auth_context.user
    runner = local_runner_service.get_for_user(db, user_id=user.id, runner_id=runner_id)
    if runner is None:
        raise HTTPException(status_code=404, detail="Runner not found")
    if runner.disabled:
        raise HTTPException(status_code=403, detail="Runner is disabled")

    subtask = db.query(Subtask).filter(Subtask.id == subtask_id).first()
    if subtask is None:
        raise HTTPException(status_code=404, detail="Subtask not found")

    task = (
        db.query(TaskResource)
        .filter(
            TaskResource.id == subtask.task_id,
            TaskResource.kind == "Task",
            TaskResource.is_active == True,
        )
        .first()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    labels = (task.json or {}).get("metadata", {}).get("labels", {}) or {}
    if labels.get("type") != "local" or labels.get("localRunnerId") != runner_id:
        raise HTTPException(
            status_code=403, detail="Subtask not assigned to this runner"
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    try:
        binary_data = await file.read()
    except Exception as e:
        logger.warning("Failed to read uploaded artifact: %s", e)
        raise HTTPException(status_code=400, detail="Failed to read artifact") from e

    try:
        context = context_service.upload_artifact(
            db=db,
            user_id=user.id,
            filename=file.filename,
            binary_data=binary_data,
            subtask_id=subtask_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    direct_url = context_service.get_file_url(db, context)
    download_url = f"{settings.API_PREFIX}/artifacts/{context.id}/download"

    return ArtifactResponse(
        id=context.id,
        filename=context.original_filename,
        file_size=context.file_size,
        mime_type=context.mime_type,
        download_url=direct_url or download_url,
        created_at=context.created_at,
    )
