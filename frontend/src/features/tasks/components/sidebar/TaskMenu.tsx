// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client';

import { Menu } from '@headlessui/react';
import {
  ArrowPathIcon,
  StopIcon,
  ClipboardDocumentIcon,
  TrashIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { HiOutlineEllipsisVertical } from 'react-icons/hi2';
import { useTranslation } from '@/hooks/useTranslation';
import type { Task } from '@/types/api';
import { getTaskStatusLabelKey, isTaskActiveStatus } from '@/utils/taskStatus';

interface TaskMenuProps {
  task: Task;
  handleCopyTaskId: (taskId: number) => void;
  handleDeleteTask: (taskId: number) => void;
  handleCancelTask?: (taskId: number) => void;
  handleRestartTask?: (task: Task) => void;
  handleRefreshStatus?: (taskId: number) => void;
  isGroupChat?: boolean;
}

export default function TaskMenu({
  task,
  handleCopyTaskId,
  handleDeleteTask,
  handleCancelTask,
  handleRestartTask,
  handleRefreshStatus,
  isGroupChat = false,
}: TaskMenuProps) {
  const { t } = useTranslation();

  const statusKey = getTaskStatusLabelKey(task.status);
  const statusLabel = statusKey ? t(statusKey) : task.status;
  const isCodeTask =
    task.task_type === 'code' || (typeof task.git_repo === 'string' && task.git_repo.trim() !== '');

  return (
    <Menu as="div" className="relative">
      <Menu.Button
        onClick={e => e.stopPropagation()}
        className="flex items-center justify-center text-text-muted hover:text-text-primary px-1"
      >
        <HiOutlineEllipsisVertical className="h-4 w-4" />
      </Menu.Button>
      <Menu.Items
        className="absolute right-0 top-full mt-1 bg-surface border border-border rounded-lg z-30 min-w-[120px] py-1"
        style={{ boxShadow: 'var(--shadow-popover)' }}
      >
        <div className="px-3 py-2 text-xs text-text-muted cursor-default select-none">
          {t('common:messages.task_status')} {statusLabel}
        </div>
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={e => {
                e.stopPropagation();
                handleCopyTaskId(task.id);
              }}
              className={`w-full px-3 py-2 text-xs text-left text-text-primary flex items-center ${active ? 'bg-muted' : ''}`}
            >
              <ClipboardDocumentIcon className="h-3.5 w-3.5 mr-2" />
              {t('common:tasks.copy_task_id')}
            </button>
          )}
        </Menu.Item>
        {handleRefreshStatus && (
          <Menu.Item>
            {({ active }) => (
              <button
                onClick={e => {
                  e.stopPropagation();
                  handleRefreshStatus(task.id);
                }}
                className={`w-full px-3 py-2 text-xs text-left text-text-primary flex items-center ${active ? 'bg-muted' : ''}`}
              >
                <ArrowPathIcon className="h-3.5 w-3.5 mr-2" />
                {t('common:tasks.refresh_status')}
              </button>
            )}
          </Menu.Item>
        )}
        {!isGroupChat && handleRestartTask && (
          <Menu.Item>
            {({ active }) => (
              <button
                onClick={e => {
                  e.stopPropagation();
                  handleRestartTask(task);
                }}
                className={`w-full px-3 py-2 text-xs text-left text-text-primary flex items-center ${active ? 'bg-muted' : ''}`}
              >
                <ArrowPathIcon className="h-3.5 w-3.5 mr-2" />
                {isCodeTask
                  ? t('common:tasks.restart_task')
                  : t('common:tasks.restart_conversation')}
              </button>
            )}
          </Menu.Item>
        )}
        {handleCancelTask && isTaskActiveStatus(task.status) && (
          <Menu.Item>
            {({ active }) => (
              <button
                onClick={e => {
                  e.stopPropagation();
                  handleCancelTask(task.id);
                }}
                className={`w-full px-3 py-2 text-xs text-left text-text-primary flex items-center ${active ? 'bg-muted' : ''}`}
              >
                <StopIcon className="h-3.5 w-3.5 mr-2" />
                {t('common:tasks.cancel_task')}
              </button>
            )}
          </Menu.Item>
        )}
        <Menu.Item>
          {({ active }) => (
            <button
              onClick={e => {
                e.stopPropagation();
                handleDeleteTask(task.id);
              }}
              className={`w-full px-3 py-2 text-xs text-left text-text-primary flex items-center ${active ? 'bg-muted' : ''}`}
            >
              {isGroupChat ? (
                <>
                  <ArrowRightOnRectangleIcon className="h-3.5 w-3.5 mr-2" />
                  {t('common:groupChat.leave')}
                </>
              ) : (
                <>
                  <TrashIcon className="h-3.5 w-3.5 mr-2" />
                  {t('common:tasks.delete_task')}
                </>
              )}
            </button>
          )}
        </Menu.Item>
      </Menu.Items>
    </Menu>
  );
}
