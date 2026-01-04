# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from typing import Literal, Optional

from pydantic import BaseModel, Field


class PRPolicyContext(BaseModel):
    changed_files: Optional[list[str]] = None
    files_changed: Optional[int] = None
    additions: Optional[int] = None
    deletions: Optional[int] = None
    passed_checks: Optional[list[str]] = None


class PRCreateActionIntent(BaseModel):
    action: Literal["create_pr"] = "create_pr"
    idempotency_key: str = Field(..., description="Idempotency key for safe retries")
    provider: Literal["github"] = "github"
    git_domain: str = Field(default="github.com")

    repo_full_name: str = Field(..., description="owner/repo")
    base_branch: str
    head_branch: str

    title: str
    body: Optional[str] = None

    policy_context: Optional[PRPolicyContext] = None
