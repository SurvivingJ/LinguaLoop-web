/**
 * Post-test vocab check (reading_listening.js wordQuiz): a Chinese word's
 * pronunciation is shown as tone-marked pinyin only, never with the numbered
 * duplicate ("biàn dé (bian4 de2)") or as numbered pinyin ("bi3"). Japanese
 * readings are shown as given.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '../../static/js/session/players/reading_listening.js';

const flush = async () => {
  for (let i = 0; i < 6; i++) await new Promise((r) => setTimeout(r, 0));
};
const json = (body) => ({ ok: true, status: 200, json: async () => body });

function payload(language, transcript) {
  return {
    test_data: { id: 'tid', title: 'T', language, transcript },
    questions_data: [{ id: 'q1', question_text: 'Q?', choices: ['a', 'b'], question_type: 'mc' }],
    vocab_token_map: [[transcript, null]],
    definitions: {},
  };
}

function submit(candidates) {
  return {
    result: {
      score: 1,
      total_questions: 1,
      question_results: [
        { question_id: 'q1', selected_answer: 'a', correct_answer: 'a', is_correct: true },
      ],
      word_quiz: { attempt_id: 'att', candidates },
    },
  };
}

const cand = (lemma, pronunciation) => ({
  sense_id: 1,
  lemma,
  pronunciation,
  correct_definition: 'right',
  options: ['right', 'wrong 1', 'wrong 2'],
});

let container;

function stub(pl, sub) {
  window.authFetch = vi.fn(async (url) => (url.endsWith('/submit') ? json(sub) : json(pl)));
}

beforeEach(() => {
  window.LinguaPrestudyLinks = {
    isPrestudied: () => false,
    clearMarker: () => {},
    renderResultActions: vi.fn(),
  };
  window.scrollTo = () => {};
  container = document.createElement('div');
  document.body.appendChild(container);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
  container.remove();
  delete window.authFetch;
  delete window.LinguaPrestudyLinks;
});

const q = (id) => container.querySelector('#' + id);

async function takeAndOpenQuiz(languageId) {
  mount(container, {
    item: { id: 'i', slug: 's1', test_type: 'reading' },
    languageId,
    sentences: false,
    onComplete: vi.fn(),
  });
  await flush();
  container.querySelector('.answer-option').click();
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  q('submitBtn').click();
  await vi.advanceTimersByTimeAsync(700);
  expect(q('wordQuizModal').style.display).toBe('block');
}

describe('vocab check pronunciation', () => {
  it('Chinese: drops the numbered duplicate and converts numbered pinyin', async () => {
    stub(
      payload('cn', '变得很快。'),
      submit([cand('变得', 'biàn dé (bian4 de2)'), cand('笔', 'bi3')]),
    );
    await takeAndOpenQuiz(1);
    expect(q('quizLemma').textContent).toBe('变得');
    expect(q('quizPronunciation').textContent).toBe('biàn dé');

    container.querySelector('.quiz-option').click(); // shuffled order: may be wrong
    if (q('quizNextBtn').style.display !== 'none') q('quizNextBtn').click();
    await vi.advanceTimersByTimeAsync(900);
    expect(q('quizLemma').textContent).toBe('笔');
    expect(q('quizPronunciation').textContent).toBe('bǐ');
  });

  it('Japanese: the kana reading is shown as given', async () => {
    stub(payload('ja', '今日は晴れ。'), submit([cand('今日', 'きょう')]));
    await takeAndOpenQuiz(3);
    expect(q('quizPronunciation').textContent).toBe('きょう');
    expect(q('quizPronunciation').style.display).toBe('block');
  });
});
