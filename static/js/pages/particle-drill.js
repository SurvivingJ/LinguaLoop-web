// /particle-drill: the Japanese particle ladder.
//
// One page, four views switched by the URL hash:
//   #/                 hub: next step, daily mix, every stage / particle / skill
//   #/skill/<id>       the skill's guide and its place on the ladder
//   #/drill/<id>       endless drill of one skill   (#/mix: a mixed session)
// /conjugation-drill mounts the same script with data-home="conj":
//   #/                 conjugation setup: forms, word pools (the learner's own
//                      known words and the level lists), guides
//   #/drill            endless conjugation rounds
//
// Content comes from /api/particle-drill (static files, cached); exercises are
// built and judged here (js/particles/*), so answering never waits on a
// request. Progress lives in localStorage and is mirrored to the server.
import {
  ADJ_FORMS,
  FORMS,
  VERB_FORMS,
  acceptedAnswers,
  conjugate,
  distractors,
  formsFor,
} from '../particles/conjugate.js';
import {
  Deck,
  build,
  gradeChoice,
  gradeFill,
  gradeFixTap,
  gradeTyped,
  parsed,
  shuffle,
} from '../particles/exercises.js';
import { answerMatches, romajiToKana } from '../particles/kana.js';
import { esc, parse, toHtml } from '../particles/markup.js';
import * as M from '../particles/mastery.js';
import { createStore } from '../particles/store.js';

const API = '/api/particle-drill';
const LANGUAGE_ID = 3;
const ROUND = 10;
const MIX_ROUND = 20;
const CONJ_MAX_LEVEL = 3; // choose -> type -> speed
const MODES = ['auto', 'choose', 'type', 'fill', 'fix', 'speed'];
const MODE_LEVEL = { meet: 1, choose: 2, type: 3, fill: 4, fix: 5, speed: 6 };

/** Translate with an English fallback ({name} params filled in either way). */
function t(key, fallback, params) {
  const i18n = window.LinguaI18n;
  let text = fallback;
  if (i18n && typeof i18n.t === 'function') {
    const v = i18n.t(`particle_drill.${key}`, params);
    if (v && v !== `particle_drill.${key}`) text = v;
  }
  return params
    ? String(text).replace(/\{(\w+)\}/g, (m, k) => (k in params ? params[k] : m))
    : text;
}

