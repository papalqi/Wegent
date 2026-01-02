// SPDX-FileCopyrightText: 2025 WeCode, Inc.
//
// SPDX-License-Identifier: Apache-2.0

export function normalizeProviderBaseUrl(providerType: string, baseUrlInput: string): string {
  const trimmed = (baseUrlInput || '').trim().replace(/\/+$/, '');
  if (!trimmed) return '';

  if (providerType === 'openai' || providerType === 'openai-responses') {
    return trimmed.endsWith('/v1') ? trimmed : `${trimmed}/v1`;
  }

  return trimmed;
}

export function getDefaultProviderBaseUrl(providerType: string): string | null {
  switch (providerType) {
    case 'openai':
    case 'openai-responses':
      return 'https://api.openai.com';
    case 'anthropic':
      return 'https://api.anthropic.com';
    case 'gemini':
      return 'https://generativelanguage.googleapis.com';
    case 'cohere':
      return 'https://api.cohere.com';
    case 'jina':
      return 'https://api.jina.ai';
    default:
      return null;
  }
}

export function getProviderBaseUrlResolvedForDisplay(
  providerType: string,
  baseUrlInput: string
): string | null {
  const normalizedInput = normalizeProviderBaseUrl(providerType, baseUrlInput);
  if (normalizedInput) return normalizedInput;

  const defaultBaseUrl = getDefaultProviderBaseUrl(providerType);
  if (!defaultBaseUrl) return null;

  return normalizeProviderBaseUrl(providerType, defaultBaseUrl);
}
