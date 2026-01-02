import React, { useState } from 'react';
import { Loader2, Clock, CheckCircle2, XCircle, Ban } from 'lucide-react';

import type { TaskStatus } from '@/types/api';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/hooks/useTranslation';
import { isTaskActiveStatus } from '@/utils/taskStatus';
import { getTaskExecutionDisplay, type TaskExecutionIcon } from '@/utils/task-execution-phase';
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
    status: TaskStatus;
    progress?: number | null;
    status_phase?: string | null;
    progress_text?: string | null;
    error_message?: string | null;
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
  if (!shouldShow || !task) return null;

  const display = getTaskExecutionDisplay({
    status: task.status,
    progress: task.progress,
    statusPhase: task.status_phase,
  });

  const Icon = ICONS[display.icon];
  const title =
    task.status === 'CANCELLING'
      ? t('chat:messages.status_cancelling')
      : t(display.labelKey) || task.progress_text || t('chat:messages.status_running');
  const progressValue = display.showProgress ? Math.max(display.progress, 3) : display.progress;

  const errorDetail =
    task.status !== 'FAILED'
      ? null
      : task.error_message ||
        retryMessage?.error ||
        t('chat:messages.unknown_error') ||
        t('chat:status.error') ||
        'Unknown error';

  return (
    <Alert variant={getAlertVariant(display.phase)} className="mb-4">
      <Icon
        className={cn('h-4 w-4', display.icon === 'spinner' && 'animate-spin')}
        aria-hidden="true"
      />
      <div>
        <AlertTitle className="mb-0">{title}</AlertTitle>
        <AlertDescription className={cn(display.showProgress ? 'mt-2' : 'mt-0')}>
          {display.showProgress && <Progress value={progressValue} className="h-1.5" />}
          {task.status === 'FAILED' && (
            <div className={cn(display.showProgress ? 'mt-3' : 'mt-2')}>
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
