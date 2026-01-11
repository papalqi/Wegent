# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Utility API endpoints.
"""

import os
from collections import deque
from pathlib import Path
from typing import Iterable, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from shared.utils.persistent_repo import PERSIST_REPO_MOUNT_PATH, detect_repo_vcs

from app.core import security
from app.models.user import User
from app.services.url_metadata import UrlMetadataResult, fetch_url_metadata

router = APIRouter()


@router.get("/url-metadata", response_model=UrlMetadataResult)
async def get_url_metadata(
    url: str = Query(..., description="The URL to fetch metadata from"),
) -> UrlMetadataResult:
    """
    Fetch metadata (title, description, favicon) from a web page URL.

    This endpoint is used by the frontend to render rich link cards for URLs
    shared in chat messages.

    - **url**: The full URL of the web page to fetch metadata from

    Returns:
        UrlMetadataResult containing:
        - url: The original URL
        - title: Page title (from og:title, twitter:title, or <title>)
        - description: Page description (from og:description, meta description)
        - favicon: URL to the site's favicon
        - success: Whether the fetch was successful
    """
    return await fetch_url_metadata(url)


class PersistentRepoDirItem(BaseModel):
    relative_path: str = Field(..., description="Path relative to persistent repo root")
    repo_dir: str = Field(
        ...,
        description=(
            "Working directory inside executor container. "
            "Always under /wegent_repos/."
        ),
    )
    repo_vcs: Optional[str] = Field(None, description="Detected VCS type: git/p4")
    is_p4: bool = Field(False, description="Whether it looks like a P4 workspace")


def _iter_child_dirs(parent: Path) -> Iterable[Path]:
    try:
        children = []
        for child in parent.iterdir():
            if not child.is_dir():
                continue
            if child.is_symlink():
                continue
            if child.name.startswith("."):
                continue
            children.append(child)
        return sorted(children, key=lambda p: p.name.lower())
    except OSError:
        return []


def _walk_dirs(
    root: Path, *, max_depth: int, scan_limit: int
) -> Iterable[tuple[str, Path]]:
    queue: deque[tuple[Path, str, int]] = deque([(root, "", 0)])
    scanned = 0

    while queue and scanned < scan_limit:
        current_dir, rel_prefix, depth = queue.popleft()
        if depth >= max_depth:
            continue

        for child in _iter_child_dirs(current_dir):
            rel = f"{rel_prefix}/{child.name}" if rel_prefix else child.name
            yield rel, child
            scanned += 1
            if scanned >= scan_limit:
                break
            queue.append((child, rel, depth + 1))


@router.get("/persistent-repo-dirs", response_model=list[PersistentRepoDirItem])
async def list_persistent_repo_dirs(
    q: str = Query("", description="Search query (case-insensitive substring match)"),
    limit: int = Query(200, ge=1, le=1000, description="Maximum number of results"),
    depth: int = Query(2, ge=1, le=5, description="Maximum directory depth to scan"),
    current_user: User = Depends(security.get_current_user),
) -> list[PersistentRepoDirItem]:
    """
    List directories under the host persistent repo root.

    The host root is provided via WEGENT_PERSIST_REPO_ROOT_HOST and is mounted into
    executor containers at /wegent_repos.
    """
    _ = current_user  # Keep auth dependency explicit even if unused.

    persist_root_host = (os.getenv("WEGENT_PERSIST_REPO_ROOT_HOST") or "").strip()
    if not persist_root_host:
        return []

    root = Path(persist_root_host).expanduser().resolve(strict=False)
    if not root.exists() or not root.is_dir():
        return []

    q_norm = q.strip().lower()
    scan_limit = min(max(limit * 20, 2000), 20000)

    results: list[PersistentRepoDirItem] = []
    for relative_path, abs_path in _walk_dirs(
        root, max_depth=depth, scan_limit=scan_limit
    ):
        if q_norm and q_norm not in relative_path.lower():
            continue

        repo_vcs, is_p4 = detect_repo_vcs(abs_path)
        results.append(
            PersistentRepoDirItem(
                relative_path=relative_path,
                repo_dir=f"{PERSIST_REPO_MOUNT_PATH}/{relative_path}",
                repo_vcs=repo_vcs,
                is_p4=is_p4,
            )
        )
        if len(results) >= limit:
            break

    return results
