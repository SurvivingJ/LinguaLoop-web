/**
 * comparison generators: A 比 B + adjective (+ how much), the 没有
 * negative, 跟…一样, and 更 / 还, as order tiles and as cloze items.
 * Pairs and adjectives are grouped so that every combination is sensible;
 * pairs whose order matters for meaning (今天 / 昨天) are not reversed.
 */
import { pick, weighted, rows, order, cloze, cap } from './util.js';

const part = (zh, py) => ({ zh, py });

// group | A | py | English with verb | B | py | English
const PAIRS = rows(`
p|我|wǒ|I am|他|tā|him
p|他|tā|he is|我|wǒ|me
p|她|tā|she is|我|wǒ|me
p|我|wǒ|I am|她|tā|her
p|小王|xiǎo wáng|Xiao Wang is|小李|xiǎo lǐ|Xiao Li
p|小李|xiǎo lǐ|Xiao Li is|小王|xiǎo wáng|Xiao Wang
p|我朋友|wǒ péng you|my friend is|我|wǒ|me
p|我|wǒ|I am|我同学|wǒ tóng xué|my classmate
p|爸爸|bà ba|Dad is|妈妈|mā ma|Mom
p|妈妈|mā ma|Mom is|爸爸|bà ba|Dad
c|这件衣服|zhè jiàn yī fu|this piece of clothing is|那件衣服|nà jiàn yī fu|that one
c|那件衣服|nà jiàn yī fu|that piece of clothing is|这件衣服|zhè jiàn yī fu|this one
c|这双鞋|zhè shuāng xié|these shoes are|那双鞋|nà shuāng xié|those ones
g|这个手机|zhè ge shǒu jī|this phone is|那个手机|nà ge shǒu jī|that one
g|那个手机|nà ge shǒu jī|that phone is|这个手机|zhè ge shǒu jī|this one
g|这台电脑|zhè tái diàn nǎo|this computer is|那台电脑|nà tái diàn nǎo|that one
w|今天|jīn tiān|today is|昨天|zuó tiān|yesterday
w|今年|jīn nián|this year is|去年|qù nián|last year
w|这个星期|zhè ge xīng qī|this week is|上个星期|shàng ge xīng qī|last week
r|这个房间|zhè ge fáng jiān|this room is|那个房间|nà ge fáng jiān|that one
r|那个房间|nà ge fáng jiān|that room is|这个房间|zhè ge fáng jiān|this one
r|我的房间|wǒ de fáng jiān|my room is|他的房间|tā de fáng jiān|his
b|这本书|zhè běn shū|this book is|那本书|nà běn shū|that one
b|那本书|nà běn shū|that book is|这本书|zhè běn shū|this one
t|坐地铁|zuò dì tiě|taking the subway is|坐公共汽车|zuò gōng gòng qì chē|taking the bus
t|坐地铁|zuò dì tiě|taking the subway is|开车|kāi chē|driving
f|这家饭馆|zhè jiā fàn guǎn|this restaurant is|那家饭馆|nà jiā fàn guǎn|that one
f|那家饭馆|nà jiā fàn guǎn|that restaurant is|这家饭馆|zhè jiā fàn guǎn|this one
l|这条路|zhè tiáo lù|this road is|那条路|nà tiáo lù|that one
l|那条路|nà tiáo lù|that road is|这条路|zhè tiáo lù|this one
x|这个箱子|zhè ge xiāng zi|this suitcase is|那个箱子|nà ge xiāng zi|that one
x|那个箱子|nà ge xiāng zi|that suitcase is|这个箱子|zhè ge xiāng zi|this one
v|飞机|fēi jī|planes are|火车|huǒ chē|trains
v|火车|huǒ chē|trains are|公共汽车|gōng gòng qì chē|buses
q|这个问题|zhè ge wèn tí|this question is|那个问题|nà ge wèn tí|that one
q|那个问题|nà ge wèn tí|that question is|这个问题|zhè ge wèn tí|this one
h|他的汉语|tā de hàn yǔ|his Chinese is|我的汉语|wǒ de hàn yǔ|mine
h|她的汉语|tā de hàn yǔ|her Chinese is|我的汉语|wǒ de hàn yǔ|mine
d|这个菜|zhè ge cài|this dish is|那个菜|nà ge cài|that one
d|那个菜|nà ge cài|that dish is|这个菜|zhè ge cài|this one
`);

