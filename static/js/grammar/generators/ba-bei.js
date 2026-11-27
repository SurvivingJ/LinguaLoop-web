/**
 * ba / bei generators: 把 and 被 sentences as order tiles built from
 * (doer, definite object, verb + result) tuples, with negation, modal verbs
 * and adverbs placed before 把 / 被, plus a 把-or-被 cloze where the roles
 * (a doer and a thing) force one of them.
 */
import { pick, weighted, rows, order, cloze, PEOPLE, fillEn, cap } from './util.js';

const part = (zh, py) => ({ zh, py });

/* ---------- 把 ---------- */

// object | py | verb + result | py | English past | English base | g deliberate, b accident
const BA_RESULT = rows(`
作业|zuò yè|做完|zuò wán|finished the homework|finish the homework|g
那本书|nà běn shū|看完|kàn wán|finished that book|finish that book|g
房间|fáng jiān|打扫干净|dǎ sǎo gān jìng|cleaned the room|clean the room|g
房间|fáng jiān|收拾好|shōu shi hǎo|tidied the room|tidy the room|g
衣服|yī fu|洗干净|xǐ gān jìng|washed the clothes|wash the clothes|g
碗|wǎn|洗干净|xǐ gān jìng|washed the dishes|wash the dishes|g
水果|shuǐ guǒ|洗干净|xǐ gān jìng|washed the fruit|wash the fruit|g
桌子|zhuō zi|擦干净|cā gān jìng|wiped the table clean|wipe the table clean|g
门|mén|关上|guān shàng|closed the door|close the door|g
窗户|chuāng hu|打开|dǎ kāi|opened the window|open the window|g
空调|kōng tiáo|打开|dǎ kāi|turned on the air conditioner|turn on the air conditioner|g
灯|dēng|关掉|guān diào|turned off the light|turn off the light|g
电视|diàn shì|关掉|guān diào|turned off the TV|turn off the TV|g
手机|shǒu jī|修好|xiū hǎo|fixed the phone|fix the phone|g
自行车|zì xíng chē|修好|xiū hǎo|fixed the bicycle|fix the bicycle|g
电脑|diàn nǎo|修好|xiū hǎo|fixed the computer|fix the computer|g
蛋糕|dàn gāo|吃完|chī wán|finished the cake|finish the cake|g
牛奶|niú nǎi|喝完|hē wán|finished the milk|finish the milk|g
咖啡|kā fēi|喝完|hē wán|finished the coffee|finish the coffee|g
药|yào|吃完|chī wán|finished the medicine|finish the medicine|g
报告|bào gào|写完|xiě wán|finished the report|finish the report|g
那封信|nà fēng xìn|写完|xiě wán|finished that letter|finish that letter|g
晚饭|wǎn fàn|做好|zuò hǎo|got dinner ready|get dinner ready|g
行李|xíng li|准备好|zhǔn bèi hǎo|got the luggage ready|get the luggage ready|g
生词|shēng cí|记住|jì zhù|memorised the new words|memorise the new words|g
手机|shǒu jī|弄丢|nòng diū|lost the phone|lose the phone|b
钥匙|yào shi|弄丢|nòng diū|lost the keys|lose the keys|b
护照|hù zhào|弄丢|nòng diū|lost the passport|lose the passport|b
钱包|qián bāo|弄丢|nòng diū|lost the wallet|lose the wallet|b
杯子|bēi zi|打破|dǎ pò|broke the cup|break the cup|b
花瓶|huā píng|打碎|dǎ suì|smashed the vase|smash the vase|b
电脑|diàn nǎo|弄坏|nòng huài|broke the computer|break the computer|b
眼镜|yǎn jìng|弄坏|nòng huài|broke the glasses|break the glasses|b
衣服|yī fu|弄脏|nòng zāng|got the clothes dirty|get the clothes dirty|b
钱|qián|花完|huā wán|spent all the money|spend all the money|b
名字|míng zi|写错|xiě cuò|wrote the name wrong|write the name wrong|b
地址|dì zhǐ|写错|xiě cuò|wrote the address wrong|write the address wrong|b
时间|shí jiān|记错|jì cuò|got the time wrong|get the time wrong|b
`);

