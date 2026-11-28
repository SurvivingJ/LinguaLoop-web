/**
 * static/js/grammar/text.js + check.js: option display, blanks, pinyin
 * alignment (one syllable per Hanzi, none for punctuation) and answer checking
 * for the four item types of data/grammar_drills/zh/SPEC.md.
 */
import { describe, it, expect } from 'vitest';
import {
  clozeSegments,
  displayOption,
  fillCloze,
  guessPinyin,
  median,
  readingMap,
  rubyPairs,
  seconds,
  syllables,
  tokenPinyin,
} from '../../static/js/grammar/text.js';
import {
  checkCloze,
  checkJudge,
  checkOrder,
  checkTyped,
  correctSentence,
  typedToOption,
} from '../../static/js/grammar/check.js';
import {
  CLOZE,
  CLOZE_NONE,
  CLOZE_PAIR,
  JUDGE_BAD,
  JUDGE_OK,
  ORDER,
  REWRITE,
} from './fixtures/grammar.js';

describe('pinyin alignment', () => {
  it('gives each Hanzi one syllable and punctuation none', () => {
    const pairs = rubyPairs('我没有哥哥。', 'wǒ méi yǒu gē ge');
    expect(pairs.map((p) => p.py)).toEqual(['wǒ', 'méi', 'yǒu', 'gē', 'ge', '']);
    expect(pairs.map((p) => p.ch).join('')).toBe('我没有哥哥。');
  });

  it('ignores punctuation written in the pinyin', () => {
    expect(syllables('yīn wèi xià yǔ, suǒ yǐ')).toEqual(['yīn', 'wèi', 'xià', 'yǔ', 'suǒ', 'yǐ']);
  });

  it('returns null when the syllable count does not fit', () => {
    expect(rubyPairs('我没有哥哥。', 'wǒ méi yǒu')).toBeNull();
    expect(rubyPairs('3 + 4', '')).toBeNull();
    expect(rubyPairs('', 'wǒ')).toBeNull();
  });

  it('cuts a cloze at its blank and keeps the answer pinyin out of the question', () => {
    const segs = clozeSegments(CLOZE);
    expect(segs.map((s) => (s.blank ? '[' + s.fill + ']' : s.text))).toEqual([
      '我昨天买',
      '[了]',
      '三本书。',
    ]);
    expect(segs[0].pairs.map((p) => p.py)).toEqual(['wǒ', 'zuó', 'tiān', 'mǎi']);
    expect(segs[1].pairs.map((p) => p.py)).toEqual(['le']);
    expect(segs[2].pairs.map((p) => p.py)).toEqual(['sān', 'běn', 'shū', '']);
  });

  it('handles an empty (∅) blank and two blanks', () => {
    const none = clozeSegments(CLOZE_NONE);
    expect(none[1]).toMatchObject({ blank: true, fill: '', pairs: [] });
    expect(none[2].pairs.map((p) => p.py)).toEqual(['kā', 'fēi', '']);
    const pair = clozeSegments(CLOZE_PAIR);
    expect(pair.filter((s) => s.blank).map((s) => s.fill)).toEqual(['因为', '所以']);
    expect(pair[0].pairs.map((p) => p.py)).toEqual(['yīn', 'wèi']);
    expect(pair[2].pairs.map((p) => p.py)).toEqual(['suǒ', 'yǐ']);
  });

  it('drops pinyin for a generated question that is not zh with a blank', () => {
    const segs = clozeSegments({ q: 'bu4 + 是 → ___', opts: ['bú shì', 'bù shì'], a: 0 });
    expect(segs.every((s) => s.pairs === null)).toBe(true);
  });

  it('gives no ruby to a question that spells out pinyin (it would show the answer)', () => {
    const tone = {
      q: '我妈妈不喝 → wǒ mā ma ___ hē',
      opts: ['bú', 'bù'],
      a: 1,
      zh: '我妈妈不喝 → wǒ mā ma bù hē',
      py: 'wǒ mā ma bù hē',
    };
    expect(clozeSegments(tone).every((s) => s.pairs === null)).toBe(true);
    const third = {
      q: '雨伞 → ___',
      opts: ['yǔ sǎn', 'yú sǎn'],
      a: 1,
      zh: '雨伞 → yú sǎn',
      py: 'yú sǎn',
    };
    expect(clozeSegments(third).every((s) => s.pairs === null)).toBe(true);
  });

  it('splits the sentence pinyin over tiles', () => {
    expect(tokenPinyin(ORDER.tokens, ORDER.py)).toEqual([
      'wǒ',
      'míng tiān',
      'zài jiā',
      'kàn',
      'diàn yǐng',
    ]);
    expect(tokenPinyin(['我', '看'], 'wǒ kàn shū')).toBeNull();
  });

  it('guesses a distractor tile from the readings seen in the topic', () => {
    const map = readingMap([CLOZE, REWRITE, JUDGE_BAD]);
    expect(guessPinyin('了', map)).toBe('le');
    expect(guessPinyin('不有', map)).toBe('bù yǒu');
    expect(guessPinyin('猫', map)).toBeNull();
  });
});

