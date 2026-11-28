/**
 * tone-sandhi generators: the tone of 不, the tone of 一, and two third
 * tones in a row. Options are pinyin; `zh` is the phrase followed by its
 * real pronunciation, and `py` is that pronunciation.
 */
import { pick, weighted, shuffle, rows, PEOPLE, fillEn, dont } from './util.js';
import { MEASURES, NOUNS } from './measure-words.js';
import { readNumber } from './numbers-time.js';

const MARKED = { a: 'āáǎà', e: 'ēéěè', i: 'īíǐì', o: 'ōóǒò', u: 'ūúǔù', ü: 'ǖǘǚǜ' };

/** Tone of one pinyin syllable: 1-4, or 5 for neutral. */
export function toneOf(syl) {
  for (const marks of Object.values(MARKED)) {
    for (let t = 0; t < 4; t++) if (syl.includes(marks[t])) return t + 1;
  }
  return 5;
}

/** The same syllable with another tone (1-4). */
export function setTone(syl, tone) {
  let base = syl;
  for (const [plain, marks] of Object.entries(MARKED)) {
    for (const m of marks) base = base.replace(m, plain);
  }
  let at = base.indexOf('a');
  if (at < 0) at = base.indexOf('e');
  if (at < 0 && base.includes('ou')) at = base.indexOf('o');
  if (at < 0) {
    for (let i = base.length - 1; i >= 0; i--) {
      if ('aeiouü'.includes(base[i])) {
        at = i;
        break;
      }
    }
  }
  return base.slice(0, at) + MARKED[base[at]][tone - 1] + base.slice(at + 1);
}

/** 不 is bú before a fourth tone, otherwise bù. */
export const buTone = (next) => (toneOf(next) === 4 ? 'bú' : 'bù');

/**
 * 一 before a word: yí before a fourth tone, yì before a first, second or
 * third tone. As an ordinal, a digit, in counting or at the end it is yī.
 */
export function yiTone(next, { ordinal = false } = {}) {
  if (ordinal || !next) return 'yī';
  return toneOf(next) === 4 ? 'yí' : 'yì';
}

/** A third tone before another third tone is said as a second tone. */
export function thirdPair(a, b) {
  return toneOf(a) === 3 && toneOf(b) === 3 ? [setTone(a, 2), b] : [a, b];
}

const TONE_NAME = ['', 'first', 'second', 'third', 'fourth', 'neutral'];

