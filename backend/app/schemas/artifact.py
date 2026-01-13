# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ArtifactResponse(BaseModel):
    id: int
    filename: str
    file_size: int = 0
    mime_type: str = ""
    download_url: Optional[str] = Field(
        None, description="Optional direct URL (S3/MinIO); may be null for MySQL"
    )
    created_at: datetime
