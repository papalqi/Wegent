# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import fnmatch
import re
from dataclasses import dataclass
from typing import Set

from app.core.config import settings


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    code: str
    message: str
    violations: tuple["PolicyViolation", ...] = ()


@dataclass(frozen=True)
class PolicyViolation:
    code: str
    message: str


def _parse_allowlist_csv(value: str) -> Set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def _looks_like_glob(pattern: str) -> bool:
    return any(ch in pattern for ch in ("*", "?", "["))


def _match_any(value: str, patterns: Set[str]) -> bool:
    for pattern in patterns:
        if not pattern:
            continue
        if _looks_like_glob(pattern):
            if fnmatch.fnmatch(value, pattern):
                return True
            continue
        if value == pattern:
            return True
    return False


def _match_any_path(path: str, patterns: Set[str]) -> bool:
    for pattern in patterns:
        if not pattern:
            continue
        if _looks_like_glob(pattern):
            if fnmatch.fnmatch(path, pattern):
                return True
            continue
        prefix = pattern
        if prefix.endswith("/"):
            if path.startswith(prefix):
                return True
            continue
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


def evaluate_create_pr_policy(
    *,
    repo_full_name: str,
    base_branch: str,
    head_branch: str,
    changed_files: list[str] | None = None,
    files_changed: int | None = None,
    additions: int | None = None,
    deletions: int | None = None,
    required_checks: list[str] | None = None,
    passed_checks: list[str] | None = None,
) -> PolicyDecision:
    violations: list[PolicyViolation] = []

    if not settings.PR_ACTION_WRITE_ENABLED:
        violations.append(
            PolicyViolation(
                code="PR_WRITE_DISABLED",
                message="PR write operations are disabled by default",
            )
        )

    repo_allowlist = _parse_allowlist_csv(settings.PR_ACTION_REPO_ALLOWLIST)
    if repo_allowlist and repo_full_name not in repo_allowlist:
        violations.append(
            PolicyViolation(
                code="REPO_NOT_ALLOWED",
                message="Target repository is not in allowlist",
            )
        )

    base_allowlist = _parse_allowlist_csv(settings.PR_ACTION_BASE_BRANCH_ALLOWLIST)
    if base_allowlist and not _match_any(base_branch, base_allowlist):
        violations.append(
            PolicyViolation(
                code="BASE_NOT_ALLOWED",
                message="Target base branch is not in allowlist",
            )
        )

    if settings.PR_POLICY_HEAD_BRANCH_REGEX:
        try:
            if not re.match(settings.PR_POLICY_HEAD_BRANCH_REGEX, head_branch or ""):
                violations.append(
                    PolicyViolation(
                        code="HEAD_BRANCH_INVALID",
                        message="Head branch does not match naming rule",
                    )
                )
        except re.error:
            violations.append(
                PolicyViolation(
                    code="POLICY_CONFIG_INVALID",
                    message="Head branch regex is invalid",
                )
            )

    max_files = int(settings.PR_POLICY_MAX_CHANGED_FILES or 0)
    max_lines = int(settings.PR_POLICY_MAX_DIFF_LINES or 0)
    if max_files > 0 and files_changed is not None and files_changed > max_files:
        violations.append(
            PolicyViolation(
                code="DIFF_TOO_LARGE",
                message="Diff exceeds maximum changed files threshold",
            )
        )
    if max_lines > 0 and additions is not None and deletions is not None:
        if (additions + deletions) > max_lines:
            violations.append(
                PolicyViolation(
                    code="DIFF_TOO_LARGE",
                    message="Diff exceeds maximum changed lines threshold",
                )
            )

    forbidden_patterns = _parse_allowlist_csv(
        settings.PR_POLICY_FORBIDDEN_PATH_PATTERNS
    )
    if forbidden_patterns and changed_files:
        for path in changed_files:
            if _match_any_path(path, forbidden_patterns):
                violations.append(
                    PolicyViolation(
                        code="FORBIDDEN_PATH_TOUCHED",
                        message=f"Forbidden path touched: {path}",
                    )
                )
                break

    required_checks_cfg = required_checks
    if required_checks_cfg is None:
        required_checks_cfg = list(
            _parse_allowlist_csv(settings.PR_POLICY_REQUIRED_CHECKS)
        )
    if required_checks_cfg:
        passed = set(passed_checks or [])
        missing = [c for c in required_checks_cfg if c not in passed]
        if missing:
            violations.append(
                PolicyViolation(
                    code="REQUIRED_CHECKS_FAILED",
                    message=f"Missing required checks: {', '.join(missing)}",
                )
            )

    if violations:
        first = violations[0]
        return PolicyDecision(
            allowed=False,
            code=first.code,
            message=first.message,
            violations=tuple(violations),
        )

    return PolicyDecision(allowed=True, code="ALLOWED", message="Allowed by policy")