const LEVEL_NAME = {
  1: ['level_meet', 'Meet'],
  2: ['level_choose', 'Choose'],
  3: ['level_type', 'Type'],
  4: ['level_fill', 'Fill all'],
  5: ['level_fix', 'Fix'],
  6: ['level_speed', 'Speed'],
  7: ['level_instant', 'Instant'],
};
const levelName = (l) => t(...(LEVEL_NAME[Math.min(Math.max(l, 1), 7)] || LEVEL_NAME[1]));
const MODE_NAME = {
  auto: ['mode_auto', 'Auto'],
  meet: ['level_meet', 'Meet'],
  choose: ['level_choose', 'Choose'],
  type: ['level_type', 'Type'],
  fill: ['level_fill', 'Fill all'],
  fix: ['level_fix', 'Fix'],
  speed: ['level_speed', 'Speed'],
};
const modeName = (m) => t(...MODE_NAME[m]);
const INSTRUCTION = {
  meet: ['ask_choose', 'Choose the particle.'],
  choose: ['ask_choose', 'Choose the particle.'],
  speed: ['ask_speed', 'Choose. Fast.'],
  type: ['ask_type', 'Type the particle.'],
  fill: ['ask_fill', 'Fill in every particle.'],
  fix: ['ask_fix', 'One particle is wrong. Tap it.'],
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const app = {
  root: null,
  store: null,
  catalog: null,
  skills: new Map(), // id -> catalog skill
  bundles: new Map(), // id -> promise of the skill payload
  conj: null, // conjugation payload
  myWords: null, // the learner's own verbs and adjectives
  session: null,
  timers: [],
};

async function getJson(path) {
  const resp = await window.authFetch(
    `${API}${path}${path.includes('?') ? '&' : '?'}language_id=${LANGUAGE_ID}`
  );
  if (!resp.ok) throw new Error(`particle drill request failed: ${resp.status}`);
  return resp.json();
}

function loadSkill(id) {
  if (!app.bundles.has(id)) {
    const p = getJson(`/skill/${encodeURIComponent(id)}`).catch((err) => {
      app.bundles.delete(id);
      throw err;
    });
    app.bundles.set(id, p);
  }
  return app.bundles.get(id);
}

async function loadConj() {
  if (!app.conj) app.conj = await getJson('/conjugation');
  return app.conj;
}

/** The learner's own verbs and adjectives; an empty pool when the request fails. */
async function loadMyWords() {
  if (!app.myWords) {
    try {
      app.myWords = await getJson('/conjugation/words');
    } catch (err) {
      console.error('particle drill: own words unavailable', err);
      return { words: [], verbs: 0, adjectives: 0, skipped: 0 };
    }
  }
  return app.myWords;
}

const MIN_OWN_WORDS = 8; // below this the level lists are switched on as well
const isConjHome = () => !!app.root && app.root.dataset.home === 'conj';
const conjHome = () => (isConjHome() ? '#/' : '#/conj');
const conjDrill = () => (isConjHome() ? '#/drill' : '#/conj/drill');

/** Chosen word pools: 'mine' and / or JLPT levels 5, 4, 3. */
function conjPools(mine) {
  const stored = app.store.setting('conjLevels', null);
  if (stored) return new Set(stored);
  return new Set(mine.words.length >= MIN_OWN_WORDS ? ['mine'] : ['mine', 5, 4]);
}

const stateOf = (id) => app.store.skill(id) || M.newState();
const furiganaOn = () => app.store.setting('furi', true);

function later(fn, ms) {
  const id = setTimeout(fn, ms);
  app.timers.push(id);
  return id;
}

function clearTimers() {
  app.timers.forEach(clearTimeout);
  app.timers = [];
  if (app.session && app.session.raf) cancelAnimationFrame(app.session.raf);
}

// ---------------------------------------------------------------------------
// Small render helpers
// ---------------------------------------------------------------------------
function pips(level, max = M.MAX_LEVEL) {
  let html = `<span class="pd-pips" role="img" aria-label="${esc(t('level_of', 'Level {n} of {max}', { n: Math.min(level, max), max }))}">`;
  for (let i = 1; i <= max; i++)
    html += `<i class="${level > i ? 'is-done' : level === i ? 'is-now' : ''}"></i>`;
  return `${html}</span>`;
}

const jlpt = (lv) => `<span class="ld-tag pd-lv">N${lv}</span>`;

/** A particle or word in the markup (に対[たい]して) as HTML with furigana. */
const rubyHtml = (marked) => toHtml(parse(marked), (slot) => esc(slot.a));
/** Guide prose: plain text in which 漢字[かな] becomes furigana. */
const proseHtml = (text) => rubyHtml(String(text || ''));
/** The same for an answer of an exercise, looked up by its displayed text. */
const rb = (ex, shown) => rubyHtml((ex && ex.ruby && ex.ruby[shown]) || shown || '');

/** A marked-up sentence as HTML; `slotHtml` renders the particle slots. */
function sentenceHtml(jp, slotHtml) {
  const p = typeof jp === 'string' ? parse(jp) : jp;
  return toHtml(p, slotHtml || ((slot) => `<b class="pd-p">${rubyHtml(slot.raw[0])}</b>`));
}

function setView(html, { dock = '', title = '' } = {}) {
  clearTimers();
  app.root.innerHTML = `
<div class="ld-screen pd-screen${furiganaOn() ? '' : ' pd-nofuri'}">
  <div class="ld-stage pd-stage">${html}</div>
  <div class="ld-dock pd-dock"${dock ? '' : ' hidden'}>${dock}</div>
</div>`;
  const heading = document.querySelector('[data-pd-title]');
  if (heading) heading.textContent = title || t('title', 'Particles');
  app.root.querySelector('.pd-stage').scrollTop = 0;
}

const $ = (sel) => app.root.querySelector(sel);
const $$ = (sel) => Array.from(app.root.querySelectorAll(sel));

// ---------------------------------------------------------------------------
// Hub
// ---------------------------------------------------------------------------
function renderHub() {
  const { catalog } = app;
  const states = app.store.doc.skills;
  const all = catalog.skills;
  const usable = all.filter((k) => k.items + k.packs > 0);
  const mastered = usable.filter((k) => M.isMastered(states[k.id])).length;
  const started = usable.filter((k) => M.isStarted(states[k.id])).length;
  const due = usable.filter((k) => M.isDue(states[k.id])).length;
  const next = M.nextUp(all, states);
  const answers = Object.values(states).reduce((n, s) => n + (s.n || 0), 0);

  const hero = next
    ? `<a class="ld-hero pd-hero" href="#/skill/${esc(next.id)}">
        <span class="ld-eyebrow">${esc(M.isStarted(states[next.id]) ? t('hub_continue', 'Continue') : t('hub_next', 'Next up'))}</span>
        <span class="pd-hero__p" lang="ja">${esc(next.p)}</span>
        <span class="pd-hero__t">${esc(next.title)}</span>
        <span class="pd-hero__m">${pips(stateOf(next.id).l)} ${esc(levelName(stateOf(next.id).l))}</span>
      </a>`
    : `<div class="ld-hero pd-hero"><span class="pd-hero__t">${esc(t('hub_all_done', 'Every skill is at Instant. Keep them there with the daily mix.'))}</span></div>`;

  const stages = catalog.stages
    .map((stage, si) => {
      const stageSkills = all.filter((k) => k.stage === stage.id && k.items + k.packs > 0);
      if (!stageSkills.length) return '';
      const done = stageSkills.filter((k) => M.isMastered(states[k.id])).length;
      const open = next ? next.stage === stage.id : si === 0;
      const groups = stage.groups
        .map((g) => {
          const rows = g.skills
            .map((id) => app.skills.get(id))
            .filter((k) => k && k.items + k.packs > 0)
            .map((k) => {
              const s = states[k.id];
              const tag = M.isDue(s)
                ? `<span class="ld-tag ld-tag--due">${esc(t('due', 'Due'))}</span>`
                : M.isMastered(s)
                  ? `<span class="ld-tag ld-tag--ok">${esc(levelName(7))}</span>`
                  : '';
              return `<a class="pd-skill" href="#/skill/${esc(k.id)}">
                <span class="pd-skill__t">${esc(k.title)}</span>
                <span class="pd-skill__m">${tag}${jlpt(k.lv)}${pips(s ? s.l : 0)}</span>
              </a>`;
            })
            .join('');
          if (!rows) return '';
          return `<section class="ld-card pd-group">
            <h3 class="pd-group__h"><span class="pd-group__p" lang="ja">${esc(g.p)}</span><span class="pd-group__n">${esc(g.name)}</span></h3>
            ${rows}
          </section>`;
        })
        .join('');
      return `<details class="pd-stagebox"${open ? ' open' : ''}>
        <summary>
          <span class="pd-stagebox__n">${si + 1}</span>
          <span class="pd-stagebox__t"><b>${esc(stage.title)}</b><small>${esc(stage.blurb)}</small></span>
          <span class="pd-stagebox__c">${done}/${stageSkills.length}</span>
        </summary>
        <div class="pd-groups">${groups}</div>
      </details>`;
    })
    .join('');

  setView(
    `<div class="pd-hub">
      ${hero}
      <div class="ld-stats ld-stats--four pd-stats">
        <div class="ld-stat"><b class="ld-stat__n">${mastered}</b><small>${esc(t('stat_instant', 'Instant'))}</small></div>
        <div class="ld-stat"><b class="ld-stat__n">${started - mastered}</b><small>${esc(t('stat_learning', 'Learning'))}</small></div>
        <div class="ld-stat"><b class="ld-stat__n">${due}</b><small>${esc(t('stat_due', 'Due'))}</small></div>
        <div class="ld-stat"><b class="ld-stat__n">${answers}</b><small>${esc(t('stat_answers', 'Answers'))}</small></div>
      </div>
      <div class="pd-actions">
        <a class="ld-btn" href="#/mix">${esc(t('hub_mix', 'Daily mix'))}<small>${esc(t('hub_mix_sub', 'due reviews and what you are learning'))}</small></a>
        <a class="ld-btn ld-btn--ghost" href="/conjugation-drill">${esc(t('hub_conj', 'Conjugation gym'))}<small>${esc(t('hub_conj_sub', 'て, ない, potential, passive …'))}</small></a>
      </div>
      <label class="pd-furi"><input type="checkbox" id="pdFuri"${furiganaOn() ? ' checked' : ''}> ${esc(t('furigana', 'Show furigana'))}</label>
      <h2 class="ld-sech">${esc(t('hub_path', 'The ladder'))}</h2>
      <p class="ld-hint pd-ladderhint">${esc(t('hub_ladder_hint', 'Each skill climbs six rungs: Meet, Choose, Type, Fill all, Fix, Speed. Five answers at 80% move you up; Speed makes it instant.'))}</p>
      ${stages || `<p class="ld-note">${esc(t('empty', 'No particle exercises are available yet.'))}</p>`}
    </div>`
  );
  $('#pdFuri').addEventListener('change', (e) => {
    app.store.setSetting('furi', e.target.checked);
    $('.pd-screen').classList.toggle('pd-nofuri', !e.target.checked);
  });
}

// ---------------------------------------------------------------------------
// Guide
// ---------------------------------------------------------------------------
function guideHtml(guide) {
  if (!guide)
    return `<p class="ld-note">${esc(t('guide_missing', 'The guide for this skill is not written yet. The drill explains each answer.'))}</p>`;
  const paras = String(guide.explain || '')
    .split(/\n\s*\n/)
    .map((p) => `<p>${proseHtml(p.trim())}</p>`)
    .join('');
  const list = (items, fn) => (items && items.length ? items.map(fn).join('') : '');
  return `
    <p class="pd-guide__rule">${proseHtml(guide.rule)}</p>
    ${paras}
    ${list(guide.patterns, (p) => `<div class="pd-pattern" lang="ja">${esc(p)}</div>`)}
    ${guide.table ? `<div class="pd-tablewrap"><table class="pd-table">${guide.table.map((row, i) => `<tr>${row.map((c) => (i ? `<td lang="ja">${sentenceHtml(c)}</td>` : `<th>${esc(c)}</th>`)).join('')}</tr>`).join('')}</table></div>` : ''}
    <h3 class="ld-sech">${esc(t('guide_examples', 'Examples'))}</h3>
    <ul class="pd-examples">${list(guide.examples, (e) => `<li><span class="pd-jp" lang="ja">${sentenceHtml(e.jp)}</span><span class="pd-en">${esc(e.en)}</span></li>`)}</ul>
    ${guide.contrast && guide.contrast.length ? `<h3 class="ld-sech">${esc(t('guide_contrast', 'Not to be confused with'))}</h3>${list(guide.contrast, (c) => `<div class="pd-contrast"><b class="pd-p" lang="ja">${esc(c.vs)}</b><span>${proseHtml(c.note)}</span></div>`)}` : ''}
    ${guide.mistakes && guide.mistakes.length ? `<h3 class="ld-sech">${esc(t('guide_mistakes', 'Common mistakes'))}</h3>${list(guide.mistakes, (m) => `<div class="pd-mistake"><div class="pd-bad" lang="ja">✕ ${sentenceHtml(m.bad)}</div><div class="pd-good" lang="ja">✓ ${sentenceHtml(m.good)}</div><small>${proseHtml(m.note)}</small></div>`)}` : ''}
    ${guide.tip ? `<p class="ld-note ld-note--ok pd-tip"><b>${esc(t('guide_tip', 'Quick test'))}</b> ${proseHtml(guide.tip)}</p>` : ''}
    ${guide.intro ? `<h3 class="ld-sech">${esc(t('guide_big_picture', 'The particle as a whole'))}</h3><p class="pd-guide__intro">${esc(guide.intro)}</p>` : ''}`;
}

async function renderSkill(id) {
  const skill = app.skills.get(id);
  if (!skill) return go('#/');
  setView(`<p class="drill-msg">${esc(t('loading', 'Loading…'))}</p>`, { title: skill.p });
  const bundle = await loadSkill(id);
  const s = stateOf(id);
  const mode = app.store.setting('mode', 'auto');
  const size = bundle.items.length;
  setView(
    `<article class="pd-guide">
      <header class="pd-guide__head">
        <span class="pd-guide__p" lang="ja">${esc(skill.p)}</span>
        <div><h2>${esc(skill.title)}</h2>
        <div class="pd-guide__meta">${jlpt(skill.lv)}${pips(s.l)}<span>${esc(levelName(s.l))}</span>${s.n ? `<span>${Math.round((s.c / s.n) * 100)}% · ${s.n}</span>` : ''}${s.rt ? `<span>${(s.rt / 1000).toFixed(1)}s</span>` : ''}</div></div>
      </header>
      ${guideHtml(bundle.guide)}
      <p class="ld-hint">${esc(t('skill_supply', '{n} written exercises{inf}', { n: size, inf: bundle.packs.length ? t('skill_supply_inf', ' and endless generated ones') : '' }))}</p>
    </article>`,
    {
      title: skill.p,
      dock: `
      <div class="ld-seg pd-modes" role="group" aria-label="${esc(t('mode', 'Exercise type'))}">
        ${MODES.map((m) => `<button type="button" data-mode="${m}" aria-pressed="${m === mode}" class="${m === mode ? 'active' : ''}">${esc(modeName(m))}</button>`).join('')}
      </div>
      <a class="ld-btn ld-btn--block" id="pdStart" href="#/drill/${esc(id)}">${esc(s.n ? t('drill_continue', 'Drill') : t('drill_start', 'Start drilling'))}</a>`,
    }
  );
  $$('.pd-modes button').forEach((btn) =>
    btn.addEventListener('click', () => {
      app.store.setSetting('mode', btn.dataset.mode);
      $$('.pd-modes button').forEach((b) => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-pressed', String(b === btn));
      });
    })
  );
}

