// static/js/grammar/sync.js
// Grammar drills: copies progress to the server and back (ADR-066). No DOM.
//
// After each finished round the page hands over the round's first-answer
// totals per topic. They wait in localStorage under QUEUE_KEY with a round key
// until the server has taken them (at least once; the server ignores a key it
// has already recorded), so a round played offline is sent on a later visit.
// On load the queue is sent, then the server's state per topic and daily
// history are fetched and the state is merged into the local store.
//
// Nothing here is ever shown to the learner: when the server is unreachable or
// the tracking tables are not there yet, the page works from its local store.

import { applyRound } from './trends.js';

export const QUEUE_KEY = 'ld.grammar.zh.sync.v1';
/** Unsent rounds kept; the oldest are dropped beyond this. */
export const MAX_QUEUE = 60;
/** The server takes at most this many topics per call. */
export const MAX_TOPICS = 10;
export const MAX_MS = 30000;
export const HISTORY_DAYS = 180;

const API = '/api/grammar-drill';

function newKey() {
  try {
    if (globalThis.crypto && globalThis.crypto.randomUUID) return globalThis.crypto.randomUUID();
  } catch {}
  const hex = (n) =>
    Array.from({ length: n }, () => Math.floor(Math.random() * 16).toString(16)).join('');
  return (
    hex(8) +
    '-' +
    hex(4) +
    '-4' +
    hex(3) +
    '-' +
    '89ab'[Math.floor(Math.random() * 4)] +
    hex(3) +
    '-' +
    hex(12)
  );
}

/** The app's API helper (base.js). No token: no call, so nobody is sent to /login. */
async function defaultRequest(method, url, body) {
  let token = null;
  try {
    token = window.localStorage.getItem('jwt_token');
  } catch {}
  if (!token || typeof window.authFetch !== 'function') return { ok: false, status: 0, data: null };
  try {
    const res = await window.authFetch(
      url,
      body ? { method, body: JSON.stringify(body) } : { method }
    );
    let data = null;
    try {
      data = await res.json();
    } catch {}
    return { ok: !!res.ok, status: res.status, data };
  } catch {
    return { ok: false, status: 0, data: null };
  }
}

/** A running count of one session's first answers per topic. */
export function createTally() {
  let topics = {};
  return {
    /** `sub` is counted only for a miss; `ms` only for a right answer. */
    add(slug, { ok, ms, sub }) {
      const t = (topics[slug] = topics[slug] || {
        topic: slug,
        answers: 0,
        correct: 0,
        timed: 0,
        ms_sum: 0,
        sub_misses: {},
      });
      t.answers += 1;
      if (ok) {
        t.correct += 1;
        if (Number.isFinite(ms) && ms > 0) {
          t.timed += 1;
          t.ms_sum += Math.min(MAX_MS, Math.round(ms));
        }
      } else if (sub) {
        t.sub_misses[sub] = (t.sub_misses[sub] || 0) + 1;
      }
      return t.answers;
    },
    /** The counts so far, and start again. */
    take() {
      const out = Object.values(topics);
      topics = {};
      return out;
    },
  };
}

/**
 * createSync({ store, storage, request, languageId, now, instant })
 *   store      the progress store (syncState, mergeRemote, practised)
 *   storage    Storage-like, for the queue
 *   request    (method, url, body) => Promise<{ ok, status, data }>, never rejects
 *   instant    (slug) => boolean, whether the topic is "instant" now
 *   known      (slug) => boolean, whether the topic exists (the server
 *              refuses a call that names a topic it does not know)
 */
