/**
 * bu-mei generator: 不 or 没, forced by a time word or by the kind of verb.
 * Frames where both are possible with different meanings (他不来 / 他没来
 * with no time word, 没想, 没能) are left out.
 */
import { pick, weighted, rows, cloze, PEOPLE, fillEn } from './util.js';

const BU = '不|bù';
const MEI = '没|méi';
const two = (rng, mei, opts) =>
  cloze(rng, { key: 'bu-mei', right: mei ? MEI : BU, wrong: [mei ? BU : MEI], ...opts });

// action | py | English base form
const ACTIONS = rows(`
去学校|qù xué xiào|go to school
去上班|qù shàng bān|go to work
来|lái|come
看电视|kàn diàn shì|watch TV
做作业|zuò zuò yè|do homework
买东西|mǎi dōng xi|go shopping
喝咖啡|hē kā fēi|drink coffee
洗衣服|xǐ yī fu|do the laundry
出门|chū mén|go out
去图书馆|qù tú shū guǎn|go to the library
参加会议|cān jiā huì yì|attend the meeting
去超市|qù chāo shì|go to the supermarket
回家吃饭|huí jiā chī fàn|come home to eat
去公园跑步|qù gōng yuán pǎo bù|go running in the park
坐地铁|zuò dì tiě|take the subway
做饭|zuò fàn|cook
去医院|qù yī yuàn|go to the hospital
`);
const PAST = rows(`
昨天|zuó tiān|yesterday
昨天晚上|zuó tiān wǎn shang|last night
今天早上|jīn tiān zǎo shang|this morning
前天|qián tiān|the day before yesterday
上个周末|shàng ge zhōu mò|last weekend
`);
const FUTURE = rows(`
明天|míng tiān|tomorrow
明天晚上|míng tiān wǎn shang|tomorrow evening
后天|hòu tiān|the day after tomorrow
这个周末|zhè ge zhōu mò|this weekend
今天晚上|jīn tiān wǎn shang|tonight
`);

// habit | py | English base form
const HABITS = rows(`
喝咖啡|hē kā fēi|drink coffee
吃早饭|chī zǎo fàn|eat breakfast
喝酒|hē jiǔ|drink alcohol
抽烟|chōu yān|smoke
吃肉|chī ròu|eat meat
看电视|kàn diàn shì|watch TV
坐地铁|zuò dì tiě|take the subway
做饭|zuò fàn|cook
吃辣的|chī là de|eat spicy food
喝牛奶|hē niú nǎi|drink milk
吃甜的东西|chī tián de dōng xi|eat sweet things
开车上班|kāi chē shàng bān|drive to work
在家吃晚饭|zài jiā chī wǎn fàn|eat dinner at home
玩游戏|wán yóu xì|play games
喝冷水|hē lěng shuǐ|drink cold water
`);
const USUALLY = rows(`
平时|píng shí|usually
一般|yī bān|generally
周末|zhōu mò|at weekends
`);

// thing one has | py | English
const HAVES = rows(`
时间|shí jiān|time
钱|qián|money
空|kòng|any free time
车|chē|a car
手机|shǒu jī|a phone
自行车|zì xíng chē|a bicycle
护照|hù zhào|a passport
电脑|diàn nǎo|a computer
兄弟姐妹|xiōng dì jiě mèi|any brothers or sisters
中文名字|zhōng wén míng zi|a Chinese name
问题|wèn tí|any questions
信用卡|xìn yòng kǎ|a credit card
`);

// identity | py | English singular | plural
const IDENTITIES = rows(`
老师|lǎo shī|a teacher|teachers
学生|xué sheng|a student|students
医生|yī shēng|a doctor|doctors
中国人|zhōng guó rén|Chinese|Chinese
美国人|měi guó rén|American|American
北京人|běi jīng rén|from Beijing|from Beijing
大学生|dà xué shēng|a university student|university students
`);

// experience | py | English past participle phrase
const EXPERIENCES = rows(`
去过中国|qù guo zhōng guó|been to China
吃过北京烤鸭|chī guo běi jīng kǎo yā|eaten Peking duck
看过这个电影|kàn guo zhè ge diàn yǐng|seen this film
学过汉语|xué guo hàn yǔ|studied Chinese
喝过中国茶|hē guo zhōng guó chá|drunk Chinese tea
坐过飞机|zuò guo fēi jī|been on a plane
听过这首歌|tīng guo zhè shǒu gē|heard this song
来过这儿|lái guo zhè r|been here
用过这个手机|yòng guo zhè ge shǒu jī|used this phone
爬过长城|pá guo cháng chéng|climbed the Great Wall
骑过马|qí guo mǎ|ridden a horse
见过大熊猫|jiàn guo dà xióng māo|seen a giant panda
去过上海|qù guo shàng hǎi|been to Shanghai
吃过火锅|chī guo huǒ guō|eaten hotpot
学过游泳|xué guo yóu yǒng|learned to swim
`);