// object | py | verb + 在 | py | place | py | English past | English base | g / b
const BA_PLACE = rows(`
车|chē|停在|tíng zài|门口|mén kǒu|parked the car at the entrance|park the car at the entrance|g
自行车|zì xíng chē|停在|tíng zài|楼下|lóu xià|parked the bicycle downstairs|park the bicycle downstairs|g
书|shū|放在|fàng zài|桌子上|zhuō zi shàng|put the book on the table|put the book on the table|g
钥匙|yào shi|放在|fàng zài|桌子上|zhuō zi shàng|put the keys on the table|put the keys on the table|g
花|huā|放在|fàng zài|桌子上|zhuō zi shàng|put the flowers on the table|put the flowers on the table|g
牛奶|niú nǎi|放在|fàng zài|冰箱里|bīng xiāng lǐ|put the milk in the fridge|put the milk in the fridge|g
手机|shǒu jī|放在|fàng zài|包里|bāo lǐ|put the phone in the bag|put the phone in the bag|g
行李|xíng li|放在|fàng zài|房间里|fáng jiān lǐ|put the luggage in the room|put the luggage in the room|g
衣服|yī fu|挂在|guà zài|衣柜里|yī guì lǐ|hung the clothes in the wardrobe|hang the clothes in the wardrobe|g
照片|zhào piàn|挂在|guà zài|墙上|qiáng shàng|hung the photo on the wall|hang the photo on the wall|g
名字|míng zi|写在|xiě zài|本子上|běn zi shàng|wrote the name in the notebook|write the name in the notebook|g
地址|dì zhǐ|写在|xiě zài|纸上|zhǐ shàng|wrote the address on the paper|write the address on the paper|g
雨伞|yǔ sǎn|忘在|wàng zài|出租车上|chū zū chē shàng|left the umbrella in the taxi|leave the umbrella in the taxi|b
钱包|qián bāo|忘在|wàng zài|家里|jiā lǐ|left the wallet at home|leave the wallet at home|b
作业|zuò yè|忘在|wàng zài|家里|jiā lǐ|left the homework at home|leave the homework at home|b
`);

// modal | py | English with {S} and {v} = base verb phrase
const MODALS = rows(`
想|xiǎng|{S} [want] to {v}.
要|yào|{S} {is} going to {v}.
应该|yīng gāi|{S} should {v}.
得|děi|{S} {have} to {v}.
可以|kě yǐ|{S} can {v}.
打算|dǎ suàn|{S} [plan] to {v}.
必须|bì xū|{S} must {v}.
`);

const BA = '把|bǎ';
const BA_WHY = {
  plain: (o, v) =>
    `把 moves the definite object ${o} in front of the verb: doer + 把 + object + verb + what happened to it. The verb cannot be left bare, so ${v} keeps its result or place and 了 closes the sentence.`,
  neg: 'Negation goes before 把, not before the verb: 没把… + verb + result. Since it did not happen, there is no 了.',
  modal: (m) =>
    `Modal verbs such as ${m} stand before 把, not between the object and the verb: ${m} + 把 + object + verb + result.`,
  dont: '别 (don\'t) comes before 把, like every negative or modal: 别把 + object + verb + result.',
  please: '请 opens the request and 把 follows it: 请把 + object + verb + result. The object cannot stay behind the verb here.',
};