// groups | adjective | py | comparative | plain | amount kinds
const ADJS = rows(`
p|高|gāo|taller|tall|a cm
p|大|dà|older|old|age
p|小|xiǎo|younger|young|age
p|忙|máng|busier|busy|a
p|瘦|shòu|thinner|thin|a
cgb|贵|guì|more expensive|expensive|a yuan
fd|贵|guì|more expensive|expensive|a
cgb|便宜|pián yi|cheaper|cheap|a yuan
fdt|便宜|pián yi|cheaper|cheap|a
cg|好看|hǎo kàn|nicer-looking|nice-looking|a
c|舒服|shū fu|more comfortable|comfortable|a
cr|大|dà|bigger|big|a
crx|小|xiǎo|smaller|small|a
g|好用|hǎo yòng|handier|handy|a
g|轻|qīng|lighter|light|a
x|轻|qīng|lighter|light|a kg
g|新|xīn|newer|new|a
w|冷|lěng|colder|cold|a deg
w|热|rè|hotter|hot|a deg
r|干净|gān jìng|cleaner|clean|a
rf|安静|ān jìng|quieter|quiet|a
r|亮|liàng|brighter|bright|a
bq|难|nán|harder|hard|a
b|容易|róng yì|easier|easy|a
b|有意思|yǒu yì si|more interesting|interesting|a
b|厚|hòu|thicker|thick|a
tv|快|kuài|faster|fast|a
t|方便|fāng biàn|more convenient|convenient|a
f|远|yuǎn|farther away|far away|a
f|近|jìn|nearer|near|a
l|长|cháng|longer|long|a
l|短|duǎn|shorter|short|a
l|宽|kuān|wider|wide|a
x|重|zhòng|heavier|heavy|a kg
x|大|dà|bigger|big|a
q|简单|jiǎn dān|simpler|simple|a
q|重要|zhòng yào|more important|important|a
h|好|hǎo|better|good|a
h|流利|liú lì|more fluent|fluent|a
d|辣|là|spicier|spicy|a
d|甜|tián|sweeter|sweet|a
d|咸|xián|saltier|salty|a
d|好吃|hǎo chī|tastier|tasty|a
`);

// kind | amount | py | English ({c} = comparative)
const AMOUNTS = rows(`
a|一点儿|yī diǎn r|a little {c}
a|得多|de duō|much {c}
a|多了|duō le|much {c}
cm|三厘米|sān lí mǐ|3 cm {c}
cm|五厘米|wǔ lí mǐ|5 cm {c}
cm|十厘米|shí lí mǐ|10 cm {c}
age|一岁|yī suì|one year {c}
age|两岁|liǎng suì|two years {c}
age|三岁|sān suì|three years {c}
age|五岁|wǔ suì|five years {c}
yuan|十块|shí kuài|10 yuan {c}
yuan|二十块|èr shí kuài|20 yuan {c}
yuan|五十块|wǔ shí kuài|50 yuan {c}
yuan|一百块|yī bǎi kuài|100 yuan {c}
deg|三度|sān dù|three degrees {c}
deg|五度|wǔ dù|five degrees {c}
kg|两公斤|liǎng gōng jīn|2 kg {c}
kg|五公斤|wǔ gōng jīn|5 kg {c}
`);

/**
 * A compatible (pair, adjective) combination. `equal` is for 没有 / 一样
 * sentences: it skips the vehicle pairs (planes are not "as fast as" trains)
 * and 小 for age (一样小 is not said of adults).
 */
function combo(rng, equal = false) {
  const [g, a, apy, aen, b, bpy, ben] = pick(
    rng,
    PAIRS.filter((x) => !equal || x[0] !== 'v')
  );
  const [, adj, adjpy, comp, plain, kinds] = pick(
    rng,
    ADJS.filter((x) => x[0].includes(g) && !(equal && g === 'p' && x[1] === '小'))
  );
  return {
    A: part(a, apy),
    aen,
    B: part(b, bpy),
    ben,
    adj: part(adj, adjpy),
    comp,
    plain,
    kinds: kinds.split(' '),
  };
}

const amountFor = (rng, c) =>
  pick(
    rng,
    AMOUNTS.filter((x) => c.kinds.includes(x[0]))
  );

const BI = '比|bǐ';
const KEY_O = 'comparison-order';
const KEY_C = 'comparison-cloze';

