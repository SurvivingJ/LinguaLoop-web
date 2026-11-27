/**
 * numbers-time generators: reading numbers, clock times, full dates and
 * prices. All pinyin comes from the per-character table in util.js.
 *
 * Policy for 2: 二 everywhere except a leading 2 before 千 / 万 / 亿, which
 * is 两 (两千, 两万, 两亿). 二百 is the form produced; 两百 is equally
 * acceptable, so neither 两百 nor 二千 / 二万 is ever offered as a wrong option.
 */
import { pick, int, chance, weighted, numWord, cloze, order, PEOPLE } from './util.js';

const DIGITS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
const UNITS = ['千', '百', '十', ''];

/** One group of up to four digits; `first` when nothing precedes it. */
function readGroup(n, first) {
  const ds = [Math.floor(n / 1000), Math.floor(n / 100) % 10, Math.floor(n / 10) % 10, n % 10];
  let out = '';
  let zero = false;
  let started = false;
  ds.forEach((d, i) => {
    if (d === 0) {
      if (started) zero = true;
      return;
    }
    if (zero) {
      out += '零';
      zero = false;
    }
    if (i === 2 && d === 1 && !started && first) out += '十';
    else out += DIGITS[d] + UNITS[i];
    started = true;
  });
  return out;
}

/** Standard reading of an integer from 0 to 999,999,999,999. */
export function readNumber(n) {
  if (n === 0) return '零';
  const groups = [
    [Math.floor(n / 1e8), '亿'],
    [Math.floor((n % 1e8) / 1e4), '万'],
    [n % 1e4, ''],
  ];
  let out = '';
  let gap = false;
  let started = false;
  for (const [v, unit] of groups) {
    if (v === 0) {
      if (started) gap = true;
      continue;
    }
    if (started && (gap || v < 1000)) out += '零';
    out += readGroup(v, !started) + unit;
    started = true;
    gap = false;
  }
  return /^二[千万亿]/.test(out) ? `两${out.slice(1)}` : out;
}

/** Wrong readings of n built from the mistakes learners really make. */
export function numberMistakes(n) {
  const right = readNumber(n);
  const out = [];
  const add = (s) => {
    if (s && s !== right && !out.includes(s)) out.push(s);
  };
  const digits = String(n);
  if (right.includes('零') && n > 0) add(right.replace(/零/g, ''));
  if (/0{2,}[1-9]/.test(digits)) add(right.replace('零', '零零'));
  if (n >= 20 && n < 100000) add([...digits].map((d) => DIGITS[d]).join(''));
  if (n >= 10 && n < 20) add(`一${right}`);
  if (n >= 21 && n < 100 && n % 10 !== 0) {
    add(`${DIGITS[Math.floor(n / 10)]}十零${DIGITS[n % 10]}`);
    if (n % 11 !== 0) add(readNumber((n % 10) * 10 + Math.floor(n / 10)));
  }
  if (n >= 10 && n % 10 === 0 && n < 1000) add(`${right}零`);
  if (right.includes('二十')) add(right.replace('二十', '两十'));
  if (n > 10 && right.endsWith('二')) add(`${right.slice(0, -1)}两`);
  if (/百[一二三四五六七八九]十/.test(right)) add(right.replace('百', '百零'));
  if (n >= 10000 && n < 1000000) {
    const k = Math.floor(n / 1000);
    const rest = n % 1000;
    add(`${readGroup(k, true)}千${rest ? (rest < 100 ? '零' : '') + readGroup(rest, false) : ''}`);
  }
  if (right.includes('万') && !right.includes('千') && !right.includes('亿')) {
    add(right.replace('万', '千'));
  }
  if (n >= 100000) {
    add(readNumber(n * 10));
    if (n % 10 === 0) add(readNumber(n / 10));
  }
  if (right.includes('亿')) add(right.replace('亿', '万万'));
  for (let step = 1; out.length < 3; step *= 10) {
    add(readNumber(n + step * 10));
    add(readNumber(n + step));
  }
  return out;
}

/* ---------- (a) number -> reading ---------- */

