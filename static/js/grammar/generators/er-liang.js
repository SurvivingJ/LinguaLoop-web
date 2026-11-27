/**
 * er-liang generator: 二 or 两, decided by what follows. Every frame is a
 * curated sentence with a subject slot; 2 before 百 / 千 / 万 is left out
 * because both forms are accepted there.
 */
import { pick, weighted, rows, cloze, PEOPLE, fillEn, numWord } from './util.js';
import { readNumber } from './numbers-time.js';

const ER = '二|èr';
const LIANG = '两|liǎng';

// verb | py | measure | py | noun | py | English with {n} | "m" when a dozen or more is plausible
const COUNTED = rows(`
买了|mǎi le|本|běn|书|shū|{S} bought {n} books.|m
买了|mǎi le|张|zhāng|票|piào|{S} bought {n} tickets.|m
买了|mǎi le|件|jiàn|衬衫|chèn shān|{S} bought {n} shirts.|
买了|mǎi le|双|shuāng|鞋|xié|{S} bought {n} pairs of shoes.|
买了|mǎi le|个|gè|面包|miàn bāo|{S} bought {n} bread rolls.|m
买了|mǎi le|瓶|píng|啤酒|pí jiǔ|{S} bought {n} bottles of beer.|m
买了|mǎi le|支|zhī|笔|bǐ|{S} bought {n} pens.|m
喝了|hē le|杯|bēi|咖啡|kā fēi|{S} drank {n} cups of coffee.|
喝了|hē le|瓶|píng|水|shuǐ|{S} drank {n} bottles of water.|
吃了|chī le|碗|wǎn|米饭|mǐ fàn|{S} ate {n} bowls of rice.|
吃了|chī le|个|gè|苹果|píng guǒ|{S} ate {n} apples.|
吃了|chī le|个|gè|饺子|jiǎo zi|{S} ate {n} dumplings.|m
写了|xiě le|封|fēng|信|xìn|{S} wrote {n} letters.|m
写了|xiě le|篇|piān|文章|wén zhāng|{S} wrote {n} articles.|m
看了|kàn le|部|bù|电影|diàn yǐng|{S} watched {n} films.|m
看了|kàn le|本|běn|小说|xiǎo shuō|{S} read {n} novels.|m
借了|jiè le|本|běn|词典|cí diǎn|{S} borrowed {n} dictionaries.|
带了|dài le|个|gè|包|bāo|{S} brought {n} bags.|
带了|dài le|件|jiàn|行李|xíng li|{S} brought {n} pieces of luggage.|
点了|diǎn le|个|gè|菜|cài|{S} ordered {n} dishes.|m
点了|diǎn le|杯|bēi|茶|chá|{S} ordered {n} cups of tea.|
照了|zhào le|张|zhāng|照片|zhào piàn|{S} took {n} photos.|m
学了|xué le|首|shǒu|中文歌|zhōng wén gē|{S} learned {n} Chinese songs.|m
养了|yǎng le|只|zhī|猫|māo|{S} {have} {n} cats.|
养了|yǎng le|条|tiáo|狗|gǒu|{S} {have} {n} dogs.|
问了|wèn le|个|gè|问题|wèn tí|{S} asked {n} questions.|m
请了|qǐng le|位|wèi|客人|kè rén|{S} invited {n} guests.|m
认识了|rèn shi le|个|gè|新朋友|xīn péng you|{S} made {n} new friends.|m
去了|qù le|个|gè|城市|chéng shì|{S} went to {n} cities.|m
有|yǒu|个|gè|孩子|hái zi|{S} {have} {n} children.|
有|yǒu|台|tái|电脑|diàn nǎo|{S} {have} {n} computers.|
有|yǒu|辆|liàng|自行车|zì xíng chē|{S} {have} {n} bicycles.|
会说|huì shuō|种|zhǒng|语言|yǔ yán|{S} can speak {n} languages.|
今天上了|jīn tiān shàng le|节|jié|课|kè|{S} had {n} classes today.||p
这个学期有|zhè ge xué qī yǒu|门|mén|课|kè|{S} {have} {n} courses this term.||p
`);

