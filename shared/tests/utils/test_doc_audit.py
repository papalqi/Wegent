# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from datetime import date

import pytest

from shared.utils.doc_audit import (DocInfo, _parse_git_iso_date, collect_doc_infos,
                                    find_stale_docs, render_json_report,
                                    render_text_report)


class TestDocAudit:
    def test_parse_git_iso_date_empty(self):
        with pytest.raises(ValueError, match="empty git date"):
            _parse_git_iso_date("")

    def test_collect_and_find_stale_docs(self):
        repo_root = object()

        def runner(cmd):
            if cmd[:3] == ["git", "ls-files", "docs/**/*.md"]:
                return "docs/a.md\ndocs/b.md\n"
            if cmd[:5] == ["git", "log", "-1", "--format=%cs", "--"]:
                if cmd[5] == "docs/a.md":
                    return "2026-01-01"
                if cmd[5] == "docs/b.md":
                    return "2025-12-01"
            raise AssertionError(f"unexpected cmd: {cmd}")

        infos = collect_doc_infos(
            repo_root,  # type: ignore[arg-type]
            pathspecs=["docs/**/*.md", "docs/*.md"],
            reference_date=date(2026, 1, 11),
            runner=runner,
        )

        assert infos == [
            DocInfo(path="docs/b.md", last_commit_date=date(2025, 12, 1), age_days=41),
            DocInfo(path="docs/a.md", last_commit_date=date(2026, 1, 1), age_days=10),
        ]

        stale = find_stale_docs(infos, threshold_days=30)
        assert [s.path for s in stale] == ["docs/b.md"]

        text = render_text_report(
            infos, threshold_days=30, reference_date=date(2026, 1, 11)
        )
        assert "docs_total: 2" in text
        assert "docs_stale: 1" in text
        assert "docs/b.md" in text

        js = render_json_report(
            infos, threshold_days=30, reference_date=date(2026, 1, 11)
        )
        assert '"docs_total": 2' in js
        assert '"docs_stale": 1' in js
        assert '"path": "docs/b.md"' in js