function makeBaOrder(rng) {
  const place = rng() < 0.28;
  const s = pick(rng, PEOPLE);
  let o;
  let opy;
  let tail;
  let past;
  let base;
  let type;
  let verb;
  if (place) {
    const [oo, oopy, v, vpy, p, ppy, enPast, enBase, t] = pick(rng, BA_PLACE);
    [o, opy, past, base, type, verb] = [oo, oopy, enPast, enBase, t, v];
    tail = [part(v, vpy), part(p, ppy)];
  } else {
    const [oo, oopy, v, vpy, enPast, enBase, t] = pick(rng, BA_RESULT);
    [o, opy, past, base, type, verb] = [oo, oopy, enPast, enBase, t, v];
    tail = [part(v, vpy)];
  }
  const obj = part(o, opy);
  const le = '了|le';
  const kind = weighted(rng, [
    [4, 'plain'],
    [3, 'neg'],
    [type === 'g' ? 4 : 0, 'modal'],
    [type === 'b' ? 2 : 0, 'dont'],
    [type === 'g' ? 1 : 0, 'please'],
  ]);
  const key = 'ba-order';
  if (kind === 'plain') {
    return order(rng, {
      key,
      tiles: [s, BA, obj, ...tail, le],
      en: `${s.en} ${past}.`,
      why: BA_WHY.plain(o, verb),
    });
  }
  if (kind === 'neg') {
    return order(rng, {
      key,
      tiles: [s, '没|méi', BA, obj, ...tail],
      en: `${s.en} didn't ${base}.`,
      why: BA_WHY.neg,
    });
  }
  if (kind === 'modal') {
    const [m, mpy, en] = pick(rng, MODALS);
    return order(rng, {
      key,
      tiles: [s, part(m, mpy), BA, obj, ...tail],
      en: fillEn(en, s).replace('{v}', base),
      why: BA_WHY.modal(m),
    });
  }
  if (kind === 'dont') {
    return order(rng, {
      key,
      tiles: ['别|bié', BA, obj, ...tail, ...(place ? [] : [le])],
      end: '！',
      en: `Don't ${base}!`,
      why: BA_WHY.dont,
    });
  }
  return order(rng, {
    key,
    tiles: ['请|qǐng', BA, obj, ...tail],
    en: `Please ${base}.`,
    why: BA_WHY.please,
  });
}

/* ---------- 被 ---------- */

// receiver | py | English | doers "zh:py:English;..." | verb + result | py | participle | active past | flags: P takes an owner, p plural
const BEI = rows(`
蛋糕|dàn gāo|cake|弟弟:dì di:my little brother;孩子们:hái zi men:the children|吃完|chī wán|eaten up|ate up|
牛奶|niú nǎi|milk|小猫:xiǎo māo:the kitten;妹妹:mèi mei:my little sister|喝完|hē wán|drunk up|drank up|
水果|shuǐ guǒ|fruit|大家:dà jiā:everyone;孩子们:hái zi men:the children|吃完|chī wán|eaten up|ate up|
饺子|jiǎo zi|dumplings|孩子们:hái zi men:the children;大家:dà jiā:everyone|吃完|chī wán|eaten up|ate up|p
啤酒|pí jiǔ|beer|朋友:péng you:a friend;大家:dà jiā:everyone|喝完|hē wán|drunk up|drank up|
鱼|yú|fish|猫:māo:the cat|吃掉|chī diào|eaten|ate|
手机|shǒu jī|phone|小偷:xiǎo tōu:a thief|偷走|tōu zǒu|stolen|stole|P
钱包|qián bāo|wallet|小偷:xiǎo tōu:a thief|偷走|tōu zǒu|stolen|stole|P
自行车|zì xíng chē|bicycle|小偷:xiǎo tōu:a thief|偷走|tōu zǒu|stolen|stole|P
自行车|zì xíng chē|bicycle|朋友:péng you:a friend;同学:tóng xué:a classmate|借走|jiè zǒu|borrowed|borrowed|P
词典|cí diǎn|dictionary|同学:tóng xué:a classmate;朋友:péng you:a friend|借走|jiè zǒu|borrowed|borrowed|P
书|shū|book|同学:tóng xué:a classmate;朋友:péng you:a friend|借走|jiè zǒu|borrowed|borrowed|P
杯子|bēi zi|cup|小猫:xiǎo māo:the kitten;孩子:hái zi:the child|打破|dǎ pò|broken|broke|P
花瓶|huā píng|vase|小猫:xiǎo māo:the kitten;小狗:xiǎo gǒu:the puppy|打碎|dǎ suì|smashed|smashed|P
电脑|diàn nǎo|computer|弟弟:dì di:my little brother;孩子:hái zi:the child|弄坏|nòng huài|broken|broke|P
眼镜|yǎn jìng|glasses|孩子:hái zi:the child;弟弟:dì di:my little brother|弄坏|nòng huài|broken|broke|Pp
衣服|yī fu|clothes|雨:yǔ:the rain|淋湿|lín shī|soaked|soaked|Pp
帽子|mào zi|hat|风:fēng:the wind|吹走|chuī zǒu|blown away|blew away|P
雨伞|yǔ sǎn|umbrella|风:fēng:the wind|吹坏|chuī huài|wrecked|wrecked|P
雨伞|yǔ sǎn|umbrella|别人:bié rén:someone else|拿走|ná zǒu|taken|took|P
照相机|zhào xiàng jī|camera|哥哥:gē ge:my older brother;朋友:péng you:a friend|拿走|ná zǒu|taken|took|P
房间|fáng jiān|room|孩子们:hái zi men:the children|弄乱|nòng luàn|messed up|messed up|P
车|chē|car|朋友:péng you:a friend|开走|kāi zǒu|driven off|drove off|P
作业|zuò yè|homework|小狗:xiǎo gǒu:the puppy|咬坏|yǎo huài|chewed up|chewed up|P
鞋|xié|shoes|小狗:xiǎo gǒu:the puppy|咬坏|yǎo huài|chewed up|chewed up|Pp
窗户|chuāng hu|window|风:fēng:the wind|吹开|chuī kāi|blown open|blew open|
窗户|chuāng hu|window|孩子们:hái zi men:the children|打破|dǎ pò|broken|broke|
门|mén|door|风:fēng:the wind|吹开|chuī kāi|blown open|blew open|
树|shù|tree|风:fēng:the wind|吹倒|chuī dǎo|blown down|blew down|
`).map(([zh, py, en, doers, v, vpy, pp, act, flags]) => ({
  zh,
  py,
  en,
  doers: doers.split(';').map((d) => d.split(':')),
  v,
  vpy,
  pp,
  act,
  owned: flags.includes('P'),
  plural: flags.includes('p'),
}));

