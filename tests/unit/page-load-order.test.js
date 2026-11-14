/**
 * Page scripts send their first API requests without waiting for things that
 * only rendering needs:
 *  - pages/test-list.js: the three list requests do not wait for i18n;
 *  - pages/study-plan.js: plan + templates are requested alongside the ELO
 *    call for the language the page opened on last time.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const read = (rel) => readFileSync(join(root, rel), 'utf8');
const run = (code) => (0, eval)(code);

// The template's markup with the Jinja tags removed.
function markup(template) {
  const html = read(`templates/${template}`);
  const content = html.split('{% block content %}')[1].split('{% endblock %}')[0];
  return content.replace(/\{%[\s\S]*?%\}/g, '').replace(/\{\{[\s\S]*?\}\}/g, '#');
}

function jsonResponse(body, status = 200) {
  return {
    ok: status < 400,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  };
}
const flush = async () => {
  for (let i = 0; i < 20; i++) await Promise.resolve();
};

let requested;

beforeEach(() => {
  localStorage.clear();
  requested = [];
  // utils.js is evaluated by setup.js; page scripts read its helpers as globals.
  Object.assign(globalThis, {
    debugLog: () => {},
    escapeHtml: window.LinguaUtils.escapeHtml,
    getDifficultyInfo: window.LinguaUtils.getDifficultyInfo,
    getDifficultyText: window.LinguaUtils.getDifficultyText,
  });
  window.LinguaI18n = { t: (key) => key, init: () => Promise.resolve() };
  globalThis.LinguaI18n = window.LinguaI18n;
});

afterEach(() => {
  delete window.LinguaI18n;
  delete globalThis.LinguaI18n;
  delete window.authFetch;
});

describe('pages/test-list.js', () => {
  const TEST = { slug: 's1', title: 'A <b>title</b>', language_id: 3, listening_rating: 1400 };
  let i18nLoaded;
  let realLoad;

  beforeEach(() => {
    document.body.innerHTML = markup('test_list.html');
    localStorage.setItem('selectedLanguageId', '3');
    realLoad = window.LinguaMetadata.load;
    const gate = new Promise((resolve) => {
      i18nLoaded = resolve;
    });
    window.LinguaMetadata.load = () => gate;
    window.authFetch = vi.fn(async (url) => {
      requested.push(url);
      if (url.startsWith('/api/tests?')) return jsonResponse({ tests: [TEST] });
      if (url.startsWith('/api/tests/recommended')) return jsonResponse({ recommended_tests: [] });
      return jsonResponse({});
    });
  });

  afterEach(() => {
    window.LinguaMetadata.load = realLoad;
  });

  it('requests all three lists before translations have loaded, and renders after', async () => {
    run(read('static/js/pages/test-list.js'));
    await flush();
    expect(requested).toEqual([
      '/api/tests?language_id=3',
      '/api/tests/recommended?language_id=3',
      '/api/tests/daily-load?language_id=3',
    ]);
    expect(document.querySelectorAll('.test-card').length).toBe(0);

    i18nLoaded({ languages: [] });
    await flush();
    const cards = document.querySelectorAll('.test-card');
    expect(cards.length).toBe(1);
    expect(cards[0].innerHTML).toContain('A &lt;b&gt;title&lt;/b&gt;');
    expect(requested.length).toBe(3);
  });

  it('shows the error only once translations are there to word it', async () => {
    window.authFetch = vi.fn(async () => jsonResponse({}, 500));
    run(read('static/js/pages/test-list.js'));
    await flush();
    const alert = document.getElementById('error-state');
    expect(alert.classList.contains('d-none')).toBe(true);
    i18nLoaded({ languages: [] });
    await flush();
    expect(alert.classList.contains('d-none')).toBe(false);
  });
});

describe('pages/study-plan.js', () => {
  const ELO = { ratings: { ja: { language_id: 3, native_name: '日本語' } } };
  const PLAN = {
    plan: { daily_minutes: 45, weekday_shape: [1, 1, 1, 1, 1, 1, 1], template_id: 1 },
    current_week: null,
    available_modules: [],
  };
  let answerElo;

  function start() {
    window.authFetch = vi.fn((url) => {
      requested.push(url);
      if (url === '/api/users/elo') {
        return new Promise((resolve) => {
          answerElo = () => resolve(jsonResponse(ELO));
        });
      }
      if (url.startsWith('/api/study-plan/templates')) {
        return Promise.resolve(
          jsonResponse({ templates: [{ template_id: 1, daily_minutes: 45, is_default: true }] })
        );
      }
      return Promise.resolve(jsonResponse(PLAN));
    });
    run(read('static/js/study-plan-settings.js'));
    run(read('static/js/weekly-study.js'));
    // Run only this instance's DOMContentLoaded handler, not earlier tests'.
    const ready = [];
    const spy = vi.spyOn(document, 'addEventListener').mockImplementation((type, fn) => {
      if (type === 'DOMContentLoaded') ready.push(fn);
    });
    run(read('static/js/pages/study-plan.js'));
    spy.mockRestore();
    ready.forEach((fn) => fn());
  }

  beforeEach(() => {
    document.body.innerHTML = markup('study_plan.html');
  });

  it('requests plan and templates alongside the ELO call when it knows the language', async () => {
    localStorage.setItem('selectedLanguageId', '3');
    start();
    await flush();
    expect(requested).toEqual([
      '/api/study-plan?language_id=3',
      '/api/study-plan/templates?language_id=3',
      '/api/users/elo',
    ]);

    answerElo();
    await flush();
    // The prefetched responses are used: nothing is requested twice.
    expect(requested.length).toBe(3);
    expect(document.getElementById('planEditor').classList.contains('d-none')).toBe(false);
    expect(document.getElementById('dailyMinutesNumber').value).toBe('45');
    expect(localStorage.getItem('linguadojo-study-plan-lang')).toBe('3');
  });

  it('fetches for the right language when the guess was wrong', async () => {
    localStorage.setItem('selectedLanguageId', '1');
    start();
    await flush();
    answerElo();
    await flush();
    expect(requested.filter((u) => u.endsWith('language_id=3')).length).toBe(2);
    expect(document.getElementById('dailyMinutesNumber').value).toBe('45');
    // Remembered, so the next visit guesses right.
    expect(localStorage.getItem('linguadojo-study-plan-lang')).toBe('3');
  });

  it('without a hint waits for the ELO response as before', async () => {
    start();
    await flush();
    expect(requested).toEqual(['/api/users/elo']);
  });
});
