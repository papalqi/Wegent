// SPDX-FileCopyrightText: 2025 WeCode, Inc.
//
// SPDX-License-Identifier: Apache-2.0

type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

const DEFAULT_SENSITIVE_KEY_PATTERNS: RegExp[] = [
  /api[_-]?key/i,
  /\bkey\b/i,
  /token/i,
  /authorization/i,
  /password/i,
  /secret/i,
  /cookie/i,
  /github[_-]?pat/i,
];

const DEFAULT_SENSITIVE_VALUE_PATTERNS: RegExp[] = [
  /\bsk-[a-z0-9]{8,}\b/i,
  /\bgithub_pat_[a-z0-9_]{10,}\b/i,
  /\bbearer\s+[a-z0-9._-]{10,}\b/i,
];

function maskString(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return value;
  if (trimmed.length <= 8) return `${trimmed[0]}***${trimmed[trimmed.length - 1]}`;
  return `${trimmed.slice(0, 4)}...${trimmed.slice(-4)} (len=${trimmed.length})`;
}

function shouldMaskKey(key: string, keyPatterns: RegExp[]): boolean {
  return keyPatterns.some(p => p.test(key));
}

function shouldMaskValue(value: string, valuePatterns: RegExp[]): boolean {
  return valuePatterns.some(p => p.test(value));
}

export function sanitizeDebugPayload(
  value: unknown,
  options?: {
    keyPatterns?: RegExp[];
    valuePatterns?: RegExp[];
    skipValueMaskKeys?: string[];
    maxDepth?: number;
  }
): JsonValue {
  const keyPatterns = options?.keyPatterns ?? DEFAULT_SENSITIVE_KEY_PATTERNS;
  const valuePatterns = options?.valuePatterns ?? DEFAULT_SENSITIVE_VALUE_PATTERNS;
  const skipValueMaskKeys = new Set(
    options?.skipValueMaskKeys ?? [
      'message',
      'prompt',
      'system_prompt',
      'content',
      'raw_message',
      'sent_message',
    ]
  );
  const maxDepth = options?.maxDepth ?? 12;

  const seen = new WeakSet<object>();

  const walk = (input: unknown, depth: number, parentKey?: string): JsonValue => {
    if (depth > maxDepth) return '[truncated: maxDepth]' as unknown as JsonValue;

    if (input === null || typeof input === 'boolean' || typeof input === 'number') {
      return input;
    }

    if (typeof input === 'string') {
      if (!parentKey || !skipValueMaskKeys.has(parentKey)) {
        if (shouldMaskValue(input, valuePatterns)) return maskString(input);
      }
      return input;
    }

    if (Array.isArray(input)) {
      return input.map(item => walk(item, depth + 1, parentKey));
    }

    if (typeof input === 'object') {
      if (seen.has(input)) return '[circular]' as unknown as JsonValue;
      seen.add(input);

      const out: Record<string, JsonValue> = {};
      for (const [k, v] of Object.entries(input)) {
        if (shouldMaskKey(k, keyPatterns)) {
          out[k] = typeof v === 'string' ? maskString(v) : ('[masked]' as unknown as JsonValue);
          continue;
        }
        out[k] = walk(v, depth + 1, k);
      }
      return out;
    }

    return String(input);
  };

  return walk(value, 0);
}

export function safePrettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return '"[unserializable]"';
  }
}
