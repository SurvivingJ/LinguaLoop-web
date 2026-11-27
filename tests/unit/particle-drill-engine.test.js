/**
 * static/js/particles/*: the particle drill's engine (no DOM).
 * Markup parsing, typed-answer matching, the ladder rules, exercise building
 * and the conjugation tables behind the conjugation gym.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expand, parse, plain, toHtml } from '../../static/js/particles/markup.js';
import { answerMatches, normalizeAnswer, romajiToKana } from '../../static/js/particles/kana.js';
import * as M from '../../static/js/particles/mastery.js';
import * as N from '../../static/js/particles/numbers.js';
import {
  Deck,
  build,
  fromPack,
  gradeChoice,
  gradeFill,
  gradeFixTap,
  gradeTyped,
  packSize,
  parsed,
} from '../../static/js/particles/exercises.js';
import {
  ADJ_FORMS,
  VERB_FORMS,
  acceptedAnswers,
  conjugate,
  distractors,
  formsFor,
} from '../../static/js/particles/conjugate.js';

const ITEM = {
  id: 'a1',
  jp: '私[わたし]{は|wa-topic}毎朝[まいあさ]七時[しちじ]{に|ni-time}駅[えき]{に/へ|ni-destination}行[い]きます。',
  en: 'I go to the station at seven every morning.',
  f: 1,
  d: ['で', 'を', 'が'],
  why: 'A clock time takes に.',
  lv: 5,
};
const seeded = (seed = 1) => {
  let x = seed;
  return () => {
    x = (x * 16807) % 2147483647;
    return (x - 1) / 2147483646;
  };
};

describe('markup', () => {
  it('parses furigana, slots and alternatives', () => {
    const { segs, slots } = parse(ITEM.jp);
    expect(slots).toMatchObject([
      { a: 'は', alt: [], skill: 'wa-topic' },
      { a: 'に', alt: [], skill: 'ni-time' },
      { a: 'に', alt: ['へ'], skill: 'ni-destination' },
    ]);
    expect(segs[0]).toEqual({ t: '私', r: 'わたし' });
    expect(segs[1]).toEqual({ slot: 0 });
    expect(plain(ITEM.jp)).toBe('私は毎朝七時に駅に行きます。');
    expect(plain(ITEM.jp, () => '＿')).toBe('私＿毎朝七時＿駅＿行きます。');
  });

  it('matches the Python parser on the shared cases', () => {
    const cases = JSON.parse(
      readFileSync(join(process.cwd(), 'tests/fixtures/particle_drill/markup_cases.json'), 'utf-8')
    );
    for (const c of cases) {
      const { slots } = parse(c.jp);
      expect(plain(c.jp)).toBe(c.plain);
      expect(slots.map((s) => [s.a, s.alt, s.skill])).toEqual(c.slots);
    }
  });

  it('renders ruby and escapes text', () => {
    const html = toHtml(parse('本[ほん]{を|o-object}A&B'), (slot) => `[${slot.a}]`);
    expect(html).toBe('<ruby>本<rt>ほん</rt></ruby>[を]A&amp;B');
  });

  it('expands pack variables', () => {
    expect(expand('<who>{は|wa-topic}<act>。', { who: '母[はは]', act: '寝[ね]ました' })).toBe(
      '母[はは]{は|wa-topic}寝[ね]ました。'
    );
  });
});

describe('typed answers', () => {
  it.each([
    ['wa', 'わ'],
    ['made', 'まで'],
    ['madeni', 'までに'],
    ['shika', 'しか'],
    ['tte', 'って'],
    ['kitte', 'きって'],
    ['onna', 'おんな'],
    ['shinbun', 'しんぶん'],
    ["kon'ya", 'こんや'],
    ['matcha', 'まっちゃ'],
    ['kyou', 'きょう'],
    ['nitsuite', 'について'],
    ['ja', 'じゃ'],
    ['じゃない', 'じゃない'],
  ])('romaji %s -> %s', (romaji, kana) => {
    expect(romajiToKana(romaji)).toBe(kana);
  });

  it('keeps an unfinished syllable while typing', () => {
    expect(romajiToKana('n', false)).toBe('n');
    expect(romajiToKana('k', false)).toBe('k');
    expect(romajiToKana('n', true)).toBe('ん');
  });

  it('accepts the particle by sound, by kana and in katakana', () => {
    expect(answerMatches(['は'], 'wa')).toBe(true);
    expect(answerMatches(['は'], 'ha')).toBe(true);
    expect(answerMatches(['は'], 'わ')).toBe(true);
    expect(answerMatches(['を'], 'o')).toBe(true);
    expect(answerMatches(['へ'], 'e')).toBe(true);
    expect(answerMatches(['までに'], 'マデニ')).toBe(true);
    expect(answerMatches(['に', 'へ'], 'he')).toBe(true);
    expect(answerMatches(['に'], 'de')).toBe(false);
    expect(answerMatches(['に'], '')).toBe(false);
    expect(normalizeAnswer(' Ni 。')).toBe('に');
  });

  it('accepts a conjugated form in kana, kanji or romaji', () => {
    const ok = ['書いて', 'かいて'];
    expect(answerMatches(ok, '書いて')).toBe(true);
    expect(answerMatches(ok, 'かいて')).toBe(true);
    expect(answerMatches(ok, 'kaite')).toBe(true);
    expect(answerMatches(ok, 'kakite')).toBe(false);
  });
});

describe('ladder', () => {
  const answer = (state, correct, extra = {}) =>
    M.record(state, { correct, ms: 1200, level: state.l, itemId: 'x', ...extra }, 1000);

  it('promotes after five answers at 80% and restarts the count', () => {
    let s = M.newState();
    let event = null;
    for (let i = 0; i < 5; i++) ({ state: s, event } = answer(s, true));
    expect(event).toBe('promoted');
    expect(s.l).toBe(2);
    expect(s.la).toBe(0);
    ({ state: s, event } = answer(s, true));
    expect(event).toBe(null);
    expect(s.l).toBe(2);
  });

  it('does not promote on a wrong answer or below the bar', () => {
    let s = M.newState();
    for (const correct of [true, false, true, false, true, false])
      ({ state: s } = answer(s, correct));
    expect(s.l).toBe(1);
    expect(s.e).toBeLessThan(M.PROMOTE_AT);
  });

  it('demotes one rung after sustained misses and never below 1', () => {
    let s = { ...M.newState(), l: 3, e: 0.8 };
    let event = null;
    for (let i = 0; i < 6 && event !== 'demoted'; i++) ({ state: s, event } = answer(s, false));
    expect(event).toBe('demoted');
    expect(s.l).toBe(2);
    let low = M.newState();
    for (let i = 0; i < 8; i++) ({ state: low } = answer(low, false));
    expect(low.l).toBe(1);
  });

  it('ignores the ladder for answers in a manually chosen mode', () => {
    let s = M.newState();
    for (let i = 0; i < 9; i++) ({ state: s } = answer(s, true, { counts: false }));
    expect(s.l).toBe(1);
    expect(s.n).toBe(9);
    expect(s.c).toBe(9);
  });

  it('ignores answers drawn at another level', () => {
    let s = { ...M.newState(), l: 3 };
    for (let i = 0; i < 9; i++) ({ state: s } = M.record(s, { correct: true, level: 1 }, 1000));
    expect(s.l).toBe(3);
  });

  it('needs eight answers at Speed, then schedules a review a day out', () => {
    let s = { ...M.newState(), l: M.MAX_LEVEL, e: 0.9 };
    let event = null;
    for (let i = 0; i < 7; i++) ({ state: s, event } = answer(s, true));
    expect(s.l).toBe(M.MAX_LEVEL);
    ({ state: s, event } = answer(s, true));
    expect(event).toBe('mastered');
    expect(M.isMastered(s)).toBe(true);
    expect(s.due).toBe(1000 + 86400000);
    expect(M.isDue(s, 1000)).toBe(false);
    expect(M.isDue(s, 1000 + 86400000)).toBe(true);
  });

  it('does not leave Speed on accuracy alone: the answers must be fast', () => {
    let s = { ...M.newState(), l: M.MAX_LEVEL, e: 0.9 };
    for (let i = 0; i < 12; i++) ({ state: s } = answer(s, true, { ms: 5500 }));
    expect(s.l).toBe(M.MAX_LEVEL);
    expect(s.rt).toBeGreaterThan(M.SPEED_RT_MS);
    let event = null;
    for (let i = 0; i < 12 && event !== 'mastered'; i++)
      ({ state: s, event } = answer(s, true, { ms: 1500 }));
    expect(event).toBe('mastered');
  });

  it('lengthens the interval after a passed review and drops back after a failed one', () => {
    const due = 5000;
    let s = { ...M.newState(), l: M.MASTERED, e: 0.95, due, iv: 0 };
    let event = null;
    for (let i = 0; i < M.REVIEW_ANSWERS; i++)
      ({ state: s, event } = M.record(s, { correct: true, level: 6 }, due + 1));
    expect(event).toBe('reviewed');
    expect(s.iv).toBe(1);
    expect(s.due).toBe(due + 1 + M.REVIEW_DAYS[1] * 86400000);

    let f = { ...M.newState(), l: M.MASTERED, e: 0.7, due, iv: 2 };
    ({ state: f, event } = M.record(f, { correct: false, level: 6 }, due + 1));
    ({ state: f, event } = M.record(f, { correct: false, level: 6 }, due + 2));
    expect(f.l).toBe(M.MAX_LEVEL - 1);
    expect(f.due).toBe(null);
  });

  it('keeps missed items first in line and forgets them once answered right', () => {
    let s = M.newState();
    ({ state: s } = M.record(s, { correct: false, level: 1, itemId: 'a' }, 1));
    ({ state: s } = M.record(s, { correct: false, level: 1, itemId: 'b' }, 2));
    expect(s.miss).toEqual(['b', 'a']);
    ({ state: s } = M.record(s, { correct: true, level: 1, itemId: 'a' }, 3));
    expect(s.miss).toEqual(['b']);
  });

  it('supports a shorter ladder (conjugation: three rungs)', () => {
    let s = { ...M.newState(), l: 3, e: 0.9 };
    let event = null;
    for (let i = 0; i < 8; i++)
      ({ state: s, event } = M.record(s, { correct: true, level: 3, ms: 1000 }, 10, 3));
    expect(event).toBe('mastered');
    expect(M.isMastered(s, 3)).toBe(true);
    expect(M.progress(s, 3)).toBe(1);
  });

  it('lowers the exercise type to what the item supports', () => {
    const one = { slotCount: 1, d: ['で'] };
    const many = { slotCount: 3, d: ['で'] };
    expect(M.modeFor(1, many)).toBe('meet');
    expect(M.modeFor(2, many)).toBe('choose');
    expect(M.modeFor(3, many)).toBe('type');
    expect(M.modeFor(4, many)).toBe('fill');
    expect(M.modeFor(4, one)).toBe('type');
    expect(M.modeFor(5, many)).toBe('fix');
    expect(M.modeFor(6, many)).toBe('speed');
    expect(M.modeFor(2, { slotCount: 1, d: [] })).toBe('type');
  });

  it('plans a mix: due reviews, weakest in-progress skills, then one new skill', () => {
    const skills = ['a', 'b', 'c', 'd', 'e'].map((id) => ({ id, items: 10, packs: 0 }));
    skills.push({ id: 'empty', items: 0, packs: 0 });
    const states = {
      a: { ...M.newState(), l: M.MASTERED, n: 40, due: 10, last: 1 },
      b: { ...M.newState(), l: 2, n: 8, e: 0.9, last: 2 },
      c: { ...M.newState(), l: 2, n: 8, e: 0.4, last: 3 },
    };
    const plan = M.planMix(skills, states, { now: 100, size: 6, fresh: 1 }).map((k) => k.id);
    // (pickCompanions is covered in its own block below)
    expect(plan).toEqual(['a', 'c', 'b', 'd']);
    expect(M.nextUp(skills, states).id).toBe('b');
  });

  it('merges two progress documents by the entry with more answers', () => {
    const a = {
      skills: { x: { n: 5, last: 9 }, y: { n: 2, last: 1 } },
      conj: {},
      settings: { furi: false },
    };
    const b = {
      skills: { x: { n: 3, last: 99 }, z: { n: 1, last: 1 } },
      conj: { te: { n: 4 } },
      settings: { furi: true, mode: 'type' },
    };
    const m = M.mergeProgress(a, b);
    expect(m.skills.x.n).toBe(5);
    expect(Object.keys(m.skills).sort()).toEqual(['x', 'y', 'z']);
    expect(m.conj.te.n).toBe(4);
    expect(m.settings).toEqual({ furi: false, mode: 'type' });
  });
});

describe('exercises', () => {
  it('builds a choose exercise with the answer among the options', () => {
    const ex = build({ ...ITEM }, 'choose', seeded(3));
    expect(ex.focus).toBe(1);
    expect(ex.options).toHaveLength(4);
    expect(ex.options).toContain('に');
    expect(gradeChoice(ex, 'に')).toBe(true);
    expect(gradeChoice(ex, 'で')).toBe(false);
    expect(build({ ...ITEM }, 'meet', seeded(3)).options).toHaveLength(3);
  });

  it('accepts alternatives of the focus slot', () => {
    const ex = build({ ...ITEM, f: 2 }, 'type');
    expect(gradeTyped(ex, 'ni')).toBe(true);
    expect(gradeTyped(ex, 'へ')).toBe(true);
    expect(gradeTyped(ex, 'e')).toBe(true);
    expect(gradeTyped(ex, 'de')).toBe(false);
  });

  it('fill: every slot is graded and alternatives count', () => {
    const ex = build({ ...ITEM }, 'fill', seeded(5));
    expect(ex.bank).toEqual(expect.arrayContaining(['は', 'に']));
    expect(ex.bank.filter((c) => c === 'に')).toHaveLength(2);
    expect(gradeFill(ex, ['は', 'に', 'へ'])).toEqual({
      perSlot: [true, true, true],
      correct: true,
    });
    expect(gradeFill(ex, ['が', 'に', 'に'])).toEqual({
      perSlot: [false, true, true],
      correct: false,
    });
  });

  it('fix: only the focus slot shows a wrong particle', () => {
    const ex = build({ ...ITEM }, 'fix', seeded(7));
    expect(ITEM.d).toContain(ex.wrong);
    expect(ex.shown[0]).toBe('は');
    expect(ex.shown[1]).toBe(ex.wrong);
    expect(ex.shown[2]).toBe('に');
    expect(gradeFixTap(ex, 1)).toBe(true);
    expect(gradeFixTap(ex, 0)).toBe(false);
    expect(ex.options).toContain('に');
    expect(ex.options).not.toContain(ex.wrong);
  });

  it('draws compound particles in kanji and accepts their reading when typed', () => {
    const item = {
      id: 'k1',
      jp: '親[おや]{に対[たい]して|nitaishite}失礼[しつれい]だ。',
      en: 'That is rude to your parents.',
      f: 0,
      d: ['に関[かん]して', 'にとって', 'として'],
      why: 'に対して marks the target of an attitude.',
      lv: 3,
    };
    const ex = build(item, 'choose', seeded(3));
    expect(ex.answer).toBe('に対して');
    expect(ex.options.sort()).toEqual(['として', 'にとって', 'に対して', 'に関して'].sort());
    expect(ex.ruby['に関して']).toBe('に関[かん]して');
    expect(ex.ruby['に対して']).toBe('に対[たい]して');
    expect(gradeChoice(ex, 'に対して')).toBe(true);
    expect(gradeChoice(ex, 'に関して')).toBe(false);
    const typed = build(item, 'type');
    expect(gradeTyped(typed, 'に対して')).toBe(true);
    expect(gradeTyped(typed, 'にたいして')).toBe(true);
    expect(gradeTyped(typed, 'nitaishite')).toBe(true);
    expect(gradeTyped(typed, 'nikanshite')).toBe(false);
    expect(build(item, 'fix', seeded(2)).shown[0]).not.toBe('に対して');
  });

  const PACK = {
    id: 'de-place-1',
    lv: 5,
    tpl: '<who>{は|wa-topic}<place>{で|de-place}<act>。',
    en: '<who> <act> at <place>.',
    f: 1,
    d: ['に', 'を', 'が'],
    why: 'The place of an action takes で.',
    vars: {
      who: [
        ['母[はは]', 'my mother'],
        ['田中[たなか]さん', 'Mr. Tanaka'],
      ],
      place: [
        ['家[いえ]', 'home'],
        ['図書館[としょかん]', 'the library'],
      ],
      act: [
        ['本[ほん]{を|o-object}読[よ]みました', 'read a book'],
        ['寝[ね]ました', 'slept'],
      ],
    },
  };

  it('generates items from a pack with the focus slot intact', () => {
    expect(packSize(PACK)).toBe(8);
    const rng = seeded(11);
    for (let i = 0; i < 20; i++) {
      const item = fromPack(PACK, rng);
      const p = parsed(item);
      expect(p.slots[item.f].a).toBe('で');
      expect(item.id.startsWith('pack:de-place-1:')).toBe(true);
      expect(item.en).toMatch(
        /^(My mother|Mr\. Tanaka) (read a book|slept) at (home|the library)\.$/
      );
      expect(plain(item.jp)).not.toMatch(/[<>{}[\]]/);
    }
  });

  it('a deck serves missed items first, avoids quick repeats and never runs dry', () => {
    const items = Array.from({ length: 30 }, (_, i) => ({ ...ITEM, id: `i${i}` }));
    const deck = new Deck({ items, packs: [], missed: ['i7', 'i3'], rng: seeded(2) });
    expect(deck.next().id).toBe('i7');
    expect(deck.next().id).toBe('i3');
    const seen = [];
    for (let i = 0; i < 100; i++) seen.push(deck.next().id);
    for (let i = 12; i < seen.length; i++) expect(seen.slice(i - 12, i)).not.toContain(seen[i]);
    expect(new Set(seen).size).toBe(30);
    const endless = new Deck({ items: [], packs: [PACK], rng: seeded(4) });
    for (let i = 0; i < 50; i++) expect(endless.next().generated).toBe(true);
    expect(new Deck({}).next()).toBe(null);
  });
});

describe('conjugation', () => {
  const TABLE = JSON.parse(
    readFileSync(
      join(process.cwd(), 'tests/fixtures/particle_drill/conjugation_cases.json'),
      'utf-8'
    )
  );

  it.each(TABLE)('$d ($c) $form -> $kana', ({ d, k, c, form, kanji, kana }) => {
    const got = conjugate({ d, k, c }, form);
    expect(got.kana[0]).toBe(kana);
    expect(got.kanji[0]).toBe(kanji);
  });

  it('covers every form in the fixture table', () => {
    const forms = new Set(TABLE.map((r) => r.form));
    for (const f of [...VERB_FORMS, ...ADJ_FORMS]) expect(forms.has(f.id)).toBe(true);
  });

  it('accepts the ら-less potential and the long causative-passive', () => {
    expect(acceptedAnswers({ d: '食べる', k: 'たべる', c: 'ichidan' }, 'potential')).toEqual(
      expect.arrayContaining(['食べられる', '食べれる', 'たべられる'])
    );
    expect(acceptedAnswers({ d: '待つ', k: 'まつ', c: 'godan' }, 'causative_passive')).toEqual(
      expect.arrayContaining(['待たされる', '待たせられる'])
    );
    expect(
      acceptedAnswers({ d: '話す', k: 'はなす', c: 'godan' }, 'causative_passive')
    ).not.toContain('話さされる');
  });

  it('asks stative verbs only for their basic forms', () => {
    expect(formsFor({ d: 'ある', k: 'ある', c: 'godan' })).not.toContain('potential');
    expect(formsFor({ d: '分かる', k: 'わかる', c: 'godan' })).not.toContain('imperative');
    expect(formsFor({ d: '書く', k: 'かく', c: 'godan' })).toContain('causative_passive');
    expect(formsFor({ d: '高い', k: 'たかい', c: 'i' })).toEqual(ADJ_FORMS.map((f) => f.id));
  });

  it('offers three wrong answers that are never an accepted form', () => {
    const words = [
      { d: '帰る', k: 'かえる', c: 'godan' },
      { d: '見る', k: 'みる', c: 'ichidan' },
      { d: '勉強する', k: 'べんきょうする', c: 'suru' },
      { d: '来る', k: 'くる', c: 'kuru' },
      { d: '高い', k: 'たかい', c: 'i' },
      { d: '静か', k: 'しずか', c: 'na' },
    ];
    for (const w of words) {
      for (const form of formsFor(w)) {
        const wrong = distractors(w, form, 3, seeded(9));
        const right = acceptedAnswers(w, form);
        expect(wrong).toHaveLength(3);
        expect(new Set(wrong).size).toBe(3);
        for (const x of wrong) expect(right).not.toContain(x);
      }
    }
  });

  it('puts the wrong-group form first: the mistake learners make', () => {
    expect(distractors({ d: '帰る', k: 'かえる', c: 'godan' }, 'nai', 3, seeded(1))[0]).toBe(
      '帰ない'
    );
    expect(distractors({ d: '見る', k: 'みる', c: 'ichidan' }, 'te', 3, seeded(1))[0]).toBe(
      '見って'
    );
  });
});

describe('interleaving: companions of a one-skill drill', () => {
  const sk = (id, p, conf = [], items = 10) => ({ id, p, group: p, conf, items, packs: 0 });
  const skills = [
    sk('wa', 'は', ['が', 'を']),
    sk('ga', 'が', ['は', 'を']),
    sk('wo', 'を', ['が', 'に']),
    sk('ni-time', 'に', ['で', 'を']),
    sk('ni-place', 'に', ['で', 'へ']),
    sk('de', 'で', ['に', 'を']),
    sk('empty', 'へ', ['に'], 0),
  ];
  const started = { ...M.newState(), l: 3, n: 12, last: 50 };
  const ids = (states, focus, opts) =>
    M.pickCompanions(skills, states, focus, { now: 100, ...opts }).map((k) => k.id);

  it('the first skill of a new learner has nothing to mix with', () => {
    expect(ids({}, 'wa')).toEqual([]);
  });
  it('earlier confusers join even before they are started', () => {
    expect(ids({}, 'wo')).toEqual(['ga']);
    expect(ids({}, 'de')).toEqual(['ni-place', 'wo', 'ni-time']);
  });
  it('started skills join; confusers come first', () => {
    expect(ids({ de: started, wa: started }, 'ga')).toEqual(['wa', 'de']);
  });
  it('never the same particle as the focus, never a skill without content', () => {
    const all = Object.fromEntries(skills.map((k) => [k.id, started]));
    const got = ids(all, 'ni-time');
    expect(got).not.toContain('ni-place');
    expect(got).not.toContain('empty');
    expect(got).not.toContain('ni-time');
  });
  it('spreads over particles before repeating one, and respects the size', () => {
    const all = Object.fromEntries(skills.map((k) => [k.id, started]));
    expect(ids(all, 'wa', { size: 3 })).toEqual(['ga', 'wo', 'ni-time']);
    expect(ids(all, 'nope')).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Grammar course: the two kanji question kinds
// ---------------------------------------------------------------------------
describe('kanji skills: reading and writing', () => {
  const reading = () => ({
    jp: '{今朝[けさ]|ym-n5-time}は早[はや]く起[お]きました。',
    f: 0,
    d: ['こんあさ', 'いまあさ', 'こんちょう'],
    ask: 'reading',
  });
  const writing = () => ({
    jp: '友達[ともだち]を{待[ま]って|nt-n5}います。',
    f: 0,
    d: ['持[ま]って', '特[ま]って', '侍[ま]って'],
    ask: 'kanji',
  });

  it('a reading skill shows the word and asks for its reading', () => {
    const ex = build(reading(), 'choose', () => 0.3);
    expect(ex.cue).toBe('今朝');
    expect(ex.answer).toBe('けさ');
    expect(ex.bare).toBe(true);
    expect(ex.options.slice().sort()).toEqual(
      ['いまあさ', 'けさ', 'こんあさ', 'こんちょう'].sort()
    );
    expect(gradeChoice(ex, 'けさ')).toBe(true);
    expect(gradeChoice(ex, 'こんあさ')).toBe(false);
    // after the answer the reading is drawn over its kanji
    expect(ex.ruby['けさ']).toBe('今朝[けさ]');
    const typed = build(reading(), 'type');
    expect(gradeTyped(typed, 'kesa')).toBe(true);
    expect(gradeTyped(typed, 'けさ')).toBe(true);
    expect(gradeTyped(typed, 'こんあさ')).toBe(false);
  });

  it('a writing skill shows the reading and offers bare written forms', () => {
    const ex = build(writing(), 'choose', () => 0.3);
    expect(ex.cue).toBe('まって');
    expect(ex.bare).toBe(true);
    expect(ex.options.slice().sort()).toEqual(['侍って', '待って', '持って', '特って'].sort());
    expect(gradeChoice(ex, '待って')).toBe(true);
    expect(gradeChoice(ex, '持って')).toBe(false);
  });

  it('their ladders skip what cannot be asked', () => {
    const r = reading();
    const w = writing();
    expect([1, 2, 3, 4, 5, 6].map((l) => M.modeFor(l, r))).toEqual([
      'meet',
      'choose',
      'type',
      'type',
      'speed',
      'speed',
    ]);
    expect([1, 2, 3, 4, 5, 6].map((l) => M.modeFor(l, w))).toEqual([
      'meet',
      'choose',
      'choose',
      'choose',
      'speed',
      'speed',
    ]);
  });

  it('skills of the same group are companions before they are started', () => {
    const sk = (id, p, group) => ({ id, p, group, conf: [], items: 10, packs: 0 });
    const skills = [
      sk('a', 'てもいい', 'g1'),
      sk('b', 'てはいけない', 'g1'),
      sk('c', 'たい', 'g2'),
      sk('d', 'なくてもいい', 'g1'),
    ];
    expect(M.pickCompanions(skills, {}, 'd').map((k) => k.id)).toEqual(['b', 'a']);
    expect(M.pickCompanions(skills, {}, 'c')).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Reading drill: numbers, prices, times, dates, durations, ages
// ---------------------------------------------------------------------------
describe('number readings', () => {
  it.each([
    [1, 'いち'],
    [10, 'じゅう'],
    [14, 'じゅうよん'],
    [20, 'にじゅう'],
    [99, 'きゅうじゅうきゅう'],
    [100, 'ひゃく'],
    [101, 'ひゃくいち'],
    [300, 'さんびゃく'],
    [600, 'ろっぴゃく'],
    [800, 'はっぴゃく'],
    [400, 'よんひゃく'],
    [700, 'ななひゃく'],
    [900, 'きゅうひゃく'],
    [365, 'さんびゃくろくじゅうご'],
    [1000, 'せん'],
    [3000, 'さんぜん'],
    [8000, 'はっせん'],
    [4000, 'よんせん'],
    [1900, 'せんきゅうひゃく'],
    [10000, 'いちまん'],
    [35000, 'さんまんごせん'],
    [100000, 'じゅうまん'],
    [1000000, 'ひゃくまん'],
    [3600, 'さんぜんろっぴゃく'],
    [18800, 'いちまんはっせんはっぴゃく'],
    [10000000, 'いっせんまん'],
    [30000000, 'さんぜんまん'],
    [12345678, 'いっせんにひゃくさんじゅうよんまんごせんろっぴゃくななじゅうはち'],
  ])('%i is %s', (n, want) => {
    expect(N.readNumber(n)).toBe(want);
  });

  it('accepts the other endings of 4, 7 and 9', () => {
    expect(N.numberReadings(14)).toEqual(['じゅうよん', 'じゅうし']);
    expect(N.numberReadings(17)).toContain('じゅうしち');
    expect(N.numberReadings(19)).toContain('じゅうく');
    expect(N.numberReadings(21000)).toEqual(['にまんせん', 'にまんいっせん']);
    expect(N.numberReadings(10000000)).toContain('せんまん');
  });

  it.each([
    [1, 'いちじ'],
    [4, 'よじ'],
    [7, 'しちじ'],
    [9, 'くじ'],
    [10, 'じゅうじ'],
    [11, 'じゅういちじ'],
    [12, 'じゅうにじ'],
  ])('%i時 is %s', (h, want) => {
    expect(N.hourReadings(h)[0]).toBe(want);
  });

  it.each([
    [1, 'いっぷん'],
    [2, 'にふん'],
    [3, 'さんぷん'],
    [4, 'よんぷん'],
    [5, 'ごふん'],
    [6, 'ろっぷん'],
    [7, 'ななふん'],
    [8, 'はっぷん'],
    [9, 'きゅうふん'],
    [10, 'じゅっぷん'],
    [11, 'じゅういっぷん'],
    [15, 'じゅうごふん'],
    [20, 'にじゅっぷん'],
    [30, 'さんじゅっぷん'],
    [36, 'さんじゅうろっぷん'],
    [45, 'よんじゅうごふん'],
    [58, 'ごじゅうはっぷん'],
  ])('%i分 is %s', (m, want) => {
    expect(N.minuteReadings(m)[0]).toBe(want);
  });

  it('minutes accept じっぷん and はちふん', () => {
    expect(N.minuteReadings(10)).toEqual(['じゅっぷん', 'じっぷん']);
    expect(N.minuteReadings(40)).toEqual(['よんじゅっぷん', 'よんじっぷん']);
    expect(N.minuteReadings(8)).toContain('はちふん');
  });

  it.each([
    [1, 'いちがつ'],
    [4, 'しがつ'],
    [7, 'しちがつ'],
    [9, 'くがつ'],
    [10, 'じゅうがつ'],
    [11, 'じゅういちがつ'],
    [12, 'じゅうにがつ'],
  ])('%i月 is %s', (m, want) => {
    expect(N.monthReadings(m)).toEqual([want]);
  });

  it.each([
    [1, 'ついたち'],
    [2, 'ふつか'],
    [3, 'みっか'],
    [4, 'よっか'],
    [5, 'いつか'],
    [6, 'むいか'],
    [7, 'なのか'],
    [8, 'ようか'],
    [9, 'ここのか'],
    [10, 'とおか'],
    [11, 'じゅういちにち'],
    [14, 'じゅうよっか'],
    [17, 'じゅうしちにち'],
    [19, 'じゅうくにち'],
    [20, 'はつか'],
    [21, 'にじゅういちにち'],
    [24, 'にじゅうよっか'],
    [29, 'にじゅうくにち'],
    [31, 'さんじゅういちにち'],
  ])('%i日 is %s', (d, want) => {
    expect(N.dayReadings(d)[0]).toBe(want);
  });

  const seeded = (seed) => () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };

  it('every generated question has a reading and three wrong readings that are not accepted', () => {
    const rng = seeded(7);
    for (const cat of N.CAT_IDS.filter((c) => c !== 'kata')) {
      for (let i = 0; i < 1500; i++) {
        const q = N.generate(cat, rng);
        expect(q.readings[0]).toMatch(/^[ぁ-ゖー]+$/);
        expect(q.wrong).toHaveLength(3);
        expect(new Set(q.wrong).size).toBe(3);
        q.wrong.forEach((w) => {
          expect(q.readings).not.toContain(w);
          expect(w).toMatch(/^[ぁ-ゖー]+$/);
        });
        expect(q.show).toMatch(/\d/);
      }
    }
  });

  it('generated readings agree with the tables', () => {
    const rng = seeded(11);
    for (let i = 0; i < 400; i++) {
      const t = N.generate('time', rng);
      const m = /^(午前|午後)?(\d+)時(半|(\d+)分)?$/.exec(t.show);
      expect(m).not.toBeNull();
      const pre = { 午前: 'ごぜん', 午後: 'ごご' }[m[1]] || '';
      const min = m[3] === '半' ? 'はん' : m[4] ? N.minuteReadings(Number(m[4]))[0] : '';
      expect(t.readings).toContain(pre + N.hourReadings(Number(m[2]))[0] + min);
      const d = N.generate('date', rng);
      const md = /^(\d+)月(\d+)日$/.exec(d.show);
      expect(d.readings[0]).toBe(
        N.monthReadings(Number(md[1]))[0] + N.dayReadings(Number(md[2]))[0]
      );
    }
  });

  it.each([
    ['duration', /^4時間$/, 'よじかん'],
    ['duration', /^9時間$/, 'くじかん'],
    ['duration', /^1週間$/, 'いっしゅうかん'],
    ['duration', /^8週間$/, 'はっしゅうかん'],
    ['duration', /^1か月$/, 'いっかげつ'],
    ['duration', /^6か月$/, 'ろっかげつ'],
    ['duration', /^10か月$/, 'じゅっかげつ'],
    ['duration', /^4年間$/, 'よねんかん'],
    ['duration', /^2日間$/, 'ふつかかん'],
    ['duration', /^20日間$/, 'はつかかん'],
    ['duration', /^10分間$/, 'じゅっぷんかん'],
    ['age', /^1歳$/, 'いっさい'],
    ['age', /^8歳$/, 'はっさい'],
    ['age', /^10歳$/, 'じゅっさい'],
    ['age', /^20歳$/, 'はたち'],
    ['age', /^18歳$/, 'じゅうはっさい'],
    ['age', /^30歳$/, 'さんじゅっさい'],
    ['price', /^800円$/, 'はっぴゃくえん'],
    ['price', /^3,000円$/, 'さんぜんえん'],
  ])('%s %s is %s', (cat, show, want) => {
    const rng = seeded(3);
    let found = null;
    for (let i = 0; i < 20000 && !found; i++) {
      const q = N.generate(cat, rng);
      if (show.test(q.show)) found = q;
    }
    expect(found, `never generated ${show}`).not.toBeNull();
    expect(found.readings[0]).toBe(want);
  });

  it('4円 is よえん, and よんえん is accepted', () => {
    const rng = seeded(5);
    let q = null;
    for (let i = 0; i < 5000 && !(q && /4円$/.test(q.show)); i++) q = N.generate('price', rng);
    expect(q.show).toMatch(/4円$/);
    expect(q.readings[0]).toMatch(/よえん$/);
    expect(q.readings[1]).toMatch(/よんえん$/);
  });

  it('katakana is matched to its meaning', () => {
    const words = [
      { k: 'コーヒー', en: 'coffee' },
      { k: 'テレビ', en: 'television' },
      { k: 'パン', en: 'bread' },
      { k: 'ドア', en: 'door' },
      { k: 'バス', en: 'bus' },
    ];
    const q = N.generate('kata', seeded(2), { katakana: words });
    expect(q.meaning).toBe(true);
    expect(words.find((w) => w.k === q.show).en).toBe(q.readings[0]);
    expect(q.wrong).toHaveLength(3);
    expect(q.wrong).not.toContain(q.readings[0]);
    expect(N.generate('kata', seeded(2), { katakana: words.slice(0, 2) })).toBeNull();
    expect(N.CATS.kata.choiceOnly).toBe(true);
  });
});
