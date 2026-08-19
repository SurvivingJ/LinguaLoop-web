// static/js/session/players/dual_translation.js
// Dual Translation player for the daily-session runner (TASK-714 / ADR-021).
//
// DT is graded, effortful production work that competes directly with test
// time, so excluding it made the Tests budget dishonest. One queue item is one
// passage (12 min/slot per test_time_estimate).
//
// Reuses the existing standalone endpoints unchanged:
//   GET  /api/dual-translation/next              -> {type:'passage', ...}
//                                                |  {type:'error_card', ...}
//   POST /api/dual-translation/<id>/submit       -> grade envelope
//
// error_card items are NOT rendered here. The backend already interleaves due
// remediation cards into /next, but no cloze/isolate renderer exists on any
// surface yet — the same gap the standalone page and the practice player have.
// Rather than show a broken card we re-request once for a passage, then fall
// back to a skip affordance. Wiring the error-card UI is the tracked follow-up
// and this player will pick it up when it lands.

const T = (key, params, fallback) =>
  window.LinguaI18n && typeof LinguaI18n.t === 'function'
    ? LinguaI18n.t(key, params) || fallback || key
    : fallback || key;

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : s;
  return d.innerHTML;
}

// How many times to re-request /next when it serves an error_card we cannot
// render. Bounded so a learner whose queue is all error cards still advances.
const MAX_ERROR_CARD_RETRIES = 2;

export function mount(container, ctx) {
  const state = { submissionId: null, submitting: false, destroyed: false };

  container.innerHTML = `
    <div class="session-card"><div class="card"><div class="card-body p-4">
      <div id="dtBody">
        <div class="text-center"><div class="spinner-border" role="status" aria-hidden="true"></div></div>
      </div>
    </div></div></div>`;

  const body = () => container.querySelector('#dtBody');

  load(0);

  return {
    destroy() {
      state.destroyed = true;
    },
  };

  async function load(attempt) {
    let data;
    try {
      const res = await window.authFetch('/api/dual-translation/next');
      const payload = await res.json();
      data = payload.data || payload;
      if (!res.ok) throw new Error(`next failed (${res.status})`);
    } catch (e) {
      console.error('dual_translation: failed to fetch next passage', e);
      renderUnavailable(
        T('session.dt_unavailable', null, 'Couldn’t load a translation passage right now.')
      );
      return;
    }
    if (state.destroyed) return;

    if (data.type === 'error_card') {
      if (attempt < MAX_ERROR_CARD_RETRIES) {
        load(attempt + 1);
        return;
      }
      renderUnavailable(
        T(
          'session.dt_error_card_pending',
          null,
          'Your next item is a review card, which isn’t playable here yet.'
        )
      );
      return;
    }

    state.submissionId = data.submission_id;
    renderPassage(data);
  }

  function renderUnavailable(message) {
    if (state.destroyed) return;
    body().innerHTML = `
      <div class="text-center">
        <h2 class="h5 mb-2">${esc(T('session.dt_heading', null, 'Dual Translation'))}</h2>
        <p class="text-muted">${esc(message)}</p>
        <a class="btn btn-outline-primary me-2" href="/dual-translation">${esc(
          T('session.open_page', null, 'Open page')
        )}</a>
        <button class="btn btn-secondary" type="button" data-dt-skip>${esc(
          T('session.skip_for_now', null, 'Skip for now')
        )}</button>
      </div>`;
    const skip = body().querySelector('[data-dt-skip]');
    if (skip) skip.onclick = () => ctx.onSkip && ctx.onSkip();
  }

  function renderPassage(data) {
    if (state.destroyed) return;
    body().innerHTML = `
      <h2 class="h5 mb-2">${esc(T('session.dt_heading', null, 'Dual Translation'))}</h2>
      <p class="text-muted small mb-3">${esc(
        T(
          'session.dt_instructions',
          null,
          'Reproduce this passage in the language you’re studying.'
        )
      )}</p>
      <blockquote class="border-start border-3 ps-3 mb-3">${esc(data.l1_text || '')}</blockquote>
      <label class="form-label" for="dtInput">${esc(
        T('session.dt_input_label', null, 'Your translation')
      )}</label>
      <textarea id="dtInput" class="form-control mb-3" rows="8"></textarea>
      <button class="btn btn-primary" type="button" data-dt-submit>${esc(
        T('session.dt_submit', null, 'Submit translation')
      )}</button>`;

    body().querySelector('[data-dt-submit]').onclick = submit;
  }

  async function submit() {
    // Re-entrancy latch: grading runs an LLM cascade, so a double-click would
    // burn a second run. (The route is idempotent per submission; the latch
    // avoids the round trip and keeps the UI honest.)
    if (state.submitting || state.destroyed) return;
    state.submitting = true;

    const input = body().querySelector('#dtInput');
    const button = body().querySelector('[data-dt-submit]');
    const reproduction = (input && input.value) || '';
    if (button) button.disabled = true;

    let grade = null;
    try {
      const res = await window.authFetch(
        `/api/dual-translation/${encodeURIComponent(state.submissionId)}/submit`,
        { method: 'POST', body: JSON.stringify({ reproduction }) }
      );
      const payload = await res.json();
      grade = payload.data || payload;
      if (!res.ok) throw new Error(`submit failed (${res.status})`);
    } catch (e) {
      console.error('dual_translation: submit failed', e);
      if (typeof window.showToast === 'function') {
        window.showToast(
          T('session.save_failed', null, 'Couldn’t save your progress — check your connection.')
        );
      }
      // The learner did the work; advance rather than trapping them here.
      state.submitting = false;
      finish();
      return;
    }
    if (state.destroyed) return;
    state.submitting = false;
    renderResult(grade);
  }

  function renderResult(grade) {
    if (state.destroyed) return;
    const score = grade && (grade.overall_score != null ? grade.overall_score : grade.score);
    body().innerHTML = `
      <div class="text-center">
        <h2 class="h5 mb-2">${esc(T('session.dt_graded', null, 'Translation graded'))}</h2>
        ${
          score != null
            ? `<p class="display-6 mb-3">${esc(String(score))}</p>`
            : `<p class="text-muted mb-3">${esc(
                T('session.dt_graded_no_score', null, 'Your work has been recorded.')
              )}</p>`
        }
        <a class="btn btn-outline-secondary me-2" href="/dual-translation">${esc(
          T('session.dt_see_details', null, 'See full feedback')
        )}</a>
        <button class="btn btn-primary" type="button" data-dt-continue>${esc(
          T('session.continue', null, 'Continue')
        )}</button>
      </div>`;
    body().querySelector('[data-dt-continue]').onclick = finish;
  }

  function finish() {
    if (state.destroyed) return;
    if (ctx.onComplete) ctx.onComplete({ submission_id: state.submissionId });
  }
}
