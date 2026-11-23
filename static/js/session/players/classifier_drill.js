// static/js/session/players/classifier_drill.js
// The noun-counting drills: Chinese measure words (classifiers) and Japanese
// counters. One engine, `mountDrill(container, ctx, config)`, runs a batch of
// items (prompt, choose or type, feedback, results, submit); a config object
// supplies what differs per drill: endpoints, i18n keys, markup and how an item
// is shown and judged. CLASSIFIER is defined here; the counter config lives in
// static/js/pages/counter-drill.js.
//
// The engine has two hosts:
//  - the daily session: `mount(container, ctx)`, the classifier drill only. ONE
//    20-item batch == one queue item: when the batch finishes the player
//    submits to /api/classifier-drill/submit (attempt + ELO + the weekly
//    Study-Plan progress hook), then shows a single Continue button that calls
//    ctx.onComplete. No redirect, no "Next round" loop.
//  - a standalone page (/classifier-drill, /counter-drill): `mountDrillPage`,
//    which passes ctx.standalone. The page markup has its own progress strip
//    and a results screen offering another round or the way out.
//
// Both hosts render one task screen (FOUNDATION.md): a progress strip, the
// prompt and answers in the scrolling .ld-stage, and feedback / Check / the
// results actions in the pinned .ld-dock. Styles: static/css/redesign/
// trainers.css (.drill-player), loaded on every page.
//
// Player contract: mount(container, ctx) -> { destroy() }.
//   ctx = { item, languageId, onComplete(result), onSkip() }.
// All DOM is scoped to `container`, and every document-level listener / timer
// is tracked and torn down in destroy().

import { T, escapeHtml, shuffle, applyI18n } from '../dom.js';
import { prefetchJson, takePrefetch } from '../prefetch.js';
import { formatPinyin } from '../pinyin-format.js';

const BATCH_SIZE = 20;

const sessionUrl = (apiBase, languageId) =>
  apiBase + '/session?language_id=' + languageId + '&count=' + BATCH_SIZE;

/**
 * Session prefetch hook: the batch, unless a classifier drill is running (its
 * submit changes what the next batch should hold).
 */
export function prefetch(item, ctx) {
  const current = ctx && ctx.current;
  if (current && current.test_type === 'classifier_drill') return null;
  return prefetchJson(sessionUrl(CLASSIFIER.apiBase, (ctx && ctx.languageId) || 1));
}

/** The classifier drill as a daily-session item. */
export function mount(container, ctx) {
  return mountDrill(container, ctx, CLASSIFIER);
}

/**
 * A drill as its own page. `config` is a drill config (see CLASSIFIER);
 * `page.navigate(url)` replaces the default location change.
 */
export function mountDrillPage(root, config, page) {
  return mountDrill(
    root,
    {
      standalone: {
        navigate: (page && page.navigate) || ((url) => (window.location.href = url)),
        // Runs inside the drill's own start-up, so a failure shows its error text.
        async prepare() {
          if (window.LinguaI18n && window.LinguaI18n.init) await window.LinguaI18n.init();
          if (window.LinguaTestIntro) window.LinguaTestIntro.init({ testType: config.testType });
          applyI18n(root);
        },
      },
    },
    config
  );
}

// el key -> element id without the config's prefix ('cd' / 'ct'). A drill's
// markup carries the ones it uses; the rest are null.
const ELEMENT_IDS = {
  header: 'Header',
  controls: 'Controls',
  loading: 'Loading',
  empty: 'Empty',
  stage: 'Stage',
  promptWrap: 'PromptWrap',
  promptBlank: 'PromptBlank',
  noun: 'Noun',
  numeral: 'Numeral',
  pronunciation: 'Pronunciation',
  reading: 'Reading',
  gloss: 'Gloss',
  reversePrompt: 'ReversePrompt',
  options: 'Options',
  typedForm: 'TypedForm',
  typedInput: 'TypedInput',
  progressLabel: 'ProgressLabel',
  progressTotal: 'ProgressTotal',
  progressFill: 'ProgressFill',
  levelBadge: 'LevelBadge',
  feedback: 'Feedback',
  fbCanonical: 'FeedbackCanonical',
  fbReading: 'FeedbackReading',
  fbGroup: 'FeedbackGroup',
  fbExamples: 'FeedbackExamples',
  fbNumerals: 'FeedbackNumerals',
  fbAlts: 'FeedbackAlts',
  fbContinue: 'FeedbackContinue',
  results: 'Results',
  resultsGrade: 'ResultsGrade',
  resultsPct: 'ResultsPct',
  resultsCorrect: 'ResultsCorrect',
  resultsTotal: 'ResultsTotal',
  resultsTime: 'ResultsTime',
  resultsElo: 'ResultsElo',
  resultsNote: 'ResultsNote',
  resultsContinue: 'ResultsContinue',
  resultsNext: 'ResultsNext',
  resultsExit: 'ResultsExit',
  modeToggle: 'ModeToggle',
  check: 'Check',
  hint: 'Hint',
};

