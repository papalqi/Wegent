from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class WorkspacePolicy(BaseModel):
    dirty_mode: str = Field("reject", description="reject|allow")
    max_artifact_mb: int = Field(50, ge=1, description="Max artifact size to upload")

    @field_validator("dirty_mode")
    @classmethod
    def _validate_dirty_mode(cls, v: str) -> str:
        if v not in ("reject", "allow"):
            raise ValueError("dirty_mode must be 'reject' or 'allow'")
        return v


class WorkspaceConfig(BaseModel):
    id: str
    name: str
    path: str
    policy: WorkspacePolicy = Field(default_factory=WorkspacePolicy)

    def resolved_path(self) -> Path:
        return Path(os.path.expanduser(self.path)).resolve()


class RunnerConfig(BaseModel):
    server_url: str
    api_key: str = Field(..., description="Personal API key starting with wg-")
    runner_id: str
    name: str = ""
    poll_interval_sec: float = Field(2.0, ge=0.2)
    codex_cmd: str = Field("codex", description="Path to codex executable")
    workspaces: List[WorkspaceConfig] = Field(default_factory=list)

    @field_validator("server_url")
    @classmethod
    def _strip_server_url(cls, v: str) -> str:
        return v.rstrip("/")

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceConfig]:
        for ws in self.workspaces:
            if ws.id == workspace_id:
                return ws
        return None


DEFAULT_CONFIG_PATH = Path("~/.wegent/local-runner.toml").expanduser()


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> RunnerConfig:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return RunnerConfig.model_validate(raw)
