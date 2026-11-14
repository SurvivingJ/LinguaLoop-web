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
 * createTrainer(container, ctx, { tokenClass, errorHideIds })
 *   tokenClass    class of a passage token element ('char-token', 'word-token')
 *   errorHideIds  sections hidden when the player fails to load
 */
export function createTrainer(container, ctx, { tokenClass, errorHideIds }) {
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
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
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

  /** Pause on `html`; elements carrying `dismissAttr` close it. */
  function showErrorModal(html, dismissAttr, onDismiss) {
    state.isPaused = true;
    afterDismiss = onDismiss || null;
    const cont = q('errorModalContainer');
    cont.innerHTML = html;
    cont
      .querySelectorAll(`[${dismissAttr}]`)
      .forEach((el) => el.addEventListener('click', dismissErrorModal));
  }

  function dismissErrorModal() {
    q('errorModalContainer').innerHTML = '';
    state.isPaused = false;
    if (afterDismiss) afterDismiss();
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
      { passive: true }
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
    }, 1000);
  }

  // ---- finishing --------------------------------------------------------

  /**
   * End the attempt: stop the clock, submit the score and show the results.
   *   submitUrl   POST target
   *   buildBody   ({ correct, total, timeSec, errors, startedAt, finishedAt }) => body
   *   logName     prefix for a failed-submit console line
   *   results     { labelHtml(grade), accuracyLabel, unitsLabel, timeLabel,
   *                 mistakesLabel, eloLabel }
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
      }
    } catch (err) {
      console.error(`${logName} submit error:`, err);
    }
  }

  function showResults(accuracy, timeSec, text) {
    const grade = gradeFor(accuracy);
    const stat = (value, label, id) =>
      `<div class="stat-box"><div class="stat-value"${id ? ` id="${id}"` : ''}>${value}</div><div class="stat-label">${label}</div></div>`;
    const html = `
            <div class="results-overlay">
                <div class="results-card">
                    <h2 class="h3">${text.labelHtml(grade)}</h2>
                    <div class="results-accuracy ${grade}">${accuracy.toFixed(1)}%</div>
                    <p style="color: var(--text-secondary); margin-bottom: 20px;">${text.accuracyLabel}</p>
                    <div class="results-stats">
                        ${stat(`${state.correctCount}/${state.playableTokens.length}`, text.unitsLabel)}
                        ${stat(formatTime(timeSec), text.timeLabel)}
                        ${stat(state.errorCount, text.mistakesLabel)}
                        ${stat('--', text.eloLabel, 'eloChangeDisplay')}
                    </div>
                    <div class="d-flex gap-2 mt-3">
                        <button class="btn btn-primary flex-fill" type="button" data-session-next>
                            <span>${T('session.next_item', null, 'Next')}</span><i class="bi bi-arrow-right ms-1"></i>
                        </button>
                    </div>
                </div>
            </div>`;
    q('resultsContainer').innerHTML = html;
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

  return {
    state,
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