/**
 * mountDrill(container, ctx, config) -> { destroy() }
 *
 * config (a drill):
 *   kind, testType      'classifier' / 'classifier_drill' (test-intro type)
 *   label               prefix of console lines ('Classifier')
 *   apiBase             '/api/classifier-drill' (+ /session, /submit)
 *   languageId          the drill's language (a session's own id wins)
 *   i18n                key prefix ('classifier_drill')
 *   prefix              element id prefix ('cd')
 *   modeKey, defaultMode   localStorage key of the mode toggle and its default
 *   ignoreSameMode      a click on the active mode does nothing
 *   display             CSS display of { loading, bar, stage, results } when shown
 *   pageMarkup, sessionMarkup   markup per host
 *   exitUrl             where the page's Done button goes
 *   lenientLoad         page only: no HTTP status check; any failure to fetch or
 *                       parse the batch reads as "could not load"
 *   submitHeaders       optional headers of the submit request
 * and hooks, each given the drill `d` = { state, el, cfg, standalone,
 * languageId, t, later, renderInput, choose, openFeedback, advance }:
 *   bindTyped(d)              wire the typed-answer form
 *   digitKeys(state)          whether number keys pick an option right now
 *   onModeChange(d)           re-render the current item after a mode switch
 *   renderCurrent(d)          show state.items[state.cursor]
 *   renderInput(d)            show the answer input of the current item
 *   onChoice(d, idx)          option `idx` was picked (the item is locked)
 *   fillFeedback(d, ...args)  fill the feedback card (args of d.openFeedback)
 *   onAdvance(d)              optional, before moving to the next item
 *   onFinish(d, total)        optional, the batch is over (before results show)
 *   grade(pct)                results emoji
 *   submitBody(d, score, timing)   body of the submit request
 *   onSubmitted(d, resp)      show what the submit returned
 *   onSubmitError(d, err)
 */
