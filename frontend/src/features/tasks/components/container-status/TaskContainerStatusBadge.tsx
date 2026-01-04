// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useTranslation } from '@/hooks/useTranslation';
import { useTaskContainerStatus } from '@/features/tasks/hooks/useTaskContainerStatus';
import { TaskContainerStatus } from '@/types/api';

function getBadgeVariant(status: TaskContainerStatus) {
  if (status === 'running') return 'success';
  if (status === 'not_found') return 'error';
  if (status === 'exited') return 'secondary';
  return 'warning';
}

function getStatusLabel(
  t: (key: string, defaultValue?: string) => string,
  status: TaskContainerStatus
) {
  if (status === 'running') return t('common:tasks.container_status_running');
  if (status === 'exited') return t('common:tasks.container_status_exited');
  if (status === 'not_found') return t('common:tasks.container_status_not_found');
  return t('common:tasks.container_status_unknown');
}

export function TaskContainerStatusBadge({ taskId }: { taskId: number }) {
  const { t } = useTranslation();
  const { data } = useTaskContainerStatus(taskId, { intervalMs: 10_000, enabled: true });

  const status = data?.status ?? 'unknown';
  const label = getStatusLabel(t, status);
  const title = t('common:tasks.container_status_title');
  const tooltip = data?.executor_name
    ? `${title}: ${label} (${data.executor_name})`
    : `${title}: ${label}`;

  return (
    <TooltipProvider>
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>
          <Badge variant={getBadgeVariant(status)} size="sm">
            {title}: {label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs">
          <p className="text-xs text-text-primary">{tooltip}</p>
          {!!data?.reason && <p className="text-xs text-text-muted mt-1">{data.reason}</p>}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
