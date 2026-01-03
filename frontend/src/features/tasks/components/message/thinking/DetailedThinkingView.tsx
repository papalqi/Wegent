// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import { memo, useMemo } from 'react';
import { useTranslation } from '@/hooks/useTranslation';
import type { ThinkingStep, TodoItem } from './types';
import { useThinkingState } from './hooks/useThinkingState';
import {
  formatToolSummary,
  calculateDuration,
  getThinkingText,
  formatConfidence,
  parseToolCallTags,
  shouldCollapse,
  getContentPreview,
} from './utils/thinkingUtils';
import { MAX_CONTENT_HEIGHT } from './utils/constants';
import { getStepTypeConfig } from './utils/stepTypeConfig';
import ThinkingHeader from './components/ThinkingHeader';
import ToolCallItem from './components/ToolCallItem';
import ToolResultItem from './components/ToolResultItem';
import TodoListDisplay from './components/TodoListDisplay';
import SystemInfoDisplay from './components/SystemInfoDisplay';
import ErrorDisplay from './components/ErrorDisplay';
import ScrollToBottom from './components/ScrollToBottom';
import { getTaskExecutionDisplay } from '@/utils/task-execution-phase';
import { useTaskPhaseTimeline } from '@/hooks/use-task-phase-timeline';

interface DetailedThinkingViewProps {
  thinking: ThinkingStep[] | null;
  taskId?: number | null;
  taskStatus?: string;
  taskPhase?: string | null;
  taskProgress?: number | null;
  taskProgressText?: string | null;
  taskErrorMessage?: string | null;
  taskUpdatedAt?: string | null;
  taskCompletedAt?: string | null;
}

/**
 * Detailed thinking view for ClaudeCode/Agno shell types
 * Shows full thinking process with tool calls, results, and system info
 */