export function mountDrill(container, ctx, cfg) {
  const standalone = (ctx && ctx.standalone) || null;
  const languageId = standalone ? cfg.languageId : (ctx && ctx.languageId) || cfg.languageId;
  const t = (key, params, fallback) => T(cfg.i18n + '.' + key, params, fallback);

  const state = {
    mode: localStorage.getItem(cfg.modeKey) || cfg.defaultMode,
    items: [],
    cursor: 0,
    correct: 0,
    errors: [],
    startTime: 0,
    currentOptions: [],
    isLocked: false,
    currentItem: null,
    itemResults: [],
    effectiveLevel: 1,
    finished: false,
    completed: false, // ctx.onComplete already called (guard against double-fire)
  };

  // ---- teardown bookkeeping -------------------------------------------------
  const timers = new Set();
  const docListeners = [];
  function later(fn, ms) {
    const id = setTimeout(() => {
      timers.delete(id);
      fn();
    }, ms);
    timers.add(id);
    return id;
  }
  function onDoc(type, fn) {
    document.addEventListener(type, fn);
    docListeners.push([type, fn]);
  }

  container.innerHTML = standalone ? cfg.pageMarkup : cfg.sessionMarkup;

  const el = {};
  Object.keys(ELEMENT_IDS).forEach((key) => {
    el[key] = container.querySelector('#' + cfg.prefix + ELEMENT_IDS[key]);
  });
  el.screen = container.querySelector('.drill-player');
  // The row shown while a batch is being played.
  const bar = el.header || el.controls;

  const d = {
    state,
    el,
    cfg,
    standalone,
    languageId,
    t,
    later,
    renderInput: () => {
      cfg.renderInput(d);
      syncDock();
    },
    choose: handleChoiceClick,
    openFeedback,
    advance,
  };
  const LOAD_FAILED = {};

  init();

  return {
    destroy() {
      timers.forEach(clearTimeout);
      timers.clear();
      docListeners.forEach(([type, fn]) => document.removeEventListener(type, fn));
      docListeners.length = 0;
    },
  };

  // ==========================================================================
  async function init() {
    try {
      if (standalone && standalone.prepare) await standalone.prepare();
      applyModeToToggle();
      bindModeToggle();
      el.fbContinue.addEventListener('click', closeFeedback);
      translateLocalKeys();
      bindResults();
      cfg.bindTyped(d);
      bindKeyboard();
      await loadBatch();
    } catch (err) {
      console.error(cfg.label + ' drill init error:', err);
      el.loading.textContent =
        t('error_init', null, 'Could not start the drill.') + ' ' + (err.message || '');
      el.loading.style.display = cfg.display.loading;
    }
  }

  function applyModeToToggle() {
    const buttons = el.modeToggle.querySelectorAll('button');
    buttons.forEach((b) => {
      const on = b.dataset.mode === state.mode;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', String(on));
    });
  }

  // Strings added by the 2026-11 redesign (static/i18n/_redesign/
  // trainers.json): the key's text, or the markup's English until the key is
  // merged into the locale files (a data-i18n would show the raw key).
  function translateLocalKeys() {
    container.querySelectorAll('[data-trk]').forEach((node) => {
      if (!node.dataset.trkFallback) node.dataset.trkFallback = node.textContent;
      node.textContent = T(node.dataset.trk, null, node.dataset.trkFallback);
    });
  }

  // The dock: Check while the typed answer is on screen, the tap hint while
  // options are. Feedback and the results hide both (trainers.css).
  function syncDock() {
    const typed = !!el.typedForm && el.typedForm.style.display !== 'none';
    if (el.check) el.check.hidden = !typed;
    if (el.hint) el.hint.hidden = typed;
  }

  // The results replace the prompt; their actions replace the dock's.
  function setResultsShown(show) {
    el.results.style.display = show ? cfg.display.results : 'none';
    if (el.screen) el.screen.classList.toggle('is-results', show);
  }

  function bindModeToggle() {
    el.modeToggle.addEventListener('click', function (e) {
      const btn = e.target.closest('button[data-mode]');
      if (!btn) return;
      if (cfg.ignoreSameMode && btn.dataset.mode === state.mode) return;
      state.mode = btn.dataset.mode;
      localStorage.setItem(cfg.modeKey, state.mode);
      applyModeToToggle();
      // Skipped while locked so switching mid-feedback cannot resurrect an
      // answered item.
      if (state.currentItem && !state.isLocked) cfg.onModeChange(d);
    });
  }

  function bindResults() {
    if (el.resultsContinue) el.resultsContinue.addEventListener('click', complete);
    if (el.resultsNext) {
      el.resultsNext.addEventListener('click', function () {
        setResultsShown(false);
        loadBatch();
      });
    }
    if (el.resultsExit) {
      el.resultsExit.addEventListener('click', function () {
        standalone.navigate(cfg.exitUrl);
      });
    }
  }

  function bindKeyboard() {
    onDoc('keydown', function (e) {
      if (el.feedback.classList.contains('show')) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          closeFeedback();
        }
        return;
      }
      if (!cfg.digitKeys(state)) return;
      const idx = parseInt(e.key, 10);
      if (idx >= 1 && idx <= state.currentOptions.length) {
        e.preventDefault();
        handleChoiceClick(idx - 1);
      }
    });
  }

  // ---- loading a batch ------------------------------------------------------

  function loadFailed(status) {
    const msg =
      t('error_load', null, 'Couldn’t load the drill.') + (status ? ' (' + status + ')' : '');
    if (standalone) el.loading.textContent = msg;
    else showEmptyState(msg);
    return LOAD_FAILED;
  }

  async function fetchBatch() {
    const url = sessionUrl(cfg.apiBase, languageId);
    if (standalone && cfg.lenientLoad) {
      try {
        const resp = await window.authFetch(url);
        return await resp.json();
      } catch {
        return loadFailed(null);
      }
    }
    let resp;
    try {
      resp = await window.authFetch(url);
    } catch (e) {
      if (standalone) throw e;
      console.error(cfg.label + ' drill load failed:', e);
      return loadFailed(null);
    }
    if (!resp.ok) return loadFailed(resp.status);
    return resp.json();
  }

  async function loadBatch() {
    el.loading.style.display = cfg.display.loading;
    el.stage.style.display = 'none';
    setResultsShown(false);
    bar.style.display = 'none';
    if (el.empty) el.empty.style.display = 'none';

    const pre = await takePrefetch(ctx && ctx.item);
    const data = pre ? pre.data : await fetchBatch();
    if (data === LOAD_FAILED) return;

    const items = (data && ((data.data && data.data.items) || data.items)) || [];
    if (!items.length) return showNoItems();

    state.items = items;
    state.cursor = 0;
    state.correct = 0;
    state.errors = [];
    state.itemResults = [];
    state.startTime = Date.now();
    state.isLocked = false;
    state.finished = false;

    el.progressTotal.textContent = items.length;
    el.loading.style.display = 'none';
    bar.style.display = cfg.display.bar;
    el.stage.style.display = cfg.display.stage;
    renderCurrent();
  }

  function showNoItems() {
    if (!standalone) {
      return showEmptyState(t('error_empty', null, 'No drill items right now — you can move on.'));
    }
    if (el.empty) {
      el.loading.style.display = 'none';
      el.empty.style.display = '';
    } else {
      el.loading.textContent = t('error_empty');
    }
  }

  // Session: no items / load failure. Let the session advance via Continue.
  function showEmptyState(msg) {
    el.controls.style.display = 'none';
    el.stage.style.display = 'none';
    el.loading.style.display = 'none';
    setResultsShown(true);
    el.resultsGrade.textContent = '👍';
    el.resultsPct.parentElement.style.display = 'none';
    el.results.querySelector('.cd-results-stats').style.display = 'none';
    if (el.resultsNote) el.resultsNote.textContent = msg;
    el.resultsContinue.textContent = T('session.next_item', null, 'Next');
  }

  // ---- playing --------------------------------------------------------------
  function renderCurrent() {
    if (state.cursor >= state.items.length) return finishBatch();
    cfg.renderCurrent(d);
    syncDock();
    // A new item starts at the top of the stage.
    const scroller = el.stage.closest('.ld-stage');
    if (scroller) scroller.scrollTop = 0;
  }

  function handleChoiceClick(idx) {
    if (state.isLocked) return;
    state.isLocked = true;
    cfg.onChoice(d, idx);
  }

  function openFeedback(...args) {
    cfg.fillFeedback(d, ...args);
    el.feedback.classList.add('show');
    el.fbContinue.focus();
  }

  function closeFeedback() {
    el.feedback.classList.remove('show');
    advance();
  }

  function advance() {
    if (cfg.onAdvance) cfg.onAdvance(d);
    state.cursor += 1;
    renderCurrent();
  }

  // ---- finishing ------------------------------------------------------------
  async function finishBatch() {
    if (state.finished) return;
    state.finished = true;

    const total = state.items.length;
    const correct = state.correct;
    const pct = total ? Math.round((correct / total) * 100) : 0;
    const finishedAtMs = Date.now();
    const time = Math.round((finishedAtMs - state.startTime) / 1000);

    el.stage.style.display = 'none';
    if (cfg.onFinish) cfg.onFinish(d, total);

    el.resultsPct.textContent = pct;
    el.resultsCorrect.textContent = correct;
    el.resultsTotal.textContent = total;
    el.resultsTime.textContent = time;
    el.resultsGrade.textContent = cfg.grade(pct);
    setResultsShown(true);
    const scroller = el.results.closest('.ld-stage');
    if (scroller) scroller.scrollTop = 0;

    // Submit (best-effort): records the attempt and its ELO change.
    try {
      const request = {
        method: 'POST',
        body: JSON.stringify(
          cfg.submitBody(
            d,
            {
              language_id: languageId,
              correct_items: correct,
              total_items: total,
              time_taken: time,
            },
            {
              started_at: state.startTime ? new Date(state.startTime).toISOString() : null,
              finished_at: new Date(finishedAtMs).toISOString(),
            }
          )
        ),
      };
      if (cfg.submitHeaders) request.headers = cfg.submitHeaders;
      const resp = await window.authFetch(cfg.apiBase + '/submit', request);
      await cfg.onSubmitted(d, resp);
    } catch (e) {
      cfg.onSubmitError(d, e);
    }
  }

  // Session: mark the item complete and let the controller advance. Guarded so
  // a double tap / Enter can't fire onComplete twice.
  function complete() {
    if (state.completed) return;
    state.completed = true;
    const total = state.items.length;
    ctx.onComplete({ correct: state.correct, total: total, mode: cfg.testType });
  }
}

