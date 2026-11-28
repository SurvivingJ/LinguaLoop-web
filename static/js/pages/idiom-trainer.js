// static/js/pages/idiom-trainer.js
// Idiom trainer (/idiom-trainer/zh, /idiom-trainer/ja). One client-rendered
// page; views switch on the URL hash:
//   #/              hub: what is due, what is being learned, the sets
//   #/set/<key>     every idiom of a set with its step
//   #/card/<id>     the card of one idiom: meaning, literal sense, the story
//                   behind it (when there is one), usage, look-alikes, examples
//   #/round         a round of twelve questions
// Content is static JSON (static/data/idioms/<lang>/, built by
// scripts/idiom_trainer.py); questions are built and judged here
// (js/idioms/*). Progress lives in localStorage and each finished round goes
// to the shared grammar-drill tracking (js/idioms/store.js).
import {
  MASTERED,
  STEPS,
  isDue,
  isMastered,
  isStarted,
  modeFor,
  newState,
  planRound,
  record,
  summary,
} from '../idioms/ladder.js';
import { build } from '../idioms/questions.js';
import { createStore } from '../idioms/store.js';
import { esc, parse, toHtml } from '../particles/markup.js';

const ROUND = 12;
const SPEED_MS = 7000;

function t(key, fallback, params) {
  const i18n = window.LinguaI18n;
  let text = fallback;
  if (i18n && typeof i18n.t === 'function') {
    const v = i18n.t(`idiom_trainer.${key}`, params);
    if (v && v !== `idiom_trainer.${key}`) text = v;
  }
  return params
    ? String(text).replace(/\{(\w+)\}/g, (m, k) => (k in params ? params[k] : m))
    : text;
}

const STEP_NAME = {
  1: ['step_meet', 'Meet'],
  2: ['step_recognise', 'Recognise'],
  3: ['step_complete', 'Complete'],
  4: ['step_judge', 'Right or wrong'],
  5: ['step_recall', 'Recall'],
  6: ['step_mastered', 'Mastered'],
};
const stepName = (l) => t(...STEP_NAME[Math.min(Math.max(l, 1), MASTERED)]);
const ASK = {
  meet: ['ask_meet', 'What does it mean here?'],
  recognise: ['ask_recognise', 'Which one fits?'],
  review: ['ask_review', 'Which one fits? Fast.'],
  complete: ['ask_complete', 'Complete it.'],
  judge: ['ask_judge', 'Is it used correctly here?'],
  recall: ['ask_recall', 'Which one would you say?'],
};

const app = {
  root: null,
  lang: 'zh',
  manifest: null,
  byId: new Map(),
  cards: new Map(), // id -> full card
  sets: new Map(), // set key -> promise of its file
  store: null,
  session: null,
  timers: [],
};

const $ = (sel) => app.root.querySelector(sel);
const $$ = (sel) => Array.from(app.root.querySelectorAll(sel));
const stateOf = (id) => app.store.state(id) || newState();
const readingsOn = () => app.store.setting('readings', true);

function later(fn, ms) {
  app.timers.push(setTimeout(fn, ms));
}
function clearTimers() {
  app.timers.forEach(clearTimeout);
  app.timers = [];
  if (app.session && app.session.raf) cancelAnimationFrame(app.session.raf);
}

function setView(html, { dock = '', title = '' } = {}) {
  clearTimers();
  app.root.innerHTML = `
<div class="ld-screen pd-screen it-screen">
  <div class="ld-stage pd-stage">${html}</div>
  <div class="ld-dock pd-dock"${dock ? '' : ' hidden'}>${dock}</div>
</div>`;
  const heading = document.querySelector('[data-it-title]');
  if (heading) heading.textContent = title || t('title', 'Idioms');
  app.root.querySelector('.pd-stage').scrollTop = 0;
}

// ---------------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------------
async function loadSet(key) {
  if (!app.sets.has(key)) {
    const info = app.manifest.sets.find((s) => s.key === key);
    // the set files sit beside the manifest
    const base = app.root.dataset.manifest.split('?')[0].replace(/[^/]*$/, '');
    const url = `${base}${key}.json?v=${info ? info.v : ''}`;
    const p = fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`idiom set ${key}: ${r.status}`);
        return r.json();
      })
      .then((body) => {
        body.cards.forEach((c) => app.cards.set(c.id, { ...c, set: key }));
        return body;
      })
      .catch((err) => {
        app.sets.delete(key);
        throw err;
      });
    app.sets.set(key, p);
  }
  return app.sets.get(key);
}

