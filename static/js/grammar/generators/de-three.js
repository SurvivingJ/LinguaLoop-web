/**
 * de-three generator: 的 / 得 / 地 decided by syntax. Three frame families
 * built from lists that are only combined where every pairing is natural:
 * modifier + 的 + noun, verb (or adjective) + 得 + complement, adverbial +
 * 地 + verb. Frames where two particles would both work (高兴地笑了 /
 * 高兴得笑了) are deliberately absent.
 */
import { pick, weighted, rows, cloze, PEOPLE, fillEn, vb, dont, poss, cap } from './util.js';

const DE = { 的: '的|de', 得: '得|de', 地: '地|de' };
const three = (rng, right, opts) =>
  cloze(rng, {
    key: 'de-three',
    right: DE[right],
    wrong: Object.keys(DE).filter((k) => k !== right),
    ...opts,
  });

/* ---------- 的: modifier + noun ---------- */

// noun | py | measure | py | English | class (c clothes, g gadgets)
const BOUGHT = rows(`
裙子|qún zi|条|tiáo|skirt|c
毛衣|máo yī|件|jiàn|sweater|c
衬衫|chèn shān|件|jiàn|shirt|c
帽子|mào zi|顶|dǐng|hat|c
大衣|dà yī|件|jiàn|coat|c
围巾|wéi jīn|条|tiáo|scarf|c
手机|shǒu jī|个|gè|phone|g
电脑|diàn nǎo|台|tái|computer|g
手表|shǒu biǎo|块|kuài|watch|g
自行车|zì xíng chē|辆|liàng|bicycle|g
照相机|zhào xiàng jī|台|tái|camera|g
`);
// modifier | py | English | classes
const MODS = rows(`
很漂亮|hěn piào liang|very pretty|c
很贵|hěn guì|very expensive|cg
很便宜|hěn pián yi|very cheap|cg
很好看|hěn hǎo kàn|very nice-looking|cg
非常贵|fēi cháng guì|extremely expensive|cg
特别好看|tè bié hǎo kàn|really nice-looking|cg
很舒服|hěn shū fu|very comfortable|c
很暖和|hěn nuǎn huo|very warm|c
很好用|hěn hǎo yòng|very handy|g
很轻|hěn qīng|very light|g
`);

// clause | py | noun | py | English noun phrase | predicate | py | English predicate
const CLAUSES = rows(`
妈妈做|mā ma zuò|菜|cài|the food Mom cooks|很好吃|hěn hǎo chī|is delicious
这家饭馆做|zhè jiā fàn guǎn zuò|鱼|yú|the fish this restaurant makes|很好吃|hěn hǎo chī|is delicious
奶奶包|nǎi nai bāo|饺子|jiǎo zi|the dumplings Grandma makes|特别香|tè bié xiāng|smell wonderful
姐姐做|jiě jie zuò|蛋糕|dàn gāo|the cake my sister makes|很甜|hěn tián|is very sweet
朋友送|péng you sòng|礼物|lǐ wù|the present a friend gave|很漂亮|hěn piào liang|is very pretty
昨天买|zuó tiān mǎi|衣服|yī fu|the clothes bought yesterday|有点儿大|yǒu diǎn r dà|are a bit big
昨天买|zuó tiān mǎi|水果|shuǐ guǒ|the fruit bought yesterday|很新鲜|hěn xīn xiān|is very fresh
上个星期看|shàng ge xīng qī kàn|电影|diàn yǐng|the film seen last week|很有意思|hěn yǒu yì si|is very interesting
老师介绍|lǎo shī jiè shào|书|shū|the book the teacher recommended|很有用|hěn yǒu yòng|is very useful
他唱|tā chàng|歌|gē|the songs he sings|很好听|hěn hǎo tīng|sound lovely
她画|tā huà|画|huà|the pictures she paints|很漂亮|hěn piào liang|are very pretty
朋友拍|péng you pāi|照片|zhào piàn|the photos a friend took|很好看|hěn hǎo kàn|look great
爸爸买|bà ba mǎi|手机|shǒu jī|the phone Dad bought|很好用|hěn hǎo yòng|is very handy
小王写|xiǎo wáng xiě|汉字|hàn zì|the characters Xiao Wang writes|很漂亮|hěn piào liang|are very pretty
这家店卖|zhè jiā diàn mài|面包|miàn bāo|the bread this shop sells|很便宜|hěn pián yi|is very cheap
学校旁边|xué xiào páng biān|咖啡店|kā fēi diàn|the café next to the school|很安静|hěn ān jìng|is very quiet
公司附近|gōng sī fù jìn|饭馆|fàn guǎn|the restaurants near the office|都很贵|dōu hěn guì|are all expensive
今天学|jīn tiān xué|生词|shēng cí|the new words learned today|不太难|bù tài nán|are not very hard
刚出|gāng chū|新手机|xīn shǒu jī|the new phone that just came out|非常贵|fēi cháng guì|is extremely expensive
去年去|qù nián qù|那个城市|nà ge chéng shì|the city visited last year|很干净|hěn gān jìng|is very clean
`);

