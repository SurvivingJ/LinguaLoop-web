/**
 * WP-INT contract test for DT guided self-repair: the frontend against REAL backend responses.
 *
 * tests/unit/fixtures/dt-repair/real/*.json are written by tests/test_dt_repair_contract.py,
 * which drives the real Flask routes (submit hook + dt_repair blueprint + service code) over an
 * in-memory DB and a scripted model. Each file is {http, body}. This file checks:
 *   1. shapes  - the stand-in API the frontend was built against (tests/e2e/dt-repair/mock-api.js)
 *                answers every endpoint with exactly the keys the real backend sends;
 *   2. reads   - every field the sheet / hosts / daily player read is present in the real bodies;
 *   3. replay  - the real sheet walks the pass, an unsure + direct pass and a daily set while a
 *                strict replay server answers with the real bodies in the order the sheet calls;
 *   4. leaks   - before a sentence's reveal nothing the browser holds (DOM, attributes, storage,
 *                the sheet's own state) contains that sentence's reference text or explanation.
 * When the Python test fails because the backend changed, regenerate the files and run this.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const load = (rel) => (0, eval)(readFileSync(join(root, rel), 'utf8'));
load('static/js/active-timer.js');
load('static/js/dt-repair-sheet.js');
load('tests/e2e/dt-repair/mock-api.js');

const REAL_DIR =
  process.env.DT_REPAIR_REAL_DIR || join(root, 'tests/unit/fixtures/dt-repair/real');
const real = (name) => JSON.parse(readFileSync(join(REAL_DIR, `${name}.json`), 'utf8'));
const BASE = '/api/dual-translation/repair';

const flush = async (n = 14) => {
  for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0));
};
const $ = (sel) => document.querySelector(sel);
const view = () => $('#dtr-sheet') && $('#dtr-sheet').dataset.view;
const click = async (sel) => {
  $(sel).click();
  await flush();
};
const type = (text) => {
  const ta = $('#dtr-ta');
  ta.value = text;
  ta.dispatchEvent(new Event('input', { bubbles: true }));
};

// ---------------------------------------------------------------------------- shape helpers
const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

// Key differences between a mock body and a real body, recursively (arrays: first elements).
function keyDiff(mock, rl, path = '') {
  const out = [];
  if (isObj(mock) && isObj(rl)) {
    new Set([...Object.keys(mock), ...Object.keys(rl)]).forEach((k) => {
      const p = path ? `${path}.${k}` : k;
      if (!(k in mock)) out.push(`${p}: sent by the backend, missing in the mock`);
      else if (!(k in rl)) out.push(`${p}: in the mock, not sent by the backend`);
      else out.push(...keyDiff(mock[k], rl[k], p));
    });
  } else if (Array.isArray(mock) && Array.isArray(rl) && mock.length && rl.length) {
    out.push(...keyDiff(mock[0], rl[0], `${path}[0]`));
  }
  return out;
}

async function call(mock, method, path, body) {
  const res = await mock.fetch(BASE + path, {
    method,
    body: body ? JSON.stringify(body) : undefined,
  });
  return { http: res.status, body: await res.json() };
}

const P = { surface: 'repair_pass' };
const D = { surface: 'daily_practice' };

// The same endpoints and outcomes, asked of the stand-in API.
async function mockBodies() {
  const m = {};
  let mk = DTRepairMock.create('en_errors');
  m.submit_open = { http: 200, body: mk.submitResponse() };
  m.session_open = await call(mk, 'GET', '/submissions/9001/session');
  m.open_pass = await call(mk, 'POST', '/items/7001/open', P);
  m.hint_where = await call(mk, 'POST', '/items/7001/hint', { ...P, expected_level: 1 });
  m.hint_kind = await call(mk, 'POST', '/items/7001/hint', { ...P, expected_level: 2 });
  m.hint_clue = await call(mk, 'POST', '/items/7001/hint', { ...P, expected_level: 3 });
  m.check_unchanged = await call(mk, 'POST', '/items/7001/check', {
    ...P,
    text: "It's a sick way to learn by doing.",
    client_check_id: 'a',
  });
  m.check_still = await call(mk, 'POST', '/items/7001/check', {
    ...P,
    text: "It's a sick, cool way to learn by doing.",
    client_check_id: 'b',
  });
  m.check_fixed = await call(mk, 'POST', '/items/7001/check', {
    ...P,
    text: "It's a great way to learn by doing.",
    client_check_id: 'c',
  });
  m.open_second = await call(mk, 'POST', '/items/7002/open', P);
  m.hint_where_second = await call(mk, 'POST', '/items/7002/hint', { ...P, expected_level: 1 });
  m.result_in_progress = await call(mk, 'GET', '/submissions/9001/result');
  m.reveal = await call(mk, 'POST', '/items/7002/reveal', { ...P, reason: 'asked' });
  m.finish = await call(mk, 'POST', '/sessions/501/finish', { closed_early: false });
  m.result = await call(mk, 'GET', '/submissions/9001/result');

  mk = DTRepairMock.create('en_errors');
  mk.fail('check', 'error');
  m.check_error = await call(mk, 'POST', '/items/7001/check', {
    ...P,
    text: 'x y',
    client_check_id: 'd',
  });
  mk.fail('check', 'inprogress');
  m.error_409_check_in_progress = await call(mk, 'POST', '/items/7001/check', {
    ...P,
    text: 'x y',
    client_check_id: 'e',
  });
  m.check_alt = await call(mk, 'POST', '/items/7001/check', {
    ...P,
    text: "It's a fine way to learn by doing.",
    client_check_id: 'f',
  });
  m.dispute = await call(mk, 'POST', '/items/7002/dispute', P);

  mk = DTRepairMock.create('en_errors');
  for (let n = 0; n < 4; n++) {
    m.check_auto_reveal = await call(mk, 'POST', '/items/7001/check', {
      ...P,
      text: `It's a sick c${n}l way to learn by doing.`,
      client_check_id: `g${n}`,
    });
  }

  mk = DTRepairMock.create('en_mixed');
  m.submit_open_mixed = { http: 200, body: mk.submitResponse() };
  m.reveal_direct = await call(mk, 'POST', '/items/7002/reveal', { ...P, reason: 'direct' });
  m.open_unsure = await call(mk, 'POST', '/items/7004/open', P);
  m.dispute_unsure = await call(mk, 'POST', '/items/7004/dispute', P);

  m.submit_clean = { http: 200, body: DTRepairMock.create('en_clean').submitResponse() };

  mk = DTRepairMock.create('daily_en');
  m.practice_due = await call(mk, 'GET', '/practice/due?language_id=2');
  m.daily_open = await call(mk, 'POST', '/items/8101/open', D);
  m.daily_hint_kind = await call(mk, 'POST', '/items/8101/hint', { ...D, expected_level: 2 });
  m.daily_check_still = await call(mk, 'POST', '/items/8101/check', {
    ...D,
    text: 'You can learn on robots and electronics.',
    client_check_id: 'h',
  });
  m.daily_check_fixed = await call(mk, 'POST', '/items/8101/check', {
    ...D,
    text: 'You can learn about robotics and electronics.',
    client_check_id: 'i',
  });
  m.daily_reveal = await call(mk, 'POST', '/items/8102/reveal', { ...D, reason: 'asked' });
  m.daily_skip = await call(mk, 'POST', '/items/8102/skip', D);
  return m;
}

// ---------------------------------------------------------------------------- replay server
function replay(script) {
  const problems = [];
  const calls = [];
  const fetch = async (url, o) => {
    const method = (o && o.method) || 'GET';
    const body = o && o.body ? JSON.parse(o.body) : null;
    const line = `${method} ${String(url).replace(BASE, '')}`;
    calls.push({ line, body });
    const next = script.shift();
    if (!next) {
      problems.push(`unexpected call ${line}`);
      return { ok: false, status: 599, json: async () => ({}) };
    }
    const [pattern, name, checkBody] = next;
    if (!pattern.test(line)) problems.push(`expected ${pattern}, got ${line}`);
    if (checkBody) {
      const why = checkBody(body);
      if (why) problems.push(`${line}: ${why}`);
    }
    const fx = real(name);
    return { ok: fx.http < 400, status: fx.http, json: async () => fx.body };
  };
  return { fetch, problems, calls, script };
}

// Everything the browser holds right now, as one string.
function browserState(handle) {
  let storage = '';
  for (const st of [window.localStorage, window.sessionStorage]) {
    for (let i = 0; i < st.length; i++) storage += st.key(i) + '=' + st.getItem(st.key(i)) + '\n';
  }
  let sheetState = '';
  try {
    sheetState = JSON.stringify(handle && handle._state, (k, v) =>
      typeof v === 'function' || (v && v.nodeType) ? undefined : v
    );
  } catch {
    sheetState = '';
  }
  return document.documentElement.outerHTML + '\n' + storage + '\n' + sheetState;
}

const S1_SECRETS = () => {
  const a = real('check_alt').body.answer;
  return [a.answer_sentence, a.explanation, 'great'];
};
const S2_SECRETS = () => {
  const a = real('reveal').body.answer;
  return [a.answer_sentence, a.explanation, 'with it.'];
};

let handle;
beforeEach(() => {
  document.body.innerHTML = '<button id="host">Submit</button>';
  window.LinguaI18n = undefined;
  window.localStorage.clear();
  window.sessionStorage.clear();
});
afterEach(() => {
  if (handle) handle.dispose();
  handle = null;
  document.body.innerHTML = '';
});

// ---------------------------------------------------------------------------- 1. shapes
describe('real backend responses vs the stand-in API', () => {
  it('the fixture set is complete', () => {
    const names = readdirSync(REAL_DIR).map((f) => f.replace(/\.json$/, ''));
    for (const n of ['submit_open', 'practice_due', 'check_still', 'reveal', 'finish', 'result']) {
      expect(names).toContain(n);
    }
  });

  it('every endpoint answers with the same keys (recursively)', async () => {
    const mock = await mockBodies();
    const diffs = [];
    for (const [name, m] of Object.entries(mock)) {
      const r = real(name);
      if (m.http !== r.http) diffs.push(`${name}: http ${m.http} (mock) vs ${r.http} (real)`);
      // /result is today's grade contract, rendered by the existing result view: top level only
      const mb = name === 'result' ? Object.fromEntries(Object.keys(m.body).map((k) => [k, 0])) : m.body;
      const rb = name === 'result' ? Object.fromEntries(Object.keys(r.body).map((k) => [k, 0])) : r.body;
      keyDiff(mb, rb).forEach((d) => diffs.push(`${name}: ${d}`));
    }
    expect(diffs).toEqual([]);
  });

  it('every response is an api_success / api_error envelope', () => {
    for (const f of readdirSync(REAL_DIR)) {
      const fx = JSON.parse(readFileSync(join(REAL_DIR, f), 'utf8'));
      if (fx.http === 401) continue; // the auth middleware's own body
      expect(fx.body.status, f).toBe(fx.http < 400 ? 'success' : 'error');
      if (fx.http >= 400) expect(typeof fx.body.error_code, f).toBe('string');
    }
  });
});

// ---------------------------------------------------------------------------- 2. reads
describe('every field the frontend reads is in the real responses', () => {
  const STEP = ['item_id', 'step_kind', 'hint_rungs', 'hint_level', 'where', 'last_text',
    'learner_sentence', 'prompt_l1', 'prompt_l1_passage', 'state', 'outcome', 'from_date',
    'l1', 'l2'];
  const ANSWER = ['heading', 'learner_sentence', 'learner_marks', 'answer_sentence',
    'answer_marks', 'explanation', 'explanation_lang', 'l2'];
  const has = (obj, keys, where) => keys.forEach((k) => expect(obj, `${where}.${k}`).toHaveProperty(k));

  it('session payload and steps', () => {
    for (const name of ['submit_open', 'submit_open_mixed', 'submit_clean', 'submit_bypassed']) {
      const rep = real(name).body.repair;
      has(rep, ['session_id', 'submission_id', 'status', 'clean', 'l1', 'l2', 'n_clean',
        'prompt_l1_passage', 'auto_advance_ms', 'steps', 'summary'], name);
      rep.steps.forEach((s) => has(s, STEP, `${name}.step`));
    }
    has(real('session_open').body.session, ['status', 'steps', 'submission_id'], 'session');
    expect(real('submit_open').body.redacted).toBe(true);
    expect(real('submit_clean').body.redacted).toBeUndefined();
  });

  it('open, hint, check, reveal, dispute, skip, finish, due', () => {
    for (const n of ['open_pass', 'daily_open', 'open_unsure']) has(real(n).body.step, STEP, n);
    for (const n of ['hint_where', 'hint_kind', 'hint_clue', 'daily_hint_kind']) {
      has(real(n).body, ['hint', 'hint_level', 'hint_number', 'hint_total', 'where', 'next'], n);
      has(real(n).body.hint, ['type', 'text', 'lang'], n);
    }
    for (const n of ['check_still', 'check_fixed', 'check_alt', 'check_auto_reveal',
      'check_error', 'check_unchanged', 'check_budget_exhausted', 'daily_check_fixed']) {
      has(real(n).body, ['result', 'closed', 'answer', 'outcome', 'where', 'checks_used',
        'hints_used', 'back_later'], n);
    }
    for (const n of ['check_alt', 'check_auto_reveal', 'check_budget_exhausted', 'reveal',
      'reveal_direct', 'dispute', 'daily_reveal']) has(real(n).body.answer, ANSWER, n);
    for (const n of ['reveal', 'dispute', 'dispute_unsure', 'daily_reveal', 'daily_skip']) {
      has(real(n).body, ['closed', 'outcome', 'answer', 'back_later'], n);
    }
    has(real('finish').body.summary, ['fixed_yourself', 'needed_help', 'saved_to_practice'], 'finish');
    has(real('practice_due').body, ['items', 'total_due'], 'due');
  });

  it('daily items say their own languages and have a prompt', () => {
    real('practice_due').body.items.forEach((s) => {
      expect(s.l1).toBe('zh');
      expect(s.l2).toBe('en');
      expect(s.prompt_l1 || s.prompt_l1_passage).toBeTruthy();
    });
  });
});

// ---------------------------------------------------------------------------- 3 + 4. replay
describe('the real sheet against the real responses', () => {
  it('repair pass: hints, still, fixed, reveal, finish, summary — and no answer before its reveal', async () => {
    const rep = real('submit_open').body.repair;
    const ccid = (b) =>
      /^[0-9a-f-]{36}$/.test(b.client_check_id) && b.surface === 'repair_pass' ? '' : 'bad check body';
    const srv = replay([
      [/^POST \/items\/7002\/open$/, 'open_pass'],
      [/^POST \/items\/7002\/hint$/, 'hint_where', (b) => (b.expected_level === 1 ? '' : 'level')],
      [/^POST \/items\/7002\/hint$/, 'hint_kind', (b) => (b.expected_level === 2 ? '' : 'level')],
      [/^POST \/items\/7002\/hint$/, 'hint_clue', (b) => (b.expected_level === 3 ? '' : 'level')],
      [/^POST \/items\/7002\/check$/, 'check_still', ccid],
      [/^POST \/items\/7002\/check$/, 'check_fixed', ccid],
      [/^POST \/items\/7003\/open$/, 'open_second'],
      [/^POST \/items\/7003\/hint$/, 'hint_where_second'],
      [/^POST \/items\/7003\/reveal$/, 'reveal', (b) => (b.reason === 'asked' ? '' : 'reason')],
      [/^POST \/sessions\/501\/finish$/, 'finish', (b) => (b.closed_early === false ? '' : 'early')],
    ]);
    const onDone = vi.fn();
    handle = DTRepairSheet.open({
      mode: 'pass',
      session: rep,
      fetch: srv.fetch,
      returnFocus: $('#host'),
      onDone,
      animate: false,
      autoAdvance: false,
    });
    expect(view()).toBe('result');
    expect($('.dtr-big').textContent).toBe('2');
    await click('#dtr-go');
    expect(view()).toBe('fix');
    expect($('#dtr-ta').value).toBe(rep.steps[0].learner_sentence);
    expect($('#dtr-prompt').getAttribute('lang')).toBe('zh');
    expect($('#dtr-field').getAttribute('lang')).toBe('en');
    await click('#dtr-hint');
    expect($('#dtr-mirror mark').textContent).toBe('sick');
    await click('#dtr-hint');
    expect($('#dtr-slot span[lang="zh"]').textContent).toBe(real('hint_kind').body.hint.text);
    await click('#dtr-hint');
    expect($('#dtr-slot').textContent).toContain(real('hint_clue').body.hint.text);
    expect($('#dtr-hint').textContent).toBe('Show answer');
    for (const s of S1_SECRETS()) expect(browserState(handle)).not.toContain(s);
    for (const s of S2_SECRETS()) expect(browserState(handle)).not.toContain(s);
    type("It's a cool way to learn by doing.");
    await click('#dtr-check');
    expect(view()).toBe('fix');
    expect($('#dtr-sheet').textContent).toContain('Still not quite');
    expect($('#dtr-mirror mark').textContent).toBe('cool');
    type("It's a great way to learn by doing!");
    await click('#dtr-check');
    expect(view()).toBe('ok');
    expect($('.dtr-moment p').textContent).toBe('With 3 hints');
    await click('#dtr-next');
    expect(view()).toBe('fix');
    await click('#dtr-hint');
    expect($('#dtr-mirror mark').textContent).toBe('without it');
    expect($('#dtr-hint').textContent).toBe('Show answer');
    for (const s of S2_SECRETS()) expect(browserState(handle)).not.toContain(s);
    await click('#dtr-hint');
    expect(view()).toBe('reveal');
    expect($('#dtr-cmp-mine del').textContent).toBe('without it');
    expect($('#dtr-cmp-ans b').textContent).toBe('with it');
    expect($('.dtr-why').textContent).toBe(real('reveal').body.answer.explanation);
    expect($('#dtr-next').textContent).toBe('Finish');
    await click('#dtr-next');
    expect(view()).toBe('summary');
    expect($('.dtr-tally').textContent.replace(/\s+/g, ' ')).toContain('Fixed yourself 1');
    await click('#dtr-done');
    expect(onDone).toHaveBeenCalledWith(
      expect.objectContaining({ closedEarly: false, summary: real('finish').body.summary })
    );
    expect(srv.problems).toEqual([]);
    expect(srv.script).toEqual([]);
  });

  it('unsure + direct pass: "Mine is fine" keeps it, the direct step is revealed on display', async () => {
    const rep = real('submit_open_mixed').body.repair;
    const srv = replay([
      [/^POST \/items\/7002\/open$/, 'open_unsure'],
      [/^POST \/items\/7002\/dispute$/, 'dispute_unsure'],
      [/^POST \/items\/7003\/reveal$/, 'reveal_direct', (b) => (b.reason === 'direct' ? '' : 'reason')],
      [/^POST \/sessions\/501\/finish$/, 'finish'],
    ]);
    handle = DTRepairSheet.open({
      mode: 'pass',
      session: rep,
      fetch: srv.fetch,
      onDone: vi.fn(),
      animate: false,
      autoAdvance: false,
    });
    expect($('#dtr-h').textContent).toContain('sentences to look at');
    await click('#dtr-go');
    expect($('#dtr-mirror mark.dtr-maybe').textContent).toBe('sick');
    await click('#dtr-fine');
    expect(view()).toBe('kept');
    await click('#dtr-next');
    expect(view()).toBe('reveal');
    expect($('#dtr-cmp-ans b').textContent).toBe('with it');
    await click('#dtr-next');
    expect(view()).toBe('summary');
    expect(srv.problems).toEqual([]);
    expect(srv.script).toEqual([]);
  });

  it('daily practice: languages and prompt from the items, fixed, hints, reveal, summary from the server', async () => {
    const items = real('practice_due').body.items;
    const timed = (b) =>
      b.surface === 'daily_practice' && b.active_ms >= 0 && /^[0-9a-f-]{36}$/.test(b.client_event_id)
        ? ''
        : 'closing call without active_ms / client_event_id';
    const srv = replay([
      [/^POST \/items\/7003\/open$/, 'daily_open'],
      [/^POST \/items\/7003\/check$/, 'daily_check_still'],
      [/^POST \/items\/7003\/check$/, 'daily_check_fixed', timed],
      [/^POST \/items\/7002\/open$/, 'daily_open_second'],
      [/^POST \/items\/7002\/hint$/, 'daily_hint_kind', (b) => (b.expected_level === 2 ? '' : 'level')],
      [/^POST \/items\/7002\/hint$/, 'daily_hint_clue'],
      [/^POST \/items\/7002\/reveal$/, 'daily_reveal', timed],
    ]);
    const onDone = vi.fn();
    handle = DTRepairSheet.open({
      mode: 'daily',
      items,
      fetch: srv.fetch,
      onDone,
      animate: false,
      autoAdvance: false,
    });
    await flush();
    expect(view()).toBe('fix');
    expect($('.dtr-eyebrow')).not.toBeNull();
    expect($('#dtr-field').getAttribute('lang')).toBe('en');
    expect($('#dtr-prompt').getAttribute('lang')).toBe('zh');
    expect($('#dtr-mirror mark').textContent).toBe('without it');
    type('You can make lots of things without it.');
    await click('#dtr-check');
    expect($('#dtr-sheet').textContent).toContain('Still not quite');
    type('You can make many things with it.');
    await click('#dtr-check');
    expect(view()).toBe('ok');
    expect($('.dtr-moment p').textContent).toBe('Without any more help');
    await click('#dtr-next');
    await click('#dtr-hint');
    await click('#dtr-hint');
    expect($('#dtr-hint').textContent).toBe('Show answer');
    await click('#dtr-hint');
    expect(view()).toBe('reveal');
    await click('#dtr-next');
    expect(view()).toBe('summary');
    const tally = $('.dtr-tally').textContent.replace(/\s+/g, ' ');
    expect(tally).toContain('Fixed yourself 1');
    expect(tally).toContain('Needed help 1');
    expect(tally).toContain(`Back in practice later ${real('daily_reveal').body.back_later ? 1 : 0}`);
    await click('#dtr-done');
    expect(onDone).toHaveBeenCalledWith({ completed: 2, closedEarly: false });
    expect(srv.problems).toEqual([]);
    expect(srv.script).toEqual([]);
  });
});