async function cardOf(id) {
  if (!app.cards.has(id)) await loadSet(app.byId.get(id).set);
  return app.cards.get(id);
}

/** A context sentence as HTML: the idiom marked, or left out as a blank. */
function sentenceHtml(s, blank) {
  const mark = (inner) =>
    blank ? '<span class="pd-blank is-focus">&nbsp;</span>' : `<b class="it-idiom">${inner}</b>`;
  if (app.lang === 'ja') {
    const p = parse(s);
    return toHtml(p, (slot) => mark(toHtml(parse(slot.raw[0]), (x) => esc(x.a))));
  }
  return esc(s).replace(/\{([^{}]*)\}/, (_m, inner) => mark(inner));
}

/** Prose that may carry furigana markup (Japanese cards). */
const prose = (text) =>
  app.lang === 'ja' ? toHtml(parse(String(text || '')), (slot) => esc(slot.a)) : esc(text || '');

const pips = (s) => {
  const level = isStarted(s) ? s.l : 0;
  let html = `<span class="pd-pips" role="img" aria-label="${esc(isStarted(s) ? stepName(level) : t('not_started', 'Not started'))}">`;
  for (let i = 1; i <= STEPS; i++)
    html += `<i class="${level > i ? 'is-done' : level === i ? 'is-now' : ''}"></i>`;
  return `${html}</span>`;
};

// ---------------------------------------------------------------------------
// Hub, set list, card
// ---------------------------------------------------------------------------
function chosenSets() {
  const all = app.manifest.sets.filter((s) => s.count).map((s) => s.key);
  const stored = app.store.setting('sets', null);
  const picked = stored ? stored.filter((k) => all.includes(k)) : all;
  return picked.length ? picked : all;
}

function renderHub() {
  const idioms = app.manifest.idioms;
  const sum = summary(idioms, app.store.states);
  const sets = chosenSets();
  const setRows = app.manifest.sets
    .filter((s) => s.count)
    .map((s) => {
      const own = idioms.filter((i) => i.set === s.key);
      const m = own.filter((i) => isMastered(app.store.state(i.id))).length;
      return `<div class="it-set">
        <button type="button" class="ld-chip it-set__on" data-set="${esc(s.key)}" aria-pressed="${sets.includes(s.key)}"><b lang="${app.lang}">${esc(s.title)}</b><small>${esc(s.en)}</small></button>
        <a class="it-set__go" href="#/set/${esc(s.key)}">${m} / ${s.count} <span aria-hidden="true">›</span></a>
      </div>`;
    })
    .join('');
  const next = sum.due
    ? t('hub_due', '{n} to review today', { n: sum.due })
    : sum.learning
      ? t('hub_learning', '{n} in progress', { n: sum.learning })
      : t('hub_fresh', 'Start with the most useful ones');
  setView(
    `<div class="pd-hub it-hub">
      <div class="ld-hero pd-hero"><span class="pd-hero__t">${esc(next)}</span>
        <span class="it-hero__sub">${esc(t('hub_sub', 'Each idiom: its story, six situations, five steps, then spaced reviews.'))}</span></div>
      <div class="ld-stats ld-stats--four pd-stats">
        <div class="ld-stat"><b class="ld-stat__n">${sum.mastered}</b><small>${esc(t('stat_mastered', 'Mastered'))}</small></div>
        <div class="ld-stat"><b class="ld-stat__n">${sum.learning}</b><small>${esc(t('stat_learning', 'Learning'))}</small></div>
        <div class="ld-stat"><b class="ld-stat__n">${sum.due}</b><small>${esc(t('stat_due', 'Due'))}</small></div>
        <div class="ld-stat"><b class="ld-stat__n">${sum.fresh}</b><small>${esc(t('stat_new', 'New'))}</small></div>
      </div>
      <h2 class="ld-sech">${esc(t('hub_sets', 'What to practise'))}</h2>
      <div class="it-sets">${setRows}</div>
      <label class="pd-furi"><input type="checkbox" id="itReadings"${readingsOn() ? ' checked' : ''}> ${esc(t('show_readings', 'Show readings under the options'))}</label>
    </div>`,
    {
      dock: `<a class="ld-btn ld-btn--block" href="#/round">${esc(t('start', 'Start a round'))}</a>`,
    }
  );
  $$('.it-set__on').forEach((btn) =>
    btn.addEventListener('click', () => {
      const now = new Set(chosenSets());
      if (now.has(btn.dataset.set) && now.size > 1) now.delete(btn.dataset.set);
      else now.add(btn.dataset.set);
      app.store.setSetting('sets', Array.from(now));
      btn.setAttribute('aria-pressed', String(now.has(btn.dataset.set)));
    })
  );
  $('#itReadings').addEventListener('change', (e) =>
    app.store.setSetting('readings', e.target.checked)
  );
}

