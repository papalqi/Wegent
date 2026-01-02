import { deriveTaskExecutionPhase, getTaskExecutionDisplay } from '@/utils/task-execution-phase';

describe('task-execution-phase', () => {
  it('should prefer statusPhase when provided', () => {
    expect(
      deriveTaskExecutionPhase({ status: 'RUNNING', progress: 0, statusPhase: 'pulling_image' })
    ).toBe('pulling_image');
  });

  it('should derive phase from progress when statusPhase is missing', () => {
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 0 })).toBe('booting_executor');
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 20 })).toBe('pulling_image');
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 40 })).toBe('loading_skills');
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 60 })).toBe('executing');
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 90 })).toBe('syncing');
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 100 })).toBe('completed');
  });

  it('should handle terminal and non-running statuses', () => {
    expect(deriveTaskExecutionPhase({ status: 'PENDING', progress: 0 })).toBe('queued');
    expect(deriveTaskExecutionPhase({ status: 'FAILED', progress: 10 })).toBe('failed');
    expect(deriveTaskExecutionPhase({ status: 'COMPLETED', progress: 10 })).toBe('completed');
    expect(deriveTaskExecutionPhase({ status: 'CANCELLING', progress: 10 })).toBe('cancelled');
  });

  it('should return stable labelKey and progress', () => {
    const display = getTaskExecutionDisplay({ status: 'RUNNING', progress: 15 });
    expect(display.phase).toBe('booting_executor');
    expect(display.labelKey).toBe('chat:messages.phase_booting_executor');
    expect(display.progress).toBe(15);
    expect(display.showProgress).toBe(true);
  });
});
