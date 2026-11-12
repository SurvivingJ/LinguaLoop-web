/**
 * Pinyin grading with dictionary-tone references: stored readings carry
 * citation tones, the grader derives sandhi (third tone, 一, 不) from the word
 * and accepts either form.
 */

import { describe, it, expect, beforeAll } from 'vitest';

let L;
beforeAll(async () => {
  globalThis.window = globalThis.window || {};
  globalThis.document = globalThis.document || {
    addEventListener() {}, getElementById() { return null }, querySelector() { return null }, querySelectorAll() { return [] },
  };
  await import('../../static/js/prestudy/prestudy.js');
  L = window.LinguaPrestudy;
});

const grade = (input, numbered, hanzi) => {
  const p = L.parsePinyinInput(input);
  return L.gradeZh(p.segs, p.tones, numbered, hanzi).ok;
};

describe('gradeZh with sandhi', () => {
  it.each([
    ['jian3 huan3', 'jian3 huan3', '减缓', true],
    ['jian2 huan3', 'jian3 huan3', '减缓', true],
    ['jian4 huan3', 'jian3 huan3', '减缓', false],
    ['zhu2 dao2 zhe3', 'zhu3 dao3 zhe3', '主导者', true],
    ['bu2 yong4', 'bu4 yong4', '不用', true],
    ['yi2 ding4', 'yi1 ding4', '一定', true],
    ['yi4 bian1', 'yi1 bian1', '一边', true],
    ['tong3 yi2 xing4', 'tong3 yi1 xing4', '统一性', false],
    ['yi2 yuan4', 'yi1 yuan4', '医院', false],
    ['kan4 yi5 kan4', 'kan4 yi1 kan4', '看一看', true],
    ['peng2 you3', 'peng2 you5', '朋友', true],
  ])('%s vs %s (%s) -> %s', (input, numbered, hanzi, ok) => {
    expect(grade(input, numbered, hanzi)).toBe(ok);
  });

  it('without the word, only third-tone sandhi applies', () => {
    expect(grade('ni2 hao3', 'ni3 hao3')).toBe(true);
    expect(grade('yi2 ding4', 'yi1 ding4')).toBe(false);
  });
});
