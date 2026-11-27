// static/js/particles/mastery.js
// The particle ladder: one small state per skill, moved by every answer.
//
//   level 1 Meet     choose, translation and furigana shown
//   level 2 Choose   choose, translation hidden until answered
//   level 3 Type     type the particle
//   level 4 Fill     every particle in the sentence blank
//   level 5 Fix      find the wrong particle and correct it
//   level 6 Speed    choose against the clock
//   level 7 Instant  mastered: comes back for spaced speed reviews
//
// Promotion mirrors the measure-word drill: at least PROMOTE_MIN answers at
// the current level with a running accuracy (EWMA) of PROMOTE_AT or better.
// Leaving Speed also needs a running answer time of SPEED_RT_MS or less.

export const MAX_LEVEL = 6;
export const MASTERED = 7;
export const LEVEL_KEYS = ['', 'meet', 'choose', 'type', 'fill', 'fix', 'speed', 'instant'];
export const ALPHA = 0.3;
export const PROMOTE_MIN = 5;
export const PROMOTE_AT = 0.8;
export const SPEED_MIN = 8; // answers needed at the Speed level
export const SPEED_AT = 0.85;
export const SPEED_RT_MS = 4000; // running answer time needed to leave Speed
export const DEMOTE_MIN = 4;
export const DEMOTE_AT = 0.45;
export const REVIEW_DAYS = [1, 3, 7, 14, 30, 60, 120];
export const REVIEW_ANSWERS = 3; // right answers that settle a due review
export const SPEED_LIMIT_MS = 6000;
export const MISSED_MAX = 20;
const DAY = 86400000;

export function newState() {
  return { l: 1, la: 0, e: null, n: 0, c: 0, rt: null, due: null, iv: 0, last: null, miss: [] };
}

const ewma = (prev, x) => (prev == null ? x : prev + ALPHA * (x - prev));

/**
 * Apply one answer. `answer` is {correct, ms, level, itemId, counts}; `level`
 * is the level the exercise was drawn at and `counts` is false for answers
 * given in a manually chosen mode (they update the statistics but never move
 * the ladder). Returns {state, event} with event one of
 * 'promoted' | 'demoted' | 'mastered' | 'reviewed' | null. Does not mutate.
 */
export function record(prev, answer, now = Date.now(), maxLevel = MAX_LEVEL) {
  const mastered = maxLevel + 1;
  const s = { ...newState(), ...prev, miss: [...((prev && prev.miss) || [])] };
  const correct = !!answer.correct;
  s.n += 1;
  if (correct) s.c += 1;
  s.e = ewma(s.e, correct ? 1 : 0);
  if (correct && Number.isFinite(answer.ms)) s.rt = Math.round(ewma(s.rt, answer.ms));
  s.last = now;
  if (answer.itemId) {
    s.miss = s.miss.filter((id) => id !== answer.itemId);
    if (!correct) s.miss = [answer.itemId, ...s.miss].slice(0, MISSED_MAX);
  }
  let event = null;
  if (answer.counts === false) return { state: s, event };

  if (s.l >= mastered) {
    // Spaced reviews of a mastered skill.
    if (!correct && s.e < 0.6) {
      s.l = Math.max(1, maxLevel - 1);
      s.la = 0;
      s.due = null;
      s.iv = 0;
      event = 'demoted';
    } else if (correct && s.due != null && now >= s.due) {
      s.la += 1;
      if (s.la >= REVIEW_ANSWERS) {
        s.iv = Math.min(s.iv + 1, REVIEW_DAYS.length - 1);
        s.due = now + REVIEW_DAYS[s.iv] * DAY;
        s.la = 0;
        event = 'reviewed';
      }
    }
    return { state: s, event };
  }

  if (answer.level !== s.l) return { state: s, event };
  s.la += 1;
  const need = s.l === maxLevel ? SPEED_MIN : PROMOTE_MIN;
  const bar = s.l === maxLevel ? SPEED_AT : PROMOTE_AT;
  // Speed is only passed fast: accuracy alone does not make a skill instant.
  const fast = s.l !== maxLevel || (s.rt != null && s.rt <= SPEED_RT_MS);
  if (correct && s.la >= need && s.e >= bar && fast) {
    s.l += 1;
    s.la = 0;
    if (s.l >= mastered) {
      s.iv = 0;
      s.due = now + REVIEW_DAYS[0] * DAY;
      event = 'mastered';
    } else {
      event = 'promoted';
    }
  } else if (!correct && s.la >= DEMOTE_MIN && s.e < DEMOTE_AT && s.l > 1) {
    s.l -= 1;
    s.la = 0;
    s.e = 0.6; // a fresh start one rung down, not a free fall
    event = 'demoted';
  }
  return { state: s, event };
}

export const isStarted = (s) => !!s && s.n > 0;
export const isMastered = (s, maxLevel = MAX_LEVEL) => !!s && s.l > maxLevel;
export const isDue = (s, now = Date.now(), maxLevel = MAX_LEVEL) =>
  isMastered(s, maxLevel) && s.due != null && now >= s.due;

