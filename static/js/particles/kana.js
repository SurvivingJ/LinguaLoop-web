// static/js/particles/kana.js
// Typed answers: romaji -> hiragana so a learner can drill without an IME, and
// the comparisons that make "wa" a right answer for は.

const TABLE = {
  a: 'あ',
  i: 'い',
  u: 'う',
  e: 'え',
  o: 'お',
  ka: 'か',
  ki: 'き',
  ku: 'く',
  ke: 'け',
  ko: 'こ',
  sa: 'さ',
  shi: 'し',
  si: 'し',
  su: 'す',
  se: 'せ',
  so: 'そ',
  ta: 'た',
  chi: 'ち',
  ti: 'ち',
  tsu: 'つ',
  tu: 'つ',
  te: 'て',
  to: 'と',
  na: 'な',
  ni: 'に',
  nu: 'ぬ',
  ne: 'ね',
  no: 'の',
  ha: 'は',
  hi: 'ひ',
  fu: 'ふ',
  hu: 'ふ',
  he: 'へ',
  ho: 'ほ',
  ma: 'ま',
  mi: 'み',
  mu: 'む',
  me: 'め',
  mo: 'も',
  ya: 'や',
  yu: 'ゆ',
  yo: 'よ',
  ra: 'ら',
  ri: 'り',
  ru: 'る',
  re: 'れ',
  ro: 'ろ',
  wa: 'わ',
  wo: 'を',
  ga: 'が',
  gi: 'ぎ',
  gu: 'ぐ',
  ge: 'げ',
  go: 'ご',
  za: 'ざ',
  ji: 'じ',
  zi: 'じ',
  zu: 'ず',
  ze: 'ぜ',
  zo: 'ぞ',
  da: 'だ',
  di: 'ぢ',
  du: 'づ',
  de: 'で',
  do: 'ど',
  ba: 'ば',
  bi: 'び',
  bu: 'ぶ',
  be: 'べ',
  bo: 'ぼ',
  pa: 'ぱ',
  pi: 'ぴ',
  pu: 'ぷ',
  pe: 'ぺ',
  po: 'ぽ',
  kya: 'きゃ',
  kyu: 'きゅ',
  kyo: 'きょ',
  sha: 'しゃ',
  shu: 'しゅ',
  sho: 'しょ',
  sya: 'しゃ',
  syu: 'しゅ',
  syo: 'しょ',
  cha: 'ちゃ',
  chu: 'ちゅ',
  cho: 'ちょ',
  tya: 'ちゃ',
  tyu: 'ちゅ',
  tyo: 'ちょ',
  nya: 'にゃ',
  nyu: 'にゅ',
  nyo: 'にょ',
  hya: 'ひゃ',
  hyu: 'ひゅ',
  hyo: 'ひょ',
  mya: 'みゃ',
  myu: 'みゅ',
  myo: 'みょ',
  rya: 'りゃ',
  ryu: 'りゅ',
  ryo: 'りょ',
  gya: 'ぎゃ',
  gyu: 'ぎゅ',
  gyo: 'ぎょ',
  ja: 'じゃ',
  ju: 'じゅ',
  jo: 'じょ',
  jya: 'じゃ',
  jyu: 'じゅ',
  jyo: 'じょ',
  zya: 'じゃ',
  zyu: 'じゅ',
  zyo: 'じょ',
  bya: 'びゃ',
  byu: 'びゅ',
  byo: 'びょ',
  pya: 'ぴゃ',
  pyu: 'ぴゅ',
  pyo: 'ぴょ',
  '-': 'ー',
};
const CONSONANTS = 'bcdfghjkmprstwyz';

/**
 * Romaji to hiragana. Text that is already kana passes through. With
 * `final` false (live typing) a trailing lone "n" or an unfinished syllable
 * is kept as typed; with `final` true a trailing "n" becomes ん.
 */
export function romajiToKana(input, final = true) {
  const s = String(input || '').toLowerCase();
  let out = '';
  let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (!/[a-z'-]/.test(c)) {
      out += c;
      i += 1;
      continue;
    }
    if (c === "'") {
      i += 1;
      continue;
    }
    // Doubled consonant -> っ (but nn is ん).
    if (CONSONANTS.includes(c) && s[i + 1] === c) {
      out += 'っ';
      i += 1;
      continue;
    }
    if (c === 't' && s.startsWith('tch', i)) {
      out += 'っ';
      i += 1;
      continue;
    }
    let matched = false;
    for (const len of [3, 2, 1]) {
      const kana = TABLE[s.substr(i, len)];
      if (kana) {
        out += kana;
        i += len;
        matched = true;
        break;
      }
    }
    if (matched) continue;
    if (c === 'n') {
      const next = s[i + 1];
      if (next === undefined) {
        out += final ? 'ん' : 'n';
        i += 1;
      } else if (next === "'") {
        out += 'ん';
        i += 2;
      } else if (next === 'n') {
        // "nn" is ん; in "onna" the second n starts the next syllable.
        out += 'ん';
        i += /[aiueoy]/.test(s[i + 2] || '') ? 1 : 2;
      } else {
        out += 'ん';
        i += 1;
      }
      continue;
    }
    out += c; // unfinished syllable while typing
    i += 1;
  }
  return out;
}

/** Katakana to hiragana. */
export function toHiragana(s) {
  return String(s || '').replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

/** A typed answer in comparable form: NFKC, no spaces, romaji and katakana as hiragana. */
export function normalizeAnswer(s) {
  const text = String(s || '')
    .normalize('NFKC')
    .replace(/[\s。、.,]/g, '');
  return toHiragana(romajiToKana(text, true));
}

// は, へ, を are pronounced わ, え, お as particles: a learner who types the
// sound has recalled the particle.
const SOUND = [
  ['は', 'わ'],
  ['へ', 'え'],
  ['を', 'お'],
];

function soundForm(s) {
  let out = toHiragana(s);
  for (const [written, spoken] of SOUND) out = out.split(written).join(spoken);
  return out;
}

/** True when `typed` is one of `accepted` (kana or kanji strings). */
export function answerMatches(accepted, typed) {
  const raw = String(typed || '')
    .normalize('NFKC')
    .replace(/[\s。、.,]/g, '');
  if (!raw) return false;
  const norm = normalizeAnswer(raw);
  return accepted.some((a) => {
    if (!a) return false;
    if (a === raw) return true;
    const want = toHiragana(a);
    return want === norm || soundForm(want) === soundForm(norm);
  });
}
