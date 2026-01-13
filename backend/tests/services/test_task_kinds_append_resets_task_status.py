from datetime import datetime

from sqlalchemy.orm import Session

from app.models.kind import Kind
from app.models.task import TaskResource
from app.models.user import User
from app.schemas.kind import Task
from app.schemas.task import TaskCreate
from app.services.adapters.task_kinds import task_kinds_service


def test_create_task_or_append_resets_error_status_for_existing_task(
    test_db: Session,
    test_user: User,
) -> None:
    bot = Kind(
        user_id=test_user.id,
        kind="Bot",
        name="bot",
        namespace="default",
        json={"kind": "Bot"},
        is_active=True,
    )
    test_db.add(bot)

    team = Kind(
        user_id=test_user.id,
        kind="Team",
        name="team",
        namespace="default",
        json={
            "kind": "Team",
            "spec": {
                "members": [{"botRef": {"name": "bot", "namespace": "default"}}],
                "collaborationModel": "collaborate",
            },
            "status": {"state": "Available"},
            "metadata": {"name": "team", "namespace": "default"},
            "apiVersion": "agent.wecode.io/v1",
        },
        is_active=True,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(team)

    task_json = {
        "kind": "Task",
        "spec": {
            "title": "t",
            "prompt": "old",
            "teamRef": {"name": "team", "namespace": "default"},
            "workspaceRef": {"name": "workspace-1", "namespace": "default"},
        },
        "status": {
            "state": "Available",
            "status": "FAILED",
            "progress": 100,
            "errorMessage": "previous error",
            "result": {"foo": "bar"},
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat(),
            "completedAt": datetime.now().isoformat(),
        },
        "metadata": {
            "name": "task-1",
            "namespace": "default",
            "labels": {
                "autoDeleteExecutor": "false",
                "taskType": "chat",
                "source": "web",
            },
        },
        "apiVersion": "agent.wecode.io/v1",
    }
    task = TaskResource(
        user_id=test_user.id,
        kind="Task",
        name="task-1",
        namespace="default",
        json=task_json,
        is_active=True,
        updated_at=datetime.now(),
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    task_kinds_service.create_task_or_append(
        test_db,
        obj_in=TaskCreate(prompt="new message"),
        user=test_user,
        task_id=task.id,
    )

    updated_task = (
        test_db.query(TaskResource).filter(TaskResource.id == task.id).first()
    )
    assert updated_task is not None

    task_crd = Task.model_validate(updated_task.json)
    assert task_crd.status is not None
    assert task_crd.status.status == "PENDING"
    assert task_crd.status.progress == 0
    assert task_crd.status.errorMessage == ""
    assert task_crd.status.result is None
    assert task_crd.status.completedAt is None
