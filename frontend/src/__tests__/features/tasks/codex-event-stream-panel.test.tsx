import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import CodexEventStreamPanel from '@/features/tasks/components/message/CodexEventStreamPanel';
import { TooltipProvider } from '@/components/ui/tooltip';

describe('CodexEventStreamPanel', () => {
  it('should render and expand events', () => {
    const t = (key: string) => key;
    const events = [
      { type: 'item.completed', item: { type: 'agent_message', text: 'hello' } },
      { type: 'turn.failed', error: { message: 'boom' } },
    ];

    const { container } = render(
      <TooltipProvider>
        <CodexEventStreamPanel events={events} t={t} />
      </TooltipProvider>
    );
    expect(
      screen.getByText((content: string) => content.includes('chat:messages.codex_event_stream'))
    ).toBeInTheDocument();

    const outerSummary = container.querySelector('summary');
    expect(outerSummary).not.toBeNull();
    fireEvent.click(outerSummary as Element);

    expect(screen.getByText(/1\. item\.completed/)).toBeInTheDocument();
    expect(screen.getByText(/2\. turn\.failed/)).toBeInTheDocument();
  });
});