const NUMBER_FRAMES = [
  {
    lo: 0,
    hi: 40,
    pre: ['今天的气温是|jīn tiān de qì wēn shì'],
    post: ['度|dù', '。'],
    en: (x) => `Today's temperature is ${x} degrees.`,
    skip2: true,
  },
  {
    lo: 11,
    hi: 60,
    pre: ['我们班有|wǒ men bān yǒu'],
    post: ['个学生|gè xué sheng', '。'],
    en: (x) => `Our class has ${x} students.`,
  },
  {
    lo: 11,
    hi: 99,
    pre: ['我带了|wǒ dài le'],
    post: ['块钱|kuài qián', '。'],
    en: (x) => `I brought ${x} yuan.`,
  },
  {
    lo: 60,
    hi: 99,
    pre: ['我奶奶今年|wǒ nǎi nai jīn nián'],
    post: ['岁|suì', '。'],
    en: (x) => `My grandma is ${x} this year.`,
  },
  {
    lo: 100,
    hi: 999,
    pre: ['这本书有|zhè běn shū yǒu'],
    post: ['页|yè', '。'],
    en: (x) => `This book has ${x} pages.`,
  },
  {
    lo: 100,
    hi: 999,
    pre: ['这件衣服|zhè jiàn yī fu'],
    post: ['块钱|kuài qián', '。'],
    en: (x) => `This piece of clothing costs ${x} yuan.`,
  },
  {
    lo: 100,
    hi: 9999,
    pre: ['我们公司有|wǒ men gōng sī yǒu'],
    post: ['个人|gè rén', '。'],
    en: (x) => `Our company has ${x} people.`,
  },
  {
    lo: 300,
    hi: 9999,
    pre: ['这个学校有|zhè ge xué xiào yǒu'],
    post: ['个学生|gè xué sheng', '。'],
    en: (x) => `This school has ${x} students.`,
  },
  {
    lo: 1000,
    hi: 9999,
    pre: ['这个手机|zhè ge shǒu jī'],
    post: ['块钱|kuài qián', '。'],
    en: (x) => `This phone costs ${x} yuan.`,
  },
  {
    lo: 3000,
    hi: 30000,
    pre: ['这台电脑|zhè tái diàn nǎo'],
    post: ['块钱|kuài qián', '。'],
    en: (x) => `This computer costs ${x} yuan.`,
  },
  {
    lo: 10000,
    hi: 99999,
    pre: ['这个体育场能坐|zhè ge tǐ yù chǎng néng zuò'],
    post: ['个人|gè rén', '。'],
    en: (x) => `This stadium can seat ${x} people.`,
  },
  {
    lo: 50000,
    hi: 999999,
    pre: ['这辆车|zhè liàng chē'],
    post: ['块钱|kuài qián', '。'],
    en: (x) => `This car costs ${x} yuan.`,
  },
  {
    lo: 100000,
    hi: 30000000,
    pre: ['这个城市有|zhè ge chéng shì yǒu'],
    post: ['人|rén', '。'],
    en: (x) => `This city has ${x} people.`,
  },
  {
    lo: 1000000,
    hi: 999999999,
    pre: ['这家公司去年赚了|zhè jiā gōng sī qù nián zhuàn le'],
    post: ['块钱|kuài qián', '。'],
    en: (x) => `This company made ${x} yuan last year.`,
  },
  {
    lo: 10000000,
    hi: 999999999,
    pre: ['这个国家有|zhè ge guó jiā yǒu'],
    post: ['人|rén', '。'],
    en: (x) => `This country has ${x} people.`,
  },
  {
    lo: 3,
    hi: 9999,
    pre: ['这里一共有|zhè lǐ yī gòng yǒu'],
    post: ['个|gè', '。'],
    en: (x) => `There are ${x} here altogether.`,
  },
];

