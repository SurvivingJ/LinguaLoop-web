// static/js/session/players/intro_drill.js
// New-word drill (wiki/features/new-word-drill.md, ADR-040).
//
// The practice session payload may carry `intro_drill`: the learner's due
// intro words. Each word is drilled until it is answered right `target` times
// (5 / 3 / 2 / 2 by session), where a right answer only COUNTS when at least
// `gap` other items came since the word was last shown, the format differs
// from the last counted one, and it was not "I don't know". Sessions 2-4 open
// with a cold recall; missing it adds one to the target. Each finished word is
// posted to /api/practice/intro/complete, which recounts with the same rules
// (services/intro_drill.py `recount`) and advances the word.
//
// The engine (createDrill) is DOM-free and unit-tested; runIntroDrill renders
// it inside the practice player's card, reusing window.ExRenderers for ladder
// exercises and window.LinguaPrestudy's reading graders.

const T = (key, params, fallback) => {
  if (window.LinguaI18n && typeof LinguaI18n.t === 'function') {
    const v = LinguaI18n.t(key, params);
    if (v && v !== key) return v;
  }
  let s = fallback || key;
  if (params) for (const k of Object.keys(params)) s = s.replace(`{${k}}`, params[k]);
  return s;
};

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

// ---------------------------------------------------------------------------
// Engine (mirrors services/intro_drill.py recount)
// ---------------------------------------------------------------------------

export const MIN_GAP_ITEMS = 4;
// With only 1-3 words left, a spacer goes between two showings of the same
// word that would otherwise have fewer than this many items between them.
export const SPACER_MIN_GAP = 2;
export const TARGETS = { 1: 5, 2: 3, 3: 2, 4: 2 };
export const CAPS = { 1: 12, 2: 8, 3: 6, 4: 6 };
export const COLD_MISS_BUMP = 1;
const KNOWN_FORMATS = new Set(['read_typed', 'read_typed2', 'def_mc', 'rev_mc', 'cloze_mc', 'cloze_typed', 'recall_typed', 'ex_use', 'ex_judge']);

export function effGap(nWords) {
  return Math.min(MIN_GAP_ITEMS, Math.max(0, nWords - 1));
}

/**
 * Re-count one word's attempts with the drill's rules. Mirror of
 * services/intro_drill.py `recount` (the shared fixture pins both); also
 * used by the prestudy page to decide whether a prime met session 1.
 * attempts: [{pos, gap, format, correct, idk}] in serving order.
 */
export function countWord(stage, attempts, nWords, formats) {
  let target = TARGETS[stage];
  const cap = CAPS[stage];
  const maxGap = effGap(nWords);
  const distinct = new Set((formats || []).filter((f) => KNOWN_FORMATS.has(f))).size >= 2;
  let counted = 0;
  let lastPos = null;
  let lastFmt = null;
  let coldCorrect = null;
  let items = 0;
  for (const a of attempts.slice().sort((x, y) => x.pos - y.pos).slice(0, cap)) {
    const ok = !!a.correct && !a.idk;
    const g = Number(a.gap);
    const gap = a.gap == null || !Number.isFinite(g) ? maxGap : Math.min(Math.max(Math.trunc(g), 0), maxGap);
    if (items === 0 && stage >= 2) {
      coldCorrect = ok;
      if (!ok) target += COLD_MISS_BUMP;
    }
    const spaced = lastPos === null || a.pos - lastPos - 1 >= gap;
    if (ok && spaced && (!distinct || a.format !== lastFmt)) {
      counted += 1;
      lastFmt = a.format;
    }
    lastPos = a.pos;
    items += 1;
    if (counted >= target) break;
  }
  return { target, counted, passed: counted >= target, cold_correct: coldCorrect, items };
}

/**
 * words: [{sense_id, stage, target, cap, cold, formats:[...]}]
 * Returns { next(), answer(item, res), remaining(), progress(sid) }.
 */