/** 0..1 progress of a skill up the ladder (for the hub's bars). */
export function progress(s, maxLevel = MAX_LEVEL) {
  if (!s || !s.n) return 0;
  if (s.l > maxLevel) return 1;
  const need = s.l === maxLevel ? SPEED_MIN : PROMOTE_MIN;
  return Math.min(1, (s.l - 1 + Math.min(s.la, need) / need) / maxLevel);
}

/**
 * The exercise mode for a ladder level, lowered to what the item supports:
 * Fill needs a second slot, Fix and the choose modes need a wrong answer.
 */
export function modeFor(level, item) {
  const slots = item.slotCount || 1;
  const hasWrong = (item.d || []).length > 0;
  if (level <= 1) return hasWrong ? 'meet' : 'type';
  if (level === 2) return hasWrong ? 'choose' : 'type';
  if (level === 3) return 'type';
  if (level === 4) return slots >= 2 ? 'fill' : 'type';
  if (level === 5) return hasWrong ? 'fix' : 'type';
  return hasWrong ? 'speed' : 'type';
}

/**
 * Skills for a mixed session, most urgent first: due reviews, then skills in
 * progress (weakest first), then up to `fresh` skills not started yet in
 * catalog order. `skills` is the catalog list; `states` maps id -> state.
 */
export function planMix(skills, states, { now = Date.now(), size = 6, fresh = 1 } = {}) {
  const usable = skills.filter((k) => (k.items || 0) + (k.packs || 0) > 0);
  const due = usable.filter((k) => isDue(states[k.id], now));
  const active = usable
    .filter((k) => isStarted(states[k.id]) && !isMastered(states[k.id]))
    .sort(
      (a, b) =>
        (states[a.id].e ?? 0) - (states[b.id].e ?? 0) || states[a.id].last - states[b.id].last
    );
  const unseen = usable.filter((k) => !isStarted(states[k.id])).slice(0, fresh);
  const picked = [];
  for (const k of [...due, ...active, ...unseen]) {
    if (picked.length >= size) break;
    if (!picked.includes(k)) picked.push(k);
  }
  if (!picked.length) picked.push(...usable.slice(0, Math.min(size, usable.length)));
  return picked;
}

/**
 * Skills to interleave with a one-skill drill, so the answer is not the same
 * particle every time. Candidates are skills of a different particle that the
 * learner has started, plus (to have a contrast from the first rounds) the
 * focus skill's listed confusers that come earlier in the catalog. Confusers
 * first, then started skills, due ones, and the nearest in catalog order; one
 * skill per particle before a particle repeats.
 */
export function pickCompanions(skills, states, focusId, { now = Date.now(), size = 5 } = {}) {
  const at = skills.findIndex((k) => k.id === focusId);
  if (at < 0) return [];
  const focus = skills[at];
  const conf = new Set(focus.conf || []);
  const rows = skills
    .map((k, i) => ({
      k,
      i,
      started: isStarted(states[k.id]),
      confuser: conf.has(k.p),
      due: isDue(states[k.id], now),
    }))
    .filter(
      (r) =>
        r.k.id !== focusId &&
        r.k.p !== focus.p &&
        (r.k.items || 0) + (r.k.packs || 0) > 0 &&
        (r.started || (r.confuser && r.i < at))
    )
    .sort(
      (a, b) =>
        b.confuser - a.confuser ||
        b.started - a.started ||
        b.due - a.due ||
        Math.abs(a.i - at) - Math.abs(b.i - at)
    );
  const picked = [];
  const seen = new Set();
  for (const r of rows) {
    if (picked.length >= size) break;
    if (seen.has(r.k.p)) continue;
    seen.add(r.k.p);
    picked.push(r.k);
  }
  for (const r of rows) {
    if (picked.length >= size) break;
    if (!picked.includes(r.k)) picked.push(r.k);
  }
  return picked;
}

/** The first skill in catalog order that is not mastered (the hub's "next up"). */
export function nextUp(skills, states) {
  return (
    skills.find((k) => (k.items || 0) + (k.packs || 0) > 0 && !isMastered(states[k.id])) || null
  );
}

/**
 * Merge two stored progress documents (this device and the server copy):
 * per skill, the entry with more answers wins; ties go to the later one.
 */
export function mergeProgress(a, b) {
  const out = {
    v: 1,
    skills: {},
    conj: {},
    settings: { ...((b && b.settings) || {}), ...((a && a.settings) || {}) },
  };
  for (const part of ['skills', 'conj']) {
    const x = (a && a[part]) || {};
    const y = (b && b[part]) || {};
    for (const id of new Set([...Object.keys(x), ...Object.keys(y)])) {
      const p = x[id];
      const q = y[id];
      if (!p || !q) out[part][id] = p || q;
      else if ((p.n || 0) !== (q.n || 0)) out[part][id] = (p.n || 0) > (q.n || 0) ? p : q;
      else out[part][id] = (p.last || 0) >= (q.last || 0) ? p : q;
    }
  }
  return out;
}
