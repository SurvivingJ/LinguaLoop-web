/**
 * Shared helpers for the grammar-drill generators: seeded picking, sentence
 * assembly from (Hanzi, pinyin) words, and the cloze / order item builders.
 * Pure data and logic, no DOM.
 */

/** Pick one element. */
export const pick = (rng, arr) => arr[Math.floor(rng() * arr.length)];

/** Integer in [lo, hi]. */
export const int = (rng, lo, hi) => lo + Math.floor(rng() * (hi - lo + 1));

/** True with probability p. */
export const chance = (rng, p) => rng() < p;

/** Fisher-Yates copy. */
export function shuffle(rng, arr) {
  const out = arr.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/** Pick by weight: entries are [weight, value]. */
export function weighted(rng, entries) {
  const total = entries.reduce((s, e) => s + e[0], 0);
  let x = rng() * total;
  for (const [wt, value] of entries) {
    x -= wt;
    if (x < 0) return value;
  }
  return entries[entries.length - 1][1];
}

/** 'zh|py|en...' -> { zh, py, en, x: [further fields] }. */
export function w(s) {
  if (typeof s !== 'string') return s;
  const [zh, py = '', en = '', ...x] = s.split('|');
  return { zh, py, en, x };
}

/** Parse a table: one 'a|b|c' row per line. */
export const rows = (text) =>
  text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => l.split('|'));

/**
 * Join parts into { zh, py }. A part is a { zh, py } word, a 'zh|py' string,
 * or a bare string of punctuation (no pinyin). Empty parts are skipped.
 */
export function join(parts) {
  let zh = '';
  const py = [];
  for (const raw of parts) {
    if (!raw) continue;
    const p = typeof raw === 'string' ? (raw.includes('|') ? w(raw) : { zh: raw, py: '' }) : raw;
    zh += p.zh;
    if (p.py) py.push(p.py);
  }
  return { zh, py: py.join(' ') };
}

/** Pinyin of the characters used to write numbers, clock times and money. */
const NUM_PY = {
  零: 'líng',
  一: 'yī',
  二: 'èr',
  两: 'liǎng',
  三: 'sān',
  四: 'sì',
  五: 'wǔ',
  六: 'liù',
  七: 'qī',
  八: 'bā',
  九: 'jiǔ',
  十: 'shí',
  百: 'bǎi',
  千: 'qiān',
  万: 'wàn',
  亿: 'yì',
  半: 'bàn',
  几: 'jǐ',
  点: 'diǎn',
  分: 'fēn',
  刻: 'kè',
  差: 'chà',
  块: 'kuài',
  毛: 'máo',
  年: 'nián',
  月: 'yuè',
  号: 'hào',
  日: 'rì',
  个: 'gè',
  小: 'xiǎo',
  时: 'shí',
  钟: 'zhōng',
  天: 'tiān',
  岁: 'suì',
  第: 'dì',
  次: 'cì',
  遍: 'biàn',
};

/** Word for a string written only with the characters above. */
export function numWord(zh) {
  const py = [...zh].map((c) => {
    if (!NUM_PY[c]) throw new Error(`no pinyin for ${c} in ${zh}`);
    return NUM_PY[c];
  });
  return { zh, py: py.join(' ') };
}

/**
 * Build a cloze item. `pre` and `post` are part lists around the blank,
 * `right` the correct option (a word), `wrong` the distractors (words or
 * bare Hanzi strings); `must` distractors are always offered. Options are
 * shuffled so the answer position varies.
 */
export function cloze(
  rng,
  { key, pre = [], post = [], right, wrong, must = [], en, why, cue, max = 3 }
) {
  const ok = w(right);
  const seen = new Set([ok.zh]);
  const bad = [];
  for (const raw of [...must, ...shuffle(rng, wrong)]) {
    const zh = typeof raw === 'string' ? raw.split('|')[0] : raw.zh;
    if (!seen.has(zh)) {
      seen.add(zh);
      bad.push(zh);
    }
  }
  const opts = shuffle(rng, [ok.zh, ...bad.slice(0, max)]);
  const full = join([...pre, ok, ...post]);
  const item = {
    id: `gen:${key}`,
    type: 'cloze',
    q: `${join(pre).zh}___${join(post).zh}`,
    opts,
    a: opts.indexOf(ok.zh),
    zh: full.zh,
    py: full.py,
    en,
    why,
  };
  if (cue) item.cue = cue;
  return item;
}

