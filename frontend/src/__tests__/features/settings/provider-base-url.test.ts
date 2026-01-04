// SPDX-FileCopyrightText: 2025 WeCode, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import {
  getProviderBaseUrlResolvedForDisplay,
  normalizeProviderBaseUrl,
} from '@/features/settings/utils/provider-base-url';

describe('provider-base-url', () => {
  describe('normalizeProviderBaseUrl', () => {
    it('adds /v1 for openai when missing', () => {
      expect(normalizeProviderBaseUrl('openai', 'https://api.openai.com')).toBe(
        'https://api.openai.com/v1'
      );
    });

    it('keeps /v1 and trims trailing slashes', () => {
      expect(normalizeProviderBaseUrl('openai', 'http://localhost:8000/v1/')).toBe(
        'http://localhost:8000/v1'
      );
    });

    it('trims trailing slashes for non-openai providers', () => {
      expect(normalizeProviderBaseUrl('anthropic', 'https://api.anthropic.com/')).toBe(
        'https://api.anthropic.com'
      );
    });
  });

  describe('getProviderBaseUrlResolvedForDisplay', () => {
    it('returns default resolved base url when input is empty', () => {
      expect(getProviderBaseUrlResolvedForDisplay('openai', '')).toBe('https://api.openai.com/v1');
    });
  });
});
