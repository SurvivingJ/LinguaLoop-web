/**
 * Unit tests for static/js/session/sentences.js (TASK-911): server sentence
 * spans drive the preview; the client split on 。！？!? is the fallback (with a
 * console.warn); the L1 reference line is hidden by default and never rendered
 * in produce mode.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  clientSplitSentences,
  normalizeServerSentences,
  fetchTestSentences,
  resolveSentences,
  renderSentenceBlocks,
  setReferencesVisible,
  hasVisibleReferences,
  hasTokenSpans,
} from '../../static/js/session/sentences.js';

const TRANSCRIPT = '猫がいる。犬もいる！鳥は？';
const SERVER = {
  sentences: [
    {
      idx: 0,
      l2_text: '猫がいる。',
      char_start: 0,
      char_end: 5,
      token_start: 0,
      token_end: 4,
      reference: { l1_text: 'There is a cat.', tightness: 0.9 },
    },
    {
      idx: 1,
      l2_text: '犬もいる！',
      char_start: 5,
      char_end: 10,
      token_start: 4,
      token_end: 8,
      reference: null,
    },
    {
      idx: 2,
      l2_text: '鳥は？',
      char_start: 10,
      char_end: 13,
      token_start: 8,
      token_end: 11,
      reference: { l1_text: 'And birds?', tightness: 0.7 },
    },
  ],
};
const TOKEN_MAP = [
  ['猫', 1],
  ['が', null],
  ['いる', 2],
  ['。', null],
  ['犬', 3],
  ['も', null],
  ['いる', 2],
  ['！', null],
  ['鳥', 4],
  ['は', null],
  ['？', null],
];

let warnSpy;
beforeEach(() => {
  warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
});
afterEach(() => {
  warnSpy.mockRestore();
});

describe('clientSplitSentences', () => {
  it('splits on 。！？!? keeping terminators and spans into the original string', () => {
    const out = clientSplitSentences(TRANSCRIPT);
    expect(out.map((s) => s.l2_text)).toEqual(['猫がいる。', '犬もいる！', '鳥は？']);
    out.forEach((s) => expect(TRANSCRIPT.slice(s.char_start, s.char_end)).toBe(s.l2_text));
    expect(out[0].reference).toBeNull();
    expect(out[0].token_start).toBeNull();
  });

  it('keeps a trailing fragment without a terminator and trims whitespace', () => {
    const out = clientSplitSentences('Hi there! And then  ');
    expect(out.map((s) => s.l2_text)).toEqual(['Hi there!', 'And then']);
    expect(clientSplitSentences('')).toEqual([]);
    expect(clientSplitSentences(null)).toEqual([]);
  });
});

describe('normalizeServerSentences', () => {
  it('returns null for no rows and unwraps a {data:{...}} envelope', () => {
    expect(normalizeServerSentences({ sentences: [] })).toBeNull();
    expect(normalizeServerSentences(null)).toBeNull();
    const rows = normalizeServerSentences({ data: SERVER });
    expect(rows).toHaveLength(3);
    expect(rows[0].reference.l1_text).toBe('There is a cat.');
  });

  it('fills withheld l2_text from char spans when the transcript is at hand', () => {
    const withheld = { sentences: SERVER.sentences.map(({ l2_text: _omit, ...r }) => r) };
    const rows = normalizeServerSentences(withheld, TRANSCRIPT);
    expect(rows.map((s) => s.l2_text)).toEqual(['猫がいる。', '犬もいる！', '鳥は？']);
    const noText = normalizeServerSentences(withheld);
    expect(noText[0].l2_text).toBeNull();
  });
});

describe('fetchTestSentences', () => {
  it('requests the endpoint with mode/l1 and returns normalised rows', async () => {
    const fetchImpl = vi.fn(async () => ({ ok: true, json: async () => SERVER }));
    const rows = await fetchTestSentences('cats', { mode: 'produce', l1: 'en', fetchImpl });
    expect(fetchImpl).toHaveBeenCalledWith('/api/tests/cats/sentences?l1=en&mode=produce');
    expect(rows).toHaveLength(3);
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it('returns null with a console.warn on 404', async () => {
    const fetchImpl = vi.fn(async () => ({ ok: false, status: 404 }));
    expect(await fetchTestSentences('cats', { fetchImpl })).toBeNull();
    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(String(warnSpy.mock.calls[0][0])).toMatch(/404/);
  });

  it('returns null with a console.warn when the endpoint has no rows', async () => {
    const fetchImpl = vi.fn(async () => ({ ok: true, json: async () => ({ sentences: [] }) }));
    expect(await fetchTestSentences('cats', { fetchImpl })).toBeNull();
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it('returns null with a console.warn when fetch throws', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error('offline');
    });
    expect(await fetchTestSentences('cats', { fetchImpl })).toBeNull();
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });
});

describe('resolveSentences', () => {
  it('prefers server rows', () => {
    const rows = normalizeServerSentences(SERVER);
    const r = resolveSentences(TRANSCRIPT, rows);
    expect(r.source).toBe('server');
    expect(r.sentences).toBe(rows);
  });

  it('falls back to the client split, never empty for a real transcript', () => {
    const r = resolveSentences(TRANSCRIPT, null);
    expect(r.source).toBe('client');
    expect(r.sentences.map((s) => s.l2_text)).toEqual(['猫がいる。', '犬もいる！', '鳥は？']);
    expect(warnSpy).toHaveBeenCalled();
  });
});

describe('renderSentenceBlocks', () => {
  let el;
  beforeEach(() => {
    el = document.createElement('div');
    document.body.appendChild(el);
  });
  afterEach(() => {
    el.remove();
  });

  it('renders one block per sentence using server spans, references hidden by default', () => {
    const rows = normalizeServerSentences(SERVER);
    renderSentenceBlocks(el, rows);
    const blocks = el.querySelectorAll('.ll-sentence');
    expect(blocks).toHaveLength(3);
    expect(blocks[1].dataset.sentenceIdx).toBe('1');
    expect(blocks[0].querySelector('.ll-sentence-text').textContent).toBe('猫がいる。');
    const refs = el.querySelectorAll('.ll-sentence-ref');
    expect(refs).toHaveLength(2); // sentence 1 has no reference
    refs.forEach((r) => expect(r.hidden).toBe(true));
    expect(refs[0].textContent).toBe('There is a cat.');
  });

  it('toggle reveals and hides the reference lines', () => {
    renderSentenceBlocks(el, normalizeServerSentences(SERVER));
    expect(setReferencesVisible(el, true)).toBe(true);
    el.querySelectorAll('.ll-sentence-ref').forEach((r) => expect(r.hidden).toBe(false));
    setReferencesVisible(el, false);
    el.querySelectorAll('.ll-sentence-ref').forEach((r) => expect(r.hidden).toBe(true));
  });

  it('never renders a reference line in produce mode, even when asked to show them', () => {
    const rows = normalizeServerSentences(SERVER);
    renderSentenceBlocks(el, rows, { mode: 'produce', showReferences: true });
    expect(el.querySelectorAll('.ll-sentence')).toHaveLength(3);
    expect(el.querySelectorAll('.ll-sentence-ref')).toHaveLength(0);
    expect(hasVisibleReferences(rows, 'produce')).toBe(false);
    expect(hasVisibleReferences(rows, null)).toBe(true);
  });

  it('builds clickable word spans from the token map inside each sentence', () => {
    const rows = normalizeServerSentences(SERVER);
    expect(hasTokenSpans(rows)).toBe(true);
    renderSentenceBlocks(el, rows, { tokenMap: TOKEN_MAP });
    const blocks = el.querySelectorAll('.ll-sentence');
    expect(blocks[0].querySelector('.ll-sentence-text').textContent).toBe('猫がいる。');
    const clickable = blocks[0].querySelectorAll('.word-clickable');
    expect(Array.from(clickable).map((s) => s.dataset.senseId)).toEqual(['1', '2']);
    expect(blocks[2].querySelectorAll('.word-clickable')).toHaveLength(1);
    // reference lines still present (hidden) alongside the clickable view
    expect(el.querySelectorAll('.ll-sentence-ref')).toHaveLength(2);
  });

  it('client-split rows render plain text via renderText and escape HTML', () => {
    const rows = clientSplitSentences('a<b>。c。');
    expect(hasTokenSpans(rows)).toBe(false);
    renderSentenceBlocks(el, rows, { tokenMap: TOKEN_MAP });
    expect(el.querySelectorAll('.ll-sentence')).toHaveLength(2);
    expect(el.querySelector('.ll-sentence-text').innerHTML).toBe('a&lt;b&gt;。');
    renderSentenceBlocks(el, rows, { renderText: (t) => '<b>' + t.length + '</b>' });
    expect(el.querySelector('.ll-sentence-text').innerHTML).toBe('<b>5</b>');
  });
});