/** A number weighted to everyday sizes, with zeros more often than chance. */
function sampleNumber(rng) {
  const len = weighted(rng, [
    [1, 1],
    [14, 2],
    [24, 3],
    [24, 4],
    [16, 5],
    [8, 6],
    [5, 7],
    [4, 8],
    [4, 9],
  ]);
  // a bare 2 is left to the 二 / 两 drill: before a measure word it is 两
  if (len === 1) return pick(rng, [0, 1, 3, 4, 5, 6, 7, 8, 9]);
  const ds = [int(rng, 1, 9)];
  for (let i = 1; i < len; i++) ds.push(int(rng, 0, 9));
  if (len >= 3) {
    const style = rng();
    if (style < 0.3) {
      // round number: keep only the first one or two digits
      const keep = int(rng, 1, 2);
      for (let i = keep; i < len; i++) ds[i] = 0;
    } else if (style < 0.75) {
      // zero out one or two inner digits so 零 matters
      ds[int(rng, 1, len - 2)] = 0;
      if (len > 4 && chance(rng, 0.5)) ds[int(rng, 1, len - 1)] = 0;
    }
  }
  return Number(ds.join(''));
}

function makeNumber(rng) {
  const n = sampleNumber(rng);
  const frames = NUMBER_FRAMES.filter((f) => n >= f.lo && n <= f.hi && !(f.skip2 && n === 2));
  const f = pick(rng, frames);
  const right = readNumber(n);
  const wrong = n === 0 ? ['无', '空', '没'] : numberMistakes(n);
  const digits = String(n);
  let why;
  if (n === 0)
    why = 'Zero as a number is 零. 无 and 空 mean "without" and "empty", not the number.';
  else if (right.includes('零')) {
    why = `${n.toLocaleString('en-US')} is ${right}: a gap of empty places inside a number is read as one 零, however many zeros there are, and zeros at the end are not read.`;
  } else if (n >= 10000) {
    why = `${n.toLocaleString('en-US')} is ${right}: Chinese groups digits in fours, so count in 万 (10,000) and 亿 (100,000,000), not in thousands and millions.`;
  } else if (/2/.test(digits)) {
    why = `${n.toLocaleString('en-US')} is ${right}: 2 is 二 in 二十 and as the last digit; 两 only replaces a leading 2 before 千, 万 or 亿.`;
  } else {
    why = `${n.toLocaleString('en-US')} is ${right}: every non-zero digit is read with its unit (千, 百, 十), largest first, and digits are never just listed.`;
  }
  return cloze(rng, {
    key: 'number-reading',
    pre: f.pre,
    post: f.post,
    right: numWord(right),
    wrong,
    en: f.en(n.toLocaleString('en-US')),
    why,
  });
}

/* ---------- (b) clock time ---------- */

const hourZh = (h) => (h === 2 ? '两' : readNumber(h));

/** Acceptable and wrong ways to say h:m (h 1-12). */
export function clockForms(h, m) {
  const H = hourZh(h);
  const N = hourZh((h % 12) + 1);
  const M = readNumber(m);
  let good;
  let bad;
  if (m === 0) {
    good = [`${H}点`];
    bad = [`${H}个小时`, `${H}分`, `点${H}`, `${H}刻`];
  } else if (m === 30) {
    good = [`${H}点半`, `${H}点三十分`, `${H}点三十`];
    bad = [`${H}半点`, `半${H}点`, `${H}点二刻`, `${H}点半分`, `${H}个半小时`, `${H}点三十刻`];
  } else if (m === 15) {
    good = [`${H}点一刻`, `${H}点十五分`, `${H}点十五`];
    bad = [
      `${H}一刻点`,
      `一刻${H}点`,
      `${H}点一个刻`,
      `${H}点十五刻`,
      `差一刻${H}点`,
      `${H}点三刻`,
    ];
  } else if (m === 45) {
    good = [`${H}点三刻`, `${H}点四十五分`, `${H}点四十五`, `差一刻${N}点`];
    bad = [`差一刻${H}点`, `${H}点差一刻`, `三刻${H}点`, `${H}点四十五刻`, `${N}点三刻`];
  } else if (m < 10) {
    good = [`${H}点零${M}分`, `${H}点零${M}`];
    bad = [`${M}分${H}点`, `${H}点${M}刻`, `${H}零${M}点`, `${H}点零${M}刻`];
    if (m > 1) bad.push(`${H}点${M}十分`);
  } else if (m >= 50) {
    const K = readNumber(60 - m);
    good = [`${H}点${M}分`, `${H}点${M}`];
    bad = [`${M}分${H}点`, `${H}点${M}刻`, `${N}点${M}分`, `${H}分${M}点`];
    if (m !== 58) {
      good.push(`差${K}分${N}点`);
      bad.push(`差${K}分${H}点`, `${H}点差${K}分`);
    }
  } else {
    good = [`${H}点${M}分`];
    if (m > 10) good.push(`${H}点${M}`);
    bad = [`${M}分${H}点`, `${H}点${M}刻`, `${H}分${M}点`, `${H}小时${M}分`, `${H}点${M}秒`];
  }
  return { good, bad: [...new Set(bad)].filter((b) => !good.includes(b)) };
}