// ==========================================================================
// MARKUP. One task screen per host (see the header comment); the session copy
// has a control row (mode + progress) instead of the page's strip and a
// single Next on the results. Styles: static/css/redesign/trainers.css.
// ==========================================================================
const MODE_TOGGLE = `
        <div class="ld-seg cd-mode-toggle drill-modes" id="cdModeToggle" title="Auto adapts each item to your per-classifier mastery">
            <button type="button" data-mode="auto" class="active" aria-pressed="true" data-i18n="classifier_drill.mode_auto">Auto</button>
            <button type="button" data-mode="mc" aria-pressed="false" data-i18n="classifier_drill.mode_mc">Choose</button>
            <button type="button" data-mode="type" aria-pressed="false" data-i18n="classifier_drill.mode_type">Type</button>
        </div>`;

// The control row: mode toggle, Auto's level badge, count and bar. `id` and
// `cls` name the row (cdControls in the session, cdHeader on the page).
const strip = (id, cls) => `
<div id="${id}" class="${cls} drill-strip" style="display:none;">
    <div class="drill-strip__row">
        ${MODE_TOGGLE}
        <div class="drill-count">
            <span class="ld-tag ld-tag--info" id="cdLevelBadge" style="display:none;"></span>
            <span class="drill-count__n"><span id="cdProgressLabel">0</span> / <span id="cdProgressTotal">0</span></span>
        </div>
    </div>
    <div class="ld-bar drill-bar"><i class="cd-progress-fill" id="cdProgressFill"></i></div>
</div>`;

