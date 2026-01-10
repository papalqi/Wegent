# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from shared.utils.persistent_repo import (
    PERSIST_REPO_MOUNT_PATH,
    WEGENT_PERSIST_REPO_DIRNAME,
    compute_persistent_repo_root,
    detect_is_p4_repo,
    detect_repo_vcs,
    find_wegent_root,
    workspace_persistent_repo_dir,
)


def _make_fake_wegent_root(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("test", encoding="utf-8")
    (root / "backend").mkdir(parents=True, exist_ok=True)
    (root / "executor").mkdir(parents=True, exist_ok=True)
    (root / "executor_manager").mkdir(parents=True, exist_ok=True)
    (root / "shared").mkdir(parents=True, exist_ok=True)


def test_find_wegent_root(tmp_path: Path) -> None:
    wegent_root = tmp_path / "Wegent"
    _make_fake_wegent_root(wegent_root)

    start = wegent_root / "backend" / "app" / "services"
    start.mkdir(parents=True, exist_ok=True)

    assert find_wegent_root(start) == wegent_root.resolve()


def test_compute_persistent_repo_root_is_fixed_sibling(tmp_path: Path) -> None:
    wegent_root = tmp_path / "Wegent"
    _make_fake_wegent_root(wegent_root)

    persist_root = compute_persistent_repo_root(wegent_root)
    assert persist_root == wegent_root.resolve().parent / WEGENT_PERSIST_REPO_DIRNAME
    assert not str(persist_root).startswith(str(wegent_root.resolve()))


def test_workspace_persistent_repo_dir(tmp_path: Path) -> None:
    root = tmp_path / "wegent_repos"
    assert workspace_persistent_repo_dir(root, 123).name == "ws-123"

    with pytest.raises(ValueError):
        workspace_persistent_repo_dir(root, 0)


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