function openGuideSheet(html) {
  const sheet = document.createElement('div');
  sheet.className = 'pd-sheet';
  sheet.innerHTML = `<div class="pd-sheet__card${furiganaOn() ? '' : ' pd-nofuri'}" role="dialog" aria-modal="true">
    <button type="button" class="ld-btn ld-btn--ghost ld-btn--sm pd-sheet__x">${esc(t('close', 'Close'))}</button>
    <article class="pd-guide">${html}</article></div>`;
  const close = () => sheet.remove();
  sheet.addEventListener('click', (e) => {
    if (e.target === sheet || e.target.closest('.pd-sheet__x')) close();
  });
  document.body.appendChild(sheet);
  sheet.querySelector('.pd-sheet__x').focus();
}

// ---------------------------------------------------------------------------
// Drill session (one skill, or a mix)
// ---------------------------------------------------------------------------
async function startDrill(skillIds, { mix = false } = {}) {
  setView(`<p class="drill-msg">${esc(t('loading', 'Loading…'))}</p>`);
  const bundles = (await Promise.all(skillIds.map((id) => loadSkill(id).catch(() => null)))).filter(
    (b) => b && b.items.length + b.packs.length > 0
  );
  if (!bundles.length) {
    setView(
      `<p class="ld-note">${esc(t('empty', 'No particle exercises are available yet.'))}</p>`
    );
    return;
  }
  const decks = new Map();
  bundles.forEach((b) => {
    decks.set(
      b.skill.id,
      new Deck({ items: b.items, packs: b.packs, missed: stateOf(b.skill.id).miss || [] })
    );
  });
  app.session = {
    kind: 'particles',
    mix,
    bundles: new Map(bundles.map((b) => [b.skill.id, b])),
    order: bundles.map((b) => b.skill.id),
    decks,
    mode: mix ? 'auto' : app.store.setting('mode', 'auto'),
    roundSize: mix ? MIX_ROUND : ROUND,
    total: 0,
  };
  newRound();
}

function newRound() {
  const ses = app.session;
  Object.assign(ses, { done: 0, right: 0, streak: 0, times: [], events: [], retry: [], asked: 0 });
  renderDrillShell();
  nextQuestion();
}

function renderDrillShell() {
  const ses = app.session;
  const only = !ses.mix && ses.kind === 'particles' ? ses.bundles.get(ses.order[0]).skill : null;
  setView(
    `<div class="pd-drill">
      <div class="pd-strip">
        <div class="pd-strip__row">
          <span class="ld-tag ld-tag--brand" id="pdBadge"></span>
          <span class="pd-strip__skill" id="pdSkillName"></span>
          <span class="pd-strip__n"><span id="pdCount">0</span> / ${ses.roundSize}</span>
        </div>
        <div class="ld-bar pd-bar"><i id="pdFill"></i></div>
        <div class="pd-clock" id="pdClock" hidden><i></i></div>
      </div>
      <p class="pd-ask" id="pdAsk"></p>
      <div class="pd-sentence" id="pdSentence" lang="ja"></div>
      <p class="pd-en" id="pdEn"></p>
      <div class="pd-answer" id="pdAnswer"></div>
    </div>`,
    {
      title: only
        ? only.p
        : ses.kind === 'conj'
          ? t('conj_title', 'Conjugation')
          : t('hub_mix', 'Daily mix'),
      dock: `
      <div class="pd-feedback" id="pdFeedback" role="status" aria-live="polite" hidden></div>
      <button type="button" class="ld-btn ld-btn--block" id="pdCheck" hidden>${esc(t('check', 'Check'))}</button>
      <button type="button" class="ld-btn ld-btn--block" id="pdNext" hidden>${esc(t('continue', 'Continue'))}</button>`,
    }
  );
  $('#pdCheck').addEventListener('click', () => app.session.onCheck && app.session.onCheck());
  $('#pdNext').addEventListener('click', advance);
}

