// static/js/session/players/_syllable_trainer.js
// What the pinyin tone trainer and the pitch-accent trainer share: both walk a
// passage one token at a time, pause on a wrong answer behind an explanation
// modal, time the attempt, submit a score and show a results card whose ELO
// figure is filled in when the submit returns. Each player supplies its own
// markup, token rendering, inputs and wording.

import {
  T,
  formatTime,
  formatClock,
  showLoading as setLoading,
  showError as setError,
  applyI18n,
} from '../dom.js';
import { prefetchJson, takePrefetch } from '../prefetch.js';

const testUrl = (slug) => `/api/tests/test/${slug}`;

/** Session prefetch hook for both trainers: the test payload is static. */
export function prefetchTest(item) {
  if (!item || !item.slug) return null;
  return prefetchJson(testUrl(item.slug));
}

/** 'excellent' | 'good' | 'fair' | 'poor' for an accuracy percentage. */
export function gradeFor(accuracy) {
  if (accuracy >= 95) return 'excellent';
  if (accuracy >= 80) return 'good';
  if (accuracy >= 60) return 'fair';
  return 'poor';
}

/**
 * Mount a trainer as its own page (/test/<slug>/pinyin, .../pitch-accent)
 * instead of inside the daily session. `ctx.standalone` switches the player to
 * its page behaviour: the page's own stylesheet, a way back to the test list,
 * Retry / All tests on the results card, and the daily-load slot is marked
 * when the page was opened from that queue (?daily=true).
 */
export function mountTestPage(mount, { root, testType }) {
  const parts = window.location.pathname.split('/');
  const slug = parts[parts.indexOf('test') + 1];
  const daily = new URLSearchParams(window.location.search).get('daily') === 'true';
  return mount(root, {
    item: { slug },
    languageId: null,
    onComplete() {},
    frame: shellFrame(),
    standalone: {
      daily,
      // Runs inside the player's own load step, so a failure here shows the
      // player's error state.
      async prepare() {
        if (window.LinguaTestIntro) window.LinguaTestIntro.init({ testType });
        if (window.LinguaMetadata) await window.LinguaMetadata.load();
        if (window.LinguaI18n && window.LinguaI18n.init) await window.LinguaI18n.init();
        applyI18n(root);
      },
    },
  });
}

/**
 * The page's task header (templates/base.html, task mode) as a session-style
 * ctx.frame, so a player talks to one interface on either host. Null when the
 * shell is absent (unit tests, older pages).
 */
export function shellFrame() {
  const shell = window.LinguaShell;
  if (!shell || typeof shell.setTaskHeader !== 'function') return null;
  return {
    setHeader: (opts) => shell.setTaskHeader(opts || {}),
    onBack: (fn) => (typeof shell.onBack === 'function' ? shell.onBack(fn) : null),
  };
}

/**
 * Translate `[data-trk]` elements under `root`: text from the key, or the
 * element's own (English) text while the key is missing from the locale
 * files. Used for strings added by the 2026-11 redesign
 * (static/i18n/_redesign/trainers.json), which a plain data-i18n would show as
 * the raw key until they are merged.
 */
export function applyLocalKeys(root) {
  root.querySelectorAll('[data-trk]').forEach((el) => {
    if (!el.dataset.trkFallback) el.dataset.trkFallback = el.textContent;
    el.textContent = T(el.dataset.trk, null, el.dataset.trkFallback);
  });
}

/**
 * createTrainer(container, ctx, { tokenClass, errorHideIds })
 *   tokenClass    class of a passage token element ('char-token', 'word-token')
 *   errorHideIds  sections hidden when the player fails to load
 *   ctx.standalone  { daily, prepare() } when mounted by mountTestPage
 */
