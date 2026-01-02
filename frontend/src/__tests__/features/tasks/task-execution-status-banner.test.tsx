import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

import { TaskExecutionStatusBanner } from '@/features/tasks/components/chat/TaskExecutionStatusBanner';

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('TaskExecutionStatusBanner', () => {
  it('should render nothing when task is null', () => {
    const { container } = render(<TaskExecutionStatusBanner task={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('should render phase label and progressbar for running tasks', () => {
    render(
      <TaskExecutionStatusBanner
        task={{
          status: 'RUNNING',
          progress: 15,
          status_phase: null,
          progress_text: null,
        }}
      />
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('chat:messages.phase_booting_executor')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should render retry and view error actions for failed tasks', () => {
    const onRetry = jest.fn();

    render(
      <TaskExecutionStatusBanner
        task={{
          status: 'FAILED',
          progress: 0,
          status_phase: null,
          progress_text: null,
          error_message: 'boom',
        }}
        retryMessage={{ content: 'x', type: 'ai', error: 'boom', subtaskId: 1 }}
        onRetry={onRetry}
      />
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('chat:actions.retry')).toBeInTheDocument();
    expect(screen.getByText('chat:actions.view_error')).toBeInTheDocument();

    fireEvent.click(screen.getByText('chat:actions.retry'));
    expect(onRetry).toHaveBeenCalled();
  });
});
