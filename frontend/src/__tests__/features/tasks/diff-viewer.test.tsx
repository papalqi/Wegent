import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import DiffViewer from '@/features/tasks/components/message/DiffViewer';

describe('DiffViewer', () => {
  it('should filter file list by query', () => {
    render(
      <DiffViewer
        diffData={null}
        isLoading={false}
        gitType="github"
        showDiffContent={false}
        fileChanges={[
          {
            old_path: 'src/a.ts',
            new_path: 'src/a.ts',
            new_file: false,
            renamed_file: false,
            deleted_file: false,
            added_lines: 1,
            removed_lines: 0,
            diff_title: 'a',
          },
          {
            old_path: 'src/b.ts',
            new_path: 'src/b.ts',
            new_file: false,
            renamed_file: false,
            deleted_file: false,
            added_lines: 0,
            removed_lines: 1,
            diff_title: 'b',
          },
        ]}
      />
    );

    expect(screen.getByText('src/a.ts')).toBeInTheDocument();
    expect(screen.getByText('src/b.ts')).toBeInTheDocument();

    const input = screen.getByPlaceholderText('tasks:workbench.filter_files_placeholder');
    fireEvent.change(input, { target: { value: 'b.ts' } });

    expect(screen.queryByText('src/a.ts')).not.toBeInTheDocument();
    expect(screen.getByText('src/b.ts')).toBeInTheDocument();

    fireEvent.change(input, { target: { value: 'nope' } });
    expect(screen.getByText('tasks:workbench.no_matching_files')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'common:actions.reset' })).toBeInTheDocument();
  });
});
