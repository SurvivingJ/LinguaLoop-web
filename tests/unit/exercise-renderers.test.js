/**
 * Unit tests for static/js/exercise-renderers.js
 *
 * ExRenderers is an IIFE that exposes its public API via window.ExRenderers
 * (set at the end of the file).  The setup.js file evals it into jsdom.
 *
 * Covered: escHtml, shuffleArr, fmtType — the pure utilities.
 * dispatch routing is covered with a minimal card stub.
 * DOM-heavy renderers (mcq, cloze, etc.) are not individually unit-tested;
 * they are exercise-level integration concerns covered by Playwright E2E.
 */

import { describe, it, expect, beforeEach } from 'vitest';

const R = () => window.ExRenderers;

// ---------------------------------------------------------------------------
// escHtml — delegates to LinguaUtils.escapeHtml when available
// ---------------------------------------------------------------------------

describe('escHtml', () => {
  it('escapes angle brackets', () => {
    expect(R().escHtml('<b>bold</b>')).toBe('&lt;b&gt;bold&lt;/b&gt;');
  });

  it('escapes & character', () => {
    expect(R().escHtml('a & b')).toBe('a &amp; b');
  });

  it('returns empty string for falsy input', () => {
    expect(R().escHtml('')).toBe('');
    expect(R().escHtml(null)).toBe('');
    expect(R().escHtml(undefined)).toBe('');
  });

  it('delegates to window.LinguaUtils.escapeHtml (same result as canonical impl)', () => {
    const payload = '<script>alert("xss")</script>';
    expect(R().escHtml(payload)).toBe(window.LinguaUtils.escapeHtml(payload));
  });
});

// ---------------------------------------------------------------------------
// shuffleArr — returns a permutation; does not mutate the input
// ---------------------------------------------------------------------------

describe('shuffleArr', () => {
  it('returns an array of the same length', () => {
    const arr = [1, 2, 3, 4, 5];
    expect(R().shuffleArr(arr)).toHaveLength(arr.length);
  });

  it('contains exactly the same elements', () => {
    const arr = ['a', 'b', 'c', 'd'];
    const result = R().shuffleArr(arr);
    expect(result.sort()).toEqual([...arr].sort());
  });

  it('does not mutate the original array', () => {
    const arr = [10, 20, 30];
    const copy = [...arr];
    R().shuffleArr(arr);
    expect(arr).toEqual(copy);
  });

  it('handles an empty array', () => {
    expect(R().shuffleArr([])).toEqual([]);
  });

  it('handles a single-element array', () => {
    expect(R().shuffleArr(['only'])).toEqual(['only']);
  });
});

// ---------------------------------------------------------------------------
// fmtType — converts snake_case exercise type to Title Case
// (LinguaI18n is not available in tests, so the fallback path runs)
// ---------------------------------------------------------------------------

describe('fmtType', () => {
  it.each([
    ['cloze_completion', 'Cloze Completion'],
    ['odd_one_out', 'Odd One Out'],
    ['tl_nl_translation', 'Tl Nl Translation'],
    ['collocation_gap_fill', 'Collocation Gap Fill'],
    ['jumbled_sentence', 'Jumbled Sentence'],
  ])('formats %s → %s', (type, expected) => {
    expect(R().fmtType(type)).toBe(expected);
  });

  it('leaves a single word unchanged except capitalisation', () => {
    expect(R().fmtType('cloze')).toBe('Cloze');
  });
});

// ---------------------------------------------------------------------------
// dispatch — routes to correct renderer based on exercise type
// ---------------------------------------------------------------------------

