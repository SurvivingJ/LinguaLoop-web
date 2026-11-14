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
//    which passes ctx.standalone. The page markup has its own sticky header and
//    a results card offering another round or the way out.
//
// Player contract: mount(container, ctx) -> { destroy() }.
//   ctx = { item, languageId, onComplete(result), onSkip() }.
// All DOM is scoped to `container`, and every document-level listener / timer
// is tracked and torn down in destroy().

import { T, escapeHtml, shuffle, applyI18n } from '../dom.js';
import { prefetchJson, takePrefetch } from '../prefetch.js';

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
    renderInput: () => cfg.renderInput(d),
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
    buttons.forEach((b) => b.classList.toggle('active', b.dataset.mode === state.mode));
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
        el.results.style.display = 'none';
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
    el.results.style.display = 'none';
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
    el.results.style.display = 'block';
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
    el.results.style.display = cfg.display.results;

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
// MARKUP. The session copy is self-contained (inline <style>) and has no
// page-level sticky header: the session shell already has a sticky progress
// bar, so the drill's own progress sits in a non-sticky control row. The page
// copy is styled by static/css/pages/drill.css.
// ==========================================================================
const SESSION_STYLES = `
<style>
    .cd-controls { max-width: 640px; margin: 8px auto 0; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
    .cd-controls-progress { display: flex; align-items: center; gap: 10px; font-size: 0.9rem; color: var(--text-muted); }
    .cd-progress-track { width: 120px; height: 6px; background: var(--border-default); border-radius: 3px; overflow: hidden; }
    .cd-progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary) 0%, var(--info) 100%); transition: width 0.3s ease; width: 0; }
    .cd-stage { max-width: 640px; margin: 0 auto; padding: 32px 20px; }
    .cd-prompt { text-align: center; font-size: 3.5rem; font-weight: 700; letter-spacing: 0.1em; color: var(--text-primary); margin-bottom: 12px; line-height: 1.1; }
    .cd-blank { display: inline-block; min-width: 1.2em; border-bottom: 4px solid var(--info); color: transparent; }
    .cd-pronunciation { text-align: center; font-size: 1.5rem; color: var(--text-muted); margin-bottom: 4px; }
    .cd-gloss { text-align: center; font-size: 1.05rem; color: var(--text-secondary); margin-bottom: 36px; }
    .cd-options { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 28px; }
    .cd-option { font-size: 2.25rem; font-weight: 600; padding: 18px 8px; border: 2px solid var(--border-default); border-radius: 12px; background: var(--bg-surface); cursor: pointer; transition: transform 0.1s, border-color 0.1s, background 0.15s; position: relative; display: flex; flex-direction: column; align-items: center; gap: 4px; }
    @media (hover: hover) and (pointer: fine) { .cd-option:hover:not(:disabled) { border-color: var(--primary); transform: translateY(-1px); } }
    .cd-option:focus { outline: none; }
    .cd-option:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
    .cd-option:disabled { cursor: default; opacity: 0.65; }
    .cd-option.correct  { background: #ecfdf5; border-color: #10b981; }
    .cd-option.wrong    { background: #fef2f2; border-color: #ef4444; }
    .cd-option .cd-option-key { position: absolute; top: 6px; left: 8px; font-size: 0.75rem; color: var(--text-muted); font-weight: 500; }
    .cd-option .cd-option-pinyin { font-size: 0.95rem; color: var(--text-muted); font-weight: 400; }
    .cd-typed-input { display: block; width: 100%; font-size: 2.5rem; font-weight: 600; text-align: center; padding: 14px 8px; border: 2px solid var(--border-default); border-radius: 12px; background: var(--bg-surface); outline: none; transition: border-color 0.1s; }
    .cd-typed-input:focus { border-color: var(--primary); }
    .cd-typed-input.wrong { border-color: #ef4444; background: #fef2f2; }
    .cd-typed-input.correct { border-color: #10b981; background: #ecfdf5; }
    .cd-feedback { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.65); display: none; align-items: center; justify-content: center; z-index: 1050; padding: 20px; }
    .cd-feedback.show { display: flex; }
    .cd-feedback-card { background: var(--bg-surface); border-radius: 16px; padding: 28px; max-width: 480px; width: 100%; box-shadow: var(--shadow-lg); }
    .cd-feedback-canonical { font-size: 3rem; text-align: center; font-weight: 700; margin: 8px 0 4px; }
    .cd-feedback-canonical .hl { color: var(--info); }
    .cd-feedback-group { text-align: center; font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 18px; }
    .cd-feedback-examples { background: var(--bg-page); border-radius: 10px; padding: 12px 16px; font-size: 1rem; margin-bottom: 18px; }
    .cd-feedback-cta { width: 100%; background: var(--primary); color: white; font-weight: 600; padding: 14px; border-radius: 10px; border: 0; cursor: pointer; font-size: 1rem; }
    .cd-results { max-width: 480px; margin: 40px auto; padding: 36px 28px; background: var(--bg-surface); border-radius: 16px; box-shadow: var(--shadow-md); text-align: center; }
    .cd-results-grade { font-size: 4rem; margin: 8px 0; }
    .cd-results-pct { font-size: 2.5rem; font-weight: 700; color: var(--primary); }
    .cd-results-stats { display: flex; justify-content: center; gap: 36px; margin: 20px 0 24px; font-size: 0.95rem; color: var(--text-secondary); }
    .cd-results-elo-badge { display: inline-block; padding: 6px 14px; border-radius: 999px; background: var(--bg-page); font-weight: 600; margin-bottom: 18px; }
    .cd-mode-toggle { display: inline-flex; background: var(--bg-page); border-radius: 999px; padding: 4px; }
    .cd-mode-toggle button { background: transparent; border: 0; padding: 6px 14px; border-radius: 999px; font-size: 0.85rem; font-weight: 500; color: var(--text-muted); cursor: pointer; }
    .cd-mode-toggle button.active { background: var(--bg-surface); color: var(--text-primary); box-shadow: var(--shadow-sm); }
    @media (max-width: 640px) {
        .cd-stage { padding: 20px 14px; }
        .cd-prompt { font-size: 2.5rem; letter-spacing: 0.05em; }
        .cd-pronunciation { font-size: 1.2rem; }
        .cd-gloss { font-size: 0.95rem; margin-bottom: 24px; }
        .cd-options { gap: 10px; margin-top: 20px; }
        .cd-option { font-size: 1.85rem; padding: 16px 6px; min-height: 76px; }
        .cd-typed-input { font-size: 2rem; padding: 12px 6px; }
        .cd-feedback-card { padding: 22px 18px; }
        .cd-feedback-canonical { font-size: 2.1rem; }
        .cd-mode-toggle button { padding: 5px 10px; font-size: 0.8rem; }
        #cdReversePrompt { font-size: 1rem !important; }
    }
</style>
`;

