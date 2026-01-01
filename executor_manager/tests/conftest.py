# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from pathlib import Path

# Add parent directory to Python path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from unittest.mock import MagicMock, Mock

import pytest


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
