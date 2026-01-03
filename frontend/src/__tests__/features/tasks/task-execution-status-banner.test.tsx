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

  it('should render real phase label for running tasks', () => {
    render(
      <TaskExecutionStatusBanner
        task={{
          status: 'RUNNING',
          progress: 15,
          status_phase: 'pulling_image',
          progress_text: null,
        }}
      />
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('chat:messages.phase_pulling_image')).toBeInTheDocument();
  });

  it('should render error details for failed tasks', () => {
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
        onRetry={jest.fn()}
      />
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('boom')).toBeInTheDocument();
  });
});
