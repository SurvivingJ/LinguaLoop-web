/**
 * measure-words generator: number / 这 / 那 + ___ + noun inside a sentence.
 * Each noun lists every measure word a native speaker accepts (the first is
 * the standard answer) and the wrong ones that may be offered. A distractor
 * is never taken from the accepted list, so 个 is only offered where it is
 * not listed as acceptable -- and in this table it is never offered at all.
 */
import { pick, weighted, rows, cloze, PEOPLE, fillEn, numWord } from './util.js';

// measure | pinyin | what it counts
export const MEASURES = Object.fromEntries(
  rows(`
个|gè|people and most things without a measure of their own
本|běn|bound things such as books
张|zhāng|flat things: paper, tickets, tables, beds
条|tiáo|long, bendy things: trousers, rivers, fish, roads
只|zhī|small animals and one of a pair
件|jiàn|upper-body clothes, presents and luggage
辆|liàng|wheeled vehicles
位|wèi|people, politely
杯|bēi|a cup or glass of a drink
瓶|píng|a bottle of something
碗|wǎn|a bowl of food
块|kuài|chunks and pieces, and watches
双|shuāng|pairs of matching things
家|jiā|businesses such as shops and restaurants
间|jiān|rooms
把|bǎ|things held by a handle
支|zhī|stick-like things such as pens
台|tái|machines and appliances
部|bù|films, series and phones
棵|kē|trees and plants
朵|duǒ|flowers
封|fēng|letters
首|shǒu|songs and poems
节|jié|class periods
座|zuò|large fixed things: mountains, bridges, buildings
种|zhǒng|kinds of things
套|tào|sets
份|fèn|portions and copies
头|tóu|large farm animals
匹|pǐ|horses
片|piàn|thin slices and tablets
顿|dùn|meals
场|chǎng|shows, matches and exams
根|gēn|long, thin, stiff things
架|jià|planes and pianos
幅|fú|paintings
篇|piān|articles and essays
句|jù|sentences
副|fù|things worn as a set, like glasses
顶|dǐng|hats
所|suǒ|schools and hospitals
扇|shàn|doors and windows
盏|zhǎn|lamps
面|miàn|flat surfaces such as mirrors
`).map(([zh, py, use]) => [zh, { zh, py, use }])
);

