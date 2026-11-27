/**
 * word-order generator: subject + time + place + verb phrase as order
 * tiles. The only free element is the time word, which may also open the
 * sentence, so every item lists exactly that alternative. Adverb items
 * (也 / 都 / 常常) are built so that only one order is possible.
 */
import { pick, weighted, rows, order, PEOPLE, vb } from './util.js';

// time | py | English | f future ("will"), h habitual (present)
const TIMES = rows(`
明天|míng tiān|tomorrow|f
今天下午|jīn tiān xià wǔ|this afternoon|f
今天晚上|jīn tiān wǎn shang|tonight|f
这个周末|zhè ge zhōu mò|this weekend|f
星期六|xīng qī liù|on Saturday|f
下个星期|xià ge xīng qī|next week|f
明天上午|míng tiān shàng wǔ|tomorrow morning|f
后天|hòu tiān|the day after tomorrow|f
明天晚上|míng tiān wǎn shang|tomorrow evening|f
每天|měi tiān|every day|h
每天晚上|měi tiān wǎn shang|every evening|h
每个周末|měi ge zhōu mò|every weekend|h
每天下午|měi tiān xià wǔ|every afternoon|h
`);

// place | py | English | verb | py | object | py | English base form | "f" = one-off, future only; "fd" = also daytime only; "h" = habit only
const PLACED = rows(`
在家|zài jiā|at home|看|kàn|电视|diàn shì|watch TV|
在家|zài jiā|at home|做|zuò|饭|fàn|cook|
在家|zài jiā|at home|看|kàn|书|shū|read|
在家|zài jiā|at home|做|zuò|作业|zuò yè|do homework|
在家|zài jiā|at home|学习|xué xí|汉语|hàn yǔ|study Chinese|
在家|zài jiā|at home|打扫|dǎ sǎo|房间|fáng jiān|clean the room|
在家|zài jiā|at home|听|tīng|音乐|yīn yuè|listen to music|
在家|zài jiā|at home|休息|xiū xi|||rest|
在家|zài jiā|at home|洗|xǐ|衣服|yī fu|do the laundry|
在学校|zài xué xiào|at school|学习|xué xí|汉语|hàn yǔ|study Chinese|
在学校|zài xué xiào|at school|打|dǎ|篮球|lán qiú|play basketball|
在学校|zài xué xiào|at school|踢|tī|足球|zú qiú|play football|
在学校|zài xué xiào|at school|吃|chī|饭|fàn|eat|
在图书馆|zài tú shū guǎn|at the library|看|kàn|书|shū|read|
在图书馆|zài tú shū guǎn|at the library|学习|xué xí|||study|
在图书馆|zài tú shū guǎn|at the library|做|zuò|作业|zuò yè|do homework|
在图书馆|zài tú shū guǎn|at the library|复习|fù xí|生词|shēng cí|revise vocabulary|
在图书馆|zài tú shū guǎn|at the library|准备|zhǔn bèi|考试|kǎo shì|prepare for the exam|f
在公司|zài gōng sī|at the office|开|kāi|会|huì|have a meeting|
在公司|zài gōng sī|at the office|加|jiā|班|bān|work overtime|
在公司|zài gōng sī|at the office|写|xiě|报告|bào gào|write reports|
在饭馆|zài fàn guǎn|at a restaurant|吃|chī|饭|fàn|eat|
在饭馆|zài fàn guǎn|at a restaurant|见|jiàn|朋友|péng you|meet friends|
在公园|zài gōng yuán|in the park|散|sàn|步|bù|take a walk|
在公园|zài gōng yuán|in the park|跑|pǎo|步|bù|go running|
在公园|zài gōng yuán|in the park|打|dǎ|太极拳|tài jí quán|do tai chi|
在公园|zài gōng yuán|in the park|锻炼|duàn liàn|身体|shēn tǐ|exercise|
在咖啡店|zài kā fēi diàn|at a café|喝|hē|咖啡|kā fēi|drink coffee|
在咖啡店|zài kā fēi diàn|at a café|见|jiàn|朋友|péng you|meet friends|
在咖啡店|zài kā fēi diàn|at a café|看|kàn|书|shū|read|
在超市|zài chāo shì|at the supermarket|买|mǎi|东西|dōng xi|do the shopping|
在超市|zài chāo shì|at the supermarket|买|mǎi|水果|shuǐ guǒ|buy fruit|
在超市|zài chāo shì|at the supermarket|买|mǎi|菜|cài|buy groceries|
在体育馆|zài tǐ yù guǎn|at the sports hall|打|dǎ|篮球|lán qiú|play basketball|
在体育馆|zài tǐ yù guǎn|at the sports hall|打|dǎ|羽毛球|yǔ máo qiú|play badminton|
在体育馆|zài tǐ yù guǎn|at the sports hall|锻炼|duàn liàn|身体|shēn tǐ|exercise|
在机场|zài jī chǎng|at the airport|接|jiē|朋友|péng you|pick up a friend|f
在电影院|zài diàn yǐng yuàn|at the cinema|看|kàn|电影|diàn yǐng|watch a film|
在商店|zài shāng diàn|at the shop|买|mǎi|衣服|yī fu|buy clothes|f
在商店|zài shāng diàn|at the shop|买|mǎi|礼物|lǐ wù|buy a present|f
在宿舍|zài sù shè|in the dorm|睡|shuì|觉|jiào|sleep|h
在宿舍|zài sù shè|in the dorm|做|zuò|作业|zuò yè|do homework|
在宿舍|zài sù shè|in the dorm|洗|xǐ|衣服|yī fu|do the laundry|
在宿舍|zài sù shè|in the dorm|休息|xiū xi|||rest|
在食堂|zài shí táng|in the canteen|吃|chī|饭|fàn|eat|
在游泳馆|zài yóu yǒng guǎn|at the pool|游|yóu|泳|yǒng|swim|
在医院|zài yī yuàn|at the hospital|看|kàn|病|bìng|see a doctor|f
在银行|zài yín háng|at the bank|取|qǔ|钱|qián|withdraw money|fd
在银行|zài yín háng|at the bank|换|huàn|钱|qián|change money|fd
在邮局|zài yóu jú|at the post office|寄|jì|信|xìn|post a letter|fd
在朋友家|zài péng you jiā|at a friend's place|吃|chī|饭|fàn|have a meal|f
在朋友家|zài péng you jiā|at a friend's place|看|kàn|电影|diàn yǐng|watch a film|f
在朋友家|zài péng you jiā|at a friend's place|玩|wán|游戏|yóu xì|play games|f
在教室|zài jiào shì|in the classroom|上|shàng|课|kè|have class|
在教室|zài jiào shì|in the classroom|做|zuò|作业|zuò yè|do homework|
在教室|zài jiào shì|in the classroom|复习|fù xí|生词|shēng cí|revise vocabulary|
`);

