import pytest
from sqlalchemy.orm import Session

from app.models.subtask import Subtask, SubtaskRole
from app.models.subtask import SubtaskStatus as ModelSubtaskStatus
from app.schemas.subtask import SubtaskExecutorUpdate
from app.services.adapters.executor_kinds import executor_kinds_service


@pytest.mark.asyncio
async def test_update_subtask_preserves_codex_events_and_shell_type(
    test_db: Session,
) -> None:
    subtask = Subtask(
        user_id=1,
        task_id=123,
        team_id=1,
        title="executor-subtask",
        bot_ids=[1],
        role=SubtaskRole.ASSISTANT,
        status=ModelSubtaskStatus.RUNNING,
        progress=0,
        message_id=1,
        result={
            "shell_type": "Codex",
            "value": "",
            "codex_events": [{"type": "init"}],
        },
    )
    test_db.add(subtask)
    test_db.commit()
    test_db.refresh(subtask)

    await executor_kinds_service.update_subtask(
        test_db,
        subtask_update=SubtaskExecutorUpdate(
            subtask_id=subtask.id,
            status="RUNNING",
            progress=10,
            result={"value": "hello", "codex_event": {"type": "tick"}},
        ),
    )

    test_db.refresh(subtask)
    assert subtask.result is not None
    assert subtask.result.get("shell_type") == "Codex"
    assert isinstance(subtask.result.get("codex_events"), list)
    assert [e.get("type") for e in subtask.result["codex_events"]] == ["init", "tick"]

    await executor_kinds_service.update_subtask(
        test_db,
        subtask_update=SubtaskExecutorUpdate(
            subtask_id=subtask.id,
            status="COMPLETED",
            progress=100,
            result={"value": "final"},
        ),
    )

    test_db.refresh(subtask)
    assert subtask.result is not None
    assert subtask.result.get("shell_type") == "Codex"
    assert isinstance(subtask.result.get("codex_events"), list)
    assert [e.get("type") for e in subtask.result["codex_events"]] == ["init", "tick"]


@pytest.mark.asyncio
async def test_update_subtask_merges_codex_events_and_codex_event(
    test_db: Session,
) -> None:
    subtask = Subtask(
        user_id=1,
        task_id=124,
        team_id=1,
        title="executor-subtask",
        bot_ids=[1],
        role=SubtaskRole.ASSISTANT,
        status=ModelSubtaskStatus.RUNNING,
        progress=0,
        message_id=1,
        result={
            "shell_type": "Codex",
            "value": "",
            "codex_events": [{"type": "init"}],
        },
    )
    test_db.add(subtask)
    test_db.commit()
    test_db.refresh(subtask)

    await executor_kinds_service.update_subtask(
        test_db,
        subtask_update=SubtaskExecutorUpdate(
            subtask_id=subtask.id,
            status="RUNNING",
            progress=10,
            result={"codex_events": [{"type": "init"}, {"type": "snapshot"}]},
        ),
    )
    test_db.refresh(subtask)
    assert subtask.result is not None
    assert [e.get("type") for e in subtask.result["codex_events"]] == [
        "init",
        "snapshot",
    ]

    await executor_kinds_service.update_subtask(
        test_db,
        subtask_update=SubtaskExecutorUpdate(
            subtask_id=subtask.id,
            status="RUNNING",
            progress=20,
            result={"codex_event": {"type": "tail"}},
        ),
    )

    test_db.refresh(subtask)
    assert subtask.result is not None
    assert [e.get("type") for e in subtask.result["codex_events"]] == [
        "init",
        "snapshot",
        "tail",
    ]
