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
