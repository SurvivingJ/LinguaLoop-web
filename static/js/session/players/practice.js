// static/js/session/players/practice.js
// Practice (vocab/exercises) player for the daily-session runner. Reuses the
// shared global ExRenderers module (static/js/exercise-renderers.js, loaded by
// study_session.html) exactly as templates/vocab_dojo.html does, but sources
// items from the Study-Plan practice surface (/api/practice/session) and
// records attempts via /api/practice/attempt with session_mode so the weekly
// counters advance. Gate / stress-test marker items are skipped in this v1
// (they require the separate /api/vocab-dojo battery endpoints).

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
  const mode = (ctx.item && ctx.item.mode) || 'acquisition';
  const minutes = (ctx.item && ctx.item.minutes) || 10;
  const languageId = ctx.languageId;

  const state = {
    exercises: [],
    retryQueue: [],
    currentIndex: 0,
    correctCount: 0,
    totalAnswered: 0,
    isAnswered: false,
  };

  const q = (id) => container.querySelector('#' + id);
  container.innerHTML = MARKUP;

  const ER = window.ExRenderers;
  const escHtml = ER && ER.escHtml ? ER.escHtml : localEsc;
  const shuffleArr = ER && ER.shuffleArr ? ER.shuffleArr : (a) => a.slice();

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
      /* container is cleared by the controller */
    },
  };

  async function load() {
    if (!ER || !ER.dispatch) {
      // Shared renderer not present — degrade gracefully so the session
      // can still advance.
      q('exerciseCard').innerHTML =
        `<p style="text-align:center;color:var(--text-secondary);padding:32px">${T('session.practice_unavailable', null, 'Practice isn’t available right now.')}</p>`;
      renderNextOnly();
      return;
    }
    try {
      const res = await window.authFetch(
        `/api/practice/session?mode=${encodeURIComponent(mode)}&minutes=${minutes}&language_id=${languageId}`
      );
      const data = await res.json();
      const items = (data.items || data.exercises || []).filter(
        (it) => !it.is_gate_marker && !it.is_stress_test_marker
      );

      if (!res.ok || items.length === 0) {
        q('exerciseCard').innerHTML =
          `<p style="text-align:center;color:var(--text-secondary);padding:32px">${T('session.practice_empty', null, 'No practice items right now — you can move on.')}</p>`;
        renderNextOnly();
        return;
      }
      state.exercises = items;
      q('progressArea').style.display = 'flex';
      renderExercise();
    } catch (e) {
      console.error('Practice load failed:', e);
      q('exerciseCard').innerHTML =
        `<p style="text-align:center;color:var(--danger);padding:32px">${T('session.practice_error', null, 'Couldn’t load practice. You can move on.')}</p>`;
      renderNextOnly();
    }
  }

  function renderExercise() {
    state.isAnswered = false;
    updateProgress();

    if (state.currentIndex >= state.exercises.length) {
      if (state.retryQueue.length > 0) {
        state.exercises.push(...shuffleArr(state.retryQueue));
        state.retryQueue = [];
        renderExercise();
        return;
      }
      showComplete();
      return;
    }

    const ex = state.exercises[state.currentIndex];
    const c = ex.content || {};

    let ribbon = '';
    if (ex.lemma) {
      ribbon = `<div class="word-ribbon"><strong>${escHtml(ex.lemma)}</strong>`;
      if (ex.pronunciation) ribbon += `<span class="sep">|</span> ${escHtml(ex.pronunciation)}`;
      if (ex.definition)
        ribbon += `<span class="sep">|</span> <span style="color:var(--text-secondary)">${escHtml(ex.definition)}</span>`;
      ribbon += '</div>';
    }
    let ladderBadge = '';
    if (ex.ladder_level) {
      ladderBadge = `<div class="ladder-badge"><span class="ladder-level">L${ex.ladder_level}</span> ${escHtml(ex.ladder_name || '')}</div>`;
    }
    const w = ribbon + ladderBadge;

    try {
      ER.dispatch(ex.exercise_type, ex, c, w);
    } catch (e) {
      console.error('Render error for', ex.exercise_type, e);
      q('exerciseCard').innerHTML =
        w +
        `<p style="color:var(--danger)">Error rendering exercise: ${escHtml(ex.exercise_type)}</p>`;
    }
  }

  function showFeedback(ok, expl) {
    const fb = container.querySelector('#exerciseFeedback');
    if (!fb) return;
    fb.className = 'exercise-feedback show ' + (ok ? 'correct' : 'incorrect');
    let html = ok
      ? '<i class="fas fa-check-circle me-2"></i>' + T('session.correct', null, 'Correct!')
      : '<i class="fas fa-times-circle me-2"></i>' + T('session.incorrect', null, 'Incorrect');
    if (expl) html += `<div style="margin-top:8px">${escHtml(expl)}</div>`;
    fb.innerHTML = html;
    const btn = container.querySelector('#nextBtn');
    if (btn) btn.classList.add('show');
  }

  function submitAttempt(ok, response) {
    const ex = state.exercises[state.currentIndex];
    if (!ex) return;
    state.totalAnswered++;
    if (ok) state.correctCount++;

    window
      .authFetch('/api/practice/attempt', {
        method: 'POST',
        body: JSON.stringify({
          exercise_id: ex.exercise_id,
          is_correct: ok,
          user_response: response,
          time_taken_ms: 0,
          session_mode: mode,
          language_id: languageId,
        }),
      })
      .then((r) => r.json())
      .then((data) => {
        if (data && data.requeue && !ok) state.retryQueue.push({ ...ex, _retry: true });
      })
      .catch((e) => console.error('Practice attempt error:', e));
  }

  function nextExercise() {
    state.currentIndex++;
    renderExercise();
  }

  function updateProgress() {
    const total = state.exercises.length;
    const done = state.currentIndex;
    q('progressText').textContent = `${done} / ${total}`;
    q('progressFill').style.width = total ? `${(done / total) * 100}%` : '0%';
    const acc = state.totalAnswered
      ? Math.round((state.correctCount / state.totalAnswered) * 100)
      : 0;
    q('scoreText').textContent = `${acc}%`;
  }

  function showComplete() {
    q('progressArea').style.display = 'none';
    const acc = state.totalAnswered
      ? Math.round((state.correctCount / state.totalAnswered) * 100)
      : 0;
    q('exerciseCard').innerHTML = `
            <div style="text-align:center;padding:24px">
                <div style="font-size:2.5rem">✅</div>
                <h2 class="h4 mb-3">${T('session.practice_done', null, 'Practice complete!')}</h2>
                <div class="d-flex gap-4 justify-content-center mb-3">
                    <div><div style="font-size:1.6rem;font-weight:700;color:var(--primary)">${state.correctCount}/${state.totalAnswered}</div><div class="text-muted small">${T('session.correct_label', null, 'Correct')}</div></div>
                    <div><div style="font-size:1.6rem;font-weight:700;color:var(--primary)">${acc}%</div><div class="text-muted small">${T('session.accuracy', null, 'Accuracy')}</div></div>
                </div>
                <button class="btn btn-primary" type="button" data-session-next><span>${T('session.next_item', null, 'Next')}</span><i class="fas fa-arrow-right ms-2"></i></button>
            </div>`;
    wireNext();
  }

  // Used when there are no items / renderer missing: just a Next button.
  function renderNextOnly() {
    q('progressArea').style.display = 'none';
    const card = q('exerciseCard');
    const btn = document.createElement('button');
    btn.className = 'btn btn-primary mt-2';
    btn.type = 'button';
    btn.setAttribute('data-session-next', '');
    btn.innerHTML = `<span>${T('session.next_item', null, 'Next')}</span><i class="fas fa-arrow-right ms-2"></i>`;
    card.appendChild(btn);
    wireNext();
  }

  function wireNext() {
    const btn = container.querySelector('[data-session-next]');
    if (btn)
      btn.onclick = () =>
        ctx.onComplete({ correct: state.correctCount, total: state.totalAnswered });
  }
}

