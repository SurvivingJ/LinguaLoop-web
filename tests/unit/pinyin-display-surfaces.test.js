/**
 * TASK-999 / TASK-997: Chinese pronunciations shown as tone-marked pinyin only
 * on the remaining surfaces, and the "Type it as" hint after a missed typed
 * reading (new-word drill and prestudy), which is always a form the reading
 * checker accepts.
 */

import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest';
import { displayPronunciation } from '../../static/js/session/pinyin-format.js';
import { typeableReading, runIntroDrill } from '../../static/js/session/players/intro_drill.js';
import { mount } from '../../static/js/session/players/reading_listening.js';

let LP;
beforeAll(async () => {
  await import('../../static/js/prestudy/prestudy.js');
  LP = window.LinguaPrestudy;
});

describe('displayPronunciation', () => {
  it.each([
    ['biàn dé (bian4 de2)', 'zh', 'biàn dé'],
    ['bi3', 'zh', 'bǐ'],
    ['bi3', 1, 'bǐ'],
    ['lu:3 se4', '1', 'lǚ sè'],
    ['zhāng', 'zh', 'zhāng'],
    ['きょう', 'ja', 'きょう'],
    ['bian4 de2', 'ja', 'bian4 de2'],
    ['bian4 de2', '', 'bian4 de2'],
    [null, 'zh', ''],
    [undefined, 'ja', ''],
  ])('%s (%s) -> %s', (text, lang, out) => {
    expect(displayPronunciation(text, lang)).toBe(out);
  });

  it('is exposed for classic page scripts', () => {
    expect(window.LinguaPinyin.formatPinyin('biàn dé (bian4 de2)')).toBe('biàn dé');
    expect(window.LinguaPinyin.displayPronunciation('きょう', 'ja')).toBe('きょう');
  });
});

// ---------------------------------------------------------------------------
// "Type it as" (TASK-997)
// ---------------------------------------------------------------------------

const zhWord = (numbered, lemma = '变得', shown = 'biàn dé') => ({
  sense_id: 1,
  lemma,
  gloss: 'to become',
  reading: { shown, numbered },
});

const accepted = (input, word) => {
  const p = LP.parsePinyinInput(input);
  return LP.gradeZh(p.segs, p.tones, word.reading.numbered, word.lemma).ok;
};

describe('new-word drill: typeableReading', () => {
  it('Chinese: the numbered form, which the checker accepts', () => {
    const w = zhWord('bian4 de2');
    expect(typeableReading(w, 'zh')).toBe('bian4 de2');
    expect(accepted('bian4 de2', w)).toBe(true);
  });

  it('ü written as v, the way it is typed, and still accepted', () => {
    const w = zhWord('lu:3 se4', '绿色', 'lǜ sè');
    const t = typeableReading(w, 'zh');
    expect(t).toBe('lv3 se4');
    expect(accepted(t, w)).toBe(true);
  });

  it('extra spaces are collapsed', () => {
    expect(typeableReading(zhWord('  bian4   de2 '), 'zh')).toBe('bian4 de2');
  });

  it('nothing for Japanese, missing readings or a form the checker rejects', () => {
    expect(typeableReading({ lemma: '今日', reading: { shown: 'きょう', numbered: null } }, 'ja')).toBe(null);
    expect(typeableReading({ lemma: '变得', reading: null }, 'zh')).toBe(null);
    expect(typeableReading(zhWord(null), 'zh')).toBe(null);
    expect(typeableReading(zhWord('???'), 'zh')).toBe(null);
  });
});

describe('prestudy: typeAs', () => {
  const rp = (numbered, hanzi = '木头') => ({ shown: 'mù tou', numbered, hanzi });

  it('Chinese test: the numbered form, accepted by the same grader', () => {
    const r = rp('mu4 tou5');
    const t = LP.typeAs(r, 1);
    expect(t).toBe('mu4 tou5');
    const p = LP.parsePinyinInput(t);
    expect(LP.gradeZh(p.segs, p.tones, r.numbered, r.hanzi).ok).toBe(true);
  });

  it('not for Japanese or without a numbered form', () => {
    expect(LP.typeAs(rp('mu4 tou5'), 3)).toBe(null);
    expect(LP.typeAs(rp(null), 1)).toBe(null);
    expect(LP.typeAs(null, 1)).toBe(null);
  });

  it('readingParts keeps the numbered half for grading', () => {
    const parts = LP.readingParts({ reading: 'mù tou (mu4 tou5)', lemma: '木头' });
    expect(parts.numbered).toBe('mu4 tou5');
    expect(parts.shown).toBe('mù tou');
  });
});

// ---------------------------------------------------------------------------
// Tap-a-word popover (reading_listening.js)
// ---------------------------------------------------------------------------

const flush = async () => {
  for (let i = 0; i < 6; i++) await new Promise((r) => setTimeout(r, 0));
};
const json = (body) => ({ ok: true, status: 200, json: async () => body });

