import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.subtask import Subtask, SubtaskRole, SubtaskStatus
from app.services.chat.operations.retry import reset_subtask_for_retry


def test_reset_subtask_for_retry_resume_preserves_codex_session(
    test_db: Session,
) -> None:
    subtask = Subtask(
        user_id=1,
        task_id=1,
        team_id=1,
        title="retry-subtask",
        bot_ids=[1],
        role=SubtaskRole.ASSISTANT,
        status=SubtaskStatus.FAILED,
        progress=100,
        message_id=1,
        result={
            "shell_type": "Codex",
            "value": "previous output",
            "error": "boom",
            "resume_session_id": "thread_123",
            "codex_events": [{"type": "init"}],
        },
    )

    reset_subtask_for_retry(test_db, subtask, retry_mode="resume", shell_type="Codex")

    assert subtask.status == SubtaskStatus.PENDING
    assert subtask.progress == 0
    assert subtask.error_message == ""
    assert subtask.result is not None
    assert subtask.result["shell_type"] == "Codex"
    assert subtask.result["retry_mode"] == "resume"
    assert subtask.result["resume_session_id"] == "thread_123"
    assert "value" not in subtask.result
    assert "error" not in subtask.result
    assert "codex_events" not in subtask.result


def test_reset_subtask_for_retry_new_session_clears_codex_session(
    test_db: Session,
) -> None:
    subtask = Subtask(
        user_id=1,
        task_id=1,
        team_id=1,
        title="retry-subtask",
        bot_ids=[1],
        role=SubtaskRole.ASSISTANT,
        status=SubtaskStatus.FAILED,
        progress=100,
        message_id=1,
        result={"shell_type": "Codex", "resume_session_id": "thread_123"},
    )

    reset_subtask_for_retry(
        test_db, subtask, retry_mode="new_session", shell_type="Codex"
    )

    assert subtask.result is not None
    assert subtask.result["shell_type"] == "Codex"
    assert subtask.result["retry_mode"] == "new_session"
    assert "resume_session_id" not in subtask.result


def test_reset_subtask_for_retry_resume_forced_to_new_session_when_flag_disabled(
    test_db: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "CODE_SHELL_RESUME_ENABLED", False)

    subtask = Subtask(
        user_id=1,
        task_id=1,
        team_id=1,
        title="retry-subtask",
        bot_ids=[1],
        role=SubtaskRole.ASSISTANT,
        status=SubtaskStatus.FAILED,
        progress=100,
        message_id=1,
        result={
            "shell_type": "Codex",
            "resume_session_id": "thread_123",
        },
    )

    reset_subtask_for_retry(test_db, subtask, retry_mode="resume", shell_type="Codex")

    assert subtask.result is not None
    assert subtask.result["retry_mode"] == "new_session"
    assert "resume_session_id" not in subtask.result


def test_reset_subtask_for_retry_new_session_generates_claude_session(
    test_db: Session,
) -> None:
    subtask = Subtask(
        user_id=1,
        task_id=1,
        team_id=1,
        title="retry-subtask",
        bot_ids=[1],
        role=SubtaskRole.ASSISTANT,
        status=SubtaskStatus.FAILED,
        progress=100,
        message_id=1,
        result={"shell_type": "ClaudeCode", "session_id": "old"},
    )

    reset_subtask_for_retry(
        test_db, subtask, retry_mode="new_session", shell_type="ClaudeCode"
    )

    assert subtask.result is not None
    assert subtask.result["shell_type"] == "ClaudeCode"
    assert subtask.result["retry_mode"] == "new_session"

    session_id = subtask.result["session_id"]
    assert session_id != "old"
    uuid.UUID(session_id)


def test_reset_subtask_for_retry_resume_forced_to_new_session_for_claude_when_flag_disabled(
    test_db: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "CODE_SHELL_RESUME_ENABLED", False)

    subtask = Subtask(
        user_id=1,
        task_id=1,
        team_id=1,
        title="retry-subtask",
        bot_ids=[1],
        role=SubtaskRole.ASSISTANT,
        status=SubtaskStatus.FAILED,
        progress=100,
        message_id=1,
        result={
            "shell_type": "ClaudeCode",
            "session_id": "old",
        },
    )

    reset_subtask_for_retry(
        test_db, subtask, retry_mode="resume", shell_type="ClaudeCode"
    )

    assert subtask.result is not None
    assert subtask.result["retry_mode"] == "new_session"
    session_id = subtask.result["session_id"]
    assert session_id != "old"
    uuid.UUID(session_id)