// ========================================================================
// MARKUP — inlines the vocab-dojo exercise styles so ExRenderers output looks
// right inside /session.
// ========================================================================
const MARKUP = `
<style>
    .vd-session-head { max-width: 680px; margin: 16px auto 0; display: flex; align-items: center; justify-content: space-between; }
    .vd-progress { display: flex; align-items: center; gap: 12px; }
    .vd-progress-text { font-size: 14px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }
    .vd-progress-bar { width: 140px; height: 6px; background: var(--border-default); border-radius: 3px; overflow: hidden; }
    .vd-progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary), #6366f1); border-radius: 3px; transition: width .4s ease; }
    .vd-score { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
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
    .word-ribbon { display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: var(--bg-muted); border-radius: 10px; margin-bottom: 16px; font-size: 14px; }
    .word-ribbon strong { font-size: 16px; color: var(--primary); }
    .word-ribbon .sep { color: var(--border-default); }
    .ladder-badge { display: inline-flex; align-items: center; gap: 6px; background: var(--bg-muted); border: 1px solid var(--border-default); border-radius: 8px; padding: 4px 12px; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; }
    .ladder-level { color: var(--primary); font-weight: 700; }
    .js-bank, .js-answer { min-height: 52px; padding: 12px; border-radius: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
    .js-bank { background: var(--bg-muted); border: 2px dashed var(--border-default); }
    .js-answer { background: rgba(30,64,175,0.04); border: 2px solid var(--primary); margin-bottom: 12px; }
    .js-chunk { padding: 8px 16px; background: var(--bg-surface); border: 2px solid var(--border-default); border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: 500; user-select: none; transition: all .15s; }
    .js-chunk:hover { border-color: var(--primary); }
    .js-chunk.placed { opacity: .4; pointer-events: none; }
    .phonetic-display { text-align: center; margin-bottom: 24px; }
    .phonetic-display .ipa { font-size: 24px; color: var(--primary); font-weight: 600; }
    .phonetic-display .pron { font-size: 16px; color: var(--text-secondary); margin-top: 4px; }
    .sentence-card { padding: 14px 18px; background: var(--bg-surface); border: 2px solid var(--border-default); border-radius: 12px; cursor: pointer; transition: all .2s; font-size: 15px; line-height: 1.6; }
    .sentence-card:hover:not(.disabled) { border-color: var(--primary); }
    .sentence-card.correct { border-color: var(--success); background: rgba(5,150,105,0.08); }
    .sentence-card.incorrect { border-color: var(--danger); background: rgba(220,38,38,0.08); }
</style>

<div class="vd-session-head">
    <span style="font-weight:700;font-size:16px;color:var(--text-primary)"><i class="fas fa-dumbbell me-2"></i><span data-i18n="session.practice_heading">Practice</span></span>
    <div class="vd-progress" id="progressArea" style="display:none">
        <span class="vd-progress-text" id="progressText">0 / 0</span>
        <div class="vd-progress-bar"><div class="vd-progress-fill" id="progressFill"></div></div>
        <span class="vd-score" id="scoreText"></span>
    </div>
</div>

<div class="exercise-card-area" id="exerciseCard"></div>
`;
