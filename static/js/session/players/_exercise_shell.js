// static/js/session/players/_exercise_shell.js
// Chrome shared by the players that run ExRenderers exercises (practice.js and
// speed_round.js): the session frame (scrolling stage + pinned dock), the
// progress row, answer feedback and the "Next" button that hands control back
// to the session. Styles live in static/css/redesign/session.css (.ex-screen).

import { T } from '../dom.js';

/**
 * The player's screen: a scrolling stage (progress row + #exerciseCard) and a
 * pinned dock (#exerciseDock) for feedback, Check and Next. `extra` is markup
 * placed between the progress row and the card (the speed-round clock).
 */
export function exerciseScreenHtml(icon, headingKey, heading, extra = '') {
  return `
<div class="ld-screen ex-screen">
  <div class="ld-stage ex-stage" id="exerciseStage">
    ${sessionHeadHtml(icon, headingKey, heading)}
    ${extra}
    <div class="exercise-card-area" id="exerciseCard"></div>
  </div>
  <div class="ld-dock ex-dock" id="exerciseDock"></div>
</div>`;
}

/** The player's title row with the (initially hidden) progress block. */
export function sessionHeadHtml(icon, headingKey, heading) {
  return `
<div class="vd-session-head">
    <span class="vd-session-title"><i class="fas ${icon} me-2" aria-hidden="true"></i><span data-i18n="${headingKey}">${heading}</span></span>
    <div class="vd-progress" id="progressArea" style="display:none">
        <span class="vd-progress-text ld-num" id="progressText">0 / 0</span>
        <div class="vd-progress-bar ld-bar"><div class="vd-progress-fill" id="progressFill"></div></div>
        <span class="vd-score ld-num" id="scoreText"></span>
    </div>
</div>`;
}

/**
 * Mark the screen as running inside the session frame: the runner's header
 * then carries the title and the "3 / 12 · 80%" count, so the in-stage title
 * and numbers are hidden (the bar stays). No-op without a frame.
 */
export function useFrame(container, ctx) {
  const frame = ctx && ctx.frame;
  if (!frame) return null;
  const root = container.querySelector('.ex-screen');
  if (root) root.classList.add('has-frame');
  return frame;
}

/** Whole-percent accuracy; 0 before anything is answered. */
export function accuracyPct(correct, answered) {
  return answered ? Math.round((correct / answered) * 100) : 0;
}

/** Point ExRenderers at this player's card, dock and callbacks. */
export function bindRenderers(ER, cardEl, state, handlers, dockEl) {
  if (!ER || !ER.init) return;
  ER.init({
    cardEl,
    dockEl: dockEl || null,
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

/** The header's right-hand count: "3 / 12 · 80%" (no accuracy before an answer). */
export function progressEndText(done, total, correct, answered) {
  const pos = `${Math.min(done + 1, total)} / ${total}`;
  return answered ? `${pos} · ${accuracyPct(correct, answered)}%` : pos;
}

/** Fill the renderer's #exerciseFeedback and reveal its Next button. */
export function renderFeedback(container, ok, expl, { correctIcon, escHtml }) {
  const fb = container.querySelector('#exerciseFeedback');
  if (!fb) return;
  fb.className =
    'exercise-feedback show ld-feedback ' +
    (ok ? 'correct ld-feedback--ok' : 'incorrect ld-feedback--bad');
  let html = ok
    ? `<b><i class="fas ${correctIcon} me-2" aria-hidden="true"></i>${T('session.correct', null, 'Correct!')}</b>`
    : `<b><i class="fas fa-times-circle me-2" aria-hidden="true"></i>${T('session.incorrect', null, 'Incorrect')}</b>`;
  // Leading blank lines (e.g. "\nExpected: …") would show as an empty row.
  const text = expl ? String(expl).replace(/^\s+/, '') : '';
  if (text) html += `<div class="ex-expl">${escHtml(text)}</div>`;
  fb.innerHTML = html;
  const hint = container.querySelector('.ex-dock-hint');
  if (hint) hint.remove();
  const btn = container.querySelector('#nextBtn');
  if (btn) {
    btn.classList.add('show');
    // Keyboard users land on Next; scroll the stage, never the page.
    try {
      btn.focus({ preventScroll: true });
    } catch {
      /* focus options unsupported */
    }
  }
  // After the dock has its final size (feedback + Next).
  revealAnswer(container);
}

/**
 * The feedback in the dock shrinks the stage, which can push the marked answer
 * (the right option, the learner's wrong pick, the correction line) below its
 * fold. Scroll the stage (never the page) so they are in view, keeping the
 * first of them at the top if they do not all fit.
 */
export function revealAnswer(container) {
  const stage = container.querySelector('#exerciseStage');
  if (!stage || stage.clientHeight === 0) return;
  const marks = [
    ...stage.querySelectorAll(
      '.exercise-option.correct, .exercise-option.incorrect, .sip-part.correct, .sip-part.incorrect, .sip-correction'
    ),
  ].filter((el) => el.offsetParent !== null && getComputedStyle(el).display !== 'none');
  if (!marks.length) return;
  const box = stage.getBoundingClientRect();
  const top = Math.min(...marks.map((el) => el.getBoundingClientRect().top));
  const bottom = Math.max(...marks.map((el) => el.getBoundingClientRect().bottom));
  const pad = 8;
  let delta = 0;
  if (bottom > box.bottom - pad) delta = bottom - box.bottom + pad;
  if (top - delta < box.top + pad) delta = top - box.top - pad;
  if (delta > 0) stage.scrollTop += delta;
}

/** The small monospace exercise id shown above every item. */
export function exerciseIdBadge(ex, escHtml) {
  return ex.exercise_id ? `<div class="exercise-id-badge">${escHtml(ex.exercise_id)}</div>` : '';
}

/** Fallback card content when a renderer throws. */
export function renderErrorHtml(prefix, ex, escHtml) {
  return (
    prefix +
    `<p class="ex-message ex-message--bad">Error rendering exercise: ${escHtml(ex.exercise_type)}</p>`
  );
}

/** A centred message in the card (empty round, load failed, checkpoint loading). */
export function messageHtml(text, bad = false) {
  return `<p class="ex-message${bad ? ' ex-message--bad' : ''}">${text}</p>`;
}

const nextInner = () =>
  `<span>${T('session.next_item', null, 'Next')}</span><i class="fas fa-arrow-right" aria-hidden="true"></i>`;

/** Markup of the session "Next" button for a results card. */
export function nextButtonHtml() {
  return `<button class="ld-btn ld-btn--block" type="button" data-session-next>${nextInner()}</button>`;
}

/** Append a lone "Next" button (no items / load failed). */
export function appendNextButton(card, className) {
  const btn = document.createElement('button');
  btn.className = className || 'ld-btn ld-btn--block';
  btn.type = 'button';
  btn.setAttribute('data-session-next', '');
  btn.innerHTML = nextInner();
  card.appendChild(btn);
}

/** One figure ("12/15" over "Correct") on a results card. */
export function statHtml(value, label) {
  return `<div class="ld-stat"><div class="ld-stat__n">${value}</div><small>${label}</small></div>`;
}

/** Wire the "Next" button to finish the item with `result()`. */
export function wireNext(container, ctx, result) {
  const btn = container.querySelector('[data-session-next]');
  if (btn) btn.onclick = () => ctx.onComplete(result());
}