// possessed noun | py | English
const OWNED = rows(`
手机|shǒu jī|phone
书|shū|book
词典|cí diǎn|dictionary
电脑|diàn nǎo|computer
雨伞|yǔ sǎn|umbrella
钥匙|yào shi|key
书包|shū bāo|school bag
自行车|zì xíng chē|bicycle
房间|fáng jiān|room
照片|zhào piàn|photo
护照|hù zhào|passport
座位|zuò wèi|seat
杯子|bēi zi|cup
帽子|mào zi|hat
行李|xíng li|luggage
`);

function makeDe(rng) {
  const s = pick(rng, PEOPLE);
  const kind = weighted(rng, [
    [3, 'adj'],
    [3, 'clause'],
    [1, 'owner'],
  ]);
  if (kind === 'owner') {
    const [n, npy, en] = pick(rng, OWNED);
    return three(rng, '的', {
      pre: ['这是|zhè shì', s],
      post: [{ zh: n, py: npy }, '。'],
      en: `This is ${poss(s)} ${en}.`,
      why: `${s.zh} says whose ${n} it is: an owner in front of a noun is linked with 的. 得 only follows a verb or adjective, and 地 only comes before a verb.`,
    });
  }
  if (kind === 'adj') {
    const [n, npy, m, mpy, en, cls] = pick(rng, BOUGHT);
    const [mod, modpy, moden] = pick(
      rng,
      MODS.filter((x) => x[3].includes(cls))
    );
    const want = rng() < 0.4;
    const art = /^[aeiou]/.test(moden) ? 'an' : 'a';
    return three(rng, '的', {
      pre: [s, want ? '想买一|xiǎng mǎi yī' : '买了一|mǎi le yī', { zh: m, py: mpy }, { zh: mod, py: modpy }],
      post: [{ zh: n, py: npy }, '。'],
      en: `${s.en} ${want ? `${vb(s, 'want')} to buy` : 'bought'} ${art} ${moden} ${en}.`,
      why: `${mod} describes the noun ${n}. A describing phrase in front of a noun is linked with 的; 得 would need a verb before it and 地 a verb after it.`,
    });
  }
  const [c, cpy, n, npy, np, pred, predpy, preden] = pick(rng, CLAUSES);
  const why = `${c} tells which ${n} is meant, so the whole phrase modifies a noun and takes 的. 得 introduces a complement after a verb and 地 marks an adverbial before a verb; neither can stand before a noun.`;
  if (rng() < 0.5) {
    return three(rng, '的', {
      pre: [{ zh: c, py: cpy }],
      post: [{ zh: n, py: npy }, { zh: pred, py: predpy }, '。'],
      en: `${cap(np)} ${preden}.`,
      why,
    });
  }
  return three(rng, '的', {
    pre: [s, '很喜欢|hěn xǐ huan', { zh: c, py: cpy }],
    post: [{ zh: n, py: npy }, '。'],
    en: `${s.en} really ${vb(s, 'like')} ${np}.`,
    why,
  });
}

/* ---------- 得: verb + complement ---------- */

