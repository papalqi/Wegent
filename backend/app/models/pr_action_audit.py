# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class PRActionAudit(Base):
    __tablename__ = "pr_action_audits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False)

    provider = Column(String(32), nullable=False, default="github")
    git_domain = Column(String(255), nullable=False, default="github.com")
    repo_full_name = Column(String(255), nullable=False)
    base_branch = Column(String(255), nullable=False)
    head_branch = Column(String(255), nullable=False)

    action = Column(String(64), nullable=False)  # e.g. create_pr
    decision = Column(String(16), nullable=False)  # allowed/denied/error

    policy_code = Column(String(64), nullable=True)
    policy_message = Column(String(1024), nullable=True)

    request_json = Column(Text, nullable=False, default="{}")
    response_json = Column(Text, nullable=True)

    pr_number = Column(Integer, nullable=True)
    pr_url = Column(String(1024), nullable=True)

    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_pr_action_idempotency"),
        {
            "sqlite_autoincrement": True,
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    @property
    def request_payload(self) -> Dict[str, Any]:
        try:
            return json.loads(self.request_json or "{}")
        except Exception:
            return {}

    @property
    def response_payload(self) -> Optional[Dict[str, Any]]:
        if not self.response_json:
            return None
        try:
            return json.loads(self.response_json)
        except Exception:
            return None