// stative or modal predicate | py | English with {S}; "f" needs a future time word
const STATES = rows(`
会开车|huì kāi chē|{S} can't drive.|
会游泳|huì yóu yǒng|{S} can't swim.|
会说日语|huì shuō rì yǔ|{S} can't speak Japanese.|
会做饭|huì zuò fàn|{S} can't cook.|
会用筷子|huì yòng kuài zi|{S} can't use chopsticks.|
知道这件事|zhī dào zhè jiàn shì|{S} {dont} know about this.|
知道他的名字|zhī dào tā de míng zi|{S} {dont} know his name.|
认识那个人|rèn shi nà ge rén|{S} {dont} know that person.|
认识这个字|rèn shi zhè ge zì|{S} {dont} know this character.|
喜欢吃鱼|xǐ huan chī yú|{S} {dont} like eating fish.|
喜欢运动|xǐ huan yùn dòng|{S} {dont} like exercise.|
喜欢喝茶|xǐ huan hē chá|{S} {dont} like tea.|
喜欢夏天|xǐ huan xià tiān|{S} {dont} like summer.|
愿意搬家|yuàn yì bān jiā|{S} {is} not willing to move house.|
应该迟到|yīng gāi chí dào|{S} shouldn't be late.|
想去|xiǎng qù|{S} {dont} want to go {t}.|f
想上班|xiǎng shàng bān|{S} {dont} want to go to work {t}.|f
能来|néng lái|{S} can't come {t}.|f
能参加会议|néng cān jiā huì yì|{S} can't attend the meeting {t}.|f
可以休息|kě yǐ xiū xi|{S} can't take a rest {t}.|f
用上班|yòng shàng bān|{S} {dont} have to work {t}.|f
`);

// verb + result | py | object | py | English base form | y = only in the 还没…呢 frame
const RESULTS = rows(`
听懂|tīng dǒng|老师的话|lǎo shī de huà|understand what the teacher said
看懂|kàn dǒng|那封信|nà fēng xìn|understand that letter
看见|kàn jiàn|通知|tōng zhī|see the notice
找到|zhǎo dào|钥匙|yào shi|find the keys
买到|mǎi dào|火车票|huǒ chē piào|manage to buy a train ticket
做完|zuò wán|作业|zuò yè|finish the homework
吃完|chī wán|饭|fàn|finish eating
看完|kàn wán|那本书|nà běn shū|finish that book
写完|xiě wán|报告|bào gào|finish the report
记住|jì zhù|那个地址|nà ge dì zhǐ|remember that address|y
听见|tīng jiàn|电话铃声|diàn huà líng shēng|hear the phone ring
学会|xué huì|游泳|yóu yǒng|learn to swim|y
洗完|xǐ wán|衣服|yī fu|finish the laundry
收到|shōu dào|那封邮件|nà fēng yóu jiàn|receive that email
见到|jiàn dào|李老师|lǐ lǎo shī|get to see Mr. Li
`);

// subject + adjective sentences: subject | py | adjective | py | English
const ADJECTIVES = rows(`
今天|jīn tiān|冷|lěng|It is not cold today.
今天|jīn tiān|热|rè|It is not hot today.
这个菜|zhè ge cài|辣|là|This dish is not spicy.
这个菜|zhè ge cài|贵|guì|This dish is not expensive.
这件衣服|zhè jiàn yī fu|贵|guì|This piece of clothing is not expensive.
这件衣服|zhè jiàn yī fu|便宜|pián yi|This piece of clothing is not cheap.
这个问题|zhè ge wèn tí|难|nán|This question is not hard.
这个问题|zhè ge wèn tí|简单|jiǎn dān|This question is not simple.
我家|wǒ jiā|远|yuǎn|My home is not far.
我家|wǒ jiā|大|dà|My home is not big.
那个房间|nà ge fáng jiān|大|dà|That room is not big.
那个房间|nà ge fáng jiān|干净|gān jìng|That room is not clean.
这本书|zhè běn shū|厚|hòu|This book is not thick.
这本书|zhè běn shū|难|nán|This book is not hard.
这个手机|zhè ge shǒu jī|贵|guì|This phone is not expensive.
这个手机|zhè ge shǒu jī|好用|hǎo yòng|This phone is not easy to use.
地铁站|dì tiě zhàn|远|yuǎn|The subway station is not far.
这家饭馆|zhè jiā fàn guǎn|贵|guì|This restaurant is not expensive.
这家饭馆|zhè jiā fàn guǎn|好吃|hǎo chī|This restaurant is not good.
汉语|hàn yǔ|难|nán|Chinese is not hard.
这杯咖啡|zhè bēi kā fēi|甜|tián|This coffee is not sweet.
那个电影|nà ge diàn yǐng|好看|hǎo kàn|That film is not good.
他的个子|tā de gè zi|高|gāo|He is not tall.
这条路|zhè tiáo lù|长|cháng|This road is not long.
这双鞋|zhè shuāng xié|舒服|shū fu|These shoes are not comfortable.
`);