// activity done together: verb | py | object | py | English base form
const TOGETHER = rows(`
看|kàn|电影|diàn yǐng|watch a film
吃|chī|饭|fàn|have a meal
打|dǎ|篮球|lán qiú|play basketball
去|qù|公园|gōng yuán|go to the park
喝|hē|咖啡|kā fēi|have coffee
学习|xué xí|汉语|hàn yǔ|study Chinese
爬|pá|山|shān|go hiking
唱|chàng|歌|gē|sing
踢|tī|足球|zú qiú|play football
做|zuò|饭|fàn|cook
去|qù|超市|chāo shì|go to the supermarket
打|dǎ|羽毛球|yǔ máo qiú|play badminton
`);
const PARTNERS = rows(`
跟朋友一起|gēn péng you yī qǐ|with friends
跟同学一起|gēn tóng xué yī qǐ|with classmates
跟家人一起|gēn jiā rén yī qǐ|with family
跟同事一起|gēn tóng shì yī qǐ|with colleagues
`);

// habit: verb | py | object | py | English base form
const HABITS = rows(`
喝|hē|咖啡|kā fēi|drink coffee
吃|chī|肉|ròu|eat meat
喝|hē|酒|jiǔ|drink alcohol
看|kàn|电视|diàn shì|watch TV
喜欢|xǐ huan|运动|yùn dòng|like exercise
坐|zuò|地铁|dì tiě|take the subway
吃|chī|早饭|zǎo fàn|eat breakfast
听|tīng|音乐|yīn yuè|listen to music
打|dǎ|篮球|lán qiú|play basketball
喝|hē|茶|chá|drink tea
做|zuò|饭|fàn|cook
玩|wán|游戏|yóu xì|play games
`);

const GROUPS = [
  { zh: '我们', py: 'wǒ men', en: 'We', obj: 'us' },
  { zh: '他们', py: 'tā men', en: 'They', obj: 'them' },
  { zh: '同学们', py: 'tóng xué men', en: 'The classmates', obj: 'them' },
  { zh: '我爸爸妈妈', py: 'wǒ bà ba mā ma', en: 'My parents', obj: 'them' },
];

