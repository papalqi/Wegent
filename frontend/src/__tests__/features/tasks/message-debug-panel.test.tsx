import { render, screen, fireEvent } from '@testing-library/react';
import MessageDebugPanel from '@/features/tasks/components/message/MessageDebugPanel';
import { TooltipProvider } from '@/components/ui/tooltip';

describe('MessageDebugPanel', () => {
  it('should render sanitized debug json and a summary label', () => {
    const data = {
      model_id: 'gpt-test',
      subtask_id: 12,
      api_key: 'sk-1234567890abcdef',
      message: 'hello',
    };

    const t = (key: string) => key;

    const { container } = render(
      <TooltipProvider>
        <MessageDebugPanel data={data} t={t} />
      </TooltipProvider>
    );

    expect(screen.getByText(/调试/)).toBeInTheDocument();
    expect(screen.getByText(/model=gpt-test/)).toBeInTheDocument();
    expect(screen.getByText(/subtask=12/)).toBeInTheDocument();

    const summary = container.querySelector('summary');
    expect(summary).not.toBeNull();
    fireEvent.click(summary as Element);

    const pre = container.querySelector('pre');
    expect(pre).not.toBeNull();
    const text = (pre as HTMLElement).textContent || '';

    expect(text).toContain('"model_id": "gpt-test"');
    expect(text).toContain('"subtask_id": 12');
    expect(text).toContain('"message": "hello"');

    expect(text).not.toContain('sk-1234567890abcdef');
    expect(text).toContain('"api_key":');
  });

  it('should render nothing when data is missing', () => {
    const t = (key: string) => key;
    const { container } = render(
      <TooltipProvider>
        <MessageDebugPanel t={t} />
      </TooltipProvider>
    );
    expect(container.firstChild).toBeNull();
  });
});
