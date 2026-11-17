/**
 * New-word drill: a Chinese reading is shown in tone-marked pinyin only. The
 * server sends {shown: 'biàn dé', numbered: 'bian4 de2'}; the numbered form is
 * for grading and must not be displayed next to it.
 */

import { describe, it, expect } from 'vitest';
import { buildItem, readingText } from '../../static/js/session/players/intro_drill.js';

const zhWord = {
  sense_id: 1,
  lemma: '变得',
  gloss: 'to become',
  pos: 'verb',
  reading: { shown: 'biàn dé', numbered: 'bian4 de2' },
};

describe('readingText', () => {
  it('Chinese: tone marks only, without the numbered duplicate', () => {
    expect(readingText(zhWord, 'zh')).toBe('biàn dé');
  });

  it('Chinese: a numbered `shown` is converted', () => {
    expect(readingText({ reading: { shown: 'bi3', numbered: 'bi3' } }, 'zh')).toBe('bǐ');
    expect(readingText({ reading: { shown: 'lu:3 se4', numbered: 'lu:3 se4' } }, 'zh')).toBe(
      'lǚ sè',
    );
  });

  it('Japanese: the kana reading as given', () => {
    expect(readingText({ reading: { shown: 'きょう', numbered: null } }, 'ja')).toBe('きょう');
  });

  it('no reading: empty', () => {
    expect(readingText({ reading: null }, 'zh')).toBe('');
  });
});

describe('def_mc item shows the tone-marked reading under the word', () => {
  it('zh', () => {
    const block = {
      lang: 'zh',
      words: [
        zhWord,
        { sense_id: 2, lemma: '木头', gloss: 'wood', pos: 'noun' },
        { sense_id: 3, lemma: '石头', gloss: 'stone', pos: 'noun' },
        { sense_id: 4, lemma: '水', gloss: 'water', pos: 'noun' },
      ],
    };
    const item = buildItem({ word: zhWord, format: 'def_mc' }, block, new Map());
    expect(item.sub).toBe('biàn dé');
  });
});