function pickSkill(ses) {
  if (ses.order.length === 1) return ses.order[0];
  // Weakest skills come up more often; never the same skill three times running.
  const weights = ses.order.map((id) => {
    const s = stateOf(id);
    return 1 + (1 - (s.e == null ? 0.5 : s.e)) * 2 + (M.isDue(s) ? 1 : 0);
  });
  let r = Math.random() * weights.reduce((a, b) => a + b, 0);
  for (let i = 0; i < weights.length; i++) {
    r -= weights[i];
    if (r <= 0) return ses.order[i];
  }
  return ses.order[0];
}

function nextQuestion() {
  const ses = app.session;
  let q;
  // A missed item comes back three questions later, and before the round ends.
  const roundOver = ses.done >= ses.roundSize;
  if (roundOver && !ses.retry.length) return finishRound();
  const retryIndex = roundOver ? 0 : ses.retry.findIndex((r) => r.at <= ses.asked);
  if (retryIndex >= 0) {
    q = ses.retry.splice(retryIndex, 1)[0].q;
    q.retry = true;
  } else if (ses.kind === 'conj') {
    q = nextConjQuestion(ses);
  } else {
    const skillId = pickSkill(ses);
    const item = ses.decks.get(skillId).next();
    q = { skillId, item };
  }
  ses.asked += 1;
  ses.q = q;
  if (ses.kind === 'conj') renderConjQuestion(q);
  else renderQuestion(q);
}

function levelAndMode(ses, q) {
  parsed(q.item);
  const s = stateOf(q.skillId);
  if (ses.mode !== 'auto') {
    const want = ses.mode;
    const mode = M.modeFor(MODE_LEVEL[want], q.item);
    return { level: MODE_LEVEL[mode], mode, counts: false };
  }
  const level = Math.min(s.l, M.MAX_LEVEL);
  return { level, mode: M.modeFor(level, q.item), counts: true };
}

function renderQuestion(q) {
  const ses = app.session;
  const { level, mode, counts } = levelAndMode(ses, q);
  const ex = build(q.item, mode);
  Object.assign(q, { level, mode, counts, ex, answered: false, started: performance.now() });
  const skill = ses.bundles.get(q.skillId).skill;
  $('#pdBadge').textContent = modeName(mode);
  $('#pdSkillName').textContent = ses.mix ? `${skill.p} · ${skill.title}` : skill.title;
  $('#pdCount').textContent = String(Math.min(ses.done, ses.roundSize));
  $('#pdFill').style.width = `${Math.min(100, (ses.done / ses.roundSize) * 100)}%`;
  $('#pdAsk').textContent = t(...INSTRUCTION[mode]);
  $('#pdFeedback').hidden = true;
  $('#pdNext').hidden = true;
  $('#pdCheck').hidden = true;
  $('#pdClock').hidden = mode !== 'speed';
  const en = $('#pdEn');
  en.textContent = q.item.en;
  en.classList.toggle('is-hidden', !(mode === 'meet' || mode === 'fill' || mode === 'fix'));
  ses.onCheck = null;
  ses.onKey = null;
  ({
    meet: askChoice,
    choose: askChoice,
    speed: askChoice,
    type: askTyped,
    fill: askFill,
    fix: askFix,
  })[mode](q);
}

function drawSentence(q, slotHtml) {
  $('#pdSentence').innerHTML = toHtml(q.ex.parsed, slotHtml);
}

const blank = (cls = '') => `<span class="pd-blank ${cls}">&nbsp;</span>`;
const focusOnly = (q, focusHtml) => (slot, i) =>
  i === q.ex.focus ? focusHtml : `<span class="pd-other">${rubyHtml(slot.raw[0])}</span>`;

function optionsHtml(options, render = esc) {
  return `<div class="pd-options">${options
    .map(
      (o, i) =>
        `<button type="button" class="ld-opt pd-opt" data-i="${i}" lang="ja"><span class="ld-opt__key" aria-hidden="true">${i + 1}</span><span class="pd-opt__t${String(o).length > 4 ? ' is-long' : ''}">${render(o)}</span></button>`
    )
    .join('')}</div>`;
}

function askChoice(q) {
  const ses = app.session;
  drawSentence(q, focusOnly(q, blank('is-focus')));
  $('#pdAnswer').innerHTML = optionsHtml(q.ex.options, (o) => rb(q.ex, o));
  const choose = (i) => {
    if (q.answered || i >= q.ex.options.length) return;
    const picked = q.ex.options[i];
    const ok = gradeChoice(q.ex, picked);
    $$('.pd-opt').forEach((btn, k) => {
      btn.disabled = true;
      if (q.ex.accepted.includes(q.ex.options[k])) btn.classList.add('is-correct');
      else if (k === i) btn.classList.add('is-wrong');
    });
    settle(q, ok, picked);
  };
  $$('.pd-opt').forEach((btn) =>
    btn.addEventListener('click', () => choose(Number(btn.dataset.i)))
  );
  ses.onKey = (e) => {
    if (/^[1-4]$/.test(e.key)) choose(Number(e.key) - 1);
  };
  if (q.mode === 'speed') runClock(q, M.SPEED_LIMIT_MS, () => settle(q, false, null, true));
}

function runClock(q, limit, onTimeout) {
  const bar = $('#pdClock i');
  const ses = app.session;
  const tick = () => {
    if (q.answered) return;
    const left = 1 - (performance.now() - q.started) / limit;
    bar.style.transform = `scaleX(${Math.max(0, left)})`;
    if (left <= 0) return onTimeout();
    ses.raf = requestAnimationFrame(tick);
  };
  ses.raf = requestAnimationFrame(tick);
}

function typedInputHtml(placeholder) {
  return `<form class="pd-typed" id="pdTypedForm" autocomplete="off">
    <input id="pdTyped" class="pd-typed__in" type="text" lang="ja" inputmode="text" autocapitalize="off" autocorrect="off" spellcheck="false" maxlength="24" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}">
    <small class="ld-hint">${esc(t('typed_hint', 'Kana or romaji (wa, ni, de …). Enter to check.'))}</small>
  </form>`;
}

/** Wire a typed input: romaji turns into kana as it is typed; Enter submits unless an IME is composing. */
function bindTyped(submit) {
  const input = $('#pdTyped');
  let composing = false;
  input.addEventListener('compositionstart', () => (composing = true));
  input.addEventListener('compositionend', () => (composing = false));
  input.addEventListener('input', () => {
    if (composing) return;
    const kana = romajiToKana(input.value, false);
    if (kana !== input.value) input.value = kana;
  });
  const fire = () => {
    if (composing) return;
    const value = input.value.trim();
    if (value) submit(value, input);
  };
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !composing && e.keyCode !== 229) {
      e.preventDefault();
      e.stopPropagation();
      fire();
    }
  });
  $('#pdTypedForm').addEventListener('submit', (e) => {
    e.preventDefault();
    fire();
  });
  const check = $('#pdCheck');
  check.hidden = false;
  app.session.onCheck = fire;
  input.focus();
}

