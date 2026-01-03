'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

export type PhaseTimelineItem = {
  id: string;
  label: string;
  startedAtMs: number;
  endedAtMs?: number;
};

type UseTaskPhaseTimelineInput = {
  taskId?: number | null;
  stageId: string | null;
  stageLabel: string | null;
  eventAtMs: number;
  isTerminal: boolean;
  terminalAtMs?: number | null;
};

export function useTaskPhaseTimeline({
  taskId,
  stageId,
  stageLabel,
  eventAtMs,
  isTerminal,
  terminalAtMs,
}: UseTaskPhaseTimelineInput): {
  timeline: PhaseTimelineItem[];
  nowMs: number;
} {
  const taskKey = taskId ?? null;
  const prevTaskKeyRef = useRef<number | null>(null);
  const [timeline, setTimeline] = useState<PhaseTimelineItem[]>([]);
  const [nowMs, setNowMs] = useState(() => Date.now());

  const resolvedTerminalAtMs = useMemo(() => {
    if (!isTerminal) return null;
    if (terminalAtMs && Number.isFinite(terminalAtMs)) return terminalAtMs;
    return eventAtMs;
  }, [eventAtMs, isTerminal, terminalAtMs]);

  useEffect(() => {
    if (prevTaskKeyRef.current === taskKey) return;
    prevTaskKeyRef.current = taskKey;
    setTimeline([]);
  }, [taskKey]);

  useEffect(() => {
    if (!stageId || !stageLabel) return;

    setTimeline(prev => {
      const last = prev[prev.length - 1];
      if (last && last.id === stageId) return prev;

      const next = prev.slice();
      if (next.length > 0) {
        const lastItem = next[next.length - 1];
        if (lastItem && lastItem.endedAtMs === undefined) {
          next[next.length - 1] = { ...lastItem, endedAtMs: eventAtMs };
        }
      }

      next.push({ id: stageId, label: stageLabel, startedAtMs: eventAtMs });
      return next;
    });
  }, [eventAtMs, stageId, stageLabel]);

  useEffect(() => {
    if (!isTerminal || !resolvedTerminalAtMs) return;

    setTimeline(prev => {
      const last = prev[prev.length - 1];
      if (!last) return prev;
      if (last.endedAtMs !== undefined) return prev;
      const next = prev.slice();
      next[next.length - 1] = { ...last, endedAtMs: resolvedTerminalAtMs };
      return next;
    });
  }, [isTerminal, resolvedTerminalAtMs]);

  useEffect(() => {
    if (isTerminal) {
      setNowMs(resolvedTerminalAtMs ?? Date.now());
      return;
    }

    setNowMs(Date.now());
    const intervalId = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, [isTerminal, resolvedTerminalAtMs]);

  return { timeline, nowMs };
}
