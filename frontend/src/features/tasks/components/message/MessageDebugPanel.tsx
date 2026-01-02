// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useMemo } from 'react';
import { Bug } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
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

function summarizeTokens(value: unknown): unknown {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return value;
  const obj = value as Record<string, unknown>;
  const prompt = obj.prompt ?? obj.input ?? obj.input_tokens;
  const completion = obj.completion ?? obj.output ?? obj.output_tokens;
  const total = obj.total ?? obj.total_tokens ?? obj.all ?? obj.usage;

  const summary: Record<string, unknown> = {};
  if (prompt !== undefined) summary.prompt = prompt;
  if (completion !== undefined) summary.completion = completion;
  if (total !== undefined) summary.total = total;

  return Object.keys(summary).length > 0 ? summary : value;
}

function buildCompactDebug(data: MessageDebugPayload | undefined): Record<string, unknown> | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  const source = data as Record<string, unknown>;

  const compact: Record<string, unknown> = {};
  const pick = (key: string, value: unknown) => {
    if (value !== undefined && value !== null) {
      compact[key] = value;
    }
  };

  pick('model_id', source.model_id ?? source.modelId ?? source.model);
  pick('subtask_id', source.subtask_id ?? source.subtaskId);
  pick(
    'request_id',
    source.request_id ?? (source.request as Record<string, unknown> | undefined)?.id
  );
  pick(
    'trace_id',
    source.trace_id ?? (source.request as Record<string, unknown> | undefined)?.trace_id
  );
  pick('status', source.status ?? source.state);
  pick(
    'latency_ms',
    source.latency_ms ?? source.latency ?? source.duration_ms ?? source.elapsed_ms
  );
  pick('error', source.error);

  const tokens = source.tokens ?? source.token_usage ?? source.usage;
  if (tokens !== undefined) {
    pick('tokens', summarizeTokens(tokens));
  }

  return Object.keys(compact).length > 0 ? compact : null;
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

  const compactData = useMemo(() => buildCompactDebug(sanitized || undefined), [sanitized]);
  const compactJson = useMemo(
    () => (compactData ? safePrettyJson(compactData) : ''),
    [compactData]
  );
  const summary = useMemo(() => getSummaryLabel(data), [data]);

  if (!data) return null;

  const debugLabel = translateOrDefault(t, 'common:debug', '调试');
  const copyLabel = translateOrDefault(t, 'chat:actions.copy', 'Copy');
  const summaryLabel = summary ? `${debugLabel}（${summary}）` : debugLabel;

  return (
    <div className="mt-2 flex justify-end">
      <Popover>
        <Tooltip>
          <TooltipTrigger asChild>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label={summaryLabel}
                className="h-8 w-8 rounded-full text-text-muted hover:text-text-primary"
              >
                <Bug className="h-4 w-4" />
              </Button>
            </PopoverTrigger>
          </TooltipTrigger>
          <TooltipContent>{summaryLabel}</TooltipContent>
        </Tooltip>
        <PopoverContent className="w-[420px] max-w-[90vw] space-y-2" align="end">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0 text-sm font-medium text-text-primary truncate">
              {summaryLabel}
            </div>
            <CopyButton
              content={jsonText}
              className="h-8 w-8 !rounded-full bg-fill-tert hover:!bg-fill-sec"
              tooltip={copyLabel}
            />
          </div>

          {compactJson && (
            <div className="rounded-md border border-border/60 bg-muted/40 p-2">
              <div className="mb-1 text-[11px] uppercase tracking-wide text-text-muted">
                Key Fields
              </div>
              <pre className="max-h-52 overflow-auto whitespace-pre-wrap break-words text-xs text-text-primary">
                {compactJson}
              </pre>
            </div>
          )}

          <div className="rounded-md border border-dashed border-border/60 bg-muted/30 p-2">
            <div className="mb-1 text-[11px] uppercase tracking-wide text-text-muted">
              Full JSON
            </div>
            <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs text-text-primary">
              {jsonText}
            </pre>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