function renderSet(key) {
  const info = app.manifest.sets.find((s) => s.key === key);
  if (!info) return go('#/');
  const rows = app.manifest.idioms
    .filter((i) => i.set === key)
    .map((i) => {
      const s = app.store.state(i.id);
      const tag = isMastered(s)
        ? `<span class="ld-tag ld-tag--ok">${esc(isDue(s) ? t('due', 'Due') : stepName(MASTERED))}</span>`
        : '';
      return `<a class="pd-skill it-row" href="#/card/${esc(i.id)}">
        <span class="pd-skill__t"><b lang="${app.lang}">${esc(i.t)}</b><small>${esc(i.mean)}</small></span>
        <span class="pd-skill__m">${i.story ? `<span class="it-book" title="${esc(t('has_story', 'Has a story'))}" aria-label="${esc(t('has_story', 'Has a story'))}">✎</span>` : ''}${tag}${pips(s)}</span></a>`;
    })
    .join('');
  setView(
    `<div class="it-list"><p class="ld-hint">${esc(t('set_hint', 'Tap an idiom to read its card. ✎ marks the ones with a story.'))}</p>
     <div class="ld-card pd-group">${rows}</div></div>`,
    { title: `${info.title} · ${info.en}` }
  );
}

function cardHtml(card) {
  const use = card.use || {};
  const near = (card.near || [])
    .map((n) => `<li><b lang="${app.lang}">${esc(n.t)}</b> ${prose(n.diff)}</li>`)
    .join('');
  const examples = card.ctx
    .slice(0, 3)
    .map(
      (c) =>
        `<div class="pd-example"><span lang="${app.lang}">${sentenceHtml(c.s, false)}</span><small>${esc(c.en)}</small></div>`
    )
    .join('');
  return `<article class="it-card">
    <div class="it-card__t" lang="${app.lang}">${esc(card.t)}</div>
    <div class="it-card__r" lang="${app.lang}">${esc(card.r)}</div>
    <p class="it-card__mean">${esc(card.mean)}</p>
    <h3>${esc(t('card_lit', 'Literally'))}</h3><p>${esc(card.lit)}</p>
    ${
      card.story
        ? `<h3>${esc(t('card_story', 'The story behind it'))}</h3><p class="it-card__story">${esc(card.story.text)}</p>
           <p class="it-card__src">${esc(t('card_source', 'Traditional account. Source:'))} <span lang="${app.lang}">${esc(card.story.source)}</span></p>`
        : ''
    }
    <h3>${esc(t('card_use', 'How it is used'))}</h3>
    <p><span class="ld-tag">${esc(use.reg || '')}</span> <span class="ld-tag">${esc(use.tone || '')}</span></p>
    <p>${prose(use.how)}</p>
    ${near ? `<h3>${esc(t('card_near', 'Do not confuse with'))}</h3><ul class="it-near">${near}</ul>` : ''}
    <h3>${esc(t('card_examples', 'In context'))}</h3>${examples}
  </article>`;
}

async function renderCard(id) {
  if (!app.byId.has(id)) return go('#/');
  setView(`<p class="drill-msg">${esc(t('loading', 'Loading…'))}</p>`);
  const card = await cardOf(id);
  setView(cardHtml(card), {
    title: app.manifest.sets.find((s) => s.key === card.set).title,
    dock: `<a class="ld-btn ld-btn--ghost ld-btn--block" href="#/set/${esc(card.set)}">${esc(t('back_list', 'Back to the list'))}</a>`,
  });
}

