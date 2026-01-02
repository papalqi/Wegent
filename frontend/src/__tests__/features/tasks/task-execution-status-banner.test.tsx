import React from 'react';
import { render, screen } from '@testing-library/react';

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

  it('should render nothing for failed tasks', () => {
    const { container } = render(
      <TaskExecutionStatusBanner
        task={{
          status: 'FAILED',
          progress: 0,
          status_phase: null,
          progress_text: null,
          error_message: 'boom',
        }}
        retryMessage={{ content: 'x', type: 'ai', error: 'boom', subtaskId: 1 }}
        onRetry={jest.fn()}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });
});
