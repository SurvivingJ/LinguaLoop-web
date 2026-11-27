// static/js/particles/conjugate.js
// Japanese verb and adjective conjugation for the endless conjugation drill.
// A word is {d: dictionary form, k: hiragana reading, c: class}; classes are
// godan | ichidan | suru | kuru for verbs and i | na for adjectives. Every
// function returns the form for both spellings, so 書く / かく give
// {kanji: ['書いて'], kana: ['かいて']}. The first entry is the canonical one;
// later entries are accepted alternatives.

const ROWS = {
  う: ['わ', 'い', 'う', 'え', 'お'],
  く: ['か', 'き', 'く', 'け', 'こ'],
  ぐ: ['が', 'ぎ', 'ぐ', 'げ', 'ご'],
  す: ['さ', 'し', 'す', 'せ', 'そ'],
  つ: ['た', 'ち', 'つ', 'て', 'と'],
  ぬ: ['な', 'に', 'ぬ', 'ね', 'の'],
  ぶ: ['ば', 'び', 'ぶ', 'べ', 'ぼ'],
  む: ['ま', 'み', 'む', 'め', 'も'],
  る: ['ら', 'り', 'る', 'れ', 'ろ'],
};
const TE = {
  う: 'って',
  つ: 'って',
  る: 'って',
  む: 'んで',
  ぶ: 'んで',
  ぬ: 'んで',
  く: 'いて',
  ぐ: 'いで',
  す: 'して',
};

export const VERB_FORMS = [
  { id: 'masu', label: 'ます form', hint: 'polite', guide: 'masu' },
  { id: 'masen', label: 'ません', hint: 'polite negative', guide: 'masu' },
  { id: 'mashita', label: 'ました', hint: 'polite past', guide: 'masu' },
  { id: 'te', label: 'て form', hint: 'and / request', guide: 'te' },
  { id: 'ta', label: 'た form', hint: 'plain past', guide: 'ta' },
  { id: 'nai', label: 'ない form', hint: 'plain negative', guide: 'nai' },
  { id: 'nakatta', label: 'なかった', hint: 'plain past negative', guide: 'nakatta' },
  { id: 'tai', label: 'たい', hint: 'want to', guide: 'tai' },
  { id: 'tari', label: 'たり', hint: 'doing things like', guide: 'tari' },
  { id: 'tara', label: 'たら', hint: 'if / when', guide: 'tara' },
  { id: 'ba', label: 'ば', hint: 'if', guide: 'ba' },
  { id: 'volitional', label: 'Volitional', hint: "let's / I'll", guide: 'volitional' },
  { id: 'potential', label: 'Potential', hint: 'can do', guide: 'potential' },
  { id: 'passive', label: 'Passive', hint: 'is done', guide: 'passive' },
  { id: 'causative', label: 'Causative', hint: 'make / let do', guide: 'causative' },
  {
    id: 'causative_passive',
    label: 'Causative-passive',
    hint: 'be made to do',
    guide: 'causative-passive',
  },
  { id: 'imperative', label: 'Imperative', hint: 'do it!', guide: 'imperative' },
  { id: 'prohibitive', label: 'Prohibitive', hint: "don't!", guide: 'prohibitive' },
];
export const ADJ_FORMS = [
  { id: 'adj_neg', label: 'Negative', hint: 'is not', guide: 'i-adjectives' },
  { id: 'adj_past', label: 'Past', hint: 'was', guide: 'i-adjectives' },
  { id: 'adj_past_neg', label: 'Past negative', hint: 'was not', guide: 'i-adjectives' },
  { id: 'adj_te', label: 'て form', hint: 'and', guide: 'i-adjectives' },
  { id: 'adj_adv', label: 'Adverb', hint: '-ly', guide: 'i-adjectives' },
  { id: 'adj_ba', label: 'Conditional', hint: 'if it is', guide: 'ba' },
  { id: 'adj_tara', label: 'たら', hint: 'if / when it is', guide: 'tara' },
];
export const FORMS = Object.fromEntries([...VERB_FORMS, ...ADJ_FORMS].map((f) => [f.id, f]));

