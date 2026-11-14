/**
 * The drill engine (static/js/session/players/classifier_drill.js) and its two
 * configs: CLASSIFIER (daily-session item and /classifier-drill page) and
 * COUNTER (/counter-drill page, static/js/pages/counter-drill.js).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  CLASSIFIER,
  mount,
  mountDrill,
  mountDrillPage,
  prefetch,
} from '../../static/js/session/players/classifier_drill.js';
import { COUNTER } from '../../static/js/pages/counter-drill.js';

const flush = () => new Promise((r) => setTimeout(r, 0));
const key = (k) => document.dispatchEvent(new KeyboardEvent('keydown', { key: k }));

const CD_ITEMS = [
  {
    level: 1,
    noun_lemma: '书',
    noun_pronunciation: 'shū',
    noun_gloss: 'book',
    classifier_id_primary: 10,
    correct_classifier_ids: [10],
    correct_classifier_hanzi: ['本'],
    correct_classifier_pinyin: ['běn'],
    distractor_ids: [11, 12],
    distractor_hanzi: ['个', '只'],
    distractor_pinyin: ['gè', 'zhī'],
    semantic_label: 'bound things',
  },
  {
    level: 2,
    noun_lemma: '猫',
    classifier_id_primary: 12,
    correct_classifier_ids: [12],
    correct_classifier_hanzi: ['只', '个'],
    distractor_ids: [10],
    distractor_hanzi: ['本'],
  },
];

const CT_ITEMS = [
  {
    noun_lemma: '鉛筆',
    noun_pronunciation: 'えんぴつ',
    noun_gloss: 'pencil',
    correct_counter_text: ['本'],
    correct_counter_reading: ['ほん'],
    distractor_text: ['枚', '匹'],
    distractor_reading: ['まい', 'ひき'],
    semantic_label: 'long thin things',
    numeral_readings: { 3: 'さんぼん', 1: 'いっぽん' },
  },
  {
    noun_lemma: '兎',
    correct_counter_text: ['匹', '羽'],
    correct_counter_reading: ['ひき', 'わ'],
    distractor_text: ['本'],
    distractor_reading: ['ほん'],
  },
];

let calls;
let container;
let handle;

/** authFetch stub: `batches` are served in turn by /session, `submit` by /submit. */
function stubApi({ batches, submit, sessionStatus = 200 }) {
  calls = [];
  let n = 0;
  window.authFetch = vi.fn(async (url, opts) => {
    const body = opts && opts.body ? JSON.parse(opts.body) : null;
    calls.push({
      url,
      method: (opts && opts.method) || 'GET',
      body,
      headers: opts && opts.headers,
    });
    if (url.includes('/session?')) {
      const items = batches[Math.min(n++, batches.length - 1)];
      return {
        ok: sessionStatus < 400,
        status: sessionStatus,
        json: async () => ({ data: { items } }),
      };
    }
    if (typeof submit === 'function') return submit();
    return { ok: true, status: 200, json: async () => submit || {} };
  });
}

async function startPage(config, page) {
  container = document.createElement('div');
  document.body.appendChild(container);
  handle = mountDrillPage(container, config, page);
  await flush();
  await flush();
}

async function startSession(ctx) {
  container = document.createElement('div');
  document.body.appendChild(container);
  handle = mount(container, ctx);
  await flush();
  await flush();
}

const q = (id) => container.querySelector('#' + id);
const option = (cls, text) =>
  [...container.querySelectorAll(cls)].find((b) => b.textContent.includes(text));

beforeEach(() => {
  localStorage.removeItem('cd_mode');
  localStorage.removeItem('ct_mode');
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
});

afterEach(() => {
  if (handle) handle.destroy();
  handle = null;
  vi.useRealTimers();
  delete window.authFetch;
  delete window.LinguaTestIntro;
  document.body.innerHTML = '';
  vi.restoreAllMocks();
});

// `flush` waits on a timer, so it needs the clock advanced under fake timers.
async function settle(ms = 0) {
  await vi.advanceTimersByTimeAsync(ms);
}

