import React, { useMemo, useState } from 'react';
import { Loader2, Clock, CheckCircle2, XCircle, Ban } from 'lucide-react';

import type { TaskStatus } from '@/types/api';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/hooks/useTranslation';
import { isTaskActiveStatus } from '@/utils/taskStatus';
import { getTaskExecutionDisplay, type TaskExecutionIcon } from '@/utils/task-execution-phase';
import { useTaskPhaseTimeline } from '@/hooks/use-task-phase-timeline';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

type TaskExecutionStatusBannerProps = {
  task: {
    id?: number | null;
    status: TaskStatus;
    progress?: number | null;
    status_phase?: string | null;
    progress_text?: string | null;
    error_message?: string | null;
    updated_at?: string | null;
    completed_at?: string | null;
  } | null;
  retryMessage?: { content: string; type: string; error?: string; subtaskId?: number } | null;
  onRetry?: (message: {
    content: string;
    type: string;
    error?: string;
    subtaskId?: number;
  }) => void;
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

export function TaskExecutionStatusBanner({
  task,
  retryMessage,
  onRetry,
}: TaskExecutionStatusBannerProps) {
  const { t } = useTranslation();

  const [isErrorDialogOpen, setIsErrorDialogOpen] = useState(false);
  const shouldShow = Boolean(task && (isTaskActiveStatus(task.status) || task.status === 'FAILED'));

  const displayForTimeline = useMemo(() => {
    const status = (task?.status ?? 'PENDING') as TaskStatus;
    return getTaskExecutionDisplay({
      status,
      progress: task?.progress,
      statusPhase: task?.status_phase ?? null,
    });
  }, [task?.progress, task?.status, task?.status_phase]);

  const stageId = task
    ? ((task.progress_text?.trim() ? task.progress_text.trim() : null) ??
      (task.status_phase?.trim() ? task.status_phase.trim() : null) ??
      displayForTimeline.phase)
    : null;

  const stageLabelForTimeline = task
    ? task.progress_text?.trim()
      ? task.progress_text
      : task.status === 'CANCELLING'
        ? t('chat:messages.status_cancelling')
        : t(displayForTimeline.labelKey) || t('chat:messages.status_running')
    : null;

  const eventAtMs = (() => {
    const parsed = task?.updated_at ? Date.parse(task.updated_at) : Number.NaN;
    return Number.isFinite(parsed) ? parsed : Date.now();
  })();

  const terminalAtMs = (() => {
    const parsed = task?.completed_at ? Date.parse(task.completed_at) : Number.NaN;
    return Number.isFinite(parsed) ? parsed : null;
  })();

  const isTerminal = Boolean(
    task && (task.status === 'COMPLETED' || task.status === 'FAILED' || task.status === 'CANCELLED')
  );

  const { timeline, nowMs } = useTaskPhaseTimeline({
    taskId: task?.id ?? null,
    stageId,
    stageLabel: stageLabelForTimeline,
    eventAtMs,
    isTerminal,
    terminalAtMs,
  });

  if (!shouldShow || !task) return null;

  const display = getTaskExecutionDisplay({
    status: task.status,
    progress: task.progress,
    statusPhase: task.status_phase,
  });

  const Icon = ICONS[display.icon];
  const title = task.progress_text?.trim()
    ? task.progress_text
    : task.status === 'CANCELLING'
      ? t('chat:messages.status_cancelling')
      : t(display.labelKey) || t('chat:messages.status_running');

  const errorDetail =
    task.status !== 'FAILED'
      ? null
      : task.error_message ||
        retryMessage?.error ||
        t('chat:messages.unknown_error') ||
        t('chat:status.error') ||
        'Unknown error';

  const formatSeconds = (ms: number) => {
    const seconds = Math.max(0, Math.floor(ms / 1000));
    return t('chat:messages.phase_elapsed', { seconds }) || `${seconds}s`;
  };

  const renderedTimeline = timeline.length > 0 ? timeline.slice(-8) : [];

  return (
    <Alert variant={getAlertVariant(display.phase)} className="mb-4">
      <Icon
        className={cn('h-4 w-4', display.icon === 'spinner' && 'animate-spin')}
        aria-hidden="true"
      />
      <div>
        <AlertTitle className="mb-0">{title}</AlertTitle>
        <AlertDescription className="mt-2">
          {renderedTimeline.length > 0 && (
            <div className="text-xs tabular-nums text-muted-foreground">
              {formatSeconds(nowMs - renderedTimeline[renderedTimeline.length - 1].startedAtMs)}
            </div>
          )}
          {task.status === 'FAILED' && (
            <div className="mt-3">
              {errorDetail && (
                <p className="text-sm text-muted-foreground line-clamp-2 break-words">
                  {errorDetail}
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {retryMessage && onRetry && retryMessage.subtaskId && (
                  <Button size="sm" onClick={() => onRetry(retryMessage)}>
                    {t('chat:actions.retry')}
                  </Button>
                )}
                <Button size="sm" variant="outline" onClick={() => setIsErrorDialogOpen(true)}>
                  {t('chat:actions.view_error')}
                </Button>
              </div>
            </div>
          )}
        </AlertDescription>
      </div>

      {task.status === 'FAILED' && errorDetail && (
        <AlertDialog open={isErrorDialogOpen} onOpenChange={setIsErrorDialogOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{t('chat:messages.phase_failed')}</AlertDialogTitle>
              <AlertDialogDescription>
                <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted/40 p-3">
                  {errorDetail}
                </pre>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <Button variant="outline" onClick={() => setIsErrorDialogOpen(false)}>
                {t('common:actions.close') || 'Close'}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </Alert>
  );
}