function makeOrder(rng) {
  const kind = weighted(rng, [
    [3, 'bi'],
    [5, 'amount'],
    [3, 'meiyou'],
    [2, 'name'],
    [3, 'yiyang'],
    [2, 'geng'],
  ]);
  const c = combo(rng, ['meiyou', 'name', 'yiyang'].includes(kind));
  const { A, B, adj } = c;
  if (kind === 'bi') {
    return order(rng, {
      key: KEY_O,
      tiles: [A, BI, B, adj],
      en: `${cap(c.aen)} ${c.comp} than ${c.ben}.`,
      why: `A + 比 + B + adjective: the thing compared (${A.zh}) comes first, the standard (${B.zh}) follows 比, and the bare adjective comes last. No 很 before it.`,
    });
  }
  if (kind === 'amount') {
    const [, m, mpy, men] = amountFor(rng, c);
    return order(rng, {
      key: KEY_O,
      tiles: [A, BI, B, adj, part(m, mpy)],
      en: `${cap(c.aen)} ${men.replace('{c}', c.comp)} than ${c.ben}.`,
      why: `How much more goes after the adjective, never before it: A + 比 + B + ${adj.zh} + ${m}. 很 or an amount in front of ${adj.zh} is not possible with 比.`,
    });
  }
  if (kind === 'meiyou' || kind === 'name') {
    const na = kind === 'name';
    return order(rng, {
      key: KEY_O,
      tiles: [A, '没有|méi yǒu', B, na && '那么|nà me', adj].filter(Boolean),
      en: `${cap(c.aen)} not as ${c.plain} as ${c.ben}.`,
      why: `"Not as … as" is A + 没有 + B + ${na ? '那么 + ' : ''}adjective. 没有 takes the place of 比; it is not added to it.`,
    });
  }
  if (kind === 'yiyang') {
    return order(rng, {
      key: KEY_O,
      tiles: [A, '跟|gēn', B, '一样|yī yàng', adj],
      alts: [[2, 1, 0, 3, 4]],
      en: `${cap(c.aen)} as ${c.plain} as ${c.ben}.`,
      why: `"As … as" is A + 跟 + B + 一样 + adjective. 一样 comes after both things compared and directly before ${adj.zh}.`,
    });
  }
  const [g, gpy] = pick(rng, [
    ['更', 'gèng'],
    ['还', 'hái'],
  ]);
  return order(rng, {
    key: KEY_O,
    tiles: [A, BI, B, part(g, gpy), adj],
    en: `${cap(c.aen)} even ${c.comp} than ${c.ben}.`,
    why: `In a 比 sentence the only degree words allowed before the adjective are 更 and 还 ("even more"): A + 比 + B + ${g} + ${adj.zh}.`,
  });
}

function makeCloze(rng) {
  const kind = pick(rng, ['geng', 'bi', 'deduo', 'meiyou', 'yiyang']);
  const c = combo(rng, kind === 'meiyou' || kind === 'yiyang');
  const { A, B, adj } = c;
  const end = ['。'];
  if (kind === 'geng') {
    return cloze(rng, {
      key: KEY_C,
      pre: [A, BI, B],
      post: [adj, ...end],
      right: '更|gèng',
      wrong: ['很', '非常', '太'],
      en: `${cap(c.aen)} even ${c.comp} than ${c.ben}.`,
      why: `很, 非常 and 太 cannot stand before the adjective in a 比 sentence. Only 更 (or 还) can: ${B.zh} is already ${c.plain}, and ${A.zh} is even more so.`,
    });
  }
  if (kind === 'bi') {
    const [, m, mpy, men] = amountFor(rng, c);
    return cloze(rng, {
      key: KEY_C,
      pre: [A],
      post: [B, adj, part(m, mpy), ...end],
      right: BI,
      wrong: ['跟', '没有', '和'],
      en: `${cap(c.aen)} ${men.replace('{c}', c.comp)} than ${c.ben}.`,
      why: `A difference with an amount (${adj.zh}${m}) needs 比. 跟 / 和 go with 一样, and 没有 cannot be followed by an amount.`,
    });
  }
  if (kind === 'deduo') {
    return cloze(rng, {
      key: KEY_C,
      pre: [A, BI, B, adj],
      post: end,
      right: '得多|de duō',
      wrong: ['很', '非常', '太'],
      en: `${cap(c.aen)} much ${c.comp} than ${c.ben}.`,
      why: `"Much more" in a 比 sentence is said after the adjective: ${adj.zh}得多 (or ${adj.zh}多了). 很, 非常 and 太 cannot be used with 比 at all.`,
    });
  }
  if (kind === 'meiyou') {
    return cloze(rng, {
      key: KEY_C,
      pre: [A],
      post: [B, adj, ...end],
      right: '没有|méi yǒu',
      wrong: ['不', '别', '不是'],
      en: `${cap(c.aen)} not as ${c.plain} as ${c.ben}.`,
      why: `"Not as ${c.plain} as" is A + 没有 + B + adjective. 不 alone cannot link the two things compared, and 别 is for commands.`,
    });
  }
  return cloze(rng, {
    key: KEY_C,
    pre: [A, '跟|gēn', B],
    post: [adj, ...end],
    right: '一样|yī yàng',
    wrong: ['一起', '一点儿', '一下'],
    en: `${cap(c.aen)} as ${c.plain} as ${c.ben}.`,
    why: `Equal degree is A + 跟 + B + 一样 + adjective. 一起 means "together", and 一点儿 or 一下 cannot come before ${adj.zh} here.`,
  });
}

export const generators = [
  { key: KEY_O, label: 'Comparison word order', make: makeOrder },
  { key: KEY_C, label: '比 / 没有 / 一样', make: makeCloze },
];