// Prompt, answer inputs and the feedback card: the same in both hosts.
const STAGE_MARKUP = `
<div id="cdStage" class="cd-stage" style="display:none;">
    <div class="cd-prompt" id="cdPromptWrap">
        <span>一</span>
        <span class="cd-blank" id="cdPromptBlank">_</span>
        <span id="cdNoun"></span>
    </div>
    <div class="cd-pronunciation" id="cdPronunciation"></div>
    <div class="cd-gloss" id="cdGloss"></div>
    <div class="cd-gloss" id="cdReversePrompt" style="display:none; font-size:1.1rem; color:var(--text-secondary);"></div>

    <div class="cd-options" id="cdOptions" style="display:none;"></div>

    <form id="cdTypedForm" style="display:none;" autocomplete="off">
        <input id="cdTypedInput" type="text" class="cd-typed-input" maxlength="2"
               inputmode="text" autocapitalize="off"
               data-i18n-placeholder="classifier_drill.typed_placeholder"
               placeholder="量词" />
    </form>
</div>

<div id="cdFeedback" class="cd-feedback" role="dialog" aria-modal="true">
    <div class="cd-feedback-card">
        <div class="cd-feedback-canonical" id="cdFeedbackCanonical"></div>
        <div class="cd-feedback-group" id="cdFeedbackGroup"></div>
        <div class="cd-feedback-examples" id="cdFeedbackExamples"></div>
        <button class="cd-feedback-cta" id="cdFeedbackContinue" data-i18n="classifier_drill.feedback_continue">Continue</button>
    </div>
</div>
`;