export function createDrill(words, opts = {}) {
  const rng = opts.rng || Math.random;
  let spacersLeft = opts.spacers || 0;
  const order = words.map((_, i) => i);
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  const W = new Map();
  order.forEach((idx, k) => {
    const w = words[idx];
    W.set(w.sense_id, {
      w, target: w.target, cap: w.cap, counted: 0, served: 0, fi: 0,
      lastFmt: null, lastPos: null, coldPending: !!w.cold, retryFmt: null,
      nextAt: k, done: false, passed: false, attempts: [],
      distinct: new Set(w.formats).size >= 2,
    });
  });
  let pos = 0;
  let lastSid = null;

  function active() {
    return [...W.values()].filter((x) => !x.done);
  }

  function next() {
    const a = active();
    if (!a.length) return null;
    const cands = a.length > 1 ? a.filter((x) => x.w.sense_id !== lastSid) : a;
    cands.sort((x, y) => x.nextAt - y.nextAt);
    const x = cands[0];
    // Too few words to keep repeats apart: put an ordinary practice item
    // (a spacer) between them while any are left.
    if (spacersLeft > 0 && x.lastPos !== null && pos - x.lastPos - 1 < SPACER_MIN_GAP) {
      return { spacer: true, pos };
    }
    const f = x.w.formats;
    const format = x.retryFmt || f[x.fi % f.length];
    // The spacing rule follows the words still being drilled, so the last
    // few words of a block are not held to a gap they cannot reach.
    return { sid: x.w.sense_id, format, pos, gap: effGap(a.length), word: x.w, retry: !!x.retryFmt };
  }

  function answer(item, res) {
    const x = W.get(item.sid);
    const ok = !!res.correct && !res.idk;
    if (x.coldPending) {
      x.coldPending = false;
      if (!ok) x.target += 1;
    }
    const gap = item.gap;
    const spaced = x.lastPos === null || item.pos - x.lastPos - 1 >= gap;
    let counted = false;
    if (ok && spaced && (!x.distinct || item.format !== x.lastFmt)) {
      x.counted += 1;
      x.lastFmt = item.format;
      counted = true;
    }
    x.attempts.push({
      pos: item.pos, gap, format: item.format, correct: !!res.correct, idk: !!res.idk,
      ms: res.ms || null, given: res.given == null ? '' : String(res.given).slice(0, 200),
      exercise_id: res.exercise_id || null,
    });
    x.lastPos = item.pos;
    x.served += 1;
    pos = item.pos + 1;
    lastSid = item.sid;
    if (ok) {
      x.retryFmt = null;
      x.fi += 1;
      x.nextAt = item.pos + gap + 1;
    } else {
      x.retryFmt = item.format;
      x.nextAt = item.pos + (res.idk ? 2 : 3) + Math.floor(rng() * 3);
    }
    if (x.counted >= x.target) {
      x.done = true;
      x.passed = true;
    } else if (x.served >= x.cap) {
      x.done = true;
    }
    return {
      counted,
      done: x.done,
      passed: x.passed,
      result: x.done
        ? { sense_id: x.w.sense_id, stage: x.w.stage, n_words: words.length, formats: x.w.formats, attempts: x.attempts }
        : null,
    };
  }

  // A spacer was answered: it takes a place in the order, no word moves.
  function skip(item) {
    spacersLeft -= 1;
    pos = item.pos + 1;
    lastSid = null;
  }

  return {
    next,
    answer,
    skip,
    remaining: () => active().length,
    progress: (sid) => {
      const x = W.get(sid);
      return x ? { counted: x.counted, target: x.target } : null;
    },
  };
}

// ---------------------------------------------------------------------------
// Grading
// ---------------------------------------------------------------------------

function norm(s) {
  return String(s || '').normalize('NFKC').trim().toLowerCase().replace(/\s+/g, ' ');
}

export function gradeReading(input, word, lang) {
  const LP = window.LinguaPrestudy;
  const rd = word.reading;
  if (!rd || !String(input).trim()) return false;
  if (lang === 'zh') {
    if (!LP || !rd.numbered) return norm(input) === norm(rd.shown);
    const pi = LP.parsePinyinInput(input);
    return LP.gradeZh(pi.segs, pi.tones, rd.numbered, word.lemma).ok;
  }
  if (LP) return LP.gradeJa(input, rd.shown).ok;
  return norm(input) === norm(rd.shown);
}

export function gradeRecall(input, word, lang) {
  if (!String(input).trim()) return false;
  if (norm(input) === norm(word.lemma)) return true;
  return lang !== 'en' && !!word.reading && gradeReading(input, word, lang);
}

// ---------------------------------------------------------------------------
// Items
// ---------------------------------------------------------------------------

function pick(arr, n, rng = Math.random) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, n);
}

function options(correct, candidates) {
  const others = [...new Set(candidates.filter((c) => c && c !== correct))];
  return pick([correct, ...pick(others, 3)], 4);
}

function readingText(word, lang) {
  if (!word.reading) return '';
  return lang === 'zh' && word.reading.numbered ? `${word.reading.shown} (${word.reading.numbered})` : word.reading.shown;
}

