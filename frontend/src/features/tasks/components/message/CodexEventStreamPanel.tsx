// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { sanitizeDebugPayload, safePrettyJson } from '@/utils/debug-sanitize';
import { CopyButton } from './BubbleTools';

type CodexEvent = Record<string, unknown>;

type EventTone = 'success' | 'error' | 'info';

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function getString(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined;
}

function truncateOneLine(input: string, max = 160): string {
  const firstLine = input.split('\n')[0] ?? '';
  if (firstLine.length <= max) return firstLine;
  return `${firstLine.slice(0, max - 1)}…`;
}

function guessTone(event: CodexEvent): EventTone {
  const type = getString(event.type) ?? '';
  const error = event.error;
  if (type.includes('failed') || type.includes('error') || error) return 'error';
  if (type.includes('completed') || type.includes('done') || type.includes('success'))
    return 'success';
  return 'info';
}

function getToneClasses(tone: EventTone): { dot: string; badge: string } {
  if (tone === 'error') {
    return {
      dot: 'bg-red-500',
      badge:
        'border-red-200 text-red-700 bg-red-50 dark:border-red-900/60 dark:text-red-200 dark:bg-red-950/30',
    };
  }
  if (tone === 'success') {
    return {
      dot: 'bg-green-500',
      badge:
        'border-green-200 text-green-700 bg-green-50 dark:border-green-900/60 dark:text-green-200 dark:bg-green-950/30',
    };
  }
  return {
    dot: 'bg-sky-500',
    badge:
      'border-sky-200 text-sky-700 bg-sky-50 dark:border-sky-900/60 dark:text-sky-200 dark:bg-sky-950/30',
  };
}

function getEventTitle(event: CodexEvent, index: number): string {
  const type = typeof event.type === 'string' ? event.type : 'event';
  const item = event.item as Record<string, unknown> | undefined;
  const itemType = item && typeof item.type === 'string' ? item.type : undefined;
  return itemType ? `${index + 1}. ${type} · ${itemType}` : `${index + 1}. ${type}`;
}

function buildEventSummary(event: CodexEvent): { headline: string; detail?: string } {
  const type = getString(event.type) ?? 'event';

  const item = isRecord(event.item) ? event.item : undefined;
  const itemType = item ? getString(item.type) : undefined;

  const headline = itemType ? `${type} · ${itemType}` : type;

  const errorMsg =
    (isRecord(event.error) ? getString(event.error.message) : undefined) ??
    getString(event.error) ??
    (isRecord(item?.error)
      ? getString((item?.error as Record<string, unknown>).message)
      : undefined);

  if (errorMsg) return { headline, detail: truncateOneLine(errorMsg) };

  const text =
    (item && getString(item.text)) ??
    (item && getString(item.content)) ??
    getString(event.message) ??
    getString(event.text);
  if (text) return { headline, detail: truncateOneLine(text) };

  const command =
    (item && getString(item.command)) ??
    (item && getString(item.cmd)) ??
    getString(event.command) ??
    getString(event.cmd);
  if (command) return { headline, detail: truncateOneLine(command) };

  const name =
    (item && getString(item.name)) ??
    getString(event.name) ??
    (isRecord(event.tool) ? getString((event.tool as Record<string, unknown>).name) : undefined);
  if (name) return { headline, detail: truncateOneLine(name) };

  return { headline };
}

function buildKeyFields(event: CodexEvent): Array<{ label: string; value: string }> {
  const rows: Array<{ label: string; value: string }> = [];
  const push = (label: string, value: unknown) => {
    if (value === undefined || value === null) return;
    if (typeof value === 'string') rows.push({ label, value });
    else if (typeof value === 'number' || typeof value === 'boolean')
      rows.push({ label, value: String(value) });
  };

  push('type', event.type);
  const item = isRecord(event.item) ? event.item : undefined;
  if (item) {
    push('item.type', item.type);
    push('item.name', item.name);
    push('item.command', item.command ?? item.cmd);
    push('item.path', item.path);
    push('item.url', item.url);
  }

  const error = event.error;
  if (isRecord(error)) {
    push('error.message', error.message);
    push('error.code', error.code);
  } else {
    push('error', error);
  }

  return rows.slice(0, 8);
}

export default function CodexEventStreamPanel({
  events,
  t,
}: {
  events?: unknown[];
  t: (key: string) => string;
}) {
  const normalized = useMemo(() => {
    if (!Array.isArray(events) || events.length === 0) return [];
    return events.filter(e => e && typeof e === 'object') as CodexEvent[];
  }, [events]);

  const pretty = useMemo(() => {
    return normalized.map(e => safePrettyJson(sanitizeDebugPayload(e)));
  }, [normalized]);

  if (normalized.length === 0) return null;

  const title = t('chat:messages.codex_event_stream') || 'Codex event stream';
  const copyLabel = t('chat:actions.copy') || 'Copy';

  return (
    <details className="mt-3 rounded-lg border border-border bg-surface/40">
      <summary className="flex items-center justify-between gap-2 px-3 py-2 text-xs text-text-muted cursor-pointer select-none">
        <span className="min-w-0 truncate">
          {title}（{normalized.length}）
        </span>
      </summary>
      <div className="px-3 pb-3">
        <div className="space-y-2">
          {normalized.map((event, index) => {
            const tone = guessTone(event);
            const toneClass = getToneClasses(tone);
            const summary = buildEventSummary(event);
            const keyFields = buildKeyFields(event);

            return (
              <details
                key={index}
                className="rounded-md border border-border/60 bg-muted/10 px-3 py-2"
              >
                <summary className="cursor-pointer select-none">
                  <div className="flex items-start gap-3">
                    <div
                      className={`mt-1.5 h-2.5 w-2.5 rounded-full flex-shrink-0 ${toneClass.dot}`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0 truncate text-xs font-medium text-text-primary">
                          {getEventTitle(event, index)}
                        </div>
                        <Badge
                          variant="outline"
                          className={`shrink-0 text-[11px] ${toneClass.badge}`}
                        >
                          {tone.toUpperCase()}
                        </Badge>
                      </div>
                      <div className="mt-0.5 flex items-center gap-2">
                        <Badge variant="secondary" className="text-[11px]">
                          {summary.headline}
                        </Badge>
                      </div>
                      {summary.detail && (
                        <div className="mt-1 text-xs text-text-muted break-words">
                          {summary.detail}
                        </div>
                      )}
                    </div>
                  </div>
                </summary>

                <div className="mt-2 space-y-2">
                  {keyFields.length > 0 && (
                    <div className="rounded-md border border-border/60 bg-muted/30 p-2">
                      <div className="mb-1 text-[11px] uppercase tracking-wide text-text-muted">
                        Key Fields
                      </div>
                      <div className="grid grid-cols-1 gap-1 text-xs">
                        {keyFields.map(row => (
                          <div key={row.label} className="flex items-start gap-2">
                            <span className="w-28 shrink-0 text-text-muted">{row.label}</span>
                            <span className="min-w-0 flex-1 break-words text-text-primary">
                              {row.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[11px] uppercase tracking-wide text-text-muted">
                      Raw JSON
                    </div>
                    <CopyButton
                      content={pretty[index] ?? ''}
                      tooltip={copyLabel}
                      className="h-8 w-8 !rounded-full bg-fill-tert hover:!bg-fill-sec"
                    />
                  </div>
                  <pre className="max-h-64 overflow-auto rounded-md bg-muted/40 p-2 text-xs text-text-primary whitespace-pre-wrap break-words">
                    {pretty[index]}
                  </pre>
                </div>
              </details>
            );
          })}
        </div>
      </div>
    </details>
  );
}