const SESSION_MARKUP = `${SESSION_STYLES}
<div id="cdLoading" class="text-center py-5 text-muted" data-i18n="classifier_drill.loading" style="display:none;">Loading…</div>

<div id="cdControls" class="cd-controls" style="display:none;">
    <div class="cd-mode-toggle" id="cdModeToggle" title="Auto adapts each item to your per-classifier mastery">
        <button type="button" data-mode="auto" class="active" data-i18n="classifier_drill.mode_auto">Auto</button>
        <button type="button" data-mode="mc"   data-i18n="classifier_drill.mode_mc">Choose</button>
        <button type="button" data-mode="type" data-i18n="classifier_drill.mode_type">Type</button>
    </div>
    <div class="cd-controls-progress">
        <span id="cdLevelBadge" style="display:none;"></span>
        <span><span id="cdProgressLabel">0</span> / <span id="cdProgressTotal">0</span></span>
        <div class="cd-progress-track"><div class="cd-progress-fill" id="cdProgressFill"></div></div>
    </div>
</div>
${STAGE_MARKUP}
<div id="cdResults" class="cd-results" style="display:none;">
    <div class="cd-results-grade" id="cdResultsGrade">🎯</div>
    <div class="cd-results-pct"><span id="cdResultsPct">0</span>%</div>
    <div class="cd-results-stats">
        <div><strong id="cdResultsCorrect">0</strong> / <span id="cdResultsTotal">0</span> <span data-i18n="classifier_drill.results_classifiers">classifiers</span></div>
        <div><strong id="cdResultsTime">0</strong>s</div>
    </div>
    <div id="cdResultsNote" class="text-muted" style="display:block; margin-bottom:12px;"></div>
    <div class="cd-results-elo-badge" id="cdResultsElo" style="display:none;"></div>
    <button class="cd-feedback-cta" id="cdResultsContinue" data-i18n="session.next_item">Next</button>
</div>
`;

const PAGE_MARKUP = `
<div id="cdHeader" class="cd-header py-3 px-3 px-md-4 flex items-center justify-between gap-2" style="display:none;">
    <div class="cd-header-left">
        <a href="/tests" class="text-slate-500 hover:text-slate-700" aria-label="Home" style="font-size: 1.1rem; line-height: 1;">&larr;</a>
        <h1 class="text-base font-semibold" data-i18n="classifier_drill.title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Measure Words</h1>
    </div>
    <div class="cd-header-right">
        <div class="text-xs text-slate-500" id="cdLevelBadge" style="display:none;"></div>
        <div class="text-sm text-slate-500" style="white-space: nowrap;"><span id="cdProgressLabel">0</span> / <span id="cdProgressTotal">0</span></div>
    </div>
    <div class="cd-header-controls">
        <div class="cd-mode-toggle" id="cdModeToggle" title="Auto adapts each item to your per-classifier mastery">
            <button type="button" data-mode="auto" class="active" data-i18n="classifier_drill.mode_auto">Auto</button>
            <button type="button" data-mode="mc"   data-i18n="classifier_drill.mode_mc">Choose</button>
            <button type="button" data-mode="type" data-i18n="classifier_drill.mode_type">Type</button>
        </div>
    </div>
    <div class="cd-progress-bar"><div class="cd-progress-fill" id="cdProgressFill"></div></div>
</div>

<div id="cdLoading" class="text-center py-20 text-slate-500" data-i18n="classifier_drill.loading">Loading…</div>
${STAGE_MARKUP}
<div id="cdResults" class="cd-results" style="display:none;">
    <div class="cd-results-grade" id="cdResultsGrade">🎯</div>
    <div class="cd-results-pct"><span id="cdResultsPct">0</span>%</div>
    <div class="cd-results-stats">
        <div><strong id="cdResultsCorrect">0</strong> / <span id="cdResultsTotal">0</span> <span data-i18n="classifier_drill.results_classifiers">classifiers</span></div>
        <div><strong id="cdResultsTime">0</strong>s</div>
    </div>
    <div class="cd-results-elo-badge" id="cdResultsElo" style="display:none;"></div>
    <div class="cd-results-actions">
        <button class="cd-feedback-cta" id="cdResultsNext" data-i18n="classifier_drill.results_next">Next round</button>
        <button class="cd-feedback-cta" id="cdResultsExit" style="background: var(--bg-page); color: var(--text-primary);" data-i18n="classifier_drill.results_exit">Done</button>
    </div>
</div>
`;

