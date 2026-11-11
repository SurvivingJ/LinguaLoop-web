/**
 * Unit tests for static/js/session/players/intro_drill.js — the new-word drill
 * engine (wiki/features/new-word-drill.tech.md). The shared fixture
 * tests/fixtures/intro_drill/engine_cases.json is also replayed by
 * tests/test_intro_drill.py against services/intro_drill.recount, so the client
 * and server count the same way.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createDrill, effGap, gradeRecall, buildItem, countWord } from '../../static/js/session/players/intro_drill.js';

const cases = JSON.parse(readFileSync(join(process.cwd(), 'tests/fixtures/intro_drill/engine_cases.json'), 'utf8'));

function lcg(seed) {
  let s = seed;
  return () => (s = (s * 1103515245 + 12345) % 2147483648) / 2147483648;
}

function run(words, pattern) {
  const d = createDrill(words, { rng: lcg(42) });
  const results = [];
  const served = [];
  let i = 0;
  let it;
  while ((it = d.next())) {
    served.push(it);
    const ch = pattern[i % pattern.length];
    i += 1;
    const r = d.answer(it, { correct: ch === 'C', idk: ch === 'I' });
    if (r.result) results.push({ r, progress: d.progress(it.sid) });
    if (i > 500) throw new Error('drill did not end');
  }
  return { results, served };
}

describe('effGap', () => {
  it('is at most 4 and at most words-1', () => {
    expect(effGap(1)).toBe(0);
    expect(effGap(3)).toBe(2);
    expect(effGap(10)).toBe(4);
  });
});

describe('createDrill (shared fixture)', () => {
  for (const c of cases) {
    it(`${c.name} reproduces the fixture`, () => {
      const { results } = run(c.words, c.pattern);
      expect(results.map((x) => x.r.result.attempts)).toEqual(c.results.map((x) => x.attempts));
      expect(results.map((x) => x.r.passed)).toEqual(c.results.map((x) => x.expect.passed));
    });
  }
});

describe('createDrill rules', () => {
  const fmts = ['read_typed', 'def_mc', 'read_typed2', 'rev_mc', 'cloze_mc'];
  const words = [1, 2, 3, 4, 5].map((sid) => ({ sense_id: sid, stage: 1, target: 5, cap: 12, cold: false, formats: fmts }));

  it('never serves the same word twice in a row while others remain', () => {
    const { served } = run(words, 'CWCCI');
    for (let k = 1; k < served.length; k++) {
      const others = served.slice(k).some((s) => s.sid !== served[k - 1].sid);
      if (others && served[k].sid === served[k - 1].sid) {
        // allowed only when it is the last word left
        expect(served.slice(k).every((s) => s.sid === served[k].sid)).toBe(true);
      }
    }
  });

  it('all right answers: every word passes in exactly target items', () => {
    const { results } = run(words, 'C');
    for (const { r } of results) {
      expect(r.passed).toBe(true);
      expect(r.result.attempts.length).toBe(5);
    }
  });

  it("'I don't know' never counts and the cold miss raises the target", () => {
    const w = [{ sense_id: 9, stage: 2, target: 3, cap: 8, cold: true, formats: ['read_typed', 'def_mc'] }];
    const d = createDrill(w, { rng: lcg(1) });
    const first = d.next();
    const r = d.answer(first, { correct: false, idk: true });
    expect(r.counted).toBe(false);
    expect(d.progress(9).target).toBe(4);
  });

  it('stops a word at its cap as not passed', () => {
    const w = [{ sense_id: 7, stage: 3, target: 2, cap: 6, cold: true, formats: ['read_typed', 'ex_judge'] }];
    const { results } = run(w, 'W');
    expect(results[0].r.passed).toBe(false);
    expect(results[0].r.result.attempts.length).toBe(6);
  });
});

describe('grading and items', () => {
  it('English recall is case- and space-insensitive', () => {
    expect(gradeRecall('  Apple ', { lemma: 'apple' }, 'en')).toBe(true);
    expect(gradeRecall('appel', { lemma: 'apple' }, 'en')).toBe(false);
  });

  it('builds MC options that include the right answer once', () => {
    const block = {
      lang: 'ja',
      words: [
        { sense_id: 1, lemma: '木', gloss: 'tree', reading: { shown: 'き' } },
        { sense_id: 2, lemma: '水', gloss: 'water', reading: { shown: 'みず' } },
      ],
      pool: [{ lemma: '火', def: 'fire' }, { lemma: '山', def: 'mountain' }],
    };
    const item = buildItem({ word: block.words[0], format: 'def_mc' }, block, new Map());
    expect(item.opts.filter((o) => o === 'tree').length).toBe(1);
    expect(item.opts.length).toBe(4);
    expect(buildItem({ word: block.words[0], format: 'ex_use' }, block, new Map())).toBe(null);
  });
});

describe('countWord (mirror of the server recount)', () => {
  for (const c of cases) {
    it(`${c.name}: agrees with the engine on every word`, () => {
      for (const r of c.results) {
        const rc = countWord(r.stage, r.attempts, r.n_words, r.formats);
        expect([rc.passed, rc.counted, rc.target]).toEqual([r.expect.passed, r.expect.counted, r.expect.target]);
      }
    });
  }
});

describe('spacers', () => {
  it('puts spacers between repeats of a lone word and then runs out', () => {
    const w = [{ sense_id: 1, stage: 2, target: 3, cap: 8, cold: true, formats: ['read_typed', 'def_mc'] }];
    const d = createDrill(w, { rng: lcg(3), spacers: 2 });
    const seq = [];
    let it;
    let guard = 0;
    while ((it = d.next()) && guard++ < 30) {
      if (it.spacer) {
        seq.push('S');
        d.skip(it);
      } else {
        seq.push('W');
        d.answer(it, { correct: true });
      }
    }
    expect(seq.filter((x) => x === 'S').length).toBe(2);
    expect(seq[0]).toBe('W');
    expect(seq.slice(0, 4)).toEqual(['W', 'S', 'S', 'W']);
  });

  it('never uses spacers when there are enough words', () => {
    const fmts = ['read_typed', 'def_mc', 'read_typed2', 'rev_mc', 'cloze_mc'];
    const ws = [1, 2, 3, 4, 5].map((sid) => ({ sense_id: sid, stage: 1, target: 5, cap: 12, cold: false, formats: fmts }));
    const d = createDrill(ws, { rng: lcg(5), spacers: 3 });
    let it;
    let spacers = 0;
    let n = 0;
    while ((it = d.next()) && n++ < 25) {
      if (it.spacer) { spacers++; d.skip(it); } else d.answer(it, { correct: true });
    }
    expect(spacers).toBe(0);
  });
});

describe('buildItem hides the answer and prefers the same part of speech', () => {
  const w = { sense_id: 1, lemma: '宗教改革', gloss: '宗教改革是16世纪的运动。', pos: 'nr', stage: 1 };
  const block = {
    lang: 'zh',
    words: [w, { sense_id: 2, lemma: '印刷术', gloss: '印刷术是复制文字的技术。', pos: 'n' }],
    pool: [
      { lemma: '快', def: '速度高。', pos: 'a' },
      { lemma: '跑', def: '用脚快速移动。', pos: 'v' },
      { lemma: '书', def: '装订成册的著作。', pos: '名词' },
      { lemma: '城市', def: '人口集中的地方。', pos: 'noun' },
    ],
  };

  it('masks the headword in the meaning options and the recall prompt', () => {
    const mc = buildItem({ word: w, format: 'def_mc' }, block, new Map());
    expect(mc.correct).toBe('～是16世纪的运动。');
    expect(mc.opts).toContain('～是16世纪的运动。');
    expect(mc.opts.every((o) => !o.includes('宗教改革'))).toBe(true);
    expect(mc.opts).toContain('～是复制文字的技术。'); // another word's headword is hidden too
    const recall = buildItem({ word: w, format: 'recall_typed' }, block, new Map());
    expect(recall.prompt).toBe('～是16世纪的运动。');
  });

  it('fills wrong options from nouns first', () => {
    for (let i = 0; i < 20; i++) {
      const rev = buildItem({ word: w, format: 'rev_mc' }, block, new Map());
      expect(rev.opts.filter((o) => o !== '宗教改革').sort()).toEqual(['书', '印刷术', '城市'].sort());
    }
  });
});
