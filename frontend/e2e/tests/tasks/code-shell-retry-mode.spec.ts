import { test, expect } from '@playwright/test';

function jsonResponse(body: unknown) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  };
}

function waitForSocketFrameSent(
  sentFrames: string[],
  predicate: (payload: string) => boolean,
  timeoutMs = 10_000
) {
  return new Promise<string>((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;

    const tick = () => {
      const found = sentFrames.find(predicate);
      if (found) {
        resolve(found);
        return;
      }
      if (Date.now() >= deadline) {
        reject(new Error('Timed out waiting for websocket frame'));
        return;
      }
      setTimeout(tick, 50);
    };

    tick();
  });
}

async function dismissQuickModeSwitchIfPresent(page: import('@playwright/test').Page) {
  const dialog = page.getByRole('dialog', { name: /Quick Mode Switch|快速模式切换/i }).first();
  if (!(await dialog.isVisible().catch(() => false))) return;

  const closeButton = dialog.getByRole('button', { name: /Close|Skip|关闭|跳过/i }).first();
  if (await closeButton.isVisible().catch(() => false)) {
    await closeButton.click();
    await expect(dialog).toBeHidden({ timeout: 10_000 });
    return;
  }

  const skipText = dialog.getByText(/Skip|跳过/i).first();
  if (await skipText.isVisible().catch(() => false)) {
    await skipText.click();
    await expect(dialog).toBeHidden({ timeout: 10_000 });
  }
}