// verb | py | object repeated before the verb (or empty) | py | adjective | py | English verb phrase | English adverb
const DEGREE = rows(`
跑|pǎo|||快|kuài|run|fast
跑|pǎo|||慢|màn|run|slowly
走|zǒu|||快|kuài|walk|fast
走|zǒu|||慢|màn|walk|slowly
说|shuō|||快|kuài|speak|fast
说|shuō|||慢|màn|speak|slowly
说|shuō|||清楚|qīng chu|speak|clearly
说|shuō|汉语|hàn yǔ|流利|liú lì|speak Chinese|fluently
说|shuō|汉语|hàn yǔ|好|hǎo|speak Chinese|well
说|shuō|英语|yīng yǔ|流利|liú lì|speak English|fluently
写|xiě|||快|kuài|write|fast
写|xiě|||慢|màn|write|slowly
写|xiě|||清楚|qīng chu|write|clearly
写|xiě|汉字|hàn zì|漂亮|piào liang|write characters|beautifully
写|xiě|汉字|hàn zì|好|hǎo|write characters|well
唱|chàng|歌|gē|好|hǎo|sing|well
唱|chàng|歌|gē|好听|hǎo tīng|sing|beautifully
跳|tiào|舞|wǔ|好|hǎo|dance|well
跳|tiào|||高|gāo|jump|high
画|huà|画|huà|好|hǎo|paint|well
画|huà|画|huà|漂亮|piào liang|paint|beautifully
做|zuò|饭|fàn|好|hǎo|cook|well
做|zuò|饭|fàn|快|kuài|cook|quickly
学|xué|||快|kuài|learn|fast
学|xué|||好|hǎo|learn|well
学|xué|||认真|rèn zhēn|study|conscientiously
吃|chī|||快|kuài|eat|fast
吃|chī|||慢|màn|eat|slowly
吃|chī|||少|shǎo|eat|little
起|qǐ|||早|zǎo|get up|early
起|qǐ|||晚|wǎn|get up|late
睡|shuì|||早|zǎo|go to bed|early
睡|shuì|||晚|wǎn|go to bed|late
睡|shuì|||好|hǎo|sleep|well
来|lái|||早|zǎo|come|early
来|lái|||晚|wǎn|come|late
到|dào|||早|zǎo|arrive|early
考|kǎo|||好|hǎo|do|well in the exam
打|dǎ|篮球|lán qiú|好|hǎo|play basketball|well
打|dǎ|乒乓球|pīng pāng qiú|好|hǎo|play table tennis|well
踢|tī|足球|zú qiú|好|hǎo|play football|well
弹|tán|钢琴|gāng qín|好|hǎo|play the piano|well
弹|tán|钢琴|gāng qín|好听|hǎo tīng|play the piano|beautifully
游|yóu|泳|yǒng|快|kuài|swim|fast
游|yóu|泳|yǒng|好|hǎo|swim|well
开|kāi|车|chē|快|kuài|drive|fast
开|kāi|车|chē|慢|màn|drive|slowly
开|kāi|车|chē|好|hǎo|drive|well
穿|chuān|||少|shǎo|dress|lightly
穿|chuān|||漂亮|piào liang|dress|beautifully
住|zhù|||远|yuǎn|live|far away
住|zhù|||近|jìn|live|close by
讲|jiǎng|||清楚|qīng chu|explain things|clearly
讲|jiǎng|||快|kuài|talk|fast
洗|xǐ|衣服|yī fu|干净|gān jìng|wash clothes|clean
打扫|dǎ sǎo|||干净|gān jìng|clean up|thoroughly
准备|zhǔn bèi|||好|hǎo|prepare|well
回答|huí dá|||好|hǎo|answer|well
回答|huí dá|||快|kuài|answer|quickly
表演|biǎo yǎn|||好|hǎo|perform|well
休息|xiū xi|||好|hǎo|rest|well
工作|gōng zuò|||认真|rèn zhēn|work|conscientiously
工作|gōng zuò|||努力|nǔ lì|work|hard
笑|xiào|||开心|kāi xīn|laugh|happily
`);
const DEGREES = [
  ['很', 'hěn', 'very'],
  ['非常', 'fēi cháng', 'extremely'],
  ['特别', 'tè bié', 'especially'],
  ['真', 'zhēn', 'really'],
  ['不太', 'bù tài', ''],
];

