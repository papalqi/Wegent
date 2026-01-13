from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class GitSnapshot:
    head: Optional[str]
    branch: Optional[str]
    dirty: bool
    porcelain: str


def _run_git(cwd: Path, args: List[str]) -> str:
    out = subprocess.check_output(
        ["git", *args], cwd=str(cwd), stderr=subprocess.STDOUT
    )
    return out.decode("utf-8", errors="replace").strip()


def get_snapshot(cwd: Path) -> GitSnapshot:
    head = None
    branch = None
    try:
        head = _run_git(cwd, ["rev-parse", "HEAD"])
    except Exception:
        head = None
    try:
        branch = _run_git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"])
    except Exception:
        branch = None
    porcelain = ""
    try:
        porcelain = _run_git(cwd, ["status", "--porcelain"])
    except Exception:
        porcelain = ""
    return GitSnapshot(
        head=head, branch=branch, dirty=bool(porcelain.strip()), porcelain=porcelain
    )


def diff_text(cwd: Path) -> str:
    return _run_git(cwd, ["diff"])


def diff_binary(cwd: Path) -> bytes:
    out = subprocess.check_output(
        ["git", "diff", "--binary"], cwd=str(cwd), stderr=subprocess.STDOUT
    )
    return out


def changed_files(cwd: Path) -> List[str]:
    raw = _run_git(cwd, ["diff", "--name-only"])
    return [line.strip() for line in raw.splitlines() if line.strip()]
