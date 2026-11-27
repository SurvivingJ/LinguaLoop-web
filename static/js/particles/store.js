// static/js/particles/store.js
// The learner's ladder state: kept in localStorage, mirrored to the server
// (PUT /api/particle-drill/progress) when that store exists.
import { mergeProgress } from './mastery.js';

const KEY = 'ld_particle_drill_v1';
const API = '/api/particle-drill/progress';
const LANGUAGE_ID = 3;

const empty = () => ({ v: 1, skills: {}, conj: {}, settings: {} });

export function createStore({ storage = window.localStorage, fetcher = window.authFetch } = {}) {
  let doc = empty();
  let timer = null;
  let serverOk = true;

  function readLocal() {
    try {
      const raw = storage.getItem(KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === 'object') doc = { ...empty(), ...parsed };
    } catch (_e) {
      doc = empty();
    }
  }

  function writeLocal() {
    try {
      storage.setItem(KEY, JSON.stringify(doc));
    } catch (_e) {
      /* private mode or full storage: the session still works in memory */
    }
  }

  async function pull() {
    if (!fetcher) return;
    try {
      const resp = await fetcher(`${API}?language_id=${LANGUAGE_ID}`);
      if (!resp.ok) return;
      const body = await resp.json();
      serverOk = body.available !== false;
      if (body.state) {
        doc = mergeProgress(doc, body.state);
        writeLocal();
      }
    } catch (_e) {
      /* offline: local state is enough */
    }
  }

  async function push() {
    timer = null;
    if (!fetcher || !serverOk) return;
    try {
      const resp = await fetcher(API, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language_id: LANGUAGE_ID, state: doc }),
      });
      if (resp.ok) {
        const body = await resp.json();
        if (body.available === false) serverOk = false;
      }
    } catch (_e) {
      /* retried on the next save */
    }
  }

  readLocal();
  return {
    get doc() {
      return doc;
    },
    skill: (id) => doc.skills[id],
    conj: (id) => doc.conj[id],
    setSkill(id, state) {
      doc.skills[id] = state;
    },
    setConj(id, state) {
      doc.conj[id] = state;
    },
    setting: (name, fallback) => (name in doc.settings ? doc.settings[name] : fallback),
    setSetting(name, value) {
      doc.settings[name] = value;
      writeLocal();
    },
    /** Write to localStorage now and to the server shortly after. */
    save() {
      writeLocal();
      if (timer == null) timer = setTimeout(push, 4000);
    },
    flush() {
      writeLocal();
      if (timer != null) {
        clearTimeout(timer);
        return push();
      }
      return Promise.resolve();
    },
    pull,
  };
}
