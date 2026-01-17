// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import { http, HttpResponse } from 'msw'

export const MOCK_REPOS = [
  {
    git_repo_id: 1,
    name: 'algorithm',
    git_repo: 'fengkuizhi/algorithm',
    git_url: 'https://github.com/fengkuizhi/algorithm.git',
    git_domain: 'github.com',
    private: false,
    type: 'github',
  },
  {
    git_repo_id: 2,
    name: 'wecode-bot',
    git_repo: 'wecode-bot/main',
    git_url: 'https://github.com/wecode-bot/main.git',
    git_domain: 'github.com',
    private: false,
    type: 'github',
  },
  {
    git_repo_id: 3,
    name: 'frontend',
    git_repo: 'project/frontend',
    git_url: 'https://github.com/project/frontend.git',
    git_domain: 'github.com',
    private: true,
    type: 'github',
  },
]

export const MOCK_BRANCHES = [
  { name: 'master', protected: true, default: true },
  { name: 'develop', protected: false, default: false },
  { name: 'feature/ui-updatelonglonglonglonglong', protected: false, default: false },
]

function searchRepos(query: string) {
  const q = query.trim().toLowerCase()
  if (!q) return MOCK_REPOS
  return MOCK_REPOS.filter(repo => {
    return (
      repo.name.toLowerCase().includes(q) ||
      repo.git_repo.toLowerCase().includes(q) ||
      repo.git_domain.toLowerCase().includes(q)
    )
  })
}

export const githubHandlers = [
  http.get('/api/github/validate-token', () => {
    return HttpResponse.json({ valid: true, user: { login: 'mock-user' } })
  }),
  // Repository list
  http.get('/api/github/repositories', () => {
    return HttpResponse.json(MOCK_REPOS)
  }),
  // Branch list
  http.get('/api/github/repositories/branches', () => {
    return HttpResponse.json(MOCK_BRANCHES)
  }),

  // New unified git endpoints
  http.get('/api/git/validate-token', () => {
    return HttpResponse.json({ valid: true, user: { login: 'mock-user' } })
  }),
  http.get('/api/git/repositories', () => {
    return HttpResponse.json(MOCK_REPOS)
  }),
  http.get('/api/git/repositories/search', ({ request }) => {
    const url = new URL(request.url)
    const query = url.searchParams.get('q') || ''
    return HttpResponse.json(searchRepos(query))
  }),
  http.get('/api/git/repositories/branches', () => {
    return HttpResponse.json(MOCK_BRANCHES)
  }),
  http.post('/api/git/repositories/refresh', () => {
    return HttpResponse.json({
      success: true,
      message: 'Repository cache refreshed',
      cleared_domains: ['github.com'],
    })
  }),
]