// The prompt and answer inputs: the same in both hosts.
const STAGE_MARKUP = `
<div id="cdStage" class="cd-stage" style="display:none;">
    <div class="cd-prompt" id="cdPromptWrap" lang="zh">
        <span>一</span>
        <span class="cd-blank" id="cdPromptBlank">_</span>
        <span id="cdNoun"></span>
    </div>
    <div class="cd-pronunciation" id="cdPronunciation"></div>
    <div class="cd-gloss" id="cdGloss"></div>
    <div class="cd-gloss cd-reverse" id="cdReversePrompt" style="display:none;"></div>

    <div class="cd-options" id="cdOptions" style="display:none;" lang="zh"></div>

    <form id="cdTypedForm" style="display:none;" autocomplete="off">
        <input id="cdTypedInput" type="text" class="cd-typed-input" maxlength="2"
               inputmode="text" autocapitalize="off" lang="zh"
               data-i18n-placeholder="classifier_drill.typed_placeholder"
               aria-label="量词"
               placeholder="量词" />
    </form>
</div>`;

// The dock: feedback (shown with .show), Check for a typed answer, the tap
// hint for options, and the results actions (shown on .is-results).
const dock = (resultsActions) => `
<div class="ld-dock drill-dock">
    <div id="cdFeedback" class="cd-feedback drill-feedback" role="region" aria-live="polite">
        <div class="cd-feedback-card drill-feedback__card">
            <div class="cd-feedback-canonical" id="cdFeedbackCanonical" lang="zh"></div>
            <div class="cd-feedback-group" id="cdFeedbackGroup"></div>
            <div class="cd-feedback-examples" id="cdFeedbackExamples"></div>
        </div>
        <button type="button" class="cd-feedback-cta ld-btn" id="cdFeedbackContinue" data-i18n="classifier_drill.feedback_continue">Continue</button>
    </div>
    <button type="submit" form="cdTypedForm" class="ld-btn drill-check" id="cdCheck" hidden data-trk="trainers.check">Check</button>
    <p class="ld-hint drill-hint" id="cdHint" data-trk="trainers.drill_tap_hint">Tap an answer.</p>
    <div class="drill-results-actions">${resultsActions}</div>
</div>`;

const resultsBody = (note) => `
    <div id="cdResults" class="cd-results drill-results" style="display:none;">
        <div class="drill-results__score">
            <div class="cd-results-grade" id="cdResultsGrade" aria-hidden="true">🎯</div>
            <div class="cd-results-pct"><span id="cdResultsPct">0</span>%</div>
        </div>
        <div class="cd-results-stats">
            <div><strong id="cdResultsCorrect">0</strong> / <span id="cdResultsTotal">0</span> <span data-i18n="classifier_drill.results_classifiers">classifiers</span></div>
            <div><strong id="cdResultsTime">0</strong>s</div>
        </div>
        ${note}
        <div class="cd-results-elo-badge ld-tag ld-tag--ok" id="cdResultsElo" style="display:none;"></div>
    </div>`;

const SESSION_MARKUP = `
<div class="ld-screen drill-player drill-player--cd">
${strip('cdControls', 'cd-controls')}
<div class="ld-stage drill-stage">
    <div id="cdLoading" class="drill-msg" data-i18n="classifier_drill.loading" style="display:none;">Loading…</div>
    ${STAGE_MARKUP}
    ${resultsBody('<div id="cdResultsNote" class="drill-results__note"></div>')}
</div>
${dock('<button type="button" class="cd-feedback-cta ld-btn" id="cdResultsContinue" data-i18n="session.next_item">Next</button>')}
</div>
`;

const PAGE_MARKUP = `
<div class="ld-screen drill-player drill-player--cd">
${strip('cdHeader', 'cd-header')}
<div class="ld-stage drill-stage">
    <div id="cdLoading" class="drill-msg" data-i18n="classifier_drill.loading">Loading…</div>
    ${STAGE_MARKUP}
    ${resultsBody('')}
</div>
${dock(`<div class="ld-row cd-results-actions">
        <button type="button" class="cd-feedback-cta ld-btn ld-btn--ghost" id="cdResultsNext" data-i18n="classifier_drill.results_next">Next round</button>
        <button type="button" class="cd-feedback-cta ld-btn" id="cdResultsExit" data-i18n="classifier_drill.results_exit">Done</button>
    </div>`)}
</div>
`;