// Verbs with no natural potential / passive / causative / command forms: the
// drill only asks their basic forms.
const BASIC_ONLY = new Set([
  'ある',
  '有る',
  '在る',
  'できる',
  '出来る',
  '分かる',
  'わかる',
  '見える',
  '聞こえる',
  '要る',
]);
const BASIC_FORMS = new Set([
  'masu',
  'masen',
  'mashita',
  'te',
  'ta',
  'nai',
  'nakatta',
  'tari',
  'tara',
  'ba',
]);

export const isVerb = (w) => ['godan', 'ichidan', 'suru', 'kuru'].includes(w.c);

/** Forms the drill may ask for a word. */
export function formsFor(word) {
  if (!isVerb(word)) return ADJ_FORMS.map((f) => f.id);
  if (BASIC_ONLY.has(word.d))
    return VERB_FORMS.filter((f) => BASIC_FORMS.has(f.id)).map((f) => f.id);
  return VERB_FORMS.map((f) => f.id);
}

const both = (word, fn) => ({ kanji: fn(word.d, false), kana: fn(word.k, true) });
const uniq = (list) => list.filter((x, i) => x && list.indexOf(x) === i);

// --- verbs ------------------------------------------------------------------
// Each builder takes the dictionary string (either spelling) and returns a
// list of forms. `kana` is true for the reading, where 来る's stem vowel shows.

function godan(s, form, iku) {
  const last = s[s.length - 1];
  const stem = s.slice(0, -1);
  const row = ROWS[last];
  if (!row) return [];
  const [a, i, , e, o] = row;
  // 行く (and its compounds) take って; 問う / 請う are not in the word lists.
  const te = iku ? 'って' : TE[last];
  const ta = te.replace('て', 'た').replace('で', 'だ');
  switch (form) {
    case 'masu':
      return [stem + i + 'ます'];
    case 'masen':
      return [stem + i + 'ません'];
    case 'mashita':
      return [stem + i + 'ました'];
    case 'tai':
      return [stem + i + 'たい'];
    case 'te':
      return [stem + te];
    case 'ta':
      return [stem + ta];
    case 'tari':
      return [stem + ta + 'り'];
    case 'tara':
      return [stem + ta + 'ら'];
    case 'nai':
      return [stem + a + 'ない'];
    case 'nakatta':
      return [stem + a + 'なかった'];
    case 'ba':
      return [stem + e + 'ば'];
    case 'volitional':
      return [stem + o + 'う'];
    case 'potential':
      return [stem + e + 'る'];
    case 'passive':
      return [stem + a + 'れる'];
    case 'causative':
      return [stem + a + 'せる'];
    case 'causative_passive':
      // 話す has no short form (話さされる is not used).
      return last === 'す' ? [stem + a + 'せられる'] : [stem + a + 'される', stem + a + 'せられる'];
    case 'imperative':
      return [stem + e];
    case 'prohibitive':
      return [s + 'な'];
    default:
      return [];
  }
}

function ichidan(s, form) {
  const stem = s.slice(0, -1);
  switch (form) {
    case 'masu':
      return [stem + 'ます'];
    case 'masen':
      return [stem + 'ません'];
    case 'mashita':
      return [stem + 'ました'];
    case 'tai':
      return [stem + 'たい'];
    case 'te':
      return [stem + 'て'];
    case 'ta':
      return [stem + 'た'];
    case 'tari':
      return [stem + 'たり'];
    case 'tara':
      return [stem + 'たら'];
    case 'nai':
      return [stem + 'ない'];
    case 'nakatta':
      return [stem + 'なかった'];
    case 'ba':
      return [stem + 'れば'];
    case 'volitional':
      return [stem + 'よう'];
    case 'potential':
      return [stem + 'られる', stem + 'れる'];
    case 'passive':
      return [stem + 'られる'];
    case 'causative':
      return [stem + 'させる'];
    case 'causative_passive':
      return [stem + 'させられる'];
    // くれる is the one ichidan verb whose command drops ろ.
    case 'imperative':
      return /(く|呉)れる$/.test(s) && s.length <= 3 ? [stem] : [stem + 'ろ'];
    case 'prohibitive':
      return [s + 'な'];
    default:
      return [];
  }
}