function askTyped(q) {
  drawSentence(q, focusOnly(q, blank('is-focus')));
  $('#pdAnswer').innerHTML = typedInputHtml(t('typed_placeholder', 'particle'));
  bindTyped((value, input) => {
    if (q.answered) return;
    input.disabled = true;
    settle(q, gradeTyped(q.ex, value), romajiToKana(value, true));
  });
}

function askFill(q) {
  const ses = app.session;
  const n = q.ex.parsed.slots.length;
  const answers = new Array(n).fill(null);
  const used = new Array(q.ex.bank.length).fill(-1); // chip -> slot it fills
  const draw = () => {
    const active = answers.indexOf(null);
    drawSentence(q, (slot, i) =>
      answers[i] == null
        ? `<button type="button" class="pd-blank pd-blank--btn${i === active ? ' is-focus' : ''}" data-slot="${i}">&nbsp;</button>`
        : `<button type="button" class="pd-blank pd-blank--btn is-filled" data-slot="${i}">${rb(q.ex, answers[i])}</button>`
    );
    $('#pdAnswer').innerHTML = `<div class="pd-bank">${q.ex.bank
      .map(
        (chip, k) =>
          `<button type="button" class="ld-chip pd-chip" data-k="${k}"${used[k] >= 0 ? ' disabled' : ''} lang="ja">${rb(q.ex, chip)}</button>`
      )
      .join('')}</div>`;
    $$('.pd-chip').forEach((btn) =>
      btn.addEventListener('click', () => place(Number(btn.dataset.k)))
    );
    $$('.pd-blank--btn.is-filled').forEach((btn) =>
      btn.addEventListener('click', () => clear(Number(btn.dataset.slot)))
    );
    $('#pdCheck').hidden = false;
    $('#pdCheck').disabled = answers.includes(null);
  };
  const place = (k) => {
    if (q.answered || used[k] >= 0) return;
    const slot = answers.indexOf(null);
    if (slot < 0) return;
    answers[slot] = q.ex.bank[k];
    used[k] = slot;
    draw();
  };
  const clear = (slot) => {
    if (q.answered) return;
    answers[slot] = null;
    const k = used.indexOf(slot);
    if (k >= 0) used[k] = -1;
    draw();
  };
  ses.onCheck = () => {
    if (q.answered || answers.includes(null)) return;
    const result = gradeFill(q.ex, answers);
    drawSentence(q, (slot, i) =>
      result.perSlot[i]
        ? `<span class="pd-blank is-filled is-correct">${rb(q.ex, answers[i])}</span>`
        : `<span class="pd-blank is-filled is-wrong">${rb(q.ex, answers[i])}</span><span class="pd-blank is-filled is-reveal">${rubyHtml(slot.raw[0])}</span>`
    );
    $$('.pd-chip').forEach((b) => (b.disabled = true));
    settle(q, result.correct, null);
  };
  ses.onKey = (e) => {
    if (/^[1-9]$/.test(e.key)) place(Number(e.key) - 1);
    else if (e.key === 'Backspace') {
      const last = answers.reduce((acc, a, i) => (a != null ? i : acc), -1);
      if (last >= 0) clear(last);
    } else if (e.key === 'Enter') ses.onCheck();
  };
  draw();
}

function askFix(q) {
  const ses = app.session;
  drawSentence(
    q,
    (slot, i) =>
      `<button type="button" class="pd-tok" data-slot="${i}">${rb(q.ex, q.ex.shown[i])}</button>`
  );
  $('#pdAnswer').innerHTML = '';
  const tap = (i) => {
    if (q.answered || q.tapped != null) return;
    q.tapped = i;
    const found = gradeFixTap(q.ex, i);
    $$('.pd-tok').forEach((btn, k) => {
      btn.disabled = true;
      if (k === q.ex.focus) btn.classList.add(found ? 'is-picked' : 'is-wrong');
      else if (k === i) btn.classList.add('is-miss');
    });
    if (!found) return settle(q, false, q.ex.wrong);
    $('#pdAsk').textContent = t('ask_fix2', 'Right. What should it be?');
    $('#pdAnswer').innerHTML = optionsHtml(q.ex.options, (o) => rb(q.ex, o));
    const choose = (k) => {
      if (q.answered || k >= q.ex.options.length) return;
      const picked = q.ex.options[k];
      const ok = gradeChoice(q.ex, picked);
      $$('.pd-opt').forEach((btn, j) => {
        btn.disabled = true;
        if (q.ex.accepted.includes(q.ex.options[j])) btn.classList.add('is-correct');
        else if (j === k) btn.classList.add('is-wrong');
      });
      settle(q, ok, ok ? picked : q.ex.wrong);
    };
    $$('.pd-opt').forEach((btn) =>
      btn.addEventListener('click', () => choose(Number(btn.dataset.i)))
    );
    ses.onKey = (e) => {
      if (/^[1-4]$/.test(e.key)) choose(Number(e.key) - 1);
    };
  };
  $$('.pd-tok').forEach((btn) =>
    btn.addEventListener('click', () => tap(Number(btn.dataset.slot)))
  );
}

/** Record the answer, show feedback, and move on (at once when right). */
function settle(q, correct, given, timedOut = false) {
  const ses = app.session;
  if (q.answered) return;
  q.answered = true;
  const ms = Math.round(performance.now() - q.started);
  ses.onKey = null;
  ses.onCheck = null;
  $('#pdCheck').hidden = true;
  $('#pdClock').hidden = true;

  if (!q.retry) {
    ses.done += 1;
    ses.total += 1;
    if (correct) ses.right += 1;
    ses.times.push(ms);
    const before = stateOf(q.skillId);
    const { state, event } = M.record(before, {
      correct,
      ms,
      level: q.level,
      itemId: q.item.generated ? null : q.item.id,
      counts: q.counts,
    });
    app.store.setSkill(q.skillId, state);
    app.store.save();
    if (event) ses.events.push({ skillId: q.skillId, event, level: state.l });
    q.event = event;
    q.newLevel = state.l;
  }
  ses.streak = correct ? ses.streak + 1 : 0;
  if (!correct && !q.retry)
    ses.retry.push({ at: ses.asked + 3, q: { skillId: q.skillId, item: q.item } });

  $('#pdCount').textContent = String(Math.min(ses.done, ses.roundSize));
  $('#pdFill').style.width = `${Math.min(100, (ses.done / ses.roundSize) * 100)}%`;
  if (q.mode !== 'fill') {
    drawSentence(q, (slot, i) =>
      i === q.ex.focus
        ? `<span class="pd-blank is-filled ${correct ? 'is-correct' : 'is-reveal'}">${rb(q.ex, q.ex.answer)}</span>`
        : `<span class="pd-other">${rubyHtml(slot.raw[0])}</span>`
    );
  }
  $('#pdEn').classList.remove('is-hidden');

  const skill = ses.bundles.get(q.skillId).skill;
  const alts = q.ex.accepted.slice(1);
  const fb = $('#pdFeedback');
  fb.hidden = false;
  fb.className = `pd-feedback ${correct ? 'is-ok' : 'is-bad'}`;
  const move =
    q.event === 'promoted' || q.event === 'mastered'
      ? `<span class="ld-tag ld-tag--ok">↑ ${esc(levelName(q.newLevel))}</span>`
      : q.event === 'demoted'
        ? `<span class="ld-tag ld-tag--warn">↓ ${esc(levelName(q.newLevel))}</span>`
        : '';
  fb.innerHTML = correct
    ? `<b>${esc(ses.streak >= 3 ? t('fb_streak', '{n} in a row', { n: ses.streak }) : t('fb_right', 'Right'))}</b> ${move}<span class="pd-feedback__why">${esc(q.item.why || '')}</span>`
    : `<b>${esc(timedOut ? t('fb_time', 'Too slow') : t('fb_wrong', 'Not quite'))}</b> ${move}
       <span class="pd-feedback__ans" lang="ja">${esc(given && !timedOut ? `${given} → ` : '')}<b>${rb(q.ex, q.ex.answer)}</b>${alts.length ? ` <small>(${esc(t('fb_also', 'also'))} ${esc(alts.join('、'))})</small>` : ''}</span>
       <span class="pd-feedback__why">${esc(q.item.why || '')}</span>
       <button type="button" class="ld-link pd-feedback__guide" id="pdGuideLink">${esc(t('fb_guide', 'Open the guide for {p}', { p: skill.p }))}</button>`;
  const link = $('#pdGuideLink');
  if (link)
    link.addEventListener('click', () =>
      openGuideSheet(guideHtml(ses.bundles.get(q.skillId).guide))
    );

  if (correct) {
    // Keep the pace: a right answer moves on by itself. Level 1 lingers so the
    // translation and the reason can be read.
    later(advance, q.mode === 'meet' ? 1400 : q.event ? 1300 : 750);
  } else {
    const next = $('#pdNext');
    next.hidden = false;
    next.focus();
  }
}

