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

// ---------------------------------------------------------------------------
// renderJumbled — explicit submit, and click-to-return from the answer box
//
// The other DOM-heavy renderers are left to E2E (see the file header), but
// this one earns unit coverage: it used to grade itself the instant the last
// chunk landed, which locked the card at exactly the moment a learner would
// want to fix a word.
// ---------------------------------------------------------------------------

describe('renderJumbled', () => {
  const CONTENT = { chunks: ['I', 'like', 'cake'], correct_ordering: [0, 1, 2] };

  let card;
  let answered;
  let submits;
  let feedback;

  const bank = () => [...card.querySelectorAll('#jsBank .js-chunk')];
  const answer = () => [...card.querySelectorAll('#jsAnswer .js-chunk')];
  const checkBtn = () => card.querySelector('#jsCheckBtn');
  const click = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  // Address chunks by their content index so the test never depends on the
  // bank's shuffle.
  const place = (ci) => click(card.querySelector(`#jsBank .js-chunk[data-chunk="${ci}"]`));
  const placeAll = (order) => order.forEach(place);

  beforeEach(() => {
    card = document.createElement('div');
    document.body.appendChild(card);
    answered = false;
    submits = [];
    feedback = [];
    R().init({
      cardEl: card,
      isAnswered: () => answered,
      setAnswered: (v) => {
        answered = v;
      },
      showFeedback: (ok, expl) => feedback.push([ok, expl]),
      submitAttempt: (ok, resp) => submits.push([ok, resp]),
      nextExercise: () => {},
    });
    R().dispatch('jumbled_sentence', { exercise_type: 'jumbled_sentence' }, CONTENT, '');
  });

  afterEach(() => {
    card.remove();
  });

  it('renders a Check button, disabled until every chunk is placed', () => {
    expect(checkBtn()).not.toBeNull();
    expect(checkBtn().hasAttribute('disabled')).toBe(true);

    place(0);
    place(1);
    expect(checkBtn().hasAttribute('disabled')).toBe(true);

    place(2);
    expect(checkBtn().hasAttribute('disabled')).toBe(false);
  });

  it('does not grade when the final chunk is placed', () => {
    placeAll([0, 1, 2]);
    expect(answer()).toHaveLength(3);
    expect(bank()).toHaveLength(0);
    expect(answered).toBe(false);
    expect(submits).toEqual([]);
  });

  it('grades a correct ordering only once Check is clicked', () => {
    placeAll([0, 1, 2]);
    click(checkBtn());
    expect(answered).toBe(true);
    expect(submits).toEqual([[true, { user_ordering: [0, 1, 2] }]]);
    expect(feedback[0][0]).toBe(true);
  });

  it('grades a wrong ordering and reports the correct one', () => {
    placeAll([2, 1, 0]);
    click(checkBtn());
    expect(submits[0][0]).toBe(false);
    expect(submits[0][1]).toEqual({ user_ordering: [2, 1, 0] });
    expect(feedback[0][1]).toContain('I like cake');
  });

  it('refuses to grade a partial answer whose prefix happens to be right', () => {
    // `[0].every((ci, i) => ci === correctOrder[i])` is true — without the
    // length guard a one-word answer would score as a correct sentence.
    place(0);
    click(checkBtn());
    expect(answered).toBe(false);
    expect(submits).toEqual([]);
  });

  it('returns a placed chunk to the bank when it is clicked', () => {
    place(1);
    expect(answer()).toHaveLength(1);
    expect(bank()).toHaveLength(2);

    click(answer()[0]);
    expect(answer()).toHaveLength(0);
    expect(bank()).toHaveLength(3);
    expect(
      bank()
        .map((el) => el.dataset.chunk)
        .sort()
    ).toEqual(['0', '1', '2']);
  });

  it('removes only the clicked chunk, keeping the rest in order', () => {
    placeAll([0, 1, 2]);
    click(answer()[1]);
    expect(answer().map((el) => el.dataset.chunk)).toEqual(['0', '2']);
  });

  it('marks placed chunks with the removal affordance class', () => {
    place(0);
    expect(answer()[0].classList.contains('js-chunk--placed')).toBe(true);
    expect(bank()[0].classList.contains('js-chunk--placed')).toBe(false);
  });

  it('drops the Check button and freezes the chunks once answered', () => {
    placeAll([0, 1, 2]);
    click(checkBtn());
    expect(checkBtn()).toBeNull();
    expect(answer().every((el) => el.classList.contains('disabled'))).toBe(true);
    expect(answer().every((el) => !el.hasAttribute('draggable'))).toBe(true);

    click(answer()[0]);
    expect(answer()).toHaveLength(3);
    expect(submits).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Escaping of pipeline-authored values (target_word in the instruction, cefr_level badge)
// ---------------------------------------------------------------------------

describe('HTML escaping of exercise content', () => {
  let card;
  const XSS = '<img src=x onerror=1>';

  beforeEach(() => {
    card = document.createElement('div');
    document.body.appendChild(card);
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

  const sd = (target_word) => ({
    target_word,
    sentences: [
      { text: 'A', is_correct: true },
      { text: 'B', is_correct: false },
    ],
    correct_answer: 'A',
    explanation: 'x',
  });

  it('renders a hostile target_word in the instruction as text', () => {
    R().dispatch('semantic_discrimination', { cefr_level: 'A1' }, sd(XSS), '');
    expect(card.querySelector('.exercise-instruction img')).toBeNull();
    expect(card.querySelector('.exercise-instruction').textContent).toContain(XSS);
  });

  it('renders ordinary CJK target_word unchanged', () => {
    R().dispatch('semantic_discrimination', { cefr_level: 'N5' }, sd('食べる'), '');
    expect(card.querySelector('.exercise-instruction').textContent).toContain('食べる');
  });

  it('renders a hostile cefr_level in the type badge as text', () => {
    R().dispatch('semantic_discrimination', { cefr_level: XSS }, sd('word'), '');
    expect(card.querySelector('.exercise-type-badge img')).toBeNull();
    expect(card.querySelector('.exercise-cefr-badge').textContent).toBe(XSS);
  });

  it('renders an ordinary cefr_level unchanged', () => {
    R().dispatch('semantic_discrimination', { cefr_level: 'HSK3' }, sd('word'), '');
    expect(card.querySelector('.exercise-cefr-badge').textContent).toBe('HSK3');
  });
});

// ---------------------------------------------------------------------------
// Spot the error: per-option explanations in the learner's language (ADR-064)
// ---------------------------------------------------------------------------

describe('renderSpotSentence explanations', () => {
  let card;
  let feedback;
  let answered;
  const realFetch = window.authFetch;

  const SENTENCES = [
    { text: '人間は言葉を使う。', is_correct: true },
    { text: '人間は言葉が使う。', is_correct: false, error_description: '助詞の誤り。' },
    { text: '彼は優しい人間だ。', is_correct: true },
  ];
  const ENTRIES = [
    { meaning: 'Humans use language.', explanation: 'を marks the object.', correction: null },
    {
      meaning: 'Humans use language.',
      explanation: 'The object of 使う takes を, not が.',
      correction: '人間は言葉を使う。',
    },
    { meaning: 'He is a kind person.', explanation: '優しい modifies 人間.', correction: null },
  ];

  beforeEach(() => {
    card = document.createElement('div');
    document.body.appendChild(card);
    feedback = [];
    answered = false;
    R().init({
      cardEl: card,
      isAnswered: () => answered,
      setAnswered: (v) => {
        answered = v;
      },
      showFeedback: (ok, expl) => feedback.push({ ok, expl }),
      submitAttempt: () => {},
      nextExercise: () => {},
    });
  });

  afterEach(() => {
    card.remove();
    window.authFetch = realFetch;
  });

  const pick = (i) => {
    const options = card.querySelectorAll('#optionsList .exercise-option');
    options[i].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  };

  it('shows why every option is right or wrong once answered, from attached content', () => {
    window.authFetch = () => {
      throw new Error('must not fetch when explanations are attached');
    };
    R().dispatch(
      'spot_incorrect_sentence',
      { exercise_id: 'e-attached' },
      { sentences: SENTENCES, option_explanations: ENTRIES },
      ''
    );
    expect(card.querySelector('.ex-opt-expl')).toBeNull(); // nothing before answering
    pick(0);
    const notes = card.querySelectorAll('.ex-opt-expl');
    expect(notes.length).toBe(3);
    expect(notes[0].textContent).toContain('Humans use language.');
    expect(notes[0].textContent).toContain('を marks the object.');
    expect(notes[1].classList.contains('ex-opt-expl--bad')).toBe(true);
    expect(notes[1].querySelector('.ex-opt-expl__fix').textContent).toContain('人間は言葉を使う。');
    expect(notes[2].querySelector('.ex-opt-expl__fix')).toBeNull();
    // the wrong sentence's meaning is labelled as literal; the right ones are not
    expect(notes[1].querySelector('.ex-opt-expl__lit').textContent).toBe('Literally:');
    expect(notes[0].querySelector('.ex-opt-expl__lit')).toBeNull();
    // the target-language note is not used when ours is there
    expect(feedback).toEqual([{ ok: false, expl: '' }]);
  });

  it('fetches explanations for an item served without them and shows them after answering', async () => {
    const asked = [];
    let release;
    const gate = new Promise((r) => {
      release = r;
    });
    window.authFetch = async (url) => {
      asked.push(url);
      await gate;
      return { ok: true, json: async () => ({ state: 'ready', option_explanations: ENTRIES }) };
    };
    R().dispatch(
      'spot_incorrect_sentence',
      { exercise_id: 'e-fetch' },
      { sentences: SENTENCES },
      ''
    );
    expect(asked).toEqual(['/api/practice/explanations/e-fetch']); // asked on display
    pick(1);
    // nothing shown twice: no old note in the bar, a loading line under the options
    expect(feedback[0]).toEqual({ ok: true, expl: '' });
    expect(card.querySelector('.ex-opt-expl')).toBeNull();
    expect(card.querySelector('.ex-opt-expl-loading')).not.toBeNull();
    release();
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    expect(card.querySelectorAll('.ex-opt-expl').length).toBe(3);
    expect(card.querySelector('.ex-opt-expl-loading')).toBeNull();
  });

  it("falls back to the item's own note under the wrong sentence when the server has none", async () => {
    window.authFetch = async () => ({ ok: true, json: async () => ({ state: 'unavailable' }) });
    R().dispatch(
      'spot_incorrect_sentence',
      { exercise_id: 'e-none' },
      { sentences: SENTENCES },
      ''
    );
    pick(1);
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    const notes = card.querySelectorAll('.ex-opt-expl');
    expect(notes.length).toBe(1);
    expect(notes[0].textContent).toContain('助詞の誤り。');
    expect(card.querySelector('.ex-opt-expl-loading')).toBeNull();
    expect(feedback[0]).toEqual({ ok: true, expl: '' });
  });

  it('keeps the old note in the feedback bar when explanations cannot be asked for', () => {
    window.authFetch = undefined;
    R().dispatch('spot_incorrect_sentence', {}, { sentences: SENTENCES }, '');
    pick(1);
    expect(feedback[0]).toEqual({ ok: true, expl: '助詞の誤り。' });
    expect(card.querySelector('.ex-opt-expl')).toBeNull();
  });
});

describe('renderSemDiscrim explanations', () => {
  let card;
  let feedback;
  let answered;
  const realFetch = window.authFetch;

  const SENTENCES = [
    { text: 'この回数券は無効になる。', is_correct: true },
    { text: '回数券でピザを半額にした。', is_correct: false, explanation: 'Needs クーポン.' },
    { text: '回数券を毎月更新する。', is_correct: false, explanation: 'Needs 定期券.' },
  ];
  const ENTRIES = [
    { meaning: 'This ticket book expires.', explanation: '回数券 can expire.', correction: null },
    {
      meaning: 'I halved the pizza price.',
      explanation: 'A discount needs クーポン.',
      correction: null,
    },
    { meaning: 'I renew it monthly.', explanation: 'A monthly pass is 定期券.', correction: null },
  ];

  beforeEach(() => {
    card = document.createElement('div');
    document.body.appendChild(card);
    feedback = [];
    answered = false;
    R().init({
      cardEl: card,
      isAnswered: () => answered,
      setAnswered: (v) => {
        answered = v;
      },
      showFeedback: (ok, expl) => feedback.push({ ok, expl }),
      submitAttempt: () => {},
      nextExercise: () => {},
    });
  });

  afterEach(() => {
    card.remove();
    window.authFetch = realFetch;
  });

  const pickText = (text) => {
    const el = card.querySelector(`.exercise-option[data-value="${text}"]`);
    el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  };
  const noteFor = (text) =>
    card.querySelector(`.exercise-option[data-value="${text}"] .ex-opt-expl`);

  it('matches attached explanations to shuffled options by sentence', () => {
    window.authFetch = () => {
      throw new Error('must not fetch when explanations are attached');
    };
    R().dispatch(
      'semantic_discrimination',
      { exercise_id: 's-attached' },
      { target_word: '回数券', sentences: SENTENCES, option_explanations: ENTRIES },
      ''
    );
    pickText(SENTENCES[1].text);
    expect(noteFor(SENTENCES[0].text).textContent).toContain('This ticket book expires.');
    expect(noteFor(SENTENCES[1].text).textContent).toContain('A discount needs クーポン.');
    expect(noteFor(SENTENCES[1].text).querySelector('.ex-opt-expl__verdict').textContent).toBe(
      'Wrong'
    );
    expect(noteFor(SENTENCES[2].text).textContent).toContain('定期券');
    expect(feedback).toEqual([{ ok: false, expl: '' }]);
  });

  it('shows the stored notes first and replaces them when the fetch arrives', async () => {
    let release;
    const gate = new Promise((r) => {
      release = r;
    });
    window.authFetch = async () => {
      await gate;
      return { ok: true, json: async () => ({ state: 'ready', option_explanations: ENTRIES }) };
    };
    R().dispatch(
      'semantic_discrimination',
      { exercise_id: 's-fetch' },
      { target_word: '回数券', sentences: SENTENCES },
      ''
    );
    pickText(SENTENCES[0].text);
    expect(noteFor(SENTENCES[0].text)).toBeNull(); // no stored note on the right one
    expect(noteFor(SENTENCES[1].text).textContent).toContain('Needs クーポン.');
    expect(card.querySelector('.ex-opt-expl-loading')).not.toBeNull();
    release();
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    expect(noteFor(SENTENCES[0].text).textContent).toContain('回数券 can expire.');
    expect(noteFor(SENTENCES[1].text).textContent).toContain('A discount needs クーポン.');
    expect(card.querySelectorAll('.ex-opt-expl').length).toBe(3);
    expect(card.querySelector('.ex-opt-expl-loading')).toBeNull();
  });
});

describe('word-option explanations (particle, word form, synonym / antonym)', () => {
  let card;
  let feedback;
  let answered;
  const realFetch = window.authFetch;

  const PARTICLE = {
    correct_answer: 'が',
    options: ['から', 'を', 'と', 'が'],
    sentence_with_blank: '机の上の時計___、朝七時を知らせた。',
    explanation: '正解。「時計が」で主語を示す。',
  };
  const ENTRIES = [
    { meaning: 'marks a starting point', explanation: 'から marks where something starts.' },
    { meaning: 'marks the direct object', explanation: 'を would make the clock an object.' },
    { meaning: 'joins nouns', explanation: 'と needs a second noun.' },
    { meaning: 'The clock on the desk announced seven.', explanation: 'が marks the subject.' },
  ];

  beforeEach(() => {
    card = document.createElement('div');
    document.body.appendChild(card);
    feedback = [];
    answered = false;
    R().init({
      cardEl: card,
      isAnswered: () => answered,
      setAnswered: (v) => {
        answered = v;
      },
      showFeedback: (ok, expl) => feedback.push({ ok, expl }),
      submitAttempt: () => {},
      nextExercise: () => {},
    });
  });

  afterEach(() => {
    card.remove();
    window.authFetch = realFetch;
  });

  const pickText = (text) => {
    const el = card.querySelector(`.exercise-option[data-value="${text}"]`);
    el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  };
  const noteFor = (text) =>
    card.querySelector(`.exercise-option[data-value="${text}"] .ex-opt-expl`);

  it("shows every particle option explained; a wrong one's meaning is a plain gloss", () => {
    window.authFetch = () => {
      throw new Error('must not fetch when explanations are attached');
    };
    R().dispatch(
      'particle_selection',
      { exercise_id: 'p-attached' },
      { ...PARTICLE, option_explanations: ENTRIES },
      ''
    );
    pickText('を');
    expect(card.querySelectorAll('.ex-opt-expl').length).toBe(4);
    const wrong = noteFor('を');
    expect(wrong.querySelector('.ex-opt-expl__verdict').textContent).toBe('Wrong');
    expect(wrong.querySelector('.ex-opt-expl__meaning').textContent).toBe(
      'marks the direct object'
    );
    expect(wrong.querySelector('.ex-opt-expl__lit')).toBeNull();
    const right = noteFor('が');
    expect(right.querySelector('.ex-opt-expl__verdict').textContent).toBe('Correct');
    expect(right.querySelector('.ex-opt-expl__meaning').textContent).toBe(
      '“The clock on the desk announced seven.”'
    );
    expect(feedback).toEqual([{ ok: false, expl: '' }]); // the Japanese note is not repeated
  });

  it('fetches explanations for a word-form item served without them', async () => {
    const asked = [];
    window.authFetch = async (url) => {
      asked.push(url);
      return {
        ok: true,
        json: async () => ({
          state: 'ready',
          option_explanations: [
            { meaning: 'past form', explanation: 'くれた needs the te-form.' },
            { meaning: 'He treated it fairly for us.', explanation: 'て joins くれた.' },
          ],
        }),
      };
    };
    R().dispatch(
      'morphology_slot',
      { exercise_id: 'm-fetch' },
      {
        base_form: '扱う',
        correct_answer: '扱って',
        options: ['扱った', '扱って'],
        sentence_with_blank: '公平に___くれた。',
        explanation: 'て形。',
      },
      ''
    );
    expect(asked).toEqual(['/api/practice/explanations/m-fetch']);
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    pickText('扱って');
    expect(noteFor('扱った').textContent).toContain('past form');
    expect(noteFor('扱って').textContent).toContain('“He treated it fairly for us.”');
    expect(feedback).toEqual([{ ok: true, expl: '' }]);
  });

  it('gives every synonym / antonym option a plain gloss', () => {
    R().dispatch(
      'synonym_antonym_match',
      { exercise_id: 'r-attached' },
      {
        word: '国内',
        relation: 'antonym',
        correct_answer: '海外',
        options: ['海外', '城下'],
        option_explanations: [
          { meaning: 'かいがい — overseas', explanation: '海外 is outside the country.' },
          { meaning: 'じょうか — castle town', explanation: 'Unrelated to 国内.' },
        ],
      },
      ''
    );
    pickText('海外');
    expect(noteFor('海外').querySelector('.ex-opt-expl__meaning').textContent).toBe(
      'かいがい — overseas'
    );
    expect(noteFor('城下').querySelector('.ex-opt-expl__meaning').textContent).toBe(
      'じょうか — castle town'
    );
  });

  it("keeps the item's own note in the bar when explanations cannot be asked for", () => {
    window.authFetch = undefined;
    R().dispatch('particle_selection', { exercise_id: 'p-offline' }, { ...PARTICLE }, '');
    pickText('が');
    expect(feedback).toEqual([{ ok: true, expl: '正解。「時計が」で主語を示す。' }]);
    expect(card.querySelector('.ex-opt-expl')).toBeNull();
  });

  it("shows the item's own note under the key when the fetch brings nothing", async () => {
    window.authFetch = async () => ({ ok: false });
    R().dispatch('particle_selection', { exercise_id: 'p-none' }, { ...PARTICLE }, '');
    pickText('を');
    expect(feedback).toEqual([{ ok: false, expl: '' }]);
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    expect(noteFor('が').textContent).toContain('正解。「時計が」で主語を示す。');
    expect(card.querySelectorAll('.ex-opt-expl').length).toBe(1);
  });

  it('a fetch that lands after the learner moved on does not paint the next item', async () => {
    let release;
    const gate = new Promise((r) => {
      release = r;
    });
    window.authFetch = async (url) => {
      if (!url.endsWith('/p-A')) return new Promise(() => {}); // B still loading
      await gate;
      return { ok: true, json: async () => ({ state: 'ready', option_explanations: ENTRIES }) };
    };
    R().dispatch('particle_selection', { exercise_id: 'p-A' }, { ...PARTICLE }, '');
    pickText('を');
    answered = false; // Next: item B, same particles in another order, not yet answered
    R().dispatch(
      'particle_selection',
      { exercise_id: 'p-B' },
      { ...PARTICLE, correct_answer: 'を', options: ['が', 'を', 'と', 'から'] },
      ''
    );
    release();
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    expect(card.querySelectorAll('.ex-opt-expl').length).toBe(0);
  });

  it('matches options whose stored text has surrounding spaces', () => {
    R().dispatch(
      'morphology_slot',
      { exercise_id: 'm-spaces' },
      {
        base_form: '扱う',
        correct_answer: '扱って ',
        options: [' 扱った', '扱って '],
        sentence_with_blank: '公平に___くれた。',
        option_explanations: [
          { meaning: 'past form', explanation: 'くれた needs the te-form.' },
          { meaning: 'He treated it fairly for us.', explanation: 'て joins くれた.' },
        ],
      },
      ''
    );
    pickText('扱って ');
    expect(card.querySelectorAll('.ex-opt-expl').length).toBe(2);
  });

  it('does not ask for an item with duplicate options', () => {
    const asked = [];
    window.authFetch = async (url) => {
      asked.push(url);
      return { ok: false };
    };
    R().dispatch(
      'particle_selection',
      { exercise_id: 'p-dupes' },
      { ...PARTICLE, options: ['が', 'が', 'を'] },
      ''
    );
    expect(asked).toEqual([]);
  });
});

describe('explanation loading line', () => {
  it('is not shown when the fetch already came back empty before the answer', async () => {
    const card = document.createElement('div');
    document.body.appendChild(card);
    let answered = false;
    R().init({
      cardEl: card,
      isAnswered: () => answered,
      setAnswered: (v) => {
        answered = v;
      },
      showFeedback: () => {},
      submitAttempt: () => {},
      nextExercise: () => {},
    });
    const realFetch = window.authFetch;
    window.authFetch = async () => ({ ok: true, json: async () => ({ state: 'unavailable' }) });
    R().dispatch(
      'spot_incorrect_sentence',
      { exercise_id: 'e-early' },
      {
        sentences: [
          { text: 'A。', is_correct: true },
          { text: 'B。', is_correct: false },
        ],
      },
      ''
    );
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    card
      .querySelectorAll('#optionsList .exercise-option')[1]
      .dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    expect(card.querySelector('.ex-opt-expl-loading')).toBeNull();
    window.authFetch = realFetch;
    card.remove();
  });
});
