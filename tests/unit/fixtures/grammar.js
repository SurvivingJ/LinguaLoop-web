// Items from data/grammar_drills/zh/SPEC.md plus a few of the same shape, for
// the grammar-drill unit tests.
export const CLOZE = {
  id: 'le-01-001',
  type: 'cloze',
  sub: 'completed-quantified',
  lvl: 1,
  q: '我昨天买___三本书。',
  opts: ['了', '过', '着', '的'],
  a: 0,
  zh: '我昨天买了三本书。',
  py: 'wǒ zuó tiān mǎi le sān běn shū',
  en: 'I bought three books yesterday.',
  why: 'A finished action with a counted object takes 了 right after the verb.',
};

export const CLOZE_NONE = {
  id: 'le-01-002',
  type: 'cloze',
  sub: 'no-le',
  lvl: 1,
  q: '我每天喝___咖啡。',
  opts: ['了', '∅'],
  a: 1,
  zh: '我每天喝咖啡。',
  py: 'wǒ měi tiān hē kā fēi',
  en: 'I drink coffee every day.',
  why: 'A habit takes no 了.',
};

export const CLOZE_PAIR = {
  id: 'connectors-01-003',
  type: 'cloze',
  sub: 'cause',
  lvl: 2,
  q: '___下雨，___我们没去。',
  opts: ['因为|所以', '虽然|但是'],
  a: 0,
  zh: '因为下雨，所以我们没去。',
  py: 'yīn wèi xià yǔ suǒ yǐ wǒ men méi qù',
  en: "Because it rained, we didn't go.",
  why: 'Cause and result pair as 因为…所以.',
};

export const ORDER = {
  id: 'word-order-01-020',
  type: 'order',
  sub: 'time-place',
  lvl: 1,
  tokens: ['我', '明天', '在家', '看', '电影'],
  alts: [['明天', '我', '在家', '看', '电影']],
  extra: ['了'],
  zh: '我明天在家看电影。',
  py: 'wǒ míng tiān zài jiā kàn diàn yǐng',
  en: "I'm watching a film at home tomorrow.",
  why: 'Time, then place, then the verb.',
};

export const REWRITE = {
  id: 'ba-02-061',
  type: 'rewrite',
  sub: 'ba-result',
  lvl: 2,
  src: '我喝完了那杯咖啡。',
  src_py: 'wǒ hē wán le nà bēi kā fēi',
  task: 'Rewrite with 把.',
  tokens: ['我', '把', '那杯咖啡', '喝完', '了'],
  zh: '我把那杯咖啡喝完了。',
  py: 'wǒ bǎ nà bēi kā fēi hē wán le',
  en: 'I finished that cup of coffee.',
  why: '把 moves the definite object in front of the verb.',
};

export const JUDGE_BAD = {
  id: 'bu-mei-01-090',
  type: 'judge',
  sub: 'mei-you',
  lvl: 1,
  s: '我不有哥哥。',
  s_py: 'wǒ bù yǒu gē ge',
  ok: false,
  zh: '我没有哥哥。',
  py: 'wǒ méi yǒu gē ge',
  en: "I don't have an older brother.",
  why: '有 is only ever negated with 没.',
};

export const JUDGE_OK = {
  id: 'bu-mei-01-091',
  type: 'judge',
  sub: 'mei-you',
  lvl: 1,
  s: '我没有哥哥。',
  ok: true,
  zh: '我没有哥哥。',
  py: 'wǒ méi yǒu gē ge',
  en: "I don't have an older brother.",
  why: '没有 is right.',
};

/** `n` items of a topic: ids <slug>-01-001…, types cycling, three sub-points. */
export function makeItems(slug, n, types = ['cloze', 'judge', 'order', 'rewrite']) {
  const answers = ['了', '过', '着'];
  return Array.from({ length: n }, (_, k) => {
    const type = types[k % types.length];
    const base = {
      id: `${slug}-01-${String(k + 1).padStart(3, '0')}`,
      type,
      sub: ['a', 'b', 'c'][k % 3],
      lvl: (k % 3) + 1,
      zh: '我买了书。',
      py: 'wǒ mǎi le shū',
      en: `Sentence ${k + 1}.`,
      why: 'Because.',
    };
    if (type === 'cloze') {
      const right = answers[k % answers.length];
      return { ...base, q: '我买___书。', opts: [right, '的'], a: 0, zh: `我买${right}书。` };
    }
    if (type === 'judge') return { ...base, s: '我买了书。', ok: true };
    const tokens = ['我', '买了', '书'];
    return type === 'rewrite'
      ? {
          ...base,
          tokens,
          src: '书我买了。',
          src_py: 'shū wǒ mǎi le',
          task: 'Put the subject first.',
        }
      : { ...base, tokens };
  });
}

/** Deterministic rng (mulberry32). */
export function seeded(seed = 1) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** In-memory Storage. */
export function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => {
      data[k] = String(v);
    },
  };
}
