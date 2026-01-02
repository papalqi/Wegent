# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Set

from app.core.config import settings


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    code: str
    message: str


def _parse_allowlist_csv(value: str) -> Set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def evaluate_create_pr_policy(
    *,
    repo_full_name: str,
    base_branch: str,
) -> PolicyDecision:
    if not settings.PR_ACTION_WRITE_ENABLED:
        return PolicyDecision(
            allowed=False,
            code="PR_WRITE_DISABLED",
            message="PR write operations are disabled by default",
        )

    repo_allowlist = _parse_allowlist_csv(settings.PR_ACTION_REPO_ALLOWLIST)
    if repo_allowlist and repo_full_name not in repo_allowlist:
        return PolicyDecision(
            allowed=False,
            code="REPO_NOT_ALLOWED",
            message="Target repository is not in allowlist",
        )

    base_allowlist = _parse_allowlist_csv(settings.PR_ACTION_BASE_BRANCH_ALLOWLIST)
    if base_allowlist and base_branch not in base_allowlist:
        return PolicyDecision(
            allowed=False,
            code="BASE_NOT_ALLOWED",
            message="Target base branch is not in allowlist",
        )

    return PolicyDecision(allowed=True, code="ALLOWED", message="Allowed by policy")