const WHY = {
  past: (t) =>
    `${t} puts the action in the past, and something that did not happen is negated with 没. 不 would be for a habit, a refusal or the future.`,
  future: (t) =>
    `${t} is in the future, so this is "won't": future and intended actions are negated with 不. 没 only denies that something has happened.`,
  habit: (t) =>
    `${t} marks a habit, and what someone does not usually do is negated with 不. 没 would deny one particular past occasion.`,
  have: '有 is only ever negated with 没: 没有. 不有 does not exist.',
  be: '是 is always negated with 不: 不是. 没是 does not exist.',
  guo: 'With 过 the sentence is about experience up to now, and "have never" is 没 + verb + 过. 不 cannot be used with 过.',
  state: (p) =>
    `${p} is a state, ability or attitude, not an event that happened, so it is negated with 不. 没 denies that an action took place.`,
  result: (v) =>
    `${v} is a verb plus result, and saying that the result was not reached is 没 + verb + result. 不${v} is not possible for a past fact.`,
  yet: '还…呢 means "not yet": something that has not happened so far is negated with 没. 不 would mean refusing or never doing it.',
  adj: (a) =>
    `${a} is an adjective describing how things are, and adjectives are negated with 不. 没 does not negate a plain quality.`,
};

const part = (zh, py) => ({ zh, py });

function makeBuMei(rng) {
  const kind = weighted(rng, [
    [16, 'past'],
    [14, 'future'],
    [12, 'habit'],
    [9, 'have'],
    [7, 'be'],
    [10, 'guo'],
    [14, 'state'],
    [9, 'result'],
    [6, 'yet'],
    [8, 'adj'],
  ]);
  const s = pick(rng, PEOPLE);
  const end = ['。'];
  if (kind === 'past' || kind === 'future') {
    const past = kind === 'past';
    const [t, tpy, ten] = pick(rng, past ? PAST : FUTURE);
    const [a, apy, aen] = pick(rng, ACTIONS);
    return two(rng, past, {
      pre: [s, part(t, tpy)],
      post: [part(a, apy), ...end],
      en: `${s.en} ${past ? "didn't" : "won't"} ${aen} ${ten}.`,
      why: past ? WHY.past(t) : WHY.future(t),
    });
  }
  if (kind === 'habit') {
    const [t, tpy, ten] = pick(rng, USUALLY);
    const [a, apy, aen] = pick(rng, HABITS);
    const en =
      t === '周末'
        ? fillEn(`{S} {dont} ${aen} ${ten}.`, s)
        : fillEn(`{S} ${ten} {dont} ${aen}.`, s);
    return two(rng, false, {
      pre: [s, part(t, tpy)],
      post: [part(a, apy), ...end],
      en,
      why: WHY.habit(t),
    });
  }
  if (kind === 'have') {
    const [n, npy, nen] = pick(rng, HAVES);
    return two(rng, true, {
      pre: [s],
      post: ['有|yǒu', part(n, npy), ...end],
      en: fillEn(`{S} {dont} have ${nen}.`, s),
      why: WHY.have,
    });
  }
  if (kind === 'be') {
    const [n, npy, sg, pl] = pick(rng, IDENTITIES);
    const who = s.zh === '我同学' ? PEOPLE[0] : s;
    return two(rng, false, {
      pre: [who],
      post: ['是|shì', part(n, npy), ...end],
      en: `${who.en} ${who.be} not ${who.be === 'are' ? pl : sg}.`,
      why: WHY.be,
    });
  }
  if (kind === 'guo') {
    const [x, xpy, xen] = pick(rng, EXPERIENCES);
    return two(rng, true, {
      pre: [s],
      post: [part(x, xpy), ...end],
      en: fillEn(`{S} {have} never ${xen}.`, s),
      why: WHY.guo,
    });
  }
  if (kind === 'state') {
    const [p, ppy, en, f] = pick(rng, STATES);
    const [t, tpy, ten] = pick(rng, FUTURE);
    return two(rng, false, {
      pre: f ? [s, part(t, tpy)] : [s],
      post: [part(p, ppy), ...end],
      en: fillEn(en, s).replace('{t}', ten),
      why: WHY.state(p),
    });
  }
  if (kind === 'result' || kind === 'yet') {
    const [v, vpy, o, opy, en] = pick(
      rng,
      RESULTS.filter((x) => kind === 'yet' || !x[5])
    );
    if (kind === 'yet') {
      return two(rng, true, {
        pre: [s, '还|hái'],
        post: [part(v, vpy), part(o, opy), '呢|ne', ...end],
        en: fillEn(`{S} {have}n't managed to ${en} yet.`, s),
        why: WHY.yet,
      });
    }
    const [t, tpy, ten] = pick(rng, PAST.slice(0, 2));
    return two(rng, true, {
      pre: [s, part(t, tpy)],
      post: [part(v, vpy), part(o, opy), ...end],
      en: `${s.en} didn't ${en} ${ten}.`,
      why: WHY.result(v),
    });
  }
  const [subj, spy, a, apy, en] = pick(rng, ADJECTIVES);
  const tai = rng() < 0.4;
  return two(rng, false, {
    pre: [part(subj, spy)],
    post: [tai && '太|tài', part(a, apy), ...end],
    en: tai ? en.replace(' not ', ' not very ') : en,
    why: WHY.adj(a),
  });
}

export const generators = [{ key: 'bu-mei', label: '不 or 没', make: makeBuMei }];
