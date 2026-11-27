/**
 * duration-frequency generator: order tiles for duration after the verb
 * (学了两年的汉语), a person object before the duration (等了他半个小时),
 * times after the verb (去过两次北京), duration before a negated verb
 * (两天没睡觉了) and the double 了 for "so far".
 *
 * Thing objects with 次 / 遍 are left out: 看过三遍这个电影, 这个电影看过三遍
 * and 看过这个电影三遍 are all heard, so no tile cut gives a single answer.
 */
import { pick, weighted, rows, order, PEOPLE, fillEn } from './util.js';

const part = (zh, py) => ({ zh, py });
const KEY = 'duration-order';

// unit | duration | py | English
const DURATIONS = rows(`
h|半个小时|bàn gè xiǎo shí|half an hour
h|一个小时|yī gè xiǎo shí|an hour
h|两个小时|liǎng gè xiǎo shí|two hours
h|三个小时|sān gè xiǎo shí|three hours
h|一个半小时|yī gè bàn xiǎo shí|an hour and a half
h|四个小时|sì gè xiǎo shí|four hours
n|十分钟|shí fēn zhōng|ten minutes
n|二十分钟|èr shí fēn zhōng|twenty minutes
n|半个小时|bàn gè xiǎo shí|half an hour
n|四十分钟|sì shí fēn zhōng|forty minutes
m|两个月|liǎng gè yuè|two months
m|三个月|sān gè yuè|three months
m|半年|bàn nián|half a year
m|六个月|liù gè yuè|six months
y|一年|yī nián|a year
y|两年|liǎng nián|two years
y|三年|sān nián|three years
y|五年|wǔ nián|five years
y|十年|shí nián|ten years
d|一天|yī tiān|a day
d|两天|liǎng tiān|two days
d|三天|sān tiān|three days
w|一个星期|yī gè xīng qī|a week
w|两个星期|liǎng gè xīng qī|two weeks
w|三个星期|sān gè xīng qī|three weeks
`);
const durations = (units) => DURATIONS.filter((d) => units.includes(d[0]));

// verb | py | object | py | English with {S} and {d} | duration units
const ACTIVITIES = rows(`
学|xué|汉语|hàn yǔ|{S} studied Chinese for {d}.|my
学|xué|游泳|yóu yǒng|{S} took swimming lessons for {d}.|m
学|xué|开车|kāi chē|{S} took driving lessons for {d}.|mw
看|kàn|电视|diàn shì|{S} watched TV for {d}.|h
看|kàn|书|shū|{S} read for {d}.|h
坐|zuò|飞机|fēi jī|{S} flew for {d}.|h
坐|zuò|火车|huǒ chē|{S} was on the train for {d}.|h
坐|zuò|地铁|dì tiě|{S} rode the subway for {d}.|n
打|dǎ|篮球|lán qiú|{S} played basketball for {d}.|h
打|dǎ|电话|diàn huà|{S} talked on the phone for {d}.|n
上|shàng|课|kè|{S} had class for {d}.|h
开|kāi|车|chē|{S} drove for {d}.|h
开|kāi|会|huì|{S} sat in a meeting for {d}.|h
做|zuò|作业|zuò yè|{S} did homework for {d}.|h
做|zuò|饭|fàn|{S} cooked for {d}.|h
听|tīng|音乐|yīn yuè|{S} listened to music for {d}.|h
弹|tán|钢琴|gāng qín|{S} played the piano for {d}.|hy
玩|wán|游戏|yóu xì|{S} played games for {d}.|h
排|pái|队|duì|{S} queued for {d}.|n
上|shàng|网|wǎng|{S} spent {d} online.|h
当|dāng|老师|lǎo shī|{S} worked as a teacher for {d}.|y
教|jiāo|英语|yīng yǔ|{S} taught English for {d}.|y
骑|qí|自行车|zì xíng chē|{S} cycled for {d}.|hn
等|děng|车|chē|{S} waited for the bus for {d}.|n
写|xiě|报告|bào gào|{S} worked on the report for {d}.|h
踢|tī|足球|zú qiú|{S} played football for {d}.|h
跳|tiào|舞|wǔ|{S} danced for {d}.|h
唱|chàng|歌|gē|{S} sang for {d}.|h
`);