function advance() {
  const ses = app.session;
  if (!ses || !ses.q || !ses.q.answered) return;
  clearTimers();
  nextQuestion();
}

function finishRound() {
  const ses = app.session;
  const pct = ses.done ? Math.round((ses.right / ses.done) * 100) : 0;
  const sorted = ses.times.slice().sort((a, b) => a - b);
  const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] / 1000 : 0;
  app.store.flush();
  const label = (e) =>
    ses.kind === 'conj'
      ? FORMS[e.skillId].label
      : `${ses.bundles.get(e.skillId).skill.p} · ${ses.bundles.get(e.skillId).skill.title}`;
  const max = ses.kind === 'conj' ? CONJ_MAX_LEVEL : M.MAX_LEVEL;
  const events = ses.events
    .map(
      (e) =>
        `<li class="${e.event === 'demoted' ? 'is-down' : 'is-up'}"><span>${esc(label(e))}</span><b>${e.event === 'demoted' ? '↓' : '↑'} ${esc(ses.kind === 'conj' ? conjLevelName(e.level) : levelName(e.level))}</b>${pips(e.level, max)}</li>`
    )
    .join('');
  const backHref = ses.kind === 'conj' ? conjHome() : ses.mix ? '#/' : `#/skill/${ses.order[0]}`;
  setView(
    `<div class="pd-results">
      <div class="pd-results__pct">${pct}<small>%</small></div>
      <div class="ld-stats ld-stats--two">
        <div class="ld-stat"><b class="ld-stat__n">${ses.right} / ${ses.done}</b><small>${esc(t('res_right', 'right'))}</small></div>
        <div class="ld-stat"><b class="ld-stat__n">${median.toFixed(1)}s</b><small>${esc(t('res_pace', 'per answer'))}</small></div>
      </div>
      ${events ? `<ul class="pd-events">${events}</ul>` : `<p class="ld-hint">${esc(pct >= 80 ? t('res_keep', 'Solid. Keep going to move up a rung.') : t('res_slow', 'Under 80%: the drill stays on this rung. Read the guide once, then go again.'))}</p>`}
      <p class="ld-hint">${esc(t('res_total', '{n} answers this session', { n: ses.total }))}</p>
    </div>`,
    {
      dock: `<div class="ld-row"><a class="ld-btn ld-btn--ghost" href="${backHref}">${esc(t('done', 'Done'))}</a>
        <button type="button" class="ld-btn" id="pdAgain">${esc(t('next_round', 'Next round'))}</button></div>`,
    }
  );
  const again = $('#pdAgain');
  again.addEventListener('click', newRound);
  again.focus();
  ses.q = null;
}

// ---------------------------------------------------------------------------
// Conjugation gym
// ---------------------------------------------------------------------------
const CONJ_LEVELS = {
  1: ['level_choose', 'Choose'],
  2: ['level_type', 'Type'],
  3: ['level_speed', 'Speed'],
  4: ['level_instant', 'Instant'],
};
const conjLevelName = (l) => t(...(CONJ_LEVELS[Math.min(Math.max(l, 1), 4)] || CONJ_LEVELS[1]));
const conjState = (id) => app.store.conj(id) || M.newState();

