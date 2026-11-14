/**
 * static/js/session/player_registry.js — players are imported on demand
 * (latency 2026-11): mount() shows a spinner, then mounts the real player once
 * its module lands; destroy() before that cancels the mount.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

const practiceMount = vi.fn((container) => {
  container.innerHTML = '<p data-i18n="x">practice player</p>';
  return { destroy: practiceDestroy };
});
const practiceDestroy = vi.fn();

vi.mock('../../static/js/session/players/practice.js', () => ({ mount: practiceMount }));

const { getPlayer, preloadPlayers } = await import('../../static/js/session/player_registry.js');

const flush = () => new Promise((r) => setTimeout(r, 0));

describe('lazy player registry', () => {
  beforeEach(() => {
    practiceMount.mockClear();
    practiceDestroy.mockClear();
    window.LinguaI18n = { applyToDOM: vi.fn() };
  });

  it('shows a spinner, then mounts the real player and translates it', async () => {
    const stage = document.createElement('div');
    const ctx = { item: { kind: 'practice' } };
    const handle = getPlayer({ kind: 'practice' }).mount(stage, ctx);
    expect(stage.querySelector('[data-player-loading]')).not.toBeNull();
    await flush();
    expect(practiceMount).toHaveBeenCalledWith(stage, ctx);
    expect(stage.textContent).toContain('practice player');
    expect(window.LinguaI18n.applyToDOM).toHaveBeenCalledWith(stage);
    handle.destroy();
    expect(practiceDestroy).toHaveBeenCalledTimes(1);
  });

  it('destroy() before the module lands cancels the mount', async () => {
    const stage = document.createElement('div');
    const handle = getPlayer({ kind: 'practice' }).mount(stage, {});
    handle.destroy();
    await flush();
    expect(practiceMount).not.toHaveBeenCalled();
    expect(practiceDestroy).not.toHaveBeenCalled();
  });

  it('preloadPlayers imports what a queue needs without mounting', async () => {
    preloadPlayers([{ kind: 'practice' }, { kind: 'test', test_type: 'nope' }, null]);
    await flush();
    expect(practiceMount).not.toHaveBeenCalled();
  });

  it('unknown test types still get the standalone placeholder', () => {
    const stage = document.createElement('div');
    const onSkip = vi.fn();
    getPlayer({ kind: 'test', test_type: 'not_a_real_type', slug: 's' }).mount(stage, { onSkip });
    stage.querySelector('[data-session-skip]').click();
    expect(onSkip).toHaveBeenCalled();
  });
});