/** Build the renderable item for an engine pick. */
export function buildItem(pickd, block, exUsed) {
  const w = pickd.word;
  const lang = block.lang;
  const others = block.words.filter((x) => x.sense_id !== w.sense_id);
  const defs = others.map((x) => x.gloss).concat((block.pool || []).map((p) => p.def));
  const lemmas = others.map((x) => x.lemma).concat((block.pool || []).map((p) => p.lemma));
  switch (pickd.format) {
    case 'read_typed':
    case 'read_typed2':
      return { kind: 'typed', grade: 'reading', prompt: w.lemma, ask: T('intro.ask_reading', null, 'Type the reading'), hint: lang === 'zh' ? T('intro.pinyin_hint', null, 'pinyin with tone numbers, e.g. mu4 tou5') : T('intro.kana_hint', null, 'kana or romaji') };
    case 'recall_typed':
      return { kind: 'typed', grade: 'recall', prompt: w.gloss, ask: T('intro.ask_recall', null, 'Type the word for this meaning'), hint: '' };
    case 'cloze_typed':
      return { kind: 'typed', grade: 'recall', prompt: w.sentence, sub: w.gloss, ask: T('intro.ask_cloze_typed', null, 'Type the missing word'), hint: '' };
    case 'def_mc':
      return { kind: 'mc', prompt: w.lemma, sub: readingText(w, lang), ask: T('intro.ask_meaning', null, 'What does it mean?'), opts: options(w.gloss, defs), correct: w.gloss };
    case 'rev_mc':
      return { kind: 'mc', prompt: w.gloss, ask: T('intro.ask_word', null, 'Which word means this?'), opts: options(w.lemma, lemmas), correct: w.lemma, big: true };
    case 'cloze_mc':
      return { kind: 'mc', prompt: w.sentence, ask: T('intro.ask_cloze', null, 'Which word fills the gap?'), opts: options(w.lemma, lemmas), correct: w.lemma, big: true };
    case 'ex_use':
    case 'ex_judge': {
      const list = (w.exercises || {})[pickd.format === 'ex_use' ? 'use' : 'judge'] || [];
      if (!list.length) return null;
      const used = exUsed.get(w.sense_id) || 0;
      exUsed.set(w.sense_id, used + 1);
      return { kind: 'ex', ex: list[used % list.length] };
    }
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------

const PENDING_KEY = 'introDrillPending';

async function postResults(results) {
  const res = await window.authFetch('/api/practice/intro/complete', {
    method: 'POST',
    body: JSON.stringify({ results }),
  });
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

function stash(result) {
  try {
    const cur = JSON.parse(sessionStorage.getItem(PENDING_KEY) || '[]');
    cur.push(result);
    sessionStorage.setItem(PENDING_KEY, JSON.stringify(cur.slice(-40)));
  } catch {
    /* storage blocked: the word is simply served again next time */
  }
}

async function flushStashed() {
  let cur = [];
  try {
    cur = JSON.parse(sessionStorage.getItem(PENDING_KEY) || '[]');
  } catch {
    return;
  }
  if (!cur.length) return;
  try {
    await postResults(cur);
    sessionStorage.removeItem(PENDING_KEY);
  } catch {
    /* keep for the next attempt */
  }
}

async function sendResult(result) {
  try {
    return await postResults([result]);
  } catch {
    try {
      return await postResults([result]);
    } catch (e) {
      console.warn('[intro] result not saved, will retry next session:', e);
      stash(result);
      return null;
    }
  }
}

/**
 * Run the drill inside `cardEl`. Resolves with {words, passed} when every word
 * has finished. `setHeader(text)` updates the practice header.
 */
export function runIntroDrill(cardEl, block, opts = {}) {
  return new Promise((resolve) => {
    flushStashed();
    const ER = window.ExRenderers;
    const lang = block.lang;
    const words = (block.words || []).filter((w) => w.formats && w.formats.length);
    if (!words.length) {
      resolve({ words: 0, passed: 0 });
      return;
    }
    const spacers = (opts.spacers || []).slice();
    let usedSpacers = 0;
    const drill = createDrill(words, { spacers: spacers.length });
    const byId = new Map(words.map((w) => [w.sense_id, w]));
    const exUsed = new Map();
    let passed = 0;
    let current = null;
    let shownAt = 0;
    const sends = [];

    function header() {
      if (opts.setHeader) {
        opts.setHeader(T('intro.progress', { n: drill.remaining(), total: words.length }, 'New words — {n} of {total} to go'));
      }
    }

    function pips(sid) {
      const p = drill.progress(sid);
      if (!p) return '';
      let h = '';
      for (let i = 0; i < p.target; i++) h += `<span class="intro-pip${i < p.counted ? ' on' : ''}"></span>`;
      return `<div class="intro-pips" title="${esc(T('intro.pips_title', null, 'Right answers needed'))}">${h}</div>`;
    }

    function stageBadge(w) {
      return `<div class="exercise-type-badge"><i class="fas fa-seedling"></i> ${esc(T('intro.stage', { n: w.stage }, 'New word · session {n} of 4'))}</div>`;
    }

    function step() {
      header();
      let p = drill.next();
      if (p && p.spacer) {
        renderSpacer(p, spacers[usedSpacers]);
        return;
      }
      let item = null;
      // A format that cannot be built here falls through to the word's next one.
      for (let guard = 0; p && guard < 6; guard++) {
        item = buildItem(p, block, exUsed);
        if (item) break;
        p = { ...p, format: p.word.formats[(p.word.formats.indexOf(p.format) + 1) % p.word.formats.length] };
      }
      if (!p) {
        cardEl.innerHTML = `<p style="text-align:center;color:var(--text-secondary);padding:32px">${esc(T('intro.saving', null, 'Saving your new words…'))}</p>`;
        Promise.allSettled(sends).then(() => resolve({ words: words.length, passed, usedSpacers }));
        return;
      }
      current = { pick: p, item };
      shownAt = performance.now();
      if (item.kind === 'ex') renderEx(p, item);
      else renderOwn(p, item);
    }

    function finish(res) {
      const ms = Math.round(performance.now() - shownAt);
      const out = drill.answer(current.pick, { ...res, ms });
      if (out.result) {
        if (out.passed) passed += 1;
        sends.push(sendResult(out.result));
      }
      return out;
    }

    function feedback(ok, idk, w, extra) {
      const rd = readingText(w, lang);
      const line = `<strong>${esc(w.lemma)}</strong>${rd ? ' · ' + esc(rd) : ''} — ${esc(w.gloss)}`;
      const head = ok
        ? `<i class="fas fa-check-circle" style="color:var(--success)"></i> ${esc(T('intro.right', null, 'Right!'))}`
        : idk
          ? `<i class="fas fa-lightbulb" style="color:var(--warning, #d97706)"></i> ${esc(T('intro.idk_shown', null, 'Here it is — it will come back soon.'))}`
          : `<i class="fas fa-times-circle" style="color:var(--danger)"></i> ${esc(T('intro.wrong', null, 'Not quite.'))}`;
      const ex = w.example && extra !== 'noex' ? `<div style="margin-top:6px;color:var(--text-secondary)">${esc(w.example)}</div>` : '';
      return `<div class="exercise-feedback show ${ok ? 'correct' : 'incorrect'}">${head}<div style="margin-top:6px">${line}</div>${ex}</div>`;
    }

    function renderOwn(p, item) {
      const w = byId.get(p.sid);
      const prompt = item.big || item.kind === 'typed' && item.grade === 'recall'
        ? `<div class="exercise-prompt">${esc(item.prompt)}</div>`
        : `<div class="exercise-prompt" style="font-size:28px;font-weight:700">${esc(item.prompt)}</div>`;
      const sub = item.sub ? `<div style="color:var(--text-secondary);margin:-12px 0 16px">${esc(item.sub)}</div>` : '';
      let body;
      if (item.kind === 'typed') {
        body = `<form id="introTypedForm" autocomplete="off" style="display:flex;gap:8px">
            <input id="introTyped" class="form-control" lang="${esc(lang)}" placeholder="${esc(item.hint || '')}" autocapitalize="off" spellcheck="false" style="flex:1;font-size:18px">
            <button class="btn btn-primary" type="submit">${esc(T('intro.check', null, 'Check'))}</button></form>`;
      } else {
        body = `<div class="exercise-options">${item.opts
          .map((o, i) => `<div class="exercise-option" data-i="${i}"><span class="option-letter">${'ABCD'[i]}</span><span>${esc(o)}</span></div>`)
          .join('')}</div>`;
      }
      cardEl.innerHTML = `${stageBadge(w)}${pips(p.sid)}
        <div class="exercise-instruction">${esc(item.ask)}</div>${prompt}${sub}${body}
        <button class="btn btn-link intro-idk" id="introIdk" type="button">${esc(T('intro.idk', null, "I don't know"))}</button>
        <div id="introFb"></div>
        <button class="btn btn-primary exercise-next-btn" id="introNext">${esc(T('exercises.next', null, 'Next'))} <i class="fas fa-arrow-right ms-1"></i></button>`;
      let answered = false;
      const done = (ok, idk, given) => {
        if (answered) return;
        answered = true;
        finish({ correct: ok, idk, given });
        cardEl.querySelectorAll('.exercise-option').forEach((el) => {
          const v = item.opts[+el.dataset.i];
          el.classList.add('disabled');
          if (v === item.correct) el.classList.add('correct');
          else if (v === given) el.classList.add('incorrect');
        });
        const inp = cardEl.querySelector('#introTyped');
        if (inp) inp.disabled = true;
        cardEl.querySelector('#introIdk').disabled = true;
        cardEl.querySelector('#introFb').innerHTML = feedback(ok, idk, w);
        const nx = cardEl.querySelector('#introNext');
        nx.classList.add('show');
        nx.focus();
      };
      cardEl.querySelector('#introNext').addEventListener('click', step);
      cardEl.querySelector('#introIdk').addEventListener('click', () => done(false, true, ''));
      if (item.kind === 'typed') {
        const inp = cardEl.querySelector('#introTyped');
        inp.focus();
        cardEl.querySelector('#introTypedForm').addEventListener('submit', (e) => {
          e.preventDefault();
          if (answered) {
            step();
            return;
          }
          const v = inp.value;
          if (!v.trim()) return;
          const ok = item.grade === 'reading' ? gradeReading(v, w, lang) : gradeRecall(v, w, lang);
          done(ok, false, v);
        });
      } else {
        cardEl.querySelectorAll('.exercise-option').forEach((el) =>
          el.addEventListener('click', () => {
            const v = item.opts[+el.dataset.i];
            done(v === item.correct, false, v);
          })
        );
      }
    }

    // An ordinary practice item between two showings of the same word; the
    // host records it (opts.onSpacer) as a normal practice attempt.
    function renderSpacer(p, ex) {
      usedSpacers += 1;
      let answered = false;
      const started = performance.now();
      ER.init({
        cardEl,
        isAnswered: () => answered,
        setAnswered: (v) => {
          answered = v;
        },
        showFeedback: (ok, expl) => {
          const fb = document.createElement('div');
          fb.className = `exercise-feedback show ${ok ? 'correct' : 'incorrect'}`;
          fb.innerHTML = `${esc(T(ok ? 'intro.right' : 'intro.wrong', null, ok ? 'Right!' : 'Not quite.'))}${expl ? `<div style="margin-top:8px">${esc(expl)}</div>` : ''}`;
          const slot = cardEl.querySelector('#exerciseFeedback');
          if (slot) slot.replaceWith(fb);
          else cardEl.appendChild(fb);
          const nb = cardEl.querySelector('#nextBtn');
          if (nb) nb.classList.add('show');
        },
        submitAttempt: (ok, resp) => {
          if (opts.onSpacer) opts.onSpacer(ex, ok, resp, Math.round(performance.now() - started));
        },
        nextExercise: () => {
          drill.skip(p);
          step();
        },
      });
      try {
        ER.dispatch(ex.exercise_type, ex, ex.content || {}, '');
      } catch (e) {
        console.error('[intro] spacer render failed', e);
        drill.skip(p);
        step();
      }
    }

    function renderEx(p, item) {
      const w = byId.get(p.sid);
      let answered = false;
      ER.init({
        cardEl,
        isAnswered: () => answered,
        setAnswered: (v) => {
          answered = v;
        },
        showFeedback: (ok, expl) => {
          const fb = document.createElement('div');
          fb.innerHTML = feedback(ok, false, w, 'noex') + (expl ? `<div style="margin-top:8px;font-size:14px">${esc(expl)}</div>` : '');
          const slot = cardEl.querySelector('#exerciseFeedback');
          if (slot) slot.replaceWith(fb);
          else cardEl.appendChild(fb);
          const nb = cardEl.querySelector('#nextBtn');
          if (nb) nb.classList.add('show');
        },
        submitAttempt: (ok, resp) => {
          finish({ correct: ok, idk: false, given: resp ? JSON.stringify(resp) : '', exercise_id: item.ex.exercise_id });
        },
        nextExercise: () => step(),
      });
      const head = stageBadge(w) + pips(p.sid);
      try {
        ER.dispatch(item.ex.exercise_type, item.ex, item.ex.content || {}, head);
      } catch (e) {
        console.error('[intro] exercise render failed', e);
        finish({ correct: false, idk: true });
        step();
      }
    }

    step();
  });
}

export const INTRO_STYLES = `
  .intro-pips { display:flex; gap:6px; margin: 0 0 14px; }
  .intro-pip { width:12px; height:12px; border-radius:50%; background: var(--border-default); }
  .intro-pip.on { background: var(--success); }
  .intro-idk { margin-top: 10px; padding-left: 0; color: var(--text-secondary); }
`;
