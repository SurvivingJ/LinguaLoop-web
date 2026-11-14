// static/js/session/players/practice.js
// Practice (vocab/exercises) player for the daily-session runner. Reuses the
// shared global ExRenderers module (static/js/exercise-renderers.js, loaded by
// study_session.html) exactly as templates/vocab_dojo.html does, but sources
// items from the Study-Plan practice surface (/api/practice/session) and
// records attempts via /api/practice/attempt with session_mode so the weekly
// counters advance. Gate / stress-test marker items are skipped in this v1
// (they require the separate /api/vocab-dojo battery endpoints).
//
// Injected DT error-remediation cards (TASK-618) ARE rendered, by the shared
// global window.DTErrorCard (static/js/dt-error-card.js) — TASK-731. They are
// deliberately NOT routed through ER.dispatch or submitAttempt: FSRS state for
// an error card lives on dt_card and is graded at
// POST /api/dual-translation/cards/<id>/review. Sending one to
// /api/practice/attempt would write it into the sense-keyed practice system and
// silently corrupt the recurrence metric the feature exists to measure.

import { extraRequestUrl } from '../tail.js';
import { runIntroDrill, INTRO_STYLES } from './intro_drill.js';
import { T, escapeHtml, nowMs, toastSaveFailed } from '../dom.js';
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

/** /api/practice/session URL for a daily practice chunk (one queue item). */
export function practiceSessionUrl(item, languageId) {
  const mode = (item && item.mode) || 'acquisition';
  const minutes = (item && item.minutes) || 10;
  const isTail = !!(item && item.is_tail);
  return `/api/practice/session?mode=${encodeURIComponent(mode)}&minutes=${minutes}&language_id=${languageId}${isTail ? '&tail=1' : ''}`;
}

/** Load one round: resolves to { ok, data }, never rejects. */
export async function fetchPracticePayload(url) {
  try {
    const res = await window.authFetch(url);
    let data = {};
    try {
      data = (await res.json()) || {};
    } catch {
      data = {};
    }
    return { ok: !!(res && res.ok), data };
  } catch {
    return { ok: false, data: {}, failed: true };
  }
}

/**
 * What a loaded round holds, so the learner sees it before starting:
 * { exercises, newWords, drillReviews, minutes }. `exercises` counts the items
 * the player will serve (DT error cards only when their renderer is loaded).
 * The new-word drill is counted in words, since its item count adapts to the
 * answers: `newWords` are on their first drill session, `drillReviews` on
 * sessions 2-4. `minutes` adds the items' expected seconds to the drill's own
 * estimate.
 */
export function summarizePracticePayload(data) {
  const d = data || {};
  const canRenderErrorCards = typeof window !== 'undefined' && !!window.DTErrorCard;
  const items = (d.items || d.exercises || []).filter(
    (it) => canRenderErrorCards || !it.is_error_exercise
  );
  const intro = d.intro_drill;
  const words = intro && Array.isArray(intro.words) ? intro.words : [];
  const newWords = words.filter((w) => (Number(w.stage) || 1) <= 1).length;
  const drillReviews = words.length - newWords;
  const seconds =
    items.reduce((s, it) => s + (Number(it.expected_seconds) || 30), 0) +
    (words.length ? (Number(intro.est_minutes) || 0) * 60 : 0);
  return {
    exercises: items.length,
    newWords,
    drillReviews,
    minutes: items.length || words.length ? Math.max(1, Math.round(seconds / 60)) : 0,
  };
}

/**
 * The start card's line for a round: "12 exercises · about 6 min", plus the
 * new-word drill's words (new and to review) and how many practice rounds
 * follow. `t` is the
 * caller's translate function (key, params, fallback). '' when the round is
 * empty and nothing follows.
 */
export function practiceCountText(summary, moreRounds, t) {
  const s = summary || {};
  const parts = [];
  if (s.exercises > 0) {
    parts.push(
      s.exercises === 1
        ? t('session.count_exercises_one', null, '1 exercise')
        : t('session.count_exercises', { count: s.exercises }, `${s.exercises} exercises`)
    );
  }
  if (s.newWords > 0) {
    parts.push(
      s.newWords === 1
        ? t('session.count_new_words_one', null, '1 new word to learn')
        : t('session.count_new_words', { count: s.newWords }, `${s.newWords} new words to learn`)
    );
  }
  if (s.drillReviews > 0) {
    parts.push(
      s.drillReviews === 1
        ? t('session.count_drill_reviews_one', null, '1 word to review')
        : t('session.count_drill_reviews', { count: s.drillReviews }, `${s.drillReviews} words to review`)
    );
  }
  if (!parts.length) {
    return moreRounds > 0 ? '' : t('session.count_none', null, 'Nothing to practise right now');
  }
  if (s.minutes > 0) {
    parts.push(t('session.count_minutes', { minutes: s.minutes }, `about ${s.minutes} min`));
  }
  if (moreRounds > 0) {
    parts.push(
      moreRounds === 1
        ? t('session.count_more_rounds_one', null, 'then 1 more round')
        : t('session.count_more_rounds', { count: moreRounds }, `then ${moreRounds} more rounds`)
    );
  }
  return parts.join(' · ');
}

