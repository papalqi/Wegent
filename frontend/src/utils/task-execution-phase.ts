import type { TaskStatus } from '@/types/api';

export type TaskExecutionPhase =
  | 'queued'
  | 'booting_executor'
  | 'pulling_image'
  | 'loading_skills'
  | 'executing'
  | 'syncing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type TaskExecutionIcon = 'spinner' | 'clock' | 'check' | 'x' | 'ban';
export type TaskExecutionTone = 'primary' | 'info' | 'success' | 'danger' | 'muted';

export type TaskExecutionDisplay = {
  phase: TaskExecutionPhase;
  labelKey: string;
  icon: TaskExecutionIcon;
  tone: TaskExecutionTone;
  progress: number;
  showProgress: boolean;
};

const TASK_EXECUTION_PHASE_CONFIG: Record<
  TaskExecutionPhase,
  Pick<TaskExecutionDisplay, 'labelKey' | 'icon' | 'tone' | 'showProgress'>
> = {
  queued: {
    labelKey: 'chat:messages.phase_queued',
    icon: 'clock',
    tone: 'info',
    showProgress: false,
  },
  booting_executor: {
    labelKey: 'chat:messages.phase_booting_executor',
    icon: 'spinner',
    tone: 'primary',
    showProgress: true,
  },
  pulling_image: {
    labelKey: 'chat:messages.phase_pulling_image',
    icon: 'spinner',
    tone: 'primary',
    showProgress: true,
  },
  loading_skills: {
    labelKey: 'chat:messages.phase_loading_skills',
    icon: 'spinner',
    tone: 'primary',
    showProgress: true,
  },
  executing: {
    labelKey: 'chat:messages.phase_executing',
    icon: 'spinner',
    tone: 'primary',
    showProgress: true,
  },
  syncing: {
    labelKey: 'chat:messages.phase_syncing',
    icon: 'spinner',
    tone: 'primary',
    showProgress: true,
  },
  completed: {
    labelKey: 'chat:messages.phase_completed',
    icon: 'check',
    tone: 'success',
    showProgress: false,
  },
  failed: {
    labelKey: 'chat:messages.phase_failed',
    icon: 'x',
    tone: 'danger',
    showProgress: false,
  },
  cancelled: {
    labelKey: 'chat:messages.phase_cancelled',
    icon: 'ban',
    tone: 'muted',
    showProgress: false,
  },
};

function toKnownPhase(value: string | null | undefined): TaskExecutionPhase | null {
  if (!value) return null;
  const normalized = value.trim().toLowerCase();
  if (
    normalized === 'queued' ||
    normalized === 'booting_executor' ||
    normalized === 'pulling_image' ||
    normalized === 'loading_skills' ||
    normalized === 'executing' ||
    normalized === 'syncing' ||
    normalized === 'completed' ||
    normalized === 'failed' ||
    normalized === 'cancelled'
  ) {
    return normalized;
  }
  return null;
}

function clampProgress(progress: number | null | undefined): number {
  const p = Number.isFinite(progress) ? (progress as number) : 0;
  return Math.min(Math.max(p, 0), 100);
}

export function deriveTaskExecutionPhase(input: {
  status: TaskStatus;
  progress?: number | null;
  statusPhase?: string | null;
}): TaskExecutionPhase {
  const phaseFromServer = toKnownPhase(input.statusPhase);
  if (phaseFromServer) return phaseFromServer;

  const status = (input.status || 'PENDING').toUpperCase() as TaskStatus;
  if (status === 'PENDING') return 'queued';
  if (status === 'FAILED') return 'failed';
  if (status === 'CANCELLED' || status === 'CANCELLING') return 'cancelled';
  if (status === 'COMPLETED') return 'completed';
  if (status === 'RUNNING' || status === 'DELETE') return 'executing';
  return 'executing';
}

export function getTaskExecutionDisplay(input: {
  status: TaskStatus;
  progress?: number | null;
  statusPhase?: string | null;
}): TaskExecutionDisplay {
  const phase = deriveTaskExecutionPhase(input);
  const progress = clampProgress(input.progress);
  const config = TASK_EXECUTION_PHASE_CONFIG[phase];

  return {
    phase,
    progress,
    labelKey: config.labelKey,
    icon: config.icon,
    tone: config.tone,
    showProgress: false,
  };
}
