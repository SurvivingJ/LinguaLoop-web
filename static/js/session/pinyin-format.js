// static/js/session/pinyin-format.js
// One display form for Chinese pronunciations: pinyin with tone marks.
//
// Stored pronunciations come in three shapes (dim_word_senses.pronunciation,
// dim_classifiers.pinyin_display): tone-marked ("zhāng"), numbered ("bi3",
// "lu:3") and both at once ("biàn dé (bian4 de2)"). `formatPinyin` turns any
// of them into the tone-marked form alone. Anything that is not numbered
// pinyin (kana, English, an already-marked string) comes back unchanged.
//
// Mirror of services/pinyin_format.py; tests/fixtures/pinyin_format/cases.json
// pins both. Display only: answer checking keeps using the numbered form.

const MARKS = {
  a: 'āáǎà',
  e: 'ēéěè',
  i: 'īíǐì',
  o: 'ōóǒò',
  u: 'ūúǔù',
  ü: 'ǖǘǚǜ',
  A: 'ĀÁǍÀ',
  E: 'ĒÉĚÈ',
  I: 'ĪÍǏÌ',
  O: 'ŌÓǑÒ',
  U: 'ŪÚǓÙ',
  Ü: 'ǕǗǙǛ',
};
// Syllabic nasals (m2, n3, ng4, hm5) take a combining mark on the m / n.
const COMBINING = ['̄', '́', '̌', '̀'];

const INITIAL = '(?:zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?';
const FINAL =
  '(?:iang|iong|uang|ueng|üan|ang|eng|ing|ong|ian|iao|uai|uan|üe|ai|ao|an|ei|en|er|ia|ie|in|io|iu|ou|ua|ui|un|uo|ue|ün|ê|a|e|i|o|u|ü)';
const SYLLABLE = new RegExp(`^(?:${INITIAL}${FINAL}|hng|hm|ng|m|n)$`);
// A run of letters ending in a tone digit, optionally followed by an er-hua
// "r" ("dian3r"). Not preceded by a letter, so "mp3" / "Windows10" are
// matched whole and then rejected as non-pinyin.
const TOKEN = /(?<![A-Za-zÜüÊê:])([A-Za-zÜüÊê:]+)([0-5])(r(?![A-Za-z]))?/g;

function normaliseU(letters) {
  return letters.replace(/u:|v/g, 'ü').replace(/U:|V/g, 'Ü');
}

/** Mark one syllable (letters without the digit, ü already normalised). */
function markSyllable(syl, tone) {
  if (tone === 0 || tone === 5) return syl;
  const lower = syl.toLowerCase();
  let idx = lower.search(/[ae]/);
  if (idx < 0) idx = lower.indexOf('ou');
  if (idx < 0) {
    for (let i = lower.length - 1; i >= 0; i--) {
      if ('iouü'.includes(lower[i])) {
        idx = i;
        break;
      }
    }
  }
  if (idx < 0) {
    // m / n / ng / hm / hng: the mark goes on the nasal.
    const n = lower.search(/[mn]/);
    if (n < 0) return syl;
    return (syl.slice(0, n + 1) + COMBINING[tone - 1] + syl.slice(n + 1)).normalize('NFC');
  }
  const ch = syl[idx];
  const marked = MARKS[ch] ? MARKS[ch][tone - 1] : ch;
  return syl.slice(0, idx) + marked + syl.slice(idx + 1);
}

/** Split a letter run into a pinyin syllable plus an optional er-hua "r". */
function parseSyllable(letters) {
  const s = normaliseU(letters);
  const lower = s.toLowerCase();
  // A lone "r" is the er-hua suffix written as its own syllable ("r5").
  if (lower === 'r' || SYLLABLE.test(lower)) return { base: s, r: '' };
  if (lower.length > 1 && lower.endsWith('r') && SYLLABLE.test(lower.slice(0, -1))) {
    return { base: s.slice(0, -1), r: s.slice(-1) };
  }
  return null;
}

/**
 * Numbered pinyin -> tone marks, in place, inside any string. Syllables may be
 * separated by spaces or run together ("bian4de2"). A standalone er-hua "r5"
 * joins the syllable before it. Non-pinyin text is left as it is.
 */
export function numberedToMarked(text) {
  if (text == null) return text;
  const s = String(text);
  if (!/[0-5]/.test(s)) return s;
  let out = '';
  let last = 0;
  TOKEN.lastIndex = 0;
  let m;
  while ((m = TOKEN.exec(s))) {
    const parsed = parseSyllable(m[1]);
    if (!parsed) continue;
    let head = s.slice(last, m.index);
    let body = markSyllable(parsed.base, Number(m[2])) + parsed.r + (m[3] || '');
    // "yi1 dian3 r5": the er-hua suffix belongs to the previous syllable.
    if (parsed.base.toLowerCase() === 'r' && last > 0 && /^\s+$/.test(head)) {
      head = '';
      body = parsed.base;
    }
    out += head + body;
    last = m.index + m[0].length;
  }
  return out + s.slice(last);
}

/** True when `text` has at least one numbered pinyin syllable. */
export function hasNumberedPinyin(text) {
  return text != null && numberedToMarked(text) !== String(text);
}

/**
 * The one form a learner sees: tone-marked pinyin. "biàn dé (bian4 de2)" ->
 * "biàn dé"; "bi3" -> "bǐ"; "zhāng" and "きょう" unchanged; null/'' -> ''.
 */
export function formatPinyin(text) {
  if (text == null) return '';
  const s = String(text).trim();
  const m = s.match(/^(.*?)\s*\(([^()]*)\)$/);
  if (m && hasNumberedPinyin(m[2])) {
    return numberedToMarked(m[1].trim() || m[2].trim());
  }
  return numberedToMarked(s);
}

/**
 * A stored pronunciation as a learner sees it: Chinese (`lang` 'zh' or
 * language id 1) in tone-marked pinyin only, every other language as stored.
 * Mirror of services/pinyin_format.display_pronunciation. Display only.
 */
export function displayPronunciation(text, lang) {
  if (text == null) return '';
  const zh = window.LinguaLanguages.hasFeature(lang, 'pinyin');
  return zh ? formatPinyin(text) : String(text);
}

// Classic (non-module) page scripts such as static/js/prestudy/prestudy.js
// read the same helpers from here once any module has imported this file.
if (typeof window !== 'undefined') {
  window.LinguaPinyin = Object.assign(window.LinguaPinyin || {}, {
    formatPinyin,
    numberedToMarked,
    hasNumberedPinyin,
    displayPronunciation,
  });
}
