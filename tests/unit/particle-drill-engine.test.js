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
      ({ state: s, event } = M.record(s, { correct: true, level: 3 }, 10, 3));
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
