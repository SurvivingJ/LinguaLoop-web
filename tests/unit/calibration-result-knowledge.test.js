/**
 * static/js/pages/calibration.js — the result screen shows the Knowledge Report's word range
 * (TASK-1042, P16, OQ33): the same range sentence, label and dates as /knowledge with a link to
 * "My vocabulary"; the reason line when there is no range yet; nothing when the report API answers
 * 404 / 503 / fails. The check's own frequency level gains a sub-line naming what it measures.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const TEMPLATE = readFileSync(join(root, 'templates/calibration.html'), 'utf8');
const SCRIPT = readFileSync(join(root, 'static/js/pages/calibration.js'), 'utf8');
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
  if (params) {
    Object.keys(params).forEach((p) => {
      text = text.replace(new RegExp('\\{' + p + '\\}', 'g'), params[p]);
    });
  }
  return text;
}

const d = (iso) =>
  new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(
    new Date(iso + 'T00:00:00Z')
  );

const ABILITY = {
  ability_zipf_85: 4.31,
  ability_zipf_85_sd: 0.27,
  answered: 70,
  correct: 41,
  confidence: 'medium',
  bands: [],
};

function respond(status, body) {
  return { ok: status < 400, status, json: async () => body };
}

function estimateShown() {
  return {
    status: 'success',
    estimate: {
      shown: true,
      kind: 'range',
      lo: 850,
      hi: 1400,
      label: 'medium',
      universe_words: 3175,
      answers: 172,
      first_answer_at: '2026-09-13',
      last_answer_at: '2026-11-15',
      reason: null,
    },
  };
}

let knowledgeResponse;
let calls;

const flush = async () => {
  for (let i = 0; i < 12; i++) await new Promise((r) => setTimeout(r, 0));
};

async function finishRun(ability = ABILITY) {
  window.authFetch = vi.fn(async (url) => {
    calls.push(url);
    if (url === '/api/calibration/start')
      return respond(200, { status: 'success', session_id: 's1' });
    if (url.startsWith('/api/calibration/next'))
      return respond(200, { items: [], exhausted: true });
    if (url === '/api/calibration/end') return respond(200, { status: 'success', ability });
    if (url.startsWith('/api/knowledge/summary')) {
      if (knowledgeResponse instanceof Error) throw knowledgeResponse;
      return knowledgeResponse;
    }
    return respond(404, {});
  });
  window.eval(SCRIPT);
  await flush();
  document.getElementById('calFinishBtn').click();
  await flush();
}

const box = () => document.getElementById('calKnowledge');

beforeEach(() => {
  // The running counts live in the task header (base.html's task_subtitle block).
  document.body.innerHTML = '<b id="calAnswered"></b><b id="calAccuracy"></b>' + markup();
  localStorage.clear();
  localStorage.setItem('selectedLanguageId', '3');
  calls = [];
  window.LinguaI18n = { t, currentLanguage: () => 'en' };
});

afterEach(() => {
  delete window.authFetch;
  delete window.LinguaI18n;
  document.body.innerHTML = '';
});

describe('calibration result: My vocabulary range', () => {
  it('shows the report range, label, dates and the link when an estimate is shown', async () => {
    knowledgeResponse = respond(200, estimateShown());
    await finishRun();
    expect(calls).toContain('/api/knowledge/summary?language_id=3');
    expect(box().hidden).toBe(false);
    const text = box().textContent;
    expect(text).toContain(
      'In the vocabulary check you recognised about 850–1,400 of the 3,175 Japanese words it draws from.'
    );
    expect(text).toContain(
      `From 172 check answers, ${d('2026-09-13')} – ${d('2026-11-15')} · Medium`
    );
    const link = box().querySelector('a');
    expect(link.getAttribute('href')).toBe('/knowledge');
    expect(link.textContent).toBe('See My vocabulary');
  });

  it('shows the reason line and the link when there is no estimate yet', async () => {
    knowledgeResponse = respond(200, {
      status: 'success',
      estimate: { shown: false, kind: 'none', reason: 'too_few_answers', have: 41 },
    });
    await finishRun();
    expect(box().hidden).toBe(false);
    expect(box().textContent).toContain('41 of 70 answers so far');
    expect(box().querySelector('a[href="/knowledge"]')).not.toBeNull();
  });

  it.each([404, 503])('renders nothing on %i', async (status) => {
    knowledgeResponse = respond(status, { status: 'error' });
    await finishRun();
    expect(box().hidden).toBe(true);
    expect(box().textContent).toBe('');
  });

  it('renders nothing when the request fails', async () => {
    knowledgeResponse = new TypeError('network down');
    await finishRun();
    expect(box().hidden).toBe(true);
  });

  it("labels the check's own frequency level", async () => {
    knowledgeResponse = respond(404, {});
    await finishRun();
    const measure = document.getElementById('calResultMeasure');
    expect(document.getElementById('calResultLevel').textContent).toBe('4.31 ± 0.27');
    expect(measure.hidden).toBe(false);
    expect(measure.textContent).toContain("this check's own measure");
  });

  it('hides that sub-line when there is no frequency level yet', async () => {
    knowledgeResponse = respond(404, {});
    await finishRun({ answered: 4, correct: 2, bands: [] });
    expect(document.getElementById('calResultMeasure').hidden).toBe(true);
  });
});
