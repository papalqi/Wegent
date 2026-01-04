# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelBase(BaseModel):
    """Model base schema"""

    name: str
    config: dict[str, Any]
    is_active: bool = True


class ModelCreate(ModelBase):
    """Model creation schema"""

    pass


class ModelUpdate(BaseModel):
    """Model update schema"""

    name: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class ModelInDB(ModelBase):
    """Database model schema"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelDetail(BaseModel):
    """Detailed model schema"""

    id: int
    name: str
    config: dict[str, Any]
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    """Model paginated response schema"""

    total: int
    items: list[ModelInDB]


# ===== Bulk create schemas =====

from typing import Any, List, Optional

from pydantic import BaseModel


class ModelBulkCreateItem(BaseModel):
    """
    Bulk create item schema.
    Accepts 'env' to match request body, we will wrap it into {'env': ...} as Model.config.
    """

    name: str
    env: dict[str, Any]
    is_active: bool = True


class ModelBulkCreateResponse(BaseModel):
    """
    Bulk create response schema.
    """

    created: List["ModelInDB"]
    skipped: List[dict]


class ProviderModelsRequest(BaseModel):
    provider_type: str
    base_url: Optional[str] = None
    api_key: str
    custom_headers: Optional[dict[str, str]] = None


class ProviderModelsResponse(BaseModel):
    success: bool
    message: str
    base_url_resolved: Optional[str] = None
    model_ids: list[str] = Field(default_factory=list)


class ProviderProbeRequest(BaseModel):
    provider_type: str
    base_url: Optional[str] = None
    api_key: str
    model_id: Optional[str] = None
    custom_headers: Optional[dict[str, str]] = None
    probe_targets: Optional[list[str]] = None


class ProviderProbeCheck(BaseModel):
    ok: bool
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class ProviderProbeResponse(BaseModel):
    success: bool
    message: str
    base_url_resolved: Optional[str] = None
    checks: dict[str, ProviderProbeCheck] = Field(default_factory=dict)
