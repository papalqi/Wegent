import { sanitizeDebugPayload, safePrettyJson } from '@/utils/debug-sanitize';

describe('debug-sanitize', () => {
  it('should mask sensitive keys and values while preserving message-like fields', () => {
    const input = {
      api_key: 'sk-1234567890abcdef',
      token: 'github_pat_1234567890_abcdefghijklmnopqrstuvwxyz',
      authorization: 'Bearer abcdefghijklmnopqrstuvwxyz.1234567890._-token',
      message: 'Bearer should-not-be-masked-in-message',
      nested: {
        password: 'p@ssw0rd123456',
        note: 'Bearer abcdefghijklmnopqrstuvwxyz.1234567890._-token',
      },
    };

    const out = sanitizeDebugPayload(input) as Record<string, unknown>;

    expect(String(out.api_key)).toContain('(len=');
    expect(String(out.api_key)).not.toBe(input.api_key);

    expect(String(out.token)).toContain('(len=');
    expect(String(out.token)).not.toBe(input.token);

    expect(String(out.authorization)).toContain('(len=');
    expect(String(out.authorization)).not.toBe(input.authorization);

    expect(out.message).toBe(input.message);

    const nested = out.nested as Record<string, unknown>;
    expect(String(nested.password)).toContain('(len=');
    expect(String(nested.password)).not.toBe(input.nested.password);

    expect(String(nested.note)).toContain('(len=');
    expect(String(nested.note)).not.toBe(input.nested.note);
  });

  it('should handle circular structures safely', () => {
    const a: Record<string, unknown> = { name: 'a' };
    const b: Record<string, unknown> = { a };
    a.b = b;

    const out = sanitizeDebugPayload(a) as Record<string, unknown>;
    expect(out.name).toBe('a');
    expect(out.b).toEqual({ a: '[circular]' });
  });

  it('safePrettyJson should not throw on unserializable values', () => {
    const circular: Record<string, unknown> = {};
    circular.self = circular;
    expect(safePrettyJson(circular)).toBe('"[unserializable]"');
  });
});
