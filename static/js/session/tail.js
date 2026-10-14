// static/js/session/tail.js
// Pure helpers for the optional end-of-session tail (session-budget-settings,
// TASK-867 frontend). The required session is the server's `queue`; once every
// required item is done, GET /api/study-session may also return
//
//   tail:       null | { reviews_left_items, reviews_left_minutes,
//                        new_words_left, new_words_left_minutes }
//   tail_queue: [ { kind:'practice', id:'tail_maint_1'|'tail_acq_1', mode, minutes,
//                   is_bonus:true, is_tail:true, is_completed:false } ]
//   governor:   { level, overdue_items, ... }
//
// Tail items are NEVER part of the required queue, so they must not count toward
// session completion. Kept DOM-free so it can be unit-tested.

/** Counts the prompt talks about: { reviews, words }. */
export function tailCounts(tail) {
  if (!tail) return { reviews: 0, words: 0 };
  return {
    reviews: Math.max(0, Number(tail.reviews_left_items) || 0),
    words: Math.max(0, Number(tail.new_words_left) || 0),
  };
}

/** True when there is something to offer AND something runnable to offer it with. */
export function hasTail(data) {
  if (!data || !data.tail) return false;
  const { reviews, words } = tailCounts(data.tail);
  if (reviews + words === 0) return false;
  return Array.isArray(data.tail_queue) && data.tail_queue.length > 0;
}

/** i18n key of the "Session done — … Keep going?" prompt, or null with nothing left. */
export function tailPromptKey(tail) {
  const { reviews, words } = tailCounts(tail);
  if (reviews > 0 && words > 0) return 'session.tail.prompt';
  if (reviews > 0) return 'session.tail.prompt_reviews_only';
  if (words > 0) return 'session.tail.prompt_words_only';
  return null;
}

/** Governor banner key ('session.governor.paused' | '.reduced') or null when normal. */
export function governorKey(governor) {
  const level = governor && governor.level;
  if (level === 'paused') return 'session.governor.paused';
  if (level === 'reduced') return 'session.governor.reduced';
  return null;
}

/** Key of the "{n} reviews" / "{n} new words" phrase, singular when n is 1. */
export function countKey(kind, n) {
  return `session.tail.${kind}_count${Number(n) === 1 ? '_one' : ''}`;
}

/** Normalise server tail items for the runner: always practice, optional, not yet done. */
export function normalizeTailItems(tailQueue) {
  return (tailQueue || []).map((item) => ({
    ...item,
    kind: item.kind || 'practice',
    is_bonus: true,
    is_tail: true,
    is_completed: false,
  }));
}

/**
 * Put a fresh tail round into the queue. Tail items left over from an earlier
 * round that were skipped (still incomplete) are replaced rather than duplicated;
 * completed ones stay (they are history). Returns { queue, firstIndex }.
 */
export function appendTailRound(queue, tailQueue) {
  const kept = (queue || []).filter((q) => !(q.is_tail && !q.is_completed));
  const fresh = normalizeTailItems(tailQueue);
  return { queue: kept.concat(fresh), firstIndex: kept.length };
}

/** Completion over the REQUIRED items only (tail and speed-round bonus never block it). */
export function requiredProgress(queue) {
  const required = (queue || []).filter((q) => !q.is_tail);
  return {
    done: required.filter((q) => q.is_completed).length,
    total: required.length,
  };
}