// number around the blank: before | after | value
const INSIDE = [
  ['十', '', 12],
  ['', '十', 20],
  ['二十', '', 22],
  ['', '十一', 21],
  ['', '十五', 25],
  ['', '十八', 28],
  ['三十', '', 32],
  ['四十', '', 42],
  ['五十', '', 52],
  ['', '十四', 24],
  ['', '十六', 26],
];

// before | py | after | py | English: 两 with durations, clock hours, times and money
const QUANTITY = rows(`
在北京住了|zài běi jīng zhù le|年|nián|{S} lived in Beijing for two years.
在这儿工作了|zài zhè r gōng zuò le|年|nián|{S} worked here for two years.
等了|děng le|个小时|gè xiǎo shí|{S} waited for two hours.
睡了|shuì le|个小时|gè xiǎo shí|{S} slept for two hours.
学了|xué le|个月汉语|gè yuè hàn yǔ|{S} studied Chinese for two months.
休息了|xiū xi le|天|tiān|{S} rested for two days.
请了|qǐng le|天假|tiān jià|{S} took two days off.
病了|bìng le|个星期|gè xīng qī|{S} {was} ill for two weeks.
去过|qù guo|次上海|cì shàng hǎi|{S} {have} been to Shanghai twice.
去了|qù le|趟医院|tàng yī yuàn|{S} went to the hospital twice.
迟到了|chí dào le|次|cì|{S} {was} late twice.
把课文读了|bǎ kè wén dú le|遍|biàn|{S} read the text aloud twice.|p
花了|huā le|块钱|kuài qián|{S} spent two yuan.
昨天|zuó tiān|点才睡觉|diǎn cái shuì jiào|{S} didn't go to bed until two o'clock yesterday.
明天下午|míng tiān xià wǔ|点到|diǎn dào|{S} will arrive at two tomorrow afternoon.
明天下午|míng tiān xià wǔ|点半下课|diǎn bàn xià kè|{S} will finish class at half past two tomorrow afternoon.|p
过|guò|天就回来|tiān jiù huí lái|{S} will be back in a couple of days.
看了|kàn le|个半小时的电视|gè bàn xiǎo shí de diàn shì|{S} watched TV for two and a half hours.
来中国|lái zhōng guó|年了|nián le|{S} {have} been in China for two years.
`);

// before | py | after | py | English: 二 as ordinal, digit, floor, grade, line
const ORDINAL = rows(`
住在|zhù zài|楼|lóu|{S} [live] on the second floor.
住在十|zhù zài shí|楼|lóu|{S} [live] on the twelfth floor.
住在|zhù zài|十楼|shí lóu|{S} [live] on the twentieth floor.
上|shàng|年级|nián jí|{S} {is} in the second year.|p
是第|shì dì|个到的|gè dào de|{S} {was} the second to arrive.
考了第|kǎo le dì|名|míng|{S} came second in the exam.|p
第|dì|天就回来了|tiān jiù huí lái le|{S} came back the very next day.
每天坐|měi tiān zuò|号线上班|hào xiàn shàng bān|{S} [take] Line 2 to work every day.
是第|shì dì|次来中国|cì lái zhōng guó|{S} {is} in China for the second time.
今年|jīn nián|十岁|shí suì|{S} {is} twenty this year.|p
今年|jīn nián|十五岁|shí wǔ suì|{S} {is} twenty-five this year.|p
今年|jīn nián|十八岁|shí bā suì|{S} {is} twenty-eight this year.|p
今年三十|jīn nián sān shí|岁|suì|{S} {is} thirty-two this year.|p
今年四十|jīn nián sì shí|岁|suì|{S} {is} forty-two this year.|p
这次考了九十|zhè cì kǎo le jiǔ shí|分|fēn|{S} scored 92 this time.|p
这次考了八十|zhè cì kǎo le bā shí|分|fēn|{S} scored 82 this time.|p
这次考了七十|zhè cì kǎo le qī shí|分|fēn|{S} scored 72 this time.|p
的生日是|de shēng rì shì|月五号|yuè wǔ hào|{S2} birthday is February 5.|g
的生日是|de shēng rì shì|月十号|yuè shí hào|{S2} birthday is February 10.|g
的生日是三月|de shēng rì shì sān yuè|号|hào|{S2} birthday is March 2.|g
的生日是十|de shēng rì shì shí|月八号|yuè bā hào|{S2} birthday is December 8.|g
的生日是六月十|de shēng rì shì liù yuè shí|号|hào|{S2} birthday is June 12.|g
的生日是九月|de shēng rì shì jiǔ yuè|十号|shí hào|{S2} birthday is September 20.|g
`);