// word | pinyin | English | kind: v verb, ap adjective of people, at of things,
// aw weather, ad distance, x fixed English
export const WORDS = rows(`
去|qù|go|v
来|lái|come|v
吃|chī|eat|v
喝|hē|drink|v
看|kàn|look|v
听|tīng|listen|v
说|shuō|speak|v
买|mǎi|buy it|v
卖|mài|sell it|v
要|yào|want it|v
想|xiǎng|want to|v
走|zǒu|leave|v
跑|pǎo|run|v
写|xiě|write|v
学|xué|study|v
问|wèn|ask|v
做|zuò|do it|v
坐|zuò|sit down|v
睡|shuì|sleep|v
用|yòng|use it|v
懂|dǒng|understand|v
等|děng|wait|v
找|zhǎo|look for it|v
洗|xǐ|wash it|v
玩|wán|play|v
穿|chuān|wear it|v
信|xìn|believe it|v
笑|xiào|laugh|v
哭|kū|cry|v
唱|chàng|sing|v
跳|tiào|jump|v
回家|huí jiā|go home|v
搬家|bān jiā|move house|v
帮忙|bāng máng|help out|v
请假|qǐng jià|ask for leave|v
散步|sàn bù|go for walks|v
聊天|liáo tiān|chat|v
知道|zhī dào|know|v
认识|rèn shi|know him|v
喜欢|xǐ huan|like it|v
同意|tóng yì|agree|v
明白|míng bai|understand|v
相信|xiāng xìn|believe it|v
记得|jì de|remember|v
担心|dān xīn|worry|v
介意|jiè yì|mind|v
需要|xū yào|need it|v
上班|shàng bān|go to work|v
上课|shàng kè|go to class|v
睡觉|shuì jiào|go to bed|v
看书|kàn shū|read|v
看电视|kàn diàn shì|watch TV|v
做饭|zuò fàn|cook|v
运动|yùn dòng|exercise|v
唱歌|chàng gē|sing|v
跳舞|tiào wǔ|dance|v
开车|kāi chē|drive|v
抽烟|chōu yān|smoke|v
喝酒|hē jiǔ|drink alcohol|v
喝茶|hē chá|drink tea|v
吃肉|chī ròu|eat meat|v
说话|shuō huà|talk|v
学习|xué xí|study|v
游泳|yóu yǒng|swim|v
打球|dǎ qiú|play ball|v
跑步|pǎo bù|go running|v
起床|qǐ chuáng|get up|v
考试|kǎo shì|take the exam|v
请客|qǐng kè|treat people|v
休息|xiū xi|rest|v
工作|gōng zuò|work|v
锻炼|duàn liàn|work out|v
加班|jiā bān|work overtime|v
出门|chū mén|go out|v
参加|cān jiā|take part|v
迟到|chí dào|arrive late|v
回答|huí dá|answer|v
旅行|lǚ xíng|travel|v
上网|shàng wǎng|go online|v
逛街|guàng jiē|go shopping|v
吃辣|chī là|eat spicy food|v
画画|huà huà|draw|v
结婚|jié hūn|get married|v
忙|máng|busy|ap
累|lèi|tired|ap
饿|è|hungry|ap
渴|kě|thirsty|ap
高|gāo|tall|ap
矮|ǎi|short|ap
胖|pàng|fat|ap
瘦|shòu|thin|ap
老|lǎo|old|ap
高兴|gāo xìng|happy|ap
开心|kāi xīn|happy|ap
紧张|jǐn zhāng|nervous|ap
满意|mǎn yì|satisfied|ap
舒服|shū fu|comfortable|ap
聪明|cōng ming|clever|ap
懒|lǎn|lazy|ap
怕|pà|afraid|ap
困|kùn|sleepy|ap
急|jí|in a hurry|ap
饱|bǎo|full|ap
客气|kè qi|polite|ap
愿意|yuàn yì|willing|ap
生气|shēng qì|angry|ap
着急|zháo jí|anxious|ap
难过|nán guò|sad|ap
放心|fàng xīn|at ease|ap
害怕|hài pà|scared|ap
好|hǎo|good|at
对|duì|right|at
错|cuò|bad|at
大|dà|big|at
小|xiǎo|small|at
贵|guì|expensive|at
便宜|pián yi|cheap|at
新|xīn|new|at
旧|jiù|old|at
长|cháng|long|at
短|duǎn|short|at
重|zhòng|heavy|at
轻|qīng|light|at
难|nán|hard|at
容易|róng yì|easy|at
简单|jiǎn dān|simple|at
好看|hǎo kàn|nice-looking|at
好吃|hǎo chī|tasty|at
好喝|hǎo hē|nice to drink|at
甜|tián|sweet|at
咸|xián|salty|at
酸|suān|sour|at
苦|kǔ|bitter|at
辣|là|spicy|at
干净|gān jìng|clean|at
脏|zāng|dirty|at
重要|zhòng yào|important|at
方便|fāng biàn|convenient|at
合适|hé shì|suitable|at
漂亮|piào liang|pretty|at
快|kuài|fast|at
慢|màn|slow|at
厚|hòu|thick|at
薄|báo|thin|at
硬|yìng|hard|at
软|ruǎn|soft|at
安全|ān quán|safe|at
危险|wēi xiǎn|dangerous|at
奇怪|qí guài|strange|at
麻烦|má fan|troublesome|at
冷|lěng|cold|aw
热|rè|hot|aw
凉快|liáng kuai|cool|aw
暖和|nuǎn huo|warm|aw
远|yuǎn|far|ad
近|jìn|near|ad
是|shì|{S} {is} not.|x
会|huì|{S} {dont} know how.|x
能|néng|{S} can't.|x
敢|gǎn|{S} {dont} dare.|x
应该|yīng gāi|{S} shouldn't.|x
在|zài|{S} {is} not in.|x
`).map(([zh, py, en, kind]) => ({ zh, py, en, kind }));

const THINGS = [
  { zh: '这个', py: 'zhè ge', en: 'This one is' },
  { zh: '那个', py: 'nà ge', en: 'That one is' },
];
const WEATHER = [
  { zh: '今天', py: 'jīn tiān', en: 'It is', tail: ' today' },
  { zh: '这儿', py: 'zhè r', en: 'It is', tail: ' here' },
  { zh: '外面', py: 'wài mian', en: 'It is', tail: ' outside' },
];
const PLACES = [
  { zh: '学校', py: 'xué xiào', en: 'The school is' },
  { zh: '我家', py: 'wǒ jiā', en: 'My home is' },
  { zh: '那儿', py: 'nà r', en: 'That place is' },
];