describe('options', () => {
  it('shows ∅ as "(nothing)" and a|b as "a … b"', () => {
    expect(displayOption('∅', '(nothing)')).toBe('(nothing)');
    expect(displayOption('因为|所以')).toBe('因为 … 所以');
    expect(displayOption('了|∅', '(nothing)')).toBe('了 … (nothing)');
  });

  it('fills blanks', () => {
    expect(fillCloze(CLOZE.q, '了')).toBe(CLOZE.zh);
    expect(fillCloze(CLOZE_NONE.q, '∅')).toBe(CLOZE_NONE.zh);
    expect(fillCloze(CLOZE_PAIR.q, '因为|所以')).toBe(CLOZE_PAIR.zh);
  });
});

describe('answer checking', () => {
  it('cloze: only the option at `a` is right', () => {
    expect(checkCloze(CLOZE, '了')).toBe(true);
    expect(checkCloze(CLOZE, '过')).toBe(false);
    expect(checkCloze(CLOZE_NONE, '∅')).toBe(true);
    expect(checkCloze(CLOZE, null)).toBe(false);
  });

  it('typed: the exact string, pairs separated by a space or comma', () => {
    expect(checkTyped(CLOZE, ' 了 ')).toBe(true);
    expect(checkTyped(CLOZE, '了了')).toBe(false);
    expect(checkTyped(CLOZE_PAIR, '因为 所以')).toBe(true);
    expect(checkTyped(CLOZE_PAIR, '因为，所以')).toBe(true);
    expect(checkTyped(CLOZE_PAIR, '所以 因为')).toBe(false);
    expect(typedToOption('')).toBe('∅');
  });

  it('order: the tokens or any alt, compared as joined strings', () => {
    expect(checkOrder(ORDER, ['我', '明天', '在家', '看', '电影'])).toBe(true);
    expect(checkOrder(ORDER, ['明天', '我', '在家', '看', '电影'])).toBe(true);
    expect(checkOrder(ORDER, ['我', '在家', '明天', '看', '电影'])).toBe(false);
    // A distractor tile makes it wrong; differently cut tiles that join the same are right.
    expect(checkOrder(ORDER, ['我', '明天', '在家', '看', '了', '电影'])).toBe(false);
    expect(checkOrder(ORDER, ['我明天', '在家看', '电影'])).toBe(true);
    expect(checkOrder(ORDER, [])).toBe(false);
    expect(checkOrder(REWRITE, REWRITE.tokens)).toBe(true);
  });

  it('judge', () => {
    expect(checkJudge(JUDGE_BAD, false)).toBe(true);
    expect(checkJudge(JUDGE_BAD, true)).toBe(false);
    expect(checkJudge(JUDGE_OK, true)).toBe(true);
  });

  it('finds the correct sentence of any item', () => {
    expect(correctSentence(JUDGE_BAD)).toBe('我没有哥哥。');
    expect(correctSentence({ type: 'cloze', q: '一___人', opts: ['个', '只'], a: 0 })).toBe(
      '一个人'
    );
    expect(correctSentence({ type: 'order', tokens: ['我', '去'] })).toBe('我去');
  });
});

describe('numbers', () => {
  it('median and seconds', () => {
    expect(median([])).toBe(0);
    expect(median([3000, 1000, 2000])).toBe(2000);
    expect(median([1000, 2000, 3000, 5000])).toBe(2500);
    expect(seconds(2140)).toBe('2.1');
  });
});
