# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
from pathlib import Path

import pytest

# Add parent directory to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_redis_client(mocker):
    """Mock Redis client used by sandbox services."""
    client = mocker.MagicMock()
    client.set.return_value = True
    client.hget.return_value = None
    client.hgetall.return_value = {}
    client.hkeys.return_value = []
    client.zrange.return_value = []
    client.zrangebyscore.return_value = []
    return client


@pytest.fixture
def sample_sandbox_metadata():
    """Sample sandbox metadata stored in Redis."""
    return {"task_id": 12345, "subtask_id": 1}


@pytest.fixture
def sample_sandbox(sample_sandbox_metadata):
    """Sample Sandbox model instance."""
    from executor_manager.models.sandbox import Sandbox, SandboxStatus

    return Sandbox(
        sandbox_id="12345",
        container_name="wegent-task-testuser-12345",
        shell_type="ClaudeCode",
        status=SandboxStatus.RUNNING,
        user_id=100,
        user_name="testuser",
        base_url="http://localhost:10001",
        created_at=1704067200.0,
        started_at=1704067210.0,
        last_activity_at=1704067210.0,
        expires_at=1704067200.0 + 1800,
        metadata=dict(sample_sandbox_metadata),
    )


@pytest.fixture
def sample_execution(sample_sandbox_metadata):
    """Sample Execution model instance."""
    from executor_manager.models.sandbox import Execution, ExecutionStatus

    return Execution(
        execution_id="exec-1",
        sandbox_id="12345",
        prompt="echo hi",
        status=ExecutionStatus.RUNNING,
        metadata={
            "task_id": 12345,
            "subtask_id": sample_sandbox_metadata["subtask_id"],
        },
    )


@pytest.fixture
def mock_docker_client(mocker):
    """Mock Docker SDK client"""
    mock_client = mocker.MagicMock()

    # Mock container object
    mock_container = mocker.MagicMock()
    mock_container.id = "test_container_id"
    mock_container.status = "running"
    mock_container.start.return_value = None
    mock_container.stop.return_value = None
    mock_container.remove.return_value = None

    mock_client.containers.create.return_value = mock_container
    mock_client.containers.get.return_value = mock_container
    mock_client.containers.list.return_value = [mock_container]

    return mock_client


@pytest.fixture
def mock_executor_config():
    """Mock executor configuration"""
    return {
        "image": "test/executor:latest",
        "cpu_limit": "1.0",
        "memory_limit": "512m",
        "network_mode": "bridge",
    }


@pytest.fixture(scope="session", autouse=True)
def cleanup_logging():
    """Clean up logging handlers and queue listeners at test session end."""
    yield

    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        if hasattr(logger, "_queue_listener"):
            try:
                logger._queue_listener.stop()
            except Exception:
                pass

    logging.shutdown()
