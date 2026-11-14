/**
 * Unit tests for static/js/session/players/dual_translation.js result handling:
 * the grade contract carries `overall_band` (1-4), a provisional grade with no
 * band offers a re-grade, a failed submit keeps the learner's text, and
 * "See full feedback" hands the grade to the standalone page.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '../../static/js/session/players/dual_translation.js';

const PASSAGE = {
  type: 'passage',
  submission_id: 42,
  l1_text: 'The cat sat on the mat.',
  age_tier: 3,
};

let submitResponses;
let submitBodies;
let ctx;
let container;

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

async function mountAndType(text) {
  mount(container, ctx);
  await flush();
  container.querySelector('#dtInput').value = text;
  container.querySelector('[data-dt-submit]').click();
  await flush();
  await flush();
}

beforeEach(() => {
  submitResponses = [];
  submitBodies = [];
  ctx = { onComplete: vi.fn(), onSkip: vi.fn() };
  container = document.createElement('div');
  document.body.appendChild(container);
  window.localStorage.clear();
  window.authFetch = vi.fn(async (url, opts) => {
    if (url === '/api/dual-translation/next') {
      return { ok: true, status: 200, json: async () => PASSAGE };
    }
    if (String(url).endsWith('/submit')) {
      submitBodies.push(JSON.parse(opts.body));
      const r = submitResponses.shift();
      return { ok: r.status < 400, status: r.status, json: async () => r.body };
    }
    throw new Error(`unexpected fetch ${url}`);
  });
});

afterEach(() => {
  container.remove();
  delete window.authFetch;
});

describe('session DT player result', () => {
  it('shows the overall band from the grade contract', async () => {
    submitResponses.push({ status: 200, body: { status: 'success', overall_band: 3, scores: {} } });
    await mountAndType('猫がマットに座った。');
    expect(container.textContent).toContain('3');
    expect(container.textContent).toContain('/4');
    expect(container.textContent).not.toContain('Your work has been recorded');
    expect(container.querySelector('[data-dt-continue]')).not.toBeNull();
  });

  it('offers a re-grade of the same text when grading did not finish', async () => {
    submitResponses.push({
      status: 200,
      body: { status: 'success', overall_band: null, provisional: true },
    });
    submitResponses.push({ status: 200, body: { status: 'success', overall_band: 2, scores: {} } });
    await mountAndType('猫がマットに座った。');
    const retry = container.querySelector('[data-dt-retry]');
    expect(retry).not.toBeNull();
    expect(ctx.onComplete).not.toHaveBeenCalled();
    retry.click();
    await flush();
    await flush();
    expect(submitBodies).toHaveLength(2);
    expect(submitBodies[1].reproduction).toBe('猫がマットに座った。');
    expect(container.querySelector('[data-dt-continue]')).not.toBeNull();
  });

  it('keeps the text on screen when the submit fails', async () => {
    submitResponses.push({ status: 500, body: { status: 'error', error: 'boom' } });
    await mountAndType('猫がマットに座った。');
    expect(ctx.onComplete).not.toHaveBeenCalled();
    expect(container.querySelector('#dtInput').value).toBe('猫がマットに座った。');
    const err = container.querySelector('[data-dt-submit-error]');
    expect(err.hidden).toBe(false);
    expect(err.textContent).toContain('500');
    expect(container.querySelector('[data-dt-skip]').hidden).toBe(false);
  });

  it('does not submit an empty translation', async () => {
    await mountAndType('   ');
    expect(submitBodies).toHaveLength(0);
  });

  it('hands the grade to the standalone page for full feedback', async () => {
    const grade = {
      status: 'success',
      overall_band: 4,
      scores: { accuracy: 4 },
      diff: [],
      errors: [],
    };
    submitResponses.push({ status: 200, body: grade });
    await mountAndType('猫がマットに座った。');
    container.querySelector('[data-dt-details]').onclick();
    const saved = JSON.parse(window.localStorage.getItem('dt_feedback_view'));
    expect(saved.submission_id).toBe(42);
    expect(saved.l1_text).toBe(PASSAGE.l1_text);
    expect(saved.age_tier).toBe(3);
    expect(saved.reproduction).toBe('猫がマットに座った。');
    expect(saved.contract.overall_band).toBe(4);
  });
});

describe('session DT player: guided self-repair branch (tech §8.7)', () => {
  const REDACTED = {
    status: 'success',
    overall_band: 3,
    scores: { accuracy: 3 },
    errors: [],
    diff: [],
    redacted: true,
    n_errors: 2,
  };
  const FULL = {
    status: 'success',
    overall_band: 2,
    scores: { accuracy: 2 },
    errors: [{ subtype: 'x' }],
    diff: [],
  };
  const SESSION = {
    session_id: 501,
    submission_id: 42,
    status: 'open',
    clean: false,
    steps: [{ item_id: 1 }],
  };
  let opened;
  let resultResponses;
  let finishCalls;

  beforeEach(() => {
    opened = [];
    resultResponses = [];
    finishCalls = 0;
    window.DTRepairSheet = {
      open: vi.fn((o) => {
        opened.push(o);
        return { close: vi.fn(), dispose: vi.fn() };
      }),
    };
    const base = window.authFetch;
    window.authFetch = vi.fn(async (url, opts) => {
      if (String(url).includes('/repair/submissions/')) {
        const r = resultResponses.shift() || { status: 200, body: FULL };
        return { ok: r.status < 400, status: r.status, json: async () => r.body };
      }
      if (String(url).includes('/repair/sessions/')) {
        finishCalls += 1;
        return { ok: true, status: 200, json: async () => ({ status: 'success' }) };
      }
      return base(url, opts);
    });
  });

  afterEach(() => {
    delete window.DTRepairSheet;
    vi.useRealTimers();
  });

  it('no repair key: today’s band screen, no sheet', async () => {
    submitResponses.push({ status: 200, body: FULL });
    await mountAndType('x');
    expect(opened).toHaveLength(0);
    expect(container.textContent).toContain('/4');
    expect(container.querySelector('[data-dt-continue]')).not.toBeNull();
  });

  it('bypassed: today’s band screen with the full contract, no sheet', async () => {
    submitResponses.push({
      status: 200,
      body: { ...FULL, repair: { status: 'bypassed', steps: [] } },
    });
    await mountAndType('x');
    expect(opened).toHaveLength(0);
    expect(container.textContent).toContain('2');
    expect(container.querySelector('[data-dt-details]')).not.toBeNull();
  });

  it('open: the sheet opens and the redacted contract is never rendered or stashed', async () => {
    submitResponses.push({ status: 200, body: { ...REDACTED, repair: SESSION } });
    await mountAndType('x');
    expect(opened).toHaveLength(1);
    expect(opened[0].mode).toBe('pass');
    expect(opened[0].session).toEqual(SESSION);
    expect(container.querySelector('[data-dt-details]')).toBeNull();
    expect(container.textContent).not.toContain('/4');
    expect(window.localStorage.getItem('dt_feedback_view')).toBeNull();
  });

  it('open: after the sheet is done the full result is fetched and rendered by the band screen', async () => {
    submitResponses.push({ status: 200, body: { ...REDACTED, repair: SESSION } });
    await mountAndType('x');
    opened[0].onDone({ summary: null, closedEarly: false });
    await flush();
    await flush();
    expect(container.textContent).toContain('2');
    container.querySelector('[data-dt-details]').onclick();
    const saved = JSON.parse(window.localStorage.getItem('dt_feedback_view'));
    expect(saved.contract.redacted).toBeUndefined();
    expect(saved.contract.errors).toHaveLength(1);
  });

  it('open: a failing result fetch retries once, then offers retry and continue', async () => {
    vi.useFakeTimers();
    submitResponses.push({ status: 200, body: { ...REDACTED, repair: SESSION } });
    mount(container, ctx);
    await vi.advanceTimersByTimeAsync(10);
    container.querySelector('#dtInput').value = 'x';
    container.querySelector('[data-dt-submit]').click();
    await vi.advanceTimersByTimeAsync(10);
    resultResponses.push({ status: 500, body: {} }, { status: 500, body: {} });
    opened[0].onDone({ closedEarly: true });
    await vi.advanceTimersByTimeAsync(1500);
    expect(container.textContent).toContain('Couldn’t load your full feedback');
    resultResponses.push({ status: 200, body: FULL });
    container.querySelector('[data-dt-result-retry]').click();
    await vi.advanceTimersByTimeAsync(50);
    expect(container.querySelector('[data-dt-details]')).not.toBeNull();
  });

  it('open: a 409 (finish did not land) triggers one more finish', async () => {
    vi.useFakeTimers();
    submitResponses.push({ status: 200, body: { ...REDACTED, repair: SESSION } });
    mount(container, ctx);
    await vi.advanceTimersByTimeAsync(10);
    container.querySelector('#dtInput').value = 'x';
    container.querySelector('[data-dt-submit]').click();
    await vi.advanceTimersByTimeAsync(10);
    resultResponses.push(
      { status: 409, body: { error_code: 'REPAIR_IN_PROGRESS' } },
      { status: 200, body: FULL }
    );
    opened[0].onDone({ closedEarly: true, error: true });
    await vi.advanceTimersByTimeAsync(1500);
    expect(finishCalls).toBe(1);
    expect(container.querySelector('[data-dt-details]')).not.toBeNull();
  });

  it('clean: the sheet opens, then the band screen uses the full contract already in hand', async () => {
    submitResponses.push({
      status: 200,
      body: { ...FULL, repair: { ...SESSION, status: 'finished', clean: true, steps: [] } },
    });
    await mountAndType('x');
    expect(opened).toHaveLength(1);
    opened[0].onDone({ clean: true });
    await flush();
    expect(window.authFetch.mock.calls.some((c) => String(c[0]).includes('/result'))).toBe(false);
    expect(container.textContent).toContain('2');
  });

  it('sheet script missing: fetch the result and continue, no dead end', async () => {
    delete window.DTRepairSheet;
    submitResponses.push({ status: 200, body: { ...REDACTED, repair: SESSION } });
    await mountAndType('x');
    await flush();
    await flush();
    expect(container.querySelector('[data-dt-details]')).not.toBeNull();
  });

  it('destroy() disposes an open sheet', async () => {
    submitResponses.push({ status: 200, body: { ...REDACTED, repair: SESSION } });
    const handle = mount(container, ctx);
    await flush();
    container.querySelector('#dtInput').value = 'x';
    container.querySelector('[data-dt-submit]').click();
    await flush();
    await flush();
    const sheet = window.DTRepairSheet.open.mock.results[0].value;
    handle.destroy();
    expect(sheet.dispose).toHaveBeenCalled();
  });
});