/** Cloze whose options are pinyin: `zh` is "phrase → pronunciation". */
function pinyinCloze(rng, { key, phrase, before, after, right, wrong, en, why, cue }) {
  const opts = shuffle(rng, [right, ...wrong]);
  const pre = before ? `${before} ` : '';
  const post = after ? ` ${after}` : '';
  return {
    id: `gen:${key}`,
    type: 'cloze',
    q: `${phrase} → ${pre}___${post}`,
    opts,
    a: opts.indexOf(right),
    zh: `${phrase} → ${pre}${right}${post}`,
    py: `${pre}${right}${post}`,
    en,
    why,
    cue,
  };
}

function makeBu(rng) {
  const word = pick(rng, WORDS);
  let s;
  let en;
  if (word.kind === 'at') {
    s = pick(rng, THINGS);
    en = `${s.en} not ${word.en}.`;
  } else if (word.kind === 'aw') {
    s = pick(rng, WEATHER);
    en = `${s.en} not ${word.en}${s.tail}.`;
  } else if (word.kind === 'ad') {
    s = pick(rng, PLACES);
    en = `${s.en} not ${word.en}.`;
  } else {
    s = pick(rng, PEOPLE);
    if (word.kind === 'x') en = fillEn(word.en, s);
    else if (word.kind === 'ap') en = `${s.en} ${s.be} not ${word.en}.`;
    else en = `${s.en} ${dont(s)} ${word.en}.`;
  }
  const first = word.py.split(' ')[0];
  const right = buTone(first);
  const tone = toneOf(first);
  return pinyinCloze(rng, {
    key: 'bu-tone',
    phrase: `${s.zh}不${word.zh}`,
    before: s.py,
    after: word.py,
    right,
    wrong: [right === 'bú' ? 'bù' : 'bú'],
    en,
    cue: 'Which tone does 不 have here?',
    why:
      tone === 4
        ? `${first} is a fourth tone, and before a fourth tone 不 rises to bú: ${right} ${word.py}. Before any other tone it stays bù.`
        : `${first} is a ${TONE_NAME[tone]} tone, so 不 keeps its own fourth tone bù. It only changes to bú before another fourth tone.`,
  });
}

