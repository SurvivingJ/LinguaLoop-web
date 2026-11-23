/**
 * static/js/pages/knowledge.js — the "My vocabulary" summary page (TASK-1040, TASK-1041).
 * wiki/features/knowledge-report.tech.md §3.1, §4, §10, §13.
 *
 * The page markup is the real template's content block (Jinja tags stripped); the script is the
 * classic IIFE, evaluated into the window. LinguaI18n is a stand-in that reads static/i18n/en.json
 * with i18n-manager.js's plural and interpolation rules, so a key missing from en.json shows up as
 * its raw key text and fails the "no raw keys" checks.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const TEMPLATE = readFileSync(join(root, 'templates/knowledge.html'), 'utf8');
const SCRIPT = readFileSync(join(root, 'static/js/pages/knowledge.js'), 'utf8');
const EN = JSON.parse(readFileSync(join(root, 'static/i18n/en.json'), 'utf8'));

function markup() {
  const content = TEMPLATE.split('{% block content %}')[1].split('{% endblock %}')[0];
  return content
    .replace(/\{#[\s\S]*?#\}/g, '')
    .replace(/\{%[\s\S]*?%\}/g, '')
    .replace(/\{\{[\s\S]*?\}\}/g, '#');
}

function t(key, params) {
  let text = EN[key] !== undefined ? EN[key] : key;
  if (params && typeof params.count === 'number' && text.indexOf('|') !== -1) {
    const parts = text.split('|');
    text = params.count === 1 ? parts[0] : parts[1];
  }
  if (params) {
    Object.keys(params).forEach((p) => {
      text = text.replace(new RegExp('\\{' + p + '\\}', 'g'), params[p]);
    });
  }
  return text;
}

// The de6fd05b/ja summary as services/vocabulary/knowledge_report.summary() builds it (§6.3).
function full() {
  return {
    status: 'success',
    language_id: 3,
    language: { id: 3, code: 'ja', name: 'Japanese' },
    as_of: '2026-11-17T12:00:00+00:00',
    method_version: 1,
    detail: { level: 0, enforced: false, preview: true },
    state: null,
    stale_days: null,
    few_tracked: false,
    estimate: {
      shown: true,
      kind: 'range',
      lo: 850,
      hi: 1400,
      label: 'medium',
      rel: 0.232,
      universe_words: 3175,
      definition_language_id: 2,
      answers: 172,
      first_answer_at: '2026-09-13',
      last_answer_at: '2026-11-15',
      reason: null,
      have: null,
      answers_needed: null,
      disagreement: false,
      rated_known_in_frame: 60,
      tick: 1111,
    },
    rated_known_words: 69,
    tracked_words: 251,
    groups: [
      {
        group: 'most_common',
        universe: 77,
        answers: 23,
        shown: true,
        share_lo: 0.73,
        share_hi: 1.0,
        tracked: 40,
        rated_known: 18,
      },
      {
        group: 'common',
        universe: 820,
        answers: 50,
        shown: false,
        share_lo: null,
        share_hi: null,
        tracked: 100,
        rated_known: 31,
      },
      {
        group: 'mid',
        universe: 1276,
        answers: 50,
        shown: true,
        share_lo: 0.17,
        share_hi: 0.47,
        tracked: 70,
        rated_known: 15,
      },
      {
        group: 'rare',
        universe: 1002,
        answers: 49,
        shown: true,
        share_lo: 0.08,
        share_hi: 0.35,
        tracked: 38,
        rated_known: 5,
      },
      {
        group: 'none',
        universe: null,
        answers: 0,
        shown: false,
        share_lo: null,
        share_hi: null,
        tracked: 3,
        rated_known: 0,
      },
    ],
    lists: [],
    lists_unavailable: false,
    watchlist: null,
    growth: {
      idle60: 95,
      d30: {
        practised: 41,
        direct_checks: 164,
        met_in_texts: 44,
        rated_known_delta: null,
        anchor_date: null,
        since: false,
        first_trend_on: '2026-12-01',
        estimate_change: null,
        pool_changed: null,
      },
      d90: {
        practised: 83,
        direct_checks: 318,
        met_in_texts: 142,
        rated_known_delta: null,
        anchor_date: null,
        since: false,
        first_trend_on: '2026-12-01',
        estimate_change: null,
        pool_changed: null,
      },
    },
    skills: {
      families: [
        {
          family: 'form_recognition',
          n: 84,
          correct: 79,
          meanings: 17,
          shown: true,
          lo: 0.868,
          hi: 0.974,
        },
        {
          family: 'form_production',
          n: 55,
          correct: 38,
          meanings: 9,
          shown: false,
          lo: null,
          hi: null,
        },
        {
          family: 'semantic_discrimination',
          n: 32,
          correct: 17,
          meanings: 11,
          shown: true,
          lo: 0.346,
          hi: 0.709,
        },
      ],
      sentence: { weak: 'semantic_discrimination', strong: 'form_recognition' },
    },
    missed_recent: { meanings: 10, flagged: 1 },
    next_steps: [
      {
        key: 'knowledge.next.review_practice',
        href: '/session?mode=practice&extra=reviews',
        params: {},
      },
      { key: 'knowledge.next.take_test', href: '/tests', params: {} },
    ],
    pro_teaser: {
      tracked_meanings: 251,
      missed_recent: 10,
      missing_next_level: null,
      next_level: null,
    },
  };
}

function respond(status, body) {
  return { ok: status < 400, status, json: async () => body };
}

let responses;
let calls;

// Dates as the page formats them (en-GB, day + short month, UTC); CLDR decides "Sep" vs "Sept".
const d = (iso) =>
  new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(
    new Date(iso + 'T00:00:00Z')
  );

const flush = async () => {
  for (let i = 0; i < 12; i++) await new Promise((r) => setTimeout(r, 0));
};

async function boot({
  summary = respond(200, full()),
  prestudy = respond(200, { status: 'success', suggestion: null }),
} = {}) {
  responses = { summary: [summary], prestudy: [prestudy] };
  window.eval(SCRIPT);
  await flush();
}

const $ = (id) => document.getElementById(id);
const visible = (id) => !$(id).classList.contains('d-none');
const text = (id) => $(id).textContent.replace(/\s+/g, ' ').trim();

beforeEach(() => {
  document.body.innerHTML = markup();
  localStorage.clear();
  localStorage.setItem('selectedLanguageId', '3');
  calls = [];
  window.LinguaI18n = { t, init: () => Promise.resolve(), currentLanguage: () => 'en' };
  window.authFetch = vi.fn(async (url) => {
    calls.push(url);
    const key = url.startsWith('/api/knowledge/summary') ? 'summary' : 'prestudy';
    const queue = responses[key];
    return queue.length > 1 ? queue.shift() : queue[0];
  });
});

afterEach(() => {
  delete window.authFetch;
  delete window.LinguaI18n;
  delete window.LinguaPaywall;
  document.body.innerHTML = '';
});

describe('knowledge page: requests', () => {
  it('asks for the summary and the prestudy suggestion for the study language', async () => {
    localStorage.setItem('selectedLanguageId', '1');
    await boot();
    expect(calls).toEqual([
      '/api/knowledge/summary?language_id=1',
      '/api/knowledge/prestudy-suggestion?language_id=1',
    ]);
  });
});

describe('knowledge page: full summary', () => {
  beforeEach(async () => {
    await boot();
  });

  it('renders the estimate card with an en dash range, the pool, label and dates', () => {
    expect(visible('knEstimate')).toBe(true);
    const card = text('knEstimate');
    expect(card).toContain(
      'In the vocabulary check you recognised about 850–1,400 of the 3,175 Japanese words it draws from.'
    );
    expect(card).toContain(
      `From 172 check answers, ${d('2026-09-13')} – ${d('2026-11-15')} · Medium`
    );
    expect(card).toContain('Rated known after a direct check: 69 words');
    expect(card).toContain('Tracked: 251 words');
    // The point estimate is a tick, never printed.
    expect(card).not.toMatch(/1,?111/);
    expect($('knEstimate').querySelector('.kn-range__tick')).not.toBeNull();
  });

  it('prefixes every claim', () => {
    const prefixes = [...document.querySelectorAll('#knEstimate .kn-prefix')].map(
      (n) => n.textContent
    );
    expect(prefixes).toEqual(['Estimated', 'Model', 'From your answers']);
  });

  it('renders the four frequency groups and the no-frequency row', () => {
    const groups = text('knGroups');
    expect(groups).toContain('Most common');
    expect(groups).toContain('73–100%');
    expect(groups).toContain('Not enough check answers at this level yet (50)');
    expect(groups).toContain('17–47%');
    expect(groups).toContain('8–35%');
    expect(groups).toContain('No frequency data');
    expect(groups).toContain('820 words in the check');
  });

  it('renders growth with its first-trend date and the idle count', () => {
    const growth = text('knGrowth');
    expect(growth).toContain('41');
    expect(growth).toContain('164');
    expect(growth).toContain(`First trend on ${d('2026-12-01')}`);
    expect(growth).toContain('Not seen for 60 days or more: 95 words');
  });

  it('renders skills with tries on words, the not-enough line and the sentence', () => {
    const skills = text('knSkills');
    expect(skills).toContain('84 tries on 17 words');
    expect(skills).toContain('Not enough producing-words practice yet (9 of 10 words)');
    expect(skills).toContain(
      'Your first-try accuracy is lower in telling-similar-words-apart exercises (53%, 32 tries on 11 words) than in recognition exercises (94%, 84 tries on 17 words).'
    );
    expect(skills).toContain('this compares your own results only');
  });

  it('renders the next steps from the summary', () => {
    const links = [...$('knNextBody').querySelectorAll('a')];
    expect(links.map((a) => a.getAttribute('href'))).toEqual([
      '/session?mode=practice&extra=reviews',
      '/tests',
    ]);
    expect(links[0].textContent).toBe('Review in Practice');
  });

  it('shows the neutral preview note in shadow mode, with no upsell', () => {
    expect(visible('knProTeaser')).toBe(true);
    const pro = text('knProTeaser');
    expect(pro).toContain('Word by word will be part of Pro when plans launch.');
    expect(pro).toContain(
      '251 words with their evidence · 10 missed recently · CSV and Anki export'
    );
    expect($('knProTeaser').querySelector('button')).toBeNull();
    expect(pro).not.toContain('Available with Pro');
  });

  it('never shows raw keys, "0 words", due/fading copy or emoji', () => {
    const page = document.body.textContent;
    expect(page).not.toMatch(/knowledge\.[a-z_]+\.[a-z_]/);
    expect(page).not.toMatch(/\b0 words\b/);
    expect(page.toLowerCase()).not.toMatch(/\bdue\b|fading|forgotten/);
    expect(page).not.toMatch(/\p{Extended_Pictographic}/u);
  });

  it('remembers the growth window', async () => {
    $('knGrowthSeg').querySelector('[data-window="90"]').click();
    expect(localStorage.getItem('kn.growthWindow')).toBe('90');
    expect(text('knGrowth')).toContain('318');
    expect($('knGrowthSeg').querySelector('[data-window="90"]').getAttribute('aria-pressed')).toBe(
      'true'
    );
  });
});

describe('knowledge page: states', () => {
  it('E0: one card with two actions, every other card hidden', async () => {
    const s = full();
    s.state = 'E0';
    await boot({ summary: respond(200, s) });
    expect(visible('knEmpty')).toBe(true);
    expect(text('knEmpty')).toContain("We don't know your Japanese vocabulary yet.");
    for (const id of ['knEstimate', 'knGroups', 'knGrowth', 'knSkills', 'knNext', 'knProTeaser']) {
      expect(visible(id)).toBe(false);
    }
    expect(document.body.textContent).not.toMatch(/\b0 words\b/);
  });

  it('E1: how many answers so far, a check button, measured group counts only', async () => {
    const s = full();
    s.state = 'E1';
    Object.assign(s.estimate, {
      shown: false,
      kind: 'none',
      lo: null,
      hi: null,
      label: null,
      reason: 'too_few_answers',
      have: 41,
      tick: null,
    });
    s.groups.forEach((g) => Object.assign(g, { shown: false, share_lo: null, share_hi: null }));
    s.rated_known_words = 0;
    await boot({ summary: respond(200, s) });
    const card = text('knEstimate');
    expect(card).toContain('10 check answers at each of 7 frequency levels: 41 of 70 so far.');
    expect(card).toContain('No words rated known after a direct check yet.');
    expect($('knEstimateBody').querySelector('a[href="/calibration"]')).not.toBeNull();
    expect(text('knGroups')).not.toContain('Not enough check answers');
    expect(text('knGroups')).not.toMatch(/\d+–\d+%/);
  });

  it('E1b: too uncertain names the answers needed per level', async () => {
    const s = full();
    Object.assign(s.estimate, {
      shown: false,
      kind: 'none',
      reason: 'too_uncertain',
      answers_needed: 32,
      have: null,
    });
    s.state = 'E1b';
    await boot({ summary: respond(200, s) });
    expect(text('knEstimate')).toContain(
      "don't pin the number down yet. About 32 more answers at each level would."
    );
  });

  it('E1c: out of date shows the last answer date', async () => {
    const s = full();
    Object.assign(s.estimate, {
      shown: false,
      kind: 'none',
      reason: 'out_of_date',
      last_answer_at: '2026-03-02',
    });
    s.state = 'E1c';
    await boot({ summary: respond(200, s) });
    expect(text('knEstimate')).toContain(`more than 6 months old (last on ${d('2026-03-02')})`);
  });

  it('upper-only renders "Fewer than {hi}" and no lower bound', async () => {
    const s = full();
    Object.assign(s.estimate, {
      kind: 'upper_only',
      lo: null,
      hi: 510,
      label: 'low',
      universe_words: 3623,
      tick: 240,
    });
    s.language = { id: 1, code: 'zh', name: 'Chinese' };
    localStorage.setItem('selectedLanguageId', '1');
    await boot({ summary: respond(200, s) });
    const card = text('knEstimate');
    expect(card).toContain('Fewer than 510 of the 3,623 Chinese words the check draws from.');
    expect(card).toContain('· Rough');
    expect(card).not.toContain('0–510');
  });

  it('E2, E3 and E10 notes', async () => {
    const s = full();
    s.few_tracked = true;
    s.tracked_words = 12;
    s.stale_days = 47;
    s.estimate.disagreement = true;
    await boot({ summary: respond(200, s) });
    const card = text('knEstimate');
    expect(card).toContain('Most of what we know comes from 12 words.');
    expect(card).toContain('Last practice 47 days ago.');
    expect(card).toContain('Your practice has rated more words known than this check suggests.');
  });

  it('E4c: lists unavailable shows only that line in the list card', async () => {
    const s = full();
    s.lists_unavailable = true;
    await boot({ summary: respond(200, s) });
    expect(visible('knLists')).toBe(true);
    expect(text('knListsBody')).toBe('Word lists are unavailable right now');
    expect(visible('knEstimate')).toBe(true);
  });

  it('E4: no list file hides the list card', async () => {
    await boot();
    expect(visible('knLists')).toBe(false);
  });

  it.each([404, 503])('%i → "This page isn\'t available yet."', async (status) => {
    await boot({ summary: respond(status, { status: 'error' }) });
    expect(visible('knUnavailable')).toBe(true);
    expect(visible('knError')).toBe(false);
    expect(visible('knEstimate')).toBe(false);
    expect(visible('knLoading')).toBe(false);
  });

  it('a server error offers a retry that reloads', async () => {
    responses = null;
    window.authFetch = vi.fn(async (url) => {
      calls.push(url);
      if (!url.startsWith('/api/knowledge/summary'))
        return respond(200, { status: 'success', suggestion: null });
      return calls.filter((u) => u.startsWith('/api/knowledge/summary')).length === 1
        ? respond(500, { status: 'error' })
        : respond(200, full());
    });
    window.eval(SCRIPT);
    await flush();
    expect(visible('knError')).toBe(true);
    $('knRetry').click();
    await flush();
    expect(visible('knError')).toBe(false);
    expect(visible('knEstimate')).toBe(true);
  });

  it('a network failure is the error state', async () => {
    window.authFetch = vi.fn(async () => {
      throw new TypeError('network down');
    });
    window.eval(SCRIPT);
    await flush();
    expect(visible('knError')).toBe(true);
  });
});

describe('knowledge page: Pro card', () => {
  function enforced() {
    const s = full();
    s.detail = { level: 0, enforced: true, preview: false };
    return s;
  }

  it('enforced level 0 shows the Pro card with own counts and "Available with Pro"', async () => {
    await boot({ summary: respond(200, enforced()) });
    const pro = text('knProTeaser');
    expect(pro).toContain('Word by word — Pro');
    expect(pro).toContain(
      '251 words with their evidence · 10 missed recently · CSV and Anki export'
    );
    expect(pro).toContain('Available with Pro');
    expect($('knProTeaser').querySelector('button')).toBeNull();
    expect(pro).not.toContain('part of Pro when plans launch');
  });

  it('a button opens LinguaPaywall only when it exists', async () => {
    window.LinguaPaywall = { open: vi.fn() };
    await boot({ summary: respond(200, enforced()) });
    const btn = $('knProTeaser').querySelector('button');
    expect(btn.textContent).toBe('See what Pro includes');
    btn.click();
    expect(window.LinguaPaywall.open).toHaveBeenCalledWith({ reason: 'bkt_report_detail' });
  });

  it('omits zero clauses', async () => {
    const s = enforced();
    s.pro_teaser = {
      tracked_meanings: 4,
      missed_recent: null,
      missing_next_level: null,
      next_level: null,
    };
    await boot({ summary: respond(200, s) });
    expect(text('knProBody')).toContain('4 words with their evidence · CSV and Anki export');
    expect(text('knProBody')).not.toContain('missed recently');
  });

  it('Pro (level 1) gets no teaser card', async () => {
    const s = full();
    s.detail = { level: 1, enforced: false, preview: false };
    await boot({ summary: respond(200, s) });
    expect(visible('knProTeaser')).toBe(false);
  });
});

describe('knowledge page: prestudy next step (rule 2)', () => {
  const suggestion = {
    test_id: 't1',
    slug: 'a-day-out',
    title: 'A <b>day</b> out',
    test_type: 'reading',
    unknown: 13,
    n: 50,
    unknown_share: 0.26,
  };

  it('is inserted at rule position 2, after the check, keeping at most three steps', async () => {
    const s = full();
    s.next_steps = [
      { key: 'knowledge.next.check', href: '/calibration', params: { n: 29 } },
      {
        key: 'knowledge.next.review_practice',
        href: '/session?mode=practice&extra=reviews',
        params: {},
      },
      { key: 'knowledge.next.take_test', href: '/tests', params: {} },
    ];
    await boot({
      summary: respond(200, s),
      prestudy: respond(200, { status: 'success', suggestion }),
    });
    const links = [...$('knNextBody').querySelectorAll('a')];
    expect(links.map((a) => a.dataset.step)).toEqual([
      'knowledge.next.check',
      'knowledge.next.prestudy',
      'knowledge.next.review_practice',
    ]);
    expect(links[0].textContent).toBe('Take the vocabulary check (about 29 answers)');
    expect(links[1].getAttribute('href')).toBe('/test/a-day-out/prestudy');
    // Database text is text, never markup.
    expect(links[1].textContent).toBe(
      'Prepare for A <b>day</b> out: 13 of its 50 key words are new to you'
    );
    expect(links[1].querySelector('b')).toBeNull();
  });

  it('comes first when no estimate step applies', async () => {
    await boot({ prestudy: respond(200, { status: 'success', suggestion }) });
    const steps = [...$('knNextBody').querySelectorAll('a')].map((a) => a.dataset.step);
    expect(steps).toEqual([
      'knowledge.next.prestudy',
      'knowledge.next.review_practice',
      'knowledge.next.take_test',
    ]);
  });

  it('a stale learner keeps "Do today\'s session" first', async () => {
    const s = full();
    s.stale_days = 40;
    s.next_steps = [
      { key: 'knowledge.next.session', href: '/session', params: {} },
      {
        key: 'knowledge.next.review_practice',
        href: '/session?mode=practice&extra=reviews',
        params: {},
      },
      { key: 'knowledge.next.take_test', href: '/tests', params: {} },
    ];
    await boot({
      summary: respond(200, s),
      prestudy: respond(200, { status: 'success', suggestion }),
    });
    const steps = [...$('knNextBody').querySelectorAll('a')].map((a) => a.dataset.step);
    expect(steps).toEqual([
      'knowledge.next.session',
      'knowledge.next.prestudy',
      'knowledge.next.review_practice',
    ]);
  });

  it('a null or failed suggestion changes nothing', async () => {
    await boot({ prestudy: respond(500, { status: 'error' }) });
    const steps = [...$('knNextBody').querySelectorAll('a')].map((a) => a.dataset.step);
    expect(steps).toEqual(['knowledge.next.review_practice', 'knowledge.next.take_test']);
  });
});

describe('knowledge page: growth with history', () => {
  it('shows the rated-known change beside its check count, and the estimate comparison', async () => {
    const s = full();
    Object.assign(s.growth.d30, {
      rated_known_delta: 19,
      anchor_date: '2026-10-18',
      first_trend_on: null,
      estimate_change: {
        verdict: 'no_clear_change',
        then: {
          lo: 850,
          hi: 1400,
          kind: 'range',
          first_answer_at: '2026-09-13',
          last_answer_at: '2026-10-17',
        },
        now: {
          lo: 900,
          hi: 1500,
          kind: 'range',
          first_answer_at: '2026-11-01',
          last_answer_at: '2026-11-15',
        },
      },
      pool_changed: { from: 3000, to: 3175 },
    });
    await boot({ summary: respond(200, s) });
    const growth = text('knGrowth');
    expect(growth).toContain(`Rated known after a direct check: +19 since ${d('2026-10-18')}`);
    expect(growth).toContain('Direct checks in this period: 164');
    expect(growth).toContain(`No clear change since ${d('2026-10-18')}`);
    expect(growth).toContain(
      `Then: 850–1,400, from answers ${d('2026-09-13')} – ${d('2026-10-17')}`
    );
    expect(growth).toContain(
      `Now: 900–1,500, from answers ${d('2026-11-01')} – ${d('2026-11-15')}`
    );
    expect(growth).toContain(
      `The check's word pool changed from 3,000 to 3,175 words since ${d('2026-10-18')}.`
    );
    expect(growth).not.toContain('learned');
  });

  it('with no direct checks it says the change comes from reading tests', async () => {
    const s = full();
    Object.assign(s.growth.d30, {
      rated_known_delta: -2,
      anchor_date: '2026-10-18',
      first_trend_on: null,
      direct_checks: 0,
    });
    await boot({ summary: respond(200, s) });
    expect(text('knGrowth')).toContain(
      'No direct checks in this period. Any change comes from your reading tests.'
    );
  });
});