// ==========================================================================
// CLASSIFIER — Chinese measure words. An item is shown at one of four levels:
// 1 choose the classifier, 2 type it, 3 reverse (choose the noun), 4 cloze.
// ==========================================================================
function classifierLevel(state, item) {
  if (state.mode === 'mc') return 1;
  if (state.mode === 'type') return 2;
  // Auto: the server-stamped per-classifier level (get_classifier_drill_session_v2
  // already lowers it to what the item's content supports), lowered again here
  // if the content is missing: Fill in needs a cloze sentence, Reverse needs
  // wrong nouns to offer; Type needs nothing.
  let lvl = Math.max(1, Math.min(4, parseInt(item.level || 1, 10) || 1));
  const reverseOk = (item.reverse_noun_options || []).length > 0;
  if (lvl === 4 && !item.cloze_blanked) lvl = reverseOk ? 3 : 2;
  if (lvl === 3 && !reverseOk) lvl = 2;
  return lvl;
}

// Shown in Auto mode only, to make promotions and demotions visible: the
// level the item is drawn at, named like the mode toggle (Choose / Type)
// where it matches.
function updateLevelBadge({ state, el, t }) {
  if (state.mode === 'auto') {
    const shown = state.effectiveLevel;
    const tag =
      shown === 1
        ? t('mode_mc', null, 'Choose')
        : shown === 2
          ? t('mode_type', null, 'Type')
          : shown === 3
            ? t('level_reverse', null, 'Reverse')
            : t('level_cloze', null, 'Fill in');
    el.levelBadge.textContent = tag;
    el.levelBadge.style.display = 'inline';
  } else {
    el.levelBadge.style.display = 'none';
  }
}

function resetClassifierPrompt({ el }) {
  el.promptBlank.style.color = '';
  el.promptBlank.style.borderBottom = '';
}

function renderClassifierOptions(d, withPinyin) {
  const { state, el } = d;
  el.options.innerHTML = '';
  state.currentOptions.forEach(function (opt, idx) {
    const btn = document.createElement('button');
    btn.className = 'cd-option';
    btn.type = 'button';
    btn.dataset.idx = idx;
    btn.innerHTML =
      '<span class="cd-option-key" aria-hidden="true">' +
      (idx + 1) +
      '</span>' +
      '<span class="cd-option-text">' +
      escapeHtml(opt.hanzi) +
      '</span>' +
      (withPinyin && opt.pinyin
        ? '<span class="cd-option-pinyin">' + escapeHtml(formatPinyin(opt.pinyin)) + '</span>'
        : '');
    btn.addEventListener('click', function () {
      d.choose(idx);
    });
    el.options.appendChild(btn);
  });
}

function renderClassifierMc(d) {
  const { state } = d;
  const item = state.currentItem;
  const correctHanzi = (item.correct_classifier_hanzi || [])[0];
  const correctId = (item.correct_classifier_ids || [])[0];
  const distractorIds = item.distractor_ids || [];
  const distractorHanzi = item.distractor_hanzi || [];
  const distractorPinyin = item.distractor_pinyin || [];

  // Every option carries its pinyin, the correct one included: when only
  // the wrong options had it, the answer was the one without.
  const correctPinyin = (item.correct_classifier_pinyin || [])[0] || '';
  const showPinyin = !!correctPinyin;
  const pool = [{ id: correctId, hanzi: correctHanzi, pinyin: correctPinyin, is_correct: true }];
  for (let i = 0; i < distractorIds.length; i++) {
    pool.push({
      id: distractorIds[i],
      hanzi: distractorHanzi[i] || '',
      pinyin: showPinyin ? distractorPinyin[i] || '' : '',
      is_correct: false,
    });
  }
  state.currentOptions = shuffle(pool);
  renderClassifierOptions(d, true);
}

function renderClassifierCloze(d) {
  const { state, el, t } = d;
  const blanked = state.currentItem.cloze_blanked || '';
  // The sentence is the prompt: no "一 _ noun" line above it.
  el.promptWrap.style.display = 'none';
  el.promptBlank.textContent = '';
  el.noun.textContent = '';
  el.pronunciation.textContent = '';
  el.gloss.textContent = '';
  el.reversePrompt.style.display = 'block';
  el.reversePrompt.innerHTML =
    '<div class="cd-cloze-label">' +
    t('cloze_prompt', null, 'Fill in the measure word') +
    '</div>' +
    '<div class="cd-cloze" lang="zh">' +
    escapeHtml(blanked).replace(/___/g, '<span class="cd-cloze-blank">&nbsp;___&nbsp;</span>') +
    '</div>';
  el.typedForm.style.display = 'none';
  el.options.style.display = 'grid';
  renderClassifierMc(d);
}

function renderClassifierForward({ state, el }) {
  const item = state.currentItem;
  el.promptWrap.style.display = 'block';
  el.reversePrompt.style.display = 'none';
  el.promptBlank.textContent = '_';
  el.noun.textContent = item.noun_lemma || '';
  // Tone-marked pinyin only (stored values can be "bi3" or "biàn dé (bian4 de2)").
  el.pronunciation.textContent = formatPinyin(item.noun_pronunciation);
  el.gloss.textContent = item.noun_gloss || '';
}

