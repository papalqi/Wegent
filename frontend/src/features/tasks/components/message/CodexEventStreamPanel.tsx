// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import React, { useMemo } from 'react';
import { sanitizeDebugPayload, safePrettyJson } from '@/utils/debug-sanitize';

type CodexEvent = Record<string, unknown>;

function getEventTitle(event: CodexEvent, index: number): string {
  const type = typeof event.type === 'string' ? event.type : 'event';
  const item = event.item as Record<string, unknown> | undefined;
  const itemType = item && typeof item.type === 'string' ? item.type : undefined;
  return itemType ? `${index + 1}. ${type} · ${itemType}` : `${index + 1}. ${type}`;
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

  return (
    <details className="mt-3 rounded-lg border border-border bg-surface/40">
      <summary className="flex items-center justify-between gap-2 px-3 py-2 text-xs text-text-muted cursor-pointer select-none">
        <span className="min-w-0 truncate">
          {title}（{normalized.length}）
        </span>
      </summary>
      <div className="px-3 pb-3">
        <div className="space-y-2">
          {normalized.map((e, i) => (
            <details key={i} className="rounded-md border border-border/60 bg-muted/20 px-2 py-2">
              <summary className="cursor-pointer select-none text-xs text-text-primary">
                {getEventTitle(e, i)}
              </summary>
              <pre className="mt-2 max-h-64 overflow-auto rounded-md bg-muted/40 p-2 text-xs text-text-primary whitespace-pre-wrap break-words">
                {pretty[i]}
              </pre>
            </details>
          ))}
        </div>
      </div>
    </details>
  );
}
