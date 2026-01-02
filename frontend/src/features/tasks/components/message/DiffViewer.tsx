// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import { useMemo, useState, useEffect } from 'react';
import { ChevronDownIcon, ChevronRightIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { BranchDiffResponse, GitDiffFile } from '@/apis/tasks';
import { useTranslation } from '@/hooks/useTranslation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tag } from '@/components/ui/tag';
import { cn } from '@/lib/utils';

interface FileChange {
  old_path: string;
  new_path: string;
  new_file: boolean;
  renamed_file: boolean;
  deleted_file: boolean;
  added_lines: number;
  removed_lines: number;
  diff_title: string;
}

interface DiffViewerProps {
  diffData: BranchDiffResponse | null;
  isLoading?: boolean;
  gitType: 'github' | 'gitlab';
  fileChanges?: FileChange[];
  showDiffContent?: boolean;
}

interface DiffFile {
  filename: string;
  status: 'added' | 'removed' | 'modified' | 'renamed';
  additions: number;
  deletions: number;
  changes: number;
  diff: string;
  oldPath?: string;
  newPath?: string;
  isExpanded: boolean;
}

function _getStatusIcon(status: string) {
  const iconClasses = 'w-4 h-4';
  switch (status) {
    case 'added':
      return <DocumentTextIcon className={`${iconClasses} text-success`} />;
    case 'removed':
      return <DocumentTextIcon className={`${iconClasses} text-error`} />;
    case 'modified':
      return <DocumentTextIcon className={`${iconClasses} text-primary`} />;
    case 'renamed':
      return <DocumentTextIcon className={`${iconClasses} text-text-secondary`} />;
    default:
      return <DocumentTextIcon className={`${iconClasses} text-text-muted`} />;
  }
}

function normalizeFileChanges(fileChanges: FileChange[]): DiffFile[] {
  return fileChanges.map(change => ({
    filename: change.new_path,
    status: change.new_file
      ? 'added'
      : change.deleted_file
        ? 'removed'
        : change.renamed_file
          ? 'renamed'
          : 'modified',
    additions: change.added_lines,
    deletions: change.removed_lines,
    changes: change.added_lines + change.removed_lines,
    diff: '',
    oldPath: change.old_path,
    newPath: change.new_path,
    isExpanded: false,
  }));
}

function normalizeGitFiles(files: GitDiffFile[]): DiffFile[] {
  return files.map(file => ({
    filename: file.filename,
    status:
      file.status === 'added'
        ? 'added'
        : file.status === 'removed'
          ? 'removed'
          : file.status === 'renamed'
            ? 'renamed'
            : 'modified',
    additions: file.additions,
    deletions: file.deletions,
    changes: file.changes,
    diff: file.patch,
    oldPath: file.previous_filename,
    newPath: file.filename,
    isExpanded: false,
  }));
}

function renderDiffContent(diff: string) {
  if (!diff) return null;

  const lines = diff.split(/\r?\n/);
  return lines.map((line, index) => {
    const isHunk = line.startsWith('@@');
    const isMeta =
      line.startsWith('diff ') ||
      line.startsWith('index ') ||
      line.startsWith('+++') ||
      line.startsWith('---') ||
      line.startsWith('new file mode') ||
      line.startsWith('deleted file mode') ||
      line.startsWith('rename from') ||
      line.startsWith('rename to');

    const isAdd = !isHunk && !isMeta && line.startsWith('+');
    const isRemove = !isHunk && !isMeta && line.startsWith('-');
    const isContext = !isHunk && !isMeta && line.startsWith(' ');

    const prefix = isAdd ? '+' : isRemove ? '-' : isContext ? ' ' : '';
    const content = prefix ? line.slice(1) : line;

    const lineClass = cn(
      'text-text-primary',
      isMeta && 'text-text-muted bg-muted/30',
      isHunk && 'text-text-secondary bg-muted/40',
      isAdd && 'text-success bg-success/10',
      isRemove && 'text-error bg-error/10',
      isContext && 'text-text-secondary'
    );

    return (
      <div key={index} className={cn('flex text-xs font-mono', lineClass)}>
        <span className="w-8 flex-shrink-0 text-right pr-2 select-none opacity-50">
          {index + 1}
        </span>
        <span className="flex-shrink-0 w-4 text-right pr-2 select-none">{prefix}</span>
        <span className="flex-1 whitespace-pre break-words">{content}</span>
      </div>
    );
  });
}

export default function DiffViewer({
  diffData,
  isLoading = false,
  fileChanges,
  showDiffContent = true,
}: DiffViewerProps) {
  const [diffFiles, setDiffFiles] = useState<DiffFile[]>([]);
  const [fileQuery, setFileQuery] = useState('');
  const { t } = useTranslation();

  // Normalize diff data when it changes
  useEffect(() => {
    if (fileChanges && fileChanges.length > 0) {
      // Use simple file changes without diff content
      setDiffFiles(normalizeFileChanges(fileChanges));
    } else if (diffData) {
      if (diffData.files) {
        setDiffFiles(normalizeGitFiles(diffData.files));
      }
    }
  }, [diffData, fileChanges]);

  const toggleFile = (index: number) => {
    setDiffFiles(prev =>
      prev.map((file, i) => (i === index ? { ...file, isExpanded: !file.isExpanded } : file))
    );
  };

  const filteredEntries = useMemo(() => {
    const q = fileQuery.trim().toLowerCase();
    return diffFiles
      .map((file, index) => ({ file, index }))
      .filter(({ file }) => (q ? file.filename.toLowerCase().includes(q) : true));
  }, [diffFiles, fileQuery]);

  const visibleFiles = useMemo(() => filteredEntries.map(e => e.file), [filteredEntries]);
  const expandableIndices = useMemo(
    () => filteredEntries.filter(e => Boolean(e.file.diff)).map(e => e.index),
    [filteredEntries]
  );
  const expandAllVisible = (expanded: boolean) => {
    const set = new Set(expandableIndices);
    setDiffFiles(prev =>
      prev.map((file, i) => (set.has(i) ? { ...file, isExpanded: expanded } : file))
    );
  };

  const totalAdditions = visibleFiles.reduce((sum, file) => sum + file.additions, 0);
  const totalDeletions = visibleFiles.reduce((sum, file) => sum + file.deletions, 0);
  const totalChanges = visibleFiles.reduce((sum, file) => sum + file.changes, 0);
  const allExpanded =
    expandableIndices.length > 0 && expandableIndices.every(i => Boolean(diffFiles[i]?.isExpanded));
  const hasDiffContent = visibleFiles.some(file => Boolean(file.diff));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        <span className="ml-3 text-text-muted">{t('tasks:workbench.loading_diff_message')}</span>
      </div>
    );
  }

  if ((!diffData && !fileChanges) || diffFiles.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-surface p-8 text-center">
        <p className="text-text-muted">{t('tasks:workbench.no_changes_found')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary - only show if we have detailed diff data */}
      <Card padding="sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-text-muted">
                {t('tasks:workbench.changes')}:
              </span>
              <span className="text-sm font-semibold text-text-primary">{totalChanges}</span>
            </div>
            {totalAdditions > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-success">
                  {t('tasks:workbench.additions')}:
                </span>
                <span className="text-sm font-semibold text-success">+{totalAdditions}</span>
              </div>
            )}
            {totalDeletions > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-error">
                  {t('tasks:workbench.deletions')}:
                </span>
                <span className="text-sm font-semibold text-error">-{totalDeletions}</span>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
            <div className="w-full sm:w-72">
              <Input
                value={fileQuery}
                onChange={e => setFileQuery(e.target.value)}
                placeholder={t('tasks:workbench.filter_files_placeholder') || 'Filter files...'}
              />
            </div>
            {showDiffContent && hasDiffContent && (
              <Button size="sm" variant="outline" onClick={() => expandAllVisible(!allExpanded)}>
                {allExpanded ? t('tasks:workbench.collapse_all') : t('tasks:workbench.expand_all')}
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Files */}
      <div className="space-y-2">
        {filteredEntries.length === 0 ? (
          <div className="rounded-lg border border-border bg-surface p-8 text-center">
            <p className="text-text-muted">
              {t('tasks:workbench.no_matching_files') || 'No matching files'}
            </p>
            {fileQuery.trim() && (
              <div className="mt-4 flex justify-center">
                <Button size="sm" variant="outline" onClick={() => setFileQuery('')}>
                  {t('common:actions.reset') || 'Reset'}
                </Button>
              </div>
            )}
          </div>
        ) : (
          filteredEntries.map(({ file, index }) => {
            const totalFileChanges = file.additions + file.deletions;
            const addedPercent =
              totalFileChanges > 0 ? (file.additions / totalFileChanges) * 100 : 0;
            const removedPercent =
              totalFileChanges > 0 ? (file.deletions / totalFileChanges) * 100 : 0;
            const isToggleable = Boolean(showDiffContent && file.diff);

            return (
              <div
                key={index}
                className="border border-border rounded-lg overflow-hidden bg-surface"
              >
                {/* File header */}
                <button
                  type="button"
                  className={cn(
                    'flex w-full items-center justify-between p-3 bg-muted/40 transition-colors text-left',
                    isToggleable && 'hover:bg-muted/70 cursor-pointer'
                  )}
                  onClick={() => isToggleable && toggleFile(index)}
                  aria-expanded={isToggleable ? file.isExpanded : undefined}
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {/* File path */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="flex-shrink-0">{_getStatusIcon(file.status)}</span>
                        <span className="text-sm font-mono text-text-primary truncate">
                          {file.filename}
                        </span>
                        {file.status === 'added' && (
                          <Tag variant="success">{t('tasks:workbench.file_status.new')}</Tag>
                        )}
                        {file.status === 'removed' && (
                          <Tag variant="error">{t('tasks:workbench.file_status.deleted')}</Tag>
                        )}
                        {file.status === 'renamed' && (
                          <Tag variant="info">{t('tasks:workbench.file_status.renamed')}</Tag>
                        )}
                      </div>
                    </div>

                    {/* Stats */}
                    <div className="flex items-center gap-3 flex-shrink-0">
                      {/* Added/Removed lines */}
                      <div className="flex items-center gap-2 text-sm font-mono">
                        {file.additions > 0 && (
                          <span className="text-success">+{file.additions}</span>
                        )}
                        {file.deletions > 0 && (
                          <span className="text-error">-{file.deletions}</span>
                        )}
                      </div>

                      {/* Visual bar */}
                      <div className="flex items-center gap-0.5 w-20">
                        {totalFileChanges > 0 && (
                          <>
                            {/* Green bars for additions */}
                            {Array.from({ length: Math.ceil(addedPercent / 20) }).map((_, i) => (
                              <div key={`add-${i}`} className="h-2 w-2 rounded-sm bg-success" />
                            ))}
                            {/* Red bars for deletions */}
                            {Array.from({ length: Math.ceil(removedPercent / 20) }).map((_, i) => (
                              <div key={`del-${i}`} className="h-2 w-2 rounded-sm bg-error" />
                            ))}
                            {/* Gray bars to fill remaining space */}
                            {Array.from({
                              length: Math.max(
                                0,
                                5 - Math.ceil(addedPercent / 20) - Math.ceil(removedPercent / 20)
                              ),
                            }).map((_, i) => (
                              <div key={`empty-${i}`} className="h-2 w-2 rounded-sm bg-border" />
                            ))}
                          </>
                        )}
                      </div>

                      {/* Expand/collapse icon - only show if diff content is available */}
                      {isToggleable && (
                        <>
                          {file.isExpanded ? (
                            <ChevronDownIcon className="w-4 h-4 text-text-muted" />
                          ) : (
                            <ChevronRightIcon className="w-4 h-4 text-text-muted" />
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </button>

                {/* Diff content - only show if available and expanded */}
                {showDiffContent && file.isExpanded && file.diff && (
                  <div className="border-t border-border bg-surface">
                    <div className="p-4 overflow-auto max-h-[60vh]">
                      <div className="inline-block min-w-full">{renderDiffContent(file.diff)}</div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