test.describe('Code Shell retry_mode', () => {
  test('emits chat:retry with retry_mode (resume/new_session)', async ({ page }) => {
    const now = new Date().toISOString();
    const taskId = 9991;
    const teamId = 1;
    const userId = 1;
    const resumeSessionId = 'thread_123';
    const failedSubtaskId = 1004;
    const taskTitle = 'E2E Code Shell retry_mode';

    const taskItem = {
      id: taskId,
      title: taskTitle,
      team_id: teamId,
      git_url: '',
      git_repo: '',
      git_repo_id: 0,
      git_domain: '',
      branch_name: '',
      prompt: '',
      status: 'FAILED',
      task_type: 'chat',
      progress: 0,
      batch: 1,
      result: {},
      error_message: 'boom',
      user_id: userId,
      user_name: 'admin',
      created_at: now,
      updated_at: now,
      completed_at: '',
    };

    const taskDetail = {
      ...taskItem,
      user: {
        id: userId,
        user_name: 'admin',
        email: 'admin@example.com',
        is_active: true,
        created_at: now,
        updated_at: now,
        git_info: [],
      },
      team: {
        id: teamId,
        name: 'Codex Team',
        description: 'E2E team',
        bots: [
          {
            bot_id: 1,
            bot_prompt: '',
            bot: {
              shell_type: 'Codex',
            },
          },
        ],
        workflow: {},
        is_active: true,
        user_id: userId,
        created_at: now,
        updated_at: now,
        agent_type: 'codex',
      },
      subtasks: [
        {
          id: 1001,
          task_id: taskId,
          team_id: teamId,
          title: 'user-1',
          bot_ids: [1],
          role: 'USER',
          message_id: 1,
          parent_id: 0,
          prompt: 'hi',
          executor_namespace: '',
          executor_name: '',
          status: 'COMPLETED',
          progress: 100,
          batch: 1,
          result: {},
          error_message: '',
          user_id: userId,
          created_at: now,
          updated_at: now,
          completed_at: now,
          bots: [],
        },
        {
          id: 1002,
          task_id: taskId,
          team_id: teamId,
          title: 'ai-1',
          bot_ids: [1],
          role: 'ASSISTANT',
          message_id: 2,
          parent_id: 1001,
          prompt: '',
          executor_namespace: '',
          executor_name: '',
          status: 'COMPLETED',
          progress: 100,
          batch: 1,
          result: {
            value: 'first answer',
            shell_type: 'Codex',
            resume_session_id: resumeSessionId,
          },
          error_message: '',
          user_id: userId,
          created_at: now,
          updated_at: now,
          completed_at: now,
          bots: [
            {
              id: 1,
              name: 'Codex Bot',
              shell_name: 'Codex',
              shell_type: 'Codex',
              agent_config: {},
              system_prompt: '',
              mcp_servers: {},
              is_active: true,
              created_at: now,
              updated_at: now,
            },
          ],
        },
        {
          id: 1003,
          task_id: taskId,
          team_id: teamId,
          title: 'user-2',
          bot_ids: [1],
          role: 'USER',
          message_id: 3,
          parent_id: 0,
          prompt: 'second question',
          executor_namespace: '',
          executor_name: '',
          status: 'COMPLETED',
          progress: 100,
          batch: 1,
          result: {},
          error_message: '',
          user_id: userId,
          created_at: now,
          updated_at: now,
          completed_at: now,
          bots: [],
        },
        {
          id: failedSubtaskId,
          task_id: taskId,
          team_id: teamId,
          title: 'ai-2',
          bot_ids: [1],
          role: 'ASSISTANT',
          message_id: 4,
          parent_id: 1003,
          prompt: '',
          executor_namespace: '',
          executor_name: '',
          status: 'FAILED',
          progress: 100,
          batch: 1,
          result: {
            shell_type: 'Codex',
            resume_session_id: resumeSessionId,
          },
          error_message: 'boom',
          user_id: userId,
          created_at: now,
          updated_at: now,
          completed_at: now,
          bots: [
            {
              id: 1,
              name: 'Codex Bot',
              shell_name: 'Codex',
              shell_type: 'Codex',
              agent_config: {},
              system_prompt: '',
              mcp_servers: {},
              is_active: true,
              created_at: now,
              updated_at: now,
            },
          ],
        },
      ],
    };

    const sentFrames: string[] = [];
    page.on('websocket', ws => {
      ws.on('framesent', frame => {
        const payload = frame.payload;
        if (typeof payload !== 'string') return;
        sentFrames.push(payload);
      });
    });

    // Force Socket.IO client to connect directly to backend (Next.js does not proxy /socket.io).
    await page.route(new RegExp('.*/runtime-config(\\?.*)?$'), async route => {
      await route.fulfill(
        jsonResponse({
          apiUrl: '',
          socketDirectUrl: 'http://localhost:8000',
          enableChatContext: false,
          codeShellResumeEnabled: true,
        })
      );
    });

    await page.route(
      new RegExp(`.*/api/tasks/${taskId}/container-status(\\?.*)?$`),
      async route => {
        await route.fulfill(
          jsonResponse({
            task_id: taskId,
            executor_name: null,
            status: 'not_found',
            state: null,
            reason: 'not_found',
          })
        );
      }
    );

    await page.route(new RegExp('.*/api/tasks/container-status(\\?.*)?$'), async route => {
      await route.fulfill(jsonResponse({ items: [] }));
    });

    await page.route(new RegExp(`.*/api/tasks/${taskId}(\\?.*)?$`), async route => {
      await route.fulfill(jsonResponse(taskDetail));
    });

    // Task lists - keep stable and deterministic
    await page.route(new RegExp('.*/api/tasks/lite/personal(\\?.*)?$'), async route => {
      await route.fulfill(jsonResponse({ total: 1, items: [taskItem] }));
    });
    await page.route(new RegExp('.*/api/tasks/lite/group(\\?.*)?$'), async route => {
      await route.fulfill(jsonResponse({ total: 0, items: [] }));
    });
    await page.route(new RegExp('.*/api/tasks/lite(\\?.*)?$'), async route => {
      await route.fulfill(jsonResponse({ total: 1, items: [taskItem] }));
    });

    const socketIoWebsocketPromise = page
      .waitForEvent('websocket', ws => ws.url().includes('/socket.io'), { timeout: 15_000 })
      .catch(() => null);

    await page.goto('/tasks');
    await page.waitForLoadState('domcontentloaded');
    await dismissQuickModeSwitchIfPresent(page);
    await socketIoWebsocketPromise;

    // Select the mocked task from the sidebar/history list (avoid relying on unstable testids/classes)
    const taskTitleLocator = page.getByText(taskTitle).first();
    await expect(taskTitleLocator).toBeVisible({ timeout: 15_000 });
    await taskTitleLocator.click();

    // Ensure the failed message is rendered and Code Shell dual retry actions are available
    await expect(page.locator('text=boom').first()).toBeVisible();
    await expect(
      page.getByRole('button', { name: /Retry \(New Session\)|新会话重试/ })
    ).toBeVisible();
    await expect(page.getByRole('button', { name: /Retry \(Resume\)|Resume 重试/ })).toBeVisible();

    // new_session retry
    const newSessionFramePromise = waitForSocketFrameSent(sentFrames, payload => {
      return (
        payload.includes('chat:retry') &&
        payload.includes(`"task_id":${taskId}`) &&
        payload.includes(`"subtask_id":${failedSubtaskId}`) &&
        payload.includes('"retry_mode":"new_session"')
      );
    });
    await page.getByRole('button', { name: /Retry \(New Session\)|新会话重试/ }).click();
    const newSessionFrame = await newSessionFramePromise;
    expect(newSessionFrame).toContain('"retry_mode":"new_session"');

    // resume retry
    const resumeFramePromise = waitForSocketFrameSent(sentFrames, payload => {
      return (
        payload.includes('chat:retry') &&
        payload.includes(`"task_id":${taskId}`) &&
        payload.includes(`"subtask_id":${failedSubtaskId}`) &&
        payload.includes('"retry_mode":"resume"')
      );
    });
    await page.getByRole('button', { name: /Retry \(Resume\)|Resume 重试/ }).click();
    const resumeFrame = await resumeFramePromise;
    expect(resumeFrame).toContain('"retry_mode":"resume"');
  });

  test('hides Code Shell dual retry buttons when resume flag is disabled', async ({ page }) => {
    const now = new Date().toISOString();
    const taskId = 9992;
    const teamId = 1;
    const userId = 1;
    const resumeSessionId = 'thread_456';
    const failedSubtaskId = 1104;
    const taskTitle = 'E2E Code Shell retry_mode (resume disabled)';

    const taskItem = {
      id: taskId,
      title: taskTitle,
      team_id: teamId,
      git_url: '',
      git_repo: '',
      git_repo_id: 0,
      git_domain: '',
      branch_name: '',
      prompt: '',
      status: 'FAILED',
      task_type: 'chat',
      progress: 0,
      batch: 1,
      result: {},
      error_message: 'boom',
      user_id: userId,
      user_name: 'admin',
      created_at: now,
      updated_at: now,
      completed_at: '',
    };

    const taskDetail = {
      ...taskItem,
      user: {
        id: userId,
        user_name: 'admin',
        email: 'admin@example.com',
        is_active: true,
        created_at: now,
        updated_at: now,
        git_info: [],
      },
      team: {
        id: teamId,
        name: 'Codex Team',
        description: 'E2E team',
        bots: [
          {
            bot_id: 1,
            bot_prompt: '',
            bot: {
              shell_type: 'Codex',
            },
          },
        ],
        workflow: {},
        is_active: true,
        user_id: userId,
        created_at: now,
        updated_at: now,
        agent_type: 'codex',
      },
      subtasks: [
        {
          id: 1101,
          task_id: taskId,
          team_id: teamId,
          title: 'user-1',
          bot_ids: [1],
          role: 'USER',
          message_id: 1,
          parent_id: 0,
          prompt: 'hi',
          executor_namespace: '',
          executor_name: '',
          status: 'COMPLETED',
          progress: 100,
          batch: 1,
          result: {},
          error_message: '',
          user_id: userId,
          created_at: now,
          updated_at: now,
          completed_at: now,
          bots: [],
        },
        {
          id: 1102,
          task_id: taskId,
          team_id: teamId,
          title: 'ai-1',
          bot_ids: [1],
          role: 'ASSISTANT',
          message_id: 2,
          parent_id: 1101,
          prompt: '',
          executor_namespace: '',
          executor_name: '',
          status: 'COMPLETED',
          progress: 100,
          batch: 1,
          result: {
            value: 'first answer',
            shell_type: 'Codex',
            resume_session_id: resumeSessionId,
          },
          error_message: '',
          user_id: userId,
          created_at: now,
          updated_at: now,
          completed_at: now,
          bots: [
            {
              id: 1,
              name: 'Codex Bot',
              shell_name: 'Codex',
              shell_type: 'Codex',
              agent_config: {},
              system_prompt: '',
              mcp_servers: {},
              is_active: true,
              created_at: now,
              updated_at: now,
            },
          ],
        },
        {
          id: 1103,
          task_id: taskId,
          team_id: teamId,
          title: 'user-2',
          bot_ids: [1],
          role: 'USER',
          message_id: 3,
          parent_id: 0,
          prompt: 'second question',
          executor_namespace: '',
          executor_name: '',
          status: 'COMPLETED',
          progress: 100,
          batch: 1,
          result: {},
          error_message: '',
          user_id: userId,
          created_at: now,
          updated_at: now,
          completed_at: now,
          bots: [],
        },
        {
          id: failedSubtaskId,
          task_id: taskId,
          team_id: teamId,
          title: 'ai-2',
          bot_ids: [1],
          role: 'ASSISTANT',
          message_id: 4,
          parent_id: 1103,
          prompt: '',
          executor_namespace: '',
          executor_name: '',
          status: 'FAILED',
          progress: 100,
          batch: 1,
          result: {
            shell_type: 'Codex',
            resume_session_id: resumeSessionId,
          },
          error_message: 'boom',
          user_id: userId,
          created_at: now,
          updated_at: now,
          completed_at: now,
          bots: [
            {
              id: 1,
              name: 'Codex Bot',
              shell_name: 'Codex',
              shell_type: 'Codex',
              agent_config: {},
              system_prompt: '',
              mcp_servers: {},
              is_active: true,
              created_at: now,
              updated_at: now,
            },
          ],
        },
      ],
    };

    const sentFrames: string[] = [];
    page.on('websocket', ws => {
      ws.on('framesent', frame => {
        const payload = frame.payload;
        if (typeof payload !== 'string') return;
        sentFrames.push(payload);
      });
    });

    await page.route(new RegExp('.*/runtime-config(\\?.*)?$'), async route => {
      await route.fulfill(
        jsonResponse({
          apiUrl: '',
          socketDirectUrl: 'http://localhost:8000',
          enableChatContext: false,
          codeShellResumeEnabled: false,
        })
      );
    });

    await page.route(
      new RegExp(`.*/api/tasks/${taskId}/container-status(\\?.*)?$`),
      async route => {
        await route.fulfill(
          jsonResponse({
            task_id: taskId,
            executor_name: null,
            status: 'not_found',
            state: null,
            reason: 'not_found',
          })
        );
      }
    );

    await page.route(new RegExp('.*/api/tasks/container-status(\\?.*)?$'), async route => {
      await route.fulfill(jsonResponse({ items: [] }));
    });

    await page.route(new RegExp(`.*/api/tasks/${taskId}(\\?.*)?$`), async route => {
      await route.fulfill(jsonResponse(taskDetail));
    });

    await page.route(new RegExp('.*/api/tasks/lite/personal(\\?.*)?$'), async route => {
      await route.fulfill(jsonResponse({ total: 1, items: [taskItem] }));
    });
    await page.route(new RegExp('.*/api/tasks/lite/group(\\?.*)?$'), async route => {
      await route.fulfill(jsonResponse({ total: 0, items: [] }));
    });
    await page.route(new RegExp('.*/api/tasks/lite(\\?.*)?$'), async route => {
      await route.fulfill(jsonResponse({ total: 1, items: [taskItem] }));
    });

    const socketIoWebsocketPromise = page
      .waitForEvent('websocket', ws => ws.url().includes('/socket.io'), { timeout: 15_000 })
      .catch(() => null);

    await page.goto('/tasks');
    await page.waitForLoadState('domcontentloaded');
    await dismissQuickModeSwitchIfPresent(page);
    await socketIoWebsocketPromise;

    const taskTitleLocator = page.getByText(taskTitle).first();
    await expect(taskTitleLocator).toBeVisible({ timeout: 15_000 });
    await taskTitleLocator.click();

    await expect(page.locator('text=boom').first()).toBeVisible();

    await expect(
      page.getByRole('button', { name: /Retry \(New Session\)|新会话重试/ })
    ).toBeHidden();
    await expect(page.getByRole('button', { name: /Retry \(Resume\)|Resume 重试/ })).toBeHidden();

    const fallbackRetryButton = page.getByRole('button', { name: /^重试$|^Retry$/ }).first();
    await expect(fallbackRetryButton).toBeVisible();

    const retryFramePromise = waitForSocketFrameSent(sentFrames, payload => {
      return (
        payload.includes('chat:retry') &&
        payload.includes(`\"task_id\":${taskId}`) &&
        payload.includes(`\"subtask_id\":${failedSubtaskId}`) &&
        !payload.includes('\"retry_mode\"')
      );
    });
    await fallbackRetryButton.click();
    await retryFramePromise;
  });
});
