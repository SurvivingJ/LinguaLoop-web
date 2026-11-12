/**
 * Dictation player (static/js/session/players/dictation.js): a play counts
 * only when audio really starts, a failed load says so and offers a skip,
 * and the learner can always skip the item in the session runner.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '../../static/js/session/players/dictation.js';

const flush = () => new Promise((r) => setTimeout(r, 0));

let playImpl;

beforeEach(() => {
  window.authFetch = vi.fn(async () => ({
    ok: true,
    json: async () => ({ test_data: { title: 'T', audio_url: 'https://audio.example/x.mp3', language: 'zh' } }),
  }));
  playImpl = () => Promise.resolve();
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(function () {
    return playImpl.call(this);
  });
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, 'load').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  delete window.authFetch;
});

async function setup(ctxExtra = {}) {
  const c = document.createElement('div');
  document.body.appendChild(c);
  const ctx = { item: { slug: 's' }, languageId: 1, onComplete: vi.fn(), ...ctxExtra };
  mount(c, ctx);
  await flush();
  await flush();
  const q = (id) => c.querySelector('#' + id);
  const type = (v) => {
    q('dictationInput').value = v;
    q('dictationInput').dispatchEvent(new Event('input'));
  };
  return { c, q, type, ctx };
}

describe('dictation audio', () => {
  it('counts a play and unlocks Submit only once playback starts', async () => {
    const { q, type } = await setup();
    type('我有');
    expect(q('submitBtn').disabled).toBe(true);
    q('playBtn').click();
    await flush();
    expect(q('replayCount').textContent).toBe('1');
    expect(q('submitBtn').disabled).toBe(false);
    expect(q('audioError').style.display).toBe('none');
  });

  it('shows the error and keeps Submit locked when playback fails', async () => {
    playImpl = () => Promise.reject(new Error('NotSupportedError'));
    const { q, type } = await setup();
    type('我有');
    q('playBtn').click();
    await flush();
    expect(q('replayCount').textContent).toBe('0');
    expect(q('submitBtn').disabled).toBe(true);
    expect(q('audioError').style.display).toBe('block');
  });

  it('shows the error when the audio element reports a load error', async () => {
    const { q } = await setup();
    q('audioElement').dispatchEvent(new Event('error'));
    expect(q('audioError').style.display).toBe('block');
    q('audioRetry').click();
    expect(q('audioError').style.display).toBe('none');
    expect(HTMLMediaElement.prototype.load).toHaveBeenCalled();
  });
});

describe('dictation skip', () => {
  it('offers skip in the session runner and calls onSkip', async () => {
    const onSkip = vi.fn();
    const { c } = await setup({ onSkip });
    const skips = [...c.querySelectorAll('[data-dict-skip]')];
    expect(skips.length).toBe(3);
    expect(skips.every((b) => b.style.display === '')).toBe(true);
    skips[1].click();
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it('hides skip where there is nowhere to skip to', async () => {
    const { c } = await setup();
    expect([...c.querySelectorAll('[data-dict-skip]')].every((b) => b.style.display === 'none')).toBe(true);
  });
});
