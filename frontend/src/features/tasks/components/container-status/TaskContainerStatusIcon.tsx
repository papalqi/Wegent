// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import { CircleHelp, Server, ServerOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TaskContainerStatus } from '@/types/api';

export function TaskContainerStatusIcon({
  status,
  className,
}: {
  status: TaskContainerStatus;
  className?: string;
}) {
  if (status === 'running') {
    return <Server className={cn('w-3.5 h-3.5 text-green-500', className)} />;
  }

  if (status === 'not_found') {
    return <ServerOff className={cn('w-3.5 h-3.5 text-red-500', className)} />;
  }

  if (status === 'exited') {
    return <Server className={cn('w-3.5 h-3.5 text-gray-400', className)} />;
  }

  return <CircleHelp className={cn('w-3.5 h-3.5 text-gray-400', className)} />;
}