function renderClassifierReverse(d) {
  const { state, el, t } = d;
  const item = state.currentItem;
  const canonical = (item.correct_classifier_hanzi || [])[0] || '';
  el.promptWrap.style.display = 'block';
  el.promptBlank.textContent = canonical;
  el.promptBlank.style.color = 'var(--brand)';
  el.promptBlank.style.borderBottom = 'none';
  el.noun.textContent = '?';
  el.pronunciation.textContent = '';
  el.gloss.textContent = '';
  el.reversePrompt.style.display = 'block';
  el.reversePrompt.textContent = t(
    'reverse_question',
    { classifier: canonical },
    'Which noun takes ' + canonical + '?'
  );

  const pool = [
    {
      id: 'noun:' + (item.noun_lemma || ''),
      hanzi: item.noun_lemma || '',
      pinyin: '',
      is_correct: true,
    },
  ];
  (item.reverse_noun_options || []).forEach(function (n) {
    pool.push({ id: 'noun:' + n, hanzi: n, pinyin: '', is_correct: false });
  });
  state.currentOptions = shuffle(pool);

  el.typedForm.style.display = 'none';
  el.options.style.display = 'grid';
  renderClassifierOptions(d, false);
}

function recordClassifierAnswer({ state }, isCorrect, picked) {
  const cid = state.currentItem.classifier_id_primary;
  if (typeof cid === 'number') {
    state.itemResults.push({
      classifier_id: cid,
      is_correct: !!isCorrect,
      level: state.effectiveLevel,
    });
  }
  if (isCorrect) {
    state.correct += 1;
  } else {
    state.errors.push({
      lemma: state.currentItem.noun_lemma,
      picked: picked,
      correct: state.currentItem.correct_classifier_hanzi,
      ts: Date.now(),
    });
  }
}

function clearMasteryChanges(el) {
  el.results.querySelectorAll('.drill-mastery').forEach((n) => n.remove());
}

// Standalone page: say how many classifiers moved up or down a level.
function showMasteryChanges({ el, t }, updates) {
  clearMasteryChanges(el);
  const promotions = updates.filter((u) => u && u.promoted);
  const demotions = updates.filter((u) => u && u.demoted);
  if (!promotions.length && !demotions.length) return;
  const banner = document.createElement('div');
  banner.className = 'ld-note drill-mastery';
  let html = '';
  if (promotions.length) {
    html += '<div>🎓 ' + t('promoted_n', { count: promotions.length }) + '</div>';
  }
  if (demotions.length) {
    html += '<div>↩️ ' + t('demoted_n', { count: demotions.length }) + '</div>';
  }
  banner.innerHTML = html;
  el.results.appendChild(banner);
}

