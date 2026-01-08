import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.kind import Kind
from app.models.subtask import Subtask, SubtaskRole, SubtaskStatus
from app.models.task import TaskResource
from app.models.user import User
from app.services.adapters.executor_kinds import ExecutorKindsService


def _create_kind(
    db: Session,
    *,
    user_id: int,
    kind: str,
    name: str,
    json: dict,
    namespace: str = "default",
) -> Kind:
    obj = Kind(
        user_id=user_id,
        kind=kind,
        name=name,
        namespace=namespace,
        json=json,
        is_active=True,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _create_task_resource(
    db: Session,
    *,
    user_id: int,
    kind: str,
    name: str,
    json: dict,
    namespace: str = "default",
) -> TaskResource:
    obj = TaskResource(
        user_id=user_id,
        kind=kind,
        name=name,
        namespace=namespace,
        json=json,
        is_active=True,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def _seed_code_shell_task(
    db: Session,
    *,
    user: User,
    shell_type: str,
    previous_session_field: dict,
) -> Subtask:
    now = datetime.now().isoformat()

    workspace_name = "ws-1"
    team_name = "team-1"
    bot_name = "bot-1"
    ghost_name = "ghost-1"
    shell_name = f"{shell_type.lower()}-shell-1"

    _create_task_resource(
        db,
        user_id=user.id,
        kind="Workspace",
        name=workspace_name,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Workspace",
            "metadata": {"name": workspace_name, "namespace": "default"},
            "spec": {
                "repository": {
                    "gitUrl": "https://example.com/repo.git",
                    "gitRepo": "example/repo",
                    "gitRepoId": 0,
                    "branchName": "main",
                    "gitDomain": "github.com",
                }
            },
            "status": {"state": "Available", "createdAt": now, "updatedAt": now},
        },
    )

    task = _create_task_resource(
        db,
        user_id=user.id,
        kind="Task",
        name="task-1",
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Task",
            "metadata": {"name": "task-1", "namespace": "default"},
            "spec": {
                "title": "test",
                "prompt": "",
                "teamRef": {"name": team_name, "namespace": "default"},
                "workspaceRef": {"name": workspace_name, "namespace": "default"},
            },
            "status": {"status": "PENDING", "createdAt": now, "updatedAt": now},
        },
    )

    team = _create_kind(
        db,
        user_id=user.id,
        kind="Team",
        name=team_name,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Team",
            "metadata": {"name": team_name, "namespace": "default"},
            "spec": {
                "members": [
                    {
                        "botRef": {"name": bot_name, "namespace": "default"},
                        "prompt": "",
                        "role": "assistant",
                    }
                ],
                "collaborationModel": "collaborate",
            },
            "status": {"state": "Available"},
        },
    )

    ghost = _create_kind(
        db,
        user_id=0,
        kind="Ghost",
        name=ghost_name,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Ghost",
            "metadata": {"name": ghost_name, "namespace": "default"},
            "spec": {"systemPrompt": "", "mcpServers": {}, "skills": []},
            "status": {"state": "Available"},
        },
    )

    shell = _create_kind(
        db,
        user_id=0,
        kind="Shell",
        name=shell_name,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Shell",
            "metadata": {"name": shell_name, "namespace": "default"},
            "spec": {"shellType": shell_type},
            "status": {"state": "Available"},
        },
    )

    bot = _create_kind(
        db,
        user_id=0,
        kind="Bot",
        name=bot_name,
        json={
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Bot",
            "metadata": {"name": bot_name, "namespace": "default"},
            "spec": {
                "ghostRef": {"name": ghost.name, "namespace": ghost.namespace},
                "shellRef": {"name": shell.name, "namespace": shell.namespace},
            },
            "status": {"state": "Available"},
        },
    )

    db.add_all(
        [
            Subtask(
                user_id=user.id,
                task_id=task.id,
                team_id=team.id,
                title="user-1",
                bot_ids=[bot.id],
                role=SubtaskRole.USER,
                status=SubtaskStatus.COMPLETED,
                progress=100,
                message_id=1,
                parent_id=0,
                prompt="hi",
                result={},
            ),
            Subtask(
                user_id=user.id,
                task_id=task.id,
                team_id=team.id,
                title="ai-1",
                bot_ids=[bot.id],
                role=SubtaskRole.ASSISTANT,
                status=SubtaskStatus.COMPLETED,
                progress=100,
                message_id=2,
                parent_id=1,
                prompt="",
                result={"shell_type": shell_type, **previous_session_field},
            ),
            Subtask(
                user_id=user.id,
                task_id=task.id,
                team_id=team.id,
                title="user-2",
                bot_ids=[bot.id],
                role=SubtaskRole.USER,
                status=SubtaskStatus.COMPLETED,
                progress=100,
                message_id=3,
                parent_id=0,
                prompt="next",
                result={},
            ),
        ]
    )
    db.commit()

    target = Subtask(
        user_id=user.id,
        task_id=task.id,
        team_id=team.id,
        title="ai-2",
        bot_ids=[bot.id],
        role=SubtaskRole.ASSISTANT,
        status=SubtaskStatus.RUNNING,
        progress=0,
        message_id=4,
        parent_id=3,
        prompt="",
        result={"shell_type": shell_type},
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def test_executor_kinds_force_codex_new_session_when_resume_flag_disabled(
    test_db: Session,
    test_user: User,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "CODE_SHELL_RESUME_ENABLED", False)

    target = _seed_code_shell_task(
        test_db,
        user=test_user,
        shell_type="Codex",
        previous_session_field={"resume_session_id": "thread_123"},
    )

    svc = ExecutorKindsService(None)
    payload = svc._format_subtasks_response(test_db, [target])["tasks"][0]

    assert payload["retry_mode"] == "new_session"
    assert "resume_session_id" not in payload


def test_executor_kinds_force_claude_new_session_when_resume_flag_disabled(
    test_db: Session,
    test_user: User,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "CODE_SHELL_RESUME_ENABLED", False)

    target = _seed_code_shell_task(
        test_db,
        user=test_user,
        shell_type="ClaudeCode",
        previous_session_field={"session_id": "session_old"},
    )

    svc = ExecutorKindsService(None)
    payload = svc._format_subtasks_response(test_db, [target])["tasks"][0]

    assert payload["retry_mode"] == "new_session"
    session_id = payload["session_id"]
    assert session_id != "session_old"
    uuid.UUID(session_id)
