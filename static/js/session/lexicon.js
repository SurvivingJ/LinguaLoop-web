// static/js/session/lexicon.js
// Small word helpers shared by the multiple-choice builders (test prestudy,
// new-word drill). Mirrored in Python by services/vocabulary/lexicon.py and in
// SQL by public.pos_class(); tests/fixtures/lexicon/cases.json pins all three.

const POS_CLASSES = {
  noun: ['noun', 'n', 'nr', 'ns', 'nt', 'nz', 'nw', 'ng', 'nrt', 'nrfg', 'vn', 'an', 'propn', '名词', '名詞'],
  verb: ['verb', 'v', 'vd', 'vg', 'vi', 'aux', '动词', '動詞'],
  adj: ['adjective', 'adj', 'a', 'ag', '形容词', '形容詞', '形状詞'],
  adv: ['adverb', 'adv', 'd', 'ad', '副词', '副詞'],
  measure: ['measure_word', 'q', '量词', '助数詞'],
  pron: ['pronoun', 'pron', 'r', '代词', '代名詞'],
};
const POS_LOOKUP = new Map();
for (const [cls, tags] of Object.entries(POS_CLASSES)) for (const t of tags) POS_LOOKUP.set(t, cls);

/**
 * Coarse part-of-speech class ('noun', 'verb', 'adj', 'adv', 'measure',
 * 'pron', or the lower-cased tag itself). Dictionary tags are mixed: the same
 * class appears as "noun", "n", "名词", "NOUN", "名詞" and fine tags like "nr".
 */
export function posClass(pos) {
  const t = String(pos == null ? '' : pos).trim().toLowerCase();
  return POS_LOOKUP.get(t) || t;
}

const CJK = /[぀-ヿ㐀-鿿]/u;

/**
 * Hide a word inside its own definition ("宗教改革是…" -> "～是…") so a
 * multiple-choice option or a recall prompt does not contain the answer.
 * CJK/kana words are replaced wherever they appear; spaced-script words only
 * as whole words, case-insensitively.
 */
export function maskHeadword(text, lemma) {
  if (!text || !lemma) return text;
  if (CJK.test(lemma)) return String(text).split(lemma).join('～');
  const esc = String(lemma).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return String(text).replace(new RegExp(`(?<![\\p{L}\\p{N}_])${esc}(?![\\p{L}\\p{N}_])`, 'giu'), '～');
}