// word with one 一 | pinyin as pronounced | English | "o" when 一 is an ordinal, digit or final
const YI_WORDS = rows(`
一个|yí gè|one (of something)|
一样|yí yàng|the same|
一定|yí dìng|definitely|
一共|yí gòng|altogether|
一下|yí xià|a moment, briefly|
一会儿|yí huì r|a little while|
一半|yí bàn|half|
一切|yí qiè|everything|
一路|yí lù|all the way|
一次|yí cì|once|
一件|yí jiàn|one item|
一位|yí wèi|one person (polite)|
一辆|yí liàng|one vehicle|
一遍|yí biàn|once through|
一岁|yí suì|one year old|
一刻|yí kè|a quarter of an hour|
一夜|yí yè|one night|
一句|yí jù|one sentence|
一块|yí kuài|one piece; one yuan|
一份|yí fèn|one portion|
一顿|yí dùn|one meal|
一套|yí tào|one set|
一座|yí zuò|one (mountain, building)|
一万|yí wàn|ten thousand|
一亿|yí yì|a hundred million|
一向|yí xiàng|all along|
一再|yí zài|again and again|
一致|yí zhì|unanimous|
一律|yí lǜ|without exception|
一辈子|yí bèi zi|a whole lifetime|
一部分|yí bù fen|a part|
一大早|yí dà zǎo|early in the morning|
一步|yí bù|one step|
一面|yí miàn|one side|
一段|yí duàn|a stretch|
一对|yí duì|a pair|
一趟|yí tàng|one trip|
一阵|yí zhèn|a spell|
一天|yì tiān|one day|
一些|yì xiē|some|
一般|yì bān|usually; ordinary|
一边|yì biān|one side; while|
一生|yì shēng|a whole life|
一张|yì zhāng|one sheet|
一杯|yì bēi|one cup|
一只|yì zhī|one (animal)|
一双|yì shuāng|one pair|
一家|yì jiā|one family; one business|
一间|yì jiān|one room|
一支|yì zhī|one (pen)|
一斤|yì jīn|half a kilo|
一千|yì qiān|one thousand|
一年|yì nián|one year|
一直|yì zhí|straight; all along|
一起|yì qǐ|together|
一点儿|yì diǎn r|a little|
一本|yì běn|one (book)|
一百|yì bǎi|one hundred|
一条|yì tiáo|one (long thing)|
一瓶|yì píng|one bottle|
一台|yì tái|one machine|
一层|yì céng|one layer|
一门|yì mén|one course|
一头|yì tóu|one (cow)|
一名|yì míng|one (person, by job)|
一群|yì qún|a group|
一种|yì zhǒng|one kind|
一把|yì bǎ|one (thing with a handle)|
一口|yì kǒu|one mouthful|
一碗|yì wǎn|one bowl|
一首|yì shǒu|one song|
一场|yì chǎng|one (match, show)|
一早|yì zǎo|early in the morning|
一秒|yì miǎo|one second|
一时|yì shí|for a moment|
一同|yì tóng|together|
一连|yì lián|in a row|
一旁|yì páng|to one side|
一身|yì shēn|all over the body|
一心|yì xīn|wholeheartedly|
一分钟|yì fēn zhōng|one minute|
一封|yì fēng|one (letter)|
一篇|yì piān|one (article)|
一棵|yì kē|one (tree)|
一节|yì jié|one (class period)|
一晚|yì wǎn|one evening|
一方面|yì fāng miàn|on the one hand|
第一|dì yī|first|o
第一次|dì yī cì|the first time|o
第一个|dì yī gè|the first one|o
第一天|dì yī tiān|the first day|o
第一名|dì yī míng|first place|o
第一课|dì yī kè|lesson one|o
一月|yī yuè|January|o
一号|yī hào|the 1st; number one|o
星期一|xīng qī yī|Monday|o
周一|zhōu yī|Monday|o
十一|shí yī|eleven|o
二十一|èr shí yī|twenty-one|o
三十一号|sān shí yī hào|the 31st|o
十一点|shí yī diǎn|eleven o'clock|o
十一月|shí yī yuè|November|o
一楼|yī lóu|the first floor|o
一年级|yī nián jí|first year (grade one)|o
一班|yī bān|class one|o
一号线|yī hào xiàn|Line 1|o
统一|tǒng yī|unified|o
唯一|wéi yī|the only one|o
万一|wàn yī|just in case|o
之一|zhī yī|one of|o
初一|chū yī|first day of the lunar month|o
一二三|yī èr sān|one, two, three|o
一九九八年|yī jiǔ jiǔ bā nián|the year 1998|o
`);

const YI_OPTS = ['yī', 'yí', 'yì'];
const YI_CUE = 'Which tone does 一 have here?';

function yiWhy(right, next) {
  if (right === 'yī') {
    return 'As an ordinal (第一, 一月, 一号, 一楼), as a digit inside or at the end of a number, and at the end of a word, 一 keeps its first tone yī whatever follows.';
  }
  const t = toneOf(next);
  return right === 'yí'
    ? `一 counts or modifies what follows, and ${next} is a fourth tone, so 一 rises to yí. Before first, second and third tones it is yì.`
    : `一 counts or modifies what follows, and ${next} is a ${TONE_NAME[t]} tone, so 一 falls to yì. Only before a fourth tone is it yí.`;
}

function makeYi(rng) {
  const kind = weighted(rng, [
    [30, 'word'],
    [40, 'one'],
    [15, 'first'],
    [15, 'tens'],
  ]);
  let phrase;
  let syl;
  let at;
  let en;
  if (kind === 'word') {
    const [zh, py, gloss] = pick(rng, YI_WORDS);
    phrase = zh;
    syl = py.split(' ');
    at = [...zh].indexOf('一');
    en = gloss;
  } else {
    const noun = pick(rng, NOUNS);
    const m = MEASURES[noun.ok[0]];
    const tail = [m.py, ...noun.py.split(' ')];
    if (kind === 'one') {
      phrase = `一${m.zh}${noun.zh}`;
      syl = [yiTone(m.py), ...tail];
      at = 0;
      en = `one ${noun.sg}`;
    } else if (kind === 'first') {
      phrase = `第一${m.zh}${noun.zh}`;
      syl = ['dì', 'yī', ...tail];
      at = 1;
      en = `the first ${noun.sg}`;
    } else {
      const tens = pick(rng, [1, 2, 3, 4, 5, 6, 7, 8, 9]);
      const head = readNumber(tens * 10 + 1);
      const headPy = {
        一: 'yī',
        二: 'èr',
        三: 'sān',
        四: 'sì',
        五: 'wǔ',
        六: 'liù',
        七: 'qī',
        八: 'bā',
        九: 'jiǔ',
        十: 'shí',
      };
      phrase = `${head}${m.zh}${noun.zh}`;
      syl = [...[...head].map((c) => headPy[c]), ...tail];
      at = head.length - 1;
      en = `${tens * 10 + 1} ${noun.pl}`;
    }
  }
  const right = syl[at];
  return pinyinCloze(rng, {
    key: 'yi-tone',
    phrase,
    before: syl.slice(0, at).join(' '),
    after: syl.slice(at + 1).join(' '),
    right,
    wrong: YI_OPTS.filter((o) => o !== right),
    en,
    cue: YI_CUE,
    why: yiWhy(right, syl[at + 1]),
  });
}