const OWNERS = rows(`
我的|wǒ de|my
他的|tā de|his
她的|tā de|her
小王的|xiǎo wáng de|Xiao Wang's
老师的|lǎo shī de|the teacher's
我妈妈的|wǒ mā ma de|my mom's
`);
const WHEN = rows(`
昨天|zuó tiān|yesterday
刚才|gāng cái|just now
上个星期|shàng ge xīng qī|last week
今天早上|jīn tiān zǎo shang|this morning
昨天晚上|zuó tiān wǎn shang|last night
前天|qián tiān|the day before yesterday
`);

/** Receiver tile and its English, with an owner where the noun takes one. */
function receiver(rng, t) {
  if (!t.owned) return { tile: part(t.zh, t.py), en: `the ${t.en}` };
  const [o, opy, oen] = pick(rng, OWNERS);
  return { tile: part(o + t.zh, `${opy} ${t.py}`), en: `${oen} ${t.en}` };
}

const BEI_T = '被|bèi';

function makeBeiOrder(rng) {
  const t = pick(rng, BEI);
  const [d, dpy, den] = pick(rng, t.doers);
  const r = receiver(rng, t);
  const R = cap(r.en);
  const be = t.plural ? 'were' : 'was';
  const doer = part(d, dpy);
  const v = part(t.v, t.vpy);
  const le = '了|le';
  const key = 'bei-order';
  const kind = weighted(rng, [
    [5, 'plain'],
    [2, 'agentless'],
    [2, 'neg'],
    [1, 'wont'],
    [1, 'maybe'],
    [1, 'nearly'],
    [1, 'already'],
    [1, 'again'],
  ]);
  const basic = `The one affected comes first, then 被 + the doer, then the verb with its result: ${r.tile.zh} + 被 + ${d} + ${t.v}. The verb needs its result or 了; it cannot end bare.`;
  if (kind === 'plain') {
    if (rng() < 0.6) {
      const [w, wpy, wen] = pick(rng, WHEN);
      return order(rng, {
        key,
        tiles: [part(w, wpy), r.tile, BEI_T, doer, v, le],
        alts: [[1, 0, 2, 3, 4, 5]],
        en: `${R} ${be} ${t.pp} by ${den} ${wen}.`,
        why: `${basic} The time word ${w} goes before 被, either before or after the receiver.`,
      });
    }
    return order(rng, {
      key,
      tiles: [r.tile, BEI_T, doer, v, le],
      en: `${R} ${be} ${t.pp} by ${den}.`,
      why: basic,
    });
  }
  if (kind === 'agentless') {
    return order(rng, {
      key,
      tiles: [r.tile, BEI_T, v, le],
      en: `${R} ${be} ${t.pp}.`,
      why: `With 被 the doer may be left out: receiver + 被 + verb + result + 了. 被 still comes directly before the verb, and ${t.v} keeps its result.`,
    });
  }
  if (kind === 'neg') {
    return order(rng, {
      key,
      tiles: [r.tile, '没|méi', BEI_T, doer, v],
      en: `${R} ${be} not ${t.pp} by ${den}.`,
      why: 'Negation goes before 被, not before the verb: 没被 + doer + verb + result. With 没 there is no 了.',
    });
  }
  if (kind === 'wont') {
    return order(rng, {
      key,
      tiles: [r.tile, '不会|bù huì', BEI_T, doer, v],
      en: `${R} won't be ${t.pp} by ${den}.`,
      why: 'Modal verbs go before 被: 不会被 + doer + verb + result. Nothing can come between the doer and the verb.',
    });
  }
  if (kind === 'maybe') {
    return order(rng, {
      key,
      tiles: [r.tile, '可能|kě néng', BEI_T, doer, v, le],
      alts: [[1, 0, 2, 3, 4, 5]],
      en: `${R} may have been ${t.pp} by ${den}.`,
      why: '可能 goes before 被 (or opens the sentence), never between 被 and the verb: 可能被 + doer + verb + result + 了.',
    });
  }
  const [adv, advpy, en] = {
    nearly: ['差点儿', 'chà diǎn r', `${R} ${be} nearly ${t.pp} by ${den}.`],
    already: ['已经', 'yǐ jīng', `${R} ${t.plural ? 'have' : 'has'} already been ${t.pp} by ${den}.`],
    again: ['又', 'yòu', `${R} ${be} ${t.pp} by ${den} again.`],
  }[kind];
  return order(rng, {
    key,
    tiles: [r.tile, part(adv, advpy), BEI_T, doer, v, le],
    en,
    why: `Adverbs such as ${adv} stand before 被, not before the verb: ${adv}被 + doer + verb + result + 了.`,
  });
}

