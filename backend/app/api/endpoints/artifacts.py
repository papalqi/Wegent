# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core import security
from app.models.subtask import Subtask
from app.models.subtask_context import ContextType, SubtaskContext
from app.services.chat.access.permissions import can_access_task_sync
from app.services.context import context_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{context_id}/download")
async def download_artifact(
    context_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user),
):
    context = db.query(SubtaskContext).filter(SubtaskContext.id == context_id).first()
    if not context or context.context_type != ContextType.ARTIFACT.value:
        raise HTTPException(status_code=404, detail="Artifact not found")

    subtask = db.query(Subtask).filter(Subtask.id == context.subtask_id).first()
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")

    if not can_access_task_sync(db, current_user.id, subtask.task_id):
        raise HTTPException(status_code=403, detail="Access denied")

    binary_data = context_service.get_file_binary_data(db, context)
    if binary_data is None:
        raise HTTPException(status_code=404, detail="Artifact content not found")

    filename = context.original_filename or context.name or f"artifact-{context_id}"
    quoted = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quoted}",
        "Content-Type": context.mime_type or "application/octet-stream",
    }
    return Response(
        content=binary_data, media_type=headers["Content-Type"], headers=headers
    )
