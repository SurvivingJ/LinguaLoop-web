// static/js/session/players/speed_round.js
// Timed fluency battery over already-mastered words (TASK-533).
//
// Same renderer stack as players/practice.js — the items ARE ordinary L1-L3
// recognition exercises — plus the one thing that makes this a speed round: a
// per-item clock that submits for you when it runs out.
//
// Two decisions worth knowing about:
//
//   * **A timeout is an answer, not an abandonment.** Failing to retrieve a
//     mastered word inside the clock is exactly the signal this format exists
//     to collect, so the timer posts `timed_out: true` with `is_correct:
//     false` rather than skipping the item.
//   * **The clock is not the practice timer.** Attempts carry
//     `is_speed_round: true`, which routes them to an FSRS-only update path.
//     A slow correct answer here must not push a mastered word back down the
//     ladder — see services/vocabulary_ladder/speed_round.py.

import { T, escapeHtml, nowMs as now, toastSaveFailed } from '../dom.js';
import { prefetchJson, takePrefetch } from '../prefetch.js';
import {
  EXERCISE_BASE_STYLES,
  sessionHeadHtml,
  accuracyPct,
  bindRenderers,
  renderProgress,
  renderFeedback,
  exerciseIdBadge,
  renderErrorHtml,
  nextButtonHtml,
  appendNextButton,
  statHtml,
  wireNext as wireNextButton,
} from './_exercise_shell.js';

function speedRoundUrl(item, languageId) {
  const requested = (item && item.size) || null;
  let url = `/api/practice/speed-round?language_id=${languageId}`;
  if (requested) url += `&size=${encodeURIComponent(requested)}`;
  return url;
}

// The battery is drawn from mastered words, which practice attempts can
// change, so it is not loaded while a practice or speed round is running.
const ATTEMPT_KINDS = { practice: true, speed_round: true };

/** Session prefetch hook. */
export function prefetch(item, ctx) {
  const current = ctx && ctx.current;
  if (current && ATTEMPT_KINDS[current.kind]) return null;
  return prefetchJson(speedRoundUrl(item, ctx && ctx.languageId));
}

