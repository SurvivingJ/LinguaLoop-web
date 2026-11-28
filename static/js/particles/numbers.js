// static/js/particles/numbers.js
// Rule engine of the reading drill: numbers, prices, clock times, dates,
// durations and ages are generated and read by rule, so the practice never
// runs out. Every reading is hiragana; `readings[0]` is the standard one and
// the rest are accepted variants (しちじ / ななじ). Katakana words come from a
// reviewed list and are matched to their meaning.
// Pure functions: the page (js/pages/particle-drill.js) owns the DOM.

const D = ['', 'いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう'];
const uniq = (list) => list.filter((x, i) => x && list.indexOf(x) === i);
const int = (rng, lo, hi) => lo + Math.floor(rng() * (hi - lo + 1));
const pick = (rng, list) => list[Math.floor(rng() * list.length)];

// ---------------------------------------------------------------------------
// Plain numbers
// ---------------------------------------------------------------------------
const SEN = { 1: 'せん', 3: 'さんぜん', 8: 'はっせん' };
const HYAKU = { 1: 'ひゃく', 3: 'さんびゃく', 6: 'ろっぴゃく', 8: 'はっぴゃく' };

/** 1..9999. `naive` drops the sound changes (the learner's typical mistake). */
function under10000(n, { lead = false, naive = false } = {}) {
  const th = Math.floor(n / 1000);
  const h = Math.floor(n / 100) % 10;
  const t = Math.floor(n / 10) % 10;
  const o = n % 10;
  let out = '';
  if (th) out += naive ? `${D[th]}せん` : th === 1 && lead ? 'いっせん' : SEN[th] || `${D[th]}せん`;
  if (h) out += naive ? `${D[h]}ひゃく` : HYAKU[h] || `${D[h]}ひゃく`;
  if (t) out += t === 1 ? 'じゅう' : `${D[t]}じゅう`;
  if (o) out += D[o];
  return out;
}

/** Standard reading of an integer from 1 to 99,999,999. */
export function readNumber(n, opts = {}) {
  const man = Math.floor(n / 10000);
  const rest = n % 10000;
  return (
    (man ? `${under10000(man, { ...opts, lead: true })}まん` : '') +
    (rest ? under10000(rest, opts) : '')
  );
}

/** Accepted readings of a bare number: the standard one and the し / しち / く endings. */
export function numberReadings(n) {
  const std = readNumber(n);
  const out = [std];
  const o = n % 10;
  if (o === 4) out.push(std.replace(/よん$/, 'し'));
  if (o === 7) out.push(std.replace(/なな$/, 'しち'));
  if (o === 9) out.push(std.replace(/きゅう$/, 'く'));
  if (Math.floor(n / 10) % 10 === 7)
    out.push(...out.map((r) => r.replace(/ななじゅう/, 'しちじゅう')));
  // 21,000 is にまんせん; にまんいっせん is also said.
  if (n > 10000 && Math.floor(n / 1000) % 10 === 1)
    out.push(...out.map((r) => r.replace(/まんせん/, 'まんいっせん')));
  // 1000万 is いっせんまん; せんまん is also heard.
  if (/^いっせん/.test(std)) out.push(...out.map((r) => r.replace(/^いっせん/, 'せん')));
  return uniq(out);
}

// ---------------------------------------------------------------------------
// Counters with sound changes: a table for 1..10, tens built in front
// ---------------------------------------------------------------------------
const table = (text) => [null, ...text.split(' ').map((cell) => cell.split('/'))];
const FUN = table(
  'いっぷん にふん さんぷん よんぷん/よんふん ごふん ろっぷん ななふん/しちふん はっぷん/はちふん きゅうふん じゅっぷん/じっぷん'
);
const SAI = table(
  'いっさい にさい さんさい よんさい ごさい ろくさい ななさい/しちさい はっさい/はちさい きゅうさい じゅっさい/じっさい'
);
const KAGETSU = table(
  'いっかげつ にかげつ さんかげつ よんかげつ ごかげつ ろっかげつ ななかげつ/しちかげつ はっかげつ/はちかげつ きゅうかげつ じゅっかげつ/じっかげつ'
);
const SHUUKAN = table(
  'いっしゅうかん にしゅうかん さんしゅうかん よんしゅうかん ごしゅうかん ろくしゅうかん ななしゅうかん/しちしゅうかん はっしゅうかん きゅうしゅうかん じゅっしゅうかん/じっしゅうかん'
);
const NEN = table(
  'いちねん にねん さんねん よねん ごねん ろくねん ななねん/しちねん はちねん きゅうねん/くねん じゅうねん'
);
const JI = table('いちじ にじ さんじ よじ ごじ ろくじ しちじ/ななじ はちじ くじ じゅうじ');
const GATSU = table(
  'いちがつ にがつ さんがつ しがつ ごがつ ろくがつ しちがつ はちがつ くがつ じゅうがつ'
);