// adjective | py | result clause | py | English with {S}
const EXTENT = rows(`
累|lèi|不想说话|bù xiǎng shuō huà|{S} {is} too tired to talk.
累|lèi|走不动了|zǒu bù dòng le|{S} {is} too tired to walk any further.
累|lèi|什么都不想做|shén me dōu bù xiǎng zuò|{S} {is} too tired to do anything.
忙|máng|没时间吃饭|méi shí jiān chī fàn|{S} {is} too busy to eat.
忙|máng|没时间睡觉|méi shí jiān shuì jiào|{S} {is} too busy to sleep.
忙|máng|连周末都不能休息|lián zhōu mò dōu bù néng xiū xi|{S} {is} so busy that even weekends are not free.
紧张|jǐn zhāng|说不出话|shuō bù chū huà|{S} {is} too nervous to speak.
紧张|jǐn zhāng|睡不着觉|shuì bù zháo jiào|{S} {is} too nervous to sleep.
气|qì|说不出话|shuō bù chū huà|{S} {is} too angry to speak.
笑|xiào|肚子都疼了|dù zi dōu téng le|{S} laughed until it hurt.
急|jí|哭了|kū le|{S} {was} worried to the point of tears.
`);

function makeDeComplement(rng) {
  const s = pick(rng, PEOPLE);
  if (rng() < 0.15) {
    const [adj, apy, res, respy, en] = pick(rng, EXTENT);
    return three(rng, '得', {
      pre: [s, { zh: adj, py: apy }],
      post: [{ zh: res, py: respy }, '。'],
      en: fillEn(en, s),
      why: `${res} says how far ${adj} goes: a result or extent after a verb or adjective is introduced by 得. 的 would need a noun after it, and 地 an adverbial before it.`,
    });
  }
  const [v, vpy, o, opy, adj, apy, enV, enAdv] = pick(rng, DEGREE);
  const [d, dpy, den] = pick(
    rng,
    DEGREES.filter((x) => x[0] !== '不太' || !'慢少晚远近'.includes(adj))
  );
  const head = o ? [s, { zh: v + o, py: `${vpy} ${opy}` }, { zh: v, py: vpy }] : [s, { zh: v, py: vpy }];
  const en =
    d === '不太'
      ? `${s.en} ${dont(s)} ${enV} very ${enAdv}.`
      : `${s.en} ${vb(s, enV)} ${den} ${enAdv}.`;
  const repeat = o
    ? ` With the object ${o}, the verb is said again so that 得 still follows the verb directly.`
    : '';
  return three(rng, '得', {
    pre: head,
    post: [{ zh: d + adj, py: `${dpy} ${apy}` }, '。'],
    en,
    why: `${d}${adj} judges how the action ${v} is done, so it is a complement after the verb, linked with 得. 的 links to a noun; 地 stands before the verb.${repeat}`,
  });
}

/* ---------- 地: adverbial + verb ---------- */

