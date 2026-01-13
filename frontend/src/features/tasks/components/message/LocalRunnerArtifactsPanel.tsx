// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

type Artifact = {
  id: number;
  filename: string;
  file_size?: number;
  mime_type?: string;
  download_url?: string;
};

type LocalRunnerResult = {
  runner_id?: string;
  workspace_id?: string;
  changed_files?: string[];
  artifacts?: Artifact[];
  patch?: {
    text?: Artifact | null;
    binary?: Artifact | null;
  };
  git_pre?: Record<string, unknown>;
  git_post?: Record<string, unknown>;
};

function isArtifact(value: unknown): value is Artifact {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const record = value as Record<string, unknown>;
  return typeof record.filename === 'string' && typeof record.id === 'number';
}

function formatBytes(size?: number): string {
  if (!size || size <= 0) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export default function LocalRunnerArtifactsPanel({
  localRunner: localRunnerRaw,
  t,
}: {
  localRunner: unknown;
  t: (key: string) => string;
}) {
  const localRunner = useMemo<LocalRunnerResult>(() => {
    if (!localRunnerRaw || typeof localRunnerRaw !== 'object' || Array.isArray(localRunnerRaw))
      return {};
    return localRunnerRaw as LocalRunnerResult;
  }, [localRunnerRaw]);
  const [open, setOpen] = useState(false);
  const [patchPreview, setPatchPreview] = useState<string | null>(null);
  const [patchLoading, setPatchLoading] = useState(false);

  const artifacts = useMemo(() => {
    return Array.isArray(localRunner.artifacts) ? localRunner.artifacts.filter(isArtifact) : [];
  }, [localRunner.artifacts]);

  const patchText = isArtifact(localRunner.patch?.text) ? localRunner.patch?.text : null;
  const patchBinary = isArtifact(localRunner.patch?.binary) ? localRunner.patch?.binary : null;

  const hasAnything = artifacts.length > 0 || !!patchText || !!patchBinary;
  if (!hasAnything) return null;

  const toggle = () => setOpen(v => !v);

  const fetchPatchPreview = async () => {
    if (!patchText?.download_url) return;
    try {
      setPatchLoading(true);
      const res = await fetch(patchText.download_url);
      const text = await res.text();
      setPatchPreview(text);
    } finally {
      setPatchLoading(false);
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-border bg-surface px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-text-primary">
            {t('chat:local_runner_placeholder')}
          </span>
          <Badge variant="secondary" className="truncate">
            {localRunner.runner_id || '-'} / {localRunner.workspace_id || '-'}
          </Badge>
        </div>
        <Button variant="ghost" size="sm" onClick={toggle}>
          {open ? t('chat:messages.collapse_content') : t('chat:messages.expand_content')}
        </Button>
      </div>

      {open && (
        <div className="mt-2 space-y-2">
          {(patchText || patchBinary) && (
            <div className="flex flex-col gap-1">
              <div className="text-xs text-text-muted">{t('chat:messages.result')}</div>
              <div className="flex flex-wrap items-center gap-2">
                {patchText?.download_url && (
                  <a
                    className="text-sm text-primary underline underline-offset-2"
                    href={patchText.download_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    patch.diff {formatBytes(patchText.file_size)}
                  </a>
                )}
                {patchBinary?.download_url && (
                  <a
                    className="text-sm text-primary underline underline-offset-2"
                    href={patchBinary.download_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    patch.diffbin {formatBytes(patchBinary.file_size)}
                  </a>
                )}
                {patchText?.download_url && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (patchPreview !== null) setPatchPreview(null);
                      else fetchPatchPreview();
                    }}
                    disabled={patchLoading}
                  >
                    {patchPreview !== null
                      ? t('chat:messages.collapse_content')
                      : t('chat:messages.expand_content')}
                  </Button>
                )}
              </div>
              {patchPreview !== null && (
                <pre className="max-h-[260px] overflow-auto rounded-md bg-base p-2 text-xs whitespace-pre-wrap">
                  {patchPreview}
                </pre>
              )}
            </div>
          )}

          {artifacts.length > 0 && (
            <div className="flex flex-col gap-1">
              <div className="text-xs text-text-muted">{t('chat:messages.download')}</div>
              <div className="flex flex-col gap-1">
                {artifacts.map(a => (
                  <a
                    key={a.id}
                    className="text-sm text-primary underline underline-offset-2"
                    href={a.download_url || '#'}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {a.filename} {formatBytes(a.file_size)}
                  </a>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(localRunner.changed_files) && localRunner.changed_files.length > 0 && (
            <div className="flex flex-col gap-1">
              <div className="text-xs text-text-muted">changed_files</div>
              <div className="text-xs text-text-muted whitespace-pre-wrap">
                {localRunner.changed_files.slice(0, 20).join('\n')}
                {localRunner.changed_files.length > 20 ? '\n…' : ''}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