/** All accepted readings of `n` (1..99) with a counter table. */
export function counterReadings(n, tbl) {
  if (n <= 10) return tbl[n].slice();
  const t = Math.floor(n / 10);
  const o = n % 10;
  const tens = t > 1 ? D[t] : '';
  if (o === 0) return tbl[10].map((r) => tens + r);
  return tbl[o].map((r) => `${tens}じゅう${r}`);
}

const DAYS = {
  1: ['ついたち'],
  2: ['ふつか'],
  3: ['みっか'],
  4: ['よっか'],
  5: ['いつか'],
  6: ['むいか'],
  7: ['なのか'],
  8: ['ようか'],
  9: ['ここのか'],
  10: ['とおか'],
  14: ['じゅうよっか'],
  17: ['じゅうしちにち', 'じゅうななにち'],
  19: ['じゅうくにち', 'じゅうきゅうにち'],
  20: ['はつか'],
  24: ['にじゅうよっか'],
  27: ['にじゅうしちにち', 'にじゅうななにち'],
  29: ['にじゅうくにち', 'にじゅうきゅうにち'],
};
/** Day of the month, 1..31. */
export const dayReadings = (d) => DAYS[d] || [`${readNumber(d)}にち`];
/** Month, 1..12. */
export const monthReadings = (m) => counterReadings(m, GATSU);
/** Clock hour, 0..24 (0時 is れいじ). */
export const hourReadings = (h) => (h === 0 ? ['れいじ'] : counterReadings(h, JI));
/** Minutes, 1..59. */
export const minuteReadings = (m) => counterReadings(m, FUN);

const cross = (a, b) => a.flatMap((x) => b.map((y) => x + y));

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------
export const CATS = {
  num100: {
    label: '1–999',
    hint: 'numbers',
    note: '300 さんびゃく, 600 ろっぴゃく, 800 はっぴゃく. 100 is ひゃく, never いちひゃく.',
  },
  numbig: {
    label: '千・万',
    hint: 'big numbers',
    note: 'Count in 万 (10,000): 35,000 is さんまんごせん. 3000 さんぜん, 8000 はっせん; 1000 is せん but 1万 is いちまん.',
  },
  price: {
    label: '円',
    hint: 'prices',
    note: 'The number reading plus えん; 4円 is よえん.',
  },
  time: {
    label: '時・分',
    hint: 'clock times',
    note: '4時 よじ, 7時 しちじ, 9時 くじ. Minutes: 1 いっぷん, 3 さんぷん, 4 よんぷん, 6 ろっぷん, 8 はっぷん, 10 じゅっぷん; the rest take ふん.',
  },
  date: {
    label: '月・日',
    hint: 'dates',
    note: '4月 しがつ, 7月 しちがつ, 9月 くがつ. Days 1 to 10, 14, 20 and 24 have their own readings (ついたち … とおか, じゅうよっか, はつか, にじゅうよっか).',
  },
  duration: {
    label: '〜間',
    hint: 'how long',
    note: 'よじかん, くじかん; いっしゅうかん, はっしゅうかん; いっかげつ, ろっかげつ; よねん. Days use the date readings plus かん (ふつかかん).',
  },
  age: {
    label: '歳',
    hint: 'ages',
    note: 'いっさい, はっさい, じゅっさい; 20歳 is はたち.',
  },
  kata: {
    label: 'カタカナ',
    hint: 'loanwords, by meaning',
    note: 'Read the katakana aloud; the English word is usually inside it.',
    choiceOnly: true,
  },
};
export const CAT_IDS = Object.keys(CATS);

const comma = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
// Digits that carry the sound changes come up more often than chance.
const TRICKY_HUNDREDS = [100, 300, 600, 800];
const TRICKY_THOUSANDS = [1000, 3000, 8000];

function genNumber(rng, big) {
  if (!big) {
    const r = rng();
    if (r < 0.15) return int(rng, 11, 99);
    if (r < 0.6) return pick(rng, TRICKY_HUNDREDS) + (rng() < 0.6 ? int(rng, 0, 99) : 0);
    return int(rng, 100, 999);
  }
  const r = rng();
  if (r < 0.3) return pick(rng, TRICKY_THOUSANDS) + pick(rng, [0, 0, 100, 300, 500, 600, 800]);
  if (r < 0.55) return int(rng, 1, 9) * 10000 + pick(rng, [0, 1000, 3000, 5000, 8000]);
  if (r < 0.75) return int(rng, 10, 99) * 10000;
  if (r < 0.9) return int(rng, 1, 9) * 1000000 + int(rng, 0, 9) * 100000;
  return int(rng, 1, 9) * 10000000;
}

