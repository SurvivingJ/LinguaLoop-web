// static/js/grammar/store.js
// Grammar drills: the learner's progress. This module is the only place that
// knows where progress lives: localStorage, with the compact per-topic state
// below (syncState / mergeRemote) copied to and from the server by sync.js.
// The per-item boxes (i) never leave the browser.
//
// Stored shape (compact; one JSON value under KEY):
//   { v: 1,
//     s: { py: 0|1, ty: 0|1 },                 settings
//     t: { <slug>: {
//       s: stage, u: highest unlocked stage,
//       r: [[...], [...], [...], [...]],       last WINDOW results per stage (ladder.encodeResult);
//                                              the time is the recall time (to "Show choices"
//                                              on a recall cloze, else the whole answer)
//       w: [[...], [...], [...], [...]],       the same answers' total times (ms)
//       i: { <id suffix>: [box, seq] },        Leitner box 0-5 and when last seen
//       q: seq,                                answers recorded for the topic
//       l: epoch seconds of the last answer,
//       sp: speed-stage base countdown (ms),
//       e: [answers, correct, best streak]     endless mode totals
//     } } }

import { LAST_STAGE, SPEED_START_MS, WINDOW, encodeResult, unlocksNext } from './ladder.js';

export const KEY = 'ld.grammar.zh.v1';
export const MAX_BOX = 5;

/** 'le-03-017' under topic 'le' -> '03-017'. Generated items have no key. */
export function itemKey(slug, id) {
  const s = String(id || '');
  if (!s || s.startsWith('gen:')) return '';
  return s.startsWith(slug + '-') ? s.slice(slug.length + 1) : s;
}

/** A stage's results for the server: '1200,-800,950' (signed ms, oldest first). */
export function encodeResults(list) {
  return (list || [])
    .slice(-WINDOW)
    .map((r) => Math.trunc(r))
    .filter((r) => r)
    .join(',');
}

/** The reverse of encodeResults; anything unreadable gives []. */
export function decodeResults(text) {
  if (typeof text !== 'string' || !text) return [];
  const parts = text.split(',');
  if (!parts.every((x) => /^-?[1-9]\d{0,5}$/.test(x))) return [];
  return parts.map(Number).slice(-WINDOW);
}

const stageOf = (n) => Math.min(LAST_STAGE, Math.max(1, Math.trunc(Number(n)) || 1));
const count = (n) => Math.max(0, Math.trunc(Number(n)) || 0);

function blankTopic() {
  return {
    s: 1,
    u: 1,
    r: [[], [], [], []],
    w: [[], [], [], []],
    i: {},
    q: 0,
    l: 0,
    sp: SPEED_START_MS,
    e: [0, 0, 0],
  };
}

function clean(raw) {
  const data = raw && typeof raw === 'object' && raw.v === 1 ? raw : { v: 1 };
  if (!data.s || typeof data.s !== 'object') data.s = {};
  if (!data.t || typeof data.t !== 'object') data.t = {};
  return data;
}

function defaultStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/**
 * `storage` is a Storage-like object (getItem / setItem); every call is
 * guarded, so a blocked or full localStorage only means progress is not kept.
 * `now()` returns epoch milliseconds.
 */
