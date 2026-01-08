import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import MessageBubble from '@/features/tasks/components/message/MessageBubble';
import { TooltipProvider } from '@/components/ui/tooltip';

const toastMock = jest.fn();
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: toastMock }),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const traceEventMock = jest.fn();
const traceCopyMock = jest.fn();
const traceDownloadMock = jest.fn();
jest.mock('@/hooks/useTraceAction', () => ({
  useTraceAction: () => ({
    trace: {
      event: traceEventMock,
      copy: traceCopyMock,
      download: traceDownloadMock,
    },
  }),
}));

jest.mock('@/hooks/useMessageFeedback', () => ({
  useMessageFeedback: () => ({
    feedback: null,
    handleLike: jest.fn(),
    handleDislike: jest.fn(),
    clearFeedback: jest.fn(),
  }),
}));

jest.mock('@uiw/react-markdown-editor', () => ({
  __esModule: true,
  default: {
    Markdown: ({ source }: { source: string }) => <div>{source}</div>,
  },
}));

jest.mock('@/components/common/MarkdownWithMermaid', () => ({
  __esModule: true,
  default: ({ source }: { source: string }) => <div>{source}</div>,
}));

function renderMessageBubble(
  msg: React.ComponentProps<typeof MessageBubble>['msg'],
  onRetry?: React.ComponentProps<typeof MessageBubble>['onRetry']
) {
  const t = () => '';
  return render(
    <TooltipProvider>
      <MessageBubble
        msg={msg}
        index={0}
        selectedTaskDetail={null}
        theme="light"
        t={t}
        onRetry={onRetry}
      />
    </TooltipProvider>
  );
}

describe('MessageBubble code shell retry', () => {
  beforeEach(() => {
    toastMock.mockClear();
  });

  it('calls onRetry with retryMode for Code Shell messages', () => {
    const onRetry = jest.fn();
    const msg: React.ComponentProps<typeof MessageBubble>['msg'] = {
      type: 'ai',
      content: '',
      timestamp: Date.now(),
      status: 'error',
      error: 'boom',
      subtaskId: 101,
      botName: 'Codex Bot',
      result: { shell_type: 'Codex', resume_session_id: 'thread_123' },
    };

    renderMessageBubble(msg, onRetry);

    fireEvent.click(screen.getByRole('button', { name: 'Resume 重试' }));
    fireEvent.click(screen.getByRole('button', { name: '新会话重试' }));

    expect(onRetry).toHaveBeenCalledTimes(2);
    expect(onRetry.mock.calls[0]?.[1]).toBe('resume');
    expect(onRetry.mock.calls[1]?.[1]).toBe('new_session');
  });

  it('blocks Codex resume retry when resume_session_id is missing', () => {
    const onRetry = jest.fn();
    const msg: React.ComponentProps<typeof MessageBubble>['msg'] = {
      type: 'ai',
      content: '',
      timestamp: Date.now(),
      status: 'error',
      error: 'boom',
      subtaskId: 102,
      botName: 'Codex Bot',
      result: { shell_type: 'Codex' },
    };

    renderMessageBubble(msg, onRetry);

    fireEvent.click(screen.getByRole('button', { name: 'Resume 重试' }));

    expect(onRetry).not.toHaveBeenCalled();
    expect(toastMock).toHaveBeenCalledTimes(1);
  });
});
