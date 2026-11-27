// static/js/grammar/round.js
// Grammar drills: the queue of one round. No DOM.
//
// A missed item goes back into the queue a few items later and keeps coming
// back until it is answered right, so a round ends only when every item has
// been answered right once. Scores count the FIRST answer to each item.
// With `more` (endless mode) the queue never runs dry.

import { median } from './text.js';

/** Items between a miss and the item's return. */
export const RETRY_GAP = 3;

/**
 * `entries` is a list of anything (the caller's { slug, item } records).
 * `more()` returns the next entry of an endless stream.
 */
export function createRound(entries, { gap = RETRY_GAP, more = null } = {}) {
  const queue = (entries || []).map((entry) => ({ entry, retry: false }));
  const first = []; // { entry, ok, ms } per first answer
  let pos = 0;
  let streak = 0;
  let best = 0;
  let answered = false;

  function fill() {
    if (more && pos >= queue.length) {
      const entry = more();
      if (entry) queue.push({ entry, retry: false });
    }
  }
  fill();

  return {
    /** { entry, retry } now on screen, or null when the round is over. */
    current() {
      return pos < queue.length ? queue[pos] : null;
    },

    /**
     * Answer the current item. Returns { first } (true when this was the
     * item's first answer, the one that counts).
     */
    answer(ok, ms) {
      const cur = queue[pos];
      if (!cur || answered) return { first: false };
      answered = true;
      if (!cur.retry) first.push({ entry: cur.entry, ok: !!ok, ms });
      streak = ok ? streak + 1 : 0;
      best = Math.max(best, streak);
      if (!ok) {
        const at = Math.min(queue.length, pos + 1 + gap);
        queue.splice(at, 0, { entry: cur.entry, retry: true });
      }
      return { first: !cur.retry };
    },

    /** Move on after an answer. Returns the next current(), or null. */
    next() {
      if (answered) {
        pos += 1;
        answered = false;
        fill();
      }
      return this.current();
    },

    isAnswered: () => answered,
    isEndless: () => !!more,
    streak: () => streak,

    /** Progress through the round: items answered right so far, of `total`. */
    progress() {
      const total = new Set(queue.map((q) => q.entry)).size;
      const pending = new Set(queue.slice(pos + (answered ? 1 : 0)).map((q) => q.entry)).size;
      return { done: total - pending, total };
    },

    /** Scores over first answers. */
    summary() {
      const correct = first.filter((f) => f.ok).length;
      return {
        answers: first.length,
        correct,
        accuracy: first.length ? correct / first.length : 0,
        medianMs: median(first.map((f) => f.ms)),
        missed: first.filter((f) => !f.ok).map((f) => f.entry),
        best,
      };
    },
  };
}
