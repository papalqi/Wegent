from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence


def _check_output(cmd: Sequence[str], *, cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd), text=True).strip()


def _parse_git_iso_date(value: str) -> date:
    if not value:
        raise ValueError("empty git date")
    return datetime.strptime(value, "%Y-%m-%d").date()


def list_tracked_files(
    repo_root: Path,
    *,
    pathspecs: Sequence[str],
    runner: Callable[[Sequence[str]], str] | None = None,
) -> list[str]:
    if runner is None:
        runner = lambda cmd: _check_output(cmd, cwd=repo_root)
    out = runner(["git", "ls-files", *pathspecs])
    files = [line.strip() for line in out.splitlines() if line.strip()]
    return sorted(set(files))


def get_last_commit_date_for_path(
    repo_root: Path,
    path: str,
    *,
    runner: Callable[[Sequence[str]], str] | None = None,
) -> date:
    if runner is None:
        runner = lambda cmd: _check_output(cmd, cwd=repo_root)
    out = runner(["git", "log", "-1", "--format=%cs", "--", path])
    return _parse_git_iso_date(out.strip())


@dataclass(frozen=True)
class DocInfo:
    path: str
    last_commit_date: date
    age_days: int


def collect_doc_infos(
    repo_root: Path,
    *,
    pathspecs: Sequence[str],
    reference_date: date | None = None,
    runner: Callable[[Sequence[str]], str] | None = None,
) -> list[DocInfo]:
    if reference_date is None:
        reference_date = date.today()
    if runner is None:
        runner = lambda cmd: _check_output(cmd, cwd=repo_root)

    paths = list_tracked_files(repo_root, pathspecs=pathspecs, runner=runner)
    infos: list[DocInfo] = []
    for path in paths:
        last = get_last_commit_date_for_path(repo_root, path, runner=runner)
        infos.append(
            DocInfo(
                path=path,
                last_commit_date=last,
                age_days=(reference_date - last).days,
            )
        )
    return sorted(infos, key=lambda i: (i.last_commit_date, i.path))


def find_stale_docs(
    infos: Iterable[DocInfo], *, threshold_days: int
) -> list[DocInfo]:
    return [info for info in infos if info.age_days >= threshold_days]


def render_text_report(
    infos: Sequence[DocInfo],
    *,
    threshold_days: int,
    reference_date: date,
) -> str:
    stale = find_stale_docs(infos, threshold_days=threshold_days)
    lines: list[str] = []
    lines.append(f"reference_date: {reference_date.isoformat()}")
    lines.append(f"threshold_days: {threshold_days}")
    lines.append(f"docs_total: {len(infos)}")
    lines.append(f"docs_stale: {len(stale)}")
    for info in stale:
        lines.append(
            f"- {info.path} last_commit={info.last_commit_date.isoformat()} age_days={info.age_days}"
        )
    return "\n".join(lines)


def render_json_report(
    infos: Sequence[DocInfo],
    *,
    threshold_days: int,
    reference_date: date,
) -> str:
    stale = find_stale_docs(infos, threshold_days=threshold_days)
    payload = {
        "reference_date": reference_date.isoformat(),
        "threshold_days": threshold_days,
        "docs_total": len(infos),
        "docs_stale": len(stale),
        "stale": [
            {
                "path": info.path,
                "last_commit": info.last_commit_date.isoformat(),
                "age_days": info.age_days,
            }
            for info in stale
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def pathspecs_for_scope(scope: str) -> list[str]:
    if scope == "docs":
        return ["docs/**/*.md", "docs/*.md"]
    if scope == "all":
        return ["**/*.md", "*.md"]
    raise ValueError(f"unsupported scope: {scope}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doc-audit")
    parser.add_argument(
        "--scope",
        choices=["docs", "all"],
        default="docs",
        help="Which markdown files to scan.",
    )
    parser.add_argument("--threshold-days", type=int, default=30)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--fail-on-stale", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    reference_date = date.today()
    infos = collect_doc_infos(
        repo_root, pathspecs=pathspecs_for_scope(args.scope), reference_date=reference_date
    )

    if args.format == "json":
        print(
            render_json_report(
                infos, threshold_days=args.threshold_days, reference_date=reference_date
            )
        )
    else:
        print(
            render_text_report(
                infos, threshold_days=args.threshold_days, reference_date=reference_date
            )
        )

    stale = find_stale_docs(infos, threshold_days=args.threshold_days)
    if args.fail_on_stale and stale:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