const SURU = {
  masu: ['します'],
  masen: ['しません'],
  mashita: ['しました'],
  tai: ['したい'],
  te: ['して'],
  ta: ['した'],
  tari: ['したり'],
  tara: ['したら'],
  nai: ['しない'],
  nakatta: ['しなかった'],
  ba: ['すれば'],
  volitional: ['しよう'],
  potential: ['できる'],
  passive: ['される'],
  causative: ['させる'],
  causative_passive: ['させられる'],
  imperative: ['しろ', 'せよ'],
  prohibitive: ['するな'],
};
// 来る: the kanji spelling keeps 来; the reading changes its vowel.
const KURU = {
  masu: ['き', 'ます'],
  masen: ['き', 'ません'],
  mashita: ['き', 'ました'],
  tai: ['き', 'たい'],
  te: ['き', 'て'],
  ta: ['き', 'た'],
  tari: ['き', 'たり'],
  tara: ['き', 'たら'],
  nai: ['こ', 'ない'],
  nakatta: ['こ', 'なかった'],
  ba: ['く', 'れば'],
  volitional: ['こ', 'よう'],
  potential: ['こ', 'られる'],
  passive: ['こ', 'られる'],
  causative: ['こ', 'させる'],
  causative_passive: ['こ', 'させられる'],
  imperative: ['こ', 'い'],
  prohibitive: ['く', 'るな'],
};

function suru(s, form) {
  const head = s.slice(0, -2);
  return (SURU[form] || []).map((tail) => head + tail);
}

function kuru(s, form, kana) {
  const rule = KURU[form];
  if (!rule) return [];
  const head = s.slice(0, -2);
  const usesKanji = !kana && s[s.length - 2] === '来';
  const out = [head + (usesKanji ? '来' : rule[0]) + rule[1]];
  if (form === 'potential') out.push(head + (usesKanji ? '来' : 'こ') + 'れる');
  return out;
}

function verbForm(cls, s, form, kana, iku) {
  if (cls === 'godan') {
    // ある: the negative is ない, not あらない.
    if (/^(ある|有る|在る)$/.test(s) && form === 'nai') return ['ない'];
    if (/^(ある|有る|在る)$/.test(s) && form === 'nakatta') return ['なかった'];
    return godan(s, form, iku);
  }
  if (cls === 'ichidan') return ichidan(s, form);
  if (cls === 'suru') return suru(s, form);
  if (cls === 'kuru') return kuru(s, form, kana);
  return [];
}

// --- adjectives -------------------------------------------------------------
function iAdj(s, form) {
  // いい conjugates on よ-.
  let stem = s.slice(0, -1);
  if (s === 'いい' || s === 'かっこいい' || s === '格好いい') stem = s.slice(0, -2) + 'よ';
  switch (form) {
    case 'adj_neg':
      return [stem + 'くない'];
    case 'adj_past':
      return [stem + 'かった'];
    case 'adj_past_neg':
      return [stem + 'くなかった'];
    case 'adj_te':
      return [stem + 'くて'];
    case 'adj_adv':
      return [stem + 'く'];
    case 'adj_ba':
      return [stem + 'ければ'];
    case 'adj_tara':
      return [stem + 'かったら'];
    default:
      return [];
  }
}

function naAdj(s, form) {
  switch (form) {
    case 'adj_neg':
      return [s + 'じゃない', s + 'ではない'];
    case 'adj_past':
      return [s + 'だった'];
    case 'adj_past_neg':
      return [s + 'じゃなかった', s + 'ではなかった'];
    case 'adj_te':
      return [s + 'で'];
    case 'adj_adv':
      return [s + 'に'];
    case 'adj_ba':
      return [s + 'なら', s + 'ならば', s + 'であれば'];
    case 'adj_tara':
      return [s + 'だったら'];
    default:
      return [];
  }
}

function formOf(cls, s, form, kana, iku) {
  if (cls === 'i') return iAdj(s, form);
  if (cls === 'na') return naAdj(s, form);
  return verbForm(cls, s, form, kana, iku);
}