// ==========================================================================
// CLASSIFIER — Chinese measure words. An item is shown at one of four levels:
// 1 choose the classifier, 2 type it, 3 reverse (choose the noun), 4 cloze.
// ==========================================================================
function classifierLevel(state, item) {
  if (state.mode === 'mc') return 1;
  if (state.mode === 'type') return 2;
  // Auto: the server-stamped per-classifier level.
  const lvl = parseInt(item.level || 1, 10);
  return Math.max(1, Math.min(4, lvl));
}

// Shown in Auto mode only, to make promotions and demotions visible.
function updateLevelBadge({ state, el }) {
  if (state.mode === 'auto') {
    const tag =
      state.effectiveLevel === 1
        ? '· MC'
        : state.effectiveLevel === 2
          ? '· Type'
          : state.effectiveLevel === 3
            ? '· Reverse'
            : '· Cloze';
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
      '<span class="cd-option-key">' +
      (idx + 1) +
      '</span>' +
      '<span>' +
      escapeHtml(opt.hanzi) +
      '</span>' +
      (withPinyin && opt.pinyin
        ? '<span class="cd-option-pinyin">' + escapeHtml(opt.pinyin) + '</span>'
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
  el.promptWrap.style.display = 'block';
  el.promptBlank.textContent = '';
  el.noun.textContent = '';
  el.pronunciation.textContent = '';
  el.gloss.textContent = '';
  el.reversePrompt.style.display = 'block';
  el.reversePrompt.innerHTML =
    '<div style="font-size:0.95rem; color:var(--text-muted); margin-bottom:8px;">' +
    t('cloze_prompt', null, 'Fill in the measure word') +
    '</div>' +
    '<div style="font-size:1.6rem; font-weight:600; line-height:1.5; color:var(--text-primary);">' +
    escapeHtml(blanked).replace(
      /___/g,
      '<span style="color:var(--info); border-bottom:3px solid var(--info); padding:0 8px;">&nbsp;___&nbsp;</span>'
    ) +
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
  el.pronunciation.textContent = item.noun_pronunciation || '';
  el.gloss.textContent = item.noun_gloss || '';
}

function renderClassifierReverse(d) {
  const { state, el, t } = d;
  const item = state.currentItem;
  const canonical = (item.correct_classifier_hanzi || [])[0] || '';
  el.promptWrap.style.display = 'block';
  el.promptBlank.textContent = canonical;
  el.promptBlank.style.color = 'var(--info)';
  el.promptBlank.style.borderBottom = 'none';
  el.noun.textContent = '?';
  el.pronunciation.textContent = '';
  el.gloss.textContent = '';
  el.reversePrompt.style.display = 'block';
  el.reversePrompt.textContent = t('reverse_prompt', null, 'Which noun fits?') + ' ' + canonical;

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

// Standalone page: say how many classifiers moved up or down a level.
function showMasteryChanges({ el, t }, updates) {
  const promotions = updates.filter((u) => u && u.promoted);
  const demotions = updates.filter((u) => u && u.demoted);
  if (!promotions.length && !demotions.length) return;
  const banner = document.createElement('div');
  banner.style.cssText =
    'margin-top:14px; padding:10px 14px; background:var(--bg-page); border-radius:10px; font-size:0.9rem;';
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
    if (lvl === 4 && state.currentItem.cloze_blanked) {
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
      ? ' <span style="font-size:1.5rem; color: var(--text-muted);">(' +
        t('also', null, 'also') +
        ': ' +
        altList.join(' / ') +
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
