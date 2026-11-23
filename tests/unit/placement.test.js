/**
 * Vocabulary placement page (templates/placement.html + static/js/pages/placement.js),
 * wiki/features/vocab-placement.tech.md §8, §14 (routes), §15, §16, §19 (UI tests).
 *
 * The page markup is the real template's content block (Jinja stripped); the script
 * is the classic IIFE, evaluated into the window. `authFetch` is a scripted fake of
 * the five /api/calibration/placement routes; `LinguaI18n.t` reads the real en.json,
 * so assertions see the shipped English copy.
 *
 * Covered: the reveal state machine (parts held until the word is complete, no
 * feedback between a word's questions, auto-advance only when all ✓, one advance per
 * action), item and probe rendering (no reading on meaning items, badge, IDK hidden
 * on forced_guess, 2-option ja sound pair, keys), progress and ending, and the result
 * blocks for the zh, ja and en fixtures.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const TEMPLATE = readFileSync(join(root, 'templates/placement.html'), 'utf8');
const SCRIPT = readFileSync(join(root, 'static/js/pages/placement.js'), 'utf8');
const EN = JSON.parse(readFileSync(join(root, 'static/i18n/en.json'), 'utf8'));

const API = '/api/calibration/placement';

function contentBlock() {
  const start = TEMPLATE.indexOf('{% block content %}') + '{% block content %}'.length;
  const end = TEMPLATE.indexOf('{% endblock %}', start);
  return TEMPLATE.slice(start, end)
    .replace(/\{#[\s\S]*?#\}/g, '')
    .replace(/\{\{\s*url_for\('profile'\)\s*\}\}/g, '/profile');
}

// The real interpolation rules of i18n-manager.js (plural "a|b" with count, {name}).
function t(key, params) {
  let text = EN[key] !== undefined ? EN[key] : key;
  if (params && typeof params.count === 'number' && text.indexOf('|') !== -1) {
    const parts = text.split('|');
    text = params.count === 1 ? parts[0] : parts[1];
  }
  if (params) {
    Object.keys(params).forEach((k) => {
      text = text.replace(new RegExp('\\{' + k + '\\}', 'g'), params[k]);
    });
  }
  return text;
}

// ---------------------------------------------------------------------------
// Fixtures (payload shapes of §14 and the orchestrator's contract)
// ---------------------------------------------------------------------------

const item = (o) => ({
  band: 1,
  probe_kind: null,
  idk_allowed: true,
  prompt_key: null,
  ...o,
});

const ZH_M1 = item({
  response_id: 11,
  vocab_id: 101,
  lemma: '学习',
  kind: 'meaning',
  options: ['to study', 'to sleep', 'to eat', 'to run'],
});
const ZH_R1 = item({
  response_id: 12,
  vocab_id: 101,
  lemma: '学习',
  kind: 'reading',
  options: ['xuěxǐ', 'shuìjiào', 'xuéxí', 'shuījiāo'],
});
const ZH_M2 = item({
  response_id: 13,
  vocab_id: 102,
  lemma: '朋友',
  kind: 'meaning',
  options: ['friend', 'enemy', 'teacher', 'student'],
});
const ZH_M3 = item({
  response_id: 15,
  vocab_id: 103,
  lemma: '电脑',
  kind: 'meaning',
  options: ['computer', 'telephone', 'television', 'radio'],
});
const JA_R = item({
  response_id: 21,
  vocab_id: 201,
  lemma: '学校',
  kind: 'reading',
  options: ['がっこう', 'がっこ', 'かっこう', 'がこう'],
});

const part = (o) => ({
  probe_kind: null,
  chosen_text: null,
  key_text: null,
  is_correct: true,
  tone_only_miss: false,
  ...o,
});

const progress = (scored, minutes) => ({ scored, cap: 60, minutes_left: minutes });

const ZH_RESULT = {
  version: 1,
  word_language_id: 1,
  definition_language_id: 2,
  instrument: 'meaning_bare_v1',
  stop_reason: 'cap',
  ended_early: false,
  fast: false,
  skip_share: 0.41,
  items: { scored: 60, meaning: 39, reading: 21, probes: 3 },
  active_seconds: 408,
  words: { asked: 39, both: 12, tones_not_yet: 3, meaning_only: 4, not_yet: 20 },
  frame_n: 3623,
  this: {
    m: { lo: 900, hi: 1700, label: 'rough' },
    mr: { lo: 500, hi: 1100, label: 'rough' },
    tone_gap: { lo: 60, hi: 420 },
    gap: { lo: 120, hi: 650 },
  },
  combined: null,
  previous: null,
  seen: false,
};

const JA_RESULT = {
  ...ZH_RESULT,
  word_language_id: 3,
  words: { asked: 40, both: 15, meaning_only: 6, not_yet: 19 },
  frame_n: 3175,
  this: {
    m: { lo: 800, hi: 1500, label: 'rough' },
    mr: { lo: 450, hi: 1000, label: 'rough' },
    gap: { lo: 100, hi: 600 },
  },
};

const EN_RESULT = {
  ...ZH_RESULT,
  word_language_id: 2,
  definition_language_id: 2,
  items: { scored: 40, meaning: 40, reading: 0, probes: 1 },
  words: { asked: 40, both: 22, not_yet: 18 },
  frame_n: 3754,
  this: { m: { lo: 1200, hi: 2000, label: 'medium' }, mr: null, gap: null },
};

// ---------------------------------------------------------------------------
// Fake server
// ---------------------------------------------------------------------------

let calls;
let routes;
let docListeners;

function respond(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}
const ok = (body, status = 200) => respond(status, { status: 'success', ...body });
const err = (status, code) => respond(status, { status: 'error', error: code, error_code: code });

const started = (it0, extra) =>
  ok({ session_id: 's-1', item: it0, progress: progress(0, 7), resumed: false, ...extra }, 201);

function answered(o) {
  return ok({
    answer: { is_correct: true, skipped: false, kind: 'meaning', probe_kind: null, role: null },
    reveal: null,
    next_item: null,
    done: false,
    result: null,
    can_stop: false,
    needed: 12,
    progress: progress(1, 6.6),
    ...o,
  });
}

function installFetch() {
  window.authFetch = vi.fn(async (url, opts = {}) => {
    const method = opts.method || 'GET';
    const path = String(url).replace(API, '').split('?')[0];
    const call = { url, method, path, body: opts.body ? JSON.parse(opts.body) : undefined };
    calls.push(call);
    let h = routes[method + ' ' + path];
    if (h === undefined) h = routes[path];
    if (h === undefined) return respond(500, { status: 'error' });
    const r = typeof h === 'function' ? h(call) : Array.isArray(h) ? h.shift() : h;
    if (r instanceof Error) throw r;
    return r;
  });
}

const flush = async (n = 8) => {
  for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0));
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function boot({ lang = '1', search = '' } = {}) {
  window.history.replaceState(null, '', '/placement' + search);
  if (lang !== null) window.localStorage.setItem('selectedLanguageId', lang);
  let init = null;
  const add = document.addEventListener;
  document.addEventListener = (type, fn, ...rest) => {
    if (type === 'DOMContentLoaded') init = fn;
    else {
      // Removed after the test, so one test's page never answers another's events.
      docListeners.push([type, fn]);
      add.call(document, type, fn, ...rest);
    }
  };
  try {
    window.eval(SCRIPT);
  } finally {
    document.addEventListener = add;
  }
  if (init) await init();
  await flush();
}

const $ = (id) => document.getElementById(id);
// Text without the word joiners that keep "500–1,100" on one line.
const txt = (n) => n.textContent.replace(/⁠/g, '');
// Shown = neither the node nor any ancestor carries `hidden`.
const visible = (id) => {
  for (let n = $(id); n; n = n.parentElement) if (n.hidden) return false;
  return true;
};
const options = () => Array.from(document.querySelectorAll('#plcOptions .cal-option'));
const answerCalls = () => calls.filter((c) => c.path === '/answer');
const key = async (k) => {
  document.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true }));
  await flush();
};
const click = async (node) => {
  node.click();
  await flush();
};

async function startTest(lang = '1', first = ZH_M1) {
  routes['POST /start'] = started(first);
  await boot({ lang });
  await click($('plcStartBtn'));
}

beforeEach(() => {
  document.body.innerHTML = contentBlock();
  window.localStorage.clear();
  window.sessionStorage.clear();
  calls = [];
  docListeners = [];
  routes = { 'GET /latest': ok({ result: null, unseen: false }) };
  installFetch();
  window.LinguaI18n = { t, currentLanguage: () => 'en', init: () => Promise.resolve() };
  window.showToast = vi.fn();
  window.LinguaShell = { setTaskHeader: vi.fn() };
});

afterEach(() => {
  docListeners.forEach(([type, fn]) => document.removeEventListener(type, fn));
  delete window.authFetch;
  delete window.LinguaI18n;
  delete window.showToast;
  delete window.LinguaShell;
  delete window.LinguaPlacement;
  document.body.innerHTML = '';
});

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

describe('pure helpers', () => {
  beforeEach(() => boot());

  it('groups a word by its scored answers only (§4)', () => {
    const g = window.LinguaPlacement.wordGroup;
    const m = (ok2) => part({ kind: 'meaning', is_correct: ok2, chosen_text: 'x' });
    const r = (o) => part({ kind: 'reading', ...o });
    expect(g([m(true), r({ is_correct: true })])).toBe('both');
    expect(g([m(true), r({ is_correct: false, tone_only_miss: true, chosen_text: 'xuěxǐ' })])).toBe(
      'tones_not_yet'
    );
    expect(g([m(true), r({ is_correct: false, chosen_text: 'shuìjiào' })])).toBe('meaning_only');
    expect(g([m(true), r({ is_correct: false, chosen_text: null })])).toBe('meaning_only');
    // reading-exempt (ja kana-only, en): meaning alone is enough
    expect(g([m(true)])).toBe('both');
    expect(g([m(false)])).toBe('not_yet');
    // probes never move a word between groups
    expect(g([m(false), r({ probe_kind: 'reading_after_miss', is_correct: true })])).toBe(
      'not_yet'
    );
    expect(
      g([
        part({ kind: 'meaning', is_correct: false, chosen_text: null }),
        part({ kind: 'meaning', probe_kind: 'forced_guess', is_correct: true }),
      ])
    ).toBe('not_yet');
    expect(
      g([m(true), r({ is_correct: true }), r({ probe_kind: 'sound_pair', is_correct: false })])
    ).toBe('both');
    // a recheck probe alone is not one of this test's words
    expect(g([r({ probe_kind: 'recheck', is_correct: true })])).toBe(null);
  });

  it('auto-advances only when every part is right', () => {
    const a = window.LinguaPlacement.allCorrect;
    expect(a([part({}), part({})])).toBe(true);
    expect(a([part({}), part({ is_correct: false })])).toBe(false);
    expect(a([])).toBe(false);
  });

  it('draws one dot per 5% of the pool: below lo, the range, above hi', () => {
    const dots = window.LinguaPlacement.bandDots(900, 1700, 3623, 20);
    expect(dots).toHaveLength(20);
    expect(dots.filter((d) => d === 'in')).toHaveLength(4);
    expect(dots.filter((d) => d === 'range')).toHaveLength(6);
    expect(dots.slice(10).every((d) => d === 'out')).toBe(true);
    expect(window.LinguaPlacement.bandDots(0, 400, 3623, 20).filter((d) => d === 'in')).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Boot, intro, start
// ---------------------------------------------------------------------------

describe('boot and intro', () => {
  it('asks /latest for the study language, then shows the intro with the time and the IDK hint', async () => {
    await boot({ lang: '1' });
    expect(calls[0]).toMatchObject({ method: 'GET', url: API + '/latest?word_language_id=1' });
    expect(visible('plcIntro')).toBe(true);
    expect($('plcIntroTime').textContent).toBe('About 7 minutes');
    expect($('plcIntro').textContent).toContain('If you have no idea, choose “I don');
    expect(visible('plcStartBtn')).toBe(true);
    expect(visible('plcStrip')).toBe(false);
  });

  it('says about 7 minutes for ja and about 5 for en', async () => {
    await boot({ lang: '3' });
    expect($('plcIntroTime').textContent).toBe('About 7 minutes');
    document.body.innerHTML = contentBlock();
    await boot({ lang: '2' });
    expect($('plcIntroTime').textContent).toBe('About 5 minutes');
  });

  it('takes the language from ?lang= (code or id) over the stored one', async () => {
    await boot({ lang: '1', search: '?lang=en' });
    expect(calls[0].url).toBe(API + '/latest?word_language_id=2');
    expect($('plcIntroTime').textContent).toBe('About 5 minutes');
  });

  it('shows "not available" when the API answers 404 (language not enabled)', async () => {
    routes['GET /latest'] = err(404, 'NOT_FOUND');
    await boot();
    expect(visible('plcMessage')).toBe(true);
    expect($('plcMessage').textContent).toBe(EN['placement.unavailable']);
    expect(calls.some((c) => c.path === '/start')).toBe(false);
  });

  it('shows "not available" when /start answers 404', async () => {
    routes['POST /start'] = err(404, 'NOT_FOUND');
    await boot();
    await click($('plcStartBtn'));
    expect($('plcMessage').textContent).toBe(EN['placement.unavailable']);
  });

  it('shows an unseen abandoned result first, with a way to take a new placement', async () => {
    routes['GET /latest'] = ok({
      result: { ...ZH_RESULT, stop_reason: 'abandoned', ended_early: true },
      unseen: true,
    });
    await boot();
    expect(visible('plcResult')).toBe(true);
    expect(visible('plcIntro')).toBe(false);
    expect($('plcResult').textContent).toContain('You ended early, so the range is wider.');
    expect(visible('plcNewBtn')).toBe(true);
    await click($('plcNewBtn'));
    expect(visible('plcIntro')).toBe(true);
  });

  it('renders nothing from translations until they have loaded', async () => {
    let loaded;
    window.LinguaI18n.init = () => new Promise((r) => (loaded = r));
    // The header subtitle slot (base.html task_subtitle block).
    document.body.insertAdjacentHTML('afterbegin', '<span id="plcLangName"></span>');
    await boot();
    // /latest has answered, but the intro waits for the strings.
    expect(calls[0].path).toBe('/latest');
    expect(visible('plcIntro')).toBe(false);
    expect(visible('plcLoading')).toBe(true);
    loaded();
    await flush();
    expect(visible('plcIntro')).toBe(true);
    expect($('plcIntroTime').textContent).toBe('About 7 minutes');
    // The subtitle carries its key, so a later language switch re-translates it.
    expect($('plcLangName').textContent).toBe('Chinese');
    expect($('plcLangName').getAttribute('data-i18n')).toBe('lang_select.name_zh');
  });

  it('re-renders the result on a UI-language switch', async () => {
    routes['GET /latest'] = ok({ result: ZH_RESULT, unseen: true });
    await boot();
    expect($('plcResult').querySelector('h1').textContent).toBe('Your placement result');
    window.LinguaI18n.t = (k, p) => '«' + t(k, p) + '»';
    document.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: 'es' } }));
    expect($('plcResult').querySelector('h1').textContent).toBe('«Your placement result»');
    expect(visible('plcNewBtn')).toBe(true);
  });

  it('keeps a number range on one line (word joiners around the dash)', async () => {
    routes['GET /latest'] = ok({ result: ZH_RESULT, unseen: true });
    await boot();
    expect(document.querySelector('.plc-range__text').textContent).toContain('500⁠–⁠1,100');
  });

  it('ignores a result the learner has already seen', async () => {
    routes['GET /latest'] = ok({ result: ZH_RESULT, unseen: false });
    await boot();
    expect(visible('plcIntro')).toBe(true);
  });

  it('starts with the word and definition languages; Enter on the intro starts too', async () => {
    routes['POST /start'] = started(ZH_M1);
    await boot({ lang: '1' });
    await key('Enter');
    const s = calls.find((c) => c.path === '/start');
    expect(s.body).toEqual({ word_language_id: 1, definition_language_id: 2 });
    expect(visible('plcItem')).toBe(true);
    expect(calls.filter((c) => c.path === '/start')).toHaveLength(1);
  });

  it('a resumed session says so and shows its pending item', async () => {
    routes['POST /start'] = started(ZH_R1, { resumed: true, progress: progress(9, 5) });
    await boot();
    await click($('plcStartBtn'));
    expect(window.showToast).toHaveBeenCalledWith(EN['placement.resumed'], 'info');
    expect($('plcPrompt').textContent).toBe('学习');
    expect($('plcInstruction').textContent).toBe('Choose the pinyin');
  });

  it('429 over the daily start limit says so', async () => {
    routes['POST /start'] = err(429, 'RATE_LIMITED');
    await boot();
    await click($('plcStartBtn'));
    expect($('plcMessage').textContent).toBe(EN['placement.rate_limited']);
  });
});

// ---------------------------------------------------------------------------
// Items and probes
// ---------------------------------------------------------------------------

describe('item rendering', () => {
  it('a meaning item shows the word only: no reading, even if a payload carried one', async () => {
    await startTest('1', { ...ZH_M1, pronunciation: 'xuéxí', reading: 'xuéxí' });
    expect($('plcPrompt').textContent).toBe('学习');
    expect($('plcPrompt').lang).toBe('zh');
    expect($('plcInstruction').textContent).toBe('Choose the meaning');
    expect(options().map((b) => b.textContent)).toEqual([
      '1to study',
      '2to sleep',
      '3to eat',
      '4to run',
    ]);
    expect($('plcItem').textContent).not.toContain('xuéxí');
    expect(document.body.textContent).not.toContain('xuéxí');
    expect($('plcOptions').classList.contains('pron')).toBe(false);
    expect(visible('plcProbeBadge')).toBe(false);
    expect(visible('plcIdkBtn')).toBe(true);
  });

  it('zh reading items ask for the pinyin, ja ones for the reading, in the word language', async () => {
    await startTest('1', ZH_R1);
    expect($('plcInstruction').textContent).toBe('Choose the pinyin');
    expect($('plcOptions').classList.contains('pron')).toBe(true);
    expect(options()[0].querySelector('.cal-option-text').lang).toBe('zh');

    document.body.innerHTML = contentBlock();
    await startTest('3', JA_R);
    expect($('plcInstruction').textContent).toBe('Choose the reading');
    expect($('plcPrompt').lang).toBe('ja');
  });

  it('labels every probe "Extra question — not scored"', async () => {
    await startTest('1', { ...ZH_R1, probe_kind: 'reading_after_miss' });
    expect(visible('plcProbeBadge')).toBe(true);
    expect($('plcProbeBadge').textContent).toBe('Extra question — not scored');
  });

  it('forced_guess hides "I don\'t know", says "Your best guess", and ignores key 0', async () => {
    await startTest('1', {
      ...ZH_M1,
      response_id: 31,
      probe_kind: 'forced_guess',
      idk_allowed: false,
    });
    expect(visible('plcIdkBtn')).toBe(false);
    expect($('plcInstruction').textContent).toBe('Your best guess');
    expect(visible('plcProbeBadge')).toBe(true);
    await key('0');
    expect(answerCalls()).toHaveLength(0);
  });

  it('the ja sound_pair probe shows 2 options and only keys 1–2 answer', async () => {
    routes['POST /answer'] = answered({});
    await startTest('3', {
      ...JA_R,
      response_id: 41,
      probe_kind: 'sound_pair',
      options: ['がっこう', 'がこう'],
    });
    expect(options()).toHaveLength(2);
    expect($('plcInstruction').textContent).toBe(EN['placement.sound_pair_prompt']);
    expect(visible('plcProbeBadge')).toBe(true);
    await key('3');
    expect(answerCalls()).toHaveLength(0);
    await key('2');
    expect(answerCalls()).toHaveLength(1);
    expect(answerCalls()[0].body.position).toBe(1);
  });

  it('keys 1–4 send positions 0–3 and key 0 sends null, with a latency', async () => {
    routes['POST /answer'] = [answered({ next_item: ZH_M2 }), answered({ next_item: ZH_M3 })];
    await startTest();
    await key('4');
    expect(answerCalls()[0].body).toMatchObject({
      session_id: 's-1',
      response_id: 11,
      position: 3,
    });
    expect(typeof answerCalls()[0].body.latency_ms).toBe('number');
    expect(answerCalls()[0].body.latency_ms).toBeGreaterThanOrEqual(0);
    await key('0');
    expect(answerCalls()[1].body).toMatchObject({ response_id: 13, position: null });
  });

  it('highlights the tapped option and locks the item while the request is in flight', async () => {
    let release;
    routes['POST /answer'] = () =>
      new Promise((r) => {
        release = () => r(answered({ next_item: ZH_R1 }));
      });
    await startTest();
    await click(options()[1]);
    expect(options()[1].classList.contains('picked')).toBe(true);
    expect(options()[1].querySelector('.cal-badge').innerHTML).toContain('svg');
    expect(options().every((b) => b.disabled)).toBe(true);
    // a second tap or key while in flight answers nothing
    await click(options()[2]);
    await key('3');
    expect(answerCalls()).toHaveLength(1);
    release();
    await flush();
    expect($('plcPrompt').textContent).toBe('学习');
    expect($('plcInstruction').textContent).toBe('Choose the pinyin');
  });

  it('marks "I don\'t know" as tapped while in flight', async () => {
    routes['POST /answer'] = () => new Promise(() => {});
    await startTest();
    await click($('plcIdkBtn'));
    expect($('plcIdkBtn').classList.contains('picked')).toBe(true);
    expect(answerCalls()[0].body.position).toBe(null);
  });
});

// ---------------------------------------------------------------------------
// Reveal state machine
// ---------------------------------------------------------------------------

describe('reveal state machine', () => {
  const zhRevealAllRight = {
    lemma: '学习',
    reading: 'xuéxí',
    meaning: 'to study',
    parts: [
      part({ kind: 'meaning', chosen_text: 'to study', key_text: 'to study' }),
      part({ kind: 'reading', chosen_text: 'xuéxí', key_text: 'xuéxí' }),
    ],
  };

  it('holds the meaning answer without feedback, then reveals the whole word once', async () => {
    routes['POST /answer'] = [
      answered({ next_item: ZH_R1 }),
      answered({
        answer: { is_correct: true, skipped: false, kind: 'reading', probe_kind: null, role: 'K' },
        reveal: zhRevealAllRight,
        next_item: ZH_M2,
        progress: progress(2, 6.3),
      }),
    ];
    await startTest();
    await click(options()[0]);
    // The meaning answer is held: no reveal, no ✓/✗, straight to the reading item.
    expect(visible('plcReveal')).toBe(false);
    expect(document.querySelector('.cal-option.correct, .cal-option.wrong')).toBe(null);
    expect($('plcInstruction').textContent).toBe('Choose the pinyin');
    await click(options()[2]);
    expect(visible('plcReveal')).toBe(true);
    const reveal = $('plcReveal');
    expect(reveal.querySelector('.plc-reveal__word').textContent).toBe('学习');
    expect(reveal.querySelector('.plc-reveal__word').lang).toBe('zh');
    expect(reveal.querySelector('.plc-reveal__reading').textContent).toBe('xuéxí');
    expect(reveal.querySelector('.plc-reveal__meaning').textContent).toBe('to study');
    expect(reveal.querySelectorAll('.plc-part--right')).toHaveLength(2);
  });

  it('all ✓ auto-advances after 450 ms without a Next button', async () => {
    routes['POST /answer'] = [
      answered({ next_item: ZH_R1 }),
      answered({ reveal: zhRevealAllRight, next_item: ZH_M2 }),
    ];
    await startTest();
    await click(options()[0]);
    await click(options()[2]);
    expect(visible('plcReveal')).toBe(true);
    expect(visible('plcNextBtn')).toBe(false);
    await sleep(200);
    expect(visible('plcReveal')).toBe(true);
    await sleep(350);
    await flush();
    expect(visible('plcItem')).toBe(true);
    expect($('plcPrompt').textContent).toBe('朋友');
  });

  it('a miss waits for "Next word"; Enter moves on exactly once', async () => {
    routes['POST /answer'] = [
      answered({
        answer: {
          is_correct: false,
          skipped: false,
          kind: 'meaning',
          probe_kind: null,
          role: null,
        },
        reveal: {
          lemma: '学习',
          reading: 'xuéxí',
          meaning: 'to study',
          parts: [part({ kind: 'meaning', is_correct: false, chosen_text: 'to eat' })],
        },
        next_item: ZH_M2,
      }),
    ];
    await startTest();
    await click(options()[2]);
    expect(visible('plcReveal')).toBe(true);
    expect(visible('plcNextBtn')).toBe(true);
    const wrong = $('plcReveal').querySelector('.plc-part--wrong');
    expect(wrong.textContent).toContain('Meaning');
    expect(wrong.textContent).toContain('You chose: to eat');
    await sleep(600);
    expect(visible('plcReveal')).toBe(true); // no timer on a miss
    const before = calls.length;
    await key('Enter');
    await key('Enter');
    await click($('plcNextBtn'));
    expect($('plcPrompt').textContent).toBe('朋友');
    expect(visible('plcItem')).toBe(true);
    expect(calls.length).toBe(before); // nothing else was fetched or answered
  });

  it('the timer and a key together advance once (one advance per action)', async () => {
    routes['POST /answer'] = [
      answered({ next_item: ZH_R1 }),
      answered({ reveal: zhRevealAllRight, next_item: ZH_M2 }),
    ];
    await startTest();
    await click(options()[0]);
    await click(options()[2]);
    const before = calls.length;
    await key('Enter');
    expect($('plcPrompt').textContent).toBe('朋友');
    await sleep(500);
    await key(' ');
    expect($('plcPrompt').textContent).toBe('朋友');
    expect(visible('plcItem')).toBe(true);
    expect(calls.length).toBe(before);
  });

  it('marks a zh tone-only miss "Right pinyin, wrong tones" with the chosen option', async () => {
    routes['POST /answer'] = [
      answered({ next_item: ZH_R1 }),
      answered({
        answer: {
          is_correct: false,
          skipped: false,
          kind: 'reading',
          probe_kind: null,
          role: 'KT',
        },
        reveal: {
          lemma: '学习',
          reading: 'xuéxí',
          meaning: 'to study',
          parts: [
            part({ kind: 'meaning', chosen_text: 'to study' }),
            part({
              kind: 'reading',
              is_correct: false,
              chosen_text: 'xuěxǐ',
              key_text: 'xuéxí',
              tone_only_miss: true,
            }),
          ],
        },
        next_item: ZH_M2,
      }),
    ];
    await startTest();
    await click(options()[0]);
    await click(options()[0]);
    const miss = $('plcReveal').querySelector('.plc-part--wrong');
    expect(miss.textContent).toContain('Pinyin');
    expect(miss.textContent).toContain('You chose: xuěxǐ');
    expect(miss.querySelector('.plc-part__tones').textContent).toBe('Right pinyin, wrong tones');
    expect(miss.querySelector('.plc-part__chosen').lang).toBe('zh');
    expect(visible('plcNextBtn')).toBe(true);
  });

  it('a skipped meaning is shown as "I don\'t know", and a probe part keeps its badge', async () => {
    routes['POST /answer'] = [
      answered({
        answer: { is_correct: false, skipped: true, kind: 'meaning', probe_kind: null, role: null },
        next_item: { ...ZH_M1, response_id: 32, probe_kind: 'forced_guess', idk_allowed: false },
      }),
      answered({
        reveal: {
          lemma: '学习',
          reading: 'xuéxí',
          meaning: 'to study',
          parts: [
            part({ kind: 'meaning', is_correct: false, chosen_text: null }),
            part({ kind: 'meaning', probe_kind: 'forced_guess', chosen_text: 'to study' }),
          ],
        },
        next_item: ZH_M2,
      }),
    ];
    await startTest();
    await key('0');
    expect($('plcInstruction').textContent).toBe('Your best guess');
    expect(visible('plcReveal')).toBe(false);
    await key('1');
    const parts = $('plcReveal').querySelectorAll('.plc-part');
    expect(parts[0].classList.contains('plc-part--skipped')).toBe(true);
    expect(parts[0].textContent).toContain("I don't know");
    expect(parts[1].dataset.probe).toBe('forced_guess');
    expect(parts[1].textContent).toContain('Extra question — not scored');
    expect(visible('plcNextBtn')).toBe(true); // not all ✓
  });

  it('retries a network error once with the same answer', async () => {
    routes['POST /answer'] = [new TypeError('Failed to fetch'), answered({ next_item: ZH_R1 })];
    await startTest();
    await click(options()[0]);
    expect(answerCalls()).toHaveLength(2);
    expect(answerCalls()[1].body).toEqual(answerCalls()[0].body);
    expect($('plcInstruction').textContent).toBe('Choose the pinyin');
  });

  it('after a second failure the item is unlocked again with an error toast', async () => {
    routes['POST /answer'] = [new TypeError('x'), respond(503, { status: 'error' })];
    await startTest();
    await click(options()[0]);
    expect(answerCalls()).toHaveLength(2);
    expect(window.showToast).toHaveBeenCalledWith(EN['placement.error_answer']);
    expect(options().every((b) => !b.disabled)).toBe(true);
    expect(options()[0].classList.contains('picked')).toBe(false);
  });

  it('an "already answered" 4xx re-syncs through /result, then /start (resume)', async () => {
    routes['POST /answer'] = err(400, 'BAD_REQUEST');
    routes['GET /result'] = err(404, 'NOT_FOUND');
    await startTest();
    routes['POST /start'] = started(ZH_M2, { resumed: true });
    await click(options()[0]);
    expect(calls.map((c) => c.method + ' ' + c.path)).toEqual([
      'GET /latest',
      'POST /start',
      'POST /answer',
      'GET /result',
      'POST /start',
    ]);
    expect($('plcPrompt').textContent).toBe('朋友');
  });
});

// ---------------------------------------------------------------------------
// Progress and ending
// ---------------------------------------------------------------------------

describe('progress and ending', () => {
  it('shows "about N minutes left" and the bar from the server progress', async () => {
    routes['POST /answer'] = answered({
      next_item: ZH_R1,
      progress: { scored: 30, cap: 60, minutes_left: 1.2 },
    });
    await startTest();
    expect(visible('plcStrip')).toBe(true);
    expect($('plcMinutes').textContent).toBe('About 7 minutes left');
    await click(options()[0]);
    expect($('plcMinutes').textContent).toBe('About 1 minute left');
    expect($('plcBar').style.width).toBe('50%');
  });

  it('before eligibility, "End now" asks for confirmation with the answers still needed', async () => {
    routes['POST /end'] = ok({ not_enough: true, needed: 7 });
    await startTest();
    expect(visible('plcEndBtn')).toBe(true);
    expect(visible('plcStopBtn')).toBe(false);
    await click($('plcEndBtn'));
    expect(calls.find((c) => c.path === '/end').body).toEqual({ session_id: 's-1' });
    expect(visible('plcConfirm')).toBe(true);
    expect($('plcConfirmText').textContent).toBe(
      'Not enough answers yet for a result — answer 7 more, or leave and come back within 24 hours.'
    );
    expect(document.getElementById('plcLeave').getAttribute('href')).toBe('/profile');
    await click($('plcKeepGoing'));
    expect(visible('plcConfirm')).toBe(false);
    expect(visible('plcItem')).toBe(true);
  });

  it('once can_stop holds, "Stop here and see your result" ends with a result', async () => {
    routes['POST /answer'] = answered({ next_item: ZH_R1, can_stop: true });
    routes['POST /end'] = ok({
      result: { ...ZH_RESULT, stop_reason: 'learner', ended_early: true },
    });
    await startTest();
    await click(options()[0]);
    expect(visible('plcStopBtn')).toBe(true);
    expect($('plcStopBtn').textContent).toBe('Stop here and see your result');
    expect(visible('plcEndBtn')).toBe(false);
    await click($('plcStopBtn'));
    expect(visible('plcResult')).toBe(true);
    expect(visible('plcStrip')).toBe(false);
    expect($('plcResult').textContent).toContain('You ended early, so the range is wider.');
  });

  it('a final word that completes the test reveals, then shows the result', async () => {
    routes['POST /answer'] = [
      answered({ next_item: ZH_R1 }),
      answered({
        reveal: {
          lemma: '学习',
          reading: 'xuéxí',
          meaning: 'to study',
          parts: [
            part({ kind: 'meaning', chosen_text: 'to study' }),
            part({ kind: 'reading', is_correct: false, chosen_text: 'shuìjiào' }),
          ],
        },
        done: true,
        result: ZH_RESULT,
      }),
    ];
    await startTest();
    await click(options()[0]);
    await click(options()[1]);
    expect(visible('plcReveal')).toBe(true);
    await click($('plcNextBtn'));
    expect(visible('plcResult')).toBe(true);
    // The word this tab saw is listed in its group.
    const group = document.querySelector('.plc-group[data-group="meaning_only"]');
    await click(group.querySelector('button'));
    expect(group.querySelector('.plc-word__lemma').textContent).toBe('学习');
    expect(group.querySelector('.plc-word__lemma').lang).toBe('zh');
    expect(group.querySelector('a.plc-action').getAttribute('href')).toBe('/session');
    expect(group.querySelector('a.plc-action').textContent).toBe('Practise these readings');
  });
});

// ---------------------------------------------------------------------------
// Result rendering (§8 blocks, in order)
// ---------------------------------------------------------------------------

async function showResultFixture(result, lang, extra) {
  routes['GET /latest'] = ok({ result, unseen: true, ...extra });
  await boot({ lang });
  return $('plcResult');
}

const blockOrder = (r) =>
  Array.from(r.children)
    .map((c) => (c.className.match(/plc-(groups|range|gaps|retake|next|how|flags)\b/) || [])[1])
    .filter(Boolean);

describe('result rendering', () => {
  it('zh: groups (with the tones group), range, gaps, next steps, how, in that order', async () => {
    const r = await showResultFixture(ZH_RESULT, '1');
    expect(blockOrder(r)).toEqual(['groups', 'range', 'gaps', 'next', 'how']);
    expect(r.querySelector('.plc-groups').textContent).toContain('Your answers (guesses included)');
    expect(r.querySelector('.plc-groups__of').textContent).toBe('Of the 39 words you were asked:');
    const rows = Array.from(r.querySelectorAll('.plc-group')).map(
      (g) =>
        g.querySelector('.plc-group__count').textContent +
        ' ' +
        g.querySelector('.plc-group__label').textContent
    );
    expect(rows).toEqual([
      '12 meaning and reading',
      '3 meaning and pinyin, not the tones',
      '4 meaning, not the reading',
      '20 not yet recognised',
    ]);
    expect(txt(r.querySelector('.plc-range__text'))).toBe(
      'Across the 3,623 Chinese words the check draws from, you recognised the meaning and the reading of about 500–1,100.'
    );
    expect(r.querySelector('.plc-range__label').textContent).toBe('Rough estimate');
    expect(r.querySelectorAll('.plc-band circle')).toHaveLength(20);
    expect(r.querySelector('.plc-band').getAttribute('role')).toBe('img');
    const gaps = Array.from(r.querySelectorAll('.plc-gap')).map(txt);
    expect(gaps).toEqual([
      'You also recognised the meaning and the pinyin, but not the tones, of about 60–420 more.',
      'You also recognised the meaning, but not the reading, of about 120–650 more.',
    ]);
    const next = Array.from(r.querySelectorAll('.plc-next a')).map((a) => [
      a.textContent,
      a.getAttribute('href'),
    ]);
    expect(next).toEqual([
      ['Practise these readings', '/session'],
      ['Learn these', '/session'],
      ["Start today's session", '/session'],
      ['Narrow your range: continue the vocabulary check', '/calibration'],
    ]);
    expect(r.querySelector('.plc-how__tones').textContent).toContain(
      'the reading includes the tones'
    );
    expect(r.querySelector('.plc-how').textContent).toContain(EN['placement.how_body_cjk']);
  });

  it('zh: each gap line appears only when the result has it', async () => {
    const r = await showResultFixture(
      { ...ZH_RESULT, this: { ...ZH_RESULT.this, tone_gap: null, gap: null } },
      '1'
    );
    expect(r.querySelector('.plc-gaps')).toBe(null);
    document.body.innerHTML = contentBlock();
    const r2 = await showResultFixture(
      { ...ZH_RESULT, this: { ...ZH_RESULT.this, tone_gap: null } },
      '1'
    );
    expect(Array.from(r2.querySelectorAll('.plc-gap')).map((p) => p.className)).toEqual([
      'plc-gap plc-gap--reading',
    ]);
  });

  it('ja: three groups (no tones group), the m+r range and the reading gap', async () => {
    const r = await showResultFixture(JA_RESULT, '3');
    expect(Array.from(r.querySelectorAll('.plc-group')).map((g) => g.dataset.group)).toEqual([
      'both',
      'meaning_only',
      'not_yet',
    ]);
    expect(txt(r.querySelector('.plc-range__text'))).toBe(
      'Across the 3,175 Japanese words the check draws from, you recognised the meaning and the reading of about 450–1,000.'
    );
    expect(r.querySelector('.plc-gap--tones')).toBe(null);
    expect(txt(r.querySelector('.plc-gap--reading'))).toContain('100–600');
    expect(r.querySelector('.plc-how__tones')).toBe(null);
  });

  it('en: "recognised · not yet recognised", the meaning range, no gaps, no reading actions', async () => {
    const r = await showResultFixture(EN_RESULT, '2');
    expect(blockOrder(r)).toEqual(['groups', 'range', 'next', 'how']);
    const labels = Array.from(r.querySelectorAll('.plc-group__label')).map((s) => s.textContent);
    expect(labels).toEqual(['recognised', 'not yet recognised']);
    expect(txt(r.querySelector('.plc-range__text'))).toBe(
      'Across the 3,754 English words the check draws from, you recognised the meaning of about 1,200–2,000.'
    );
    expect(r.querySelector('.plc-range__label').textContent).toBe('Medium estimate');
    expect(r.textContent).not.toContain('Practise these readings');
    expect(r.querySelector('.plc-how').textContent).toContain(EN['placement.how_body_en']);
  });

  it('lo = 0 uses the beginner phrasing', async () => {
    const r = await showResultFixture(
      { ...ZH_RESULT, this: { ...ZH_RESULT.this, mr: { lo: 0, hi: 400, label: 'rough' } } },
      '1'
    );
    expect(txt(r.querySelector('.plc-range__text'))).toBe(
      "Most of the check's words are still new to you (fewer than 400 of 3,623)."
    );
  });

  it('the retake block appears only with result.previous, with the verdict and the combined range', async () => {
    const withPrev = {
      ...ZH_RESULT,
      previous: {
        session_id: 'old',
        ended_at: '2026-10-02T10:00:00Z',
        mr: { lo: 200, hi: 700 },
        verdict: 'up',
      },
      combined: { m: { lo: 1000, hi: 1600 }, mr: { lo: 600, hi: 1000, label: 'rough' } },
    };
    const r = await showResultFixture(withPrev, '1');
    expect(blockOrder(r)).toEqual(['groups', 'range', 'gaps', 'retake', 'next', 'how']);
    const retake = r.querySelector('.plc-retake');
    expect(txt(retake.querySelector('.plc-retake__this'))).toBe('This placement: 500–1,100');
    expect(txt(retake.querySelector('.plc-retake__previous'))).toMatch(
      /^Previous \(.*2026.*\): 200–700$/
    );
    expect(retake.querySelector('.plc-retake__verdict').textContent).toBe('Clearly up');
    expect(txt(retake.querySelector('.plc-retake__combined'))).toBe(
      'Combined with your earlier answers: 600–1,000'
    );

    document.body.innerHTML = contentBlock();
    const r2 = await showResultFixture(
      { ...withPrev, previous: { ...withPrev.previous, verdict: 'same' }, combined: null },
      '1'
    );
    expect(r2.querySelector('.plc-retake__verdict').textContent).toBe('Not clearly different');
    expect(r2.querySelector('.plc-retake__combined')).toBe(null);
  });

  it('flags come last: ended early and fast', async () => {
    const r = await showResultFixture({ ...ZH_RESULT, ended_early: true, fast: true }, '1');
    expect(blockOrder(r).at(-1)).toBe('flags');
    expect(Array.from(r.querySelectorAll('.plc-flag')).map((p) => p.textContent)).toEqual([
      'You ended early, so the range is wider.',
      EN['placement.fast_flag'],
    ]);
  });

  it('groups open in place to the server word lists and their action', async () => {
    const r = await showResultFixture(ZH_RESULT, '1', {
      session_id: 's-9',
      word_lists: {
        not_yet: [{ lemma: '电脑', reading: 'diànnǎo', meaning: 'computer' }],
        both: ['朋友'],
      },
    });
    const notYet = r.querySelector('.plc-group[data-group="not_yet"]');
    const head = notYet.querySelector('button.plc-group__head');
    expect(head.getAttribute('aria-expanded')).toBe('false');
    await click(head);
    expect(head.getAttribute('aria-expanded')).toBe('true');
    expect(notYet.querySelector('.plc-word__lemma').textContent).toBe('电脑');
    expect(notYet.querySelector('.plc-word__reading').textContent).toBe('diànnǎo');
    expect(notYet.querySelector('a.plc-action').textContent).toBe('Learn these');
    const both = r.querySelector('.plc-group[data-group="both"]');
    await click(both.querySelector('button'));
    expect(both.querySelector('.plc-word__lemma').textContent).toBe('朋友');
    expect(both.querySelector('a.plc-action')).toBe(null);
  });

  it('adds "(up to k today)" when a group is larger than the remaining new-word budget', async () => {
    const r = await showResultFixture(ZH_RESULT, '1', { new_word_budget_left: 8 });
    const learn = Array.from(r.querySelectorAll('.plc-next a')).find((a) =>
      a.textContent.startsWith('Learn these')
    );
    expect(learn.textContent).toBe('Learn these (up to 8 today)');
  });

  it('a group with no words is not tappable', async () => {
    const r = await showResultFixture(
      { ...ZH_RESULT, words: { ...ZH_RESULT.words, tones_not_yet: 0 } },
      '1'
    );
    const tones = r.querySelector('.plc-group[data-group="tones_not_yet"]');
    expect(tones.querySelector('button')).toBe(null);
    expect(tones.querySelector('.plc-group__count').textContent).toBe('0');
  });

  it('never states an exam level, a pass/fail or praise', async () => {
    for (const [res, lang] of [
      [ZH_RESULT, '1'],
      [JA_RESULT, '3'],
      [EN_RESULT, '2'],
    ]) {
      document.body.innerHTML = contentBlock();
      const r = await showResultFixture(res, lang);
      expect(r.textContent).not.toMatch(/\b(HSK|JLPT|level|pass|fail|great|excellent)\b/i);
      expect(r.textContent.replace(/I don't know/g, '')).not.toMatch(/\bknow\b/i);
    }
  });
});
