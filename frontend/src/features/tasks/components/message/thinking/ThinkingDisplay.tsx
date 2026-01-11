// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import { memo } from 'react';
import type { ThinkingDisplayProps } from './types';
import DetailedThinkingView from './DetailedThinkingView';
import type { ThinkingStep } from './types';

function buildDefaultThinkingSteps(taskStatus?: string): ThinkingStep[] {
  const normalizedStatus = (taskStatus ?? '').toUpperCase();
  if (!normalizedStatus) return [];

  const steps: ThinkingStep[] = [{ title: 'thinking.initialize_agent', next_action: 'continue' }];

  if (normalizedStatus !== 'PENDING') {
    steps.push({ title: 'thinking.running', next_action: 'continue' });
  }

  if (normalizedStatus === 'COMPLETED') {
    steps.push({ title: 'thinking.execution_completed', next_action: 'continue' });
  } else if (normalizedStatus === 'FAILED') {
    steps.push({ title: 'thinking.execution_failed', next_action: 'continue' });
  } else if (normalizedStatus === 'CANCELLED') {
    steps.push({ title: 'tasks:thinking.execution_cancelled', next_action: 'continue' });
  }

  return steps;
}

function mergeThinkingSteps(base: ThinkingStep[], fallback: ThinkingStep[]): ThinkingStep[] {
  if (!fallback.length) return base;
  if (!base.length) return fallback;

  const merged = base.slice();
  const hasTitle = (title: string) => merged.some(step => step.title === title);

  const init = fallback.find(step => step.title === 'thinking.initialize_agent');
  if (init && !hasTitle(init.title)) {
    merged.unshift(init);
  }

  const running = fallback.find(step => step.title === 'thinking.running');
  if (running && !hasTitle(running.title)) {
    const initIndex = merged.findIndex(step => step.title === 'thinking.initialize_agent');
    const insertIndex = initIndex >= 0 ? initIndex + 1 : 0;
    merged.splice(insertIndex, 0, running);
  }

  const terminal = fallback.find(
    step =>
      step.title === 'thinking.execution_completed' ||
      step.title === 'thinking.execution_failed' ||
      step.title === 'tasks:thinking.execution_cancelled'
  );
  if (terminal && !hasTitle(terminal.title)) {
    merged.push(terminal);
  }

  return merged;
}

/**
 * Thinking display component.
 * Always uses DetailedThinkingView to show the full timeline and avoid missing details.
 */
const ThinkingDisplay = memo(function ThinkingDisplay({
  thinking,
  taskId,
  taskStatus,
  taskPhase,
  taskProgress,
  taskProgressText,
  taskErrorMessage,
  taskUpdatedAt,
  taskCompletedAt,
}: ThinkingDisplayProps) {
  const safeThinking = Array.isArray(thinking) ? thinking : [];
  const displayThinking = mergeThinkingSteps(safeThinking, buildDefaultThinkingSteps(taskStatus));

  if (displayThinking.length === 0) return null;

  // Always render detailed view (timeline + tool calls + results)
  return (
    <DetailedThinkingView
      thinking={displayThinking}
      taskId={taskId}
      taskStatus={taskStatus}
      taskPhase={taskPhase}
      taskProgress={taskProgress}
      taskProgressText={taskProgressText}
      taskErrorMessage={taskErrorMessage}
      taskUpdatedAt={taskUpdatedAt}
      taskCompletedAt={taskCompletedAt}
    />
  );
});

export default ThinkingDisplay;
