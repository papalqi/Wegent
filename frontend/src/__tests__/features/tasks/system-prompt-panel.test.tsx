import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import type { Team } from '@/types/api';
import SystemPromptPanel from '@/features/tasks/components/chat/SystemPromptPanel';

const mockTeam: Team = {
  id: 1,
  name: 'Demo Team',
  description: 'Demo',
  bots: [
    {
      bot_id: 1,
      bot_prompt: 'You are a helpful assistant.',
      role: 'assistant',
      bot: {},
    },
  ],
  workflow: {},
  is_active: true,
  user_id: 1,
  created_at: '2026-01-02T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
};

describe('SystemPromptPanel', () => {
  it('should render nothing when team is null', () => {
    const { container } = render(<SystemPromptPanel team={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('should toggle open and show copy button', () => {
    render(<SystemPromptPanel team={mockTeam} />);

    const trigger = screen.getByRole('button', { name: 'chat:settings.system_prompt' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');

    expect(screen.getByRole('button', { name: 'chat:actions.copy' })).toBeInTheDocument();
  });
});