// two-syllable words starting with a third tone | pinyin as written | English
const THIRD_WORDS = rows(`
你好|nǐ hǎo|hello
可以|kě yǐ|may, can
水果|shuǐ guǒ|fruit
手表|shǒu biǎo|watch
雨伞|yǔ sǎn|umbrella
所以|suǒ yǐ|so, therefore
了解|liǎo jiě|to understand
理解|lǐ jiě|to comprehend
洗澡|xǐ zǎo|to take a bath
洗手|xǐ shǒu|to wash one's hands
打扫|dǎ sǎo|to clean up
表演|biǎo yǎn|to perform
语法|yǔ fǎ|grammar
也许|yě xǔ|perhaps
只好|zhǐ hǎo|to have no choice but to
只有|zhǐ yǒu|only
永远|yǒng yuǎn|forever
友好|yǒu hǎo|friendly
领导|lǐng dǎo|leader
管理|guǎn lǐ|to manage
处理|chǔ lǐ|to deal with
导演|dǎo yǎn|film director
广场|guǎng chǎng|public square
勇敢|yǒng gǎn|brave
美好|měi hǎo|beautiful, fine
展览|zhǎn lǎn|exhibition
减少|jiǎn shǎo|to reduce
好久|hǎo jiǔ|a long time
老虎|lǎo hǔ|tiger
老板|lǎo bǎn|boss
老鼠|lǎo shǔ|mouse
小姐|xiǎo jiě|miss, young lady
小狗|xiǎo gǒu|puppy
小鸟|xiǎo niǎo|little bird
小雨|xiǎo yǔ|light rain
小组|xiǎo zǔ|small group
口语|kǒu yǔ|spoken language
古老|gǔ lǎo|ancient
海水|hǎi shuǐ|sea water
冷水|lěng shuǐ|cold water
总统|zǒng tǒng|president
总理|zǒng lǐ|premier
旅馆|lǚ guǎn|hotel
允许|yǔn xǔ|to allow
粉笔|fěn bǐ|chalk
手指|shǒu zhǐ|finger
影响|yǐng xiǎng|influence
鼓掌|gǔ zhǎng|to applaud
往往|wǎng wǎng|often
指导|zhǐ dǎo|to guide
选举|xuǎn jǔ|election
水饺|shuǐ jiǎo|boiled dumplings
保险|bǎo xiǎn|insurance
感想|gǎn xiǎng|impressions
采访|cǎi fǎng|to interview
尽管|jǐn guǎn|even though
起点|qǐ diǎn|starting point
买米|mǎi mǐ|to buy rice
买酒|mǎi jiǔ|to buy alcohol
买笔|mǎi bǐ|to buy a pen
买伞|mǎi sǎn|to buy an umbrella
有水|yǒu shuǐ|there is water
有雨|yǒu yǔ|there is rain
请你|qǐng nǐ|to invite you
给你|gěi nǐ|for you
给我|gěi wǒ|for me
想买|xiǎng mǎi|to want to buy
想走|xiǎng zǒu|to want to leave
想写|xiǎng xiě|to want to write
想洗|xiǎng xǐ|to want to wash
几点|jǐ diǎn|what time
老师|lǎo shī|teacher
老人|lǎo rén|old person
北京|běi jīng|Beijing
手机|shǒu jī|mobile phone
语言|yǔ yán|language
美国|měi guó|the USA
可能|kě néng|possible
小学|xiǎo xué|primary school
小时|xiǎo shí|hour
小心|xiǎo xīn|careful
小猫|xiǎo māo|kitten
小孩|xiǎo hái|child
以前|yǐ qián|before
以后|yǐ hòu|after
好听|hǎo tīng|nice to listen to
请问|qǐng wèn|excuse me, may I ask
请坐|qǐng zuò|please sit down
请进|qǐng jìn|please come in
请客|qǐng kè|to treat someone
请假|qǐng jià|to ask for leave
米饭|mǐ fàn|cooked rice
午饭|wǔ fàn|lunch
早饭|zǎo fàn|breakfast
晚饭|wǎn fàn|dinner
考试|kǎo shì|exam
比赛|bǐ sài|match
旅行|lǚ xíng|to travel
可爱|kě ài|cute
可是|kě shì|but
好玩|hǎo wán|fun
解决|jiě jué|to solve
准备|zhǔn bèi|to prepare
火车|huǒ chē|train
每天|měi tiān|every day
每年|měi nián|every year
女人|nǚ rén|woman
有名|yǒu míng|famous
有钱|yǒu qián|rich
有人|yǒu rén|there is someone
有事|yǒu shì|to be busy with something
有空|yǒu kòng|to have free time
有用|yǒu yòng|useful
起床|qǐ chuáng|to get up
礼物|lǐ wù|present
马上|mǎ shàng|right away
买书|mǎi shū|to buy books
买菜|mǎi cài|to buy groceries
买票|mǎi piào|to buy tickets
买药|mǎi yào|to buy medicine
买花|mǎi huā|to buy flowers
想喝|xiǎng hē|to want to drink
想吃|xiǎng chī|to want to eat
想去|xiǎng qù|to want to go
想来|xiǎng lái|to want to come
想看|xiǎng kàn|to want to watch
想学|xiǎng xué|to want to learn
给他|gěi tā|for him
`);