export const CLASSIFIER = {
  kind: 'classifier',
  testType: 'classifier_drill',
  label: 'Classifier',
  apiBase: '/api/classifier-drill',
  languageId: 1, // Chinese
  i18n: 'classifier_drill',
  prefix: 'cd',
  modeKey: 'cd_mode',
  defaultMode: 'auto',
  ignoreSameMode: false,
  display: { loading: 'block', bar: 'flex', stage: 'block', results: 'block' },
  exitUrl: '/tests',
  pageMarkup: PAGE_MARKUP,
  sessionMarkup: SESSION_MARKUP,

  bindTyped(d) {
    const { state, el, later } = d;
    el.typedForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (state.isLocked || !state.currentItem) return;
      const raw = (el.typedInput.value || '').trim();
      if (!raw) return;
      const correctHanzi = state.currentItem.correct_classifier_hanzi || [];
      const isCorrect = correctHanzi.indexOf(raw) !== -1;
      state.isLocked = true;
      recordClassifierAnswer(d, isCorrect, raw);
      if (isCorrect) {
        el.typedInput.classList.add('correct');
        later(d.advance, 400);
      } else {
        el.typedInput.classList.add('wrong');
        later(function () {
          d.openFeedback(raw);
        }, 250);
      }
    });
  },

  // Keys 1-4 pick an option everywhere but in typed mode.
  digitKeys: (state) => !state.isLocked && !!state.currentItem && state.effectiveLevel !== 2,

  onModeChange(d) {
    resetClassifierPrompt(d);
    d.state.effectiveLevel = classifierLevel(d.state, d.state.currentItem);
    updateLevelBadge(d);
    d.renderInput();
  },

  renderCurrent(d) {
    const { state, el } = d;
    // Drop focus so the previous question's tapped option does not carry a
    // sticky :focus / :hover state into the new render (mobile).
    if (document.activeElement && typeof document.activeElement.blur === 'function') {
      document.activeElement.blur();
    }
    state.currentItem = state.items[state.cursor];
    state.isLocked = false;
    state.effectiveLevel = classifierLevel(state, state.currentItem);

    el.progressLabel.textContent = String(state.cursor + 1);
    el.progressFill.style.width = (100 * state.cursor) / state.items.length + '%';
    updateLevelBadge(d);
    d.renderInput();
  },

  renderInput(d) {
    const { state, el } = d;
    const lvl = state.effectiveLevel;
    if (lvl === 4) {
      renderClassifierCloze(d);
      return;
    }
    if (lvl === 3) {
      renderClassifierReverse(d);
      return;
    }
    renderClassifierForward(d);
    if (lvl === 2) {
      el.typedForm.style.display = 'block';
      el.options.style.display = 'none';
      el.typedInput.value = '';
      el.typedInput.classList.remove('wrong', 'correct');
      requestAnimationFrame(() => el.typedInput.focus());
    } else {
      el.typedForm.style.display = 'none';
      el.options.style.display = 'grid';
      renderClassifierMc(d);
    }
  },

  onChoice(d, idx) {
    const { state, el, later } = d;
    const opt = state.currentOptions[idx];

    let isCorrect;
    if (state.effectiveLevel === 3) {
      isCorrect = !!opt.is_correct;
    } else {
      const correctIds = state.currentItem.correct_classifier_ids || [];
      isCorrect = correctIds.indexOf(opt.id) !== -1;
    }
    recordClassifierAnswer(d, isCorrect, opt.hanzi);

    const buttons = el.options.querySelectorAll('.cd-option');
    buttons.forEach(function (b) {
      b.disabled = true;
    });

    // Drop focus so mobile WebKit doesn't paint a sticky ring on the tapped
    // option; the .correct / .wrong classes carry the feedback.
    const clickedBtn = buttons[idx];
    if (clickedBtn && typeof clickedBtn.blur === 'function') clickedBtn.blur();

    if (isCorrect) {
      clickedBtn.classList.add('correct');
      later(d.advance, 400);
    } else {
      clickedBtn.classList.add('wrong');
      state.currentOptions.forEach(function (o, i) {
        if (o.is_correct) buttons[i].classList.add('correct');
      });
      later(function () {
        d.openFeedback(opt.hanzi);
      }, 280);
    }
  },

  fillFeedback({ state, el, t }, picked) {
    const item = state.currentItem;
    const canonical = (item.correct_classifier_hanzi || [])[0] || '';
    const altList = (item.correct_classifier_hanzi || []).slice(1);
    const altSuffix = altList.length
      ? ' <span class="cd-feedback-alt">(' +
        t('also', null, 'also') +
        ': ' +
        altList.map(escapeHtml).join(' / ') +
        ')</span>'
      : '';
    el.fbCanonical.innerHTML =
      '一 <span class="hl">' +
      escapeHtml(canonical) +
      '</span> ' +
      escapeHtml(item.noun_lemma || '') +
      altSuffix;
    el.fbGroup.textContent = item.semantic_label || '';
    el.fbExamples.textContent = t('your_answer', null, 'Your answer') + ': ' + picked;
  },

  onAdvance: resetClassifierPrompt,

  onFinish({ el }, total) {
    // The session's control row goes; the page keeps its header.
    if (el.controls) el.controls.style.display = 'none';
    // A previous round's ELO and level changes are not this round's.
    clearMasteryChanges(el);
    el.resultsElo.style.display = 'none';
    // The level badge names the item on screen; the results have none.
    el.levelBadge.style.display = 'none';
    el.progressFill.style.width = '100%';
    el.progressLabel.textContent = String(total);
  },

  grade: (pct) => (pct >= 95 ? '🏆' : pct >= 80 ? '🎯' : pct >= 60 ? '👍' : '💪'),

  submitBody: ({ state }, score, timing) => ({
    ...score,
    item_results: state.itemResults,
    started_at: timing.started_at,
    finished_at: timing.finished_at,
  }),

  async onSubmitted(d, resp) {
    if (!resp.ok) return;
    const { el, t } = d;
    const payload = await resp.json();
    const result = (payload && (payload.data || payload)) || {};
    const elo = result.user_elo_change || {};
    if (typeof elo.change === 'number' && elo.change !== 0) {
      const sign = elo.change > 0 ? '+' : '';
      el.resultsElo.textContent = t(
        'results_elo',
        { value: sign + elo.change },
        'ELO ' + sign + elo.change
      );
      el.resultsElo.style.display = 'inline-block';
    } else if (typeof elo.change === 'number') {
      el.resultsElo.textContent = t('results_elo_unchanged', null, 'ELO unchanged');
      el.resultsElo.style.display = 'inline-block';
    }
    if (d.standalone) showMasteryChanges(d, result.mastery_updates || []);
  },

  onSubmitError(d, err) {
    console.error('Classifier drill submit failed:', err);
  },
};