// noun | pinyin | singular | plural | accepted measures (first = answer) | wrong measures | frame codes
export const NOUNS = rows(`
书|shū|book|books|本 套 册|张 条 件|b r j t p l
词典|cí diǎn|dictionary|dictionaries|本 部|张 件 块|b j t p
杂志|zá zhì|magazine|magazines|本 份|张 条 件|b r t
小说|xiǎo shuō|novel|novels|本 部 篇|张 件 条|b r l
课本|kè běn|textbook|textbooks|本 套 册|张 条 件|b t p x
笔记本|bǐ jì běn|notebook|notebooks|本 个|张 条 件|b t p
护照|hù zhào|passport|passports|本 个|条 件 支|t x
报纸|bào zhǐ|newspaper|newspapers|份 张|本 件 条|b r
地图|dì tú|map|maps|张 幅 份|本 条 件|b t p
票|piào|ticket|tickets|张|本 条 件|b t
照片|zhào piàn|photo|photos|张 幅|本 条 件|z t l
桌子|zhuō zi|table|tables|张|条 本 件|b t p
床|chuáng|bed|beds|张|条 件 本|b t p
沙发|shā fā|sofa|sofas|张 个 套 组|条 本 支|b t p
纸|zhǐ|sheet of paper|sheets of paper|张|本 件 条|b x
邮票|yóu piào|stamp|stamps|张 枚 套|本 条 件|b
银行卡|yín háng kǎ|bank card|bank cards|张|本 条 件|h t
名片|míng piàn|business card|business cards|张|本 条 件|x
画|huà|painting|paintings|幅 张|本 条 件|b t l p
椅子|yǐ zi|chair|chairs|把 张|条 本 支|b t p
雨伞|yǔ sǎn|umbrella|umbrellas|把|条 张 本|b t p x
刀|dāo|knife|knives|把|条 张 本|b t
钥匙|yào shi|key|keys|把 串|条 张 本|t x
牙刷|yá shuā|toothbrush|toothbrushes|把 支|条 张 件|b t
吉他|jí tā|guitar|guitars|把|条 张 辆|b t p
剪刀|jiǎn dāo|pair of scissors|pairs of scissors|把|双 条 张|b t x
扇子|shàn zi|fan|fans|把|条 张 件|b t
梳子|shū zi|comb|combs|把|条 张 件|b t
勺子|sháo zi|spoon|spoons|把 个 只|条 张 双|b t x
叉子|chā zi|fork|forks|把 个|条 张 双|b t
钢琴|gāng qín|piano|pianos|架 台|把 辆 张|b t p
笔|bǐ|pen|pens|支 枝 根|条 张 本|b t p
铅笔|qiān bǐ|pencil|pencils|支 枝 根|张 本 件|b t
烟|yān|cigarette|cigarettes|支 根 包 条|张 本 件|T
裤子|kù zi|pair of trousers|pairs of trousers|条|件 双 张|b t p l
裙子|qún zi|skirt|skirts|条 件|双 张 本|b t p l
毛巾|máo jīn|towel|towels|条 块|件 本 支|b t
领带|lǐng dài|tie|ties|条|件 张 双|b t p
围巾|wéi jīn|scarf|scarves|条|件 张 双|b t p l
项链|xiàng liàn|necklace|necklaces|条 串|张 双 本|b t p l
被子|bèi zi|quilt|quilts|条 床|张 件 本|b t
毯子|tǎn zi|blanket|blankets|条 张 块|件 本 支|b t
河|hé|river|rivers|条|张 座 件|s f
路|lù|road|roads|条|张 座 件|f
新闻|xīn wén|news story|news stories|条 则 个|本 张 件|r
消息|xiāo xi|message|messages|条 个|本 张 件|U
鱼|yú|fish|fish|条 尾 只|匹 头 张|b s y
狗|gǒu|dog|dogs|条 只|匹 张 位|y s l
蛇|shé|snake|snakes|条 只|匹 头 张|s
猫|māo|cat|cats|只|条 匹 头|y s l
鸟|niǎo|bird|birds|只|条 匹 头|s y l
鸡|jī|chicken|chickens|只|条 匹 头|y s
兔子|tù zi|rabbit|rabbits|只|条 匹 头|y s l
老虎|lǎo hǔ|tiger|tigers|只 头|条 匹 位|s
熊猫|xióng māo|panda|pandas|只|条 匹 位|s l
猴子|hóu zi|monkey|monkeys|只|条 匹 头|s
鸭子|yā zi|duck|ducks|只|条 匹 头|s y
羊|yáng|sheep|sheep|只 头|条 匹 位|s y
马|mǎ|horse|horses|匹|条 张 位|s y
牛|niú|cow|cows|头 只|匹 条 张|s y
猪|zhū|pig|pigs|头 只 口|匹 条 张|s y
大象|dà xiàng|elephant|elephants|头 只|匹 条 张|s
鞋|xié|pair of shoes|pairs of shoes|双|条 件 张|b t p l
袜子|wà zi|pair of socks|pairs of socks|双|条 件 张|b t
筷子|kuài zi|pair of chopsticks|pairs of chopsticks|双 副 把|条 张 件|b t x
手套|shǒu tào|pair of gloves|pairs of gloves|双 副|条 件 张|b t
眼镜|yǎn jìng|pair of glasses|pairs of glasses|副|双 条 张|b t p
衣服|yī fu|piece of clothing|pieces of clothing|件 套 身|条 张 双|b t p l
衬衫|chèn shān|shirt|shirts|件|条 张 双|b t p l
毛衣|máo yī|sweater|sweaters|件|条 张 双|b t p l
大衣|dà yī|coat|coats|件|条 张 双|b t p
外套|wài tào|jacket|jackets|件|条 张 双|b t p l
礼物|lǐ wù|present|presents|件 份 个|条 张 本|b t l
行李|xíng li|piece of luggage|pieces of luggage|件|条 张 本|x t
西装|xī zhuāng|suit|suits|套 件 身|条 双 张|b t p
帽子|mào zi|hat|hats|顶 个|条 双 张|b t p l
车|chē|car|cars|辆 部 台|条 张 匹|b t p h
自行车|zì xíng chē|bicycle|bicycles|辆 部 台|条 张 匹|b t p h
出租车|chū zū chē|taxi|taxis|辆 部 台|条 张 只|s
公共汽车|gōng gòng qì chē|bus|buses|辆 部 台|条 张 只|s
摩托车|mó tuō chē|motorbike|motorbikes|辆 部 台|条 张 匹|b t h
飞机|fēi jī|plane|planes|架|辆 条 张|s
船|chuán|boat|boats|条 只 艘|辆 张 匹|s
老师|lǎo shī|teacher|teachers|位 个 名|只 条 张|n
医生|yī shēng|doctor|doctors|位 个 名|只 条 本|n
客人|kè rén|guest|guests|位 个|只 条 张|n I
朋友|péng you|friend|friends|个 位|只 条 本|I
学生|xué sheng|student|students|个 名 位|只 条 本|n
人|rén|person|people|个|只 条 本|n s
孩子|hái zi|child|children|个|只 条 本|s
咖啡|kā fēi|cup of coffee|cups of coffee|杯|条 张 块|d o
茶|chá|cup of tea|cups of tea|杯|条 张 块|d o
牛奶|niú nǎi|glass of milk|glasses of milk|杯|条 张 块|d
果汁|guǒ zhī|glass of juice|glasses of juice|杯|条 张 块|d o
啤酒|pí jiǔ|bottle of beer|bottles of beer|瓶|条 张 块|d b o
可乐|kě lè|bottle of cola|bottles of cola|瓶|条 张 块|d b
矿泉水|kuàng quán shuǐ|bottle of mineral water|bottles of mineral water|瓶|条 张 块|d b
米饭|mǐ fàn|bowl of rice|bowls of rice|碗|条 张 支|e o
面条|miàn tiáo|bowl of noodles|bowls of noodles|碗|张 支 件|e o
汤|tāng|bowl of soup|bowls of soup|碗|条 张 支|d o
蛋糕|dàn gāo|piece of cake|pieces of cake|块|条 张 支|e b
巧克力|qiǎo kè lì|piece of chocolate|pieces of chocolate|块 盒|张 支 本|e b
糖|táng|sweet|sweets|块 颗 粒|条 张 本|e
饼干|bǐng gān|biscuit|biscuits|块 片 包 盒|条 张 本|e
肉|ròu|piece of meat|pieces of meat|块 片|张 支 本|e b
手表|shǒu biǎo|watch|watches|块 只|张 本 件|b t p l
面包|miàn bāo|slice of bread|slices of bread|片 块|张 支 本|e
药|yào|tablet|tablets|片 粒 颗|条 张 支|e
饭|fàn|meal|meals|顿 餐|条 张 本|e
苹果|píng guǒ|apple|apples|个 只 颗|条 张 支|e b
鸡蛋|jī dàn|egg|eggs|个 只 颗 枚|条 张 支|e b
西瓜|xī guā|watermelon|watermelons|个 只|条 张 支|b
包子|bāo zi|steamed bun|steamed buns|个 只|条 张 支|e b
杯子|bēi zi|cup|cups|个 只|条 张 本|b t p
箱子|xiāng zi|suitcase|suitcases|个 只 口|条 张 本|x t b
书包|shū bāo|school bag|school bags|个 只|条 张 本|b t p
香蕉|xiāng jiāo|banana|bananas|根 个 只 把 串|张 本 件|e b
黄瓜|huáng guā|cucumber|cucumbers|根 条|张 本 件|b e
饭馆|fàn guǎn|restaurant|restaurants|家 个 间|所 位 张|V W l
商店|shāng diàn|shop|shops|家 个 间|位 张 条|V W l
公司|gōng sī|company|companies|家 个|位 张 条|W
银行|yín háng|bank|banks|家 个 所|位 张 条|W V
超市|chāo shì|supermarket|supermarkets|家 个|位 张 条|W V
宾馆|bīn guǎn|hotel|hotels|家 个 座|位 张 条|V W
咖啡店|kā fēi diàn|café|cafés|家 个 间|位 张 条|V W l
书店|shū diàn|bookshop|bookshops|家 个|位 张 条|V W l
工厂|gōng chǎng|factory|factories|家 个 座|位 张 条|W
医院|yī yuàn|hospital|hospitals|家 所 个 座|位 张 条|W V
学校|xué xiào|school|schools|所 个|位 张 条|W
大学|dà xué|university|universities|所 个|位 张 条|W
房间|fáng jiān|room|rooms|间 个|张 条 位|K l
教室|jiào shì|classroom|classrooms|间 个|张 条 位|l
电脑|diàn nǎo|computer|computers|台 部 个|辆 张 条|b t p h
电视|diàn shì|TV|TVs|台 部 个|辆 张 条|b t p
冰箱|bīng xiāng|fridge|fridges|台 个|辆 张 条|b t p
洗衣机|xǐ yī jī|washing machine|washing machines|台 个|辆 张 条|b t p
空调|kōng tiáo|air conditioner|air conditioners|台 个 部|辆 张 条|b t p
照相机|zhào xiàng jī|camera|cameras|台 部 个 架|辆 张 条|b t p l
手机|shǒu jī|phone|phones|部 个 台 支|辆 张 条|b t p l h
电影|diàn yǐng|film|films|部 个 场|本 张 条|m l
电视剧|diàn shì jù|TV series|TV series|部 个|本 张 条|m l
树|shù|tree|trees|棵 株|朵 张 只|s f
白菜|bái cài|Chinese cabbage|Chinese cabbages|棵 颗 个|朵 条 张|b
花|huā|flower|flowers|朵 束 枝 支 盆 棵|张 条 本|b s l
信|xìn|letter|letters|封|本 张 件|w
邮件|yóu jiàn|email|emails|封 个|本 张 条|w U
歌|gē|song|songs|首 支 个|本 张 条|c i l
诗|shī|poem|poems|首|本 张 条|w
课|kè|class|classes|节 堂 门|本 张 条|a
山|shān|mountain|mountains|座|条 张 棵|s f
桥|qiáo|bridge|bridges|座|张 棵 辆|s f
城市|chéng shì|city|cities|座 个|家 条 张|V l
大楼|dà lóu|building|buildings|座 栋 幢 个|条 张 辆|f
公园|gōng yuán|park|parks|个 座|位 张 条|V l
博物馆|bó wù guǎn|museum|museums|个 座 家 所|位 张 条|V
图书馆|tú shū guǎn|library|libraries|个 座 家 所|位 张 条|V W
语言|yǔ yán|language|languages|种 门|本 张 条|L
水果|shuǐ guǒ|kind of fruit|kinds of fruit|种 样|本 张 条|b e
颜色|yán sè|colour|colours|种 个|本 张 条|l
房子|fáng zi|house|houses|套 栋 座 所 间 个 幢|条 张 辆|b t p l
问题|wèn tí|question|questions|个 道|本 张 件|q
故事|gù shi|story|stories|个 则 段|本 张 件|G i
汉字|hàn zì|Chinese character|Chinese characters|个|本 张 条|w
句子|jù zi|sentence|sentences|个|本 张 件|w
话|huà|sentence|sentences|句 段|本 张 件|H
文章|wén zhāng|article|articles|篇|本 张 条|w r
日记|rì jì|diary entry|diary entries|篇|张 条 件|w
作文|zuò wén|essay|essays|篇|张 条 件|w
菜|cài|dish|dishes|个 道 盘 份 样|条 张 本|o
比赛|bǐ sài|match|matches|场 次 个|本 张 条|m J
考试|kǎo shì|exam|exams|场 次 个|本 张 条|J
音乐会|yīn yuè huì|concert|concerts|场 个 次|本 张 条|i
窗户|chuāng hu|window|windows|扇 个|张 条 本|O
门|mén|door|doors|扇 道 个|张 条 本|O
灯|dēng|lamp|lamps|盏 个|张 条 本|b t p
镜子|jìng zi|mirror|mirrors|面 个 块|条 本 支|b t p
`).map(([zh, py, sg, pl, ok, bad, frames]) => ({
  zh,
  py,
  sg,
  pl,
  ok: ok.split(' '),
  bad: bad.split(' '),
  frames: frames.split(' '),
}));