const CLOCK_FRAMES = [
  { pre: ['现在|xiàn zài'], post: ['。'], en: (t) => `It's ${t} now.` },
  { pre: ['我们|wǒ men'], post: ['见面吧|jiàn miàn ba', '。'], en: (t) => `Let's meet at ${t}.` },
  { pre: ['电影|diàn yǐng'], post: ['开始|kāi shǐ', '。'], en: (t) => `The film starts at ${t}.` },
  { pre: ['火车|huǒ chē'], post: ['开|kāi', '。'], en: (t) => `The train leaves at ${t}.` },
  { pre: ['飞机|fēi jī'], post: ['起飞|qǐ fēi', '。'], en: (t) => `The plane takes off at ${t}.` },
  { pre: ['会议|huì yì'], post: ['开始|kāi shǐ', '。'], en: (t) => `The meeting starts at ${t}.` },
  {
    pre: ['我明天|wǒ míng tiān'],
    post: ['到|dào', '。'],
    en: (t) => `I'll arrive at ${t} tomorrow.`,
  },
  {
    pre: ['商店|shāng diàn'],
    post: ['关门|guān mén', '。'],
    en: (t) => `The shop closes at ${t}.`,
  },
];

function clockWhy(h, m, right) {
  const t = `${h}:${String(m).padStart(2, '0')}`;
  let why;
  if (m === 0) {
    why = `${t} is ${right}: a clock hour is the number plus 点. 小时 counts hours of duration, and 分 and 刻 are parts of an hour.`;
  } else if (m === 30) {
    why = `${t} is ${right}: the hour with 点 comes first, then 半 (or 三十分). 二刻 is not said, and 个半小时 is a length of time, not a clock time.`;
  } else if (m === 15 || m === 45) {
    why = `${t} is ${right}: 一刻 is a quarter of an hour and follows the hour; with 差 you count back from the coming hour (差一刻 + next hour).`;
  } else if (m < 10) {
    why = `${t} is ${right}: hour + 点 first, and minutes below ten take 零 after 点. 刻 only counts quarters of an hour.`;
  } else if (m >= 50) {
    why = `${t} is ${right}: hour + 点 + minutes, or count back with 差 from the coming hour. 差 never goes with the hour that has already started.`;
  } else {
    why = `${t} is ${right}: hour + 点, then the minutes (+ 分), largest unit first. 小时 is for durations and 刻 only for quarters.`;
  }
  return right.includes('两点') ? `${why} 2 o'clock is 两点, never 二点.` : why;
}

function makeClock(rng) {
  const h = int(rng, 1, 12);
  const m = weighted(rng, [
    [2, 0],
    [3, 15],
    [3, 30],
    [3, 45],
    [3, pick(rng, [5, 10, 20, 25, 35, 40, 50, 55])],
    [3, int(rng, 1, 9)],
    [3, int(rng, 11, 59)],
  ]);
  const { good, bad } = clockForms(h, m);
  const right = pick(rng, good);
  const must = right.includes('两点') ? [right.replace('两点', '二点')] : [];
  const f = pick(rng, CLOCK_FRAMES);
  return cloze(rng, {
    key: 'clock-time',
    pre: f.pre,
    post: f.post,
    right: numWord(right),
    wrong: bad,
    must,
    en: f.en(`${h}:${String(m).padStart(2, '0')}`),
    why: clockWhy(h, m, right),
  });
}

/* ---------- (c) full dates as order tiles ---------- */

const MONTHS =
  'January February March April May June July August September October November December'.split(
    ' '
  );
