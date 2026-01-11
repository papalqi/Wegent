# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from app.core.config import settings
from app.services.pr_policy import evaluate_create_pr_policy


def _base_kwargs() -> dict:
    return {
        "repo_full_name": "octo/repo",
        "base_branch": "main",
        "head_branch": "wegent-123",
    }


def test_policy_denies_repo_not_allowed(mocker):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/allowed")
    mocker.patch.object(settings, "PR_ACTION_BASE_BRANCH_ALLOWLIST", "")
    mocker.patch.object(settings, "PR_POLICY_HEAD_BRANCH_REGEX", "")

    decision = evaluate_create_pr_policy(**_base_kwargs())
    assert decision.allowed is False
    assert decision.code == "REPO_NOT_ALLOWED"


def test_policy_denies_base_not_allowed(mocker):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")
    mocker.patch.object(settings, "PR_ACTION_BASE_BRANCH_ALLOWLIST", "release/*")
    mocker.patch.object(settings, "PR_POLICY_HEAD_BRANCH_REGEX", "")

    decision = evaluate_create_pr_policy(**_base_kwargs())
    assert decision.allowed is False
    assert decision.code == "BASE_NOT_ALLOWED"


def test_policy_denies_head_branch_invalid(mocker):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")
    mocker.patch.object(settings, "PR_ACTION_BASE_BRANCH_ALLOWLIST", "main")
    mocker.patch.object(settings, "PR_POLICY_HEAD_BRANCH_REGEX", r"^wegent-[0-9]+$")

    decision = evaluate_create_pr_policy(
        repo_full_name="octo/repo",
        base_branch="main",
        head_branch="wegent-abc",
    )
    assert decision.allowed is False
    assert decision.code == "HEAD_BRANCH_INVALID"


def test_policy_denies_diff_too_large(mocker):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")
    mocker.patch.object(settings, "PR_ACTION_BASE_BRANCH_ALLOWLIST", "main")
    mocker.patch.object(settings, "PR_POLICY_HEAD_BRANCH_REGEX", "")
    mocker.patch.object(settings, "PR_POLICY_MAX_CHANGED_FILES", 3)
    mocker.patch.object(settings, "PR_POLICY_MAX_DIFF_LINES", 0)

    decision = evaluate_create_pr_policy(
        files_changed=10, additions=1, deletions=1, **_base_kwargs()
    )
    assert decision.allowed is False
    assert decision.code == "DIFF_TOO_LARGE"


def test_policy_denies_forbidden_path_touched(mocker):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")
    mocker.patch.object(settings, "PR_ACTION_BASE_BRANCH_ALLOWLIST", "main")
    mocker.patch.object(settings, "PR_POLICY_HEAD_BRANCH_REGEX", "")
    mocker.patch.object(
        settings, "PR_POLICY_FORBIDDEN_PATH_PATTERNS", ".env,**/*.pem,secrets/**"
    )

    decision = evaluate_create_pr_policy(
        changed_files=["src/app.py", ".env", "README.md"],
        **_base_kwargs(),
    )
    assert decision.allowed is False
    assert decision.code == "FORBIDDEN_PATH_TOUCHED"


def test_policy_denies_required_checks_failed(mocker):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")
    mocker.patch.object(settings, "PR_ACTION_BASE_BRANCH_ALLOWLIST", "main")
    mocker.patch.object(settings, "PR_POLICY_HEAD_BRANCH_REGEX", "")
    mocker.patch.object(settings, "PR_POLICY_REQUIRED_CHECKS", "ci/unit,ci/lint")

    decision = evaluate_create_pr_policy(
        passed_checks=["ci/unit"],
        **_base_kwargs(),
    )
    assert decision.allowed is False
    assert decision.code == "REQUIRED_CHECKS_FAILED"


def test_policy_allows_when_all_rules_pass(mocker):
    mocker.patch.object(settings, "PR_ACTION_WRITE_ENABLED", True)
    mocker.patch.object(settings, "PR_ACTION_REPO_ALLOWLIST", "octo/repo")
    mocker.patch.object(settings, "PR_ACTION_BASE_BRANCH_ALLOWLIST", "main,release/*")
    mocker.patch.object(settings, "PR_POLICY_HEAD_BRANCH_REGEX", r"^wegent-[0-9]+$")
    mocker.patch.object(settings, "PR_POLICY_MAX_CHANGED_FILES", 10)
    mocker.patch.object(settings, "PR_POLICY_MAX_DIFF_LINES", 20)
    mocker.patch.object(
        settings, "PR_POLICY_FORBIDDEN_PATH_PATTERNS", ".env,**/*.pem,secrets/**"
    )
    mocker.patch.object(settings, "PR_POLICY_REQUIRED_CHECKS", "ci/unit,ci/lint")

    decision = evaluate_create_pr_policy(
        changed_files=["src/app.py", "README.md"],
        files_changed=2,
        additions=5,
        deletions=5,
        passed_checks=["ci/unit", "ci/lint"],
        repo_full_name="octo/repo",
        base_branch="main",
        head_branch="wegent-123",
    )
    assert decision.allowed is True
    assert decision.code == "ALLOWED"