const NUMS = [
  ['一', 'one'],
  ['两', 'two'],
  ['三', 'three'],
  ['四', 'four'],
  ['五', 'five'],
  ['六', 'six'],
];

// code -> counted frame: text before the number, English with {q} = "three books"
const COUNT_FRAMES = {
  b: [
    ['想买|xiǎng mǎi', '{S} [want] to buy {q}.', 6],
    ['昨天买了|zuó tiān mǎi le', '{S} bought {q} yesterday.', 6],
  ],
  h: [['有|yǒu', '{S} {have} {q}.', 3]],
  y: [['养了|yǎng le', '{S} {have} {q}.', 3]],
  e: [['吃了|chī le', '{S} ate {q}.', 3]],
  d: [['喝了|hē le', '{S} drank {q}.', 3]],
  s: [['看见了|kàn jiàn le', '{S} saw {q}.', 5]],
  w: [['写了|xiě le', '{S} wrote {q}.', 5]],
  r: [['看了|kàn le', '{S} read {q}.', 3]],
  m: [['看了|kàn le', '{S} watched {q}.', 3]],
  c: [['唱了|chàng le', '{S} sang {q}.', 3]],
  i: [['听了|tīng le', '{S} listened to {q}.', 3]],
  a: [['今天上了|jīn tiān shàng le', '{S} had {q} today.', 4]],
  o: [['点了|diǎn le', '{S} ordered {q}.', 4]],
  j: [['借了|jiè le', '{S} borrowed {q}.', 4]],
  z: [['照了|zhào le', '{S} took {q}.', 6]],
  x: [['带了|dài le', '{S} brought {q}.', 4]],
  q: [['问了|wèn le', '{S} asked {q}.', 5]],
  I: [['请了|qǐng le', '{S} invited {q}.', 6]],
  K: [['订了|dìng le', '{S} booked {q}.', 3]],
  T: [['抽了|chōu le', '{S} smoked {q}.', 3]],
  G: [['讲了|jiǎng le', '{S} told {q}.', 3]],
  J: [['参加了|cān jiā le', '{S} took part in {q}.', 3]],
  L: [['会说|huì shuō', '{S} can speak {q}.', 4]],
  U: [['发了|fā le', '{S} sent {q}.', 5]],
  H: [['只说了|zhǐ shuō le', '{S} only said {q}.', 3]],
};

