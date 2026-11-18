/**
 * Unit tests for the standalone page script static/js/dual_translation.js:
 * GET /next carries the selected study language, ALL_DONE has its own message,
 * and a GRADING_UNAVAILABLE submit shows the "temporarily unavailable" notice
 * instead of the retry-inviting "Grading didn't finish" banner.
 *
 * The page markup is the real template's content block (Jinja tags stripped);
 * the script is a classic IIFE, evaluated into the window and started by
 * calling its DOMContentLoaded handler.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const TEMPLATE = readFileSync(join(root, 'templates/dual_translation.html'), 'utf8');
const SCRIPT = readFileSync(join(root, 'static/js/dual_translation.js'), 'utf8');

function contentBlock() {
  const start = TEMPLATE.indexOf('{% block content %}') + '{% block content %}'.length;
  const end = TEMPLATE.indexOf('{% endblock %}', start);
  return TEMPLATE.slice(start, end).replace(/\{#[\s\S]*?#\}/g, '');
}

const PASSAGE = {
  status: 'success',
  type: 'passage',
  submission_id: 77,
  l1_text: 'It is sunny today. I went to the park.',
  age_tier: 3,
  rubric_descriptors: {},
};

let calls;
let responses;

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

// Evaluate the IIFE and run ITS DOMContentLoaded handler only (dispatching the
// event would also re-run the handlers registered by earlier tests' copies).
async function boot() {
  let init = null;
  const add = document.addEventListener;
  document.addEventListener = (type, fn, ...rest) => {
    if (type === 'DOMContentLoaded') init = fn;
    else add.call(document, type, fn, ...rest);
  };
  try {
    window.eval(SCRIPT);
  } finally {
    document.addEventListener = add;
  }
  await init();
  for (let i = 0; i < 4; i++) await flush();
}

function respond(status, body) {
  return { ok: status < 400, status, json: async () => body };
}

beforeEach(() => {
  document.body.innerHTML = contentBlock();
  window.localStorage.clear();
  window.sessionStorage.clear();
  calls = [];
  responses = {};
  window.showToast = vi.fn();
  window.LinguaMetadata = {
    load: async () => ({ languages: [{ id: 3, language_code: 'ja' }] }),
  };
  window.authFetch = vi.fn(async (url, opts) => {
    calls.push({ url, opts });
    const key = String(url).startsWith('/api/dual-translation/next') ? 'next' : 'submit';
    const queue = responses[key] || [];
    return queue.length ? queue.shift() : respond(200, PASSAGE);
  });
});

afterEach(() => {
  delete window.authFetch;
  delete window.showToast;
  delete window.LinguaMetadata;
  document.body.innerHTML = '';
});

describe('standalone DT page: GET /next', () => {
  it('sends the selected study language', async () => {
    window.localStorage.setItem('selectedLanguageId', '3');
    await boot();
    expect(calls[0].url).toBe('/api/dual-translation/next?language_id=3');
    expect(document.getElementById('dtReference').textContent).toBe(PASSAGE.l1_text);
  });

  it('lets the server choose when no language is stored', async () => {
    await boot();
    expect(calls[0].url).toBe('/api/dual-translation/next');
  });

  it('shows the all-done state with a re-serve action on ALL_DONE', async () => {
    window.localStorage.setItem('selectedLanguageId', '3');
    responses.next = [respond(404, { status: 'error', error_code: 'ALL_DONE' })];
    await boot();
    const box = document.getElementById('dtEmpty');
    expect(box.style.display).toBe('block');
    expect(box.textContent).toContain('translated every passage');
    const reserve = document.getElementById('dtReserve');
    expect(reserve.hidden).toBe(false);
    expect(document.getElementById('dtDock').hidden).toBe(false);
    expect(document.getElementById('dtBrowseTests').hidden).toBe(false);

    // The action asks for a re-serve and shows the "translated before" note.
    responses.next = [
      respond(200, {
        ...PASSAGE,
        repeat_of: { graded_at: '2026-11-10T09:00:00Z', band: 3, of_submission_id: 5 },
      }),
    ];
    reserve.click();
    for (let i = 0; i < 4; i++) await flush();
    expect(calls[1].url).toBe('/api/dual-translation/next?language_id=3&reserve=1');
    const note = document.getElementById('dtPassageNote');
    expect(note.hidden).toBe(false);
    expect(note.textContent).toContain('band 3');
    expect(note.textContent).toContain("doesn't count");
  });

  it('does not offer a re-serve when a re-serve found nothing', async () => {
    responses.next = [respond(404, { status: 'error', error_code: 'ALL_DONE' })];
    await boot();
    responses.next = [respond(404, { status: 'error', error_code: 'ALL_DONE' })];
    document.getElementById('dtReserve').click();
    for (let i = 0; i < 4; i++) await flush();
    expect(document.getElementById('dtReserve').hidden).toBe(true);
  });

  it('NO_PASSAGES is an honest empty state that points to the tests', async () => {
    responses.next = [respond(404, { status: 'error', error_code: 'NO_PASSAGES' })];
    await boot();
    expect(document.getElementById('dtEmptyMsg').textContent).toContain('reviewed translation');
    expect(document.getElementById('dtReserve').hidden).toBe(true);
    expect(document.getElementById('dtBrowseTests').getAttribute('href')).toBe('/tests');
  });

  it('notes a passage from a test not taken yet', async () => {
    responses.next = [respond(200, { ...PASSAGE, from_untaken_test: true })];
    await boot();
    const note = document.getElementById('dtPassageNote');
    expect(note.hidden).toBe(false);
    expect(note.textContent).toContain("haven't taken");
  });

  it('a normal passage has no note', async () => {
    await boot();
    expect(document.getElementById('dtPassageNote').hidden).toBe(true);
  });

  it('passes a test_id from the page URL', async () => {
    window.history.replaceState(null, '', '/dual-translation?test_id=bbbbbbbb-0000-0000-0000-000000000002');
    try {
      await boot();
      expect(calls[0].url).toBe(
        '/api/dual-translation/next?test_id=bbbbbbbb-0000-0000-0000-000000000002'
      );
    } finally {
      window.history.replaceState(null, '', '/');
    }
  });
});

describe('standalone DT page: grading unavailable', () => {
  async function submit(text) {
    document.getElementById('dtReproduction').value = text;
    document.getElementById('dtSubmit').click();
    for (let i = 0; i < 4; i++) await flush();
  }

  it('shows the unavailable notice, keeps the text and saves nothing', async () => {
    window.localStorage.setItem('selectedLanguageId', '3');
    await boot();
    responses.submit = [
      respond(503, {
        status: 'error',
        error_code: 'GRADING_UNAVAILABLE',
        error: 'Grading is temporarily unavailable.',
      }),
    ];
    await submit('今日は晴れです。');
    const notice = document.getElementById('dtUnavailableNotice');
    expect(notice.hidden).toBe(false);
    expect(notice.textContent).toContain('wasn’t graded or saved');
    expect(notice.textContent).toContain('try again');
    // still on the reproduce phase with the text, not on a (provisional) result
    expect(document.getElementById('dtReproduce').style.display).toBe('flex');
    expect(document.getElementById('dtResult').style.display).toBe('none');
    expect(document.getElementById('dtProvisionalNotice').style.display).toBe('none');
    expect(document.getElementById('dtReproduction').value).toBe('今日は晴れです。');
    expect(document.getElementById('dtSubmit').disabled).toBe(false);
    expect(document.getElementById('dtSubmit').textContent).toBe('Try again');
    expect(window.showToast).not.toHaveBeenCalled();
  });

  it('a grade with no band keeps the text and offers a retry instead of an empty result', async () => {
    await boot();
    responses.submit = [
      respond(200, { status: 'success', overall_band: null, provisional: true, diff: [], errors: [] }),
      respond(200, { status: 'success', overall_band: 3, scores: { accuracy: 3 }, diff: [], errors: [] }),
    ];
    await submit('今日は晴れです。');
    const notice = document.getElementById('dtUnavailableNotice');
    expect(notice.hidden).toBe(false);
    expect(notice.textContent).toContain('nothing was saved');
    expect(document.getElementById('dtResult').style.display).toBe('none');
    expect(document.getElementById('dtReproduction').value).toBe('今日は晴れです。');
    expect(document.getElementById('dtSubmit').textContent).toBe('Try again');
    await submit('今日は晴れです。');
    expect(notice.hidden).toBe(true);
    expect(document.getElementById('dtResult').style.display).toBe('flex');
  });

  it('a later successful submit clears the notice', async () => {
    await boot();
    responses.submit = [
      respond(503, { status: 'error', error_code: 'GRADING_UNAVAILABLE' }),
      respond(200, {
        status: 'success',
        overall_band: 3,
        scores: { accuracy: 3 },
        diff: [],
        errors: [],
      }),
    ];
    await submit('今日は晴れです。');
    expect(document.getElementById('dtUnavailableNotice').hidden).toBe(false);
    await submit('今日は晴れです。');
    expect(document.getElementById('dtUnavailableNotice').hidden).toBe(true);
    expect(document.getElementById('dtResult').style.display).toBe('flex');
  });

  it('other submit failures keep the existing toast', async () => {
    await boot();
    responses.submit = [respond(500, { status: 'error', error: 'boom' })];
    await submit('今日は晴れです。');
    expect(window.showToast).toHaveBeenCalled();
    expect(document.getElementById('dtUnavailableNotice').hidden).toBe(true);
  });
});
