import { deriveTaskExecutionPhase, getTaskExecutionDisplay } from '@/utils/task-execution-phase';

describe('task-execution-phase', () => {
  it('should prefer statusPhase when provided', () => {
    expect(
      deriveTaskExecutionPhase({ status: 'RUNNING', progress: 0, statusPhase: 'pulling_image' })
    ).toBe('pulling_image');
  });

  it('should not infer detailed phases from progress when statusPhase is missing', () => {
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 0 })).toBe('executing');
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 20 })).toBe('executing');
    expect(deriveTaskExecutionPhase({ status: 'RUNNING', progress: 100 })).toBe('executing');
  });

  it('should handle terminal and non-running statuses', () => {
    expect(deriveTaskExecutionPhase({ status: 'PENDING', progress: 0 })).toBe('queued');
    expect(deriveTaskExecutionPhase({ status: 'FAILED', progress: 10 })).toBe('failed');
    expect(deriveTaskExecutionPhase({ status: 'COMPLETED', progress: 10 })).toBe('completed');
    expect(deriveTaskExecutionPhase({ status: 'CANCELLING', progress: 10 })).toBe('cancelled');
  });

  it('should return stable labelKey and progress', () => {
    const display = getTaskExecutionDisplay({ status: 'RUNNING', progress: 15 });
    expect(display.phase).toBe('executing');
    expect(display.labelKey).toBe('chat:messages.phase_executing');
    expect(display.progress).toBe(15);
    expect(display.showProgress).toBe(false);
  });
});