/* ---------- 把 or 被 ---------- */

function makeBaOrBei(key) {
  return (rng) => {
    const t = pick(rng, BEI);
    const [d, dpy, den] = pick(rng, t.doers);
    const r = receiver(rng, t);
    const doer = part(d, dpy);
    const tail = [part(t.v, t.vpy), '了|le', '。'];
    const ba = rng() < 0.5;
    if (ba) {
      return cloze(rng, {
        key,
        max: 1,
        pre: [doer],
        post: [r.tile, ...tail],
        right: BA,
        wrong: ['被'],
        en: `${cap(den)} ${t.act} ${r.en}.`,
        why: `${d} is the doer and comes first, and ${r.tile.zh} is what gets handled, so the object is marked with 把. With 被 the sentence would say that ${d} was ${t.pp}.`,
      });
    }
    return cloze(rng, {
      key,
      max: 1,
      pre: [r.tile],
      post: [doer, ...tail],
      right: BEI_T,
      wrong: ['把'],
      en: `${cap(r.en)} ${t.plural ? 'were' : 'was'} ${t.pp} by ${den}.`,
      why: `${r.tile.zh} comes first but is the thing affected, and ${d} is the doer, so the doer is introduced by 被. 把 would make ${r.tile.zh} the one acting on ${d}.`,
    });
  };
}

export const baGenerators = [
  { key: 'ba-order', label: '把 sentence order', make: makeBaOrder },
  { key: 'ba-or-bei', label: '把 or 被', make: makeBaOrBei('ba-or-bei') },
];
export const beiGenerators = [
  { key: 'bei-order', label: '被 sentence order', make: makeBeiOrder },
  { key: 'bei-or-ba', label: '被 or 把', make: makeBaOrBei('bei-or-ba') },
];

