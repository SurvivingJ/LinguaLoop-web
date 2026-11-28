/**
 * static/js/grammar/generators: the infinite-practice generators for the
 * Chinese grammar drills. Every generator is run with a seeded rng and each
 * item is checked against the item contract in data/grammar_drills/zh/SPEC.md.
 */
import { describe, it, expect } from 'vitest';
import { generatorsFor, GENERATOR_TOPICS } from '../../static/js/grammar/generators/index.js';
import {
  readNumber,
  numberMistakes,
  clockForms,
} from '../../static/js/grammar/generators/numbers-time.js';
import {
  buTone,
  yiTone,
  thirdPair,
  toneOf,
  setTone,
  WORDS,
} from '../../static/js/grammar/generators/tone-sandhi.js';
import { NOUNS, MEASURES } from '../../static/js/grammar/generators/measure-words.js';

/** Deterministic rng (mulberry32). */
function seeded(seed) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const PER_GENERATOR = 400;
const HAN = /\p{Script=Han}/gu;
const PUNCTUATION = /[。，！？、：；]/g;
const SYLLABLE = /^[a-zāáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜ]+$/;

// Topic -> generator keys, with the fewest distinct items each must reach in
// PER_GENERATOR draws (set well below what the tables produce today).
const EXPECTED = {
  'numbers-time': { 'number-reading': 300, 'clock-time': 300, 'date-order': 350, money: 250 },
  'er-liang': { 'er-liang': 250 },
  'tone-sandhi': { 'bu-tone': 250, 'yi-tone': 200, 'third-tones': 200 },
  'measure-words': { 'measure-words': 300 },
  'de-three': { 'de-three': 300 },
  'bu-mei': { 'bu-mei': 280 },
  'potential-complement': { 'potential-form': 300 },
  'word-order': { 'word-order': 300 },
  ba: { 'ba-order': 280, 'ba-or-bei': 200 },
  bei: { 'bei-order': 300, 'bei-or-ba': 200 },
  comparison: { 'comparison-order': 250, 'comparison-cloze': 250 },
  'duration-frequency': { 'duration-order': 320 },
  'separable-verbs': { 'separable-cloze': 280, 'separable-order': 280 },
};

const ALL = GENERATOR_TOPICS.flatMap((slug) =>
  generatorsFor(slug).map((g, i) => ({ slug, g, seed: slug.length * 131 + i * 17 + 5 }))
);

const sample = ({ g, seed }, n = PER_GENERATOR) => {
  const rng = seeded(seed);
  return Array.from({ length: n }, () => g.make(rng));
};

const signature = (item) =>
  JSON.stringify([item.type, item.q || item.tokens, item.opts && [...item.opts].sort(), item.zh]);

describe('generator registry', () => {
  it('lists exactly the planned topics and keys', () => {
    expect([...GENERATOR_TOPICS].sort()).toEqual(Object.keys(EXPECTED).sort());
    for (const slug of GENERATOR_TOPICS) {
      expect(generatorsFor(slug).map((g) => g.key)).toEqual(Object.keys(EXPECTED[slug]));
    }
  });

  it('returns an empty list for topics without generators', () => {
    expect(generatorsFor('le')).toEqual([]);
    expect(generatorsFor('no-such-topic')).toEqual([]);
    expect(generatorsFor('constructor')).toEqual([]);
  });

  it('gives every generator a label and a make() that defaults to Math.random', () => {
    for (const { g } of ALL) {
      expect(typeof g.label).toBe('string');
      expect(g.label.length).toBeGreaterThan(2);
      const item = g.make();
      expect(item.id).toBe(`gen:${g.key}`);
    }
  });

  it('survives a long run without throwing', () => {
    for (const entry of ALL) {
      const rng = seeded(entry.seed + 1000);
      for (let i = 0; i < 4000; i++) expect(entry.g.make(rng).id).toBe(`gen:${entry.g.key}`);
    }
  });

  it('is reproducible for the same seed', () => {
    for (const entry of ALL) {
      expect(sample(entry, 20)).toEqual(sample(entry, 20));
    }
  });
});

