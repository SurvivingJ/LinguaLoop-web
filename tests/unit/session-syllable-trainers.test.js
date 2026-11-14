/**
 * The pinyin and pitch-accent session players, which share
 * static/js/session/players/_syllable_trainer.js: answer by key, pause on a
 * mistake, submit the score and show results with the ELO change.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount as mountPinyin, prefetch as prefetchPinyin } from '../../static/js/session/players/pinyin.js';
import { mount as mountPitch } from '../../static/js/session/players/pitch_accent.js';
import { gradeFor } from '../../static/js/session/players/_syllable_trainer.js';

const flush = () => new Promise((r) => setTimeout(r, 0));
const key = (k) => document.dispatchEvent(new KeyboardEvent('keydown', { key: k }));

const PINYIN = {
  test_data: { title: 'Tones', language: 'zh' },
  pinyin_payload: [
    { char: '你', word: '你好', pinyin_text: 'ni', context_tone: 2, is_sandhi: true, sandhi_rule: '3+3 → 2+3' },
    { char: '好', word: '你好', pinyin_text: 'hao', context_tone: 3 },
    { char: '。', is_punctuation: true },
  ],
};

const PITCH = {
  test_data: { title: 'Accent', language: 'ja' },
  pitch_payload: [
    { surface: '雨', kana: 'あめ', mora: ['あ', 'め'], mora_count: 2, accent: 1, pattern_class: 'atamadaka', contour: ['H', 'L'] },
    { surface: '。', is_punctuation: true },
    { surface: '飴', kana: 'あめ', mora: ['あ', 'め'], mora_count: 2, accent: 0, pattern_class: 'heiban', contour: ['L', 'H'] },
  ],
};

let posts;
let handle;
let container;

function stubFetch(payload, submitResult) {
  posts = [];
  window.authFetch = vi.fn(async (url, opts) => {
    if (opts && opts.method === 'POST') {
      posts.push({ url, body: JSON.parse(opts.body) });
      return { ok: true, json: async () => ({ result: submitResult }) };
    }
    return { ok: true, statusText: 'OK', json: async () => payload };
  });
}

async function start(mount, item) {
  container = document.createElement('div');
  document.body.appendChild(container);
  const ctx = { item, languageId: 2, onComplete: vi.fn() };
  handle = mount(container, ctx);
  await flush();
  await flush();
  return ctx;
}

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  localStorage.removeItem('pa_mode');
});

afterEach(() => {
  if (handle) handle.destroy();
  handle = null;
  delete window.authFetch;
  document.body.innerHTML = '';
  document.body.className = '';
  vi.restoreAllMocks();
});

describe('gradeFor', () => {
  it('bands accuracy', () => {
    expect([100, 95, 94.9, 80, 79, 60, 59.9, 0].map(gradeFor)).toEqual([
      'excellent', 'excellent', 'good', 'good', 'fair', 'fair', 'poor', 'poor',
    ]);
  });
});

describe('pinyin player', () => {
  it('runs a passage: mistake modal, completion, submit and ELO', async () => {
    stubFetch(PINYIN, { user_elo_change: { change: 7 } });
    const ctx = await start(mountPinyin, { slug: 'p1' });
    const q = (id) => container.querySelector('#' + id);
    expect(window.authFetch).toHaveBeenCalledWith('/api/tests/test/p1');
    expect(q('testTitle').textContent).toBe('Tones');
    expect(container.querySelectorAll('.char-token')).toHaveLength(3);
    expect(container.querySelector('.char-token.current').dataset.index).toBe('0');

    key('ArrowRight'); // tone 1, wrong (expected 2)
    expect(container.querySelector('.error-modal')).not.toBeNull();
    expect(container.querySelector('.sandhi-explanation').textContent).toContain('3+3');
    key('ArrowUp'); // ignored while paused
    expect(container.querySelector('.char-token.completed')).toBeNull();
    key('Enter');
    expect(container.querySelector('.error-modal')).toBeNull();

    key('ArrowUp'); // tone 2
    const first = container.querySelector('.char-token[data-index="0"]');
    expect(first.classList.contains('tone-2')).toBe(true);
    expect(first.querySelector('.char-pinyin').textContent).toBe('ní');
    expect(q('progressFill').style.width).toBe('50%');
    key('ArrowLeft'); // tone 3 -> complete
    await flush();

    expect(posts).toHaveLength(1);
    expect(posts[0].url).toBe('/api/tests/p1/submit-pinyin');
    expect(posts[0].body).toMatchObject({ correct_chars: 1, total_chars: 2, time_taken: 0 });
    expect(posts[0].body.errors).toEqual([
      { char: '你', word: '你好', pinyin: 'ni', expected: 2, guessed: 1, is_sandhi: true, sandhi_rule: '3+3 → 2+3' },
    ]);
    expect(posts[0].body.started_at).toBeTruthy();
    expect(posts[0].body.finished_at).toBeTruthy();

    expect(container.querySelector('.results-accuracy').textContent).toBe('50.0%');
    expect(container.querySelector('.results-accuracy').classList.contains('poor')).toBe(true);
    const stats = [...container.querySelectorAll('.stat-value')].map((el) => el.textContent);
    expect(stats).toEqual(['2/2', '0:00', '1', '+7']);
    expect(q('eloChangeDisplay').className).toBe('stat-value text-success');
    expect(q('touchArea').style.display).toBe('none');

    container.querySelector('[data-session-next]').click();
    expect(ctx.onComplete).toHaveBeenCalledWith({ accuracy: 50 });
  });

  it('uses a prefetched payload, and shows the error state when there is no data', async () => {
    stubFetch({ test_data: {}, pinyin_payload: [] });
    const item = { slug: 'p2', prefetch: Promise.resolve({ ok: true, data: PINYIN }) };
    await start(mountPinyin, item);
    expect(window.authFetch).not.toHaveBeenCalled();
    expect(container.querySelectorAll('.char-token')).toHaveLength(3);
    handle.destroy();

    vi.spyOn(console, 'error').mockImplementation(() => {});
    await start(mountPinyin, { slug: 'p3' });
    expect(container.querySelector('#errorState').style.display).toBe('block');
    expect(container.querySelector('#errorMessage').textContent).toContain('No pinyin data');
    expect(container.querySelector('#passageContainer').style.display).toBe('none');
  });

  it('prefetch asks for the test payload', async () => {
    stubFetch(PINYIN);
    const res = await prefetchPinyin({ slug: 'p1' });
    expect(res).toEqual({ ok: true, status: undefined, data: PINYIN });
  });

  it('destroy removes the document key handler', async () => {
    stubFetch(PINYIN);
    await start(mountPinyin, { slug: 'p1' });
    handle.destroy();
    key('ArrowUp');
    expect(container.querySelector('.char-token.completed')).toBeNull();
  });
});

describe('pitch-accent player', () => {
  it('quick mode: mistake modal, completion and submit', async () => {
    stubFetch(PITCH, { user_elo_change: { change: -3 } });
    const ctx = await start(mountPitch, { slug: 'j1' });
    const q = (id) => container.querySelector('#' + id);
    expect(document.body.classList.contains('pitch-accent-page')).toBe(true);
    expect(container.querySelectorAll('.word-token')).toHaveLength(3);

    key('ArrowLeft'); // heiban, wrong (atamadaka)
    expect(container.querySelector('.error-modal')).not.toBeNull();
    expect(container.querySelector('.error-kana').textContent).toBe('あめ');
    container.querySelector('button[data-pa-dismiss]').click();
    expect(container.querySelector('.error-modal')).toBeNull();

    key('ArrowUp'); // atamadaka
    expect(container.querySelector('.word-token[data-index="0"]').classList.contains('cls-atamadaka')).toBe(true);
    expect(container.querySelector('.word-token.current').dataset.index).toBe('2');
    key('ArrowLeft'); // heiban -> complete
    await flush();

    expect(posts[0].url).toBe('/api/tests/j1/submit-pitch-accent');
    expect(posts[0].body).toMatchObject({
      correct_units: 1,
      total_units: 2,
      time_taken: 0,
      furigana_used: false,
    });
    expect(posts[0].body.errors[0]).toMatchObject({
      surface: '雨',
      pattern_class: 'atamadaka',
      mode: 'quick',
      info: { mode: 'quick', guessedClass: 'heiban' },
    });
    const stats = [...container.querySelectorAll('.stat-value')].map((el) => el.textContent);
    expect(stats).toEqual(['2/2', '0:00', '1', '-3']);
    expect(q('eloChangeDisplay').className).toBe('stat-value text-danger');
    expect(q('controlsHint').style.display).toBe('none');

    container.querySelector('[data-session-next]').click();
    expect(ctx.onComplete).toHaveBeenCalledWith({ accuracy: 50 });
    handle.destroy();
    expect(document.body.classList.contains('pitch-accent-page')).toBe(false);
  });

  it('contour mode: the scratchpad resets after a rejected contour', async () => {
    localStorage.setItem('pa_mode', 'contour');
    stubFetch(PITCH);
    await start(mountPitch, { slug: 'j1' });
    expect(container.querySelector('#scratchpad')).not.toBeNull();
    key('h');
    key('h'); // mora 1 == mora 2 -> invalid once complete
    key('l');
    key('Enter');
    expect(container.querySelector('.error-modal')).not.toBeNull();
    key('Enter');
    expect(container.querySelector('.error-modal')).toBeNull();
    expect(container.querySelectorAll('.scratch-cell.selected')).toHaveLength(0);

    key('h');
    key('l');
    key('l');
    key('Enter'); // H L L: drop after mora 1 = atamadaka
    expect(container.querySelector('.word-token[data-index="0"]').classList.contains('completed')).toBe(true);
  });
});
