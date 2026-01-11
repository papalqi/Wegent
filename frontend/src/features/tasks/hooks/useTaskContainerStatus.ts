// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { taskApis } from '@/apis/tasks';
import { TaskExecutorContainerStatus } from '@/types/api';

type TaskId = number;
type StatusMap = Record<TaskId, TaskExecutorContainerStatus>;

function normalizeTaskIds(taskIds: number[]): number[] {
  const unique = Array.from(new Set(taskIds.filter(id => Number.isFinite(id) && id > 0)));
  unique.sort((a, b) => a - b);
  return unique;
}

export function useTaskContainerStatus(
  taskId: number | null | undefined,
  options?: { intervalMs?: number; enabled?: boolean }
) {
  const intervalMs = options?.intervalMs ?? 10_000;
  const enabled = options?.enabled ?? true;

  const [data, setData] = useState<TaskExecutorContainerStatus | null>(null);
  const [error, setError] = useState<unknown>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const refresh = useCallback(async () => {
    if (!taskId || !enabled) return;
    if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return;

    try {
      const res = await taskApis.getTaskContainerStatus(taskId);
      setData(res);
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, [taskId, enabled]);

  useEffect(() => {
    if (!taskId || !enabled) {
      setData(null);
      return;
    }

    refresh();

    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    pollingRef.current = setInterval(() => {
      refresh();
    }, intervalMs);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [taskId, enabled, intervalMs, refresh]);

  return { data, error, refresh };
}

export function useTaskContainerStatusMap(
  taskIds: number[],
  options?: { intervalMs?: number; enabled?: boolean; maxTasks?: number }
) {
  const intervalMs = options?.intervalMs ?? 15_000;
  const enabled = options?.enabled ?? true;
  const maxTasks = options?.maxTasks ?? 50;

  const ids = useMemo(() => normalizeTaskIds(taskIds).slice(0, maxTasks), [taskIds, maxTasks]);
  const [map, setMap] = useState<StatusMap>({});
  const [error, setError] = useState<unknown>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    if (ids.length === 0) return;
    if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return;

    try {
      const res = await taskApis.getTasksContainerStatus(ids);
      const next: StatusMap = {};
      for (const item of res.items ?? []) {
        next[item.task_id] = item;
      }
      setMap(next);
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, [enabled, ids]);

  useEffect(() => {
    if (!enabled || ids.length === 0) {
      setMap({});
      return;
    }

    refresh();

    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    pollingRef.current = setInterval(() => {
      refresh();
    }, intervalMs);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [enabled, ids, intervalMs, refresh]);

  return { map, error, refresh, ids };
}