// ---------------------------------------------------------------------------
// Round
// ---------------------------------------------------------------------------
async function startRound() {
  setView(`<p class="drill-msg">${esc(t('loading', 'Loading…'))}</p>`);
  const queue = planRound(app.manifest.idioms, app.store.states, {
    size: ROUND,
    sets: chosenSets(),
  });
  if (!queue.length) {
    setView(`<p class="ld-note">${esc(t('empty', 'No idioms are available yet.'))}</p>`);
    return;
  }
  await Promise.all([...new Set(queue.map((id) => app.byId.get(id).set))].map(loadSet));
  app.session = {
    queue,
    at: 0,
    done: 0,
    right: 0,
    events: [],
    met: new Set(),
    seen: new Map(),
    retried: new Set(),
  };
  nextQuestion();
}

function shell(q) {
  const ses = app.session;
  setView(
    `<div class="pd-drill it-drill">
      <div class="pd-strip">
        <div class="pd-strip__row">
          <span class="ld-tag ld-tag--brand">${esc(stepName(q.level))}</span>
          <span class="pd-strip__skill"></span>
          <span class="pd-strip__n">${Math.min(ses.done, ses.queue.length)} / ${ses.queue.length}</span>
        </div>
        <div class="ld-bar pd-bar"><i style="width:${(ses.done / ses.queue.length) * 100}%"></i></div>
        <div class="pd-clock" id="itClock"${q.mode === 'review' ? '' : ' hidden'}><i></i></div>
      </div>
      <p class="pd-ask">${esc(t(...ASK[q.mode]))}</p>
      <div class="pd-sentence it-prompt" id="itPrompt" lang="${app.lang}"></div>
      <p class="pd-en" id="itEn"></p>
      <div class="pd-answer" id="itAnswer"></div>
    </div>`,
    {
      title: t('round', 'Round'),
      dock: `<div class="pd-feedback" id="itFeedback" role="status" aria-live="polite" hidden></div>
        <button type="button" class="ld-btn ld-btn--block" id="itNext" hidden>${esc(t('continue', 'Continue'))}</button>`,
    }
  );
  $('#itNext').addEventListener('click', advance);
}

function nextQuestion() {
  const ses = app.session;
  if (ses.at >= ses.queue.length) return finishRound();
  const id = ses.queue[ses.at];
  const card = app.cards.get(id);
  const s = stateOf(id);
  // A new idiom is read before it is asked about.
  if (!isStarted(s) && !ses.met.has(id)) {
    ses.met.add(id);
    setView(cardHtml(card), {
      title: t('new_idiom', 'New idiom'),
      dock: `<button type="button" class="ld-btn ld-btn--block" id="itGotIt">${esc(t('got_it', 'Got it: ask me'))}</button>`,
    });
    $('#itGotIt').addEventListener('click', nextQuestion);
    $('#itGotIt').focus();
    return;
  }
  const level = Math.min(s.l, MASTERED);
  const mode = modeFor(level);
  const seen = ses.seen.get(id) || [];
  const q = build(card, mode, app.manifest.idioms, Math.random, seen);
  if (q.ctx != null) ses.seen.set(id, [...seen, q.ctx]);
  Object.assign(q, { id, level, answered: false, started: performance.now() });
  ses.q = q;
  shell(q);
  drawQuestion(q);
}

function optionLabel(q, o) {
  if (q.judge)
    return o === 'right'
      ? esc(t('opt_right', 'Used correctly'))
      : esc(t('opt_wrong', 'Wrong here'));
  if (q.mode === 'meet') return esc(o);
  const row = q.mode === 'complete' ? null : app.manifest.idioms.find((i) => i.t === o);
  const reading = row && readingsOn() ? `<small class="it-opt__r">${esc(row.r)}</small>` : '';
  return `<span lang="${app.lang}">${esc(o)}</span>${reading}`;
}