export function createTrainer(container, ctx, { tokenClass, errorHideIds }) {
  const standalone = ctx.standalone || null;
  const frame = ctx.frame || null;
  const state = {
    slug: ctx.item.slug,
    testData: null,
    allTokens: [],
    playableTokens: [],
    playableIndices: [],
    currentIndex: 0,
    correctCount: 0,
    errorCount: 0,
    errors: [],
    startTime: null,
    timerInterval: null,
    isComplete: false,
    isPaused: false,
  };

  const cleanup = [];
  const on = (el, ev, fn, opts) => {
    el.addEventListener(ev, fn, opts);
    cleanup.push(() => el.removeEventListener(ev, fn, opts));
  };
  const q = (id) => container.querySelector('#' + id);
  const qs = (sel) => container.querySelector(sel);
  const qsa = (sel) => container.querySelectorAll(sel);

  /** The task header (session runner or page shell): text only. */
  function setHeader(opts) {
    if (frame && typeof frame.setHeader === 'function') frame.setHeader(opts);
  }

  // Back while the mistake sheet is open closes the sheet (the attempt goes
  // on) instead of leaving the trainer.
  if (frame && typeof frame.onBack === 'function') {
    const off = frame.onBack(() => {
      if (!state.isPaused || state.isComplete) return false;
      dismissErrorModal();
      return true;
    });
    if (typeof off === 'function') cleanup.push(off);
  }

  function destroy() {
    if (state.timerInterval) {
      clearInterval(state.timerInterval);
      state.timerInterval = null;
    }
    cleanup.forEach((fn) => {
      try {
        fn();
      } catch (_) {}
    });
  }

  /** The test payload: prefetched by the session, or requested now. */
  async function fetchTest(loadFailedMessage) {
    const pre = await takePrefetch(ctx.item);
    if (pre) return pre.data;
    const resp = await window.authFetch(testUrl(state.slug));
    if (!resp.ok) throw new Error(loadFailedMessage(resp));
    return resp.json();
  }

  /** Keep the tokens and index the ones the learner answers. */
  function setTokens(tokens, isPlayable) {
    state.allTokens = tokens;
    state.allTokens.forEach((tok, i) => {
      if (isPlayable(tok)) {
        state.playableIndices.push(i);
        state.playableTokens.push(tok);
      }
    });
  }

  const tokenEl = (playableIdx) =>
    qs(`.${tokenClass}[data-index="${state.playableIndices[playableIdx]}"]`);

  /** Move the "current" marker to the token at state.currentIndex. */
  function markCurrent() {
    const prev = qs(`.${tokenClass}.current`);
    if (prev) prev.classList.remove('current');
    const el = tokenEl(state.currentIndex);
    if (el) {
      el.classList.remove('upcoming');
      el.classList.add('current');
      const reduce =
        window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' });
    }
  }

  function flashCorrect(el) {
    el.classList.add('correct-flash');
    setTimeout(() => el.classList.remove('correct-flash'), 200);
  }

  function flashError(playableIdx) {
    const el = tokenEl(playableIdx);
    if (el) {
      el.classList.add('error-flash');
      setTimeout(() => el.classList.remove('error-flash'), 300);
    }
  }

  function updateProgress() {
    const total = state.playableTokens.length;
    const pct = total > 0 ? (state.currentIndex / total) * 100 : 0;
    q('progressFill').style.width = pct + '%';
  }

  // ---- error modal ------------------------------------------------------
  let afterDismiss = null;
  let returnFocus = null;

  /** Pause on `html`; elements carrying `dismissAttr` close it. */
  function showErrorModal(html, dismissAttr, onDismiss) {
    state.isPaused = true;
    afterDismiss = onDismiss || null;
    const cont = q('errorModalContainer');
    cont.innerHTML = html;
    cont
      .querySelectorAll(`[${dismissAttr}]`)
      .forEach((el) => el.addEventListener('click', dismissErrorModal));
    // The sheet is a modal dialog: focus its Continue button (so a screen
    // reader announces it and a focused dock button cannot be re-pressed),
    // and hand focus back to where it was when the sheet closes.
    // Only a keyboard user's focus (:focus-visible) is handed back: a dock
    // button that kept focus after a tap would otherwise take the next Space.
    const active = document.activeElement;
    returnFocus =
      active && active !== document.body && container.contains(active) && focusVisible(active)
        ? active
        : null;
    const cta = cont.querySelector(`button[${dismissAttr}]`);
    if (cta) cta.focus({ preventScroll: true });
  }

  function focusVisible(el) {
    try {
      return el.matches(':focus-visible');
    } catch {
      return false;
    }
  }

  function dismissErrorModal() {
    q('errorModalContainer').innerHTML = '';
    state.isPaused = false;
    const back = returnFocus;
    returnFocus = null;
    if (afterDismiss) afterDismiss();
    if (back && back.isConnected && !state.isComplete && container.contains(back)) {
      back.focus({ preventScroll: true });
    }
  }

  // ---- swipe input ------------------------------------------------------

  /**
   * Swipes on `touchArea` call onSwipe('left'|'right'|'up'|'down'); a short
   * tap in place calls onTap when given.
   */
  function bindSwipe(touchArea, onSwipe, onTap) {
    let startX, startY, startTime;
    on(
      touchArea,
      'touchstart',
      (e) => {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        startTime = Date.now();
      },
      { passive: true }
    );
    on(
      touchArea,
      'touchend',
      (e) => {
        if (startX === undefined) return;
        // No compatibility click after the touch: a tap that opens the
        // mistake sheet would otherwise land on the sheet's backdrop at once
        // and close it again.
        if (e.cancelable) e.preventDefault();
        const dx = e.changedTouches[0].clientX - startX;
        const dy = e.changedTouches[0].clientY - startY;
        const absDx = Math.abs(dx);
        const absDy = Math.abs(dy);
        const elapsed = Date.now() - startTime;
        const threshold = 30;
        startX = startY = undefined;
        if (absDx < threshold && absDy < threshold && elapsed < 300) {
          if (onTap) onTap();
        } else if (absDx > absDy) onSwipe(dx > 0 ? 'right' : 'left');
        else onSwipe(dy < 0 ? 'up' : 'down');
      },
      { passive: false }
    );
    on(
      touchArea,
      'touchmove',
      (e) => {
        e.preventDefault();
      },
      { passive: false }
    );
  }

  // ---- timer ------------------------------------------------------------

  function startTimer() {
    state.startTime = Date.now();
    const el = q('elapsedTime');
    state.timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
      if (el) el.textContent = formatClock(elapsed);
      // The clock also sits in the header's right-hand slot.
      setHeader({ end: formatClock(elapsed) });
    }, 1000);
  }

  // ---- finishing --------------------------------------------------------

  /**
   * End the attempt: stop the clock, submit the score and show the results.
   *   submitUrl   POST target
   *   buildBody   ({ correct, total, timeSec, errors, startedAt, finishedAt }) => body
   *   logName     prefix for a failed-submit console line
   *   results     { labelHtml(grade), accuracyLabel, unitsLabel, timeLabel,
   *                 mistakesLabel, eloLabel, retryLabel, allTestsLabel }
   *                 (the last two label the standalone page's links)
   */
  function complete({ submitUrl, buildBody, logName, results }) {
    state.isComplete = true;
    clearInterval(state.timerInterval);
    const total = state.playableTokens.length;
    const correct = Math.max(0, total - state.errorCount);
    const accuracy = total > 0 ? (correct / total) * 100 : 0;
    const timeSec = Math.floor((Date.now() - state.startTime) / 1000);
    submitResults(submitUrl, buildBody, logName, { correct, total, timeSec });
    showResults(accuracy, timeSec, results);
  }

  async function submitResults(submitUrl, buildBody, logName, score) {
    try {
      const startedAt = state.startTime ? new Date(state.startTime).toISOString() : null;
      const finishedAt = new Date().toISOString();
      const resp = await window.authFetch(submitUrl, {
        method: 'POST',
        body: JSON.stringify(
          buildBody({ ...score, errors: state.errors.slice(0, 50), startedAt, finishedAt })
        ),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.result) updateResultsWithElo(data.result);
        if (standalone && standalone.daily) {
          markDailyLoadComplete(state.testData ? state.testData.id : null);
        }
      }
    } catch (err) {
      console.error(`${logName} submit error:`, err);
    }
  }

  // The "Today's Test Load" queue on the Tests page only learns an attempt is
  // finished when it is told.
  function markDailyLoadComplete(testId) {
    const languageId = localStorage.getItem('selectedLanguageId');
    if (!languageId || !testId) return;
    window
      .authFetch('/api/tests/daily-load/complete', {
        method: 'POST',
        body: JSON.stringify({ test_id: testId, language_id: parseInt(languageId) }),
      })
      .catch((err) => console.error('Error marking daily load complete:', err));
  }

  function showResults(accuracy, timeSec, text) {
    const grade = gradeFor(accuracy);
    const stat = (value, label, id) =>
      `<div class="stat-box"><div class="stat-value"${id ? ` id="${id}"` : ''}>${value}</div><div class="stat-label">${label}</div></div>`;
    const actions = standalone
      ? `
                        <a href="/test/${state.slug}/preview" class="ld-btn ld-btn--ghost">
                            <i class="bi bi-arrow-repeat" aria-hidden="true"></i>${text.retryLabel}
                        </a>
                        <a href="/tests" class="ld-btn">
                            <i class="bi bi-list-ul" aria-hidden="true"></i>${text.allTestsLabel}
                        </a>
                    `
      : `
                        <button class="ld-btn" type="button" data-session-next>
                            <span>${T('session.next_item', null, 'Next')}</span><i class="bi bi-arrow-right" aria-hidden="true"></i>
                        </button>
                    `;
    // A screen of its own over the trainer: score and stats in a scrolling
    // stage, the way on pinned in the dock.
    const html = `
            <div class="results-overlay">
                <div class="results-card ld-screen">
                    <div class="ld-stage results-body">
                        <div class="results-score">
                            <div class="results-accuracy ${grade}">${accuracy.toFixed(1)}%</div>
                            <div>
                                <h2 class="results-grade">${text.labelHtml(grade)}</h2>
                                <p class="results-label">${text.accuracyLabel}</p>
                            </div>
                        </div>
                        <div class="results-stats">
                            ${stat(`${state.correctCount}/${state.playableTokens.length}`, text.unitsLabel)}
                            ${stat(formatTime(timeSec), text.timeLabel)}
                            ${stat(state.errorCount, text.mistakesLabel)}
                            ${stat('--', text.eloLabel, 'eloChangeDisplay')}
                        </div>
                    </div>
                    <div class="ld-dock"><div class="ld-row">${actions}</div></div>
                </div>
            </div>`;
    q('resultsContainer').innerHTML = html;
    setHeader({ end: '' });
    const nextBtn = q('resultsContainer').querySelector('[data-session-next]');
    if (nextBtn) nextBtn.onclick = () => ctx.onComplete({ accuracy });
  }

  function updateResultsWithElo(result) {
    const eloEl = q('eloChangeDisplay');
    if (eloEl && result.user_elo_change) {
      const change = result.user_elo_change.change || 0;
      const sign = change >= 0 ? '+' : '';
      eloEl.textContent = sign + change;
      eloEl.className = 'stat-value ' + (change >= 0 ? 'text-success' : 'text-danger');
    }
  }

  /**
   * The session lays a player's markup out without the whitespace between
   * tags (inline elements sit flush); the standalone page keeps it.
   */
  const compact = (markup) => markup.replace(/>\s+</g, '><');

  /** Standalone page: add the way back to the test list to the error state. */
  function addBackLink() {
    const alert = qs('#errorState .alert');
    if (!standalone || !alert) return;
    const link = document.createElement('a');
    link.href = '/tests';
    link.className = 'btn btn-danger';
    link.innerHTML =
      '<i class="fas fa-arrow-left me-2" aria-hidden="true"></i><span data-i18n="test.back_to_tests">Back to Tests</span>';
    alert.appendChild(link);
  }

  /** Standalone page: what the page needs before the test loads. */
  async function prepare() {
    if (standalone && standalone.prepare) await standalone.prepare();
  }

  return {
    state,
    standalone,
    frame,
    setHeader,
    addBackLink,
    prepare,
    compact,
    on,
    q,
    qs,
    qsa,
    destroy,
    fetchTest,
    setTokens,
    tokenEl,
    markCurrent,
    flashCorrect,
    flashError,
    updateProgress,
    showErrorModal,
    dismissErrorModal,
    bindSwipe,
    startTimer,
    complete,
    showLoading: (show) => setLoading(container, show),
    showError: (msg) => setError(container, msg, errorHideIds),
  };
}
