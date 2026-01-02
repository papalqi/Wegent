import React from 'react';
import { Loader2, Clock, CheckCircle2, XCircle, Ban } from 'lucide-react';

import type { TaskStatus } from '@/types/api';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/hooks/useTranslation';
import { isTaskActiveStatus } from '@/utils/taskStatus';
import { getTaskExecutionDisplay, type TaskExecutionIcon } from '@/utils/task-execution-phase';

type TaskExecutionStatusBannerProps = {
  task: {
    status: TaskStatus;
    progress: number;
    status_phase?: string | null;
    progress_text?: string | null;
  } | null;
};

const ICONS: Record<TaskExecutionIcon, React.ComponentType<{ className?: string }>> = {
  spinner: Loader2,
  clock: Clock,
  check: CheckCircle2,
  x: XCircle,
  ban: Ban,
};

function getAlertVariant(phase: string): React.ComponentProps<typeof Alert>['variant'] {
  if (phase === 'failed') return 'destructive';
  if (phase === 'completed') return 'success';
  if (phase === 'cancelled') return 'warning';
  return 'default';
}

export function TaskExecutionStatusBanner({ task }: TaskExecutionStatusBannerProps) {
  const { t } = useTranslation();

  if (!task || !isTaskActiveStatus(task.status)) return null;

  const display = getTaskExecutionDisplay({
    status: task.status,
    progress: task.progress,
    statusPhase: task.status_phase,
  });

  const Icon = ICONS[display.icon];
  const title = t(display.labelKey) || task.progress_text || t('chat:messages.status_running');
  const progressValue = display.showProgress ? Math.max(display.progress, 3) : display.progress;

  return (
    <Alert variant={getAlertVariant(display.phase)} className="mb-4">
      <Icon
        className={cn('h-4 w-4', display.icon === 'spinner' && 'animate-spin')}
        aria-hidden="true"
      />
      <div>
        <AlertTitle className="mb-0">{title}</AlertTitle>
        {display.showProgress && (
          <AlertDescription className="mt-2">
            <Progress value={progressValue} className="h-1.5" />
          </AlertDescription>
        )}
      </div>
    </Alert>
  );
}