describe('drill configs', () => {
  const HOOKS = [
    'bindTyped',
    'digitKeys',
    'onModeChange',
    'renderCurrent',
    'renderInput',
    'onChoice',
    'fillFeedback',
    'grade',
    'submitBody',
    'onSubmitted',
    'onSubmitError',
  ];

  it.each([
    ['classifier', CLASSIFIER],
    ['counter', COUNTER],
  ])('%s defines everything the engine reads', (_name, cfg) => {
    for (const hook of HOOKS) expect(typeof cfg[hook], hook).toBe('function');
    for (const field of [
      'kind',
      'testType',
      'label',
      'apiBase',
      'i18n',
      'prefix',
      'modeKey',
      'defaultMode',
      'exitUrl',
      'pageMarkup',
    ]) {
      expect(typeof cfg[field], field).toBe('string');
    }
    expect(Object.keys(cfg.display).sort()).toEqual(['bar', 'loading', 'results', 'stage']);
    // The page markup carries the elements under the config's id prefix.
    const root = document.createElement('div');
    root.innerHTML = cfg.pageMarkup;
    for (const id of [
      'Header',
      'Loading',
      'Stage',
      'Options',
      'TypedForm',
      'TypedInput',
      'ModeToggle',
      'Feedback',
      'FeedbackContinue',
      'Results',
      'ResultsNext',
      'ResultsExit',
      'ResultsElo',
      'ProgressFill',
    ]) {
      expect(root.querySelector('#' + cfg.prefix + id), cfg.prefix + id).not.toBeNull();
    }
  });

  it('differ where the drills differ', () => {
    expect([CLASSIFIER.apiBase, COUNTER.apiBase]).toEqual([
      '/api/classifier-drill',
      '/api/counter-drill',
    ]);
    expect([CLASSIFIER.languageId, COUNTER.languageId]).toEqual([1, 3]);
    expect([CLASSIFIER.testType, COUNTER.testType]).toEqual(['classifier_drill', 'counter_drill']);
    expect([CLASSIFIER.modeKey, COUNTER.modeKey]).toEqual(['cd_mode', 'ct_mode']);
    expect([CLASSIFIER.defaultMode, COUNTER.defaultMode]).toEqual(['auto', 'mc']);
    expect([100, 95, 80, 60, 59].map(CLASSIFIER.grade)).toEqual(['🏆', '🏆', '🎯', '👍', '💪']);
    expect([100, 90, 89, 70, 69].map(COUNTER.grade)).toEqual(['🏆', '🏆', '🎯', '🎯', '📚']);
    // Only the classifier drill runs inside the daily session.
    expect(typeof CLASSIFIER.sessionMarkup).toBe('string');
    expect(COUNTER.sessionMarkup).toBeUndefined();
  });
});

describe('classifier drill in the session', () => {
  it('plays a batch, submits it and completes the item once', async () => {
    stubApi({
      batches: [CD_ITEMS],
      submit: { data: { user_elo_change: { change: 12 }, mastery_updates: [{ promoted: true }] } },
    });
    vi.useRealTimers();
    const ctx = { item: {}, languageId: 1, onComplete: vi.fn() };
    await startSession(ctx);

    expect(calls[0].url).toBe('/api/classifier-drill/session?language_id=1&count=20');
    expect(container.querySelector('style')).not.toBeNull();
    expect(q('cdHeader')).toBeNull();
    expect(q('cdControls').style.display).toBe('flex');
    expect(q('cdLevelBadge').textContent).toBe('· MC');
    expect(container.querySelectorAll('.cd-option')).toHaveLength(3);

    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    option('.cd-option', '本').click();
    await settle(400);
    expect(q('cdProgressLabel').textContent).toBe('2');
    expect(q('cdTypedForm').style.display).toBe('block');

    q('cdTypedInput').value = '错';
    q('cdTypedForm').dispatchEvent(new Event('submit', { cancelable: true }));
    await settle(250);
    expect(q('cdFeedback').classList.contains('show')).toBe(true);
    expect(q('cdFeedbackCanonical').textContent).toContain('只');
    key('Enter');
    await settle(0);
    vi.useRealTimers();
    await flush();

    const post = calls.find((c) => c.method === 'POST');
    expect(post.url).toBe('/api/classifier-drill/submit');
    expect(Object.keys(post.body)).toEqual([
      'language_id',
      'correct_items',
      'total_items',
      'time_taken',
      'item_results',
      'started_at',
      'finished_at',
    ]);
    expect(post.body).toMatchObject({
      language_id: 1,
      correct_items: 1,
      total_items: 2,
      item_results: [
        { classifier_id: 10, is_correct: true, level: 1 },
        { classifier_id: 12, is_correct: false, level: 2 },
      ],
    });
    expect(post.headers).toBeUndefined();
    expect(q('cdResults').style.display).toBe('block');
    expect(q('cdControls').style.display).toBe('none');
    expect(q('cdResultsGrade').textContent).toBe('💪');
    expect(q('cdResultsElo').textContent).toContain('+12');
    // The promotion banner belongs to the standalone page.
    expect(q('cdResults').textContent).not.toContain('🎓');
    expect(q('cdResultsNext')).toBeNull();

    q('cdResultsContinue').click();
    q('cdResultsContinue').click();
    expect(ctx.onComplete).toHaveBeenCalledTimes(1);
    expect(ctx.onComplete).toHaveBeenCalledWith({ correct: 1, total: 2, mode: 'classifier_drill' });
  });

  it('uses the session language and a prefetched batch', async () => {
    stubApi({ batches: [CD_ITEMS] });
    vi.useRealTimers();
    const pending = prefetch({}, { languageId: 4, current: null });
    expect(calls[0].url).toBe('/api/classifier-drill/session?language_id=4&count=20');
    expect(prefetch({}, { current: { test_type: 'classifier_drill' } })).toBeNull();
    await startSession({ item: { prefetch: pending }, languageId: 4, onComplete: vi.fn() });
    expect(calls).toHaveLength(1);
    expect(q('cdNoun').textContent).toBe('书');
  });

  it('a failed or empty load offers Next instead of blocking the session', async () => {
    stubApi({ batches: [CD_ITEMS], sessionStatus: 500 });
    vi.useRealTimers();
    const ctx = { item: {}, languageId: 1, onComplete: vi.fn() };
    await startSession(ctx);
    expect(q('cdResults').style.display).toBe('block');
    expect(q('cdResultsNote').textContent).toContain('(500)');
    q('cdResultsContinue').click();
    expect(ctx.onComplete).toHaveBeenCalledTimes(1);
  });

  it('destroy removes the document key handler', async () => {
    stubApi({ batches: [CD_ITEMS] });
    vi.useRealTimers();
    await startSession({ item: {}, languageId: 1, onComplete: vi.fn() });
    handle.destroy();
    key('1');
    expect(container.querySelector('.cd-option.correct, .cd-option.wrong')).toBeNull();
  });
});