// verb | py | English past | duration units
const PERSON_VERBS = rows(`
等|děng|waited for|nh
找|zhǎo|looked for|nh
陪|péi|kept {p} company for|hd
教|jiāo|taught|my
照顾|zhào gù|looked after|dwm
`);
const OBJECTS = rows(`
他|tā|him
她|tā|her
我|wǒ|me
老师|lǎo shī|the teacher
孩子|hái zi|the child
奶奶|nǎi nai|Grandma
朋友|péng you|a friend
`);

const PLACES = rows(`
北京|běi jīng|Beijing
上海|shàng hǎi|Shanghai
中国|zhōng guó|China
日本|rì běn|Japan
长城|cháng chéng|the Great Wall
西安|xī ān|Xi'an
香港|xiāng gǎng|Hong Kong
美国|měi guó|the USA
那个公园|nà ge gōng yuán|that park
那家饭馆|nà jiā fàn guǎn|that restaurant
`);
const COUNTS = rows(`
一次|yī cì|once
两次|liǎng cì|twice
三次|sān cì|three times
很多次|hěn duō cì|many times
几次|jǐ cì|a few times
`);
const PRONOUN_VERBS = rows(`
见过|jiàn guo|met
找过|zhǎo guo|looked for
问过|wèn guo|asked
帮过|bāng guo|helped
请过|qǐng guo|invited
`);
const PRONOUNS = rows(`
他|tā|him
她|tā|her
我|wǒ|me
他们|tā men|them
`);

// verb phrase | py | English participle | s = short gaps only
const GAPS = rows(`
回家|huí jiā|been home|
睡觉|shuì jiào|slept|s
喝咖啡|hē kā fēi|had coffee|
上课|shàng kè|been to class|s
看电影|kàn diàn yǐng|seen a film|
出门|chū mén|been out|s
运动|yùn dòng|exercised|
吃肉|chī ròu|eaten meat|
抽烟|chōu yān|smoked|
喝酒|hē jiǔ|had a drink|
给家里打电话|gěi jiā lǐ dǎ diàn huà|called home|
休息|xiū xi|had a rest|s
上班|shàng bān|been to work|s
做饭|zuò fàn|cooked|
看书|kàn shū|read a book|
`);
const GAP_DURATIONS = rows(`
s|两天|liǎng tiān|two days
s|三天|sān tiān|three days
s|好几天|hǎo jǐ tiān|several days
s|一个星期|yī gè xīng qī|a week
l|一个月|yī gè yuè|a month
l|两个月|liǎng gè yuè|two months
l|半年|bàn nián|half a year
l|一年|yī nián|a year
l|很久|hěn jiǔ|a long time
`);

// verb | py | English participle | duration units
const ONGOING = rows(`
等|děng|been waiting|nh
睡|shuì|been asleep|h
工作|gōng zuò|been working|h
休息|xiū xi|been resting|d
病|bìng|been ill|dw
走|zǒu|been walking|h
学|xué|been studying|h
忙|máng|been busy|dw
找|zhǎo|been searching|nh
`);

