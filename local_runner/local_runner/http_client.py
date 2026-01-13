from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass(frozen=True)
class ApiClient:
    server_url: str
    api_key: str
    runner_id: str

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def heartbeat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.server_url}/api/local-runners/heartbeat"
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def dispatch_task(
        self, *, limit: int = 1, task_status: str = "PENDING"
    ) -> Dict[str, Any]:
        url = (
            f"{self.server_url}/api/local-runners/tasks/dispatch"
            f"?runner_id={self.runner_id}&limit={limit}&task_status={task_status}"
        )
        resp = requests.post(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def update_subtask(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.server_url}/api/local-runners/tasks?runner_id={self.runner_id}"
        resp = requests.put(url, headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def upload_artifact(
        self, *, subtask_id: int, filename: str, data: bytes
    ) -> Dict[str, Any]:
        url = f"{self.server_url}/api/local-runners/artifacts/upload?runner_id={self.runner_id}"
        files = {"file": (filename, data)}
        form = {"subtask_id": str(subtask_id)}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.post(url, headers=headers, files=files, data=form, timeout=60)
        resp.raise_for_status()
        return resp.json()