describe('classifier drill page', () => {
  it('shows the page layout, the mastery banner, another round and the way out', async () => {
    stubApi({
      batches: [[CD_ITEMS[0]], [CD_ITEMS[0]]],
      submit: {
        data: {
          user_elo_change: { change: 0 },
          mastery_updates: [{ promoted: true }, { demoted: true }],
        },
      },
    });
    window.LinguaTestIntro = { init: vi.fn() };
    const navigate = vi.fn();
    vi.useRealTimers();
    await startPage(CLASSIFIER, { navigate });

    expect(window.LinguaTestIntro.init).toHaveBeenCalledWith({ testType: 'classifier_drill' });
    expect(container.querySelector('style')).toBeNull();
    expect(q('cdControls')).toBeNull();
    expect(q('cdHeader').style.display).toBe('flex');
    expect(q('cdHeader').querySelector('a').getAttribute('href')).toBe('/tests');

    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    option('.cd-option', '本').click();
    await settle(400);
    vi.useRealTimers();
    await flush();

    expect(q('cdResults').style.display).toBe('block');
    // The page keeps its header on the results screen.
    expect(q('cdHeader').style.display).toBe('flex');
    expect(q('cdResultsElo').style.display).toBe('inline-block');
    expect(q('cdResults').textContent).toContain('🎓');
    expect(q('cdResults').textContent).toContain('↩️');
    expect(q('cdResultsContinue')).toBeNull();

    q('cdResultsNext').click();
    await flush();
    await flush();
    expect(calls.filter((c) => c.url.includes('/session?'))).toHaveLength(2);
    expect(q('cdResults').style.display).toBe('none');
    expect(q('cdStage').style.display).toBe('block');
    expect(q('cdProgressLabel').textContent).toBe('1');

    q('cdResultsExit').click();
    expect(navigate).toHaveBeenCalledWith('/tests');
  });

  it('always drills Chinese and reports a failed load in place', async () => {
    stubApi({ batches: [CD_ITEMS], sessionStatus: 503 });
    vi.useRealTimers();
    await startPage(CLASSIFIER);
    expect(calls[0].url).toBe('/api/classifier-drill/session?language_id=1&count=20');
    expect(q('cdLoading').textContent).toContain('(503)');
    expect(q('cdResults').style.display).toBe('none');
  });

  it('the mode toggle is remembered and re-renders the current item', async () => {
    stubApi({ batches: [CD_ITEMS] });
    vi.useRealTimers();
    await startPage(CLASSIFIER);
    container.querySelector('#cdModeToggle button[data-mode="type"]').click();
    expect(localStorage.getItem('cd_mode')).toBe('type');
    expect(q('cdTypedForm').style.display).toBe('block');
    expect(q('cdOptions').style.display).toBe('none');
    expect(q('cdLevelBadge').style.display).toBe('none');
  });
});