function makeDuration(rng) {
  const s = pick(rng, PEOPLE);
  const kind = weighted(rng, [
    [4, 'de'],
    [3, 'plain'],
    [3, 'person'],
    [2, 'place'],
    [2, 'pronoun'],
    [3, 'gap'],
    [2, 'ongoing'],
  ]);
  if (kind === 'de' || kind === 'plain') {
    const [v, vpy, o, opy, en, units] = pick(rng, ACTIVITIES);
    const [, d, dpy, den] = pick(rng, durations(units));
    const english = fillEn(en, s)
      .replace('{d}', den)
      .replace(/^(We|They) was/, '$1 were')
      .replace(/^I was/, 'I was');
    const verb = part(`${v}了`, `${vpy} le`);
    if (kind === 'de') {
      return order(rng, {
        key: KEY,
        tiles: [s, verb, part(`${d}的`, `${dpy} de`), part(o, opy)],
        en: english,
        why: `How long goes after the verb, not before it: verb + 了 + duration + 的 + object. ${d}的 sits between ${v}了 and ${o}; a duration before the verb would be wrong here.`,
      });
    }
    return order(rng, {
      key: KEY,
      tiles: [s, verb, part(d, dpy), part(o, opy)],
      alts: [
        [3, 0, 1, 2],
        [0, 3, 1, 2],
      ],
      en: english,
      why: `How long goes right after verb + 了 and before the object: ${v}了 + ${d} + ${o}. The object can only escape by moving in front of the verb as a topic; the duration never comes before the verb.`,
    });
  }
  if (kind === 'person') {
    const [v, vpy, en, units] = pick(rng, PERSON_VERBS);
    const [o, opy, oen] = pick(
      rng,
      OBJECTS.filter((x) => x[0] !== s.zh && !(x[0] === '朋友' && s.zh === '我朋友'))
    );
    const [, d, dpy, den] = pick(rng, durations(units));
    const phrase = en.includes('{p}') ? en.replace('{p}', oen) : `${en} ${oen} for`;
    return order(rng, {
      key: KEY,
      tiles: [s, part(`${v}了`, `${vpy} le`), part(o, opy), part(d, dpy)],
      en: `${s.en} ${phrase} ${den}.`,
      why: `When the object is a person, it comes straight after the verb and the duration follows it: ${v}了 + ${o} + ${d}. The duration cannot come before the verb.`,
    });
  }
  if (kind === 'place') {
    const [p, ppy, pen] = pick(rng, PLACES);
    const [c, cpy, cen] = pick(rng, COUNTS);
    return order(rng, {
      key: KEY,
      tiles: [s, '去过|qù guo', part(c, cpy), part(p, ppy)],
      alts: [
        [0, 1, 3, 2],
        [3, 0, 1, 2],
      ],
      en: fillEn(`{S} {have} been to ${pen} ${cen}.`, s),
      why: `How many times goes after the verb: 去过 + ${c}. With a place as object, ${c} may come before or after ${p}, but never before the verb as in "twice went".`,
    });
  }
  if (kind === 'pronoun') {
    const [v, vpy, ven] = pick(rng, PRONOUN_VERBS);
    const [o, opy, oen] = pick(
      rng,
      PRONOUNS.filter((x) => x[0] !== s.zh)
    );
    const [c, cpy, cen] = pick(rng, COUNTS);
    return order(rng, {
      key: KEY,
      tiles: [s, part(v, vpy), part(o, opy), part(c, cpy)],
      en: fillEn(`{S} {have} ${ven} ${oen} ${cen}.`, s),
      why: `A pronoun object comes directly after the verb, and the number of times follows it: ${v} + ${o} + ${c}. ${c} cannot stand before the verb or before the pronoun.`,
    });
  }
  if (kind === 'gap') {
    const [g, gpy, gen, short] = pick(rng, GAPS);
    const [, d, dpy, den] = pick(
      rng,
      GAP_DURATIONS.filter((x) => !short || x[0] === 's')
    );
    return order(rng, {
      key: KEY,
      tiles: [s, part(d, dpy), '没|méi', part(g, gpy), '了|le'],
      en: fillEn(`{S} {have}n't ${gen} for ${den}.`, s),
      why: `For something that has not happened, the length of time goes BEFORE the negated verb: ${d} + 没 + verb, with 了 at the end for "so far". After the verb, a duration says how long the action lasted.`,
    });
  }
  const [v, vpy, ven, units] = pick(rng, ONGOING);
  const [, d, dpy, den] = pick(rng, durations(units));
  return order(rng, {
    key: KEY,
    tiles: [s, part(`${v}了`, `${vpy} le`), part(d, dpy), '了|le'],
    en: fillEn(`{S} {have} ${ven} for ${den} now.`, s),
    why: `Duration follows verb + 了, and a second 了 at the very end says it is still going on: ${v}了 + ${d} + 了. Without the final 了 the action would be over.`,
  });
}

export const generators = [
  { key: KEY, label: 'Duration and times: where they go', make: makeDuration },
];