// text before | py | adverbial | py | verb phrase | py | English with {S}
const MANNER = rows(`
每天都|měi tiān dōu|认真|rèn zhēn|学习|xué xí|{S} [study] conscientiously every day.
每天都|měi tiān dōu|努力|nǔ lì|工作|gōng zuò|{S} [work] hard every day.
每天都|měi tiān dōu|认真|rèn zhēn|练习汉字|liàn xí hàn zì|{S} [practise] characters carefully every day.
正在|zhèng zài|认真|rèn zhēn|做作业|zuò zuò yè|{S} {is} doing homework carefully.
正在|zhèng zài|认真|rèn zhēn|听老师讲课|tīng lǎo shī jiǎng kè|{S} {is} listening carefully to the teacher.
正在|zhèng zài|安静|ān jìng|看书|kàn shū|{S} {is} reading quietly.
正在|zhèng zài|努力|nǔ lì|学汉语|xué hàn yǔ|{S} {is} working hard at Chinese.
正在|zhèng zài|大声|dà shēng|读课文|dú kè wén|{S} {is} reading the text aloud.
||慢慢|màn màn|走了过来|zǒu le guò lái|{S} slowly walked over.
||慢慢|màn màn|站了起来|zhàn le qǐ lái|{S} slowly stood up.
||慢慢|màn màn|习惯了这儿的生活|xí guàn le zhè r de shēng huó|{S} slowly got used to life here.
||慢慢|màn màn|明白了|míng bai le|{S} slowly came to understand.
||慢慢|màn màn|喝着茶|hē zhe chá|{S} {was} slowly sipping tea.
||高兴|gāo xìng|告诉大家这个消息|gào su dà jiā zhè ge xiāo xi|{S} happily told everyone the news.
||高兴|gāo xìng|跟大家打招呼|gēn dà jiā dǎ zhāo hu|{S} happily greeted everyone.
||生气|shēng qì|关上了门|guān shàng le mén|{S} angrily shut the door.
||着急|zháo jí|问老师怎么办|wèn lǎo shī zěn me bàn|{S} anxiously asked the teacher what to do.
||仔细|zǐ xì|检查了一遍|jiǎn chá le yī biàn|{S} checked it over carefully.
||仔细|zǐ xì|看了看那张照片|kàn le kàn nà zhāng zhào piàn|{S} looked at the photo carefully.
||小心|xiǎo xīn|拿起杯子|ná qǐ bēi zi|{S} carefully picked up the cup.
||小心|xiǎo xīn|打开了盒子|dǎ kāi le hé zi|{S} carefully opened the box.
||安静|ān jìng|坐在那儿|zuò zài nà r|{S} sat there quietly.
||轻轻|qīng qīng|关上了门|guān shàng le mén|{S} gently closed the door.
||轻轻|qīng qīng|敲了敲门|qiāo le qiāo mén|{S} knocked gently on the door.
||热情|rè qíng|欢迎客人|huān yíng kè rén|{S} warmly welcomed the guests.
||礼貌|lǐ mào|回答了问题|huí dá le wèn tí|{S} answered the question politely.
||很快|hěn kuài|吃完了饭|chī wán le fàn|{S} quickly finished eating.
||很快|hěn kuài|做完了作业|zuò wán le zuò yè|{S} quickly finished the homework.
||不停|bù tíng|看手机|kàn shǒu jī|{S} kept looking at the phone.
||不停|bù tíng|咳嗽|ké sou|{S} kept coughing.
||一遍一遍|yī biàn yī biàn|读课文|dú kè wén|{S} read the text again and again.
||一遍一遍|yī biàn yī biàn|练习|liàn xí|{S} practised again and again.
||好好|hǎo hǎo|休息了一天|xiū xi le yī tiān|{S} had a good day's rest.
||耐心|nài xīn|回答每一个问题|huí dá měi yī gè wèn tí|{S} patiently answered every question.
||耐心|nài xīn|等着|děng zhe|{S} waited patiently.
||舒服|shū fu|躺在沙发上|tǎng zài shā fā shàng|{S} lay comfortably on the sofa.
||顺利|shùn lì|通过了考试|tōng guò le kǎo shì|{S} passed the exam without trouble.
||简单|jiǎn dān|介绍了一下自己|jiè shào le yī xià zì jǐ|{S} gave a brief self-introduction.
||清楚|qīng chu|记得那一天|jì de nà yī tiān|{S} [remember] that day clearly.
||客气|kè qi|说了声谢谢|shuō le shēng xiè xie|{S} politely said thank you.
||安全|ān quán|到家了|dào jiā le|{S} got home safely.
||随便|suí biàn|吃了点儿东西|chī le diǎn r dōng xi|{S} grabbed a quick bite.
||简单|jiǎn dān|吃了点儿早饭|chī le diǎn r zǎo fàn|{S} had a quick breakfast.
`);

function makeDeAdverbial(rng) {
  const s = pick(rng, PEOPLE);
  const [pre, prepy, adv, advpy, vp, vppy, en] = pick(rng, MANNER);
  return three(rng, '地', {
    pre: [s, pre && { zh: pre, py: prepy }, { zh: adv, py: advpy }],
    post: [{ zh: vp, py: vppy }, '。'],
    en: fillEn(en, s),
    why: `${adv} says how the action is carried out and stands in front of the verb (${vp}), so it is an adverbial marked with 地. 的 links to a noun, and 得 comes after the verb, not before it.`,
  });
}

function makeDeThree(rng) {
  return weighted(rng, [
    [4, makeDe],
    [4, makeDeComplement],
    [3, makeDeAdverbial],
  ])(rng);
}

export const generators = [{ key: 'de-three', label: '的 / 得 / 地', make: makeDeThree }];
