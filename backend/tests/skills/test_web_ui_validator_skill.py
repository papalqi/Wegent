# SPDX-FileCopyrightText: 2025 WeCode, Inc.
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import yaml

SKILL_DIR = (
    Path(__file__).parent.parent.parent / "init_data" / "skills" / "web_ui_validator"
)


def _read_skill_frontmatter(skill_md_path: Path) -> dict:
    content = skill_md_path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise AssertionError("SKILL.md must start with YAML frontmatter")

    end = content.find("\n---\n", 4)
    if end == -1:
        raise AssertionError("SKILL.md YAML frontmatter end marker not found")

    frontmatter = content[4:end]
    return yaml.safe_load(frontmatter) or {}


def test_web_ui_validator_skill_package_layout() -> None:
    assert SKILL_DIR.exists() and SKILL_DIR.is_dir()
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "web_ui_validator.py").exists()
    assert (SKILL_DIR / "mcp_http_ui_server.py").exists()


def test_web_ui_validator_skill_metadata_binds_codex_and_claudecode() -> None:
    meta = _read_skill_frontmatter(SKILL_DIR / "SKILL.md")
    bind_shells = meta.get("bindShells") or []
    assert isinstance(bind_shells, list)
    assert set(bind_shells) == {"ClaudeCode", "Codex"}
