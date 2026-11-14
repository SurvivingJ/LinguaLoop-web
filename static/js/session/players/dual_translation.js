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
// error_card items ARE rendered here (TASK-731) via the shared global
// window.DTErrorCard (static/js/dt-error-card.js, loaded by study_session.html),
// the same renderer the standalone page and the practice player use. The card
// grades itself to POST /api/dual-translation/cards/<id>/review — NOT to the
// submit endpoint above — because FSRS state for error cards lives on dt_card.
// One served card satisfies the queue item, exactly as one passage does.

import { T, escapeHtml as esc } from '../dom.js';

export function mount(container, ctx) {
  const timer =
    window.ActiveTimer && typeof window.ActiveTimer.create === 'function'
      ? window.ActiveTimer.create()
      : null;
  const state = {
    submissionId: null,
    submitting: false,
    destroyed: false,
    card: null,
    primedToken: null,
    l1Text: '',
    ageTier: null,
    reproduction: '',
    activeMs: null,
    eventId: null,
  };

  container.innerHTML = `
    <div class="session-card"><div class="card"><div class="card-body p-4">
      <div id="dtBody">
        <div class="text-center"><div class="spinner-border" role="status" aria-hidden="true"></div></div>
      </div>
    </div></div></div>`;

  const body = () => container.querySelector('#dtBody');

  load();

  return {
    destroy() {
      state.destroyed = true;
      if (timer) timer.reset();
      if (state.card) state.card.destroy();
    },
  };

  // Test prestudy Produce (wiki/features/test-prestudy.md): when the learner
  // finished a prestudy follow-up in this session, today's translation slot
  // uses the window of that test with the most primed words. Falls back to the
  // ordinary next passage on any failure (e.g. no references in this language).
  async function loadProduce() {
    const L = window.LinguaPrestudyLinks;
    const req = L && L.takeProduceRequest ? L.takeProduceRequest() : null;
    if (!req) return null;
    try {
      const res = await window.authFetch(
        `/api/tests/${encodeURIComponent(req.slug)}/prestudy/produce`,
        {
          method: 'POST',
          body: JSON.stringify({}),
        }
      );
      if (!res.ok) return null;
      const payload = await res.json();
      const data = payload.data || payload;
      return data && data.submission_id ? data : null;
    } catch (e) {
      console.warn('dual_translation: prestudy Produce unavailable, using next passage', e);
      return null;
    }
  }

  async function load() {
    const produce = await loadProduce();
    if (state.destroyed) return;
    if (produce) {
      state.submissionId = produce.submission_id;
      state.primedToken = produce.primed_token || null;
      renderPassage(produce);
      return;
    }
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
      renderErrorCard(data);
      return;
    }

    state.submissionId = data.submission_id;
    renderPassage(data);
  }

  function renderErrorCard(card) {
    if (state.destroyed) return;
    // The shared renderer is a plain global; if the script tag is missing we
    // degrade to the skip affordance rather than trapping the learner.
    if (!window.DTErrorCard) {
      console.error('dual_translation: DTErrorCard global not loaded');
      renderUnavailable(
        T('session.dt_unavailable', null, 'Couldn’t load a translation passage right now.')
      );
      return;
    }
    state.card = window.DTErrorCard.mount(body(), card, {
      onDone: () => {
        if (state.destroyed) return;
        if (ctx.onComplete) ctx.onComplete({ card_id: card.card_id });
      },
    });
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
    state.l1Text = data.l1_text || '';
    state.ageTier = data.age_tier != null ? data.age_tier : null;
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
      <div class="alert alert-warning small" data-dt-submit-error hidden></div>
      <button class="btn btn-primary" type="button" data-dt-submit>${esc(
        T('session.dt_submit', null, 'Submit translation')
      )}</button>
      <button class="btn btn-link" type="button" data-dt-skip hidden>${esc(
        T('session.skip_for_now', null, 'Skip for now')
      )}</button>`;

    if (timer) timer.start();
    body().querySelector('[data-dt-submit]').onclick = submit;
  }

  async function submit() {
    // Re-entrancy latch: grading runs an LLM cascade, so a double-click would
    // burn a second run. (The route is idempotent per submission; the latch
    // avoids the round trip and keeps the UI honest.)
    if (state.submitting || state.destroyed) return;

    const input = body().querySelector('#dtInput');
    const reproduction = ((input && input.value) || '').trim();
    if (!reproduction) {
      if (input) input.focus();
      return;
    }
    gradeReproduction(reproduction);
  }

  // POST /submit and render the grade. Shared by the first submit and the
  // "Try again" after a provisional (unpersisted) grade: the server persists
  // nothing until a grade has scores, so re-posting the same text re-grades.
  async function gradeReproduction(reproduction) {
    if (state.submitting || state.destroyed) return;
    state.submitting = true;
    state.reproduction = reproduction;
    const button = body().querySelector('[data-dt-submit], [data-dt-retry]');
    if (button) {
      button.disabled = true;
      button.textContent = T('dual_translation.submitting', null, 'Grading…');
    }

    // Active time is measured once, on the first attempt, and its event id is
    // reused on retry so the server credits it at most once.
    if (timer && state.activeMs === null) {
      state.activeMs = timer.stop();
      state.eventId = window.ActiveTimer.newEventId();
    }
    const payload = { reproduction };
    if (state.primedToken) payload.primed_token = state.primedToken;
    if (state.activeMs !== null) {
      payload.active_ms = state.activeMs;
      payload.client_event_id = state.eventId;
    }

    let grade = null;
    let status = null;
    try {
      const res = await window.authFetch(
        `/api/dual-translation/${encodeURIComponent(state.submissionId)}/submit`,
        { method: 'POST', body: JSON.stringify(payload) }
      );
      status = res.status;
      const resBody = await res.json().catch(() => ({}));
      grade = resBody.data || resBody;
      if (!res.ok) throw new Error(`submit failed (${res.status})`);
    } catch (e) {
      console.error('dual_translation: submit failed', e);
      state.submitting = false;
      if (state.destroyed) return;
      // Keep the learner's text on screen: nothing was saved, so advancing
      // here would silently throw their translation away.
      showSubmitError(status, grade && grade.error);
      return;
    }
    if (state.destroyed) return;
    state.submitting = false;
    renderResult(grade);
  }

  function showSubmitError(status, message) {
    const box = body().querySelector('[data-dt-submit-error]');
    const button = body().querySelector('[data-dt-submit], [data-dt-retry]');
    const skip = body().querySelector('[data-dt-skip]');
    const base = T('dual_translation.error_submit', null, "Couldn't grade your translation.");
    if (box) {
      box.textContent = base + (status ? ` (${status}${message ? `: ${message}` : ''})` : '');
      box.hidden = false;
    } else if (typeof window.showToast === 'function') {
      window.showToast(base, 'error');
    }
    if (button) {
      button.disabled = false;
      button.textContent = T('session.dt_retry', null, 'Try again');
    }
    if (skip) {
      skip.hidden = false;
      skip.onclick = finish;
    }
  }

  function renderResult(grade) {
    if (state.destroyed) return;
    const band = grade && grade.overall_band != null ? grade.overall_band : null;

    // Both grading passes failed: the server returned a provisional contract
    // with no band and persisted nothing. Offer a re-grade of the same text.
    if (band == null) {
      body().innerHTML = `
        <div class="text-center">
          <h2 class="h5 mb-2">${esc(T('session.dt_heading', null, 'Dual Translation'))}</h2>
          <div class="alert alert-warning small" data-dt-submit-error>${esc(
            T(
              'session.dt_grading_incomplete',
              null,
              'Grading didn’t finish, so nothing was saved. Try again to get your grade.'
            )
          )}</div>
          <button class="btn btn-primary me-2" type="button" data-dt-retry>${esc(
            T('session.dt_retry', null, 'Try again')
          )}</button>
          <button class="btn btn-link" type="button" data-dt-skip>${esc(
            T('session.skip_for_now', null, 'Skip for now')
          )}</button>
        </div>`;
      body().querySelector('[data-dt-retry]').onclick = () => gradeReproduction(state.reproduction);
      body().querySelector('[data-dt-skip]').onclick = finish;
      return;
    }

    body().innerHTML = `
      <div class="text-center">
        <h2 class="h5 mb-2">${esc(T('session.dt_graded', null, 'Translation graded'))}</h2>
        ${
          grade.provisional
            ? `<div class="alert alert-warning small">${esc(
                T(
                  'dual_translation.grading_incomplete',
                  null,
                  'Grading didn’t finish — submit again to get full feedback.'
                )
              )}</div>`
            : ''
        }
        <p class="display-6 mb-0">${esc(String(band))}<span class="fs-5 text-muted">/4</span></p>
        <p class="small text-muted mb-3">${esc(T('dual_translation.overall_band', null, 'Overall band'))}</p>
        ${renderTargetWords(grade.target_words)}
        <a class="btn btn-outline-secondary me-2" href="/dual-translation" target="_blank" rel="opener" data-dt-details>${esc(
          T('session.dt_see_details', null, 'See full feedback')
        )}</a>
        <button class="btn btn-primary" type="button" data-dt-continue>${esc(
          T('session.continue', null, 'Continue')
        )}</button>
      </div>`;
    // The standalone page renders this exact grade (diff, errors, dimensions)
    // instead of pulling a new passage. localStorage, not sessionStorage: the
    // link opens a new tab so the session keeps its place.
    body().querySelector('[data-dt-details]').onclick = () => stashFeedback(grade);
    body().querySelector('[data-dt-continue]').onclick = finish;
  }

  function stashFeedback(grade) {
    try {
      window.localStorage.setItem(
        'dt_feedback_view',
        JSON.stringify({
          at: Date.now(),
          submission_id: state.submissionId,
          l1_text: state.l1Text,
          age_tier: state.ageTier,
          reproduction: state.reproduction,
          contract: grade,
        })
      );
    } catch {
      /* storage blocked: the page falls back to a new passage */
    }
  }

  // Produce: one row per primed word (produced / different form / omitted).
  function renderTargetWords(rows) {
    if (!Array.isArray(rows) || !rows.length) return '';
    const label = (st) =>
      st === 'produced'
        ? T('prestudy.produce_produced', null, 'Produced')
        : st === 'variant'
          ? T('prestudy.produce_variant', null, 'Different form')
          : T('prestudy.produce_omitted', null, 'Missing: back tomorrow');
    const cls = (st) =>
      st === 'produced'
        ? 'text-bg-success'
        : st === 'variant'
          ? 'text-bg-warning'
          : 'text-bg-danger';
    return `<div class="text-start mb-3"><div class="small text-muted mb-1">${esc(
      T('prestudy.produce_words', null, 'Your primed words')
    )}</div><ul class="list-unstyled mb-0">${rows
      .map(
        (r) =>
          `<li class="d-flex justify-content-between gap-2 py-1 border-bottom"><span>${esc(r.lemma || '')}</span><span class="badge ${cls(r.status)}">${esc(label(r.status))}</span></li>`
      )
      .join('')}</ul></div>`;
  }

  function finish() {
    if (state.destroyed) return;
    if (ctx.onComplete) ctx.onComplete({ submission_id: state.submissionId });
  }
}
