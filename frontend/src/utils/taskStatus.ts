// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import type { TaskStatus } from '@/types/api';

export function getTaskStatusLabelKey(status: TaskStatus): string | null {
  switch (status) {
    case 'RUNNING':
      return 'chat:messages.status_running';
    case 'PENDING':
      return 'chat:messages.status_pending';
    case 'CANCELLING':
      return 'chat:messages.status_cancelling';
    case 'CANCELLED':
      return 'chat:messages.status_cancelled';
    case 'COMPLETED':
      return 'chat:messages.status_completed';
    case 'FAILED':
      return 'chat:messages.status_failed';
    case 'DELETE':
      return null;
    default:
      return null;
  }
}

export function isTaskActiveStatus(status: TaskStatus): boolean {
  return status === 'PENDING' || status === 'RUNNING' || status === 'CANCELLING';
}

export function isTaskTerminalStatus(status: TaskStatus): boolean {
  return (
    status === 'COMPLETED' || status === 'FAILED' || status === 'CANCELLED' || status === 'DELETE'
  );
}