// whole sentences with no subject slot: before | py | after | py | answer | English | why
const FIXED = rows(`
今天星期|jīn tiān xīng qī|||二|Today is Tuesday.|Days of the week are numbered, so Tuesday is 星期二. 两 only counts things before a measure word.
一加一等于|yī jiā yī děng yú|||二|One plus one is two.|In counting and arithmetic the number 2 is 二. 两 needs a measure word after it.
我们学到第|wǒ men xué dào dì|课了|kè le|二|We have got to lesson 2.|After 第 the ordinal is always 二: 第二课. 两课 would mean two lessons.
我们学了|wǒ men xué le|课|kè|两|We studied two lessons.|Counting lessons: 两 before the measure 课. 第二课 would be the second lesson.
这|zhè|本书都很有意思|běn shū dōu hěn yǒu yì si|两|Both of these books are interesting.|Two of something before a measure word (本) is 两, also after 这 or 那.
那|nà|个人我都不认识|gè rén wǒ dōu bù rèn shi|两|I don't know either of those two people.|Two people: 两 before the measure 个, also after 这 or 那.
这|zhè|天我很忙|tiān wǒ hěn máng|两|I've been busy these last couple of days.|天 is its own measure word, so two days is 两天; 这两天 means these couple of days.
他们|tā men|个人都是老师|gè rén dōu shì lǎo shī|两|Both of them are teachers.|Counting two people before 个 takes 两. 二个 is not said.
三分之|sān fēn zhī|的学生是女生|de xué sheng shì nǚ shēng|二|Two thirds of the students are girls.|Fractions are read as numbers, so 2 is 二: 三分之二.
百分之|bǎi fēn zhī|十的人不同意|shí de rén bù tóng yì|二|Twenty percent of people disagree.|二十 is a number in its own right; inside tens 2 is always 二.
现在是|xiàn zài shì|月|yuè|二|It's February now.|Months are numbered: February is 二月. 两个月 would be a length of two months.
我在这儿住了|wǒ zài zhè r zhù le|个月|gè yuè|两|I've lived here for two months.|A length of two months counts months with 个, so 两个月. 二月 is February.
请翻到第十|qǐng fān dào dì shí|页|yè|二|Please turn to page 12.|In 十二 the 2 is a digit of a larger number, so 二, and after 第 only 二 is possible.
我的房间在十|wǒ de fáng jiān zài shí|楼|lóu|二|My room is on the twelfth floor.|Floors are numbered like ordinals, and in 十二 the 2 is always 二.
现在|xiàn zài|点半|diǎn bàn|两|It's half past two now.|Clock hours count with 点, and a bare 2 before it is 两: 两点半. 二点 is not said.
现在十|xiàn zài shí|点|diǎn|二|It's twelve o'clock now.|两 is only for a bare 2. In 十二 the 2 is part of a larger number and stays 二: 十二点.
一共|yī gòng|块五|kuài wǔ|两|That's two yuan fifty altogether.|Before 块 a bare 2 is 两: 两块五.
一共十|yī gòng shí|块|kuài|二|That's twelve yuan altogether.|In 十二 the 2 is always 二, even right before 块.
`);

