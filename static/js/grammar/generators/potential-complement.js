/**
 * potential-complement generator: choose the right "can't" (V不R) or "can"
 * (V得R) form of a verb + result pair, in a context that forces it.
 *
 * Distractors are malformed orders. Forms that are real Chinese with another
 * meaning are never offered: 不进去 ("won't go in") for directional pairs,
 * V得不R (洗得不干净 is a degree complement), 没来得及, and 能V得R.
 */
import { pick, shuffle, w, cloze, PEOPLE, fillEn } from './util.js';

/**
 * A verb + result pair. `neg` / `pos` are contexts 'clause|py|English with
 * {S}'; flags: d = directional (不VR means "won't", so it is not offered),
 * m = 没V得R is a real form.
 */
const pair = (v, r, o, flags, neg, pos = []) => ({
  v: w(v),
  r: w(r),
  o: o ? w(o) : null,
  flags,
  neg: neg.map(w),
  pos: pos.map(w),
});

const PAIRS = [
  pair(
    '看|kàn',
    '懂|dǒng',
    '',
    '',
    [
      "这本书太难了|zhè běn shū tài nán le|This book is too hard. {S} can't understand it.",
      "这封信是用日语写的|zhè fēng xìn shì yòng rì yǔ xiě de|This letter is written in Japanese. {S} can't understand it.",
      "这个句子太长了|zhè ge jù zi tài cháng le|This sentence is too long. {S} can't understand it.",
    ],
    [
      '这本书不难|zhè běn shū bù nán|This book is not hard. {S} can understand it.',
      '这个句子很简单|zhè ge jù zi hěn jiǎn dān|This sentence is simple. {S} can understand it.',
    ]
  ),
  pair(
    '听|tīng',
    '懂|dǒng',
    '',
    '',
    [
      "老师说得太快了|lǎo shī shuō de tài kuài le|The teacher speaks too fast. {S} can't follow.",
      "那个人说的是上海话|nà ge rén shuō de shì shàng hǎi huà|That person is speaking Shanghainese. {S} can't understand.",
      "新闻说得太快了|xīn wén shuō de tài kuài le|The news is read too fast. {S} can't follow it.",
    ],
    ['老师说得很慢|lǎo shī shuō de hěn màn|The teacher speaks slowly. {S} can follow.']
  ),
  pair(
    '听|tīng',
    '见|jiàn',
    '',
    '',
    [
      "外面太吵了|wài mian tài chǎo le|It is too noisy outside. {S} can't hear anything.",
      "声音太小了|shēng yīn tài xiǎo le|The sound is too quiet. {S} can't hear it.",
    ],
    ['声音很大|shēng yīn hěn dà|The sound is loud. {S} can hear it.']
  ),
  pair(
    '看|kàn',
    '见|jiàn',
    '',
    '',
    [
      "天太黑了|tiān tài hēi le|It is too dark. {S} can't see anything.",
      "雾太大了|wù tài dà le|The fog is too thick. {S} can't see anything.",
      "前面的人太高了|qián mian de rén tài gāo le|The person in front is too tall. {S} can't see.",
    ],
    ['灯开着|dēng kāi zhe|The light is on. {S} can see.']
  ),
  pair(
    '看|kàn',
    '清楚|qīng chu',
    '',
    '',
    [
      "字太小了|zì tài xiǎo le|The writing is too small. {S} can't make it out.",
      "黑板太远了|hēi bǎn tài yuǎn le|The blackboard is too far away. {S} can't see it clearly.",
    ],
    ['字很大|zì hěn dà|The writing is big. {S} can see it clearly.']
  ),
  pair(
    '听|tīng',
    '清楚|qīng chu',
    '',
    '',
    [
      "电话里声音太小了|diàn huà lǐ shēng yīn tài xiǎo le|The voice on the phone is too quiet. {S} can't hear it clearly.",
      "教室里太吵了|jiào shì lǐ tài chǎo le|The classroom is too noisy. {S} can't hear clearly.",
    ],
    ['教室里很安静|jiào shì lǐ hěn ān jìng|The classroom is quiet. {S} can hear clearly.']
  ),
  pair(
    '吃|chī',
    '完|wán',
    '',
    '',
    [
      "菜太多了|cài tài duō le|There is too much food. {S} can't finish it.",
      "这碗面太大了|zhè wǎn miàn tài dà le|This bowl of noodles is too big. {S} can't finish it.",
    ],
    ['菜不多|cài bù duō|There is not much food. {S} can finish it.']
  ),
  pair(
    '做|zuò',
    '完|wán',
    '',
    '',
    [
      "作业太多了|zuò yè tài duō le|There is too much homework. {S} can't finish it.",
      "工作太多了|gōng zuò tài duō le|There is too much work. {S} can't finish it.",
    ],
    ['作业不多|zuò yè bù duō|There is not much homework. {S} can finish it.']
  ),
  pair(
    '看|kàn',
    '完|wán',
    '',
    '',
    ["这本书太厚了|zhè běn shū tài hòu le|This book is too thick. {S} can't finish reading it."],
    ['这本书很薄|zhè běn shū hěn báo|This book is thin. {S} can finish reading it.']
  ),
  pair(
    '喝|hē',
    '完|wán',
    '',
    '',
    ["咖啡太多了|kā fēi tài duō le|There is too much coffee. {S} can't finish it."],
    ['茶不多|chá bù duō|There is not much tea. {S} can finish it.']
  ),
  pair(
    '写|xiě',
    '完|wán',
    '',
    '',
    ["报告太长了|bào gào tài cháng le|The report is too long. {S} can't finish writing it."],
    ['报告不长|bào gào bù cháng|The report is not long. {S} can finish writing it.']
  ),
  pair(
    '买|mǎi',
    '到|dào',
    '票|piào',
    '',
    ["票卖完了|piào mài wán le|The tickets are sold out. {S} can't get a ticket."],
    ['票还有很多|piào hái yǒu hěn duō|There are still plenty of tickets. {S} can get one.']
  ),
  pair('找|zhǎo', '到|dào', '钥匙|yào shi', '', [
    "房间太乱了|fáng jiān tài luàn le|The room is too messy. {S} can't find the keys.",
  ]),
  pair('找|zhǎo', '到|dào', '工作|gōng zuò', '', [
    "现在工作很难找|xiàn zài gōng zuò hěn nán zhǎo|Jobs are hard to find now. {S} can't find one.",
  ]),
  pair(
    '记|jì',
    '住|zhù',
    '',
    '',
    [
      "生词太多了|shēng cí tài duō le|There are too many new words. {S} can't remember them.",
      "这个电话号码太长了|zhè ge diàn huà hào mǎ tài cháng le|This phone number is too long. {S} can't remember it.",
    ],
    ['生词不多|shēng cí bù duō|There are not many new words. {S} can remember them.']
  ),
  pair(
    '进|jìn',
    '去|qù',
    '',
    'd',
    [
      "门锁着|mén suǒ zhe|The door is locked. {S} can't get in.",
      "人太多了|rén tài duō le|It is too crowded. {S} can't get in.",
    ],
    ['门开着|mén kāi zhe|The door is open. {S} can get in.']
  ),
  pair('出|chū', '去|qù', '', 'd', [
    "雨太大了|yǔ tài dà le|The rain is too heavy. {S} can't get out.",
    "门锁着|mén suǒ zhe|The door is locked. {S} can't get out.",
  ]),
  pair('回|huí', '去|qù', '', 'd', [
    "没有车了|méi yǒu chē le|There are no more buses. {S} can't get back.",
  ]),
  pair('上|shàng', '去|qù', '', 'd', [
    "电梯坏了|diàn tī huài le|The lift is broken. {S} can't get up there.",
  ]),
  pair('爬|pá', '上去|shàng qù', '', 'd', [
    "山太高了|shān tài gāo le|The mountain is too high. {S} can't climb up.",
  ]),
  pair('想|xiǎng', '起来|qǐ lái', '', '', [
    "那个人叫什么名字|nà ge rén jiào shén me míng zi|{S} can't recall what that person is called.",
    "钥匙放在哪儿了|yào shi fàng zài nǎ r le|{S} can't recall where the keys were put.",
  ]),
  pair('睡|shuì', '着|zháo', '', '', [
    "咖啡喝得太多了|kā fēi hē de tài duō le|Too much coffee. {S} can't get to sleep.",
    "外面太吵了|wài mian tài chǎo le|It is too noisy outside. {S} can't get to sleep.",
    "房间太热了|fáng jiān tài rè le|The room is too hot. {S} can't get to sleep.",
  ]),
  pair(
    '买|mǎi',
    '起|qǐ',
    '',
    '',
    [
      "这个手机太贵了|zhè ge shǒu jī tài guì le|This phone is too expensive. {S} can't afford it.",
      "北京的房子太贵了|běi jīng de fáng zi tài guì le|Housing in Beijing is too expensive. {S} can't afford it.",
    ],
    ['这个手机不贵|zhè ge shǒu jī bù guì|This phone is not expensive. {S} can afford it.']
  ),
  pair(
    '来|lái',
    '及|jí',
    '',
    'm',
    [
      "时间太紧了|shí jiān tài jǐn le|Time is too tight. {S} can't make it in time.",
      "火车十分钟以后开|huǒ chē shí fēn zhōng yǐ hòu kāi|The train leaves in ten minutes. {S} can't make it in time.",
    ],
    ['时间还早|shí jiān hái zǎo|It is still early. {S} can make it in time.']
  ),
  pair(
    '拿|ná',
    '动|dòng',
    '',
    '',
    ["这个箱子太重了|zhè ge xiāng zi tài zhòng le|This suitcase is too heavy. {S} can't carry it."],
    ['这个箱子不重|zhè ge xiāng zi bù zhòng|This suitcase is not heavy. {S} can carry it.']
  ),
  pair('搬|bān', '动|dòng', '', '', [
    "这张桌子太重了|zhè zhāng zhuō zi tài zhòng le|This table is too heavy. {S} can't move it.",
  ]),
  pair(
    '打|dǎ',
    '开|kāi',
    '',
    '',
    [
      "这个瓶子太紧了|zhè ge píng zi tài jǐn le|This bottle is too tight. {S} can't open it.",
      "窗户坏了|chuāng hu huài le|The window is broken. {S} can't open it.",
    ],
    ['这个瓶子不紧|zhè ge píng zi bù jǐn|This bottle is not tight. {S} can open it.']
  ),
  pair('关|guān', '上|shàng', '', '', [
    "窗户坏了|chuāng hu huài le|The window is broken. {S} can't close it.",
    "箱子里东西太多了|xiāng zi lǐ dōng xi tài duō le|There is too much in the suitcase. {S} can't close it.",
  ]),
  pair('洗|xǐ', '干净|gān jìng', '', '', [
    "这件衣服太脏了|zhè jiàn yī fu tài zāng le|This piece of clothing is too dirty. {S} can't get it clean.",
  ]),
  pair(
    '修|xiū',
    '好|hǎo',
    '',
    '',
    ["这台电脑太旧了|zhè tái diàn nǎo tài jiù le|This computer is too old. {S} can't fix it."],
    ['问题不大|wèn tí bù dà|The problem is not serious. {S} can fix it.']
  ),
  pair('跟|gēn', '上|shàng', '', '', [
    "前面的人走得太快了|qián mian de rén zǒu de tài kuài le|The people ahead walk too fast. {S} can't keep up.",
  ]),
  pair('做|zuò', '出来|chū lái', '', '', [
    "这道题太难了|zhè dào tí tài nán le|This problem is too hard. {S} can't work it out.",
  ]),
  pair('看|kàn', '出来|chū lái', '', '', [
    "这两张照片太像了|zhè liǎng zhāng zhào piàn tài xiàng le|These two photos are too alike. {S} can't tell them apart.",
  ]),
  pair('学|xué', '会|huì', '', '', [
    "这个太难了|zhè ge tài nán le|This is too hard. {S} can't master it.",
  ]),
  pair('赶|gǎn', '上|shàng', '火车|huǒ chē', '', [
    "路上堵车了|lù shang dǔ chē le|There is a traffic jam. {S} can't catch the train.",
  ]),
  pair('说|shuō', '清楚|qīng chu', '', '', [
    "这件事太复杂了|zhè jiàn shì tài fù zá le|This matter is too complicated. {S} can't explain it clearly.",
  ]),
  pair(
    '穿|chuān',
    '上|shàng',
    '',
    '',
    ["这条裤子太小了|zhè tiáo kù zi tài xiǎo le|These trousers are too small. {S} can't get them on."],
    ['这条裤子不小|zhè tiáo kù zi bù xiǎo|These trousers are not small. {S} can get them on.']
  ),
  pair('考|kǎo', '上|shàng', '大学|dà xué', '', [
    "分数太低了|fēn shù tài dī le|The score is too low. {S} can't get into university.",
  ]),
];

