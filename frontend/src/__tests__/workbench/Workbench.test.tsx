import React from 'react';
import { render, screen } from '@testing-library/react';

import Workbench from '@/features/tasks/components/workbench/Workbench';

jest.mock('@/features/theme/ThemeProvider', () => ({
  useTheme: () => ({ theme: 'light' }),
}));

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.mock('@uiw/react-markdown-editor', () => ({
  __esModule: true,
  default: {
    Markdown: ({ source }: { source: string }) => <div>{source}</div>,
  },
}));

jest.mock('@/apis/tasks', () => ({
  taskApis: {
    getBranchDiff: jest.fn(),
  },
}));

describe('Workbench', () => {
  it('clears cached overview when switching tasks without new workbench data', () => {
    const oldWorkbenchData = {
      taskTitle: 'Old Task',
      taskNumber: '37',
      status: 'completed',
      completedTime: '2026-01-01T00:00:00.000Z',
      repository: 'owner/repo',
      branch: 'main',
      sessions: 1,
      premiumRequests: 0,
      lastUpdated: '2026-01-01T00:00:00.000Z',
      summary: '',
      changes: [],
      originalPrompt: '',
      file_changes: [],
      git_info: {
        initial_commit_id: '',
        initial_commit_message: '',
        task_commits: [],
        source_branch: 'main',
        target_branch: '', // Prevent auto diff loading in test
      },
    } as const;

    const { rerender } = render(
      <Workbench
        isOpen
        onClose={() => {}}
        onOpen={() => {}}
        workbenchData={oldWorkbenchData}
        taskTitle="Old Task"
        taskNumber="#37"
        thinking={null}
      />
    );

    expect(screen.getByRole('heading', { name: 'Old Task' })).toBeInTheDocument();

    rerender(
      <Workbench
        isOpen
        onClose={() => {}}
        onOpen={() => {}}
        workbenchData={null}
        taskTitle="New Task"
        taskNumber="#43"
        thinking={null}
      />
    );

    expect(screen.queryByRole('heading', { name: 'Old Task' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'New Task' })).toBeInTheDocument();
  });
});
