// static/js/session/players/_exercise_shell.js
// Chrome shared by the players that run ExRenderers exercises (practice.js and
// speed_round.js): card styles, the progress header, answer feedback and the
// "Next" button that hands control back to the session.

import { T } from '../dom.js';

// Card styles for ExRenderers output inside /session (from vocab-dojo).
export const EXERCISE_BASE_STYLES = `
    .vd-session-head { max-width: 680px; margin: 16px auto 0; display: flex; align-items: center; justify-content: space-between; }
    .vd-progress { display: flex; align-items: center; gap: 12px; }
    .vd-progress-text { font-size: 14px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; }
    .vd-progress-bar { width: 140px; height: 6px; background: var(--border-default); border-radius: 3px; overflow: hidden; }
    .vd-progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary), #6366f1); border-radius: 3px; transition: width .4s ease; }
    .vd-score { font-size: 14px; font-weight: 600; color: var(--text-secondary); }
    .exercise-card-area { max-width: 680px; margin: 16px auto; background: var(--bg-surface); border-radius: 16px; box-shadow: var(--shadow-md, 0 4px 12px rgba(0,0,0,0.08)); padding: 28px; min-height: 300px; }
    .exercise-id-badge { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; color: var(--text-secondary); opacity: .55; margin-bottom: 6px; user-select: all; cursor: text; }
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
    .phonetic-display .pron { font-size: 16px; color: var(--text-secondary); margin-top: 4px; }`;

/** The player's title row with the (initially hidden) progress block. */
export function sessionHeadHtml(icon, headingKey, heading) {
  return `
<div class="vd-session-head">
    <span style="font-weight:700;font-size:16px;color:var(--text-primary)"><i class="fas ${icon} me-2"></i><span data-i18n="${headingKey}">${heading}</span></span>
    <div class="vd-progress" id="progressArea" style="display:none">
        <span class="vd-progress-text" id="progressText">0 / 0</span>
        <div class="vd-progress-bar"><div class="vd-progress-fill" id="progressFill"></div></div>
        <span class="vd-score" id="scoreText"></span>
    </div>
</div>`;
}

/** Whole-percent accuracy; 0 before anything is answered. */
export function accuracyPct(correct, answered) {
  return answered ? Math.round((correct / answered) * 100) : 0;
}

/** Point ExRenderers at this player's card and callbacks. */
export function bindRenderers(ER, cardEl, state, handlers) {
  if (!ER || !ER.init) return;
  ER.init({
    cardEl,
    isAnswered: () => state.isAnswered,
    setAnswered: (v) => {
      state.isAnswered = v;
    },
    showFeedback: (ok, expl) => handlers.showFeedback(ok, expl),
    submitAttempt: (ok, resp) => handlers.submitAttempt(ok, resp),
    nextExercise: () => handlers.nextExercise(),
  });
}

/** "3 / 12", the bar and the running accuracy. */
export function renderProgress(container, done, total, correct, answered) {
  const q = (id) => container.querySelector('#' + id);
  q('progressText').textContent = `${done} / ${total}`;
  q('progressFill').style.width = total ? `${(done / total) * 100}%` : '0%';
  q('scoreText').textContent = `${accuracyPct(correct, answered)}%`;
}

/** Fill the renderer's #exerciseFeedback and reveal its Next button. */
export function renderFeedback(container, ok, expl, { correctIcon, escHtml }) {
  const fb = container.querySelector('#exerciseFeedback');
  if (!fb) return;
  fb.className = 'exercise-feedback show ' + (ok ? 'correct' : 'incorrect');
  let html = ok
    ? `<i class="fas ${correctIcon} me-2"></i>` + T('session.correct', null, 'Correct!')
    : '<i class="fas fa-times-circle me-2"></i>' + T('session.incorrect', null, 'Incorrect');
  if (expl) html += `<div style="margin-top:8px">${escHtml(expl)}</div>`;
  fb.innerHTML = html;
  const btn = container.querySelector('#nextBtn');
  if (btn) btn.classList.add('show');
}

/** The small monospace exercise id shown above every item. */
export function exerciseIdBadge(ex, escHtml) {
  return ex.exercise_id ? `<div class="exercise-id-badge">${escHtml(ex.exercise_id)}</div>` : '';
}

/** Fallback card content when a renderer throws. */
export function renderErrorHtml(prefix, ex, escHtml) {
  return (
    prefix +
    `<p style="color:var(--danger)">Error rendering exercise: ${escHtml(ex.exercise_type)}</p>`
  );
}

const nextInner = () =>
  `<span>${T('session.next_item', null, 'Next')}</span><i class="fas fa-arrow-right ms-2"></i>`;

/** Markup of the session "Next" button for a results card. */
export function nextButtonHtml() {
  return `<button class="btn btn-primary" type="button" data-session-next>${nextInner()}</button>`;
}

/** Append a lone "Next" button (no items / load failed). */
export function appendNextButton(card, className) {
  const btn = document.createElement('button');
  btn.className = className;
  btn.type = 'button';
  btn.setAttribute('data-session-next', '');
  btn.innerHTML = nextInner();
  card.appendChild(btn);
}

/** One figure ("12/15" over "Correct") on a results card. */
export function statHtml(value, label, color = 'var(--primary)') {
  return `<div><div style="font-size:1.6rem;font-weight:700;color:${color}">${value}</div><div class="text-muted small">${label}</div></div>`;
}

/** Wire the "Next" button to finish the item with `result()`. */
export function wireNext(container, ctx, result) {
  const btn = container.querySelector('[data-session-next]');
  if (btn) btn.onclick = () => ctx.onComplete(result());
}
