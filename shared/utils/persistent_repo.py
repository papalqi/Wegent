# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

WEGENT_PERSIST_REPO_DIRNAME = "wegent_repos"
PERSIST_REPO_MOUNT_PATH = "/wegent_repos"


def _resolve(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def normalize_persist_repo_dir(repo_dir: str) -> str:
    """
    Normalize a user-provided repo_dir and ensure it stays under the persistent
    repo mount directory.

    - Relative paths are treated as relative to PERSIST_REPO_MOUNT_PATH.
    - The returned path is an absolute, resolved path.
    - The mount root itself (i.e. "/wegent_repos") is not allowed.

    Raises:
        ValueError: If the resolved path escapes PERSIST_REPO_MOUNT_PATH.
    """
    repo_dir = (repo_dir or "").strip()
    if not repo_dir:
        return ""

    if not repo_dir.startswith("/"):
        repo_dir = f"{PERSIST_REPO_MOUNT_PATH}/{repo_dir.lstrip('/')}"

    resolved_repo_dir = _resolve(Path(repo_dir))
    resolved_mount_path = _resolve(Path(PERSIST_REPO_MOUNT_PATH))

    if resolved_repo_dir == resolved_mount_path:
        raise ValueError("repo_dir must be a subdirectory under persistent mount")

    try:
        resolved_repo_dir.relative_to(resolved_mount_path)
    except ValueError as e:
        raise ValueError("repo_dir must stay under persistent mount") from e

    return str(resolved_repo_dir)


def detect_is_p4_repo(repo_dir: Path) -> bool:
    repo_dir = _resolve(repo_dir)
    if not repo_dir.exists():
        return False

    markers = [repo_dir / ".p4config", repo_dir / ".p4ignore"]
    return any(p.exists() for p in markers)


def detect_repo_vcs(repo_dir: Path) -> Tuple[Optional[str], bool]:
    """
    Lightweight VCS detection based on filesystem markers.
    Returns (repo_vcs, is_p4).
    """
    repo_dir = _resolve(repo_dir)
    if detect_is_p4_repo(repo_dir):
        return "p4", True

    if (repo_dir / ".git").exists():
        return "git", False

    return None, False