describe('counter drill page', () => {
  it('runs the same engine against the counter endpoints', async () => {
    stubApi({ batches: [CT_ITEMS], submit: { data: { user_elo_change: { change: -5 } } } });
    window.LinguaTestIntro = { init: vi.fn() };
    vi.useRealTimers();
    await startPage(COUNTER);

    expect(window.LinguaTestIntro.init).toHaveBeenCalledWith({ testType: 'counter_drill' });
    expect(calls[0].url).toBe('/api/counter-drill/session?language_id=3&count=20');
    expect(q('ctHeader').style.display).toBe('');
    expect(q('ctNoun').textContent).toBe('鉛筆');
    expect(q('ctProgressLabel').textContent).toBe('0');
    expect(container.querySelectorAll('.ct-option')).toHaveLength(3);

    // Feedback follows a correct answer too, with the numeral readings in order.
    option('.ct-option', '本').click();
    expect(q('ctFeedback').classList.contains('show')).toBe(true);
    expect(q('ctFeedbackCanonical').textContent).toBe('✓ 鉛筆を一本');
    expect(q('ctFeedbackNumerals').textContent).toMatch(/1本.*いっぽん.*3本.*さんぼん/);
    key('Enter');

    // Any counter the dictionary accepts is right, typed or chosen.
    container.querySelector('#ctModeToggle button[data-mode="type"]').click();
    expect(localStorage.getItem('ct_mode')).toBe('type');
    q('ctTypedInput').value = '羽';
    q('ctTypedInput').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(q('ctPromptBlank').classList.contains('correct')).toBe(true);
    expect(q('ctFeedbackCanonical').textContent).toBe('✓ 兎を一匹');
    expect(q('ctFeedbackAlts').textContent).toContain('羽');
    q('ctFeedbackContinue').click();
    await flush();
    await flush();

    const post = calls.find((c) => c.method === 'POST');
    expect(post.url).toBe('/api/counter-drill/submit');
    expect(post.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(Object.keys(post.body)).toEqual([
      'language_id',
      'correct_items',
      'total_items',
      'time_taken',
      'started_at',
      'finished_at',
      'idempotency_key',
    ]);
    expect(post.body).toMatchObject({ language_id: 3, correct_items: 2, total_items: 2 });
    expect(post.body.item_results).toBeUndefined();
    expect(q('ctHeader').style.display).toBe('none');
    expect(q('ctResultsGrade').textContent).toBe('🏆');
    expect(q('ctResultsElo').textContent).toBe('▼ -5 ELO');
  });

  it('an IME composition Enter does not submit the typed answer', async () => {
    localStorage.setItem('ct_mode', 'type');
    stubApi({ batches: [CT_ITEMS] });
    vi.useRealTimers();
    await startPage(COUNTER);
    const input = q('ctTypedInput');
    input.value = 'ほん';
    input.dispatchEvent(new Event('compositionstart'));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(q('ctFeedback').classList.contains('show')).toBe(false);
    input.dispatchEvent(new Event('compositionend'));
    input.value = '本';
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(q('ctFeedback').classList.contains('show')).toBe(true);
  });

  it('shows the empty state, and a submit failure, in place', async () => {
    stubApi({ batches: [[]] });
    vi.useRealTimers();
    await startPage(COUNTER);
    expect(q('ctEmpty').style.display).toBe('');
    expect(q('ctLoading').style.display).toBe('none');
    handle.destroy();
    document.body.innerHTML = '';

    vi.spyOn(console, 'error').mockImplementation(() => {});
    stubApi({
      batches: [[CT_ITEMS[0]]],
      submit: () => {
        throw new Error('offline');
      },
    });
    await startPage(COUNTER);
    option('.ct-option', '枚').click();
    expect(q('ctFeedbackCanonical').textContent).toBe('✕ 鉛筆を一本');
    key(' ');
    await flush();
    await flush();
    expect(q('ctResultsGrade').textContent).toBe('📚');
    expect(q('ctResultsElo').textContent).toBe('counter_drill.submit_failed');
  });

  it('reads a batch that cannot be parsed as a load failure', async () => {
    calls = [];
    window.authFetch = vi.fn(async () => ({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError('not json');
      },
    }));
    vi.useRealTimers();
    await startPage(COUNTER);
    expect(q('ctLoading').textContent).toBe('Couldn’t load the drill.');
  });
});

describe('mountDrill', () => {
  it('takes any config: the host is chosen by ctx.standalone', async () => {
    stubApi({ batches: [CT_ITEMS] });
    vi.useRealTimers();
    container = document.createElement('div');
    document.body.appendChild(container);
    const prepare = vi.fn(async () => {});
    handle = mountDrill(container, { standalone: { prepare, navigate: vi.fn() } }, COUNTER);
    await flush();
    await flush();
    expect(prepare).toHaveBeenCalledTimes(1);
    expect(q('ctStage').style.display).toBe('');
  });
});
