// static/js/grammar/text.js
// Grammar drills: text helpers with no DOM. Options, blanks, pinyin alignment.
// Item and guide formats: data/grammar_drills/zh/SPEC.md.

export const BLANK = '___';
/** An option part meaning "nothing goes in this blank". */
export const EMPTY = '∅';

const HANZI = /[一-鿿]/;
const LATIN = /[A-Za-z\u00C0-\u024F]/;
const PY_SPLIT = /[\s，。？！、；：“”‘’（）《》…—,.?!;:]+/;

export const isHanzi = (ch) => HANZI.test(ch);

/** "wǒ mǎi le" -> ['wǒ', 'mǎi', 'le'] (punctuation in the pinyin is dropped). */
export function syllables(py) {
  return String(py || '')
    .trim()
    .split(PY_SPLIT)
    .filter(Boolean);
}

/**
 * One entry per character of `text`: { ch, py }. Hanzi take the syllables of
 * `py` in order, everything else gets ''. Null when the pinyin does not have
 * exactly one syllable per Hanzi (then no pinyin can be shown for the text).
 */
export function rubyPairs(text, py) {
  const chars = Array.from(String(text || ''));
  const syls = syllables(py);
  const hanzi = chars.filter(isHanzi).length;
  if (!hanzi || syls.length !== hanzi) return null;
  let i = 0;
  return chars.map((ch) => ({ ch, py: isHanzi(ch) ? syls[i++] : '' }));
}

/** 'a|b' -> ['a', 'b']. */
export function optionParts(opt) {
  return String(opt == null ? '' : opt).split('|');
}

/** How an option reads on a button: ∅ -> the "(nothing)" label, 'a|b' -> 'a … b'. */
export function displayOption(opt, nothingLabel) {
  return optionParts(opt)
    .map((p) => (p === EMPTY ? nothingLabel || '(nothing)' : p))
    .join(' … ');
}

/** The question with `opt` written into its blanks (extra blanks stay). */
export function fillCloze(q, opt) {
  let out = String(q || '');
  optionParts(opt).forEach((p) => {
    out = out.replace(BLANK, p === EMPTY ? '' : p);
  });
  return out;
}

/**
 * A cloze question cut at its blanks, each piece with the pinyin it has in the
 * full sentence: [{ text, pairs } | { blank: true, fill, pairs }]. `fill` is
 * what the right option puts there ('' for ∅). `pairs` is null throughout when
 * the item has no usable pinyin, `zh` is not the question filled in, or the
 * question or its answer is itself pinyin.
 */
export function clozeSegments(item) {
  const pieces = String(item.q || '').split(BLANK);
  const right = optionParts(item.opts ? item.opts[item.a] : '');
  const filled = fillCloze(item.q, item.opts ? item.opts[item.a] : '');
  // A question or answer that spells out pinyin (generated tone drills) is
  // asking for a reading: ruby over its characters would give the answer away.
  const all = filled === item.zh && !LATIN.test(filled) ? rubyPairs(item.zh, item.py) : null;
  let pos = 0;
  const cut = (text) => {
    const n = Array.from(text).length;
    const pairs = all ? all.slice(pos, pos + n) : null;
    pos += n;
    return pairs;
  };
  const segs = [];
  pieces.forEach((text, k) => {
    if (text) segs.push({ text, pairs: cut(text) });
    if (k < pieces.length - 1) {
      const fill = right[k] == null || right[k] === EMPTY ? '' : right[k];
      segs.push({ blank: true, fill, pairs: cut(fill) });
    }
  });
  return segs;
}

/**
 * Pinyin per tile, for tiles that join to the sentence (punctuation removed):
 * ['wǒ', 'míng tiān', ...]. Null when the syllable count does not fit.
 */
export function tokenPinyin(tokens, py) {
  const syls = syllables(py);
  const need = (tokens || []).reduce((n, t) => n + Array.from(t).filter(isHanzi).length, 0);
  if (!need || need !== syls.length) return null;
  let i = 0;
  return tokens.map((t) => {
    const n = Array.from(t).filter(isHanzi).length;
    const part = syls.slice(i, i + n).join(' ');
    i += n;
    return part;
  });
}

/** character -> its most frequent syllable across the items' sentences. */
export function readingMap(items) {
  const counts = new Map();
  const add = (text, py) => {
    (rubyPairs(text, py) || []).forEach(({ ch, py: syl }) => {
      if (!syl) return;
      if (!counts.has(ch)) counts.set(ch, new Map());
      const m = counts.get(ch);
      const key = syl.toLowerCase();
      m.set(key, (m.get(key) || 0) + 1);
    });
  };
  (items || []).forEach((it) => {
    add(it.zh, it.py);
    if (it.src) add(it.src, it.src_py);
    if (it.s && it.s_py) add(it.s, it.s_py);
  });
  const out = new Map();
  counts.forEach((m, ch) => {
    let best = '';
    let top = 0;
    m.forEach((n, syl) => {
      if (n > top) {
        top = n;
        best = syl;
      }
    });
    out.set(ch, best);
  });
  return out;
}

/** Pinyin for `text` from a readingMap, or null when a character is unknown. */
export function guessPinyin(text, map) {
  const out = [];
  for (const ch of Array.from(String(text || ''))) {
    if (!isHanzi(ch)) continue;
    const syl = map && map.get(ch);
    if (!syl) return null;
    out.push(syl);
  }
  return out.length ? out.join(' ') : null;
}

/** Median of a list of numbers (0 for none). */
export function median(nums) {
  const a = (nums || []).filter((n) => Number.isFinite(n)).sort((x, y) => x - y);
  if (!a.length) return 0;
  const mid = a.length >> 1;
  return a.length % 2 ? a[mid] : (a[mid - 1] + a[mid]) / 2;
}

/** 2140 -> '2.1' (seconds, one decimal). */
export function seconds(ms) {
  return (Math.max(0, ms) / 1000).toFixed(1);
}
