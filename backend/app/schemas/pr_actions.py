# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CreatePullRequestAction(BaseModel):
    provider: Literal["github"] = "github"
    git_domain: str = Field(default="github.com", description="Git provider domain")
    repo_full_name: str = Field(
        ..., description="Repository full name, e.g. 'owner/repo'"
    )
    base_branch: str = Field(..., description="Base branch, e.g. 'main'")
    head_branch: str = Field(..., description="Head branch, e.g. 'wegent-xxx'")
    title: str = Field(..., min_length=1, max_length=256)
    body: Optional[str] = Field(default=None, max_length=20000)


class UpdatePullRequestAction(BaseModel):
    provider: Literal["github"] = "github"
    git_domain: str = Field(default="github.com", description="Git provider domain")
    repo_full_name: str = Field(
        ..., description="Repository full name, e.g. 'owner/repo'"
    )
    pr_number: int = Field(..., ge=1)
    base_branch: str = Field(..., description="Base branch, e.g. 'main'")
    head_branch: str = Field(..., description="Head branch, e.g. 'wegent-xxx'")
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    body: Optional[str] = Field(default=None, max_length=20000)


class PullRequestActionResult(BaseModel):
    audit_id: int
    idempotency_key: str
    provider: str
    git_domain: str
    repo_full_name: str
    base_branch: str
    head_branch: str
    pr_number: int
    pr_url: str


class PRActionErrorDetail(BaseModel):
    code: str
    message: str
    audit_id: Optional[int] = None