/** Wrong readings for a number: no sound changes, and the numbers next door. */
function numberWrongs(n, suffix = '') {
  const near = [
    n * 10,
    n % 10 === 0 ? n / 10 : 0,
    n + 100,
    n + 1000,
    n > 200 ? n - 100 : 0,
    n + 10,
  ];
  return [
    readNumber(n, { naive: true }),
    ...near.filter((x) => x > 0 && x < 100000000).map((x) => readNumber(x)),
  ].map((r) => r + suffix);
}

function genTime(rng) {
  const h = int(rng, 1, 12);
  const kind = rng();
  const m =
    kind < 0.15
      ? 0
      : kind < 0.3
        ? 30
        : rng() < 0.6
          ? pick(rng, [1, 3, 4, 6, 8, 10, 13, 16, 18, 20, 24, 40, 44, 50])
          : int(rng, 1, 59);
  const pre =
    rng() < 0.25
      ? pick(rng, [
          ['午前', 'ごぜん'],
          ['午後', 'ごご'],
        ])
      : ['', ''];
  const hours = hourReadings(h);
  let readings = m ? cross(hours, minuteReadings(m)) : hours;
  if (m === 30) readings = [...cross(hours, ['はん']), ...readings];
  const show = `${pre[0]}${h}時${m === 30 ? '半' : m ? `${m}分` : ''}`;
  // Typical mistakes: よんじ / きゅうじ, ふん where ぷん belongs (or the reverse),
  // and the times next door.
  const minute = m === 30 ? 'はん' : m ? minuteReadings(m)[0] : '';
  const badHour = { 4: 'よんじ', 9: 'きゅうじ' }[h];
  const other = (k) => hourReadings(((h + k - 1) % 12) + 1)[0];
  const wrong = [
    badHour ? badHour + minute : '',
    m && m !== 30 ? `${hours[0]}${readNumber(m)}ふん` : '',
    m && m !== 30 ? `${hours[0]}${readNumber(m)}ぷん` : '',
    other(1) + minute,
    m ? hours[0] + minuteReadings(m === 59 ? 58 : m + 1)[0] : `${hours[0]}はん`,
    other(2) + minute,
    other(6) + minute,
  ];
  return {
    show,
    readings: readings.map((r) => pre[1] + r),
    wrong: wrong.filter(Boolean).map((r) => pre[1] + r),
  };
}

function genDate(rng) {
  const m = rng() < 0.45 ? pick(rng, [4, 7, 9]) : int(rng, 1, 12);
  const d =
    rng() < 0.65 ? pick(rng, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 20, 24]) : int(rng, 11, 28);
  const months = monthReadings(m);
  const days = dayReadings(d);
  const badMonth =
    { 4: 'よんがつ', 7: 'なながつ', 9: 'きゅうがつ' }[m] || monthReadings((m % 12) + 1)[0];
  const plainDay = `${readNumber(d)}にち`;
  const twin = {
    4: 8,
    8: 4,
    2: 20,
    20: 2,
    6: 9,
    9: 6,
    5: 6,
    3: 6,
    14: 24,
    24: 14,
    1: 2,
    7: 9,
    10: 20,
  }[d];
  const wrong = [
    badMonth + days[0],
    months[0] + plainDay,
    months[0] + dayReadings(twin || (d % 28) + 1)[0],
    badMonth + plainDay,
    months[0] + dayReadings((d % 28) + 2)[0],
  ];
  return { show: `${m}月${d}日`, readings: cross(months, days), wrong };
}