let container;
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
  container.remove();
  delete window.authFetch;
  delete window.LinguaPrestudyLinks;
});

async function popoverReading(language, reading) {
  const payload = {
    test_data: { id: 'tid', title: 'T', language, transcript: '词。' },
    questions_data: [{ id: 'q1', question_text: 'Q?', choices: ['a', 'b'], question_type: 'mc' }],
    vocab_token_map: [
      ['词', 7],
      ['。', null],
    ],
    definitions: { 7: { word: '词', definition: 'word', part_of_speech: 'noun', reading } },
  };
  const submit = {
    result: {
      score: 1,
      total_questions: 1,
      question_results: [
        { question_id: 'q1', selected_answer: 'a', correct_answer: 'a', is_correct: true },
      ],
    },
  };
  window.authFetch = vi.fn(async (url) => (url.endsWith('/submit') ? json(submit) : json(payload)));
  mount(container, {
    item: { id: 'i', slug: 's1', test_type: 'reading' },
    languageId: language === 'ja' ? 3 : 1,
    sentences: false,
    onComplete: vi.fn(),
  });
  await flush();
  container.querySelector('.answer-option').click();
  container.querySelector('#submitBtn').click();
  await flush();
  const word = container.querySelector('.word-clickable');
  expect(word).toBeTruthy();
  word.click();
  await flush();
  return container.querySelector('#popoverReading');
}

describe('tap-a-word popover reading', () => {
  it('Chinese: a stored "marked (numbered)" form shows tone marks only', async () => {
    const el = await popoverReading('cn', 'biàn dé (bian4 de2)');
    expect(el.textContent).toBe('biàn dé');
    expect(el.style.display).toBe('block');
  });

  it('Chinese: numbered pinyin is converted', async () => {
    expect((await popoverReading('zh', 'ci2')).textContent).toBe('cí');
  });

  it('Japanese: the kana reading as given', async () => {
    expect((await popoverReading('ja', 'ことば')).textContent).toBe('ことば');
  });

  it('no reading: hidden', async () => {
    expect((await popoverReading('zh', null)).style.display).toBe('none');
  });
});

// ---------------------------------------------------------------------------
// New-word drill feedback (TASK-997): the hint shows after a missed typed
// reading only
// ---------------------------------------------------------------------------

describe('new-word drill feedback', () => {
  async function answer(lang, word, format, input) {
    window.authFetch = vi.fn(async () => json({ ok: true }));
    const card = document.createElement('div');
    container.appendChild(card);
    runIntroDrill(card, { lang, words: [{ ...word, formats: [format], stage: 1, target: 5, cap: 12 }] });
    await flush();
    if (input === null) {
      card.querySelector('#introIdk').click();
    } else if (format.startsWith('read')) {
      card.querySelector('#introTyped').value = input;
      card.querySelector('#introTypedForm').dispatchEvent(new Event('submit', { cancelable: true }));
    } else {
      card.querySelector('.exercise-option').click();
    }
    await flush();
    return card.querySelector('#introFb');
  }
  const zh = { sense_id: 1, lemma: '变得', gloss: 'to become', pos: 'verb', reading: { shown: 'biàn dé', numbered: 'bian4 de2' } };

  it('wrong typed reading: tone-marked answer plus how to type it', async () => {
    const fb = await answer('zh', zh, 'read_typed', 'bian1 de1');
    expect(fb.querySelector('.intro-fb-line').textContent).toContain('biàn dé');
    expect(fb.querySelector('.intro-fb-line').textContent).not.toContain('bian4');
    expect(fb.querySelector('.intro-fb-type').textContent).toBe('Type it as: bian4 de2');
  });

  it("skipped (I don't know): the hint too", async () => {
    const fb = await answer('zh', zh, 'read_typed', null);
    expect(fb.querySelector('.intro-fb-type').textContent).toBe('Type it as: bian4 de2');
  });

  it('right typed reading: no hint', async () => {
    const fb = await answer('zh', zh, 'read_typed', 'bian4 de2');
    expect(fb.querySelector('.ld-feedback--ok')).toBeTruthy();
    expect(fb.querySelector('.intro-fb-type')).toBe(null);
  });

  it('other items (meaning choice): no hint even when wrong', async () => {
    const words = { ...zh };
    const fb = await answer('zh', words, 'def_mc', '');
    expect(fb.querySelector('.intro-fb-type')).toBe(null);
  });

  it('Japanese typed reading: no hint', async () => {
    const ja = { sense_id: 2, lemma: '今日', gloss: 'today', pos: 'noun', reading: { shown: 'きょう', numbered: null } };
    const fb = await answer('ja', ja, 'read_typed', 'あした');
    expect(fb.querySelector('.ld-feedback--bad')).toBeTruthy();
    expect(fb.querySelector('.intro-fb-type')).toBe(null);
  });
});
