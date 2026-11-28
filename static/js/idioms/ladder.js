// static/js/idioms/ladder.js
// The ladder of one idiom. Five steps, each asked in a context the learner has
// not just seen, then spaced reviews:
//   1 meet       read it in context, choose what it means there
//   2 recognise  a new situation: which idiom fits?
//   3 complete   the meaning and the first half: choose the second half
//   4 judge      a sentence that uses it: right or wrong here?
//   5 recall     a situation in English only: which idiom?
//   6 mastered   reviews after 1, 3, 7, 14, 30, 60, 120 days (recognise, against the clock)
// Two right answers in a row move an idiom up a step. A wrong answer keeps it
// where it is; a wrong answer in a review sends it back to step 4.
// Pure functions: the page (js/pages/idiom-trainer.js) owns the DOM.

export const STEPS = 5;
export const MASTERED = 6;
export const REVIEW_DAYS = [1, 3, 7, 14, 30, 60, 120];
export const MODES = ['meet', 'recognise', 'complete', 'judge', 'recall', 'review'];
const DAY = 86400000;

export function newState() {
  return { l: 1, k: 0, n: 0, c: 0, last: null, due: null, iv: 0, hi: 1 };
}

export const isStarted = (s) => !!s && s.n > 0;
export const isMastered = (s) => !!s && s.l >= MASTERED;
export const isDue = (s, now = Date.now()) => isMastered(s) && s.due != null && s.due <= now;
export const modeFor = (level) => MODES[Math.min(Math.max(level, 1), MASTERED) - 1];

/**
 * Record one answer. Returns { state, event }; event is 'up', 'mastered',
 * 'kept' (a review passed), 'down' (a review failed) or null.
 */
export function record(prev, correct, now = Date.now()) {
  const s = { ...newState(), ...prev };
  let event = null;
  s.n += 1;
  if (correct) s.c += 1;
  s.last = now;
  if (s.l >= MASTERED) {
    if (correct) {
      s.iv = Math.min(s.iv + 1, REVIEW_DAYS.length - 1);
      s.due = now + REVIEW_DAYS[s.iv] * DAY;
      event = 'kept';
    } else {
      s.l = 4;
      s.k = 0;
      s.iv = 0;
      s.due = null;
      event = 'down';
    }
  } else if (correct) {
    s.k += 1;
    if (s.k >= 2) {
      s.l += 1;
      s.k = 0;
      event = 'up';
      if (s.l >= MASTERED) {
        s.l = MASTERED;
        s.iv = 0;
        s.due = now + REVIEW_DAYS[0] * DAY;
        event = 'mastered';
      }
    }
  } else {
    s.k = 0;
  }
  s.hi = Math.max(s.hi || 1, s.l);
  return { state: s, event };
}

/**
 * The idioms of one round, as a queue of ids. Due reviews come first (once
 * each), then the idioms being learned (oldest answer first), then new ones in
 * list order until `active` idioms are in play. Every idiom being learned is
 * asked twice, never back to back, because a step needs two right answers.
 */
export function planRound(
  idioms,
  states,
  { now = Date.now(), size = 12, active = 5, sets = null } = {}
) {
  const pool = sets ? idioms.filter((i) => sets.includes(i.set)) : idioms;
  const st = (i) => states[i.id];
  const due = pool.filter((i) => isDue(st(i), now)).sort((a, b) => st(a).due - st(b).due);
  const learning = pool
    .filter((i) => isStarted(st(i)) && !isMastered(st(i)))
    .sort((a, b) => (st(a).last || 0) - (st(b).last || 0));
  // New idioms by their place in their own set's list, so every chosen set
  // contributes its most useful ones first.
  const fresh = pool
    .filter((i) => !isStarted(st(i)))
    .map((i, at) => ({ i, at }))
    .sort((a, b) => (a.i.rank ?? a.at) - (b.i.rank ?? b.at) || a.at - b.at)
    .map((x) => x.i);
  const reviews = due.slice(0, Math.floor(size / 2)).map((i) => i.id);
  const slots = Math.max(1, Math.floor((size - reviews.length) / 2));
  const inPlay = learning.slice(0, Math.min(active, slots));
  for (const i of fresh) {
    if (inPlay.length >= Math.min(active, slots)) break;
    inPlay.push(i);
  }
  const ids = inPlay.map((i) => i.id);
  // first pass, reviews, second pass rotated so no idiom follows itself
  const second = ids.length > 1 ? [...ids.slice(1), ids[0]] : ids;
  const queue = [...ids, ...reviews, ...second];
  for (let i = 1; i < queue.length; i++) {
    if (queue[i] === queue[i - 1] && i + 1 < queue.length)
      [queue[i], queue[i + 1]] = [queue[i + 1], queue[i]];
  }
  return queue;
}

/** Counts for the hub. */
export function summary(idioms, states, now = Date.now()) {
  let learning = 0;
  let mastered = 0;
  let due = 0;
  for (const i of idioms) {
    const s = states[i.id];
    if (!isStarted(s)) continue;
    if (isMastered(s)) {
      mastered += 1;
      if (isDue(s, now)) due += 1;
    } else learning += 1;
  }
  return { learning, mastered, due, fresh: idioms.length - learning - mastered };
}

/** Merge two stored documents: per idiom, more answers wins; a tie goes to the later one. */
export function mergeStates(a, b) {
  const out = {};
  for (const id of new Set([...Object.keys(a || {}), ...Object.keys(b || {})])) {
    const p = a && a[id];
    const q = b && b[id];
    if (!p || !q) out[id] = p || q;
    else if ((p.n || 0) !== (q.n || 0)) out[id] = (p.n || 0) > (q.n || 0) ? p : q;
    else out[id] = (p.last || 0) >= (q.last || 0) ? p : q;
  }
  return out;
}
