/**
 * static/js/session/pinyin-format.js: numbered pinyin -> tone marks for
 * display. The cases are shared with tests/test_pinyin_format.py.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  formatPinyin,
  numberedToMarked,
  hasNumberedPinyin,
} from '../../static/js/session/pinyin-format.js';

const CASES = JSON.parse(
  readFileSync(join(process.cwd(), 'tests/fixtures/pinyin_format/cases.json'), 'utf-8'),
).format;

describe('formatPinyin (shared cases)', () => {
  it.each(CASES)('%j -> %j', (raw, expected) => {
    expect(formatPinyin(raw)).toBe(expected);
  });

  it.each(CASES)('is idempotent on %j', (_raw, expected) => {
    expect(formatPinyin(expected)).toBe(expected);
  });
});

describe('numberedToMarked', () => {
  it('converts in place and leaves surrounding text', () => {
    expect(numberedToMarked(null)).toBe(null);
    expect(numberedToMarked('一 bi3 笔')).toBe('一 bǐ 笔');
    expect(numberedToMarked('bi3, di1')).toBe('bǐ, dī');
  });
});

describe('hasNumberedPinyin', () => {
  it('detects numbered syllables only', () => {
    expect(hasNumberedPinyin('bian4 de2')).toBe(true);
    expect(hasNumberedPinyin('lu:3')).toBe(true);
    expect(hasNumberedPinyin('biàn dé')).toBe(false);
    expect(hasNumberedPinyin('mp3')).toBe(false);
    expect(hasNumberedPinyin('きょう')).toBe(false);
    expect(hasNumberedPinyin(null)).toBe(false);
  });

  it('keeps a parenthesis that is not a numbered duplicate', () => {
    expect(formatPinyin('zhāng (classifier)')).toBe('zhāng (classifier)');
  });
});
