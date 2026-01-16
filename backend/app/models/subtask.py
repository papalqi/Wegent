# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Subtask model representing a message in a task conversation.

Re-exported from shared package for backward compatibility.
"""

from shared.models.db import SenderType, Subtask, SubtaskRole, SubtaskStatus

__all__ = ["Subtask", "SubtaskStatus", "SubtaskRole", "SenderType"]