const HEADS = [
  { zh: '很', py: 'hěn', kinds: ['ap', 'at', 'aw', 'ad'], en: (x) => `very ${x}` },
  { zh: '我', py: 'wǒ', kinds: ['v'], en: (x) => `I ${x}` },
  { zh: '你', py: 'nǐ', kinds: ['v'], en: (x) => `you ${x}` },
];
const COUNTERS = [
  ['五', 'wǔ', 'five'],
  ['九', 'jiǔ', 'nine'],
  ['两', 'liǎng', 'two'],
  ['几', 'jǐ', 'how many'],
];

function makeThird(rng) {
  const kind = weighted(rng, [
    [40, 'word'],
    [35, 'head'],
    [25, 'count'],
  ]);
  let zh;
  let a;
  let rest;
  let en;
  if (kind === 'word') {
    const [word, py, gloss] = pick(rng, THIRD_WORDS);
    zh = word;
    [a, ...rest] = py.split(' ');
    en = gloss;
  } else if (kind === 'head') {
    const head = pick(rng, HEADS);
    const word = pick(
      rng,
      WORDS.filter((x) => head.kinds.includes(x.kind))
    );
    zh = head.zh + word.zh;
    a = head.py;
    rest = word.py.split(' ');
    en = head.en(word.en);
  } else {
    const [c, cpy, cen] = pick(rng, COUNTERS);
    const m = pick(rng, Object.values(MEASURES));
    zh = c + m.zh;
    a = cpy;
    rest = [m.py];
    en = `${cen} (counting ${m.use})`;
  }
  const [b, ...more] = rest;
  const tb = toneOf(b);
  const tail = more.length ? ` ${more.join(' ')}` : '';
  const written = `${a} ${b}${tail}`;
  const firstUp = `${setTone(a, 2)} ${b}${tail}`;
  const secondMoved = `${a} ${setTone(b, tb === 2 ? 3 : 2)}${tail}`;
  const changes = tb === 3;
  const right = changes ? firstUp : written;
  const opts = shuffle(rng, [written, firstUp, secondMoved]);
  return {
    id: 'gen:third-tones',
    type: 'cloze',
    q: `${zh} → ___`,
    opts,
    a: opts.indexOf(right),
    zh: `${zh} → ${right}`,
    py: right,
    en,
    why: changes
      ? `${a} and ${b} are both third tones. The first of two third tones is said as a second tone, so ${written} sounds like ${firstUp}; the second one does not change.`
      : `${b} is a ${TONE_NAME[tb]} tone, so nothing changes: a third tone only becomes a second tone before another third tone. ${a} is just said low.`,
    cue: 'How is this really pronounced?',
  };
}

export const generators = [
  { key: 'bu-tone', label: '不: bù or bú', make: makeBu },
  { key: 'yi-tone', label: '一: yī, yí or yì', make: makeYi },
  { key: 'third-tones', label: 'Two third tones', make: makeThird },
];