const WEEKDAYS = [
  ['星期天', 'xīng qī tiān', 'Sunday'],
  ['星期一', 'xīng qī yī', 'Monday'],
  ['星期二', 'xīng qī èr', 'Tuesday'],
  ['星期三', 'xīng qī sān', 'Wednesday'],
  ['星期四', 'xīng qī sì', 'Thursday'],
  ['星期五', 'xīng qī wǔ', 'Friday'],
  ['星期六', 'xīng qī liù', 'Saturday'],
];
const PERIODS = [
  { zh: '上午', py: 'shàng wǔ', hours: [8, 9, 10, 11], en: 'a.m.' },
  { zh: '下午', py: 'xià wǔ', hours: [1, 2, 3, 4, 5], en: 'p.m.' },
  { zh: '晚上', py: 'wǎn shang', hours: [7, 8, 9, 10], en: 'p.m.' },
];
// event | py | English | parts of the day it can be held in (indexes into PERIODS)
const EVENTS = [
  ['会议', 'huì yì', 'The meeting', [0, 1]],
  ['考试', 'kǎo shì', 'The exam', [0, 1]],
  ['比赛', 'bǐ sài', 'The match', [0, 1, 2]],
  ['面试', 'miàn shì', 'The interview', [0, 1]],
  ['晚会', 'wǎn huì', 'The party', [2]],
  ['婚礼', 'hūn lǐ', 'The wedding', [0]],
  ['演出', 'yǎn chū', 'The show', [1, 2]],
  ['活动', 'huó dòng', 'The event', [0, 1, 2]],
];
const DATE_WHY =
  'Chinese time expressions run from the largest unit to the smallest: 年, 月, 号/日, 星期, then 上午/下午/晚上 and the hour. The English order (weekday first, year last) does not carry over.';

const yearWord = (y) => numWord(`${[...String(y)].map((d) => DIGITS[d]).join('')}年`);

function makeDate(rng) {
  const month = int(rng, 1, 12);
  const day = int(rng, 1, 28);
  const monthW = numWord(`${readNumber(month)}月`);
  const dayW = numWord(`${readNumber(day)}${chance(rng, 0.8) ? '号' : '日'}`);
  const kind = weighted(rng, [
    [3, 'today'],
    [4, 'event'],
    [2, 'born'],
  ]);
  const md = `${MONTHS[month - 1]} ${day}`;
  if (kind === 'born') {
    const p = pick(
      rng,
      PEOPLE.filter((x) => x.be !== 'are')
    );
    const year = /妈妈|爸爸/.test(p.zh) ? int(rng, 1955, 1975) : int(rng, 1985, 2008);
    return order(rng, {
      key: 'date-order',
      tiles: [
        { zh: `${p.zh}是`, py: `${p.py} shì` },
        yearWord(year),
        monthW,
        dayW,
        '出生的|chū shēng de',
      ],
      en: `${p.en} was born on ${md}, ${year}.`,
      why: DATE_WHY,
    });
  }
  if (kind === 'today') {
    const withYear = chance(rng, 0.6);
    const year = int(rng, 2018, 2032);
    const wd = withYear
      ? WEEKDAYS[new Date(Date.UTC(year, month - 1, day)).getUTCDay()]
      : pick(rng, WEEKDAYS);
    return order(rng, {
      key: 'date-order',
      tiles: [
        '今天是|jīn tiān shì',
        ...(withYear ? [yearWord(year)] : []),
        monthW,
        dayW,
        { zh: wd[0], py: wd[1] },
      ],
      en: `Today is ${wd[2]}, ${md}${withYear ? `, ${year}` : ''}.`,
      why: DATE_WHY,
    });
  }
  const ev = pick(rng, EVENTS);
  const wd = chance(rng, 0.5) ? pick(rng, WEEKDAYS) : null;
  const period = PERIODS[pick(rng, ev[3])];
  const hour = pick(rng, period.hours);
  const half = chance(rng, 0.3);
  return order(rng, {
    key: 'date-order',
    tiles: [
      { zh: `${ev[0]}时间是`, py: `${ev[1]} shí jiān shì` },
      monthW,
      dayW,
      ...(wd ? [{ zh: wd[0], py: wd[1] }] : []),
      { zh: period.zh, py: period.py },
      numWord(`${hourZh(hour)}点${half ? '半' : ''}`),
    ],
    en: `${ev[2]} is on ${wd ? `${wd[2]}, ` : ''}${md} at ${hour}${half ? ':30' : ''} ${period.en.replace(/\.$/, '')}.`,
    why: DATE_WHY,
  });
}