function drawQuestion(q) {
  const p = q.prompt;
  const prompt = $('#itPrompt');
  if (p.sentence) prompt.innerHTML = sentenceHtml(p.sentence, p.blank);
  else if (p.stem)
    prompt.innerHTML = `<span class="it-stem">${esc(p.stem)}<span class="pd-blank is-focus">&nbsp;</span></span>`;
  else prompt.innerHTML = '';
  $('#itEn').textContent = p.text || p.en || '';
  const wide = q.mode === 'meet' || q.options.some((o) => String(o).length > 5);
  $('#itAnswer').innerHTML = `<div class="pd-options${wide ? ' pd-options--wide' : ''}">${q.options
    .map(
      (o, i) =>
        `<button type="button" class="ld-opt pd-opt" data-i="${i}"><span class="ld-opt__key" aria-hidden="true">${i + 1}</span><span class="pd-opt__t is-long">${optionLabel(q, o)}</span></button>`
    )
    .join('')}</div>`;
  $$('.pd-opt').forEach((btn) =>
    btn.addEventListener('click', () => choose(Number(btn.dataset.i)))
  );
  if (q.mode === 'review') {
    const bar = $('#itClock i');
    const tick = () => {
      if (q.answered) return;
      const left = 1 - (performance.now() - q.started) / SPEED_MS;
      bar.style.transform = `scaleX(${Math.max(0, left)})`;
      if (left <= 0) return choose(-1);
      app.session.raf = requestAnimationFrame(tick);
    };
    app.session.raf = requestAnimationFrame(tick);
  }
}

function choose(i) {
  const ses = app.session;
  const q = ses && ses.q;
  if (!q || q.answered || i >= q.options.length) return;
  q.answered = true;
  const correct = i === q.answer;
  const ms = Math.round(performance.now() - q.started);
  $$('.pd-opt').forEach((btn, k) => {
    btn.disabled = true;
    if (k === q.answer) btn.classList.add('is-correct');
    else if (k === i) btn.classList.add('is-wrong');
  });
  const { state, event } = record(stateOf(q.id), correct);
  app.store.answer(q.id, state, { correct, ms });
  ses.done += 1;
  if (correct) ses.right += 1;
  if (event) ses.events.push({ id: q.id, event, level: state.l });
  // a missed idiom comes back three questions later, once
  if (!correct && !ses.retried.has(q.id)) {
    ses.retried.add(q.id);
    const at = Math.min(ses.at + 3, ses.queue.length);
    ses.queue.splice(at, 0, q.id);
  }
  // the sentence is shown whole once answered
  if (q.prompt.sentence) $('#itPrompt').innerHTML = sentenceHtml(q.prompt.sentence, false);
  else if (q.prompt.stem) $('#itPrompt').innerHTML = `<b class="it-idiom">${esc(q.card.t)}</b>`;
  const fb = $('#itFeedback');
  fb.hidden = false;
  fb.className = `pd-feedback ${correct ? 'is-ok' : 'is-bad'}`;
  const move =
    event === 'up' || event === 'mastered'
      ? `<span class="ld-tag ld-tag--ok">↑ ${esc(stepName(state.l))}</span>`
      : event === 'down'
        ? `<span class="ld-tag ld-tag--warn">↓ ${esc(stepName(state.l))}</span>`
        : '';
  fb.innerHTML = `<b>${esc(correct ? t('fb_right', 'Right') : i < 0 ? t('fb_time', 'Too slow') : t('fb_wrong', 'Not quite'))}</b> ${move}
    <span class="pd-feedback__ans" lang="${app.lang}"><b>${esc(q.card.t)}</b> <small>${esc(q.card.r)}</small></span>
    <span class="pd-feedback__why">${esc(q.card.mean)}${q.after.why ? ` — ${esc(q.after.why)}` : ''}</span>
    ${q.after.en && q.after.en !== q.card.mean ? `<span class="pd-feedback__why">${esc(q.after.en)}</span>` : ''}
    ${correct ? '' : `<button type="button" class="ld-link pd-feedback__guide" id="itOpenCard">${esc(t('fb_card', 'Read its card again'))}</button>`}`;
  const link = $('#itOpenCard');
  if (link) link.addEventListener('click', () => openSheet(cardHtml(q.card)));
  if (correct) later(advance, event ? 1500 : 1000);
  else {
    const next = $('#itNext');
    next.hidden = false;
    next.focus();
  }
}

