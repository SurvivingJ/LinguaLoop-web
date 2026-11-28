// static/js/idioms/questions.js
// Builds one question for an idiom card at a step of its ladder.
// Pure functions: the page (js/pages/idiom-trainer.js) owns the DOM.
//
// A question: { mode, card, prompt, options[], answer (index), after }
//   prompt.sentence   a context with the idiom in braces (shown, or blanked)
//   prompt.blank      true when the idiom is hidden in the sentence
//   prompt.en         the translation, where it is shown before answering
//   prompt.text       a line of English (the meaning, or the cue)
//   prompt.stem       the first half of the idiom (complete)
//   after             { en, why }: shown with the feedback

export function shuffle(list, rng = Math.random) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const pick = (list, rng) => list[Math.floor(rng() * list.length)];

/**
 * Other idioms to offer beside `card`: the same set first, never a listed
 * near-synonym, never the same theme (two idioms of one theme can fit one
 * situation), and never one whose `key` text equals the card's.
 */
export function distractors(card, pool, n, rng = Math.random, key = 't') {
  const near = new Set((card.near || []).map((x) => x.t));
  const ok = (o) =>
    o.id !== card.id && !near.has(o.t) && o.tag !== card.tag && o[key] !== card[key];
  const same = shuffle(
    pool.filter((o) => ok(o) && o.set === card.set),
    rng
  );
  const other = shuffle(
    pool.filter((o) => ok(o) && o.set !== card.set),
    rng
  );
  const out = [];
  const seen = new Set([card[key]]);
  for (const o of [...same, ...other]) {
    if (out.length >= n) break;
    if (seen.has(o[key])) continue;
    seen.add(o[key]);
    out.push(o);
  }
  // A small pool (a set being built): relax the theme rule rather than offer too few.
  if (out.length < n) {
    for (const o of shuffle(pool, rng)) {
      if (out.length >= n) break;
      if (o.id === card.id || near.has(o.t) || seen.has(o[key])) continue;
      seen.add(o[key]);
      out.push(o);
    }
  }
  return out;
}

function choice(right, wrongs, rng) {
  const options = shuffle([right, ...wrongs], rng);
  return { options, answer: options.indexOf(right) };
}

/** The second halves that can be offered beside this card's: other idioms' second halves. */
function halves(card, pool, n, rng) {
  const out = [];
  const seen = new Set([card.parts[1]]);
  for (const o of shuffle(
    pool.filter((x) => x.id !== card.id && x.parts && x.set === card.set),
    rng
  )) {
    if (out.length >= n) break;
    // a half that would also complete this stem into a real idiom is not offered
    if (seen.has(o.parts[1]) || pool.some((x) => x.t === card.parts[0] + o.parts[1])) continue;
    seen.add(o.parts[1]);
    out.push(o.parts[1]);
  }
  return out;
}

/**
 * `pool` is every card that may serve as a distractor (cards loaded so far);
 * `seen` lists context indexes this idiom was recently shown in, so the next
 * one is new where possible.
 */
export function build(card, mode, pool, rng = Math.random, seen = []) {
  const fresh = (from, to) => {
    const all = [];
    for (let i = from; i < to && i < card.ctx.length; i++) all.push(i);
    const unseen = all.filter((i) => !seen.includes(i));
    return pick(unseen.length ? unseen : all, rng);
  };
  const base = { mode, card };
  if (mode === 'meet') {
    const at = fresh(0, 2);
    const c = card.ctx[at];
    const wrong = distractors(card, pool, 3, rng, 'mean').map((o) => o.mean);
    return {
      ...base,
      ctx: at,
      prompt: { sentence: c.s, blank: false },
      ...choice(card.mean, wrong, rng),
      after: { en: c.en },
    };
  }
  if (mode === 'recognise' || mode === 'review') {
    const at = fresh(1, 6);
    const c = card.ctx[at];
    const wrong = distractors(card, pool, 3, rng).map((o) => o.t);
    return {
      ...base,
      ctx: at,
      prompt: { sentence: c.s, blank: true, en: c.en },
      ...choice(card.t, wrong, rng),
      after: { en: c.en },
    };
  }
  if (mode === 'complete') {
    const wrong = halves(card, pool, 3, rng);
    return {
      ...base,
      prompt: { text: card.mean, stem: card.parts[0] },
      ...choice(card.parts[1], wrong, rng),
      after: { en: card.lit },
    };
  }
  if (mode === 'judge') {
    const good = rng() < 0.5;
    if (good) {
      const at = fresh(2, 6);
      const c = card.ctx[at];
      return {
        ...base,
        ctx: at,
        judge: true,
        prompt: { sentence: c.s, blank: false },
        options: ['right', 'wrong'],
        answer: 0,
        after: { en: c.en },
      };
    }
    const b = pick(card.bad, rng);
    return {
      ...base,
      judge: true,
      prompt: { sentence: b.s, blank: false },
      options: ['right', 'wrong'],
      answer: 1,
      after: { en: b.en, why: b.why },
    };
  }
  // recall: the situation in English only, six idioms to choose from
  const wrong = distractors(card, pool, 5, rng).map((o) => o.t);
  return {
    ...base,
    prompt: { text: card.cue },
    ...choice(card.t, wrong, rng),
    after: { en: card.mean },
  };
}
