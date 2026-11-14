/**
 * The pinyin and pitch-accent session players, which share
 * static/js/session/players/_syllable_trainer.js: answer by key, pause on a
 * mistake, submit the score and show results with the ELO change.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  mount as mountPinyin,
  prefetch as prefetchPinyin,
} from '../../static/js/session/players/pinyin.js';
import { mount as mountPitch } from '../../static/js/session/players/pitch_accent.js';
import { gradeFor, mountTestPage } from '../../static/js/session/players/_syllable_trainer.js';

const flush = () => new Promise((r) => setTimeout(r, 0));
const key = (k) => document.dispatchEvent(new KeyboardEvent('keydown', { key: k }));

const PINYIN = {
  test_data: { title: 'Tones', language: 'zh' },
  pinyin_payload: [
    {
      char: '你',
      word: '你好',
      pinyin_text: 'ni',
      context_tone: 2,
      is_sandhi: true,
      sandhi_rule: '3+3 → 2+3',
    },
    { char: '好', word: '你好', pinyin_text: 'hao', context_tone: 3 },
    { char: '。', is_punctuation: true },
  ],
};

const PITCH = {
  test_data: { title: 'Accent', language: 'ja' },
  pitch_payload: [
    {
      surface: '雨',
      kana: 'あめ',
      mora: ['あ', 'め'],
      mora_count: 2,
      accent: 1,
      pattern_class: 'atamadaka',
      contour: ['H', 'L'],
    },
    { surface: '。', is_punctuation: true },
    {
      surface: '飴',
      kana: 'あめ',
      mora: ['あ', 'め'],
      mora_count: 2,
      accent: 0,
      pattern_class: 'heiban',
      contour: ['L', 'H'],
    },
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
      'excellent',
      'excellent',
      'good',
      'good',
      'fair',
      'fair',
      'poor',
      'poor',
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
      {
        char: '你',
        word: '你好',
        pinyin: 'ni',
        expected: 2,
        guessed: 1,
        is_sandhi: true,
        sandhi_rule: '3+3 → 2+3',
      },
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
    expect(
      container.querySelector('.word-token[data-index="0"]').classList.contains('cls-atamadaka')
    ).toBe(true);
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
    expect(
      container.querySelector('.word-token[data-index="0"]').classList.contains('completed')
    ).toBe(true);
  });
});

describe('standalone pages (ctx.standalone)', () => {
  const PINYIN_TEST = { ...PINYIN, test_data: { id: 'tid-1', title: 'Tones', language: 'zh' } };
  let order;

  function standaloneCtx(slug, daily) {
    order = [];
    const fetchStub = window.authFetch;
    window.authFetch = vi.fn((url, opts) => {
      order.push(url);
      return fetchStub(url, opts);
    });
    return {
      item: { slug },
      languageId: null,
      onComplete: vi.fn(),
      standalone: {
        daily,
        prepare: vi.fn(async () => {
          order.push('prepare');
        }),
      },
    };
  }

  async function startStandalone(mount, ctx) {
    container = document.createElement('div');
    document.body.appendChild(container);
    handle = mount(container, ctx);
    await flush();
    await flush();
  }

  afterEach(() => {
    localStorage.removeItem('selectedLanguageId');
  });

  it('pinyin: page styles, back link, Retry / All tests, daily-load slot', async () => {
    stubFetch(PINYIN_TEST, { user_elo_change: { change: 2 } });
    localStorage.setItem('selectedLanguageId', '1');
    const ctx = standaloneCtx('p9', true);
    await startStandalone(mountPinyin, ctx);

    // The page links its own stylesheet; the session copy is not injected.
    expect(container.querySelector('style')).toBeNull();
    expect(container.querySelector('#errorState a.btn-danger').getAttribute('href')).toBe('/tests');
    expect(ctx.standalone.prepare).toHaveBeenCalledTimes(1);
    expect(order.slice(0, 2)).toEqual(['prepare', '/api/tests/test/p9']);

    key('ArrowRight'); // wrong
    expect(container.querySelector('.error-pinyin').textContent).toBe('ní (你好)');
    key('Enter');
    key('ArrowUp');
    key('ArrowLeft');
    await flush();
    await flush();

    expect(container.querySelector('[data-session-next]')).toBeNull();
    const links = [...container.querySelectorAll('.results-card a')].map((a) =>
      a.getAttribute('href')
    );
    expect(links).toEqual(['/test/p9/preview', '/tests']);
    expect(posts.map((p) => p.url)).toEqual([
      '/api/tests/p9/submit-pinyin',
      '/api/tests/daily-load/complete',
    ]);
    expect(posts[1].body).toEqual({ test_id: 'tid-1', language_id: 1 });
    expect(ctx.onComplete).not.toHaveBeenCalled();
  });

  it('pinyin: no daily-load call unless the page was opened from the daily queue', async () => {
    stubFetch(PINYIN_TEST, { user_elo_change: { change: 2 } });
    localStorage.setItem('selectedLanguageId', '1');
    await startStandalone(mountPinyin, standaloneCtx('p9', false));
    key('ArrowUp');
    key('ArrowLeft');
    await flush();
    await flush();
    expect(posts.map((p) => p.url)).toEqual(['/api/tests/p9/submit-pinyin']);
  });

  it('pinyin: a failing prepare step shows the error state', async () => {
    stubFetch(PINYIN_TEST);
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const ctx = standaloneCtx('p9', false);
    ctx.standalone.prepare = vi.fn(async () => {
      throw new Error('metadata down');
    });
    await startStandalone(mountPinyin, ctx);
    expect(container.querySelector('#errorMessage').textContent).toBe('metadata down');
    expect(window.authFetch).not.toHaveBeenCalled();
  });

  it('the session keeps its own styles, compact markup, Next button and no page extras', async () => {
    stubFetch(PINYIN_TEST, { user_elo_change: { change: 2 } });
    localStorage.setItem('selectedLanguageId', '1');
    await start(mountPinyin, { slug: 'p1' });
    expect(container.querySelector('style')).not.toBeNull();
    expect(container.querySelector('#errorState a')).toBeNull();
    expect(container.querySelector('#testLanguage').nextSibling.nodeType).toBe(1);
    key('ArrowRight');
    expect(container.querySelector('.error-pinyin').textContent).toBe('ní(你好)');
    key('Enter');
    key('ArrowUp');
    key('ArrowLeft');
    await flush();
    await flush();
    expect(container.querySelector('[data-session-next]')).not.toBeNull();
    expect(container.querySelector('.results-card a')).toBeNull();
    expect(posts.map((p) => p.url)).toEqual(['/api/tests/p1/submit-pinyin']);
  });

  it('pitch accent: back link, unknown-word tooltip, page links and daily-load slot', async () => {
    const payload = {
      test_data: { id: 'tid-2', title: 'Accent', language: 'ja' },
      pitch_payload: [
        ...PITCH.pitch_payload,
        { surface: '謎', mora_count: 2, pattern_class: 'unknown' },
      ],
    };
    stubFetch(payload, { user_elo_change: { change: 1 } });
    localStorage.setItem('selectedLanguageId', '3');
    const ctx = standaloneCtx('j9', true);
    await startStandalone(mountPitch, ctx);

    expect(container.querySelector('#errorState a.btn-danger').getAttribute('href')).toBe('/tests');
    expect(order.slice(0, 2)).toEqual(['prepare', '/api/tests/test/j9']);
    expect(container.querySelector('.word-token[data-index="3"] .word-surface').title).toBe(
      'No accent data'
    );

    key('ArrowUp');
    key('ArrowLeft');
    await flush();
    await flush();
    const links = [...container.querySelectorAll('.results-card a')].map((a) =>
      a.getAttribute('href')
    );
    expect(links).toEqual(['/test/j9/preview', '/tests']);
    expect(posts.map((p) => p.url)).toEqual([
      '/api/tests/j9/submit-pitch-accent',
      '/api/tests/daily-load/complete',
    ]);
    expect(posts[1].body).toEqual({ test_id: 'tid-2', language_id: 3 });
  });

  it('pitch accent in the session: no tooltip, no back link', async () => {
    const payload = {
      test_data: { title: 'Accent', language: 'ja' },
      pitch_payload: [
        ...PITCH.pitch_payload,
        { surface: '謎', mora_count: 2, pattern_class: 'unknown' },
      ],
    };
    stubFetch(payload);
    await start(mountPitch, { slug: 'j1' });
    expect(container.querySelector('.word-token[data-index="3"] .word-surface').title).toBe('');
    expect(container.querySelector('#errorState a')).toBeNull();
  });

  it('mountTestPage reads the slug and ?daily from the URL and prepares the page', async () => {
    const realLocation = window.location.href;
    window.history.pushState({}, '', '/test/my-slug/pinyin?daily=true');
    const intro = { init: vi.fn() };
    const i18n = { init: vi.fn(async () => {}), t: (k) => k, applyToDOM: vi.fn() };
    const metaLoad = vi.spyOn(window.LinguaMetadata, 'load').mockResolvedValue({});
    window.LinguaTestIntro = intro;
    window.LinguaI18n = i18n;
    try {
      const root = document.createElement('div');
      const mount = vi.fn(() => ({ destroy() {} }));
      mountTestPage(mount, { root, testType: 'pinyin' });
      const ctx = mount.mock.calls[0][1];
      expect(mount.mock.calls[0][0]).toBe(root);
      expect(ctx.item).toEqual({ slug: 'my-slug' });
      expect(ctx.standalone.daily).toBe(true);
      await ctx.standalone.prepare();
      expect(intro.init).toHaveBeenCalledWith({ testType: 'pinyin' });
      expect(metaLoad).toHaveBeenCalled();
      expect(i18n.init).toHaveBeenCalled();
      expect(i18n.applyToDOM).toHaveBeenCalledWith(root);
    } finally {
      delete window.LinguaTestIntro;
      delete window.LinguaI18n;
      window.history.pushState({}, '', realLocation);
    }
  });
});