const WHY = {
  counted: (m) =>
    `Two of something before a measure word (${m}) is 两. 二 is for counting, digits, dates and ordinals, not for "two of".`,
  inside: (num, m) =>
    `In ${num} the 2 is one digit of a larger number, so it is 二 even right before the measure ${m}. 两 only stands for a bare 2.`,
  quantity:
    'A bare 2 that counts something (years, days, hours, times, 点, 块) is 两. 二 would read like a digit or an ordinal here.',
  ordinal:
    'Ordinals, dates, floors, line numbers and the digits inside a larger number (二十, 十二, 九十二) use 二. 两 only counts "two of" before a measure word.',
};

/** Subjects a row allows: p = pronouns and names only, g = one person only. */
function subjectsFor(tag) {
  if (tag === 'p') return PEOPLE.slice(0, 7);
  if (tag === 'g') return PEOPLE.filter((x) => x.be !== 'are');
  return PEOPLE;
}

const two = (rng, opts) => cloze(rng, { key: 'er-liang', max: 1, ...opts });

function makeErLiang(rng) {
  const kind = weighted(rng, [
    [22, 'counted'],
    [20, 'inside'],
    [22, 'quantity'],
    [26, 'ordinal'],
    [10, 'fixed'],
  ]);
  if (kind === 'fixed') {
    const [a, apy, b, bpy, ans, en, why] = pick(rng, FIXED);
    const post = b ? [{ zh: b, py: bpy }, '。'] : ['。'];
    const liang = ans === '两';
    return two(rng, {
      pre: [{ zh: a, py: apy }],
      post,
      right: liang ? LIANG : ER,
      wrong: [liang ? ER : LIANG],
      en,
      why,
    });
  }
  if (kind === 'counted' || kind === 'inside') {
    const pool = kind === 'inside' ? COUNTED.filter((r) => r[7] === 'm') : COUNTED;
    const [v, vpy, m, mpy, n, npy, en, , tag] = pick(rng, pool);
    const s = pick(rng, subjectsFor(tag));
    const tail = [{ zh: m + n, py: `${mpy} ${npy}` }, '。'];
    if (kind === 'counted') {
      return two(rng, {
        pre: [s, { zh: v, py: vpy }],
        post: tail,
        right: LIANG,
        wrong: [ER],
        en: fillEn(en, s).replace('{n}', 'two'),
        why: WHY.counted(m),
      });
    }
    const [before, after, value] = pick(rng, INSIDE);
    return two(rng, {
      pre: [s, { zh: v, py: vpy }, before && numWord(before)],
      post: [after && numWord(after), ...tail],
      right: ER,
      wrong: [LIANG],
      en: fillEn(en, s).replace('{n}', String(value)),
      why: WHY.inside(readNumber(value), m),
    });
  }
  const [a, apy, b, bpy, en, tag] = pick(rng, kind === 'quantity' ? QUANTITY : ORDINAL);
  const s = pick(rng, subjectsFor(tag));
  const liang = kind === 'quantity';
  const poss = s.en === 'I' ? 'My' : `${s.en}'s`;
  const fixedEn = { He: 'His', She: 'Her', We: 'Our', They: 'Their' }[s.en] || poss;
  return two(rng, {
    pre: [s, { zh: a, py: apy }],
    post: [{ zh: b, py: bpy }, '。'],
    right: liang ? LIANG : ER,
    wrong: [liang ? ER : LIANG],
    en: fillEn(en.replace('{S2}', fixedEn), s),
    why: liang ? WHY.quantity : WHY.ordinal,
  });
}

export const generators = [{ key: 'er-liang', label: '二 or 两', make: makeErLiang }];
