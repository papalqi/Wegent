# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from shared.utils.persistent_repo import (
    PERSIST_REPO_MOUNT_PATH,
    detect_is_p4_repo,
    detect_repo_vcs,
    normalize_persist_repo_dir,
)


def test_detect_repo_vcs_p4(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".p4config").write_text("P4PORT=perforce:1666", encoding="utf-8")
    repo_vcs, is_p4 = detect_repo_vcs(repo)
    assert repo_vcs == "p4"
    assert is_p4 is True
    assert detect_is_p4_repo(repo) is True


def test_detect_repo_vcs_git(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    repo_vcs, is_p4 = detect_repo_vcs(repo)
    assert repo_vcs == "git"
    assert is_p4 is False


def test_persist_repo_mount_path_constant() -> None:
    assert PERSIST_REPO_MOUNT_PATH.startswith("/")


def test_normalize_persist_repo_dir_relative_under_mount() -> None:
    assert normalize_persist_repo_dir("my-repo") == f"{PERSIST_REPO_MOUNT_PATH}/my-repo"


def test_normalize_persist_repo_dir_rejects_path_traversal() -> None:
    for repo_dir in ("../etc", "../../root", "/wegent_repos/../etc"):
        try:
            normalize_persist_repo_dir(repo_dir)
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for repo_dir={repo_dir!r}")


def test_normalize_persist_repo_dir_rejects_mount_root() -> None:
    for repo_dir in (PERSIST_REPO_MOUNT_PATH, f"{PERSIST_REPO_MOUNT_PATH}/."):
        try:
            normalize_persist_repo_dir(repo_dir)
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for repo_dir={repo_dir!r}")