const NEG = PAIRS.flatMap((p) => p.neg.map((ctx) => ({ p, ctx })));
const POS = PAIRS.flatMap((p) => p.pos.map((ctx) => ({ p, ctx })));

/** Wrong "can't" forms for a pair. */
function wrongNegative({ v, r, flags }) {
  const V = v.zh;
  const R = r.zh;
  const out = [`${V}${R}不`, `${V}没${R}`];
  if (!flags.includes('d')) out.push(`不${V}${R}`);
  if (!flags.includes('m')) out.push(`没${V}得${R}`);
  if (R.length === 2 && /^[起出上下进回过]/.test(R)) out.push(`${V}${R[0]}不${R[1]}`);
  return out;
}

function makePotential(rng) {
  const negative = rng() < 0.75;
  const { p, ctx } = pick(rng, negative ? NEG : POS);
  const s = pick(rng, PEOPLE);
  const { v, r, o } = p;
  const mid = negative ? '不|bù' : '得|de';
  const right = { zh: v.zh + mid[0] + r.zh, py: `${v.py} ${mid.split('|')[1]} ${r.py}` };
  const wrong = negative
    ? wrongNegative(p)
    : [`得${v.zh}${r.zh}`, `${v.zh}${r.zh}得`, `${v.zh}能${r.zh}`, `${v.zh}可以${r.zh}`];
  return cloze(rng, {
    key: 'potential-form',
    pre: [ctx, '，', s],
    post: [o, '。'],
    right,
    wrong: shuffle(rng, wrong),
    en: fillEn(ctx.en, s),
    why: negative
      ? `"Cannot manage to" is verb + 不 + result: ${right.zh}. 不 goes between ${v.zh} and ${r.zh}, never in front of the whole compound or after it, and 没 does not combine with 得.`
      : `"Can manage to" is verb + 得 + result: ${right.zh}. 得 goes between ${v.zh} and ${r.zh}; 能 and 可以 cannot be put inside the compound.`,
  });
}

export const generators = [
  { key: 'potential-form', label: 'V不R / V得R', make: makePotential },
];