/**
 * Build an order item. `tiles` are words in the correct order; `alts` are
 * the other correct orders, each a list of indexes into `tiles`.
 */
export function order(rng, { key, tiles, alts = [], end = '。', en, why, cue }) {
  const words = tiles.map(w);
  const tokens = words.map((t) => t.zh);
  const item = {
    id: `gen:${key}`,
    type: 'order',
    tokens,
    alts: alts.map((perm) => perm.map((i) => tokens[i])),
    zh: tokens.join('') + end,
    py: join(words).py,
    en,
    why,
  };
  if (cue) item.cue = cue;
  return item;
}

/** Third-person singular of an English verb phrase ("watch TV" -> "watches TV"). */
export function s3(phrase) {
  const [verb, ...rest] = phrase.split(' ');
  let v;
  if (verb === 'have') v = 'has';
  else if (verb === 'be') v = 'is';
  else if (/(s|sh|ch|x|o)$/.test(verb)) v = `${verb}es`;
  else if (/[^aeiou]y$/.test(verb)) v = `${verb.slice(0, -1)}ies`;
  else v = `${verb}s`;
  return [v, ...rest].join(' ');
}

/**
 * People used as subjects. `en` starts a sentence, `obj` is the object form,
 * `be` the present of "to be", `sg` whether the verb takes -s.
 */
export const PEOPLE = rows(`
我|wǒ|I|me|am|
他|tā|He|him|is|s
她|tā|She|her|is|s
我们|wǒ men|We|us|are|
他们|tā men|They|them|are|
小王|xiǎo wáng|Xiao Wang|Xiao Wang|is|s
小李|xiǎo lǐ|Xiao Li|Xiao Li|is|s
我妈妈|wǒ mā ma|My mom|my mom|is|s
我爸爸|wǒ bà ba|My dad|my dad|is|s
我哥哥|wǒ gē ge|My older brother|my older brother|is|s
我姐姐|wǒ jiě jie|My older sister|my older sister|is|s
我弟弟|wǒ dì di|My younger brother|my younger brother|is|s
我妹妹|wǒ mèi mei|My younger sister|my younger sister|is|s
我朋友|wǒ péng you|My friend|my friend|is|s
我同学|wǒ tóng xué|My classmate|my classmate|is|s
`).map(([zh, py, en, obj, be, sg]) => ({ zh, py, en, obj, be, sg: sg === 's' }));

/** Present-tense English verb phrase agreeing with a subject. */
export const vb = (subj, base) => (subj.sg ? s3(base) : base);
export const dont = (subj) => (subj.sg ? "doesn't" : "don't");
export const have = (subj) => (subj.sg ? 'has' : 'have');
export const was = (subj) => (subj.be === 'are' ? 'were' : 'was');

/** Capitalise the first letter. */
export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * Fill an English template for a subject: {S} subject, {o} object form,
 * {have} {is} {was} {dont} agreeing forms, [verb phrase] present tense.
 */
export function fillEn(tpl, subj) {
  return tpl
    .replace(/\{S\}/g, subj.en)
    .replace(/\{o\}/g, subj.obj)
    .replace(/\{have\}/g, have(subj))
    .replace(/\{is\}/g, subj.be)
    .replace(/\{was\}/g, was(subj))
    .replace(/\{dont\}/g, dont(subj))
    .replace(/\[([^\]]+)\]/g, (_m, phrase) => vb(subj, phrase));
}

/** English possessive for a subject, lower case ("my", "his", "my mom's"). */
export function poss(subj) {
  const fixed = { I: 'my', He: 'his', She: 'her', We: 'our', They: 'their' }[subj.en];
  return fixed || `${subj.obj}'s`;
}
