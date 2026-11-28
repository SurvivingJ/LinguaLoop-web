// static/js/idioms/store.js
// The learner's idiom ladders for one language: kept in localStorage and
// mirrored to the shared grammar-drill tracking (/api/grammar-drill), where an
// idiom is the topic `idiom-<id>` with six stages.
//   POST /round     when a round ends: first-answer totals and the state per idiom
//   GET  /progress  on load: the account's states, merged in
// Until the tracking tables exist both answer 503; rounds then wait in the
// browser (at most 60) and are sent later.
import { MASTERED, mergeStates } from './ladder.js';

const API = '/api/grammar-drill';
const MAX_QUEUE = 60;
const MAX_TOPICS = 10;
const MAX_MS = 30000;
const PREFIX = 'idiom-';

export const topicOf = (id) => PREFIX + id;
export const idOf = (topic) => (topic.startsWith(PREFIX) ? topic.slice(PREFIX.length) : null);

const int = (n, lo, hi) => Math.min(hi, Math.max(lo, Math.round(Number(n) || 0)));

/** A local ladder state as the tracking state row: {u, l, s}. */
export function toServerState(s) {
  const level = int(s.l, 1, MASTERED);
  return {
    u: int(Math.max(s.hi || 0, level), 1, MASTERED),
    l: Math.floor((s.last || 0) / 1000),
    s: {
      l: level,
      k: int(s.k, 0, 5),
      n: int(s.n, 0, 1e7),
      c: int(s.c, 0, 1e7),
      due: s.due == null ? null : Math.round(s.due),
      iv: int(s.iv, 0, 400),
      last: s.last == null ? null : Math.round(s.last),
    },
  };
}

const uuid = () =>
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : 'xxxxxxxx-xxxx-4xxx-8xxx-xxxxxxxxxxxx'.replace(/x/g, () =>
        Math.floor(Math.random() * 16).toString(16)
      );

export function createStore({
  lang,
  languageId,
  storage = window.localStorage,
  fetcher = window.authFetch,
  now = () => Date.now(),
} = {}) {
  const KEY = `ld_idioms_${lang}_v1`;
  const QUEUE_KEY = `ld_idioms_${lang}_queue_v1`;
  const empty = () => ({ v: 1, idioms: {}, settings: {} });
  let doc = empty();
  let queue = [];
  let round = new Map();
  let sending = null;

  const read = (key, fallback) => {
    try {
      const raw = storage.getItem(key);
      const parsed = raw ? JSON.parse(raw) : null;
      return parsed && typeof parsed === 'object' ? parsed : fallback;
    } catch (_e) {
      return fallback;
    }
  };
  const write = (key, value) => {
    try {
      storage.setItem(key, JSON.stringify(value));
    } catch (_e) {
      /* private mode or full storage: the session still works in memory */
    }
  };

  function enqueue(body) {
    queue.push(body);
    if (queue.length > MAX_QUEUE) queue = queue.slice(queue.length - MAX_QUEUE);
    write(QUEUE_KEY, queue);
  }

  /** Send queued rounds in order; stop at the first one the server cannot take now. */
  function send() {
    if (!fetcher || sending) return sending || Promise.resolve();
    sending = (async () => {
      while (queue.length) {
        let resp;
        try {
          resp = await fetcher(`${API}/round`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(queue[0]),
          });
        } catch (_e) {
          break;
        }
        // 4xx other than a rate limit: it will never be accepted; drop it.
        if (!resp.ok && !(resp.status >= 400 && resp.status < 500 && resp.status !== 429)) break;
        queue.shift();
        write(QUEUE_KEY, queue);
      }
    })().finally(() => {
      sending = null;
    });
    return sending;
  }

  const entry = (id, r) => {
    const state = toServerState(doc.idioms[id]);
    return {
      topic: topicOf(id),
      answers: r.answers,
      correct: r.correct,
      timed: r.correct,
      ms_sum: r.ms,
      stage: state.s.l,
      instant: state.s.l >= MASTERED,
      sub_misses: {},
      state,
    };
  };

  function endRound() {
    const entries = [];
    round.forEach((r, id) => {
      if (doc.idioms[id] && r.answers) entries.push(entry(id, r));
    });
    round = new Map();
    const playedAt = Math.floor(now() / 1000);
    for (let i = 0; i < entries.length; i += MAX_TOPICS)
      enqueue({
        language_id: languageId,
        round_key: uuid(),
        mode: 'round',
        played_at: playedAt,
        topics: entries.slice(i, i + MAX_TOPICS),
      });
    return send();
  }

  async function pull() {
    if (!fetcher) return;
    let body;
    try {
      const resp = await fetcher(`${API}/progress?language_id=${languageId}&days=1`);
      if (!resp.ok) return;
      body = await resp.json();
    } catch (_e) {
      return;
    }
    const states = (body && body.states) || {};
    const remote = {};
    Object.keys(states).forEach((topic) => {
      const id = idOf(topic);
      const st = states[topic];
      if (id && st && st.s) remote[id] = { ...st.s, hi: st.u };
    });
    doc.idioms = mergeStates(doc.idioms, remote);
    write(KEY, doc);
    // progress this browser made before the account had any
    const queued = new Set(
      queue.filter((b) => b.mode === 'sync').flatMap((b) => b.topics.map((t) => t.topic))
    );
    const missing = Object.keys(doc.idioms)
      .filter(
        (id) => (doc.idioms[id].n || 0) > 0 && !states[topicOf(id)] && !queued.has(topicOf(id))
      )
      .map((id) => ({ ...entry(id, { answers: 0, correct: 0, ms: 0 }), instant: false }));
    for (let i = 0; i < missing.length; i += MAX_TOPICS)
      enqueue({
        language_id: languageId,
        round_key: uuid(),
        mode: 'sync',
        topics: missing.slice(i, i + MAX_TOPICS),
      });
    send();
  }

  doc = { ...empty(), ...read(KEY, empty()) };
  queue = Array.isArray(read(QUEUE_KEY, [])) ? read(QUEUE_KEY, []) : [];

  return {
    get states() {
      return doc.idioms;
    },
    get queued() {
      return queue.length;
    },
    state: (id) => doc.idioms[id],
    /** Store an idiom's new state and count the answer towards the round. */
    answer(id, state, { correct, ms }) {
      doc.idioms[id] = state;
      const r = round.get(id) || { answers: 0, correct: 0, ms: 0 };
      r.answers += 1;
      if (correct) {
        r.correct += 1;
        r.ms += Math.min(MAX_MS, Math.max(0, Math.round(ms || 0)));
      }
      round.set(id, r);
      write(KEY, doc);
    },
    setting: (name, fallback) => (name in doc.settings ? doc.settings[name] : fallback),
    setSetting(name, value) {
      doc.settings[name] = value;
      write(KEY, doc);
    },
    endRound,
    pull,
  };
}
