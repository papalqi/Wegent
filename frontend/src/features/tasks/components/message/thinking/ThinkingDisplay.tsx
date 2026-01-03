// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import { memo } from 'react';
import type { ThinkingDisplayProps } from './types';
import DetailedThinkingView from './DetailedThinkingView';

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
  // Early return if no thinking data
  if (!thinking || thinking.length === 0) {
    return null;
  }

  // Always render detailed view (timeline + tool calls + results)
  return (
    <DetailedThinkingView
      thinking={thinking}
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