/** {kanji: [...], kana: [...]} for a word and form id; empty lists when the form does not exist. */
export function conjugate(word, form, cls = word.c) {
  // 行く and its compounds (持って行く) take って; decided on the dictionary
  // spelling so the reading follows it.
  const iku = /行く$/.test(word.d) || word.d === 'いく' || word.d === 'ゆく';
  return both(word, (s, kana) => uniq(formOf(cls, s, form, kana, iku)));
}

/** Every spelling the drill accepts as the answer. */
export function acceptedAnswers(word, form) {
  const r = conjugate(word, form);
  return uniq([...r.kanji, ...r.kana]);
}

// --- wrong answers ------------------------------------------------------------
const SIBLINGS = {
  masu: ['tai', 'masen', 'mashita'],
  masen: ['masu', 'nai', 'mashita'],
  mashita: ['masu', 'ta', 'masen'],
  te: ['ta', 'tari', 'masu'],
  ta: ['te', 'tara', 'mashita'],
  tari: ['tara', 'ta', 'te'],
  tara: ['tari', 'ba', 'ta'],
  nai: ['nakatta', 'masen', 'prohibitive'],
  nakatta: ['nai', 'ta', 'masen'],
  tai: ['masu', 'volitional', 'te'],
  ba: ['tara', 'potential', 'imperative'],
  volitional: ['imperative', 'masu', 'potential'],
  potential: ['passive', 'causative', 'ba'],
  passive: ['potential', 'causative', 'causative_passive'],
  causative: ['passive', 'causative_passive', 'potential'],
  causative_passive: ['causative', 'passive', 'potential'],
  imperative: ['volitional', 'prohibitive', 'ba'],
  prohibitive: ['imperative', 'nai', 'volitional'],
  adj_neg: ['adj_past_neg', 'adj_adv', 'adj_past'],
  adj_past: ['adj_past_neg', 'adj_tara', 'adj_te'],
  adj_past_neg: ['adj_neg', 'adj_past', 'adj_te'],
  adj_te: ['adj_adv', 'adj_past', 'adj_neg'],
  adj_adv: ['adj_te', 'adj_neg', 'adj_ba'],
  adj_ba: ['adj_tara', 'adj_te', 'adj_adv'],
  adj_tara: ['adj_ba', 'adj_past', 'adj_te'],
};
const WRONG_CLASS = {
  godan: ['ichidan'],
  ichidan: ['godan'],
  suru: [],
  kuru: ['godan'],
  i: ['na'],
  na: ['i'],
};

/**
 * Up to `count` wrong answers a learner could plausibly produce, in the kanji
 * spelling: the form built with the wrong verb group's rule (the real
 * mistake), then with the wrong sound change, then neighbouring forms.
 */
export function distractors(word, form, count = 3, rng = Math.random) {
  const right = new Set(acceptedAnswers(word, form));
  const out = [];
  const add = (list) => {
    for (const x of list || []) {
      if (x && !right.has(x) && !out.includes(x)) out.push(x);
    }
  };
  // 1. Wrong group (ichidan rule on a godan verb and the reverse, な rule on an い adjective).
  for (const cls of WRONG_CLASS[word.c] || []) {
    const fake = conjugate({ ...word, c: cls }, form, cls).kanji;
    add(fake.slice(0, 1));
  }
  // 2. Wrong sound change in the て / た family.
  if (word.c === 'godan' && ['te', 'ta', 'tari', 'tara'].includes(form)) {
    const stem = word.d.slice(0, -1);
    const tail = { te: '', ta: '', tari: 'り', tara: 'ら' }[form];
    const endings =
      form === 'te' ? ['って', 'んで', 'いて', 'して'] : ['った', 'んだ', 'いた', 'した'];
    add(shuffle(endings, rng).map((e) => stem + e + tail));
  }
  // 3. Neighbouring forms of the same word.
  const near = [];
  for (const sib of SIBLINGS[form] || []) near.push(...conjugate(word, sib).kanji.slice(0, 1));
  add(shuffle(near, rng));
  // 4. Any other form, so there are always `count` options.
  if (out.length < count) {
    const rest = formsFor(word).filter((f) => f !== form);
    add(shuffle(rest, rng).map((f) => conjugate(word, f).kanji[0]));
  }
  return out.slice(0, count);
}

function shuffle(list, rng) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
