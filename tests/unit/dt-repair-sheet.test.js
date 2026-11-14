/**
 * Unit tests for static/js/dt-repair-sheet.js (the DT guided self-repair pop-up,
 * wiki/features/dt-guided-self-repair.tech.md §8.5 and §8.11), against the stand-in API in
 * tests/e2e/dt-repair/mock-api.js and the normative fixtures of §4.12.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const load = (rel) => (0, eval)(readFileSync(join(root, rel), 'utf8'));
load('static/js/active-timer.js');
load('static/js/dt-repair-sheet.js');
load('tests/e2e/dt-repair/mock-api.js');

const fixture = (name) =>
  JSON.parse(readFileSync(join(root, 'tests/unit/fixtures/dt-repair', name + '.json'), 'utf8'));
const flush = async (n = 12) => {
  for (let i = 0; i < n; i++) await new Promise((r) => setTimeout(r, 0));
};

let mock;
let onDone;
let handle;
let returnFocus;
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
const checks = () => mock.callsTo(/\/check$/);

function openPass(name, opts = {}) {
  mock = DTRepairMock.create(name);
  onDone = vi.fn();
  handle = DTRepairSheet.open({
    mode: 'pass',
    session: mock.session,
    fetch: mock.fetch,
    returnFocus,
    onDone,
    animate: false,
    autoAdvance: false,
    ...opts,
  });
  return mock;
}

function openDaily(name = 'daily_en') {
  mock = DTRepairMock.create(name);
  onDone = vi.fn();
  handle = DTRepairSheet.open({
    mode: 'daily',
    items: mock.items,
    l2: mock.l2,
    fetch: mock.fetch,
    returnFocus,
    onDone,
    animate: false,
    autoAdvance: false,
  });
  return mock;
}

beforeEach(() => {
  document.body.innerHTML = '<button id="host">Submit</button>';
  returnFocus = $('#host');
  window.LinguaI18n = undefined;
});

afterEach(() => {
  if (handle) handle.dispose();
  handle = null;
  document.body.innerHTML = '';
  vi.useRealTimers();
});

describe('shell', () => {
  it('is a labelled modal dialog over an inert host with the page scroll locked', () => {
    openPass('en_errors');
    const sheet = $('#dtr-sheet');
    expect(sheet.getAttribute('role')).toBe('dialog');
    expect(sheet.getAttribute('aria-modal')).toBe('true');
    expect($('#host').inert).toBe(true);
    expect(document.body.style.overflow).toBe('hidden');
    expect($('#dtr-live').getAttribute('aria-live')).toBe('polite');
    handle.dispose();
    expect($('#host').inert).toBe(false);
    expect(document.body.style.overflow).toBe('');
  });

  it('opening a second sheet closes the first', () => {
    openPass('en_errors');
    openPass('zh_errors');
    expect(document.querySelectorAll('.dtr-sheet').length).toBe(1);
  });
});

describe('result and clean views', () => {
  it('shows the count, the label and how many look fine', () => {
    openPass('en_errors');
    expect(view()).toBe('result');
    expect($('.dtr-big').textContent).toBe('2');
    expect($('#dtr-h').textContent).toContain('sentences to fix');
    expect($('.dtr-moment p').textContent).toBe('The other 2 look fine.');
  });

  it('says "to look at" when every step is unsure, and hides the line when nothing is clean', () => {
    openPass('en_unsure');
    expect($('#dtr-h').textContent).toContain('sentence to look at');
    handle.dispose();
    mock = DTRepairMock.create('en_errors');
    mock.session.n_clean = 0;
    handle = DTRepairSheet.open({
      mode: 'pass',
      session: mock.session,
      fetch: mock.fetch,
      onDone: vi.fn(),
      animate: false,
    });
    expect($('.dtr-moment p')).toBeNull();
  });

  it('clean session: tick view, Done closes without a finish call', async () => {
    openPass('en_clean');
    expect(view()).toBe('clean');
    expect($('#dtr-h').textContent).toBe('No issues found');
    await click('#dtr-done');
    expect(onDone).toHaveBeenCalledWith(
      expect.objectContaining({ clean: true, closedEarly: false })
    );
    expect(mock.callsTo(/finish/).length).toBe(0);
    expect($('#dtr-sheet')).toBeNull();
  });

  it('Start opens the first step and posts /open with the surface', async () => {
    openPass('en_errors');
    await click('#dtr-go');
    expect(view()).toBe('fix');
    const open = mock.callsTo(/\/items\/7001\/open/);
    expect(open.length).toBe(1);
    expect(open[0].body.surface).toBe('repair_pass');
  });
});

describe('fix view', () => {
  beforeEach(async () => {
    openPass('en_errors');
    await click('#dtr-go');
  });

  it('has a real label, a pre-filled editable field and an obvious Check button', () => {
    const lab = $('label[for="dtr-ta"]');
    expect(lab.textContent.trim()).toBe('Fix your sentence');
    expect($('#dtr-ta').value).toBe("It's a sick way to learn by doing.");
    expect($('#dtr-ta').readOnly).toBe(false);
    expect($('#dtr-check').textContent).toBe('Check');
    expect($('#dtr-ta').getAttribute('placeholder')).toBeNull();
  });

  it('unchanged text: slot message, no request', async () => {
    await click('#dtr-check');
    expect($('#dtr-slot').textContent).toContain('same sentence');
    expect(checks().length).toBe(0);
  });

  it('typing clears the slot message', async () => {
    await click('#dtr-check');
    type("It's a sick way to learn by doing!");
    expect($('#dtr-slot').textContent).toBe('');
  });

  it('a double press sends one request and ignores the second', async () => {
    type("It's a great way to learn by doing.");
    $('#dtr-check').click();
    $('#dtr-check').click();
    await flush();
    expect(checks().length).toBe(1);
  });

  it('shows a spinner and read-only field while checking', async () => {
    type("It's a great way to learn by doing.");
    $('#dtr-check').click();
    expect($('#dtr-check').getAttribute('aria-busy')).toBe('true');
    expect($('#dtr-check').textContent).toContain('Checking');
    expect($('#dtr-ta').readOnly).toBe(true);
    await flush();
  });

  it('check body follows §4.6 and the idempotency key is reused after a network failure', async () => {
    mock.fail('check', 'network');
    type("It's a great  way to learn by doing.\n");
    await click('#dtr-check');
    expect($('#dtr-slot').textContent).toContain('Couldn’t check');
    expect($('#dtr-ta').value).toContain('great');
    await click('#dtr-check');
    const [a, b] = checks();
    expect(a.body.text).toBe("It's a great way to learn by doing.");
    expect(a.body.surface).toBe('repair_pass');
    expect(a.body.client_check_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(b.body.client_check_id).toBe(a.body.client_check_id);
  });

  it('a server "error" result gets a new key; two errors turn the primary into Show answer', async () => {
    mock.fail('check', 'error', 'error');
    type("It's a great way to learn by doing.");
    await click('#dtr-check');
    await click('#dtr-check');
    const [a, b] = checks();
    expect(b.body.client_check_id).not.toBe(a.body.client_check_id);
    expect($('#dtr-check').textContent).toBe('Show answer');
    await click('#dtr-check');
    expect(view()).toBe('reveal');
    expect(mock.callsTo(/reveal/)[0].body.reason).toBe('grader_failed');
  });

  it('a 7 s client timeout degrades to the same retry path', async () => {
    vi.useFakeTimers();
    mock.fail('check', 'timeout');
    type("It's a great way to learn by doing.");
    $('#dtr-check').click();
    await vi.advanceTimersByTimeAsync(7100);
    vi.useRealTimers();
    await flush();
    expect($('#dtr-slot').textContent).toContain('Couldn’t check');
    expect($('#dtr-check').getAttribute('aria-busy')).toBe('false');
  });

  it('409 CHECK_IN_PROGRESS retries once with the same key', async () => {
    mock.fail('check', 'inprogress');
    type("It's a great way to learn by doing.");
    vi.useFakeTimers();
    $('#dtr-check').click();
    await vi.advanceTimersByTimeAsync(1100);
    vi.useRealTimers();
    await flush();
    const [a, b] = checks();
    expect(b.body.client_check_id).toBe(a.body.client_check_id);
    expect(view()).toBe('ok');
  });

  it('fixed: success view, "On your own", then Next', async () => {
    type("It's a great way to learn by doing.");
    await click('#dtr-check');
    expect(view()).toBe('ok');
    expect($('#dtr-h').textContent).toBe('Fixed');
    expect($('.dtr-moment p').textContent).toBe('On your own');
    await click('#dtr-next');
    expect(view()).toBe('fix');
    expect($('#dtr-ta').value).toBe('You can make many things without it.');
  });

  it('still flagged: message, underline updated, no answer in the DOM', async () => {
    await click('#dtr-hint');
    type("It's a sick way to learn by doing. really");
    await click('#dtr-check');
    expect(view()).toBe('fix');
    expect($('#dtr-slot').textContent).toContain('Still not quite');
    expect($('#dtr-mirror mark').textContent).toBe('sick');
    expect(document.body.textContent).not.toContain('great way');
  });

  it('no_issue_found goes to the alt answer view', async () => {
    type("It's a lovely way to learn by doing.");
    await click('#dtr-check');
    expect(view()).toBe('alt');
    expect($('#dtr-h').textContent).toBe('No issue found. Compare:');
  });

  it('auto-reveals after the check cap', async () => {
    for (let i = 0; i < 4; i++) {
      type(`It's a sick way to learn by doing.${'x'.repeat(i + 1)}`);
      await click('#dtr-check');
    }
    expect(view()).toBe('reveal');
  });

  it('Enter during an IME composition does not check; plain Enter does', async () => {
    type("It's a great way to learn by doing.");
    const ta = $('#dtr-ta');
    ta.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, isComposing: true })
    );
    const e229 = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    Object.defineProperty(e229, 'keyCode', { value: 229 });
    ta.dispatchEvent(e229);
    ta.dispatchEvent(new Event('compositionstart', { bubbles: true }));
    ta.dispatchEvent(new Event('compositionend', { bubbles: true }));
    ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await flush();
    expect(checks().length).toBe(0);
    await new Promise((r) => setTimeout(r, 5));
    ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await flush();
    expect(checks().length).toBe(1);
  });
});

describe('hint ladder', () => {
  beforeEach(async () => {
    openPass('en_errors');
    await click('#dtr-go');
  });

  it('where, kind, clue replace each other in one slot and the button relabels', async () => {
    expect($('#dtr-hint').textContent).toBe('Need a hint?');
    await click('#dtr-hint');
    expect($('#dtr-slot').textContent).toContain('Hint 1 of 3');
    expect($('#dtr-slot').textContent).toContain('Look at the underlined part.');
    expect($('#dtr-mirror mark').textContent).toBe('sick');
    expect($('#dtr-hint').textContent).toBe('Another hint');
    await click('#dtr-hint');
    expect($('#dtr-slot').textContent).toContain('Register — how formal it sounds');
    expect($('#dtr-slot').textContent).not.toContain('underlined');
    await click('#dtr-hint');
    expect($('#dtr-slot').textContent).toContain('casual slang');
    expect($('#dtr-hint').textContent).toBe('Show answer');
    expect(document.querySelectorAll('#dtr-slot').length).toBe(1);
    const levels = mock.callsTo(/\/hint$/).map((c) => c.body.expected_level);
    expect(levels).toEqual([1, 2, 3]);
  });

  it('server hint text carries its own lang', async () => {
    await click('#dtr-hint');
    await click('#dtr-hint');
    expect($('#dtr-slot span[lang]').getAttribute('lang')).toBe('en');
  });

  it('Show answer asks for the reveal and shows both blocks', async () => {
    for (let i = 0; i < 3; i++) await click('#dtr-hint');
    await click('#dtr-hint');
    expect(view()).toBe('reveal');
    expect(mock.callsTo(/reveal/)[0].body.reason).toBe('asked');
  });

  it('hint failure keeps the button; the second failure makes it Show answer', async () => {
    mock.fail('hint', 'network', 'network');
    await click('#dtr-hint');
    expect($('#dtr-slot').textContent).toContain('Couldn’t load a hint');
    expect($('#dtr-hint').textContent).toBe('Need a hint?');
    await click('#dtr-hint');
    expect($('#dtr-hint').textContent).toBe('Show answer');
  });

  it('a short ladder goes straight from the where hint to Show answer', async () => {
    type("It's a great way to learn by doing.");
    await click('#dtr-check');
    await click('#dtr-next');
    await click('#dtr-hint');
    expect($('#dtr-hint').textContent).toBe('Show answer');
  });
});

describe('answer view', () => {
  it('shows You wrote (the ORIGINAL sentence, struck) above Answer (marked), then the explanation', async () => {
    openPass('en_errors');
    await click('#dtr-go');
    type("It's a cool way to learn by doing.");
    for (let i = 0; i < 4; i++) {
      type(`It's a sick way to learn by doing.${'y'.repeat(i + 1)}`);
      await click('#dtr-check');
    }
    expect(view()).toBe('reveal');
    const mine = $('#dtr-cmp-mine');
    const ans = $('#dtr-cmp-ans');
    expect(mine.compareDocumentPosition(ans) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(mine.querySelector('.dtr-tag').textContent).toBe('You wrote');
    expect(ans.querySelector('.dtr-tag').textContent).toBe('Answer');
    expect(mine.querySelector('.dtr-sent').textContent).toBe("It's a sick way to learn by doing.");
    expect(mine.querySelector('del').textContent).toBe('sick');
    expect(ans.querySelector('b').textContent).toBe('great');
    expect(mine.querySelector('.dtr-sent').lang).toBe('en');
    expect($('.dtr-why').textContent).toContain('slang');
  });

  it('renders both sentences unmarked when the mark lists are empty', async () => {
    openPass('en_mixed');
    await click('#dtr-go');
    type("It's a great way to learn by doing.");
    await click('#dtr-check');
    await click('#dtr-next');
    expect(view()).toBe('reveal'); // the direct step: reveal{reason: direct} on display
    expect(mock.callsTo(/reveal/)[0].body.reason).toBe('direct');
  });

  it('a dispute shows "Noted. Compare:"', async () => {
    openPass('en_errors');
    await click('#dtr-go');
    await click('#dtr-fine');
    expect(view()).toBe('reveal');
    expect($('#dtr-h').textContent).toBe('Noted. Compare:');
  });

  it('a failed reveal shows retry and skip, never a blank sheet', async () => {
    openPass('en_errors');
    await click('#dtr-go');
    mock.fail('reveal', 'http500');
    for (let i = 0; i < 3; i++) await click('#dtr-hint');
    await click('#dtr-hint');
    expect(view()).toBe('answer_failed');
    expect($('#dtr-retry')).not.toBeNull();
    await click('#dtr-retry');
    expect(view()).toBe('reveal');
  });
});

describe('unsure steps', () => {
  it('"Mine is fine" keeps the sentence as written', async () => {
    openPass('en_unsure');
    await click('#dtr-go');
    expect($('#dtr-lab').textContent).toContain('This part may need another look');
    expect($('#dtr-mirror mark.dtr-maybe')).not.toBeNull();
    expect($('#dtr-hint')).toBeNull();
    await click('#dtr-fine');
    expect(view()).toBe('kept');
    expect($('#dtr-h').textContent).toBe('Kept as written');
  });

  it('Check turns into the filled primary button once the text changes', async () => {
    openPass('en_unsure');
    await click('#dtr-go');
    expect($('#dtr-check').classList.contains('dtr-plain')).toBe(true);
    type('Building a simple robot arm with Arduino is a fun DIY project.');
    expect($('#dtr-check').classList.contains('dtr-primary')).toBe(true);
  });
});

describe('finishing', () => {
  it('Finish -> summary from the finish response -> Done closes with the summary', async () => {
    openPass('en_errors');
    await click('#dtr-go');
    type("It's a great way to learn by doing.");
    await click('#dtr-check');
    await click('#dtr-next');
    type('You can make many things with it.');
    await click('#dtr-check');
    expect($('#dtr-next').textContent).toBe('Finish');
    await click('#dtr-next');
    expect(view()).toBe('summary');
    expect($('.dtr-tally').textContent).toContain('Fixed yourself');
    await click('#dtr-done');
    expect(onDone).toHaveBeenCalledWith(
      expect.objectContaining({
        closedEarly: false,
        summary: expect.objectContaining({ fixed_yourself: 2 }),
      })
    );
    expect(mock.callsTo(/finish/)[0].body.closed_early).toBe(false);
    expect($('#host') === document.activeElement).toBe(true);
  });

  it('summary falls back to client counts when finish fails; Done still works', async () => {
    openPass('en_errors');
    mock.fail('finish', 'network');
    await click('#dtr-go');
    type("It's a great way to learn by doing.");
    await click('#dtr-check');
    await click('#dtr-next');
    await click('#dtr-fine');
    await click('#dtr-next');
    expect(view()).toBe('summary');
    expect($('.dtr-tally li b').textContent).toBe('1');
    await click('#dtr-done');
    expect(onDone).toHaveBeenCalled();
  });

  it('close / Escape finishes early and hands control back', async () => {
    openPass('en_errors');
    await click('#dtr-go');
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await flush();
    expect(mock.callsTo(/finish/)[0].body.closed_early).toBe(true);
    expect(onDone).toHaveBeenCalledWith(expect.objectContaining({ closedEarly: true }));
    expect($('#dtr-sheet')).toBeNull();
  });

  it('Escape closes a full-text overlay first', async () => {
    openPass('stress_ja');
    await click('#dtr-go');
    const full = document.createElement('button');
    full.className = 'dtr-full';
    $('#dtr-sheet').appendChild(full);
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await flush();
    expect($('.dtr-full')).toBeNull();
    expect($('#dtr-sheet')).not.toBeNull();
  });
});

describe('auto-advance and motion', () => {
  it('advances after auto_advance_ms; any interaction cancels it', async () => {
    vi.useFakeTimers();
    openPass('en_errors', { autoAdvance: true });
    $('#dtr-go').click();
    await vi.advanceTimersByTimeAsync(10);
    type("It's a great way to learn by doing.");
    $('#dtr-check').click();
    await vi.advanceTimersByTimeAsync(50);
    expect(view()).toBe('ok');
    await vi.advanceTimersByTimeAsync(1700);
    expect(view()).toBe('fix');
    expect($('#dtr-sheet').dataset.i).toBe('1');
    type('You can make many things with it.');
    $('#dtr-check').click();
    await vi.advanceTimersByTimeAsync(50);
    expect(view()).toBe('ok');
    $('#dtr-sheet').dispatchEvent(new Event('click', { bubbles: true }));
    await vi.advanceTimersByTimeAsync(2000);
    expect(view()).toBe('ok');
  });

  it('reduced motion: no auto-advance, Next only', async () => {
    vi.useFakeTimers();
    window.matchMedia = (q) => ({
      matches: /reduce/.test(q),
      addEventListener() {},
      removeEventListener() {},
    });
    openPass('en_errors', { autoAdvance: true });
    $('#dtr-go').click();
    await vi.advanceTimersByTimeAsync(10);
    type("It's a great way to learn by doing.");
    $('#dtr-check').click();
    await vi.advanceTimersByTimeAsync(50);
    await vi.advanceTimersByTimeAsync(3000);
    expect(view()).toBe('ok');
    delete window.matchMedia;
  });
});

describe('daily mode', () => {
  it('opens the first item with the surface, shows the from-date eyebrow and walks to the summary', async () => {
    openDaily('daily_en');
    expect(view()).toBe('fix');
    expect($('.dtr-eyebrow').textContent).toMatch(/^From your translation on /);
    expect($('#dtr-field').lang).toBe('en');
    await flush();
    expect(mock.callsTo(/\/open$/)[0].body.surface).toBe('daily_practice');
    expect($('#dtr-mirror mark')).not.toBeNull(); // the span is underlined from the start
    type('You can learn about robotics and electronics.');
    await click('#dtr-check');
    expect($('.dtr-moment p').textContent).toBe('Without any more help');
    expect(checks()[0].body.client_event_id).toMatch(/^[0-9a-f-]{36}$/);
    await click('#dtr-next');
    await click('#dtr-fine');
    await click('#dtr-next');
    expect($('#dtr-h').textContent).toBe('Practice done');
    expect($('.dtr-tally').textContent).toContain('Back in practice later');
    await click('#dtr-done');
    expect(onDone).toHaveBeenCalledWith({ completed: 2, closedEarly: false });
    expect(mock.callsTo(/finish/).length).toBe(0);
  });

  it('closing mid-item skips it', async () => {
    openDaily('daily_zh');
    await flush();
    await click('#dtr-close');
    expect(mock.callsTo(/\/skip$/).length).toBe(1);
    expect(onDone).toHaveBeenCalledWith({ completed: 0, closedEarly: true });
  });
});

describe('fixtures (§4.12) drive the same code', () => {
  it('the submit_open fixture session renders as a result view with two steps', () => {
    const fx = fixture('submit_open');
    handle = DTRepairSheet.open({
      mode: 'pass',
      session: fx.repair,
      fetch: async () => ({ ok: true, status: 200, json: async () => fixture('finish') }),
      onDone: vi.fn(),
      animate: false,
    });
    expect($('.dtr-big').textContent).toBe('2');
    expect(fx.redacted).toBe(true);
  });

  it('hint and check fixtures have the shapes the sheet reads', () => {
    expect(fixture('hint_where').where).toEqual({ start: 7, end: 11, text: 'sick', point: false });
    expect(fixture('check_fixed').outcome).toBe('self_repaired');
    expect(fixture('check_alt').answer.heading).toBe('no_issue');
    expect(fixture('check_auto_reveal').auto_reveal).toBe(true);
    expect(fixture('reveal').answer.learner_marks).toEqual([[25, 35]]);
  });

  it('a stubbed API serving the fixtures reaches the fixed view', async () => {
    const fx = fixture('submit_open');
    const fetch = vi.fn(async (url) => {
      const body = /\/check$/.test(url)
        ? fixture('check_fixed')
        : /\/open$/.test(url)
          ? { status: 'success', step: fx.repair.steps[0] }
          : fixture('finish');
      return { ok: true, status: 200, json: async () => body };
    });
    handle = DTRepairSheet.open({
      mode: 'pass',
      session: fx.repair,
      fetch,
      onDone: vi.fn(),
      animate: false,
      autoAdvance: false,
    });
    await click('#dtr-go');
    type("It's a great way to learn by doing.");
    await click('#dtr-check');
    expect(view()).toBe('ok');
    expect($('.dtr-moment p').textContent).toBe('With 1 hint');
  });
});

describe('helpers', () => {
  it('norm matches the server normalisation', () => {
    expect(DTRepairSheet.norm('  a\tb \n c  ')).toBe('a b c');
  });
});
