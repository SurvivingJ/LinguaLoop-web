/**
 * separable-verbs generators: 了 / 过 / a duration / a count goes INSIDE a
 * verb-object compound (睡了八个小时觉, 见过面, 搬过三次家), and the person
 * involved needs a preposition or 的 (跟他见面, 帮他的忙), as cloze and as
 * order tiles.
 */
import { pick, weighted, rows, order, cloze, PEOPLE, fillEn } from './util.js';

const part = (zh, py) => ({ zh, py });

// unit | duration | py | English
const DURATIONS = rows(`
s|六个小时|liù gè xiǎo shí|six hours
s|七个小时|qī gè xiǎo shí|seven hours
s|八个小时|bā gè xiǎo shí|eight hours
s|十个小时|shí gè xiǎo shí|ten hours
h|半个小时|bàn gè xiǎo shí|half an hour
h|一个小时|yī gè xiǎo shí|an hour
h|两个小时|liǎng gè xiǎo shí|two hours
h|三个小时|sān gè xiǎo shí|three hours
n|十分钟|shí fēn zhōng|ten minutes
n|二十分钟|èr shí fēn zhōng|twenty minutes
n|半个小时|bàn gè xiǎo shí|half an hour
n|一会儿|yī huì r|a while
d|一天|yī tiān|a day
d|两天|liǎng tiān|two days
d|三天|sān tiān|three days
d|一个星期|yī gè xīng qī|a week
m|两个月|liǎng gè yuè|two months
m|三个月|sān gè yuè|three months
m|半年|bàn nián|half a year
`);
// unit | time | py | English
const WHEN = rows(`
s|昨天晚上|zuó tiān wǎn shang|last night
s|昨天|zuó tiān|yesterday
h|昨天|zuó tiān|yesterday
h|今天|jīn tiān|today
h|今天下午|jīn tiān xià wǔ|this afternoon
h|昨天晚上|zuó tiān wǎn shang|last night
n|昨天|zuó tiān|yesterday
n|今天|jīn tiān|today
n|刚才|gāng cái|just now
d|上个月|shàng ge yuè|last month
d|这个月|zhè ge yuè|this month
m|去年|qù nián|last year
`);

// verb | py | object | py | English with {S}, {d} duration, {t} time | unit
const TIMED = rows(`
睡|shuì|觉|jiào|{S} slept for {d} {t}.|s
游|yóu|泳|yǒng|{S} swam for {d} {t}.|h
跑|pǎo|步|bù|{S} ran for {d} {t}.|h
聊|liáo|天|tiān|{S} chatted for {d} {t}.|n
上|shàng|课|kè|{S} had class for {d} {t}.|h
开|kāi|会|huì|{S} sat in a meeting for {d} {t}.|h
散|sàn|步|bù|{S} took a walk for {d} {t}.|n
跳|tiào|舞|wǔ|{S} danced for {d} {t}.|h
唱|chàng|歌|gē|{S} sang for {d} {t}.|h
排|pái|队|duì|{S} queued for {d} {t}.|n
加|jiā|班|bān|{S} worked overtime for {d} {t}.|h
上|shàng|网|wǎng|{S} spent {d} online {t}.|h
洗|xǐ|澡|zǎo|{S} spent {d} in the shower {t}.|n
请|qǐng|假|jià|{S} took {d} off {t}.|d
住|zhù|院|yuàn|{S} spent {d} in hospital {t}.|d
放|fàng|假|jià|{S} had {d} of holiday {t}.|d
发|fā|烧|shāo|{S} had a fever for {d} {t}.|d
打|dǎ|工|gōng|{S} worked part-time for {d} {t}.|m
`);

