// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import {
  getProviderBaseUrlResolvedForDisplay,
  normalizeProviderBaseUrl,
} from '@/features/settings/utils/provider-base-url'

export type ProviderType = 'openai' | 'openai-responses' | 'anthropic' | 'gemini'

export type PublicModelFormData = {
  name: string
  displayName: string
  providerType: ProviderType
  modelId: string
  baseUrl: string
  apiKey: string
  customHeaders: string
  useAdvancedJson: boolean
  advancedJson: string
  is_active: boolean
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const ensureRecord = (parent: Record<string, unknown>, key: string): Record<string, unknown> => {
  const existing = parent[key]
  if (isRecord(existing)) return existing
  const created: Record<string, unknown> = {}
  parent[key] = created
  return created
}

export const parseCustomHeaders = (value: string): Record<string, string> | null => {
  if (!value.trim()) return {}
  try {
    const parsed = JSON.parse(value)
    if (!isRecord(parsed)) return null
    for (const [_k, v] of Object.entries(parsed)) {
      if (typeof v !== 'string') return null
    }
    return parsed as Record<string, string>
  } catch {
    return null
  }
}

const toEnvModelValue = (providerType: ProviderType): string => {
  if (providerType === 'anthropic') return 'claude'
  if (providerType === 'openai-responses') return 'openai'
  return providerType
}

const extractEnv = (json: Record<string, unknown>): Record<string, unknown> => {
  const spec = isRecord(json.spec) ? json.spec : null
  const specModelConfig = spec && isRecord(spec.modelConfig) ? spec.modelConfig : null
  if (specModelConfig) {
    if (isRecord(specModelConfig.env)) return specModelConfig.env
    // Some historical data may store env-like keys directly under modelConfig
    return specModelConfig
  }

  const modelConfig = isRecord(json.modelConfig) ? json.modelConfig : null
  if (modelConfig) {
    if (isRecord(modelConfig.env)) return modelConfig.env
    return modelConfig
  }

  if (isRecord(json.env)) return json.env

  // Fallback: treat the root object as env-like config when it contains known keys
  const hasEnvLikeKeys =
    typeof json.model === 'string' ||
    typeof json.provider === 'string' ||
    typeof json.model_id === 'string' ||
    typeof json.api_key === 'string' ||
    typeof json.base_url === 'string'
  if (hasEnvLikeKeys) return json

  return {}
}

export const extractDisplayName = (json: Record<string, unknown>): string => {
  const metadata = isRecord(json.metadata) ? json.metadata : null
  if (!metadata) return ''
  const displayName = metadata.displayName
  return typeof displayName === 'string' ? displayName : ''
}

export const extractProviderType = (json: Record<string, unknown>): ProviderType => {
  const spec = isRecord(json.spec) ? json.spec : null
  const protocol = spec?.protocol
  if (protocol === 'openai-responses') return 'openai-responses'

  const env = extractEnv(json)
  const rawModel = env.model
  const rawProvider = env.provider ?? json.provider
  const modelValue =
    (typeof rawModel === 'string' && rawModel) ||
    (typeof rawProvider === 'string' && rawProvider) ||
    'openai'

  if (modelValue === 'claude' || modelValue === 'anthropic') return 'anthropic'
  if (modelValue === 'openai-responses') return 'openai-responses'
  if (modelValue === 'gemini') return 'gemini'
  return 'openai'
}

export const extractModelId = (json: Record<string, unknown>): string => {
  const env = extractEnv(json)
  const modelId = env.model_id ?? json.model_id
  return typeof modelId === 'string' ? modelId : ''
}

export const extractApiKey = (json: Record<string, unknown>): string => {
  const env = extractEnv(json)
  const apiKey = env.api_key ?? json.api_key
  return typeof apiKey === 'string' ? apiKey : ''
}

export const extractBaseUrl = (json: Record<string, unknown>): string => {
  const env = extractEnv(json)
  const baseUrl = env.base_url ?? json.base_url
  return typeof baseUrl === 'string' ? baseUrl : ''
}

export const extractCustomHeaders = (json: Record<string, unknown>): Record<string, string> => {
  const env = extractEnv(json)
  const headers = env.custom_headers ?? json.custom_headers
  if (!isRecord(headers)) return {}
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(headers)) {
    if (typeof v === 'string') out[k] = v
  }
  return out
}

export const buildPublicModelJson = (
  baseJson: Record<string, unknown> | null,
  data: {
    name: string
    displayName: string
    providerType: ProviderType
    modelId: string
    baseUrl: string
    apiKey: string
    customHeaders: Record<string, string>
  }
): Record<string, unknown> => {
  const cloned: Record<string, unknown> =
    baseJson && isRecord(baseJson) ? JSON.parse(JSON.stringify(baseJson)) : {}

  cloned.apiVersion = 'agent.wecode.io/v1'
  cloned.kind = 'Model'

  const metadata = ensureRecord(cloned, 'metadata')
  metadata.name = data.name
  metadata.namespace = 'default'
  if (data.displayName.trim()) {
    metadata.displayName = data.displayName.trim()
  } else {
    delete metadata.displayName
  }

  const spec = ensureRecord(cloned, 'spec')
  const modelConfig = ensureRecord(spec, 'modelConfig')
  const env = ensureRecord(modelConfig, 'env')

  env.model = toEnvModelValue(data.providerType)
  env.model_id = data.modelId.trim()
  env.api_key = data.apiKey

  if (data.providerType === 'openai-responses') {
    spec.protocol = 'openai-responses'
  } else if (spec.protocol === 'openai-responses') {
    delete spec.protocol
  }

  const resolvedBaseUrl =
    normalizeProviderBaseUrl(data.providerType, data.baseUrl) ||
    getProviderBaseUrlResolvedForDisplay(data.providerType, '') ||
    ''
  if (resolvedBaseUrl) {
    env.base_url = resolvedBaseUrl
  } else {
    delete env.base_url
  }

  if (data.customHeaders && Object.keys(data.customHeaders).length > 0) {
    env.custom_headers = data.customHeaders
  } else {
    delete env.custom_headers
  }

  const status = ensureRecord(cloned, 'status')
  if (typeof status.state !== 'string') status.state = 'Available'

  return cloned
}
