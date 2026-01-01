import { supportsAttachments } from '@/features/tasks/service/attachmentService';

describe('attachmentService Codex support', () => {
  it('returns true when team.agent_type is Codex', () => {
    const team = { agent_type: 'Codex', bots: [] } as unknown as import('@/types/api').Team;
    expect(supportsAttachments(team)).toBe(true);
  });

  it('returns true when first bot shell_type is Codex', () => {
    const team = {
      agent_type: undefined,
      bots: [{ bot: { shell_type: 'Codex' } }],
    } as unknown as import('@/types/api').Team;
    expect(supportsAttachments(team)).toBe(true);
  });
});
