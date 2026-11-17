/**
 * Prestudy word prime, "choose the meaning" / "choose the word" options
 * (static/js/prestudy/prestudy.js meaningOptions): every option of one item is
 * in one gloss language, and no distractor is a plausible meaning of the target.
 * E2E finding 2026-11-16: 格外 had only a Chinese gloss, so its options mixed a
 * Chinese correct answer with English distractors, one of which ("especially;
 * standing out") was effectively right.
 */

import { describe, it, expect, beforeAll } from 'vitest';

let L;
beforeAll(async () => {
  await import('../../static/js/prestudy/prestudy.js');
  L = window.LinguaPrestudy;
});

const EN = '2',
  ZH = '1';
const sense = (lemma, glosses) => ({
  lemma,
  glosses: Object.fromEntries(Object.entries(glosses).map(([k, v]) => [k, { def: v }])),
});
const SENSES = {
  10: sense('格外', { [ZH]: '表示程度超过一般；特别，分外。' }), // no English gloss
  11: sense('特别', { [ZH]: '与众不同，不普通。', [EN]: 'especially; standing out' }),
  12: sense('猫', { [ZH]: '一种常见的宠物。', [EN]: 'cat' }),
  13: sense('跑', { [ZH]: '用脚快速前进。', [EN]: 'to run' }),
  14: sense('书', { [ZH]: '写着文字的册子。', [EN]: 'book' }),
  15: sense('高兴', { [ZH]: '心里快乐。', [EN]: 'happy; glad' }),
  16: sense('快乐', { [ZH]: '感到幸福或满意。', [EN]: 'happy' }), // overlaps 高兴
  17: sense('猫', { [ZH]: '像猫一样轻手轻脚。', [EN]: 'to sneak like a cat' }), // second sense of 猫
  18: sense('雨', { [ZH]: '从云中落下的水。', [EN]: 'rain' }),
};
const POOL = Object.keys(SENSES);
const opts = (sid, extra) =>
  L.meaningOptions(sid, POOL, { senses: SENSES, langs: [EN, ZH], ...(extra || {}) });

function langOf(text) {
  return /[一-鿿]/.test(text) ? ZH : EN;
}

describe('meaningOptions', () => {
  it('uses the learner language when the target has a gloss in it', () => {
    const m = opts('12');
    expect(m.lang).toBe(EN);
    expect(m.target).toBe('cat');
    expect(m.distractors.length).toBe(3);
    for (const d of m.distractors) expect(langOf(d.text)).toBe(EN);
  });

  it('builds the whole item in the study language when the target has no learner gloss (格外)', () => {
    for (let run = 0; run < 20; run++) {
      const m = opts('10');
      expect(m.lang).toBe(ZH);
      expect(langOf(m.target)).toBe(ZH);
      for (const d of m.distractors) expect(langOf(d.text)).toBe(ZH);
      // 特别 is named in 格外's gloss: never a distractor
      expect(m.distractors.map((d) => d.sid)).not.toContain('11');
      expect(m.distractors.map((d) => d.text)).not.toContain('especially; standing out');
    }
  });

  it('never offers another sense of the same word or an overlapping gloss', () => {
    for (let run = 0; run < 20; run++) {
      const cat = opts('12').distractors.map((d) => d.sid);
      expect(cat).not.toContain('17');
      const happy = opts('15').distractors.map((d) => d.sid);
      expect(happy).not.toContain('16'); // "happy" is part of "happy; glad"
    }
  });

  it('skips the item when fewer than two clean distractors exist', () => {
    const tiny = { 1: SENSES[10], 2: SENSES[11], 3: SENSES[12] };
    const m = L.meaningOptions('1', ['1', '2', '3'], { senses: tiny, langs: [EN, ZH] });
    expect(m).toBeNull(); // only 猫 is clean in Chinese
  });

  it('falls back to the study language when the learner language has too few distractors', () => {
    const s = {
      1: sense('猫', { [ZH]: '一种常见的宠物。', [EN]: 'cat' }),
      2: sense('跑', { [ZH]: '用脚快速前进。' }),
      3: sense('书', { [ZH]: '写着文字的册子。' }),
      4: sense('雨', { [ZH]: '从云中落下的水。', [EN]: 'rain' }),
    };
    const m = L.meaningOptions('1', ['1', '2', '3', '4'], { senses: s, langs: [EN, ZH] });
    expect(m.lang).toBe(ZH);
    expect(m.distractors.length).toBe(3);
  });

  it('masks the headword in every option', () => {
    const s = {
      1: sense('学校', { [ZH]: '学校是学习的地方。' }),
      2: sense('医院', { [ZH]: '医院是看病的地方。' }),
      3: sense('公园', { [ZH]: '公园是玩的地方。' }),
    };
    const mask = (d, lemma) => d.split(lemma).join('～');
    const m = L.meaningOptions('1', ['1', '2', '3'], { senses: s, langs: [EN, ZH], mask });
    expect(m.target).toBe('～是学习的地方。');
    expect(m.distractors.map((d) => d.text).sort()).toEqual(['～是玩的地方。', '～是看病的地方。']);
  });
});

describe('plausibleMeaning', () => {
  it('flags one word inside the other and a contained gloss part (real-app finding 坐在 / 坐)', () => {
    const s = {
      1: sense('坐在', { [EN]: 'to sit on; to put your bottom down on a chair' }),
      2: sense('坐', { [EN]: 'to sit; to put your body down on a chair' }),
      3: sense('座位', { [EN]: 'seat; to sit' }),
      4: sense('时', { [EN]: 'time; a period or moment (formal)' }),
    };
    expect(L.plausibleMeaning(s, '1', '2', EN)).toBe(true); // 坐 is inside 坐在
    expect(L.plausibleMeaning(s, '1', '3', EN)).toBe(true); // "to sit" part shared
    expect(L.plausibleMeaning(s, '1', '4', EN)).toBe(false);
  });

  it('flags same lemma, identical, contained and overlapping glosses', () => {
    expect(L.plausibleMeaning(SENSES, '12', '17', EN)).toBe(true);
    expect(L.plausibleMeaning(SENSES, '15', '16', EN)).toBe(true);
    expect(L.plausibleMeaning(SENSES, '10', '11', ZH)).toBe(true);
    expect(L.plausibleMeaning(SENSES, '12', '13', EN)).toBe(false);
  });
});

describe('wordConfusable (cloze word choice)', () => {
  it('rejects a word inside the target, another sense of it, or a word with an overlapping gloss', () => {
    expect(L.wordConfusable(SENSES, '12', '17', [EN, ZH])).toBe(true); // 猫 / 猫
    expect(L.wordConfusable(SENSES, '15', '16', [EN, ZH])).toBe(true); // happy; glad / happy
    expect(L.wordConfusable(SENSES, '10', '11', [EN, ZH])).toBe(true); // 格外's gloss names 特别
    const s = { 1: sense('坐在', { [EN]: 'to sit on' }), 2: sense('坐', {}) };
    expect(L.wordConfusable(s, '1', '2', [EN, ZH])).toBe(true); // no gloss, but 坐 is inside 坐在
  });

  it('keeps unrelated words, and a missing gloss alone is no reason to reject', () => {
    expect(L.wordConfusable(SENSES, '12', '13', [EN, ZH])).toBe(false); // cat / to run
    expect(L.wordConfusable(SENSES, '10', '14', [EN, ZH])).toBe(false); // 格外 has no English gloss
  });
});