describe('dispatch routing', () => {
  let card;

  beforeEach(() => {
    card = document.createElement('div');
    document.body.appendChild(card);

    // Minimal stubs — dispatch requires init() to be called first
    R().init({
      cardEl: card,
      isAnswered: () => false,
      setAnswered: () => {},
      showFeedback: () => {},
      submitAttempt: () => {},
      nextExercise: () => {},
    });
  });

  afterEach(() => {
    card.remove();
  });

  it('renders something into the card for a cloze_completion exercise', () => {
    R().dispatch(
      'cloze_completion',
      {},
      {
        sentence_with_blank: 'I ___ to the store.',
        options: ['went', 'go', 'gone'],
        correct_answer: 'went',
        explanation: 'Past tense.',
      },
      ''
    );
    expect(card.innerHTML).not.toBe('');
    expect(card.innerHTML).toContain('option');
  });

  it('renders something for odd_one_out', () => {
    // renderOddOneOut reads c.items (array) and c.odd_index (number)
    R().dispatch(
      'odd_one_out',
      {},
      {
        items: ['apple', 'banana', 'car', 'orange'],
        odd_index: 2,
        explanation: 'Not a fruit.',
      },
      ''
    );
    expect(card.innerHTML).not.toBe('');
    expect(card.innerHTML).toContain('apple');
  });

  it('falls back to generic renderer for unknown exercise type', () => {
    // renderGeneric reads ex.exercise_type — pass it to avoid a crash
    expect(() => {
      R().dispatch('nonexistent_type', { exercise_type: 'nonexistent_type' }, {}, '');
    }).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// Ladder renderers for the ten types that previously fell through to
// renderGeneric (raw JSON). Each fixture is a real content shape taken from a
// live row, minus the `hant` mirror (which is selected server-side).
// ---------------------------------------------------------------------------

describe('ladder script/sound, measure-word and relation renderers', () => {
  let card;
  let submitted;

  beforeEach(() => {
    card = document.createElement('div');
    document.body.appendChild(card);
    submitted = [];
    let answered = false;
    R().init({
      cardEl: card,
      isAnswered: () => answered,
      setAnswered: (v) => {
        answered = v;
      },
      showFeedback: () => {},
      submitAttempt: (ok, resp) => submitted.push({ ok, resp }),
      nextExercise: () => {},
    });
  });

  afterEach(() => {
    card.remove();
  });

  const click = (value) => {
    const el = card.querySelector(`.exercise-option[data-value="${value}"]`);
    expect(el, `no option with value ${value}`).not.toBeNull();
    el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  };

  const FIXTURES = {
    hanzi_to_pinyin: {
      prompt: '将',
      options: ['jiāng', 'jiǎng', 'qiāng', 'jiān'],
      correct_answer: 'jiāng',
      word: '将',
      direction: 'hanzi_to_pinyin',
      schema_version: 2,
    },
    pinyin_to_hanzi: {
      prompt: 'jiāng',
      options: ['将', '江', '姜', '疆'],
      correct_answer: '将',
      word: '将',
      direction: 'pinyin_to_hanzi',
      schema_version: 2,
    },
    kanji_to_reading: {
      prompt: '機械',
      options: ['きかい', 'きがい', 'ぎかい', 'きけい'],
      correct_answer: 'きかい',
      word: '機械',
      schema_version: 2,
    },
    reading_to_kanji: {
      prompt: 'きかい',
      options: ['機械', '機会', '奇怪', '器械'],
      correct_answer: '機械',
      word: '機械',
      schema_version: 2,
    },
    tone_id_word: {
      word: '将',
      options: ['4', '1', '2', '3'],
      full_pinyin: 'jiāng',
      toneless_pinyin: 'jiang',
      option_labels: {
        1: 'high level (1)',
        2: 'rising (2)',
        3: 'dipping (3)',
        4: 'falling (4)',
      },
      correct_answer: '1',
      syllable_count: 1,
      schema_version: 2,
    },
    classifier_match: {
      stem: '一___公司',
      word: '公司',
      options: ['座', '家', '间', '处'],
      pronunciation: 'gōng sī',
      correct_answer: '家',
      accepted_answers: ['家'],
      option_readings: { 家: 'jiā', 座: 'zuò', 间: 'jiān', 处: 'chù' },
      semantic_label: 'businesses / institutions / homes',
      schema_version: 2,
    },
    counter_match: {
      stem: '人を一___',
      word: '人',
      options: ['人', '方', '名', '名様'],
      pronunciation: 'ひと',
      correct_answer: '人',
      accepted_answers: ['人'],
      option_readings: { 人: 'にん', 名: 'めい', 方: 'かた', 名様: 'めいさま' },
      schema_version: 2,
    },
    synonym_antonym_match: {
      word: '政府',
      options: ['民众', '国家', '机构', '无政府'],
      relation: 'antonym',
      correct_answer: '无政府',
      nl: { en: { definition: 'the body that governs a state', explanation: 'opposite' } },
      schema_version: 2,
    },
    word_family: {
      stem: 'technical',
      options: ['technicous', 'technical', 'technicment', 'technicive'],
      required_pos: 'adjective',
      correct_answer: 'technical',
      sentence_with_blank: 'Understanding many ___ terms takes time.',
      nl: { en: { explanation: 'the base adjective' } },
      schema_version: 2,
    },
    particle_selection: {
      options: ['から', 'に', 'で', 'を'],
      error_tags: { に: 'source_vs_goal' },
      target_word: '一',
      correct_answer: 'から',
      original_sentence: '一から十まで数えてみましょう。',
      sentence_with_blank: '一___十まで数えてみましょう。',
      nl: { en: { explanation: '起点を表す' } },
      schema_version: 2,
    },
  };

  it.each(Object.keys(FIXTURES))('renders %s as a real item, not raw JSON', (type) => {
    R().dispatch(type, { exercise_type: type }, FIXTURES[type], '');
    expect(card.querySelector('#optionsList')).not.toBeNull();
    expect(card.querySelectorAll('.exercise-option')).toHaveLength(4);
    // renderGeneric's tell: the content dict printed as a JSON blob.
    expect(card.innerHTML).not.toContain('schema_version');
  });

  it.each(Object.keys(FIXTURES))('grades the key correct for %s', (type) => {
    const c = FIXTURES[type];
    R().dispatch(type, { exercise_type: type }, c, '');
    click(c.correct_answer);
    expect(submitted).toEqual([{ ok: true, resp: { selected: c.correct_answer } }]);
  });

  it('shows tone labels but submits the contour value', () => {
    R().dispatch('tone_id_word', { exercise_type: 'tone_id_word' }, FIXTURES.tone_id_word, '');
    expect(card.innerHTML).toContain('high level (1)');
    // The toneless pinyin is shown; the marked pinyin would be the answer.
    expect(card.innerHTML).toContain('jiang');
    expect(card.innerHTML).not.toContain('jiāng');
    click('1');
    expect(submitted[0]).toEqual({ ok: true, resp: { selected: '1' } });
  });

  it('accepts any of a measure word’s accepted_answers', () => {
    const c = {
      ...FIXTURES.classifier_match,
      stem: '一___书',
      word: '书',
      options: ['本', '册', '张', '颗'],
      correct_answer: '本',
      accepted_answers: ['本', '册'],
      option_readings: { 本: 'běn', 册: 'cè' },
    };
    R().dispatch('classifier_match', { exercise_type: 'classifier_match' }, c, '');
    click('册'); // the secondary answer, not correct_answer
    expect(submitted[0].ok).toBe(true);
  });

  it('renders option readings under measure-word options', () => {
    R().dispatch('counter_match', { exercise_type: 'counter_match' }, FIXTURES.counter_match, '');
    expect(card.innerHTML).toContain('にん');
  });

  it('shows the context sentence for a polyphone in the script→sound direction', () => {
    R().dispatch(
      'hanzi_to_pinyin',
      { exercise_type: 'hanzi_to_pinyin' },
      {
        ...FIXTURES.hanzi_to_pinyin,
        prompt: '行',
        word: '行',
        is_polyphonic: true,
        context_sentence: '我们去银行取钱。',
        context_target: '行',
      },
      ''
    );
    expect(card.innerHTML).toContain('银');
  });

  it('blanks the target in the context sentence for the sound→script direction', () => {
    R().dispatch(
      'pinyin_to_hanzi',
      { exercise_type: 'pinyin_to_hanzi' },
      {
        ...FIXTURES.pinyin_to_hanzi,
        prompt: 'háng',
        word: '银行',
        options: ['银行', '银杏', '很行', '艮行'],
        correct_answer: '银行',
        is_polyphonic: true,
        context_sentence: '我们去银行取钱。',
        context_target: '银行',
      },
      ''
    );
    // The key must not appear in the prompt — printing the context sentence
    // intact would hand over the answer.
    const prompt = card.querySelector('.exercise-prompt').innerHTML;
    expect(prompt).not.toContain('银行');
    expect(prompt).toContain('取钱');
  });

  it('drops the context sentence when the target has no literal match', () => {
    R().dispatch(
      'reading_to_kanji',
      { exercise_type: 'reading_to_kanji' },
      {
        prompt: 'いく',
        options: ['行く', '生く', '逝く', '往く'],
        correct_answer: '行く',
        word: '行く',
        is_polyphonic: true,
        // The conjugated 行き has no literal match for the 行く target, so
        // there is no safe place to cut the blank.
        context_sentence: '学校へ行きました。',
        context_target: '行く',
        schema_version: 2,
      },
      ''
    );
    expect(card.querySelector('.exercise-prompt').innerHTML).not.toContain('学校');
  });

  it('uses the flattened nl explanation and required_pos for word_family', () => {
    R().dispatch('word_family', { exercise_type: 'word_family' }, FIXTURES.word_family, '');
    expect(card.innerHTML).toContain('technical');
    expect(card.innerHTML).toContain('adjective');
  });
});
