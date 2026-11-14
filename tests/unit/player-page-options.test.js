/**
 * Page-level options of the reading/listening and dictation players: what the
 * standalone test pages (static/js/pages/test.js, test-dictation.js) pass, and
 * that the session runner's defaults are untouched when none is passed.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount as mountTest } from '../../static/js/session/players/reading_listening.js';
import { mount as mountDictation } from '../../static/js/session/players/dictation.js';

const flush = async () => {
  for (let i = 0; i < 6; i++) await new Promise((r) => setTimeout(r, 0));
};
const json = (body, ok = true) => ({ ok, status: ok ? 200 : 500, json: async () => body });

const PAYLOAD = {
  test_data: {
    id: 'tid',
    title: 'A test',
    language: 'ja',
    transcript: '今日は晴れ。公園へ行く。',
    audio_url: 'https://audio.example/a.mp3',
  },
  questions_data: [{ id: 'q1', question_text: 'Q?', choices: ['a', 'b'], question_type: 'mc' }],
  vocab_token_map: [
    ['今日', 11],
    ['は晴れ。公園へ行く。', null],
  ],
  definitions: { 11: { word: '今日', definition: 'today' } },
};
const SUBMIT = {
  result: {
    score: 0,
    total_questions: 1,
    question_results: [
      { question_id: 'q1', selected_answer: 'a', correct_answer: 'b', is_correct: false },
    ],
  },
};

let calls;
let container;

beforeEach(() => {
  calls = [];
  window.authFetch = vi.fn(async (url, opts) => {
    calls.push([(opts && opts.method) || 'GET', url]);
    if (url.endsWith('/sentences')) {
      return json({
        sentences: [
          { idx: 0, l2_text: '今日は晴れ。', char_start: 0, char_end: 6, reference: { l1_text: 'Sunny.' } },
        ],
      });
    }
    if (url.endsWith('/submit')) return json(SUBMIT);
    if (url.endsWith('/submit-dictation')) {
      return json({ result: { accuracy: 100, word_correct: 1, word_total: 1, replay_count: 1, diff: [] } });
    }
    return json(PAYLOAD);
  });
  window.LinguaPrestudyLinks = {
    isPrestudied: () => false,
    clearMarker: () => {},
    renderResultActions: vi.fn(),
  };
  window.scrollTo = () => {};
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(() => Promise.resolve());
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {});
  container = document.createElement('div');
  document.body.appendChild(container);
});

afterEach(() => {
  vi.restoreAllMocks();
  container.remove();
  document.body.classList.remove('test-page');
  delete window.authFetch;
  delete window.LinguaPrestudyLinks;
});

const q = (id) => container.querySelector('#' + id);
const urls = () => calls.map((c) => c[1]);

async function takeTest(ctx) {
  const handle = mountTest(container, {
    item: { id: 'item-1', slug: 's1', test_type: 'reading' },
    languageId: 3,
    onComplete: vi.fn(),
    ...ctx,
  });
  await flush();
  return handle;
}

async function answerAndSubmit() {
  container.querySelector('.answer-option').click();
  q('submitBtn').click();
  await flush();
}

describe('reading/listening player: session defaults', () => {
  it('fetches the test and its sentences, and finishes with Next -> onComplete', async () => {
    const onComplete = vi.fn();
    await takeTest({ onComplete });
    expect(urls()).toEqual(['/api/tests/test/s1', '/api/tests/s1/sentences']);
    expect(container.querySelectorAll('.ll-sentence').length).toBe(1);

    await answerAndSubmit();
    const actions = window.LinguaPrestudyLinks.renderResultActions.mock.calls[0][1];
    expect(actions.returnTo).toBe('session');
    expect(typeof actions.beforeLeave).toBe('function');

    const btn = q('submitBtn');
    expect(btn.classList.contains('btn-primary')).toBe(true);
    btn.click();
    expect(onComplete).toHaveBeenCalledWith(SUBMIT);
  });

  it('adds no popover backdrop', async () => {
    window.innerWidth = 390;
    await takeTest();
    await answerAndSubmit();
    container.querySelector('.word-clickable').click();
    expect(q('wordDefinitionPopover').style.display).toBe('block');
    expect(document.querySelector('.word-popover-backdrop')).toBeNull();
    window.innerWidth = 1024;
  });
});

describe('reading/listening player: page options', () => {
  it('payload: renders the handed-over test without requesting it', async () => {
    await takeTest({ payload: PAYLOAD, sentences: false });
    expect(urls()).toEqual([]);
    expect(q('testTitleText').textContent).toBe('A test');
  });

  it('sentences: false keeps the plain transcript and asks for no sentence rows', async () => {
    await takeTest({ sentences: false });
    expect(urls()).toEqual(['/api/tests/test/s1']);
    expect(container.querySelectorAll('.ll-sentence').length).toBe(0);
    expect(q('transcriptText').textContent).toBe(PAYLOAD.test_data.transcript);
    expect(q('toggleReferences').style.display).toBe('none');

    await answerAndSubmit();
    expect(container.querySelectorAll('.word-clickable').length).toBe(1);
    expect(q('transcriptText').textContent).toBe(PAYLOAD.test_data.transcript);
  });

  it('ready: nothing renders until the promise settles', async () => {
    let release;
    const ready = new Promise((r) => (release = r));
    await takeTest({ ready });
    expect(container.querySelectorAll('.answer-option').length).toBe(0);
    release();
    await flush();
    expect(container.querySelectorAll('.answer-option').length).toBe(2);
  });

  it('audioPreload: sets the listening audio element preload', async () => {
    await takeTest({ item: { slug: 's1', test_type: 'listening' }, audioPreload: 'metadata' });
    expect(q('audioElement').preload).toBe('metadata');
    expect(q('audioElement').getAttribute('src')).toBe(PAYLOAD.test_data.audio_url);
  });

  it('finishButton and resultActions replace the session hand-off', async () => {
    const onComplete = vi.fn();
    const finishButton = vi.fn((btn) => {
      btn.textContent = 'Back';
    });
    await takeTest({ onComplete, finishButton, resultActions: {} });
    await answerAndSubmit();

    const actions = window.LinguaPrestudyLinks.renderResultActions.mock.calls[0][1];
    expect(actions).toEqual({ slug: 's1', type: 'reading', wrong: 1, prestudied: false });

    const btn = q('submitBtn');
    expect(finishButton).toHaveBeenCalledWith(btn, SUBMIT, { testId: 'tid' });
    expect(btn.disabled).toBe(false);
    expect(btn.classList.contains('btn-success')).toBe(true);
    btn.click();
    expect(onComplete).not.toHaveBeenCalled();
    expect(calls.filter((c) => c[0] === 'POST').length).toBe(1);
  });

  it('popoverBackdrop: dims the page on a phone and clears with the popover', async () => {
    window.innerWidth = 390;
    const handle = await takeTest({ popoverBackdrop: true });
    await answerAndSubmit();
    container.querySelector('.word-clickable').click();
    const backdrop = document.querySelector('.word-popover-backdrop');
    expect(backdrop.style.display).toBe('block');
    backdrop.click();
    expect(backdrop.style.display).toBe('none');
    expect(q('wordDefinitionPopover').style.display).toBe('none');
    handle.destroy();
    expect(document.querySelector('.word-popover-backdrop')).toBeNull();
    window.innerWidth = 1024;
  });

  it('rerender() redraws the questions and keeps the answers', async () => {
    const handle = await takeTest();
    container.querySelector('.answer-option').click();
    const before = container.querySelector('.question-card');
    handle.rerender();
    expect(container.querySelector('.question-card')).not.toBe(before);
    expect(container.querySelectorAll('.answer-option.selected').length).toBe(1);
    expect(q('submitBtn').disabled).toBe(false);
  });
});

async function takeDictation(ctx) {
  mountDictation(container, { item: { slug: 'd1' }, languageId: 3, onComplete: vi.fn(), ...ctx });
  await flush();
}

async function playTypeSubmit() {
  q('playBtn').click();
  await flush();
  q('dictationInput').value = '今日';
  q('dictationInput').dispatchEvent(new Event('input'));
  q('submitBtn').click();
  await flush();
}

describe('dictation player: session defaults', () => {
  it('has no Back link and finishes with Next -> onComplete', async () => {
    const onComplete = vi.fn();
    await takeDictation({ onComplete });
    expect(container.querySelectorAll('a[href]').length).toBe(0);
    expect(q('audioElement').preload).toBe('auto');
    await playTypeSubmit();
    container.querySelector('[data-session-next]').click();
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});

describe('dictation player: page options', () => {
  it('backHref: adds Back to the footer and the error state', async () => {
    await takeDictation({ backHref: '/tests' });
    const footer = container.querySelector('.dict-actions-row');
    expect(footer.firstElementChild.getAttribute('href')).toBe('/tests');
    expect(footer.lastElementChild).toBe(q('submitBtn'));
    expect(q('errorState').querySelector('a.btn-danger').getAttribute('href')).toBe('/tests');
  });

  it('audioPreload and ready', async () => {
    let release;
    const ready = new Promise((r) => (release = r));
    await takeDictation({ audioPreload: 'metadata', ready });
    expect(calls.length).toBe(0);
    release();
    await flush();
    expect(urls()).toEqual(['/api/tests/test/d1?mode=dictation']);
    expect(q('audioElement').preload).toBe('metadata');
  });

  it('resultActions: fills the results actions instead of Next', async () => {
    const onComplete = vi.fn();
    const resultActions = vi.fn((el) => {
      el.innerHTML = '<a href="/tests">All Tests</a>';
    });
    await takeDictation({ onComplete, resultActions });
    await playTypeSubmit();
    const actions = container.querySelector('.dict-results-actions');
    expect(container.querySelector('[data-session-next]')).toBeNull();
    expect(actions.querySelector('a').getAttribute('href')).toBe('/tests');
    const [el, response, info] = resultActions.mock.calls[0];
    expect(el).toBe(actions);
    expect(response.result.accuracy).toBe(100);
    expect(info).toEqual({ slug: 'd1', testData: PAYLOAD.test_data });
    expect(onComplete).not.toHaveBeenCalled();
  });
});