describe.each(ALL)('$slug / $g.key', (entry) => {
  const items = sample(entry);

  it('fills the common fields', () => {
    for (const item of items) {
      expect(item.id).toBe(`gen:${entry.g.key}`);
      expect(['cloze', 'order', 'judge']).toContain(item.type);
      for (const field of ['zh', 'py', 'en', 'why']) {
        expect(typeof item[field], `${field} of ${item.zh}`).toBe('string');
        expect(item[field].length, `${field} of ${item.zh}`).toBeGreaterThan(0);
      }
      expect(item.why.length, item.why).toBeGreaterThanOrEqual(15);
      expect(item.why.length, item.why).toBeLessThanOrEqual(260);
      expect(item.en, item.zh).not.toMatch(/[{}[\]]|undefined|null/);
      expect(item.why, item.zh).not.toMatch(/undefined|null|\{/);
      if ('cue' in item) expect(item.cue.length).toBeGreaterThan(0);
    }
  });

  it('has one pinyin syllable per Hanzi', () => {
    for (const item of items) {
      const hanzi = (item.zh.match(HAN) || []).length;
      const syllables = item.py.split(' ');
      expect(hanzi, item.zh).toBeGreaterThanOrEqual(2);
      expect(syllables.length, `${item.zh} / ${item.py}`).toBe(hanzi);
      for (const s of syllables) expect(s, `${item.zh} / ${item.py}`).toMatch(SYLLABLE);
    }
  });

  it('builds well-formed cloze items', () => {
    for (const item of items.filter((x) => x.type === 'cloze')) {
      expect(item.q.split('___').length, item.q).toBe(2);
      expect(item.opts.length).toBeGreaterThanOrEqual(2);
      expect(item.opts.length).toBeLessThanOrEqual(4);
      expect(Number.isInteger(item.a) && item.a >= 0 && item.a < item.opts.length).toBe(true);
      expect(item.zh).toBe(item.q.replace('___', item.opts[item.a]));
      const sentences = item.opts.map((o) => item.q.replace('___', o));
      expect(new Set(item.opts).size, item.q).toBe(item.opts.length);
      expect(new Set(sentences).size, item.q).toBe(item.opts.length);
      for (const o of item.opts) expect(o.length, item.q).toBeGreaterThan(0);
    }
  });

  it('builds well-formed order items', () => {
    for (const item of items.filter((x) => x.type === 'order')) {
      expect(item.tokens.length).toBeGreaterThanOrEqual(3);
      expect(item.tokens.length).toBeLessThanOrEqual(10);
      expect(item.tokens.join('')).toBe(item.zh.replace(PUNCTUATION, ''));
      expect(Array.isArray(item.alts)).toBe(true);
      expect(item.alts.length).toBeLessThanOrEqual(2);
      const main = item.tokens.join('|');
      const sorted = [...item.tokens].sort().join('|');
      const seen = new Set([main]);
      for (const alt of item.alts) {
        expect([...alt].sort().join('|'), item.zh).toBe(sorted);
        expect(seen.has(alt.join('|')), item.zh).toBe(false);
        seen.add(alt.join('|'));
      }
    }
  });

  it('produces many distinct items and varies the answer position', () => {
    const distinct = new Set(items.map(signature)).size;
    expect(distinct).toBeGreaterThanOrEqual(EXPECTED[entry.slug][entry.g.key]);
    const cloze = items.filter((x) => x.type === 'cloze');
    if (cloze.length) {
      const positions = new Set(cloze.map((x) => x.a));
      expect(positions.size).toBeGreaterThanOrEqual(2);
      const maxOpts = Math.max(...cloze.map((x) => x.opts.length));
      expect(positions.size).toBe(maxOpts);
    }
  });
});

describe('number reader', () => {
  it.each([
    [0, '零'],
    [5, '五'],
    [10, '十'],
    [12, '十二'],
    [20, '二十'],
    [22, '二十二'],
    [100, '一百'],
    [105, '一百零五'],
    [110, '一百一十'],
    [111, '一百一十一'],
    [200, '二百'],
    [222, '二百二十二'],
    [1000, '一千'],
    [1001, '一千零一'],
    [1010, '一千零一十'],
    [1100, '一千一百'],
    [2000, '两千'],
    [2002, '两千零二'],
    [2200, '两千二百'],
    [10000, '一万'],
    [10001, '一万零一'],
    [10010, '一万零一十'],
    [12000, '一万二千'],
    [20000, '两万'],
    [22000, '两万二千'],
    [30507, '三万零五百零七'],
    [100000, '十万'],
    [105000, '十万五千'],
    [110000, '十一万'],
    [100012, '十万零一十二'],
    [200000, '二十万'],
    [1000000, '一百万'],
    [2000000, '二百万'],
    [10000000, '一千万'],
    [20000000, '两千万'],
    [100000000, '一亿'],
    [100005000, '一亿零五千'],
    [200000000, '两亿'],
    [520701540, '五亿二千零七十万一千五百四十'],
    [999999999, '九亿九千九百九十九万九千九百九十九'],
  ])('%i -> %s', (n, expected) => {
    expect(readNumber(n)).toBe(expected);
  });

  // Policy: 二百 is the reading produced; 两百 is equally acceptable. A leading
  // 2 before 千 / 万 / 亿 is 两, where 二 is tolerated in formal reading. So a
  // wrong option may never differ from the answer only by 二 <-> 两 before
  // 百 / 千 / 万 / 亿.
  it('never offers a 二 / 两 variant before 百, 千, 万 or 亿 as a mistake', () => {
    const swap = (s) => s.replace(/[二两](?=[百千万亿])/g, '2');
    for (const n of [200, 202, 220, 1200, 2000, 2020, 2200, 20000, 22000, 200000000, 220022]) {
      const right = swap(readNumber(n));
      for (const wrong of numberMistakes(n)) expect(swap(wrong), `${n}: ${wrong}`).not.toBe(right);
    }
  });

  it('gives at least three distinct mistakes, none equal to the reading', () => {
    const rng = seeded(99);
    const sizes = [9, 99, 999, 9999, 99999, 999999, 99999999, 999999999];
    for (let i = 0; i < 2000; i++) {
      const n = 1 + Math.floor(rng() * sizes[i % sizes.length]);
      const wrong = numberMistakes(n);
      expect(wrong.length, String(n)).toBeGreaterThanOrEqual(3);
      expect(new Set(wrong).size).toBe(wrong.length);
      expect(wrong).not.toContain(readNumber(n));
    }
  });

  it('makes the typical mistakes: missing 零, digit listing, 两十, thousands grouping', () => {
    expect(numberMistakes(105)).toContain('一百五');
    expect(numberMistakes(105)).toContain('一零五');
    expect(numberMistakes(1005)).toContain('一千零零五');
    expect(numberMistakes(25)).toContain('两十五');
    expect(numberMistakes(12)).toContain('十两');
    expect(numberMistakes(12)).toContain('一十二');
    expect(numberMistakes(30507)).toContain('三十千五百零七');
    expect(numberMistakes(10000)).toContain('十千');
    expect(numberMistakes(150)).not.toContain('一百五');
  });
});

describe('clock forms', () => {
  it('accepts the standard readings', () => {
    expect(clockForms(3, 45).good).toEqual([
      '三点三刻',
      '三点四十五分',
      '三点四十五',
      '差一刻四点',
    ]);
    expect(clockForms(3, 15).good).toContain('三点一刻');
    expect(clockForms(3, 30).good).toContain('三点半');
    expect(clockForms(3, 5).good).toEqual(['三点零五分', '三点零五']);
    expect(clockForms(2, 0).good).toEqual(['两点']);
    expect(clockForms(12, 45).good).toContain('差一刻一点');
    expect(clockForms(1, 50).good).toContain('差十分两点');
    expect(clockForms(10, 10).good).toEqual(['十点十分']);
  });

  it('never lists an accepted reading as wrong', () => {
    for (let h = 1; h <= 12; h++) {
      for (let m = 0; m < 60; m++) {
        const { good, bad } = clockForms(h, m);
        expect(bad.length, `${h}:${m}`).toBeGreaterThanOrEqual(3);
        for (const b of bad) expect(good, `${h}:${m}`).not.toContain(b);
        // the other clock's acceptable forms must not appear as this one's answer
        expect(new Set([...good, ...bad]).size).toBe(good.length + bad.length);
      }
    }
  });

  it('offers 二点 as the mistake whenever the answer has 两点', () => {
    const [clock] = generatorsFor('numbers-time').filter((g) => g.key === 'clock-time');
    const rng = seeded(4);
    let seen = 0;
    for (let i = 0; i < 600; i++) {
      const item = clock.make(rng);
      if (!item.zh.includes('两点')) continue;
      seen += 1;
      expect(item.opts.some((o) => o.includes('二点'))).toBe(true);
    }
    expect(seen).toBeGreaterThan(10);
  });
});

describe('tone rules', () => {
  it('不 is bú only before a fourth tone', () => {
    expect(buTone('shì')).toBe('bú');
    expect(buTone('qù')).toBe('bú');
    expect(buTone('yào')).toBe('bú');
    expect(buTone('chī')).toBe('bù');
    expect(buTone('lái')).toBe('bù');
    expect(buTone('hǎo')).toBe('bù');
    expect(buTone('máng')).toBe('bù');
  });

  it('一 is yí before a fourth tone, yì before the others, yī as ordinal or final', () => {
    expect(yiTone('gè')).toBe('yí');
    expect(yiTone('yàng')).toBe('yí');
    expect(yiTone('dìng')).toBe('yí');
    expect(yiTone('tiān')).toBe('yì');
    expect(yiTone('nián')).toBe('yì');
    expect(yiTone('qǐ')).toBe('yì');
    expect(yiTone('běn')).toBe('yì');
    expect(yiTone('yuè', { ordinal: true })).toBe('yī');
    expect(yiTone('gè', { ordinal: true })).toBe('yī');
    expect(yiTone(undefined)).toBe('yī');
  });

  it('the first of two third tones becomes a second tone', () => {
    expect(thirdPair('nǐ', 'hǎo')).toEqual(['ní', 'hǎo']);
    expect(thirdPair('hěn', 'hǎo')).toEqual(['hén', 'hǎo']);
    expect(thirdPair('shuǐ', 'guǒ')).toEqual(['shuí', 'guǒ']);
    expect(thirdPair('lǎo', 'shī')).toEqual(['lǎo', 'shī']);
    expect(thirdPair('hěn', 'máng')).toEqual(['hěn', 'máng']);
    expect(thirdPair('kàn', 'hǎo')).toEqual(['kàn', 'hǎo']);
  });

  it('reads and rewrites tone marks', () => {
    expect(['mā', 'má', 'mǎ', 'mà', 'ma'].map(toneOf)).toEqual([1, 2, 3, 4, 5]);
    expect(toneOf('lǜ')).toBe(4);
    expect(setTone('hǎo', 2)).toBe('háo');
    expect(setTone('liǎng', 2)).toBe('liáng');
    expect(setTone('jiǔ', 2)).toBe('jiú');
    expect(setTone('shuǐ', 2)).toBe('shuí');
    expect(setTone('gǒu', 2)).toBe('góu');
    expect(setTone('lǚ', 2)).toBe('lǘ');
    expect(setTone('xué', 3)).toBe('xuě');
  });

  it('applies the 不 rule in generated items', () => {
    const [bu] = generatorsFor('tone-sandhi');
    const rng = seeded(11);
    for (let i = 0; i < 400; i++) {
      const item = bu.make(rng);
      const [, after] = item.q.split('___ ');
      const expected = toneOf(after.split(' ')[0]) === 4 ? 'bú' : 'bù';
      expect(item.opts[item.a], item.q).toBe(expected);
      expect([...item.opts].sort()).toEqual(['bù', 'bú'].sort());
    }
  });

  it('applies the 一 rule in generated items', () => {
    const yi = generatorsFor('tone-sandhi')[1];
    const rng = seeded(12);
    const answers = new Set();
    for (let i = 0; i < 600; i++) {
      const item = yi.make(rng);
      const phrase = item.q.split(' → ')[0];
      const [before, after] = item.q.split(' → ')[1].split('___');
      const next = after.trim().split(' ')[0];
      const answer = item.opts[item.a];
      answers.add(answer);
      expect([...item.opts].sort()).toEqual(['yī', 'yí', 'yì'].sort());
      const ordinal =
        /^第|^星期|^周|^初|[十]一/.test(phrase) ||
        before.trim().length > 0 ||
        /^一[月号楼班二九]|^一年级/.test(phrase);
      if (!ordinal) expect(answer, item.q).toBe(yiTone(next));
      else expect(answer, item.q).toBe('yī');
    }
    expect(answers.size).toBe(3);
  });

  it('applies the third-tone rule in generated items', () => {
    const third = generatorsFor('tone-sandhi')[2];
    const rng = seeded(13);
    let changed = 0;
    for (let i = 0; i < 600; i++) {
      const item = third.make(rng);
      const written = item.opts.find(
        (o) =>
          toneOf(o.split(' ')[0]) === 3 &&
          item.opts.filter((p) => p.split(' ')[1] === o.split(' ')[1]).length === 2
      );
      const [a, b, ...rest] = written.split(' ');
      const expected = [...thirdPair(a, b), ...rest].join(' ');
      expect(item.opts[item.a], item.q).toBe(expected);
      if (expected !== written) changed += 1;
    }
    expect(changed).toBeGreaterThan(100);
    expect(changed).toBeLessThan(500);
  });

  it('has a table of about 150 common words with tone marks', () => {
    expect(WORDS.length).toBeGreaterThanOrEqual(150);
    for (const word of WORDS) {
      expect(word.py.split(' ').length, word.zh).toBe([...word.zh].length);
      expect(toneOf(word.py.split(' ')[0]), word.zh).toBeLessThanOrEqual(4);
    }
  });
});

describe('measure-word table', () => {
  it('has at least 120 nouns, each with a standard measure and 2-3 wrong ones', () => {
    expect(NOUNS.length).toBeGreaterThanOrEqual(120);
    expect(new Set(NOUNS.map((n) => n.zh)).size).toBe(NOUNS.length);
    for (const noun of NOUNS) {
      expect(MEASURES[noun.ok[0]], noun.zh).toBeTruthy();
      expect(noun.bad.length, noun.zh).toBeGreaterThanOrEqual(2);
      expect(noun.bad.length, noun.zh).toBeLessThanOrEqual(3);
      for (const bad of noun.bad) {
        expect(MEASURES[bad], `${noun.zh} ${bad}`).toBeTruthy();
        expect(noun.ok, `${noun.zh} ${bad}`).not.toContain(bad);
      }
      expect(noun.py.split(' ').length, noun.zh).toBe([...noun.zh].length);
    }
  });

  it('never offers 个 as a wrong measure word', () => {
    for (const noun of NOUNS) expect(noun.bad, noun.zh).not.toContain('个');
  });
});

describe('topic-specific guarantees', () => {
  const run = (slug, key, n = 400, seed = 21) => {
    const g = generatorsFor(slug).find((x) => x.key === key);
    const rng = seeded(seed);
    return Array.from({ length: n }, () => g.make(rng));
  };

  it('er-liang: two options, 二 and 两', () => {
    for (const item of run('er-liang', 'er-liang')) {
      expect([...item.opts].sort()).toEqual(['两', '二'].sort());
      expect(item.q).not.toMatch(/___[百千万亿]/);
    }
  });

  it('bu-mei: forced by 有 / 是 / 过 and by time words', () => {
    for (const item of run('bu-mei', 'bu-mei', 800)) {
      const answer = item.opts[item.a];
      expect([...item.opts].sort()).toEqual(['不', '没'].sort());
      if (item.q.includes('___有')) expect(answer).toBe('没');
      if (item.q.includes('___是')) expect(answer).toBe('不');
      if (item.q.includes('过')) expect(answer).toBe('没');
      if (/明天|后天|今天晚上|这个周末|平时|一般/.test(item.q)) expect(answer).toBe('不');
      if (/昨天|前天|今天早上|上个周末|还___/.test(item.q)) expect(answer).toBe('没');
    }
  });

  it('de-three: always the three particles', () => {
    const answers = new Set();
    for (const item of run('de-three', 'de-three')) {
      expect([...item.opts].sort()).toEqual(['的', '得', '地'].sort());
      answers.add(item.opts[item.a]);
    }
    expect(answers.size).toBe(3);
  });

  it('potential-complement: the answer has 不 or 得 inside the compound', () => {
    for (const item of run('potential-complement', 'potential-form')) {
      const answer = item.opts[item.a];
      expect(answer).toMatch(/^.[不得]/);
      expect(item.opts.length).toBe(4);
      // forms that are real Chinese with another meaning are never offered
      for (const o of item.opts) {
        expect(o).not.toMatch(/得不/);
        expect(o).not.toMatch(/^不[进出回上爬]/);
        expect(o).not.toBe('没来得及');
      }
    }
  });

  it('measure-words: the answer is the standard measure and no option is acceptable twice', () => {
    const byZh = Object.fromEntries(NOUNS.map((n) => [n.zh, n]));
    const nouns = [...NOUNS].sort((a, b) => b.zh.length - a.zh.length);
    for (const item of run('measure-words', 'measure-words', 800)) {
      const after = item.q.split('___')[1];
      const noun = nouns.find((n) => after.startsWith(n.zh));
      expect(noun, item.q).toBeTruthy();
      const accepted = item.opts.filter((o) => byZh[noun.zh].ok.includes(o));
      expect(accepted, item.q).toEqual([item.opts[item.a]]);
    }
  });

  it('word-order: a leading time word is the only alternative order', () => {
    for (const item of run('word-order', 'word-order')) {
      expect(item.type).toBe('order');
      for (const alt of item.alts) {
        expect(alt[0]).toBe(item.tokens[1]);
        expect(alt[1]).toBe(item.tokens[0]);
        expect(alt.slice(2)).toEqual(item.tokens.slice(2));
      }
      const zai = item.tokens.findIndex((t) => t.startsWith('在'));
      if (zai > 0) expect(zai).toBeLessThan(item.tokens.length - 1);
    }
  });

  it('ba / bei: negation, modals and adverbs come before 把 / 被', () => {
    for (const item of run('ba', 'ba-order')) {
      const ba = item.tokens.indexOf('把');
      expect(ba).toBeGreaterThanOrEqual(0);
      expect(item.alts).toEqual([]);
      for (const word of ['没', '别', '想', '要', '应该', '得', '可以', '打算', '必须', '请']) {
        const at = item.tokens.indexOf(word);
        if (at >= 0) expect(at).toBeLessThan(ba);
      }
      if (item.tokens.includes('没')) expect(item.tokens).not.toContain('了');
    }
    for (const item of run('bei', 'bei-order')) {
      const bei = item.tokens.indexOf('被');
      expect(bei).toBeGreaterThanOrEqual(1);
      for (const word of ['没', '不会', '可能', '差点儿', '已经', '又']) {
        const at = item.tokens.indexOf(word);
        if (at >= 0) expect(at).toBeLessThan(bei);
      }
    }
    for (const [slug, key] of [
      ['ba', 'ba-or-bei'],
      ['bei', 'bei-or-ba'],
    ]) {
      const answers = new Set();
      for (const item of run(slug, key)) {
        expect([...item.opts].sort()).toEqual(['把', '被'].sort());
        answers.add(item.opts[item.a]);
      }
      expect(answers.size).toBe(2);
    }
  });

  it('comparison: 比 sentences never put 很 before the adjective', () => {
    for (const item of run('comparison', 'comparison-order')) {
      expect(item.zh).not.toMatch(/比.*[很非太]/);
      if (item.tokens.includes('一样')) expect(item.alts.length).toBe(1);
      else expect(item.alts).toEqual([]);
    }
    for (const item of run('comparison', 'comparison-cloze')) {
      expect(item.zh).not.toMatch(/比.*(很|非常|太)/);
    }
  });

  it('duration-frequency: durations follow the verb unless it is negated', () => {
    for (const item of run('duration-frequency', 'duration-order')) {
      const mei = item.tokens.indexOf('没');
      if (mei >= 0) {
        expect(mei).toBe(2);
        expect(item.tokens[item.tokens.length - 1]).toBe('了');
      } else {
        expect(item.tokens[1]).toMatch(/了$|过$/);
      }
    }
  });

  it('separable-verbs: 了 / 过 sit inside the compound', () => {
    for (const item of run('separable-verbs', 'separable-order')) {
      const verb = item.tokens.findIndex((t) => /[了过]$/.test(t));
      expect(verb).toBeGreaterThanOrEqual(1);
      expect(verb).toBe(item.tokens.length - 3);
    }
    for (const item of run('separable-verbs', 'separable-cloze')) {
      const answer = item.opts[item.a];
      if (!/^[了过]/.test(answer)) continue;
      // the wrong options are the same pieces in another order
      const pieces = [...answer].sort().join('');
      for (const o of item.opts.filter((x) => x.length === answer.length)) {
        expect([...o].sort().join(''), item.q).toBe(pieces);
      }
    }
  });
});
