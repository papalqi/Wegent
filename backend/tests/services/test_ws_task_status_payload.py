import asyncio

import pytest

from app.api.ws.events import TaskStatusPayload
from app.services.chat.ws_emitter import WebSocketEmitter
from app.api.ws.events import ServerEvents


class _DummySio:
    def __init__(self):
        self.emitted = []

    async def emit(self, event, payload, room=None, namespace=None):
        self.emitted.append((event, payload, room, namespace))


@pytest.mark.asyncio
async def test_emit_task_status_includes_phase_and_progress_text():
    sio = _DummySio()
    emitter = WebSocketEmitter(sio)

    await emitter.emit_task_status(
        user_id=1,
        task_id=2,
        status="RUNNING",
        progress=30,
        status_phase="pulling_image",
        progress_text="拉取镜像中",
    )

    assert len(sio.emitted) == 1
    event, payload, room, namespace = sio.emitted[0]
    assert event == ServerEvents.TASK_STATUS
    assert payload["status_phase"] == "pulling_image"
    assert payload["progress_text"] == "拉取镜像中"
    assert payload["task_id"] == 2
    assert payload["status"] == "RUNNING"
    assert payload["progress"] == 30
    assert room == "user:1"
    assert namespace == emitter.namespace


def test_task_status_payload_accepts_new_optional_fields():
    payload = TaskStatusPayload(
        task_id=1,
        status="RUNNING",
        progress=10,
        status_phase="booting_executor",
        progress_text="Docker 启动中",
    )
    assert payload.status_phase == "booting_executor"
    assert payload.progress_text == "Docker 启动中"


def test_derive_phase_and_text_from_progress():
    from app.services.adapters.executor_kinds import ExecutorKindsService

    svc = ExecutorKindsService(None)
    phase, text = svc._derive_status_phase_and_text(status="RUNNING", progress=45)
    assert phase == "loading_skills"
    assert "加载" in text
