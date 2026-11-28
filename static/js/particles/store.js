// static/js/particles/store.js
// The learner's ladder state for the Japanese drills (particles, grammar,
// conjugation, reading). It lives in localStorage and is mirrored to the
// shared grammar-drill tracking (/api/grammar-drill, language 3):
//   POST /round     when a round ends: first-answer totals per topic (daily
//                   summary) and the topic's current state
//   GET  /progress  on load: the states stored for the account, merged in
// Until the tracking tables exist both answer 503; rounds then wait in a
// queue in localStorage (at most 60) and are sent later.
import { mergeProgress } from './mastery.js';

const KEY = 'ld_particle_drill_v1';
const QUEUE_KEY = 'ld_particle_drill_queue_v1';
const API = '/api/grammar-drill';
const LANGUAGE_ID = 3;
const MAX_QUEUE = 60;
const MAX_TOPICS = 10; // per request
const MAX_MS = 30000; // one recall time, as the server caps it
export const SKILL_STAGES = 7; // six rungs and Instant
export const FORM_STAGES = 4; // conjugation and reading: three rungs and Instant

const empty = () => ({ v: 1, skills: {}, conj: {}, settings: {} });

/** Tracking topic of a ladder entry: a skill id, conj-<form> or read-<category>. */
export function topicOf(part, id) {
  if (part === 'skills') return id;
  return id.startsWith('read:') ? `read-${id.slice(5)}` : `conj-${id.replace(/_/g, '-')}`;
}

/** The reverse: [part, id] in the local document. */
export function entryOf(topic) {
  if (topic.startsWith('read-')) return ['conj', `read:${topic.slice(5)}`];
  if (topic.startsWith('conj-')) return ['conj', topic.slice(5).replace(/-/g, '_')];
  return ['skills', topic];
}

const stagesOf = (part) => (part === 'skills' ? SKILL_STAGES : FORM_STAGES);
const clampInt = (n, lo, hi) => Math.min(hi, Math.max(lo, Math.round(Number(n) || 0)));

