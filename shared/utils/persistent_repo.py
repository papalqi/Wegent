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


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        return child.is_relative_to(parent)
    except AttributeError:
        child_parts = child.parts
        parent_parts = parent.parts
        return len(child_parts) >= len(parent_parts) and child_parts[: len(parent_parts)] == parent_parts


def find_wegent_root(start: Path, *, max_depth: int = 12) -> Path:
    """
    Find the Wegent repository root by walking upwards from start.
    The root is identified by containing AGENTS.md and core module folders.
    """
    current = _resolve(start)
    if current.is_file():
        current = current.parent

    for _ in range(max_depth + 1):
        if (
            (current / "AGENTS.md").is_file()
            and (current / "backend").is_dir()
            and (current / "executor").is_dir()
            and (current / "executor_manager").is_dir()
            and (current / "shared").is_dir()
        ):
            return current
        if current.parent == current:
            break
        current = current.parent
    raise ValueError(f"Unable to locate Wegent root from: {start}")


def compute_persistent_repo_root(wegent_root: Path) -> Path:
    """
    Compute the host persistent repo root as a fixed sibling directory:
    dirname(WEGENT_ROOT)/wegent_repos
    """
    wegent_root_real = _resolve(wegent_root)
    parent_real = _resolve(wegent_root_real.parent)
    persist_root = _resolve(parent_real / WEGENT_PERSIST_REPO_DIRNAME)

    expected = parent_real / WEGENT_PERSIST_REPO_DIRNAME
    if persist_root != expected:
        raise ValueError(
            f"Persistent repo root must be exactly {expected}, got {persist_root}"
        )

    if _is_relative_to(persist_root, wegent_root_real):
        raise ValueError(
            f"Persistent repo root must not be inside Wegent root: {persist_root}"
        )

    if persist_root.parent != parent_real:
        raise ValueError(
            f"Persistent repo root must be under {parent_real}, got {persist_root}"
        )

    return persist_root


def workspace_persistent_repo_dir(persist_root: Path, workspace_id: int) -> Path:
    if not isinstance(workspace_id, int) or workspace_id <= 0:
        raise ValueError(f"workspace_id must be a positive int, got {workspace_id!r}")
    return _resolve(persist_root) / f"ws-{workspace_id}"


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