function genDuration(rng) {
  const kind = pick(rng, ['h', 'm', 'd', 'w', 'mo', 'y']);
  if (kind === 'h') {
    const n = rng() < 0.5 ? pick(rng, [4, 7, 9, 14, 24]) : int(rng, 1, 24);
    const readings = counterReadings(n, JI).map((r) => `${r}かん`);
    const bad = { 4: 'よんじかん', 9: 'きゅうじかん' };
    return {
      show: `${n}時間`,
      readings,
      wrong: [
        bad[n % 10] ? readNumber(n - (n % 10)) + bad[n % 10] : '',
        `${readNumber(n)}じ`,
        `${readNumber(n)}かん`,
        counterReadings((n % 24) + 1, JI)[0] + 'かん',
        counterReadings((n % 24) + 2, JI)[0] + 'かん',
      ],
    };
  }
  if (kind === 'm') {
    const n = rng() < 0.6 ? pick(rng, [1, 3, 4, 6, 8, 10, 20, 30, 40]) : int(rng, 1, 59);
    const base = minuteReadings(n);
    return {
      show: `${n}分間`,
      readings: base.map((r) => `${r}かん`),
      wrong: [
        `${readNumber(n)}ふんかん`,
        `${readNumber(n)}ぷんかん`,
        `${minuteReadings((n % 59) + 1)[0]}かん`,
        `${readNumber(n)}びょうかん`,
        `${minuteReadings((n % 58) + 2)[0]}かん`,
      ],
    };
  }
  if (kind === 'd') {
    const n = rng() < 0.75 ? int(rng, 2, 10) : pick(rng, [14, 20, 12, 15, 30]);
    const twin = { 4: 8, 8: 4, 2: 20, 20: 2, 6: 9, 9: 6, 5: 6, 3: 6, 7: 9, 10: 20, 14: 4 }[n];
    return {
      show: `${n}日間`,
      readings: dayReadings(n).map((r) => `${r}かん`),
      wrong: [
        `${readNumber(n)}にちかん`,
        `${dayReadings(twin || n + 1)[0]}かん`,
        `${readNumber(n)}かかん`,
        `${dayReadings(n + 1 > 31 ? 2 : n + 1)[0]}かん`,
        `${dayReadings(n + 2 > 31 ? 3 : n + 2)[0]}かん`,
      ],
    };
  }
  const [tbl, unit, plain, max] = {
    w: [SHUUKAN, '週間', 'しゅうかん', 10],
    mo: [KAGETSU, 'か月', 'かげつ', 12],
    y: [NEN, '年間', 'ねん', 30],
  }[kind];
  const n =
    rng() < 0.6 ? pick(rng, kind === 'y' ? [4, 7, 9, 14, 20] : [1, 6, 8, 10]) : int(rng, 1, max);
  const tail = kind === 'y' ? 'かん' : '';
  const next = (k) => counterReadings(((n + k - 1) % max) + 1, tbl)[0] + tail;
  return {
    show: `${n}${unit}`,
    readings: counterReadings(n, tbl).map((r) => r + tail),
    wrong: [readNumber(n) + plain + tail, next(1), next(2), next(3)],
  };
}

function genAge(rng) {
  const n = rng() < 0.55 ? pick(rng, [1, 8, 10, 18, 20, 21, 28, 30, 40, 50, 60]) : int(rng, 1, 99);
  const readings = n === 20 ? ['はたち', 'にじゅっさい', 'にじっさい'] : counterReadings(n, SAI);
  const next = (k) => counterReadings(((n + k - 1) % 99) + 1, SAI)[0];
  return {
    show: `${n}歳`,
    readings,
    wrong: [
      `${readNumber(n)}さい`,
      n === 20 ? 'はつか' : `${readNumber(n)}ざい`,
      next(1),
      next(10),
      next(2),
    ],
  };
}

/**
 * One question of a category.
 *   { show, readings[], wrong[3], en }   reading categories
 *   { show, readings[en], wrong[3 en], meaning: true }   katakana (by meaning)
 * `lists.katakana` is the reviewed word list ({k, en, lv}).
 */
export function generate(cat, rng = Math.random, lists = {}) {
  let q;
  if (cat === 'kata') {
    const words = lists.katakana || [];
    if (words.length < 4) return null;
    const w = pick(rng, words);
    const wrong = [];
    for (let tries = 0; wrong.length < 3 && tries < 60; tries++) {
      const o = pick(rng, words);
      if (o.en !== w.en && !wrong.includes(o.en)) wrong.push(o.en);
    }
    return { cat, show: w.k, readings: [w.en], wrong, meaning: true, en: '' };
  }
  if (cat === 'num100' || cat === 'numbig') {
    const n = genNumber(rng, cat === 'numbig');
    q = { show: comma(n), readings: numberReadings(n), wrong: numberWrongs(n) };
  } else if (cat === 'price') {
    const n =
      rng() < 0.2 ? int(rng, 1, 9) * 100 + 4 : genNumber(rng, rng() < 0.6) - (rng() < 0.5 ? 0 : 20);
    const amount = Math.max(1, n);
    const std = `${readNumber(amount)}えん`;
    const o = amount % 10;
    const readings =
      o === 4
        ? [std.replace(/よんえん$/, 'よえん'), std]
        : o === 7
          ? [std, std.replace(/ななえん$/, 'しちえん')]
          : [std];
    q = { show: `${comma(amount)}円`, readings, wrong: numberWrongs(amount, 'えん') };
  } else if (cat === 'time') q = genTime(rng);
  else if (cat === 'date') q = genDate(rng);
  else if (cat === 'duration') q = genDuration(rng);
  else if (cat === 'age') q = genAge(rng);
  else return null;
  const wrong = uniq(q.wrong).filter((r) => !q.readings.includes(r));
  return {
    cat,
    show: q.show,
    readings: uniq(q.readings),
    wrong: wrong.slice(0, 3),
    note: CATS[cat].note,
    en: '',
  };
}