// verb | py | object | py | lead-in | py | English participle phrase | counts allowed
const EXPERIENCE = rows(`
见|jiàn|面|miàn|跟他|gēn tā|met him|c
见|jiàn|面|miàn|跟老师|gēn lǎo shī|met the teacher|c
吵|chǎo|架|jià|跟他|gēn tā|quarrelled with him|c
握|wò|手|shǒu|跟他|gēn tā|shaken hands with him|c
打|dǎ|架|jià|跟同学|gēn tóng xué|had a fight with a classmate|c
结|jié|婚|hūn|||been married|c
请|qǐng|假|jià|||taken leave|c
游|yóu|泳|yǒng|||gone swimming|
跳|tiào|舞|wǔ|||danced|
出|chū|差|chāi|||been on a business trip|c
住|zhù|院|yuàn|||been in hospital|c
上|shàng|当|dàng|||been tricked|c
滑|huá|雪|xuě|||gone skiing|c
爬|pá|山|shān|||gone hiking|c
照|zhào|相|xiàng|||had a photo taken|
打|dǎ|工|gōng|||had a part-time job|
留|liú|学|xué|||studied abroad|
搬|bān|家|jiā|||moved house|c
请|qǐng|客|kè|||treated people to a meal|c
`);
const COUNTS = rows(`
一次|yī cì|once
两次|liǎng cì|twice
三次|sān cì|three times
几次|jǐ cì|a few times
`);

// lead-in | py | right | py | wrong forms | English with {S} | s = one person only
const PARTNERED = rows(`
明天要|míng tiān yào|跟他见面|gēn tā jiàn miàn|见面他 见他面|{S} {is} going to meet him tomorrow.|
想|xiǎng|帮他的忙|bāng tā de máng|帮忙他 帮忙他的|{S} [want] to help him.|
很|hěn|生他的气|shēng tā de qì|生气他 生气他的|{S} {is} very angry with him.|
打算|dǎ suàn|跟她结婚|gēn tā jié hūn|结婚她 结她婚|{S} [plan] to marry her.|s
应该|yīng gāi|向老师道歉|xiàng lǎo shī dào qiàn|道歉老师 道老师歉|{S} should apologise to the teacher.|
常常|cháng cháng|跟朋友聊天|gēn péng you liáo tiān|聊天朋友 聊朋友天|{S} often [chat] with friends.|
不想|bù xiǎng|跟同学吵架|gēn tóng xué chǎo jià|吵架同学 吵同学架|{S} {dont} want to quarrel with classmates.|
去年|qù nián|从北京大学毕业|cóng běi jīng dà xué bì yè|毕业北京大学 毕北京大学业|{S} graduated from Peking University last year.|
昨天|zuó tiān|跟老师见了面|gēn lǎo shī jiàn le miàn|见面了老师 见了面老师|{S} met the teacher yesterday.|
昨天|zuó tiān|帮了他一个忙|bāng le tā yī gè máng|帮忙了他一个 帮了一个忙他|{S} did him a favour yesterday.|
周末要|zhōu mò yào|跟朋友见面|gēn péng you jiàn miàn|见面朋友 见朋友面|{S} {is} going to meet friends at the weekend.|
明天想|míng tiān xiǎng|跟同事聊天|gēn tóng shì liáo tiān|聊天同事 聊同事天|{S} [want] to chat with colleagues tomorrow.|
`);

const INSIDE_WHY = (v, o, what) =>
  `${v}${o} is verb + object, not one solid verb, so ${what} goes between ${v} and ${o}. Nothing can be attached after the object ${o}.`;

/** Verb, time and duration for a 了 + duration item. */
function timed(rng) {
  const [v, vpy, o, opy, en, unit] = pick(rng, TIMED);
  const [, d, dpy, den] = pick(
    rng,
    DURATIONS.filter((x) => x[0] === unit)
  );
  const [, t, tpy, ten] = pick(
    rng,
    WHEN.filter((x) => x[0] === unit)
  );
  return { v, vpy, o, opy, en, d, dpy, den, t, tpy, ten };
}