export function createStore(storage = defaultStorage(), key = KEY, now = Date.now) {
  let data;
  try {
    data = clean(JSON.parse((storage && storage.getItem(key)) || 'null'));
  } catch {
    data = clean(null);
  }

  function save() {
    try {
      if (storage) storage.setItem(key, JSON.stringify(data));
    } catch {}
  }

  function raw(slug, create) {
    let t = data.t[slug];
    if (!t && create) {
      t = data.t[slug] = blankTopic();
    }
    if (t) {
      const base = blankTopic();
      Object.keys(base).forEach((k) => {
        if (t[k] == null) t[k] = base[k];
      });
      while (t.r.length < LAST_STAGE) t.r.push([]);
      while (t.w.length < LAST_STAGE) t.w.push([]);
    }
    return t;
  }

  /** A topic as the engine reads it (a copy: change it through the store). */
  function topic(slug) {
    const t = raw(slug, false) || blankTopic();
    const results = {};
    const totals = {};
    t.r.forEach((list, k) => {
      results[k + 1] = list.slice();
      totals[k + 1] = (t.w[k] || []).slice();
    });
    return {
      stage: t.s,
      unlocked: t.u,
      results,
      totals,
      items: t.i,
      seq: t.q,
      last: t.l,
      speedMs: t.sp,
      answers: t.q + t.e[0],
      endless: { answers: t.e[0], correct: t.e[1], best: t.e[2] },
    };
  }

  return {
    topic,

    settings() {
      return { pinyin: !!data.s.py, typing: !!data.s.ty };
    },

    setSetting(name, on) {
      const k = { pinyin: 'py', typing: 'ty' }[name];
      if (!k) return;
      data.s[k] = on ? 1 : 0;
      save();
    },

    /** Topics with any recorded answer, most recent first. */
    practised() {
      return Object.keys(data.t)
        .filter((slug) => data.t[slug].q > 0 || (data.t[slug].e || [0])[0] > 0)
        .sort((a, b) => (data.t[b].l || 0) - (data.t[a].l || 0));
    },

    /** Choose the stage to drill (any unlocked one). */
    setStage(slug, n) {
      const t = raw(slug, true);
      t.s = Math.min(t.u, Math.max(1, n | 0));
      save();
      return t.s;
    },

    setSpeed(slug, ms) {
      raw(slug, true).sp = Math.round(ms);
      save();
    },

    /**
     * Record a first answer to an item. `stage` null (mixed review, endless)
     * moves the item's box only; a stage number also feeds that stage's
     * rolling results and may unlock the next stage. `ms` is the recall time
     * (the stage metric); `totalMs` the whole answer, when it differs. Returns
     * { unlocked } with the newly opened stage number, or 0.
     */
    record(slug, { id, stage, ok, ms, totalMs }) {
      const t = raw(slug, true);
      t.q += 1;
      t.l = Math.floor(now() / 1000);
      const k = itemKey(slug, id);
      if (k) {
        const box = t.i[k] ? t.i[k][0] : 0;
        t.i[k] = [ok ? Math.min(MAX_BOX, box + 1) : 0, t.q];
      }
      let unlocked = 0;
      if (stage) {
        const list = t.r[stage - 1];
        list.push(encodeResult(ok, ms));
        if (list.length > WINDOW) list.splice(0, list.length - WINDOW);
        const totals = t.w[stage - 1];
        totals.push(Math.abs(encodeResult(true, totalMs == null ? ms : totalMs)));
        if (totals.length > WINDOW) totals.splice(0, totals.length - WINDOW);
        if (stage === t.u && stage < LAST_STAGE && unlocksNext(list)) {
          t.u = stage + 1;
          unlocked = t.u;
        }
      }
      save();
      return { unlocked };
    },

    /** Add one endless-mode answer to the topic's totals. */
    recordEndless(slug, ok, streak) {
      const t = raw(slug, true);
      t.e[0] += 1;
      if (ok) t.e[1] += 1;
      t.e[2] = Math.max(t.e[2], streak || 0);
      t.l = Math.floor(now() / 1000);
      save();
    },

    /**
     * The part of a topic the server keeps (so progress follows the learner):
     * { u, r: [4 strings], q, e: [answers, correct, best], l }. Null for a
     * topic with nothing recorded.
     */
    syncState(slug) {
      const t = raw(slug, false);
      if (!t || (!t.q && !t.e[0])) return null;
      return {
        u: t.u,
        r: t.r.slice(0, LAST_STAGE).map(encodeResults),
        q: t.q,
        e: [count(t.e[0]), count(t.e[1]), count(t.e[2])],
        l: t.l,
      };
    },

    /**
     * Take in the server's state for a topic. Never loses local progress:
     * the unlocked stage and the counts only go up, and the rolling results
     * are replaced only when the server's last answer is later than the local
     * one. Returns true when anything changed.
     */
    mergeRemote(slug, remote) {
      if (!remote || typeof remote !== 'object') return false;
      const had = raw(slug, false);
      const fresh = !had || (!had.q && !had.e[0]);
      const t = raw(slug, true);
      const before = JSON.stringify(t);
      t.u = Math.max(t.u, stageOf(remote.u));
      const theirs = count(remote.l);
      if (theirs > t.l && Array.isArray(remote.r)) {
        for (let k = 0; k < LAST_STAGE; k++) {
          t.r[k] = decodeResults(remote.r[k]);
          t.w[k] = t.r[k].map((r) => Math.abs(r));
        }
        t.l = theirs;
      }
      t.q = Math.max(t.q, count(remote.q));
      const e = Array.isArray(remote.e) ? remote.e : [];
      t.e = [0, 1, 2].map((k) => Math.max(count(t.e[k]), count(e[k])));
      // A browser that has never drilled the topic starts at the highest open stage.
      if (fresh) t.s = t.u;
      const changed = JSON.stringify(t) !== before;
      if (changed) save();
      else if (!had) delete data.t[slug];
      return changed;
    },

    /** The whole stored value. */
    dump() {
      return JSON.parse(JSON.stringify(data));
    },
  };
}