const DetailedThinkingView = memo(function DetailedThinkingView({
  thinking,
  taskId,
  taskStatus,
  taskPhase,
  taskProgress,
  taskProgressText,
  taskErrorMessage,
  taskUpdatedAt,
  taskCompletedAt,
}: DetailedThinkingViewProps) {
  const { t } = useTranslation();

  const taskDisplay = useMemo(() => {
    if (!taskStatus) return null;
    return getTaskExecutionDisplay({
      status: taskStatus as never,
      progress: taskProgress ?? undefined,
      statusPhase: taskPhase ?? undefined,
    });
  }, [taskPhase, taskProgress, taskStatus]);

  const stageLabel = useMemo(() => {
    if (!taskStatus || !taskDisplay) return null;
    if (taskProgressText?.trim()) return taskProgressText;
    return (
      (taskStatus === 'CANCELLING'
        ? t('chat:messages.status_cancelling')
        : t(taskDisplay.labelKey)) || t('chat:messages.status_running')
    );
  }, [t, taskDisplay, taskProgressText, taskStatus]);

  const stageId = useMemo(() => {
    if (!taskStatus || !taskDisplay) return null;
    if (taskProgressText?.trim()) return taskProgressText.trim();
    if (taskPhase?.trim()) return taskPhase.trim();
    return taskDisplay.phase;
  }, [taskDisplay, taskPhase, taskProgressText, taskStatus]);

  const eventAtMs = useMemo(() => {
    const parsed = taskUpdatedAt ? Date.parse(taskUpdatedAt) : Number.NaN;
    return Number.isFinite(parsed) ? parsed : Date.now();
  }, [taskUpdatedAt]);

  const terminalAtMs = useMemo(() => {
    const parsed = taskCompletedAt ? Date.parse(taskCompletedAt) : Number.NaN;
    return Number.isFinite(parsed) ? parsed : null;
  }, [taskCompletedAt]);

  const isTerminal =
    taskStatus === 'COMPLETED' || taskStatus === 'FAILED' || taskStatus === 'CANCELLED';

  const { timeline, nowMs } = useTaskPhaseTimeline({
    taskId,
    stageId,
    stageLabel,
    eventAtMs,
    isTerminal,
    terminalAtMs,
  });

  const formatSeconds = (ms: number) => {
    const seconds = Math.max(0, Math.floor(ms / 1000));
    return t('chat:messages.phase_elapsed', { seconds }) || `${seconds}s`;
  };

  const renderedTimeline = timeline.length > 0 ? timeline.slice(-8) : [];

  const {
    items,
    isOpen,
    toggleOpen,
    isCompleted,
    isRunning,
    toolCounts,
    contentRef,
    showScrollToBottom,
    handleScrollToBottom,
    expandedParams,
    toggleParamExpansion,
  } = useThinkingState({ thinking, taskStatus });

  // Early return if no items
  if (items.length === 0) {
    return null;
  }

  // Format collapsed title
  const formatCollapsedTitle = (): string => {
    let statusText = '';
    if (taskStatus === 'COMPLETED') {
      statusText = t('tasks:thinking.execution_completed');
    } else if (taskStatus === 'FAILED') {
      statusText = t('tasks:thinking.execution_failed');
    } else if (taskStatus === 'CANCELLED') {
      statusText = t('tasks:thinking.execution_cancelled');
    }

    const toolSummary = formatToolSummary(toolCounts);
    const duration = calculateDuration(items);

    let result = statusText;
    if (toolSummary) {
      result += ' ' + toolSummary;
    }
    if (duration) {
      result += ' · ' + duration;
    }

    return result;
  };

  // Get title based on state
  const getTitle = () => {
    if (!isOpen && isCompleted) {
      return formatCollapsedTitle();
    }
    if (isCompleted) {
      return t('tasks:thinking.execution_completed');
    }
    return t('chat:messages.thinking') || 'Thinking';
  };

  // Render text content with tool_call parsing
  const renderTextContent = (text: string, uniqueId: string) => {
    const parsed = parseToolCallTags(text);

    if (!parsed) {
      // Check if this is a TodoWrite tool call in text format
      const todoWriteMatch = text.match(
        /<tool_call>TodoWrite\s*<arg_key>todos<\/arg_key>\s*<arg_value>([\s\S]*?)<\/arg_value>/
      );
      if (todoWriteMatch) {
        try {
          const todosData = JSON.parse(todoWriteMatch[1]);
          if (Array.isArray(todosData)) {
            return <TodoListDisplay todos={todosData as TodoItem[]} />;
          }
        } catch {
          // Fall through to text rendering
        }
      }

      // No tool_call tags, render as plain text with collapse support
      const isCollapsible = shouldCollapse(text);
      const textKey = `${uniqueId}-text`;
      const isExpanded = expandedParams.has(textKey);
      const displayText = isCollapsible && !isExpanded ? getContentPreview(text) : text;

      return (
        <div className="text-xs text-text-secondary">
          {isCollapsible && (
            <div className="flex justify-end mb-1">
              <button
                onClick={() => toggleParamExpansion(textKey)}
                className="flex items-center gap-1 text-blue-400 hover:text-blue-500 hover:font-semibold transition-colors text-xs"
              >
                {isExpanded
                  ? t('chat:thinking.collapse') || 'Collapse'
                  : t('chat:thinking.expand') || 'Expand'}
              </button>
            </div>
          )}
          <div className="whitespace-pre-wrap">
            {displayText}
            {isCollapsible && !isExpanded && <span className="text-blue-400">...</span>}
          </div>
        </div>
      );
    }

    // Render with parsed tool_call - handle TodoWrite specially
    if (parsed.toolName === 'TodoWrite' && parsed.args.todos) {
      try {
        const todosData = JSON.parse(parsed.args.todos);
        if (Array.isArray(todosData)) {
          return (
            <div className="space-y-2">
              {parsed.beforeText && (
                <div className="text-xs text-text-secondary whitespace-pre-wrap">
                  {parsed.beforeText}
                </div>
              )}
              <TodoListDisplay todos={todosData as TodoItem[]} />
              {parsed.afterText && (
                <div className="text-xs text-text-secondary whitespace-pre-wrap">
                  {parsed.afterText}
                </div>
              )}
            </div>
          );
        }
      } catch {
        // Fall through
      }
    }

    // Generic tool call rendering
    return (
      <div className="space-y-2">
        {parsed.beforeText && (
          <div className="text-xs text-text-secondary whitespace-pre-wrap">{parsed.beforeText}</div>
        )}
        <div>
          <div className="text-xs font-medium text-blue-400 mb-1">
            {t('chat:thinking.pre_tool_call') || 'Tool Call'}: {parsed.toolName}
          </div>
          <div className="space-y-2">
            {Object.entries(parsed.args).map(([key, value]) => {
              const paramKey = `${uniqueId}-toolcall-${key}`;
              const isCollapsible = shouldCollapse(value);
              const isExpanded = expandedParams.has(paramKey);
              const displayValue = isCollapsible && !isExpanded ? getContentPreview(value) : value;

              return (
                <div key={paramKey} className="text-xs">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="font-medium text-blue-300">{key}:</span>
                    {isCollapsible && (
                      <button
                        onClick={() => toggleParamExpansion(paramKey)}
                        className="text-xs text-blue-400 hover:text-blue-500 hover:font-semibold transition-colors"
                      >
                        {isExpanded
                          ? t('chat:thinking.collapse') || 'Collapse'
                          : t('chat:thinking.expand') || 'Expand'}
                      </button>
                    )}
                  </div>
                  <pre className="text-text-tertiary overflow-x-auto whitespace-pre-wrap break-words">
                    {displayValue}
                    {isCollapsible && !isExpanded && <span className="text-blue-400">...</span>}
                  </pre>
                </div>
              );
            })}
          </div>
        </div>
        {parsed.afterText && (
          <div className="text-xs text-text-secondary whitespace-pre-wrap">{parsed.afterText}</div>
        )}
      </div>
    );
  };

  // Render details content based on type
  const renderDetailsContent = (item: ThinkingStep, itemIndex: number) => {
    const details = item.details;
    if (!details) return null;

    // Handle assistant/user message with content array
    if ((details.type === 'assistant' || details.type === 'user') && details.message?.content) {
      return (
        <div className="mt-2 space-y-2">
          {details.message.content.map((content, idx) => {
            if (content.type === 'tool_use') {
              return (
                <ToolCallItem
                  key={idx}
                  toolName={content.name || 'unknown'}
                  input={content.input as Record<string, unknown>}
                  itemIndex={itemIndex}
                />
              );
            } else if (content.type === 'tool_result') {
              return (
                <ToolResultItem
                  key={idx}
                  content={content.content || ''}
                  isError={content.is_error}
                  itemIndex={itemIndex}
                />
              );
            } else if (content.type === 'text' && content.text) {
              return (
                <div key={idx}>
                  {renderTextContent(content.text, `item-${itemIndex}-text-${idx}`)}
                </div>
              );
            }
            return null;
          })}
        </div>
      );
    }

    // Handle direct tool_use type
    if (details.type === 'tool_use') {
      return (
        <div className="mt-2">
          <ToolCallItem
            toolName={details.name || 'unknown'}
            input={details.input as Record<string, unknown>}
            itemIndex={itemIndex}
          />
        </div>
      );
    }

    // Handle direct tool_result type
    if (details.type === 'tool_result') {
      return (
        <div className="mt-2">
          <ToolResultItem
            content={details.content || ''}
            isError={details.is_error}
            itemIndex={itemIndex}
          />
        </div>
      );
    }

    // Handle result message type
    if (details.type === 'result') {
      return (
        <div>
          <div className="text-xs font-medium text-purple-400 mb-1">
            📋 {t('chat:thinking.result_message') || 'Result Message'}
          </div>
          <div className="space-y-1 text-xs text-text-tertiary">
            {details.subtype && <div>Subtype: {details.subtype}</div>}
            {details.num_turns !== undefined && <div>Turns: {details.num_turns}</div>}
            {details.duration_ms !== undefined && <div>Duration: {details.duration_ms}ms</div>}
            {details.usage && (
              <div>
                Tokens: {details.usage.input_tokens || 0} in / {details.usage.output_tokens || 0}{' '}
                out
              </div>
            )}
          </div>
        </div>
      );
    }

    // Handle system message type
    if (details.type === 'system') {
      return (
        <div>
          <SystemInfoDisplay
            subtype={details.subtype}
            model={details.model}
            tools={details.tools}
            mcpServers={details.mcp_servers}
            permissionMode={details.permissionMode}
            cwd={details.cwd}
          />
        </div>
      );
    }

    // Handle execution failed with error_message
    if (details.error_message || details.execution_type) {
      return (
        <div className="mt-2">
          <ErrorDisplay
            errorMessage={details.error_message || ''}
            executionType={details.execution_type}
          />
        </div>
      );
    }

    return null;
  };

  return (
    <div className="w-full relative" data-thinking-inline>
      {/* Task-level phase strip so users see pulling image/loading model inside bubble */}
      {taskStatus && taskDisplay && stageLabel && (
        <div className="mb-2 rounded-lg border border-border/60 bg-surface/70 p-3">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0 text-xs font-semibold text-text-primary truncate">
                {stageLabel}
              </div>
              {renderedTimeline.length > 0 && (
                <div className="shrink-0 text-xs tabular-nums text-text-tertiary">
                  {formatSeconds(nowMs - renderedTimeline[renderedTimeline.length - 1].startedAtMs)}
                </div>
              )}
            </div>

            {renderedTimeline.length > 1 && (
              <div className="space-y-1">
                {renderedTimeline.map((item, index) => {
                  const isLast = index === renderedTimeline.length - 1;
                  const endAtMs = item.endedAtMs ?? nowMs;
                  const durationMs = Math.max(0, endAtMs - item.startedAtMs);
                  return (
                    <div
                      key={`${item.id}-${item.startedAtMs}`}
                      className="flex items-center justify-between gap-2 text-xs"
                    >
                      <div
                        className={[
                          'min-w-0 truncate',
                          isLast ? 'text-text-primary' : 'text-text-tertiary',
                        ].join(' ')}
                      >
                        {item.label}
                      </div>
                      <div className="shrink-0 tabular-nums text-text-tertiary">
                        {formatSeconds(durationMs)}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {taskErrorMessage?.trim() && (
              <div className="rounded-md border border-red-500/20 bg-red-500/10 p-2">
                <ErrorDisplay errorMessage={taskErrorMessage} />
              </div>
            )}
          </div>
        </div>
      )}

      <ThinkingHeader
        title={getTitle()}
        isOpen={isOpen}
        isCompleted={isCompleted}
        isRunning={isRunning}
        toolSummary={!isOpen ? formatToolSummary(toolCounts) : undefined}
        onToggle={toggleOpen}
      />

      {isOpen && (
        <div className="relative">
          <div
            ref={contentRef}
            className="overflow-y-auto custom-scrollbar space-y-0.5 pb-2 pt-1"
            style={{ maxHeight: MAX_CONTENT_HEIGHT }}
          >
            {items.map((item, index) => {
              const confidenceText = formatConfidence(item.confidence);
              const hasLegacyFields = !!(item.action || item.result || item.reasoning);

              // Get step type configuration for styling
              const stepConfig = getStepTypeConfig(item.details, hasLegacyFields);

              // Determine if this step is currently running
              const isStepRunning = index === items.length - 1 && isRunning;

              return (
                <div key={index} className="relative pl-4 py-1.5 mb-1">
                  {/* Timeline vertical line */}
                  {index < items.length - 1 && (
                    <div
                      className="absolute left-[7px] top-[1.25rem] w-0.5 bg-border/30"
                      style={{ height: 'calc(100% - 0.5rem)' }}
                    />
                  )}

                  {/* Timeline dot with color coding */}
                  <div
                    className={`absolute left-[3px] top-[0.5rem] w-2.5 h-2.5 rounded-full border-2 ${
                      isStepRunning
                        ? `${stepConfig.iconClass.replace('text-', 'border-')} ${stepConfig.iconClass.replace('text-', 'bg-')} animate-pulse`
                        : `${stepConfig.iconClass.replace('text-', 'border-')} bg-surface`
                    }`}
                  />

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    {/* Title with color coding */}
                    <div className={`mb-0.5 font-medium text-xs ${stepConfig.titleClass}`}>
                      {getThinkingText(item.title, t)}
                    </div>

                    {/* Legacy fields for backward compatibility */}
                    {hasLegacyFields && (
                      <>
                        {item.action && (
                          <div className="mb-1 text-xs text-text-secondary">
                            <span className="font-medium">
                              {t('chat:messages.action') || 'Action'}:{' '}
                            </span>
                            {getThinkingText(item.action, t)}
                          </div>
                        )}
                        {item.result && (
                          <div className="mb-1 text-xs text-text-tertiary">
                            <span className="font-medium">
                              {t('chat:messages.result') || 'Result'}:{' '}
                            </span>
                            {renderTextContent(
                              getThinkingText(item.result, t),
                              `item-${index}-legacy-result`
                            )}
                          </div>
                        )}
                        {item.reasoning && (
                          <div className="mb-1 text-xs text-text-tertiary">
                            <span className="font-medium">
                              {t('chat:messages.reasoning') || 'Reasoning'}:{' '}
                            </span>
                            {renderTextContent(
                              getThinkingText(item.reasoning, t),
                              `item-${index}-legacy-reasoning`
                            )}
                          </div>
                        )}
                      </>
                    )}

                    {/* New details field */}
                    {renderDetailsContent(item, index)}

                    {/* Footer with confidence and next_action */}
                    <div className="flex flex-wrap items-center justify-between gap-2 mt-1.5">
                      {confidenceText && (
                        <div className="text-xs text-text-tertiary">
                          <span className="font-medium">
                            {t('chat:messages.confidence') || 'Confidence'}:{' '}
                          </span>
                          {confidenceText}
                        </div>
                      )}
                      {item.next_action &&
                        item.next_action !== 'continue' &&
                        item.next_action !== 'thinking.continue' && (
                          <div className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-xs border border-blue-500/20">
                            {getThinkingText(item.next_action, t)}
                          </div>
                        )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <ScrollToBottom show={showScrollToBottom} onClick={handleScrollToBottom} />
        </div>
      )}
    </div>
  );
});

export default DetailedThinkingView;