// code -> frame with 这 / 那: [before, after, English with {d} = "this book"]
const DEMO_FRAMES = {
  l: ['很喜欢|hěn xǐ huan', '', '{S} really [like] {d}.'],
  n: ['认识|rèn shi', '', '{S} [know] {d}.'],
  V: ['去过|qù guo', '', '{S} {have} been to {d}.'],
  W: ['在|zài', '工作|gōng zuò', '{S} [work] at {d}.'],
  O: ['打开了|dǎ kāi le', '', '{S} opened {d}.'],
};
const DEMOS = [
  ['这', 'zhè', 'this'],
  ['那', 'nà', 'that'],
];

function why(noun, wrong) {
  const m = MEASURES[noun.ok[0]];
  const others = wrong
    .slice(0, 2)
    .map((b) => `${b} is for ${MEASURES[b].use}`)
    .join('; ');
  return `${noun.zh} is counted with ${m.zh}, the measure for ${m.use}. ${others}.`;
}

function makeMeasure(rng) {
  const noun = pick(rng, NOUNS);
  const code = pick(rng, noun.frames);
  const m = MEASURES[noun.ok[0]];
  const tail = { zh: noun.zh, py: noun.py };
  const base = { key: 'measure-words', right: m, wrong: noun.bad, why: why(noun, noun.bad) };
  if (code === 'f') {
    const [n, en] = pick(rng, NUMS.slice(0, 3));
    return cloze(rng, {
      ...base,
      pre: ['前面有|qián miàn yǒu', numWord(n)],
      post: [tail, '。'],
      en: n === '一' ? `There is one ${noun.sg} ahead.` : `There are ${en} ${noun.pl} ahead.`,
    });
  }
  if (code === 't' || code === 'p') {
    const [d, dpy, den] = pick(rng, DEMOS);
    const whose = code === 't';
    return cloze(rng, {
      ...base,
      pre: [{ zh: d, py: dpy }],
      post: [tail, whose ? '是谁的|shì shéi de' : '多少钱|duō shao qián', '？'],
      en: whose ? `Whose is ${den} ${noun.sg}?` : `How much is ${den} ${noun.sg}?`,
    });
  }
  const s = pick(rng, PEOPLE);
  if (DEMO_FRAMES[code]) {
    const [before, after, en] = DEMO_FRAMES[code];
    const [d, dpy, den] = pick(rng, DEMOS);
    return cloze(rng, {
      ...base,
      pre: [s, before, { zh: d, py: dpy }],
      post: [tail, after, '。'],
      en: fillEn(en, s).replace('{d}', `${den} ${noun.sg}`),
    });
  }
  const [before, en, maxN] = pick(rng, COUNT_FRAMES[code]);
  const [n, nen] = weighted(
    rng,
    NUMS.slice(0, maxN).map((x, i) => [i < 3 ? 3 : 1, x])
  );
  return cloze(rng, {
    ...base,
    pre: [s, before, numWord(n)],
    post: [tail, '。'],
    en: fillEn(en, s).replace('{q}', `${nen} ${n === '一' ? noun.sg : noun.pl}`),
  });
}

export const generators = [
  { key: 'measure-words', label: 'Measure word for the noun', make: makeMeasure },
];