async function renderConj() {
  setView(`<p class="drill-msg">${esc(t('loading', 'Loading…'))}</p>`, {
    title: t('conj_title', 'Conjugation'),
  });
  const [data, mine] = await Promise.all([loadConj(), loadMyWords()]);
  const chosen = new Set(app.store.setting('conjForms', ['masu', 'te', 'nai', 'ta']));
  const levels = conjPools(mine);
  const mode = app.store.setting('conjMode', 'auto');
  const ownNote = mine.words.length
    ? t(
        'conj_mine_note',
        'From your vocabulary: {v} verbs and {a} adjectives you know. New ones join as you learn them.',
        { v: mine.verbs, a: mine.adjectives }
      )
    : t(
        'conj_mine_empty',
        'No verbs or adjectives in your vocabulary yet. Take tests or a placement check and they appear here; until then use the level lists.'
      );
  const chip = (f) => {
    const s = conjState(f.id);
    return `<button type="button" class="ld-chip pd-form" data-form="${f.id}" aria-pressed="${chosen.has(f.id)}">
      <b lang="ja">${esc(f.label)}</b><small>${esc(f.hint)}</small>${pips(s.n ? s.l : 0, CONJ_MAX_LEVEL)}</button>`;
  };
  const guides = (data.guide || [])
    .map(
      (g) =>
        `<button type="button" class="pd-skill pd-conjguide" data-guide="${esc(g.id)}"><span class="pd-skill__t">${esc(g.title)}</span><span class="pd-skill__m">${esc(t('guide', 'Guide'))}</span></button>`
    )
    .join('');
  setView(
    `<div class="pd-conj">
      <p class="ld-hint">${esc(t('conj_intro', 'Pick the forms to drill. Words come at random and never run out; three rungs: Choose, Type, Speed.'))}</p>
      <h2 class="ld-sech">${esc(t('conj_words', 'Words'))}</h2>
      <p class="ld-hint pd-ownnote">${esc(ownNote)}</p>
      <div class="ld-chips pd-levels">
        <button type="button" class="ld-chip" data-lv="mine" aria-pressed="${levels.has('mine')}"${mine.words.length ? '' : ' disabled'}>${esc(t('conj_mine', 'Words I know'))} · ${mine.words.length}</button>
        ${[5, 4, 3]
          .map(
            (lv) =>
              `<button type="button" class="ld-chip" data-lv="${lv}" aria-pressed="${levels.has(lv)}">N${lv}${lv === 3 ? '+' : ''}</button>`
          )
          .join('')}</div>
      <h2 class="ld-sech">${esc(t('conj_verbs', 'Verb forms'))}</h2>
      <div class="pd-forms">${VERB_FORMS.map(chip).join('')}</div>
      <h2 class="ld-sech">${esc(t('conj_adjs', 'Adjective forms'))}</h2>
      <div class="pd-forms">${ADJ_FORMS.map(chip).join('')}</div>
      ${guides ? `<h2 class="ld-sech">${esc(t('conj_guides', 'How each form is built'))}</h2><div class="ld-card pd-group">${guides}</div>` : ''}
    </div>`,
    {
      title: t('conj_title', 'Conjugation'),
      dock: `<div class="ld-seg pd-modes" role="group">${['auto', 'choose', 'type', 'speed']
        .map(
          (m) =>
            `<button type="button" data-mode="${m}" aria-pressed="${m === mode}" class="${m === mode ? 'active' : ''}">${esc(modeName(m))}</button>`
        )
        .join('')}</div>
        <button type="button" class="ld-btn ld-btn--block" id="pdConjStart">${esc(t('drill_start', 'Start drilling'))}</button>`,
    }
  );
  const toggle = (btn, set, value, key) => {
    if (set.has(value)) set.delete(value);
    else set.add(value);
    btn.setAttribute('aria-pressed', String(set.has(value)));
    app.store.setSetting(key, Array.from(set));
    $('#pdConjStart').disabled = !chosen.size || !levels.size;
  };
  $$('.pd-form').forEach((btn) =>
    btn.addEventListener('click', () => toggle(btn, chosen, btn.dataset.form, 'conjForms'))
  );
  $$('.pd-levels button').forEach((btn) =>
    btn.addEventListener('click', () =>
      toggle(btn, levels, btn.dataset.lv === 'mine' ? 'mine' : Number(btn.dataset.lv), 'conjLevels')
    )
  );
  $$('.pd-modes button').forEach((btn) =>
    btn.addEventListener('click', () => {
      app.store.setSetting('conjMode', btn.dataset.mode);
      $$('.pd-modes button').forEach((b) => {
        b.classList.toggle('active', b === btn);
        b.setAttribute('aria-pressed', String(b === btn));
      });
    })
  );
  $$('.pd-conjguide').forEach((btn) =>
    btn.addEventListener('click', () => {
      const g = data.guide.find((x) => x.id === btn.dataset.guide);
      openGuideSheet(`<h2>${esc(g.title)}</h2>${guideHtml(g)}`);
    })
  );
  $('#pdConjStart').disabled = !chosen.size || !levels.size;
  $('#pdConjStart').addEventListener('click', () => go(conjDrill()));
}

async function startConj() {
  const [data, mine] = await Promise.all([loadConj(), loadMyWords()]);
  const forms = app.store.setting('conjForms', ['masu', 'te', 'nai', 'ta']).filter((f) => FORMS[f]);
  const levels = conjPools(mine);
  const inLevel = (w) => levels.has(w.lv) || (levels.has(3) && w.lv < 3);
  // The learner's own words first, then the level lists; one entry per word.
  const pool = new Map();
  if (levels.has('mine')) mine.words.forEach((w) => pool.set(`${w.d}|${w.k}`, w));
  [...(data.verbs || []), ...(data.adjectives || [])].filter(inLevel).forEach((w) => {
    if (!pool.has(`${w.d}|${w.k}`)) pool.set(`${w.d}|${w.k}`, w);
  });
  const words = Array.from(pool.values());
  const verbs = words.filter((w) => w.c !== 'i' && w.c !== 'na');
  const adjs = words.filter((w) => w.c === 'i' || w.c === 'na');
  const usable = forms.filter((f) => (f.startsWith('adj_') ? adjs.length : verbs.length));
  if (!usable.length) return go(conjHome());
  app.session = {
    kind: 'conj',
    forms: usable,
    verbs,
    adjs,
    guide: new Map((data.guide || []).map((g) => [g.id, g])),
    mode: app.store.setting('conjMode', 'auto'),
    roundSize: MIX_ROUND,
    total: 0,
    recent: [],
  };
  newRound();
}

function nextConjQuestion(ses) {
  // Weakest forms come up more often.
  const weights = ses.forms.map((f) => {
    const s = conjState(f);
    return 1 + (1 - (s.e == null ? 0.5 : s.e)) * 2;
  });
  let r = Math.random() * weights.reduce((a, b) => a + b, 0);
  let form = ses.forms[0];
  for (let i = 0; i < weights.length; i++) {
    r -= weights[i];
    if (r <= 0) {
      form = ses.forms[i];
      break;
    }
  }
  const pool = form.startsWith('adj_') ? ses.adjs : ses.verbs;
  let word = pool[0];
  for (let tries = 0; tries < 30; tries++) {
    const w = pool[Math.floor(Math.random() * pool.length)];
    if (formsFor(w).includes(form) && !ses.recent.includes(w.d)) {
      word = w;
      break;
    }
  }
  ses.recent.push(word.d);
  if (ses.recent.length > 15) ses.recent.shift();
  return { skillId: form, word };
}

function renderConjQuestion(q) {
  const ses = app.session;
  const s = conjState(q.skillId);
  const form = FORMS[q.skillId];
  let level = Math.min(s.l, CONJ_MAX_LEVEL);
  let counts = true;
  if (ses.mode !== 'auto') {
    level = { choose: 1, type: 2, speed: 3 }[ses.mode];
    counts = false;
  }
  const mode = { 1: 'choose', 2: 'type', 3: 'speed' }[level];
  const right = conjugate(q.word, q.skillId);
  Object.assign(q, {
    level,
    mode,
    counts,
    right,
    accepted: acceptedAnswers(q.word, q.skillId),
    answered: false,
    started: performance.now(),
  });
  $('#pdBadge').textContent = conjLevelName(level);
  $('#pdSkillName').textContent = '';
  $('#pdCount').textContent = String(Math.min(ses.done, ses.roundSize));
  $('#pdFill').style.width = `${Math.min(100, (ses.done / ses.roundSize) * 100)}%`;
  $('#pdAsk').textContent = t('conj_ask', 'Give this form:');
  $('#pdFeedback').hidden = true;
  $('#pdNext').hidden = true;
  $('#pdCheck').hidden = true;
  $('#pdClock').hidden = mode !== 'speed';
  $('#pdSentence').innerHTML =
    `<span class="pd-word"><ruby>${esc(q.word.d)}<rt>${esc(q.word.d === q.word.k ? '' : q.word.k)}</rt></ruby></span>
    <span class="pd-arrow" aria-hidden="true">→</span><span class="pd-target">${esc(form.label)}<small>${esc(form.hint)}</small></span>`;
  $('#pdEn').textContent = q.word.en || '';
  $('#pdEn').classList.remove('is-hidden');
  ses.onKey = null;
  ses.onCheck = null;
  if (mode === 'type') {
    $('#pdAnswer').innerHTML = typedInputHtml(form.label);
    bindTyped((value, input) => {
      if (q.answered) return;
      input.disabled = true;
      settleConj(q, answerMatches(q.accepted, value), romajiToKana(value, true));
    });
    return;
  }
  const options = shuffle([right.kanji[0], ...distractors(q.word, q.skillId, 3)]);
  q.options = options;
  $('#pdAnswer').innerHTML = optionsHtml(options);
  const choose = (i) => {
    if (q.answered || i >= options.length) return;
    const ok = q.accepted.includes(options[i]);
    $$('.pd-opt').forEach((btn, k) => {
      btn.disabled = true;
      if (q.accepted.includes(options[k])) btn.classList.add('is-correct');
      else if (k === i) btn.classList.add('is-wrong');
    });
    settleConj(q, ok, options[i]);
  };
  $$('.pd-opt').forEach((btn) =>
    btn.addEventListener('click', () => choose(Number(btn.dataset.i)))
  );
  ses.onKey = (e) => {
    if (/^[1-4]$/.test(e.key)) choose(Number(e.key) - 1);
  };
  if (mode === 'speed') runClock(q, M.SPEED_LIMIT_MS, () => settleConj(q, false, null, true));
}

