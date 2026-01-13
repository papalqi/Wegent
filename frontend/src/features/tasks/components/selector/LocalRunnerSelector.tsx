// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { localRunnersApis } from '@/apis/local-runners';
import type { LocalRunner } from '@/types/api';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useTranslation } from '@/hooks/useTranslation';

export interface LocalRunnerSelectorProps {
  disabled?: boolean;
  runnerId: string | null;
  setRunnerId: (value: string | null) => void;
  workspaceId: string | null;
  setWorkspaceId: (value: string | null) => void;
}

function isOnline(runner: LocalRunner): boolean {
  const online = runner.capabilities?.online;
  return online === true;
}

export default function LocalRunnerSelector({
  disabled = false,
  runnerId,
  setRunnerId,
  workspaceId,
  setWorkspaceId,
}: LocalRunnerSelectorProps) {
  const { t } = useTranslation();
  const [runners, setRunners] = useState<LocalRunner[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        setLoading(true);
        const res = await localRunnersApis.list();
        if (mounted) setRunners(res.items || []);
      } catch (_err) {
        if (mounted) setRunners([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    const timer = setInterval(load, 10_000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const availableRunners = useMemo(() => {
    return runners
      .filter(r => !r.disabled)
      .sort((a, b) => (isOnline(b) ? 1 : 0) - (isOnline(a) ? 1 : 0));
  }, [runners]);

  const selectedRunner = useMemo(() => {
    return availableRunners.find(r => r.id === runnerId) || null;
  }, [availableRunners, runnerId]);

  const availableWorkspaces = useMemo(() => {
    if (!selectedRunner) return [];
    return selectedRunner.workspaces || [];
  }, [selectedRunner]);

  const handleRunnerChange = (value: string) => {
    setRunnerId(value || null);
    setWorkspaceId(null);
  };

  const handleWorkspaceChange = (value: string) => {
    setWorkspaceId(value || null);
  };

  const runnerPlaceholder = loading
    ? t('chat:local_runner_loading')
    : t('chat:local_runner_placeholder');
  const workspacePlaceholder = t('chat:local_workspace_placeholder');

  return (
    <div className="flex items-center gap-2">
      <Select value={runnerId || ''} onValueChange={handleRunnerChange} disabled={disabled}>
        <SelectTrigger className="h-8 w-[180px]">
          <SelectValue placeholder={runnerPlaceholder} />
        </SelectTrigger>
        <SelectContent>
          {availableRunners.length === 0 && (
            <SelectItem value="__none__" disabled>
              {t('chat:local_runner_empty')}
            </SelectItem>
          )}
          {availableRunners.map(r => (
            <SelectItem key={r.id} value={r.id}>
              {r.name}{' '}
              {isOnline(r)
                ? t('chat:local_runner_online_suffix')
                : t('chat:local_runner_offline_suffix')}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={workspaceId || ''}
        onValueChange={handleWorkspaceChange}
        disabled={disabled || !selectedRunner}
      >
        <SelectTrigger className="h-8 w-[180px]">
          <SelectValue placeholder={workspacePlaceholder} />
        </SelectTrigger>
        <SelectContent>
          {availableWorkspaces.length === 0 && (
            <SelectItem value="__none__" disabled>
              {t('chat:local_workspace_empty')}
            </SelectItem>
          )}
          {availableWorkspaces.map(ws => (
            <SelectItem key={ws.id} value={ws.id}>
              {ws.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
