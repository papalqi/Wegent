// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useMemo } from 'react';
import { CopyButton } from './BubbleTools';
import { sanitizeDebugPayload, safePrettyJson } from '@/utils/debug-sanitize';

export type MessageDebugPayload = Record<string, unknown>;

function translateOrDefault(t: (key: string) => string, key: string, fallback: string): string {
  const v = t(key);
  return v === key ? fallback : v;
}

function getSummaryLabel(data: MessageDebugPayload | undefined): string | null {
  if (!data) return null;

  const model =
    (data.model_id as string | undefined) ||
    (data?.request && (data.request as Record<string, unknown>).model_id
      ? String((data.request as Record<string, unknown>).model_id)
      : undefined) ||
    (data?.wsPayload && (data.wsPayload as Record<string, unknown>).force_override_bot_model
      ? String((data.wsPayload as Record<string, unknown>).force_override_bot_model)
      : undefined);

  const subtaskId =
    (data.subtask_id as number | string | undefined) ||
    (data.subtaskId as number | string | undefined);

  const parts: string[] = [];
  if (model) parts.push(`model=${model}`);
  if (subtaskId !== undefined) parts.push(`subtask=${subtaskId}`);

  return parts.length > 0 ? parts.join(' · ') : null;
}

export default function MessageDebugPanel({
  data,
  t,
}: {
  data?: MessageDebugPayload;
  t: (key: string) => string;
}) {
  const sanitized = useMemo(() => {
    if (!data) return null;
    return sanitizeDebugPayload(data);
  }, [data]);

  const jsonText = useMemo(() => {
    if (!sanitized) return '';
    return safePrettyJson(sanitized);
  }, [sanitized]);

  const summary = useMemo(() => getSummaryLabel(data), [data]);

  if (!data) return null;

  const debugLabel = translateOrDefault(t, 'common:debug', '调试');
  const copyLabel = translateOrDefault(t, 'chat:actions.copy', 'Copy');

  return (
    <details className="mt-3 rounded-lg border border-border bg-surface/40">
      <summary className="flex items-center justify-between gap-2 px-3 py-2 text-xs text-text-muted cursor-pointer select-none">
        <span className="min-w-0 truncate">
          {debugLabel} {summary ? `（${summary}）` : ''}
        </span>
        <CopyButton
          content={jsonText}
          className="h-[26px] w-[26px] !rounded-full bg-fill-tert hover:!bg-fill-sec"
          tooltip={copyLabel}
        />
      </summary>
      <div className="px-3 pb-3">
        <pre className="max-h-80 overflow-auto rounded-md bg-muted/40 p-2 text-xs text-text-primary whitespace-pre-wrap break-words">
          {jsonText}
        </pre>
      </div>
    </details>
  );
}