/* ---------- (d) money ---------- */

const GOODS = [
  ['这个面包', 'zhè ge miàn bāo', 'This bread', 2, 15],
  ['一瓶水', 'yī píng shuǐ', 'A bottle of water', 1, 5],
  ['一斤苹果', 'yī jīn píng guǒ', 'Half a kilo of apples', 3, 15],
  ['一杯咖啡', 'yī bēi kā fēi', 'A cup of coffee', 12, 40],
  ['这本书', 'zhè běn shū', 'This book', 18, 90],
  ['一张电影票', 'yī zhāng diàn yǐng piào', 'A film ticket', 25, 80],
  ['一碗面条', 'yī wǎn miàn tiáo', 'A bowl of noodles', 8, 30],
  ['这支笔', 'zhè zhī bǐ', 'This pen', 1, 12],
  ['一个包子', 'yī gè bāo zi', 'A steamed bun', 1, 4],
  ['一斤香蕉', 'yī jīn xiāng jiāo', 'Half a kilo of bananas', 2, 9],
  ['这件衬衫', 'zhè jiàn chèn shān', 'This shirt', 80, 400],
  ['这双鞋', 'zhè shuāng xié', 'This pair of shoes', 100, 900],
  ['这个书包', 'zhè ge shū bāo', 'This school bag', 60, 300],
];

function makeMoney(rng) {
  const [zh, py, en, lo, hi] = pick(rng, GOODS);
  const y = int(rng, lo, hi);
  const j =
    y >= 100
      ? 0
      : weighted(rng, [
          [4, 0],
          [3, 5],
          [3, int(rng, 1, 9)],
        ]);
  const Y = y === 2 ? '两' : readNumber(y);
  const J = DIGITS[j];
  let good;
  let bad;
  if (j === 0) {
    good = [`${Y}块`];
    bad = [`${Y}毛`, `${Y}分`, `块${Y}`, `${Y}点块`];
    if (y >= 100) bad = numberMistakes(y).map((s) => `${s}块`);
  } else {
    good = [`${Y}块${J}`, `${Y}块${J}毛`];
    bad = [
      `${J}毛${Y}块`,
      `${Y}块${J}十毛`,
      `${Y}点${J}毛`,
      `${Y}毛${J}块`,
      `${Y}块${J}分`,
      `${Y}块零${J}`,
    ];
  }
  const right = pick(rng, good);
  const must = [];
  if (y === 2) must.push(`二${right.slice(1)}`);
  else if (y < 100 && Y.endsWith('二')) must.push(right.replace('二块', '两块'));
  else if (y < 100 && Y.startsWith('二十')) must.push(right.replace('二十', '两十'));
  const price = `¥${y}.${j}0`;
  let why = `${price} is ${right}: 块 (yuan) comes first, then 毛 (tenths of a yuan), and a final 毛 may be dropped.`;
  if (j === 0)
    why = `${price} is ${right}: the amount is a number plus 块; 毛 are tenths of a yuan and 分 hundredths.`;
  if (y === 2) why += ' Before 块, a single 2 is 两.';
  else if (must.length) why += ' Inside 十二 and 二十, 2 stays 二 even before 块.';
  if (y >= 100 && right.includes('零')) why += ' An empty place inside the number is read 零.';
  return cloze(rng, {
    key: 'money',
    pre: [{ zh, py }],
    post: ['。'],
    right: numWord(right),
    wrong: bad,
    must,
    en: `${en} costs ${price}.`,
    why,
  });
}

export const generators = [
  { key: 'number-reading', label: 'Reading numbers', make: makeNumber },
  { key: 'clock-time', label: 'Clock time', make: makeClock },
  { key: 'date-order', label: 'Dates: largest to smallest', make: makeDate },
  { key: 'money', label: 'Prices: 块 and 毛', make: makeMoney },
];