export function createSync({
  store,
  storage = null,
  request = defaultRequest,
  languageId = 1,
  now = Date.now,
  instant = () => false,
  known = () => true,
  key = QUEUE_KEY,
} = {}) {
  let progress = null;
  let down = false; // the server said no this visit: queue only
  let sending = null;

  function read() {
    try {
      const list = JSON.parse((storage && storage.getItem(key)) || '[]');
      return Array.isArray(list) ? list.filter((j) => j && j.k && Array.isArray(j.t)) : [];
    } catch {
      return [];
    }
  }

  function write(list) {
    try {
      if (storage) storage.setItem(key, JSON.stringify(list.slice(-MAX_QUEUE)));
    } catch {}
  }

  function entry(t) {
    const state = store.syncState(t.topic);
    return {
      topic: t.topic,
      answers: t.answers || 0,
      correct: t.correct || 0,
      timed: t.timed || 0,
      ms_sum: t.ms_sum || 0,
      stage: state ? state.u : 1,
      instant: !!(state && state.u >= 4 && instant(t.topic)),
      sub_misses: t.sub_misses || {},
      state,
    };
  }

  function push(mode, topics) {
    const list = read();
    for (let k = 0; k < topics.length; k += MAX_TOPICS) {
      list.push({
        k: newKey(),
        m: mode,
        at: Math.floor(now() / 1000),
        t: topics.slice(k, k + MAX_TOPICS).map(entry),
      });
    }
    write(list);
  }

  async function sendAll() {
    let sent = 0;
    for (;;) {
      const list = read();
      const job = list[0];
      if (!job || down) return sent;
      const res = await request('POST', API + '/round', {
        language_id: languageId,
        round_key: job.k,
        mode: job.m,
        played_at: job.at,
        topics: job.t,
      });
      if (res.ok) {
        sent += 1;
        if (progress && res.data && res.data.practice_day && res.data.recorded) {
          progress = applyRound(progress, res.data.practice_day, job.t);
        }
      } else if (res.status !== 400) {
        // Offline, signed out, rate limited, tables not there yet: keep it for a later visit.
        down = true;
        return sent;
      }
      // Taken, or refused for good (400): either way it leaves the queue.
      write(read().filter((j) => j.k !== job.k));
    }
  }

  function flush() {
    if (!sending) {
      sending = sendAll().finally(() => {
        sending = null;
      });
    }
    return sending;
  }

  return {
    /**
     * Queue one finished session and try to send it. `topics` is
     * createTally().take(); topics without answers are left out.
     */
    queueRound(mode, topics) {
      const list = (topics || []).filter((t) => t && t.answers > 0 && known(t.topic));
      if (!list.length) return Promise.resolve(0);
      push(mode, list);
      return flush();
    },

    flush,

    /**
     * Send what is waiting, then fetch the server's progress and merge its
     * states into the store. Resolves the progress ({ today, daily, states })
     * or null when the server has none to give. `merged` counts the topics
     * whose local state changed.
     */
    async pull() {
      await flush();
      if (down) return null;
      const res = await request(
        'GET',
        API + '/progress?language_id=' + languageId + '&days=' + HISTORY_DAYS
      );
      if (!res.ok || !res.data || !Array.isArray(res.data.daily)) {
        down = true;
        return null;
      }
      const states = res.data.states && typeof res.data.states === 'object' ? res.data.states : {};
      let merged = 0;
      Object.keys(states).forEach((slug) => {
        if (known(slug) && store.mergeRemote(slug, states[slug])) merged += 1;
      });
      // `merged`: topics whose local state the server's copy changed.
      progress = { today: res.data.today || '', daily: res.data.daily, states, merged };
      // Progress made before tracking existed: upload the state once. No
      // daily history is made up for it.
      const waiting = new Set(read().flatMap((j) => j.t.map((t) => t.topic)));
      const local = store
        .practised()
        .filter((slug) => known(slug) && !states[slug] && !waiting.has(slug))
        .map((slug) => ({ topic: slug }));
      if (local.length) {
        push('sync', local);
        await flush();
      }
      return progress;
    },

    /** The last pulled progress, kept up to date with rounds sent since; or null. */
    progress: () => progress,
    pending: () => read().length,
  };
}