// Items that record practice attempts: the next round's content depends on
// the answers still being given, so it must not be loaded while one runs.
const ATTEMPT_KINDS = { practice: true, speed_round: true };

/**
 * Session prefetch hook: load a daily practice round ahead of its player.
 * Skipped for extra rounds (built from the learner's choice at start time).
 */
export function prefetch(item, ctx) {
  if (!item || item.is_extra) return null;
  const current = ctx && ctx.current;
  if (current && ATTEMPT_KINDS[current.kind]) return null;
  return fetchPracticePayload(practiceSessionUrl(item, ctx && ctx.languageId));
}

/** Start-card line for a prefetched round ('' when it failed to load). */
export function describePrefetch(res, { moreRounds, t }) {
  return res && res.ok ? practiceCountText(summarizePracticePayload(res.data), moreRounds, t) : '';
}

export function mount(container, ctx) {
  const mode = (ctx.item && ctx.item.mode) || 'acquisition';
  const minutes = (ctx.item && ctx.item.minutes) || 10;
  const languageId = ctx.languageId;
  // session-budget-settings: items of the optional "Keep going?" round carry
  // is_tail; the flag goes on the session URL and is echoed on attempt POSTs.
  const isTail = !!(ctx.item && ctx.item.is_tail);
  // Practice extra rounds (ADR-036): items come from /api/practice/extra and
  // mix reviews with new words, so each attempt is credited by its own mode.
  const extra = ctx.item && ctx.item.is_extra ? ctx.item.extra || {} : null;

  const state = {
    exercises: [],
    retryQueue: [],
    currentIndex: 0,
    correctCount: 0,
    totalAnswered: 0,
    isAnswered: false,
    // TASK-701: timestamp (performance.now) of when the current item was
    // rendered, so we can measure render→submit elapsed and credit real
    // practice minutes server-side.
    renderedAt: 0,
    // Handle to a mounted DT error card, so a re-render can tear it down.
    errorCard: null,
  };

  const q = (id) => container.querySelector('#' + id);
  container.innerHTML = MARKUP + `<style>${INTRO_STYLES}</style>`;

  const ER = window.ExRenderers;
  const escHtml = ER && ER.escHtml ? ER.escHtml : escapeHtml;
  const shuffleArr = ER && ER.shuffleArr ? ER.shuffleArr : (a) => a.slice();

  function initRenderers() {
    bindRenderers(ER, q('exerciseCard'), state, { showFeedback, submitAttempt, nextExercise });
  }
  initRenderers();

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
      // The start card may already have loaded this round to show its size;
      // use that payload once instead of asking the server again.
      const pre = !extra && ctx.item && ctx.item.prefetch;
      if (pre) delete ctx.item.prefetch;
      let res = pre ? await pre : null;
      if (!res || !res.ok) {
        res = await fetchPracticePayload(
          extra
            ? extraRequestUrl(languageId, extra, extra.exclude)
            : practiceSessionUrl({ mode, minutes, is_tail: isTail }, languageId)
        );
      }
      if (res.failed) throw new Error('practice load failed'); // network: show the error card
      const data = res.data;
      // Skip gate / stress markers (they need the separate /api/vocab-dojo
      // battery endpoints). Injected DT error-remediation cards are kept and
      // rendered by renderErrorCard below (TASK-731). If the shared renderer
      // global is missing, drop them rather than showing a broken item.
      const canRenderErrorCards = !!window.DTErrorCard;
      // Gate / stress-test markers stay in the queue: renderExercise opens
      // their battery (POST /api/vocab-dojo/gate | /stress-test) in place.
      const items = (data.items || data.exercises || []).filter(
        (it) => canRenderErrorCards || !it.is_error_exercise
      );
      if (!canRenderErrorCards) {
        console.error('practice: DTErrorCard global not loaded — error cards dropped');
      }

      // New-word drill (ADR-040): due intro words run first, then the items.
      const intro = data.intro_drill;
      if (res.ok && intro && Array.isArray(intro.words) && intro.words.length) {
        const headEl = container.querySelector('[data-i18n="session.practice_heading"]');
        // With only a few drill words, up to 3 ordinary items go between their
        // repeats (recorded as normal practice attempts) and are then not
        // served again below.
        const spacers = intro.words.length < 5
          ? items.filter((it) => !it.is_gate_marker && !it.is_stress_test_marker && !it.is_error_exercise).slice(0, 3)
          : [];
        const done = await runIntroDrill(q('exerciseCard'), intro, {
          setHeader: (t) => {
            if (headEl) headEl.textContent = t;
          },
          spacers,
          onSpacer: (ex, ok, response, ms) => {
            state.totalAnswered++;
            if (ok) state.correctCount++;
            postAttempt(ex, ok, response, ms).catch((e) => console.error('spacer attempt error:', e));
          },
        });
        const used = new Set(spacers.slice(0, done.usedSpacers || 0));
        for (let i = items.length - 1; i >= 0; i--) if (used.has(items[i])) items.splice(i, 1);
        state.introWords = done.words;
        if (headEl) headEl.textContent = T('session.practice_heading', null, 'Practice');
        initRenderers();
        if (items.length === 0) {
          showComplete();
          return;
        }
      }

      if (!res.ok || items.length === 0) {
        q('exerciseCard').innerHTML =
          `<p style="text-align:center;color:var(--text-secondary);padding:32px">${T('session.practice_empty', null, 'No practice items right now — you can move on.')}</p>`;
        renderNextOnly();
        return;
      }
      state.exercises = items;
      if (extra) {
        // Remembered so the next round's reviews skip this round's words.
        ctx.item.served_sense_ids = items
          .map((it) => it.sense_id)
          .filter((sid) => Number.isInteger(sid));
      }
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

    // Ladder checkpoint (gate) or final test (stress test): fetch its battery
    // and run it in place of the marker.
    if (ex.is_gate_marker || ex.is_stress_test_marker) {
      openBattery(ex);
      return;
    }

    // DT error cards bypass ER.dispatch entirely — different renderer,
    // different grade endpoint, no sense linkage.
    if (ex.is_error_exercise) {
      renderErrorCard(ex);
      return;
    }

    const c = ex.content || {};

    // Surfaced on every render (including the error fallback below) so a
    // broken exercise can be reported by ID instead of by vague description.
    const idBadge = exerciseIdBadge(ex, escHtml);
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
    let batteryBadge = '';
    if (ex.battery) {
      const b = ex.battery;
      const label = b.kind === 'gate'
        ? T('session.checkpoint_badge', { i: b.results.length + 1, n: b.size }, 'Checkpoint · {i} of {n}')
        : T('session.final_test_badge', { i: b.results.length + 1, n: b.size }, 'Final test · {i} of {n}');
      batteryBadge = `<div class="ladder-badge"><i class="fas fa-flag-checkered"></i> ${escHtml(label)}</div>`;
    }
    const w = idBadge + batteryBadge + ribbon + ladderBadge;

    // Start the per-item timer as the exercise becomes visible (TASK-701).
    state.renderedAt = nowMs();

    try {
      ER.dispatch(ex.exercise_type, ex, c, w);
    } catch (e) {
      console.error('Render error for', ex.exercise_type, ex.exercise_id, e);
      q('exerciseCard').innerHTML = renderErrorHtml(w, ex, escHtml);
    }
  }

  // Render one injected DT error card. Grading happens inside DTErrorCard
  // (POST /api/dual-translation/cards/<id>/review); we only count it toward
  // the session tallies and advance. `was_correct` is null for
  // isolate_retranslate cards — there we fall back to the FSRS rating, matching
  // the server's own default.
  function renderErrorCard(ex) {
    state.renderedAt = nowMs();
    state.errorCard = window.DTErrorCard.mount(q('exerciseCard'), ex, {
      onDone: (result) => {
        state.totalAnswered++;
        const ok =
          result.was_correct === null || result.was_correct === undefined
            ? result.rating !== window.DTErrorCard.RATING_AGAIN
            : result.was_correct;
        if (ok) state.correctCount++;
        nextExercise();
      },
    });
  }

  function showFeedback(ok, expl) {
    renderFeedback(container, ok, expl, { correctIcon: 'fa-check-circle', escHtml });
  }

  // POST one attempt. authFetch resolves on 4xx/5xx, so check r.ok explicitly;
  // returns the parsed body on success, or null on any failure.
  // `timeTakenMs` is the measured render→submit elapsed for this item; the
  // server clamps absurd values and falls back to `expected_seconds` (TASK-701).
  async function postAttempt(ex, ok, response, timeTakenMs) {
    const r = await window.authFetch('/api/practice/attempt', {
      method: 'POST',
      body: JSON.stringify({
        exercise_id: ex.exercise_id,
        is_correct: ok,
        user_response: response,
        time_taken_ms: timeTakenMs,
        expected_seconds: ex.expected_seconds,
        session_mode:
          extra && (ex.mode === 'acquisition' || ex.mode === 'maintenance') ? ex.mode : mode,
        language_id: languageId,
        ...(isTail ? { is_tail: true } : {}),
        ...(ex.battery ? { exercise_context: ex.battery.kind === 'gate' ? 'gate' : 'stress_test' } : {}),
      }),
    });
    if (!r || !r.ok) return null;
    return r.json();
  }

  async function submitAttempt(ok, response) {
    const ex = state.exercises[state.currentIndex];
    if (!ex) return;
    state.totalAnswered++;
    if (ok) state.correctCount++;

    // Measure once, before the retry loop, so a retry doesn't inflate the
    // elapsed time. 0 when the timer never started — the server credits the
    // item's expected_seconds estimate rather than nothing.
    const elapsedMs = state.renderedAt ? Math.max(0, Math.round(nowMs() - state.renderedAt)) : 0;

    let data = null;
    for (let attempt = 0; attempt < 2 && data === null; attempt++) {
      try {
        data = await postAttempt(ex, ok, response, elapsedMs); // one silent retry on failure (M2)
      } catch (e) {
        console.error('Practice attempt error:', e);
        data = null;
      }
    }
    if (data === null) {
      // Persisted nothing — surface it instead of silently dropping the attempt.
      toastSaveFailed();
    } else if (data.requeue && !ok && !ex.battery) {
      state.retryQueue.push({ ...ex, _retry: true });
    }
    // Battery items are first-try only; the last one submits the battery.
    if (ex.battery) {
      ex.battery.results.push({ exercise_id: ex.exercise_id, is_correct: !!ok });
      if (ex.battery.results.length === ex.battery.size) await submitBattery(ex.battery);
    }
  }

  // ---- Ladder checkpoints and final test (ADR-005) ---------------------

  async function openBattery(marker) {
    const isGate = !!marker.is_gate_marker;
    q('exerciseCard').innerHTML =
      `<p style="text-align:center;color:var(--text-secondary);padding:32px">${escHtml(T('session.checkpoint_loading', null, 'Getting your checkpoint ready…'))}</p>`;
    let battery = null;
    try {
      const r = await window.authFetch(isGate ? '/api/vocab-dojo/gate' : '/api/vocab-dojo/stress-test', {
        method: 'POST',
        body: JSON.stringify({
          sense_id: marker.sense_id,
          language_id: languageId,
          ...(isGate ? { gate_name: marker.gate_name } : {}),
        }),
      });
      const j = r && r.ok ? await r.json() : null;
      battery = j ? j.data || j : null;
    } catch (e) {
      console.warn('[practice] battery not loaded:', e);
    }
    const exercises = (battery && battery.exercises) || [];
    if (!exercises.length || (isGate && !['gate_a', 'gate_b'].includes(marker.gate_name))) {
      // Nothing to run (no exercises yet): skip the marker, the word stays gated.
      state.exercises.splice(state.currentIndex, 1);
      renderExercise();
      return;
    }
    const b = {
      kind: isGate ? 'gate' : 'stress',
      gate_name: marker.gate_name,
      sense_id: marker.sense_id,
      token: battery.battery_token,
      size: exercises.length,
      results: [],
    };
    const items = exercises.map((e) => ({
      ...e,
      sense_id: e.sense_id || marker.sense_id,
      expected_seconds: 30,
      mode: marker.mode || mode,
      battery: b,
    }));
    state.exercises.splice(state.currentIndex, 1, ...items);
    renderExercise();
  }

  async function submitBattery(b) {
    let res = null;
    try {
      const r = await window.authFetch(
        b.kind === 'gate' ? '/api/vocab-dojo/gate/result' : '/api/vocab-dojo/stress-test/result',
        {
          method: 'POST',
          body: JSON.stringify({
            sense_id: b.sense_id,
            language_id: languageId,
            battery_token: b.token,
            results: b.results,
            ...(b.kind === 'gate' ? { gate_name: b.gate_name } : {}),
          }),
        }
      );
      const j = r && r.ok ? await r.json() : null;
      res = j ? j.data || j : null;
    } catch (e) {
      console.warn('[practice] battery result not saved:', e);
    }
    const fb = container.querySelector('#exerciseFeedback');
    if (!fb || !res) return;
    const passed = res.passed !== false && !res.error;
    const score = `${res.correct}/${res.battery_size}`;
    const key = b.kind === 'gate'
      ? (passed ? 'session.checkpoint_passed' : 'session.checkpoint_failed')
      : (passed ? 'session.final_test_passed' : 'session.final_test_failed');
    const fallback = {
      'session.checkpoint_passed': 'Checkpoint passed ({score}) — this word moves up a ring.',
      'session.checkpoint_failed': 'Checkpoint not passed ({score}) — keep practising this word and it will come back.',
      'session.final_test_passed': 'Final test passed ({score}) — this word is mastered and moves to long-term review.',
      'session.final_test_failed': 'Final test not passed ({score}) — a little more practice first.',
    }[key];
    const div = document.createElement('div');
    div.className = 'battery-result';
    div.style.cssText = 'margin-top:10px;font-weight:600';
    div.textContent = T(key, { score }, fallback);
    fb.appendChild(div);
  }

  function nextExercise() {
    if (state.errorCard) {
      state.errorCard.destroy();
      state.errorCard = null;
    }
    state.currentIndex++;
    renderExercise();
  }

  function updateProgress() {
    renderProgress(
      container,
      state.currentIndex,
      state.exercises.length,
      state.correctCount,
      state.totalAnswered
    );
  }

  function showComplete() {
    q('progressArea').style.display = 'none';
    const acc = accuracyPct(state.correctCount, state.totalAnswered);
    q('exerciseCard').innerHTML = `
            <div style="text-align:center;padding:24px">
                <div style="font-size:2.5rem">✅</div>
                <h2 class="h4 mb-3">${T('session.practice_done', null, 'Practice complete!')}</h2>
                ${state.introWords ? `<p class="text-muted">${T('intro.done', { n: state.introWords }, 'New-word drill done: {n} words.')}</p>` : ''}
                <div class="d-flex gap-4 justify-content-center mb-3"${state.introWords && !state.totalAnswered ? ' hidden' : ''}>
                    ${statHtml(`${state.correctCount}/${state.totalAnswered}`, T('session.correct_label', null, 'Correct'))}
                    ${statHtml(`${acc}%`, T('session.accuracy', null, 'Accuracy'))}
                </div>
                ${nextButtonHtml()}
            </div>`;
    wireNext();
  }

  // Used when there are no items / renderer missing: just a Next button.
  function renderNextOnly() {
    q('progressArea').style.display = 'none';
    appendNextButton(q('exerciseCard'), 'btn btn-primary mt-2');
    wireNext();
  }

  function wireNext() {
    wireNextButton(container, ctx, () => ({
      correct: state.correctCount,
      total: state.totalAnswered,
    }));
  }
}