function makeInsideCloze(rng) {
  const s = pick(rng, PEOPLE);
  if (rng() < 0.55) {
    const x = timed(rng);
    return cloze(rng, {
      key: 'separable-cloze',
      pre: [s, part(x.t, x.tpy), part(x.v, x.vpy)],
      post: ['。'],
      right: part(`了${x.d}${x.o}`, `le ${x.dpy} ${x.opy}`),
      wrong: [`${x.o}了${x.d}`, `${x.d}了${x.o}`, `了${x.o}${x.d}`],
      en: fillEn(x.en, s).replace('{d}', x.den).replace('{t}', x.ten),
      why: INSIDE_WHY(x.v, x.o, `了 and the duration ${x.d}`),
    });
  }
  const [v, vpy, o, opy, lead, leadpy, en, c] = pick(rng, EXPERIENCE);
  const single = v === '结' ? PEOPLE.filter((p) => p.be !== 'are') : PEOPLE;
  const who = pick(rng, single);
  const head = [who, lead && part(lead, leadpy), part(v, vpy)];
  if (c && rng() < 0.5) {
    const [n, npy, nen] = pick(rng, COUNTS);
    return cloze(rng, {
      key: 'separable-cloze',
      pre: head,
      post: ['。'],
      right: part(`过${n}${o}`, `guo ${npy} ${opy}`),
      wrong: [`${o}过${n}`, `${n}过${o}`, `过${o}${n}`],
      en: fillEn(`{S} {have} ${en} ${nen}.`, who),
      why: INSIDE_WHY(v, o, `过 and the count ${n}`),
    });
  }
  return cloze(rng, {
    key: 'separable-cloze',
    pre: head,
    post: ['。'],
    right: part(`过${o}`, `guo ${opy}`),
    wrong: [`${o}过`, `${o}了过`],
    en: fillEn(`{S} {have} ${en} before.`, who),
    why: INSIDE_WHY(v, o, '过'),
  });
}

function makePartnerCloze(rng) {
  const [lead, leadpy, right, rightpy, wrong, en, one] = pick(rng, PARTNERED);
  const s = pick(rng, one ? PEOPLE.filter((p) => p.be !== 'are') : PEOPLE);
  return cloze(rng, {
    key: 'separable-cloze',
    pre: [s, part(lead, leadpy)],
    post: ['。'],
    right: part(right, rightpy),
    wrong: wrong.split(' '),
    en: fillEn(en, s),
    why: 'A verb-object compound already has its object inside it, so it cannot take another one after it. The person is brought in with a preposition before the verb (跟 / 向 / 从 …) or with 的 inside the compound.',
  });
}

function makeSeparableOrder(rng) {
  const s = pick(rng, PEOPLE);
  if (rng() < 0.6) {
    const x = timed(rng);
    return order(rng, {
      key: 'separable-order',
      tiles: [
        s,
        part(x.t, x.tpy),
        part(`${x.v}了`, `${x.vpy} le`),
        part(x.d, x.dpy),
        part(x.o, x.opy),
      ],
      alts: [[1, 0, 2, 3, 4]],
      en: fillEn(x.en, s).replace('{d}', x.den).replace('{t}', x.ten),
      why: `${INSIDE_WHY(x.v, x.o, `了 and the duration ${x.d}`)} Only the time word ${x.t} may also open the sentence.`,
    });
  }
  const [v, vpy, o, opy, lead, leadpy, en] = pick(
    rng,
    EXPERIENCE.filter((r) => r[7] === 'c')
  );
  const who =
    v === '结'
      ? pick(
          rng,
          PEOPLE.filter((p) => p.be !== 'are')
        )
      : s;
  const [n, npy, nen] = pick(rng, COUNTS);
  return order(rng, {
    key: 'separable-order',
    tiles: [
      who,
      lead && part(lead, leadpy),
      part(`${v}过`, `${vpy} guo`),
      part(n, npy),
      part(o, opy),
    ].filter(Boolean),
    en: fillEn(`{S} {have} ${en} ${nen}.`, who),
    why: INSIDE_WHY(v, o, `过 and the count ${n}`),
  });
}

function makeSeparableCloze(rng) {
  return weighted(rng, [
    [7, makeInsideCloze],
    [3, makePartnerCloze],
  ])(rng);
}

export const generators = [
  { key: 'separable-cloze', label: 'What goes inside the verb', make: makeSeparableCloze },
  { key: 'separable-order', label: 'Separable verb order', make: makeSeparableOrder },
];