/** A local ladder state as the tracking state row: {u, l, s}. */
export function toServerState(part, s) {
  const max = stagesOf(part);
  const level = clampInt(s.l, 1, max);
  return {
    u: clampInt(Math.max(s.hi || 0, level), 1, max),
    l: Math.floor((s.last || 0) / 1000),
    s: {
      l: level,
      la: clampInt(s.la, 0, 1e7),
      e: s.e == null ? null : Math.min(1, Math.max(0, Number(s.e) || 0)),
      n: clampInt(s.n, 0, 1e7),
      c: clampInt(s.c, 0, 1e7),
      rt: s.rt == null ? null : Math.min(600000, Math.max(0, Math.round(s.rt))),
      due: s.due == null ? null : Math.round(s.due),
      iv: clampInt(s.iv, 0, 400),
      last: s.last == null ? null : Math.round(s.last),
      miss: (s.miss || []).filter((m) => /^[0-9a-f]{10}$/.test(m)).slice(0, 12),
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
  storage = window.localStorage,
  fetcher = window.authFetch,
  now = () => Date.now(),
} = {}) {
  let doc = empty();
  let queue = [];
  let round = new Map(); // topic -> first-answer totals of the round in progress
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
  const writeLocal = () => write(KEY, doc);
  const writeQueue = () => write(QUEUE_KEY, queue);

  function enqueue(body) {
    queue.push(body);
    // Oldest rounds go first when the queue is full: the state rides on every
    // later round, only that day's counts are lost.
    if (queue.length > MAX_QUEUE) queue = queue.slice(queue.length - MAX_QUEUE);
    writeQueue();
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
          break; // offline: try again later
        }
        // 4xx other than a rate limit: the round will never be accepted; drop it.
        if (!resp.ok && !(resp.status >= 400 && resp.status < 500 && resp.status !== 429)) break;
        queue.shift();
        writeQueue();
      }
    })().finally(() => {
      sending = null;
    });
    return sending;
  }

  function stateEntry(part, id) {
    const s = doc[part][id];
    return s ? toServerState(part, s) : null;
  }

  /** Close the round in progress: queue its totals and send. */
  function endRound(mode = 'round') {
    if (!round.size) return send();
    const entries = [];
    round.forEach((r, topic) => {
      const [part, id] = entryOf(topic);
      const state = stateEntry(part, id);
      if (!state || !r.answers) return;
      const max = stagesOf(part);
      entries.push({
        topic,
        answers: r.answers,
        correct: r.correct,
        timed: r.correct,
        ms_sum: r.ms,
        stage: state.s.l,
        instant: state.s.l >= max,
        sub_misses: {},
        state,
      });
    });
    round = new Map();
    const playedAt = Math.floor(now() / 1000);
    for (let i = 0; i < entries.length; i += MAX_TOPICS)
      enqueue({
        language_id: LANGUAGE_ID,
        round_key: uuid(),
        mode,
        played_at: playedAt,
        topics: entries.slice(i, i + MAX_TOPICS),
      });
    return send();
  }

  /** Load the account's states and merge them in; upload what only this browser has. */
  async function pull() {
    if (!fetcher) return;
    let body;
    try {
      const resp = await fetcher(`${API}/progress?language_id=${LANGUAGE_ID}&days=1`);
      if (!resp.ok) return; // 503 until the tables exist: local state is enough
      body = await resp.json();
    } catch (_e) {
      return; // offline
    }
    const states = (body && body.states) || {};
    const remote = empty();
    Object.keys(states).forEach((topic) => {
      const st = states[topic];
      if (!st || !st.s) return;
      const [part, id] = entryOf(topic);
      remote[part][id] = { ...st.s, miss: st.s.miss || [], hi: st.u };
    });
    doc = { ...mergeProgress(doc, remote), settings: doc.settings };
    writeLocal();
    // First upload of progress this browser made before the account had any.
    const missing = [];
    ['skills', 'conj'].forEach((part) =>
      Object.keys(doc[part]).forEach((id) => {
        const topic = topicOf(part, id);
        if (!states[topic] && (doc[part][id].n || 0) > 0)
          missing.push({
            topic,
            answers: 0,
            correct: 0,
            timed: 0,
            ms_sum: 0,
            stage: toServerState(part, doc[part][id]).s.l,
            instant: false,
            sub_misses: {},
            state: toServerState(part, doc[part][id]),
          });
      })
    );
    const queued = new Set(
      queue.filter((b) => b.mode === 'sync').flatMap((b) => b.topics.map((t) => t.topic))
    );
    const fresh = missing.filter((t) => !queued.has(t.topic));
    for (let i = 0; i < fresh.length; i += MAX_TOPICS)
      enqueue({
        language_id: LANGUAGE_ID,
        round_key: uuid(),
        mode: 'sync',
        topics: fresh.slice(i, i + MAX_TOPICS),
      });
    send();
  }

  doc = { ...empty(), ...read(KEY, empty()) };
  queue = Array.isArray(read(QUEUE_KEY, [])) ? read(QUEUE_KEY, []) : [];

  const setEntry = (part, id, state) => {
    const prev = doc[part][id];
    doc[part][id] = { ...state, hi: Math.max((prev && prev.hi) || 0, state.hi || 0, state.l || 1) };
  };

  return {
    get doc() {
      return doc;
    },
    get queued() {
      return queue.length;
    },
    skill: (id) => doc.skills[id],
    conj: (id) => doc.conj[id],
    setSkill: (id, state) => setEntry('skills', id, state),
    setConj: (id, state) => setEntry('conj', id, state),
    setting: (name, fallback) => (name in doc.settings ? doc.settings[name] : fallback),
    setSetting(name, value) {
      doc.settings[name] = value;
      writeLocal();
    },
    /**
     * Count one first answer towards the round in progress. `part` is 'skills'
     * or 'conj'; `ms` is the recall time of a right answer.
     */
    note(part, id, { correct, ms }) {
      const topic = topicOf(part, id);
      const r = round.get(topic) || { answers: 0, correct: 0, ms: 0 };
      r.answers += 1;
      if (correct) {
        r.correct += 1;
        r.ms += Math.min(MAX_MS, Math.max(0, Math.round(ms || 0)));
      }
      round.set(topic, r);
    },
    /** Write to localStorage now; the server hears at the end of the round. */
    save: writeLocal,
    endRound,
    /** Leaving the page or the drill: write locally and close the round. */
    flush(mode) {
      writeLocal();
      return endRound(mode);
    },
    pull,
  };
}
