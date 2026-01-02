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

    render(
      <TooltipProvider>
        <MessageDebugPanel data={data} t={t} />
      </TooltipProvider>
    );

    const button = screen.getByRole('button', { name: /调试（model=gpt-test · subtask=12）/ });
    expect(button).toBeInTheDocument();

    fireEvent.click(button);

    const compactPre = screen.getByText(/Key Fields/).parentElement?.querySelector('pre');
    expect(compactPre).not.toBeNull();
    expect(compactPre?.textContent).toContain('"model_id": "gpt-test"');
    expect(compactPre?.textContent).toContain('"subtask_id": 12');

    const fullJsonPre = screen.getByText(/Full JSON/).parentElement?.querySelector('pre');
    const text = fullJsonPre?.textContent || '';

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