const GROUP_NAME = {
  godan: ['group_godan', 'Group 1 (godan, う-verb)'],
  ichidan: ['group_ichidan', 'Group 2 (ichidan, る-verb)'],
  suru: ['group_suru', 'Irregular (する)'],
  kuru: ['group_kuru', 'Irregular (来る)'],
  i: ['group_i', 'い-adjective'],
  na: ['group_na', 'な-adjective'],
};

function settleConj(q, correct, given, timedOut = false) {
  const ses = app.session;
  if (q.answered) return;
  q.answered = true;
  const ms = Math.round(performance.now() - q.started);
  ses.onKey = null;
  ses.onCheck = null;
  $('#pdCheck').hidden = true;
  $('#pdClock').hidden = true;
  if (!q.retry) {
    ses.done += 1;
    ses.total += 1;
    if (correct) ses.right += 1;
    ses.times.push(ms);
    const { state, event } = M.record(
      conjState(q.skillId),
      { correct, ms, level: q.level, counts: q.counts },
      Date.now(),
      CONJ_MAX_LEVEL
    );
    app.store.setConj(q.skillId, state);
    app.store.save();
    if (event) ses.events.push({ skillId: q.skillId, event, level: state.l });
    q.event = event;
    q.newLevel = state.l;
  }
  ses.streak = correct ? ses.streak + 1 : 0;
  if (!correct && !q.retry)
    ses.retry.push({ at: ses.asked + 3, q: { skillId: q.skillId, word: q.word } });
  $('#pdCount').textContent = String(Math.min(ses.done, ses.roundSize));
  $('#pdFill').style.width = `${Math.min(100, (ses.done / ses.roundSize) * 100)}%`;

  const form = FORMS[q.skillId];
  const guide = ses.guide.get(form.guide);
  const answer = q.right.kanji[0];
  const reading = q.right.kana[0] !== answer ? ` <small>${esc(q.right.kana[0])}</small>` : '';
  const fb = $('#pdFeedback');
  fb.hidden = false;
  fb.className = `pd-feedback ${correct ? 'is-ok' : 'is-bad'}`;
  const group = `<span class="ld-tag">${esc(t(...GROUP_NAME[q.word.c]))}</span>`;
  fb.innerHTML = correct
    ? `<b>${esc(ses.streak >= 3 ? t('fb_streak', '{n} in a row', { n: ses.streak }) : t('fb_right', 'Right'))}</b> <span class="pd-feedback__ans" lang="ja"><b>${esc(answer)}</b>${reading}</span> ${group}`
    : `<b>${esc(timedOut ? t('fb_time', 'Too slow') : t('fb_wrong', 'Not quite'))}</b>
       <span class="pd-feedback__ans" lang="ja">${esc(given && !timedOut ? `${given} → ` : '')}<b>${esc(answer)}</b>${reading}</span> ${group}
       ${guide ? `<span class="pd-feedback__why">${proseHtml(guide.rule)}</span><button type="button" class="ld-link pd-feedback__guide" id="pdGuideLink">${esc(t('fb_guide', 'Open the guide for {p}', { p: guide.title }))}</button>` : ''}`;
  const link = $('#pdGuideLink');
  if (link)
    link.addEventListener('click', () =>
      openGuideSheet(`<h2>${esc(guide.title)}</h2>${guideHtml(guide)}`)
    );
  if (correct) later(advance, q.event ? 1300 : 800);
  else {
    const next = $('#pdNext');
    next.hidden = false;
    next.focus();
  }
}

// ---------------------------------------------------------------------------
// Routing and start-up
// ---------------------------------------------------------------------------
function go(hash) {
  if (window.location.hash === hash) route();
  else window.location.hash = hash;
}

async function route() {
  const hash = window.location.hash.replace(/^#\/?/, '');
  const [view, arg] = hash.split('/');
  if (app.session) app.store.flush();
  app.session = null;
  try {
    if (isConjHome()) {
      // /conjugation-drill: the setup is the home view.
      if (view === 'drill') await startConj();
      else await renderConj();
      return;
    }
    if (view === 'conj') {
      window.location.replace('/conjugation-drill');
      return;
    }
    if (view === 'skill' && arg) await renderSkill(decodeURIComponent(arg));
    else if (view === 'drill' && arg) await startDrill([decodeURIComponent(arg)]);
    else if (view === 'mix') {
      const picked = M.planMix(app.catalog.skills, app.store.doc.skills, { size: 6, fresh: 1 });
      await startDrill(
        picked.map((k) => k.id),
        { mix: true }
      );
    } else renderHub();
  } catch (err) {
    console.error('particle drill:', err);
    setView(`<p class="ld-note ld-note--bad">${esc(t('error_load', 'Could not load the particle drill. Check your connection and try again.'))}</p>
      <p><a class="ld-btn ld-btn--ghost" href="#/">${esc(t('back_hub', 'Back'))}</a></p>`);
  }
}

function onKeydown(e) {
  const ses = app.session;
  if (!ses || e.metaKey || e.ctrlKey || e.altKey) return;
  if (document.querySelector('.pd-sheet')) {
    if (e.key === 'Escape') document.querySelector('.pd-sheet').remove();
    return;
  }
  if (ses.q && ses.q.answered) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      advance();
    }
    return;
  }
  if (e.target && e.target.tagName === 'INPUT') return;
  if (ses.onKey) ses.onKey(e);
}

export async function mount(root) {
  app.root = root;
  app.store = createStore();
  root.innerHTML = `<p class="drill-msg">${esc(t('loading', 'Loading…'))}</p>`;
  try {
    // The conjugation page needs no particle catalog.
    const [catalog] = await Promise.all([
      root.dataset.home === 'conj' ? null : getJson('/catalog'),
      app.store.pull(),
    ]);
    app.catalog = catalog;
    if (catalog) catalog.skills.forEach((k) => app.skills.set(k.id, k));
  } catch (err) {
    console.error('particle drill:', err);
    root.innerHTML = `<p class="ld-note ld-note--bad">${esc(t('error_load', 'Could not load the particle drill. Check your connection and try again.'))}</p>`;
    return;
  }
  window.addEventListener('hashchange', route);
  document.addEventListener('keydown', onKeydown);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') app.store.flush();
  });
  route();
}

const host = document.getElementById('particleDrillRoot');
if (host) {
  const start = () => mount(host);
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start);
}