function openSheet(html) {
  const sheet = document.createElement('div');
  sheet.className = 'pd-sheet';
  sheet.innerHTML = `<div class="pd-sheet__card" role="dialog" aria-modal="true">
    <button type="button" class="ld-btn ld-btn--ghost ld-btn--sm pd-sheet__x">${esc(t('close', 'Close'))}</button>${html}</div>`;
  sheet.addEventListener('click', (e) => {
    if (e.target === sheet || e.target.closest('.pd-sheet__x')) sheet.remove();
  });
  document.body.appendChild(sheet);
  sheet.querySelector('.pd-sheet__x').focus();
}

function advance() {
  const ses = app.session;
  if (!ses || !ses.q || !ses.q.answered) return;
  ses.at += 1;
  nextQuestion();
}

function finishRound() {
  const ses = app.session;
  app.store.endRound();
  const pct = ses.done ? Math.round((ses.right / ses.done) * 100) : 0;
  const events = ses.events
    .map((e) => {
      const i = app.byId.get(e.id);
      return `<li class="${e.event === 'down' ? 'is-down' : 'is-up'}"><span lang="${app.lang}">${esc(i.t)}</span><b>${e.event === 'down' ? '↓' : e.event === 'kept' ? '✓' : '↑'} ${esc(stepName(e.level))}</b></li>`;
    })
    .join('');
  setView(
    `<div class="pd-results">
      <div class="pd-results__pct">${pct}<small>%</small></div>
      <p class="ld-hint">${esc(t('res_line', '{r} of {n} right', { r: ses.right, n: ses.done }))}</p>
      ${events ? `<ul class="pd-events">${events}</ul>` : `<p class="ld-hint">${esc(t('res_none', 'Two right answers in a row move an idiom up a step.'))}</p>`}
    </div>`,
    {
      title: t('round', 'Round'),
      dock: `<div class="ld-row"><a class="ld-btn ld-btn--ghost" href="#/">${esc(t('done', 'Done'))}</a>
        <button type="button" class="ld-btn" id="itAgain">${esc(t('next_round', 'Next round'))}</button></div>`,
    }
  );
  app.session = null;
  $('#itAgain').addEventListener('click', startRound);
  $('#itAgain').focus();
}

// ---------------------------------------------------------------------------
// Routing and start-up
// ---------------------------------------------------------------------------
function go(hash) {
  if (window.location.hash === hash) route();
  else window.location.hash = hash;
}

async function route() {
  const [view, arg] = window.location.hash.replace(/^#\/?/, '').split('/');
  if (app.session) app.store.endRound();
  app.session = null;
  try {
    if (view === 'round') await startRound();
    else if (view === 'set' && arg) renderSet(decodeURIComponent(arg));
    else if (view === 'card' && arg) await renderCard(decodeURIComponent(arg));
    else renderHub();
  } catch (err) {
    console.error('idiom trainer:', err);
    setView(`<p class="ld-note ld-note--bad">${esc(t('error_load', 'Could not load the idioms. Check your connection and try again.'))}</p>
      <p><a class="ld-btn ld-btn--ghost" href="#/">${esc(t('back', 'Back'))}</a></p>`);
  }
}

function onKeydown(e) {
  if (e.metaKey || e.ctrlKey || e.altKey || !app.session || !app.session.q) return;
  if (/^[1-6]$/.test(e.key) && !app.session.q.answered) choose(Number(e.key) - 1);
}

export async function mount(root) {
  app.root = root;
  app.lang = root.dataset.lang;
  app.store = createStore({ lang: app.lang, languageId: Number(root.dataset.languageId) });
  root.innerHTML = `<p class="drill-msg">${esc(t('loading', 'Loading…'))}</p>`;
  try {
    const [resp] = await Promise.all([fetch(root.dataset.manifest), app.store.pull()]);
    if (!resp.ok) throw new Error(`manifest ${resp.status}`);
    app.manifest = await resp.json();
    app.manifest.idioms.forEach((i) => app.byId.set(i.id, i));
  } catch (err) {
    console.error('idiom trainer:', err);
    root.innerHTML = `<p class="ld-note ld-note--bad">${esc(t('error_load', 'Could not load the idioms. Check your connection and try again.'))}</p>`;
    return;
  }
  window.addEventListener('hashchange', route);
  document.addEventListener('keydown', onKeydown);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') app.store.endRound();
  });
  route();
}

const host = document.getElementById('idiomTrainerRoot');
if (host) {
  const start = () => mount(host);
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start);
}