export function mount(container, ctx) {
  const languageId = ctx.languageId;

  const state = {
    items: [],
    secondsPerItem: 8,
    currentIndex: 0,
    correctCount: 0,
    totalAnswered: 0,
    timedOutCount: 0,
    isAnswered: false,
    renderedAt: 0,
    // Handles for the running clock, cleared on every transition so a stale
    // timer can never submit against the *next* item.
    tickHandle: null,
    deadline: 0,
  };

  const q = (id) => container.querySelector('#' + id);
  container.innerHTML = MARKUP;

  const ER = window.ExRenderers;
  const escHtml = ER && ER.escHtml ? ER.escHtml : escapeHtml;

  bindRenderers(ER, q('exerciseCard'), state, { showFeedback, submitAttempt, nextExercise });

  load();

  return {
    destroy() {
      stopClock();
    },
  };

  // -----------------------------------------------------------------
  // Loading
  // -----------------------------------------------------------------

  async function load() {
    if (!ER || !ER.dispatch) {
      showMessage(T('session.speed_unavailable', null, 'Speed rounds aren’t available right now.'));
      return;
    }
    try {
      const pre = await takePrefetch(ctx.item);
      let res = pre;
      let body = pre && pre.data;
      if (!pre) {
        res = await window.authFetch(speedRoundUrl(ctx.item, languageId));
        body = await res.json();
      }
      const data = (body && (body.data || body)) || {};

      if (!res.ok) {
        showMessage(
          T('session.speed_error', null, 'Couldn’t load the speed round. You can move on.')
        );
        return;
      }

      const items = data.items || [];
      if (!items.length) {
        // An empty battery is the normal state for most learners, so it reads
        // as a nudge rather than as a failure.
        showMessage(emptyMessage(data.no_content_reason));
        return;
      }

      state.items = items;
      state.secondsPerItem = data.seconds_per_item || state.secondsPerItem;
      q('progressArea').style.display = 'flex';
      renderExercise();
    } catch (e) {
      console.error('Speed round load failed:', e);
      showMessage(
        T('session.speed_error', null, 'Couldn’t load the speed round. You can move on.')
      );
    }
  }

  function emptyMessage(reason) {
    if (reason === 'no_mastered_words') {
      return T(
        'session.speed_no_mastered',
        null,
        'Speed rounds unlock once you’ve mastered some words — keep practising.'
      );
    }
    if (reason === 'too_few_items_for_a_battery') {
      return T(
        'session.speed_too_few',
        null,
        'Not quite enough mastered words for a full round yet.'
      );
    }
    return T('session.speed_empty', null, 'No speed round available right now.');
  }

  // -----------------------------------------------------------------
  // Rendering + the clock
  // -----------------------------------------------------------------

  function renderExercise() {
    stopClock();
    state.isAnswered = false;
    updateProgress();

    if (state.currentIndex >= state.items.length) {
      showComplete();
      return;
    }

    const ex = state.items[state.currentIndex];
    state.renderedAt = now();

    // Surfaced on every render (including the error fallback below) so a
    // broken exercise can be reported by ID instead of by vague description.
    const idBadge = exerciseIdBadge(ex, escHtml);

    try {
      ER.dispatch(ex.exercise_type, ex, ex.content || {}, idBadge);
    } catch (e) {
      console.error('Render error for', ex.exercise_type, ex.exercise_id, e);
      q('exerciseCard').innerHTML = renderErrorHtml(idBadge, ex, escHtml);
      return;
    }

    startClock();
  }

  function startClock() {
    const ms = state.secondsPerItem * 1000;
    state.deadline = now() + ms;
    const bar = q('speedTimerFill');
    const label = q('speedTimerText');
    if (bar) bar.style.width = '100%';

    state.tickHandle = window.setInterval(() => {
      const remaining = Math.max(0, state.deadline - now());
      if (bar) {
        bar.style.width = `${(remaining / ms) * 100}%`;
        bar.classList.toggle('urgent', remaining <= 3000);
      }
      if (label) label.textContent = `${Math.ceil(remaining / 1000)}s`;

      if (remaining <= 0) {
        stopClock();
        handleTimeout();
      }
    }, 100);
  }

  function stopClock() {
    if (state.tickHandle) {
      window.clearInterval(state.tickHandle);
      state.tickHandle = null;
    }
  }

  function handleTimeout() {
    // Guard against a race with a click that landed in the same tick.
    if (state.isAnswered) return;
    state.isAnswered = true;
    state.timedOutCount++;
    submitAttempt(false, null, true);
    showFeedback(false, T('session.speed_timed_out', null, 'Out of time'));
  }

  // -----------------------------------------------------------------
  // Answering
  // -----------------------------------------------------------------

  function showFeedback(ok, expl) {
    stopClock();
    renderFeedback(container, ok, expl, { correctIcon: 'fa-bolt', escHtml });
  }

  async function submitAttempt(ok, response, timedOut) {
    const ex = state.items[state.currentIndex];
    if (!ex) return;
    stopClock();

    state.totalAnswered++;
    if (ok) state.correctCount++;

    const elapsedMs = state.renderedAt ? Math.max(0, Math.round(now() - state.renderedAt)) : 0;

    let saved = null;
    for (let attempt = 0; attempt < 2 && saved === null; attempt++) {
      try {
        const r = await window.authFetch('/api/practice/attempt', {
          method: 'POST',
          body: JSON.stringify({
            exercise_id: ex.exercise_id,
            is_correct: !!ok,
            user_response: response,
            time_taken_ms: elapsedMs,
            timed_out: !!timedOut,
            // Routes the attempt to the FSRS-only path.
            is_speed_round: true,
            language_id: languageId,
          }),
        });
        saved = r && r.ok ? await r.json() : null;
      } catch (e) {
        console.error('Speed-round attempt error:', e);
        saved = null;
      }
    }
    if (saved === null) toastSaveFailed();
  }

  function nextExercise() {
    state.currentIndex++;
    renderExercise();
  }

  // -----------------------------------------------------------------
  // Chrome
  // -----------------------------------------------------------------

  function updateProgress() {
    renderProgress(
      container,
      state.currentIndex,
      state.items.length,
      state.correctCount,
      state.totalAnswered
    );
  }

  function showComplete() {
    stopClock();
    q('progressArea').style.display = 'none';
    const timerWrap = q('speedTimer');
    if (timerWrap) timerWrap.style.display = 'none';

    const acc = accuracyPct(state.correctCount, state.totalAnswered);
    q('exerciseCard').innerHTML = `
            <div style="text-align:center;padding:24px">
                <div style="font-size:2.5rem">⚡</div>
                <h2 class="h4 mb-3">${T('session.speed_done', null, 'Speed round complete!')}</h2>
                <div class="d-flex gap-4 justify-content-center mb-3">
                    ${statHtml(`${state.correctCount}/${state.totalAnswered}`, T('session.correct_label', null, 'Correct'))}
                    ${statHtml(`${acc}%`, T('session.accuracy', null, 'Accuracy'))}
                    ${statHtml(state.timedOutCount, T('session.speed_timeouts', null, 'Ran out'), 'var(--text-secondary)')}
                </div>
                ${nextButtonHtml()}
            </div>`;
    wireNext();
  }

  function showMessage(text) {
    stopClock();
    q('progressArea').style.display = 'none';
    const timerWrap = q('speedTimer');
    if (timerWrap) timerWrap.style.display = 'none';
    q('exerciseCard').innerHTML =
      `<p style="text-align:center;color:var(--text-secondary);padding:32px">${escHtml(text)}</p>`;
    appendNextButton(q('exerciseCard'), 'btn btn-primary mt-2 d-block mx-auto');
    wireNext();
  }

  function wireNext() {
    wireNextButton(container, ctx, () => ({
      correct: state.correctCount,
      total: state.totalAnswered,
      timed_out: state.timedOutCount,
    }));
  }
}

// ========================================================================
// MARKUP — the practice card styles plus the countdown bar.
// ========================================================================
const MARKUP = `
<style>${EXERCISE_BASE_STYLES}
    .speed-timer { max-width: 680px; margin: 12px auto 0; display: flex; align-items: center; gap: 12px; }
    .speed-timer-bar { flex: 1; height: 8px; background: var(--border-default); border-radius: 4px; overflow: hidden; }
    .speed-timer-fill { height: 100%; width: 100%; background: linear-gradient(90deg, var(--primary), #6366f1); border-radius: 4px; transition: width .1s linear; }
    .speed-timer-fill.urgent { background: linear-gradient(90deg, var(--danger, #dc2626), #f97316); }
    .speed-timer-text { font-size: 14px; font-weight: 700; color: var(--text-secondary); min-width: 34px; text-align: right; font-variant-numeric: tabular-nums; }
</style>
${sessionHeadHtml('fa-bolt', 'session.speed_heading', 'Speed Round')}

<div class="speed-timer" id="speedTimer" role="timer" aria-live="off">
    <div class="speed-timer-bar"><div class="speed-timer-fill" id="speedTimerFill"></div></div>
    <span class="speed-timer-text" id="speedTimerText"></span>
</div>

<div class="exercise-card-area" id="exerciseCard"></div>
`;
