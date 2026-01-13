# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LocalRunnerWorkspace(BaseModel):
    id: str = Field(..., description="Workspace ID (runner-local identifier)")
    name: str = Field(..., description="Workspace display name")
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class LocalRunnerHeartbeatRequest(BaseModel):
    runner_id: str = Field(..., description="Runner ID")
    name: Optional[str] = Field(None, description="Runner display name")
    version: Optional[str] = Field(None, description="Runner version string")
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    workspaces: List[LocalRunnerWorkspace] = Field(default_factory=list)


class LocalRunnerInDB(BaseModel):
    id: str
    name: str
    disabled: bool
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    workspaces: List[LocalRunnerWorkspace] = Field(default_factory=list)
    last_seen_at: datetime

    class Config:
        from_attributes = True


class LocalRunnerListResponse(BaseModel):
    items: List[LocalRunnerInDB]
