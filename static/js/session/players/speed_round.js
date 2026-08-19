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

const T = (key, params, fallback) =>
  window.LinguaI18n && typeof LinguaI18n.t === 'function'
    ? LinguaI18n.t(key, params) || fallback || key
    : fallback || key;

function localEsc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : s;
  return d.innerHTML;
}

export function mount(container, ctx) {
  const languageId = ctx.languageId;
  const requested = (ctx.item && ctx.item.size) || null;

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
  const escHtml = ER && ER.escHtml ? ER.escHtml : localEsc;

  if (ER && ER.init) {
    ER.init({
      cardEl: q('exerciseCard'),
      isAnswered: () => state.isAnswered,
      setAnswered: (v) => {
        state.isAnswered = v;
      },
      showFeedback: (ok, expl) => showFeedback(ok, expl),
      submitAttempt: (ok, resp) => submitAttempt(ok, resp),
      nextExercise: () => nextExercise(),
    });
  }

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
      let url = `/api/practice/speed-round?language_id=${languageId}`;
      if (requested) url += `&size=${encodeURIComponent(requested)}`;
      const res = await window.authFetch(url);
      const body = await res.json();
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

    try {
      ER.dispatch(ex.exercise_type, ex, ex.content || {}, '');
    } catch (e) {
      console.error('Render error for', ex.exercise_type, e);
      q('exerciseCard').innerHTML =
        `<p style="color:var(--danger)">Error rendering exercise: ${escHtml(ex.exercise_type)}</p>`;
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
    const fb = container.querySelector('#exerciseFeedback');
    if (!fb) return;
    fb.className = 'exercise-feedback show ' + (ok ? 'correct' : 'incorrect');
    let html = ok
      ? '<i class="fas fa-bolt me-2"></i>' + T('session.correct', null, 'Correct!')
      : '<i class="fas fa-times-circle me-2"></i>' + T('session.incorrect', null, 'Incorrect');
    if (expl) html += `<div style="margin-top:8px">${escHtml(expl)}</div>`;
    fb.innerHTML = html;
    const btn = container.querySelector('#nextBtn');
    if (btn) btn.classList.add('show');
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
    if (saved === null && typeof window.showToast === 'function') {
      window.showToast(
        T('session.save_failed', null, 'Couldn’t save your progress — check your connection.')
      );
    }
  }

  function nextExercise() {
    state.currentIndex++;
    renderExercise();
  }

  // -----------------------------------------------------------------
  // Chrome
  // -----------------------------------------------------------------

  function updateProgress() {
    const total = state.items.length;
    q('progressText').textContent = `${state.currentIndex} / ${total}`;
    q('progressFill').style.width = total ? `${(state.currentIndex / total) * 100}%` : '0%';
    const acc = state.totalAnswered
      ? Math.round((state.correctCount / state.totalAnswered) * 100)
      : 0;
    q('scoreText').textContent = `${acc}%`;
  }

  function showComplete() {
    stopClock();
    q('progressArea').style.display = 'none';
    const timerWrap = q('speedTimer');
    if (timerWrap) timerWrap.style.display = 'none';

    const acc = state.totalAnswered
      ? Math.round((state.correctCount / state.totalAnswered) * 100)
      : 0;
    q('exerciseCard').innerHTML = `
            <div style="text-align:center;padding:24px">
                <div style="font-size:2.5rem">⚡</div>
                <h2 class="h4 mb-3">${T('session.speed_done', null, 'Speed round complete!')}</h2>
                <div class="d-flex gap-4 justify-content-center mb-3">
                    <div><div style="font-size:1.6rem;font-weight:700;color:var(--primary)">${state.correctCount}/${state.totalAnswered}</div><div class="text-muted small">${T('session.correct_label', null, 'Correct')}</div></div>
                    <div><div style="font-size:1.6rem;font-weight:700;color:var(--primary)">${acc}%</div><div class="text-muted small">${T('session.accuracy', null, 'Accuracy')}</div></div>
                    <div><div style="font-size:1.6rem;font-weight:700;color:var(--text-secondary)">${state.timedOutCount}</div><div class="text-muted small">${T('session.speed_timeouts', null, 'Ran out')}</div></div>
                </div>
                <button class="btn btn-primary" type="button" data-session-next><span>${T('session.next_item', null, 'Next')}</span><i class="fas fa-arrow-right ms-2"></i></button>
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
    const btn = document.createElement('button');
    btn.className = 'btn btn-primary mt-2 d-block mx-auto';
    btn.type = 'button';
    btn.setAttribute('data-session-next', '');
    btn.innerHTML = `<span>${T('session.next_item', null, 'Next')}</span><i class="fas fa-arrow-right ms-2"></i>`;
    q('exerciseCard').appendChild(btn);
    wireNext();
  }

  function wireNext() {
    const btn = container.querySelector('[data-session-next]');
    if (btn)
      btn.onclick = () =>
        ctx.onComplete({
          correct: state.correctCount,
          total: state.totalAnswered,
          timed_out: state.timedOutCount,
        });
  }

  function now() {
    return window.performance && performance.now ? performance.now() : Date.now();
  }
}

// ========================================================================
// MARKUP — the practice card styles plus the countdown bar.
// ========================================================================
const MARKUP = `
<style>
    .vd-session-head { max-width: 680px; margin: 16px auto 0; display: flex; align-items: center; justify-content: space-between; }
    .vd-progress { display: flex; align-items: center; gap: 12px; }
    .vd-progress-text { font-size: 14px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }
    .vd-progress-bar { width: 140px; height: 6px; background: var(--border-default); border-radius: 3px; overflow: hidden; }
    .vd-progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary), #6366f1); border-radius: 3px; transition: width .4s ease; }
    .vd-score { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
    .speed-timer { max-width: 680px; margin: 12px auto 0; display: flex; align-items: center; gap: 12px; }
    .speed-timer-bar { flex: 1; height: 8px; background: var(--border-default); border-radius: 4px; overflow: hidden; }
    .speed-timer-fill { height: 100%; width: 100%; background: linear-gradient(90deg, var(--primary), #6366f1); border-radius: 4px; transition: width .1s linear; }
    .speed-timer-fill.urgent { background: linear-gradient(90deg, var(--danger, #dc2626), #f97316); }
    .speed-timer-text { font-size: 14px; font-weight: 700; color: var(--text-secondary); min-width: 34px; text-align: right; font-variant-numeric: tabular-nums; }
    .exercise-card-area { max-width: 680px; margin: 16px auto; background: var(--bg-surface); border-radius: 16px; box-shadow: var(--shadow-md, 0 4px 12px rgba(0,0,0,0.08)); padding: 28px; min-height: 300px; }
    .exercise-type-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; }
    .exercise-instruction { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 16px; }
    .exercise-prompt { font-size: 18px; line-height: 1.6; color: var(--text-primary); margin-bottom: 20px; }
    .exercise-prompt .blank { background: var(--bg-muted); border-bottom: 2px solid var(--primary); padding: 2px 20px; border-radius: 4px; }
    .exercise-options { display: flex; flex-direction: column; gap: 10px; }
    .exercise-option { display: flex; align-items: center; gap: 12px; padding: 14px 18px; background: var(--bg-surface); border: 2px solid var(--border-default); border-radius: 12px; cursor: pointer; transition: all .2s; font-size: 15px; }
    .exercise-option:hover:not(.disabled) { border-color: var(--primary); background: rgba(30,64,175,0.04); }
    .exercise-option.correct { border-color: var(--success); background: rgba(5,150,105,0.08); }
    .exercise-option.incorrect { border-color: var(--danger); background: rgba(220,38,38,0.08); }
    .exercise-option.disabled { pointer-events: none; opacity: .85; }
    .option-letter { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: var(--bg-muted); font-weight: 700; font-size: 13px; color: var(--text-secondary); flex-shrink: 0; }
    .exercise-feedback { margin-top: 16px; padding: 14px 18px; border-radius: 12px; font-size: 14px; line-height: 1.6; display: none; }
    .exercise-feedback.show { display: block; }
    .exercise-feedback.correct { background: rgba(5,150,105,0.08); border: 1px solid rgba(5,150,105,0.2); color: var(--text-primary); }
    .exercise-feedback.incorrect { background: rgba(220,38,38,0.08); border: 1px solid rgba(220,38,38,0.2); color: var(--text-primary); }
    .exercise-next-btn { display: none; margin-top: 16px; }
    .exercise-next-btn.show { display: inline-flex; }
    .phonetic-display { text-align: center; margin-bottom: 24px; }
    .phonetic-display .ipa { font-size: 24px; color: var(--primary); font-weight: 600; }
    .phonetic-display .pron { font-size: 16px; color: var(--text-secondary); margin-top: 4px; }
</style>

<div class="vd-session-head">
    <span style="font-weight:700;font-size:16px;color:var(--text-primary)"><i class="fas fa-bolt me-2"></i><span data-i18n="session.speed_heading">Speed Round</span></span>
    <div class="vd-progress" id="progressArea" style="display:none">
        <span class="vd-progress-text" id="progressText">0 / 0</span>
        <div class="vd-progress-bar"><div class="vd-progress-fill" id="progressFill"></div></div>
        <span class="vd-score" id="scoreText"></span>
    </div>
</div>

<div class="speed-timer" id="speedTimer" role="timer" aria-live="off">
    <div class="speed-timer-bar"><div class="speed-timer-fill" id="speedTimerFill"></div></div>
    <span class="speed-timer-text" id="speedTimerText"></span>
</div>

<div class="exercise-card-area" id="exerciseCard"></div>
`;
