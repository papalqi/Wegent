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
  taskStatus,
}: ThinkingDisplayProps) {
  // Early return if no thinking data
  if (!thinking || thinking.length === 0) {
    return null;
  }

  // Always render detailed view (timeline + tool calls + results)
  return <DetailedThinkingView thinking={thinking} taskStatus={taskStatus} />;
});

export default ThinkingDisplay;
