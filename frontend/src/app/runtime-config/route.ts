// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

/**
 * Runtime Configuration API
 *
 * This endpoint provides runtime configuration values that can be changed
 * without rebuilding the application. Environment variables are read at
 * server startup time, not build time.
 *
 * Architecture:
 * - RUNTIME_INTERNAL_API_URL: Used by Next.js server-side rewrites (next.config.js) to proxy to backend
 * - NEXT_PUBLIC_API_URL: Used by browser for direct API calls (empty = use '/api' proxy mode)
 *
 * Recommended setup (browser uses proxy):
 * - Set RUNTIME_INTERNAL_API_URL=http://backend:8000 (for Next.js server to reach backend)
 * - Leave NEXT_PUBLIC_API_URL empty or unset (browser uses '/api' which is proxied)
 *
 * Direct mode setup (browser calls backend directly):
 * - Set NEXT_PUBLIC_API_URL=http://backend:8000 (browser calls backend directly)
 * - RUNTIME_INTERNAL_API_URL is not needed in this case
 */

import { NextResponse } from 'next/server'

export async function GET() {
  // Helper to parse boolean env vars
  const parseBoolean = (value: string | undefined, defaultValue: boolean): boolean => {
    if (value === undefined || value === '') return defaultValue
    return value.toLowerCase() === 'true'
  }

  const parseEnableFlag = (value: string | undefined, defaultValue: boolean): boolean => {
    if (value === undefined || value === '') return defaultValue
    const normalized = value.toLowerCase()
    if (normalized === 'enable' || normalized === 'enabled') return true
    if (normalized === 'disable' || normalized === 'disabled') return false
    return parseBoolean(value, defaultValue)
  }

  const parseLoginMode = (
    value: string | undefined,
    defaultValue: 'password' | 'oidc' | 'all'
  ): 'password' | 'oidc' | 'all' => {
    if (!value) return defaultValue
    const normalized = value.toLowerCase()
    if (normalized === 'password' || normalized === 'oidc' || normalized === 'all') {
      return normalized
    }
    return defaultValue
  }

  return NextResponse.json({
    // Backend API URL for browser
    // Empty string = use '/api' proxy mode (recommended)
    // Full URL = browser calls backend directly (not recommended for same-network deployments)
    apiUrl: process.env.NEXT_PUBLIC_API_URL || '',

    // Socket.IO direct URL - can be changed at runtime
    // Priority: RUNTIME_SOCKET_DIRECT_URL > NEXT_PUBLIC_SOCKET_DIRECT_URL > empty
    // Note: Empty string means use relative path through Next.js proxy
    socketDirectUrl:
      process.env.RUNTIME_SOCKET_DIRECT_URL || process.env.NEXT_PUBLIC_SOCKET_DIRECT_URL || '',

    // Enable chat context feature (knowledge base background)
    // Priority: RUNTIME_ENABLE_CHAT_CONTEXT > NEXT_PUBLIC_ENABLE_CHAT_CONTEXT > false
    enableChatContext: parseBoolean(process.env.RUNTIME_ENABLE_CHAT_CONTEXT, false),

    // Enable Code Shell resume semantics (Codex resume_session_id, ClaudeCode session_id reuse)
    // Priority: CODE_SHELL_RESUME_ENABLED > NEXT_PUBLIC_CODE_SHELL_RESUME_ENABLED > true
    codeShellResumeEnabled: parseBoolean(
      process.env.CODE_SHELL_RESUME_ENABLED,
      parseBoolean(process.env.NEXT_PUBLIC_CODE_SHELL_RESUME_ENABLED, true)
    ),

    // UI/runtime feature toggles and links
    docsUrl:
      process.env.RUNTIME_DOCS_URL ||
      process.env.NEXT_PUBLIC_DOCS_URL ||
      'https://github.com/wecode-ai/wegent/tree/main/docs',
    feedbackUrl:
      process.env.RUNTIME_FEEDBACK_URL ||
      process.env.NEXT_PUBLIC_FEEDBACK_URL ||
      'https://github.com/wecode-ai/wegent/issues/new',
    vscodeLinkTemplate:
      process.env.RUNTIME_VSCODE_LINK_TEMPLATE ||
      process.env.NEXT_PUBLIC_VSCODE_LINK_TEMPLATE ||
      '',

    // Module toggles
    enableWiki: parseBoolean(
      process.env.RUNTIME_ENABLE_WIKI,
      parseBoolean(process.env.NEXT_PUBLIC_ENABLE_WIKI, false)
    ),
    enableCodeKnowledgeAddRepo: parseBoolean(
      process.env.RUNTIME_ENABLE_CODE_KNOWLEDGE_ADD_REPO,
      parseBoolean(process.env.NEXT_PUBLIC_ENABLE_CODE_KNOWLEDGE_ADD_REPO, true)
    ),
    enableDisplayQuotas: parseEnableFlag(
      process.env.RUNTIME_FRONTEND_ENABLE_DISPLAY_QUOTAS ||
        process.env.NEXT_PUBLIC_FRONTEND_ENABLE_DISPLAY_QUOTAS,
      false
    ),

    // Login UI
    loginMode: parseLoginMode(
      process.env.RUNTIME_LOGIN_MODE || process.env.NEXT_PUBLIC_LOGIN_MODE,
      'all'
    ),
    oidcLoginText:
      process.env.RUNTIME_OIDC_LOGIN_TEXT || process.env.NEXT_PUBLIC_OIDC_LOGIN_TEXT || '',

    // OpenTelemetry (frontend)
    otelEnabled: parseBoolean(process.env.RUNTIME_OTEL_ENABLED, false),
    otelServiceName: process.env.RUNTIME_OTEL_SERVICE_NAME || 'wegent-frontend',
    otelCollectorEndpoint: process.env.RUNTIME_OTEL_COLLECTOR_ENDPOINT || 'http://localhost:4318',
  })
}
