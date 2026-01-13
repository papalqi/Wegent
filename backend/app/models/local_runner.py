# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class LocalRunner(Base):
    __tablename__ = "local_runners"

    id = Column(String(64), primary_key=True, index=True, comment="Runner ID")
    user_id = Column(Integer, nullable=False, index=True, comment="Owner user ID")

    name = Column(String(255), nullable=False, default="", comment="Display name")
    disabled = Column(Boolean, nullable=False, default=False, comment="Disable flag")

    # Public metadata reported by the runner. Must NOT include local filesystem paths.
    capabilities = Column(JSON, nullable=False, default=dict, comment="Capabilities")
    workspaces = Column(JSON, nullable=False, default=list, comment="Workspace list")

    last_seen_at = Column(
        DateTime,
        nullable=False,
        default=func.now(),
        index=True,
        comment="Last heartbeat",
    )

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
