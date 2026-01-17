// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import { User } from '@/types/api'

export const MOCK_USER: User = {
  id: 1,
  user_name: 'admin',
  email: 'admin@example.com',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  git_info: [
    {
      git_domain: 'github.com',
      git_token: 'mock_token',
      type: 'github',
    },
  ],
}
import { http, HttpResponse } from 'msw'

function generateMockJwt(secondsValid: number) {
  const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }))
  const exp = Math.floor(Date.now() / 1000) + secondsValid
  const payload = btoa(JSON.stringify({ exp }))
  return `${header}.${payload}.signature`
}

export const authHandlers = [
  http.post('/api/auth/login', async ({ request }) => {
    const body = await request.json()
    if (
      typeof body !== 'object' ||
      body === null ||
      !('user_name' in body) ||
      !('password' in body)
    ) {
      return HttpResponse.json({ error: 'Invalid request body' }, { status: 400 })
    }
    const { user_name, password } = body as { user_name: string; password: string }

    if (user_name === 'admin' && password === 'admin') {
      return HttpResponse.json({
        access_token: generateMockJwt(60 * 60),
        token_type: 'bearer',
      })
    } else {
      return HttpResponse.json({ detail: 'Incorrect username or password' }, { status: 401 })
    }
  }),
  http.get('/api/users/me', () => {
    return HttpResponse.json(MOCK_USER)
  }),
  http.put<never, Record<string, unknown>>('/api/users/me', async ({ request }) => {
    const userData = await request.json()
    const updatedUser = { ...MOCK_USER, ...userData, updated_at: new Date().toISOString() }
    return HttpResponse.json(updatedUser)
  }),
  http.get('/api/users/quick-access', () => {
    return HttpResponse.json({
      system_version: 1,
      user_version: null,
      show_system_recommended: true,
      teams: [],
    })
  }),
  http.get('/api/users/welcome-config', () => {
    return HttpResponse.json({
      slogans: [
        { id: 1, zh: '欢迎使用 Wegent', en: 'Welcome to Wegent', mode: 'both' },
        { id: 2, zh: '从一个任务开始', en: 'Start with a task', mode: 'both' },
      ],
      tips: [
        { id: 1, zh: '输入需求并发送', en: 'Type your request and send', mode: 'both' },
        { id: 2, zh: '用快捷卡片快速开始', en: 'Use quick cards to get started', mode: 'both' },
      ],
    })
  }),
  http.get('/api/quota/claude/quota', () => {
    return HttpResponse.json({
      quota_source: 'mock',
      data: {
        open: true,
        quota: 100,
        remaining: 100,
        usage: 0,
        user: 'admin',
        user_quota_detail: {
          demand_quota: 0,
          monthly_quota: 100,
          monthly_usage: 0,
          permanent_quota: 0,
          permanent_usage: 0,
          task_quota: 0,
        },
      },
    })
  }),
]