// ========================================================================
// MARKUP — the shared exercise styles plus the practice-only ones.
// ========================================================================
const MARKUP = `
<style>${EXERCISE_BASE_STYLES}
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
    .js-chunk.disabled { cursor: default; }
    /* A chunk in the answer box is removable — the × says so, and turning it
       red on hover says which way the click goes. */
    .js-chunk--placed::after { content: '\\00d7'; margin-left: 8px; color: var(--text-secondary); font-weight: 700; }
    .js-chunk--placed:hover { border-color: var(--danger); }
    .js-chunk--placed:hover::after { color: var(--danger); }
    .js-chunk--placed.disabled::after { content: none; }
    /* Drop target caret for drag-reordering. Without a rule the element is
       created on every dragover and renders as nothing. */
    .js-drop-indicator { width: 3px; align-self: stretch; min-height: 28px; background: var(--primary); border-radius: 2px; }
    .js-bank.drag-over, .js-answer.drag-over { border-color: var(--primary); background: rgba(30,64,175,0.08); }
    .sentence-card { padding: 14px 18px; background: var(--bg-surface); border: 2px solid var(--border-default); border-radius: 12px; cursor: pointer; transition: all .2s; font-size: 15px; line-height: 1.6; }
    .sentence-card:hover:not(.disabled) { border-color: var(--primary); }
    .sentence-card.correct { border-color: var(--success); background: rgba(5,150,105,0.08); }
    .sentence-card.incorrect { border-color: var(--danger); background: rgba(220,38,38,0.08); }
</style>
${sessionHeadHtml('fa-dumbbell', 'session.practice_heading', 'Practice')}

<div class="exercise-card-area" id="exerciseCard"></div>
`;