const part = (zh, py) => ({ zh, py });
const vp = (v, vpy, o, opy) => (o ? [part(v, vpy), part(o, opy)] : [part(v, vpy)]);
const KEY = 'word-order';

function makeTimePlace(rng) {
  const s = pick(rng, PEOPLE);
  const [place, ppy, pen, v, vpy, o, opy, en, once] = pick(rng, PLACED);
  const [t, tpy, ten, tense] = pick(
    rng,
    TIMES.filter((x) => (!once || x[3] === once[0]) && !(once === 'fd' && x[0].includes('晚上')))
  );
  const tiles = [s, part(t, tpy), part(place, ppy), ...vp(v, vpy, o, opy)];
  const rest = tiles.map((_, i) => i).slice(2);
  return order(rng, {
    key: KEY,
    tiles,
    alts: [[1, 0, ...rest]],
    en: tense === 'f' ? `${s.en} will ${en} ${pen} ${ten}.` : `${s.en} ${vb(s, en)} ${pen} ${ten}.`,
    why: `Subject + time + place + verb: ${t} (when) comes before ${place} (where), and both come before ${v}. The time word may also open the sentence, but neither time nor place can follow the verb as in English.`,
  });
}

function makeTogether(rng) {
  const s = pick(rng, PEOPLE);
  const [v, vpy, o, opy, en] = pick(rng, TOGETHER);
  const [p, ppy, pen] = pick(rng, PARTNERS);
  const [t, tpy, ten] = pick(
    rng,
    TIMES.filter((x) => x[3] === 'f')
  );
  return order(rng, {
    key: KEY,
    tiles: [s, part(t, tpy), part(p, ppy), part(v, vpy), part(o, opy)],
    alts: [[1, 0, 2, 3, 4]],
    en: `${s.en} will ${en} ${pen} ${ten}.`,
    why: `Who you do it with goes before the verb: subject + time + 跟…一起 + verb. "With friends" cannot follow the verb as in English; only ${t} may move to the front.`,
  });
}

function makeAdverb(rng) {
  const kind = pick(rng, ['ye-dou', 'ye-dou-bu', 'ye-changchang', 'dou-place', 'ye-place']);
  const [v, vpy, o, opy, en] = pick(
    rng,
    HABITS.filter((x) => kind !== 'ye-changchang' || x[0] !== '喜欢')
  );
  if (kind === 'ye-changchang') {
    const s = pick(rng, PEOPLE);
    return order(rng, {
      key: KEY,
      tiles: [s, '也|yě', '常常|cháng cháng', part(v, vpy), part(o, opy)],
      en: `${s.en} often ${vb(s, en)} too.`,
      why: 'Adverbs stand between the subject and the verb, and 也 comes first among them: 也常常 + verb. An adverb never goes before the subject or after the verb.',
    });
  }
  if (kind === 'dou-place' || kind === 'ye-place') {
    const dou = kind === 'dou-place';
    const s = dou ? pick(rng, GROUPS) : pick(rng, PEOPLE);
    const [place, ppy, pen, pv, pvpy, po, popy, pe] = pick(
      rng,
      PLACED.filter((x) => !x[8])
    );
    return order(rng, {
      key: KEY,
      tiles: [s, dou ? '都|dōu' : '也|yě', part(place, ppy), ...vp(pv, pvpy, po, popy)],
      en: dou ? `${s.en} all ${pe} ${pen}.` : `${s.en} also ${vb(s, pe)} ${pen}.`,
      why: `${dou ? '都' : '也'} follows the subject directly and comes before the place phrase ${place}, which in turn comes before the verb: subject + adverb + place + verb.`,
    });
  }
  const s = pick(rng, GROUPS);
  const neg = kind === 'ye-dou-bu';
  return order(rng, {
    key: KEY,
    tiles: [s, '也|yě', '都|dōu', neg && '不|bù', part(v, vpy), part(o, opy)].filter(Boolean),
    en: neg ? `${s.en} don't ${en} either, none of ${s.obj}.` : `${s.en} all ${en} too.`,
    why: neg
      ? 'Fixed adverb order before the verb: 也, then 都, then 不. All three stand between the subject and the verb.'
      : 'When both appear, 也 comes before 都, and both stand between the subject and the verb.',
  });
}

function makeWordOrder(rng) {
  return weighted(rng, [
    [6, makeTimePlace],
    [2, makeTogether],
    [3, makeAdverb],
  ])(rng);
}

export const generators = [{ key: KEY, label: 'Time, place, adverbs', make: makeWordOrder }];
