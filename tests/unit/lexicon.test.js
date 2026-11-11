/** static/js/session/lexicon.js against the shared fixture (also replayed by tests/test_lexicon.py). */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { posClass, maskHeadword } from '../../static/js/session/lexicon.js';

const cases = JSON.parse(readFileSync(join(process.cwd(), 'tests/fixtures/lexicon/cases.json'), 'utf8'));

describe('posClass', () => {
  it.each(cases.pos_class)('%s -> %s', (tag, expected) => expect(posClass(tag)).toBe(expected));
});

describe('maskHeadword', () => {
  it.each(cases.mask_headword)('%s / %s', (text, lemma, expected) => expect(maskHeadword(text, lemma)).toBe(expected));
});
