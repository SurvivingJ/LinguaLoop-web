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

// GET /next for the session's study language (the server falls back to the
// language of the learner's latest test when none is given).
// `reserve`: TASK-989 - translate an earlier (already graded) passage again.
export function nextUrl(languageId, reserve = false) {
  const id = parseInt(languageId, 10);
  const params = [];
  if (id > 0) params.push(`language_id=${encodeURIComponent(id)}`);
  if (reserve) params.push('reserve=1');
  return `/api/dual-translation/next${params.length ? `?${params.join('&')}` : ''}`;
}

// The line shown above the reference for a passage from a test not taken yet,
// or one translated before (re-served; kept out of the error profile).
export function passageNote(data) {
  const r = data && data.repeat_of;
  if (r) {
    const when = r.graded_at ? new Date(r.graded_at) : null;
    if (when && !isNaN(when.getTime()) && r.band != null) {
      const date = when.toLocaleDateString();
      return T(
        'dual_translation.repeat_note',
        { date, band: r.band },
        'You translated this passage on {date} (band {band}). This try doesn’t count towards your error profile.'
      );
    }
    return T(
      'dual_translation.repeat_note_nodate',
      null,
      'You’ve translated this passage before. This try doesn’t count towards your error profile.'
    );
  }
  if (data && data.from_untaken_test) {
    return T(
      'dual_translation.untaken_note',
      null,
      'This passage is from a test you haven’t taken yet, so you’ll see part of that test’s text.'
    );
  }
  return '';
}

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

  // Redesign 2026-11 (session-frame.md): a scrolling stage and a pinned dock.
  // Every action (Submit, Try again, Continue, Skip) lives in the dock.
  container.innerHTML = `
    <div class="ld-screen dt-player">
      <div class="ld-stage dt-player__stage" data-dt-stage>
        <div id="dtBody" class="dt-player__body">
          <div class="dt-player__spin"><div class="spinner-border" role="status" aria-hidden="true"></div></div>
        </div>
      </div>
      <div class="ld-dock dt-player__dock" data-dt-dock hidden></div>
    </div>`;

  const body = () => container.querySelector('#dtBody');
  const dock = () => container.querySelector('[data-dt-dock]');
  const stage = () => container.querySelector('[data-dt-stage]');
  const $ = (sel) => container.querySelector(sel);

  // Fill the stage and the dock in one go; an empty dock is hidden.
  function paint(stageHtml, dockHtml) {
    body().innerHTML = stageHtml;
    const d = dock();
    if (d) {
      d.innerHTML = dockHtml || '';
      d.hidden = !dockHtml;
    }
    const st = stage();
    if (st) st.scrollTop = 0;
  }

  load();

  return {
    destroy() {
      state.destroyed = true;
      if (state.sheet) state.sheet.dispose();
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

  async function load(reserve = false) {
    const produce = reserve ? null : await loadProduce();
    if (state.destroyed) return;
    if (produce) {
      state.submissionId = produce.submission_id;
      state.primedToken = produce.primed_token || null;
      renderPassage(produce);
      return;
    }
    let data;
    try {
      const res = await window.authFetch(nextUrl(ctx.languageId, reserve));
      const payload = await res.json();
      data = payload.data || payload;
      if (res.status === 404 && data && data.error_code === 'ALL_DONE') {
        renderUnavailable(
          T(
            'dual_translation.all_done_any',
            null,
            'You’ve translated every passage that has a reviewed translation in this language. You can translate an earlier one again, or come back when new passages are added.'
          ),
          { reserve: !reserve }
        );
        return;
      }
      if (res.status === 404 && data && data.error_code === 'NO_PASSAGES') {
        renderUnavailable(
          T(
            'dual_translation.none_available',
            null,
            'No passage in this language has a reviewed translation into your language yet. Take a test in the meantime, and check back later.'
          )
        );
        return;
      }
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
    if (dock()) dock().hidden = false;
    state.card = window.DTErrorCard.mount(body(), card, {
      dock: dock() || undefined,
      onDone: () => {
        if (state.destroyed) return;
        if (ctx.onComplete) ctx.onComplete({ card_id: card.card_id });
      },
    });
  }

  function renderUnavailable(message, opts = {}) {
    if (state.destroyed) return;
    paint(
      `<div class="dt-player__msg">
        <h2 class="ld-h2">${esc(T('session.dt_heading', null, 'Dual Translation'))}</h2>
        <p class="ld-muted">${esc(message)}</p>
      </div>`,
      `${
        opts.reserve
          ? `<button class="ld-btn" type="button" data-dt-reserve>${esc(
              T('dual_translation.reserve_action', null, 'Translate an earlier passage again')
            )}</button>`
          : ''
      }<a class="ld-btn ld-btn--ghost" href="/dual-translation">${esc(
        T('session.open_page', null, 'Open page')
      )}</a>
      <button class="ld-link ld-link--quiet" type="button" data-dt-skip>${esc(
        T('session.skip_for_now', null, 'Skip for now')
      )}</button>`
    );
    const skip = $('[data-dt-skip]');
    if (skip) skip.onclick = () => ctx.onSkip && ctx.onSkip();
    const again = $('[data-dt-reserve]');
    if (again) {
      again.onclick = () => {
        paint(
          '<div class="dt-player__spin"><div class="spinner-border" role="status" aria-hidden="true"></div></div>',
          ''
        );
        load(true);
      };
    }
  }

  function renderPassage(data) {
    if (state.destroyed) return;
    state.l1Text = data.l1_text || '';
    state.ageTier = data.age_tier != null ? data.age_tier : null;
    // The runner sets the study language on its stage (#sessionStage[lang]).
    const l2 = (container.getAttribute && container.getAttribute('lang')) || '';
    const note = passageNote(data);
    paint(
      `${note ? `<p class="ld-note dt-passage-note" data-dt-note>${esc(note)}</p>` : ''}<p class="ld-muted ld-small dt-player__instr">${esc(
        T(
          'session.dt_instructions',
          null,
          'Reproduce this passage in the language you’re studying.'
        )
      )}</p>
      <div class="ld-card dt-player__ref">
        <p class="ld-eyebrow">${esc(
          T('dual_translation.reference_label', null, 'Reference (in your language)')
        )}</p>
        <p class="dt-player__l1">${esc(data.l1_text || '')}</p>
      </div>
      <label class="visually-hidden" for="dtInput">${esc(
        T('session.dt_input_label', null, 'Your translation')
      )}</label>
      <textarea id="dtInput" class="dt-player__input" rows="4"${l2 ? ` lang="${esc(l2)}"` : ''} placeholder="${esc(
        T('dual_translation.reproduction_placeholder', null, 'Type your translation here…')
      )}"></textarea>
      <div class="ld-note ld-note--warn" data-dt-submit-error role="alert" hidden></div>`,
      `<button class="ld-btn" type="button" data-dt-submit>${esc(
        T('session.dt_submit', null, 'Submit translation')
      )}</button>
      ${
        data.source
          ? `<button class="ld-link ld-link--quiet dt-skip" type="button" data-dt-skip-passage>${esc(
              T('dual_translation.skip_passage', null, 'Skip this passage')
            )}</button>`
          : ''
      }
      <button class="ld-link ld-link--quiet" type="button" data-dt-skip hidden>${esc(
        T('session.skip_for_now', null, 'Skip for now')
      )}</button>`
    );

    if (timer) timer.start();
    $('[data-dt-submit]').onclick = submit;
    // GET /next resumes this passage until it is translated or skipped; the
    // skipped one comes back after everything not seen yet.
    const skipPassage = $('[data-dt-skip-passage]');
    if (skipPassage) {
      skipPassage.onclick = async () => {
        if (state.submitting || state.destroyed || !state.submissionId) return;
        skipPassage.disabled = true;
        try {
          const res = await window.authFetch(
            `/api/dual-translation/${encodeURIComponent(state.submissionId)}/skip`,
            { method: 'POST' }
          );
          if (!res.ok && res.status !== 409) throw new Error(`skip ${res.status}`);
        } catch {
          skipPassage.disabled = false;
          return;
        }
        if (state.destroyed) return;
        paint(
          '<div class="dt-player__spin"><div class="spinner-border" role="status" aria-hidden="true"></div></div>',
          ''
        );
        load(false);
      };
    }
  }

  async function submit() {
    // Re-entrancy latch: grading runs an LLM cascade, so a double-click would
    // burn a second run. (The route is idempotent per submission; the latch
    // avoids the round trip and keeps the UI honest.)
    if (state.submitting || state.destroyed) return;

    const input = $('#dtInput');
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
    const button = $('[data-dt-submit], [data-dt-retry]');
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
      if (grade && grade.error_code === 'GRADING_UNAVAILABLE') {
        showGradingUnavailable();
        return;
      }
      showSubmitError(status, grade && grade.error);
      return;
    }
    if (state.destroyed) return;
    state.submitting = false;
    handleGrade(grade);
  }

  // Guided self-repair (wiki/features/dt-guided-self-repair.tech.md §8.7). The client reacts to the
  // response, not to a flag: no `repair` key (flag off, ineligible grade, hook error) or a bypassed
  // pass is today's band screen exactly. A clean or open session opens the pop-up first.
  function handleGrade(grade) {
    const repair = grade && grade.repair;
    if (!repair || repair.status === 'bypassed') return renderResult(grade);
    if (repair.clean) return openRepair(repair, () => renderResult(grade));
    if (repair.status === 'open') return openRepair(repair, () => showServerResult(repair));
    // finished / abandoned (a cached re-submit): the full contract came with it
    return grade.redacted ? showServerResult(repair) : renderResult(grade);
  }

  function openRepair(repair, after) {
    if (!window.DTRepairSheet) {
      console.error('dual_translation: DTRepairSheet global not loaded');
      return after();
    }
    state.sheet = window.DTRepairSheet.open({
      mode: 'pass',
      session: repair,
      fetch: window.authFetch,
      returnFocus: dock() || body(),
      onDone: () => {
        state.sheet = null;
        if (!state.destroyed) after();
      },
    });
    return undefined;
  }

  // The full contract is only served once the session is finished. One retry after 1 s; a 409
  // (the finish call did not land) triggers one more finish. The redacted contract is never
  // rendered or stashed.
  async function fetchFullResult(repair) {
    const url = `/api/dual-translation/repair/submissions/${encodeURIComponent(repair.submission_id)}/result`;
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await window.authFetch(url);
        const data = await res.json().catch(() => ({}));
        const contract = data.data && !('status' in data) ? data.data : data;
        if (res.ok && contract && !contract.redacted) return contract;
        if (res.status === 409 && repair.session_id != null) {
          await window
            .authFetch(
              `/api/dual-translation/repair/sessions/${encodeURIComponent(repair.session_id)}/finish`,
              { method: 'POST', body: JSON.stringify({ closed_early: true }) }
            )
            .catch(() => null);
        }
      } catch (e) {
        console.warn('dual_translation: result fetch failed', e);
      }
      if (attempt === 0) await new Promise((r) => setTimeout(r, 1000));
    }
    return null;
  }

  async function showServerResult(repair) {
    if (state.destroyed) return;
    paint(
      '<div class="dt-player__spin"><div class="spinner-border" role="status" aria-hidden="true"></div></div>',
      ''
    );
    const full = await fetchFullResult(repair);
    if (state.destroyed) return;
    if (full) return renderResult(full);
    paint(
      `<div class="dt-player__msg">
        <div class="ld-note ld-note--warn" role="alert">${esc(
          T('dt_repair.result_load_failed', null, 'Couldn’t load your full feedback.')
        )}</div>
      </div>`,
      `<button class="ld-btn" type="button" data-dt-result-retry>${esc(
        T('dt_repair.retry', null, 'Try again')
      )}</button>
      <button class="ld-link ld-link--quiet" type="button" data-dt-continue>${esc(
        T('session.continue', null, 'Continue')
      )}</button>`
    );
    $('[data-dt-result-retry]').onclick = () => showServerResult(repair);
    $('[data-dt-continue]').onclick = finish;
    return undefined;
  }

  // No model could grade the translation (provider refused or failed). Nothing
  // was graded or saved, so the same text can be submitted again: offer "Try
  // again" (the learner's text stays in the box) next to "Skip for now".
  function showGradingUnavailable() {
    const box = $('[data-dt-submit-error]');
    const button = $('[data-dt-submit], [data-dt-retry]');
    const skip = $('[data-dt-skip]');
    const message = T(
      'dual_translation.grading_unavailable',
      null,
      'Grading didn’t work this time, so your translation wasn’t graded or saved. Please try again.'
    );
    if (box) {
      box.textContent = message;
      box.hidden = false;
      box.dataset.dtUnavailable = '';
    } else if (typeof window.showToast === 'function') {
      window.showToast(message, 'error');
    }
    if (button) {
      button.hidden = false;
      button.disabled = false;
      button.textContent = T('session.dt_retry', null, 'Try again');
    }
    if (skip) {
      skip.hidden = false;
      skip.onclick = () => ctx.onSkip && ctx.onSkip();
    }
  }

  function showSubmitError(status, message) {
    const box = $('[data-dt-submit-error]');
    const button = $('[data-dt-submit], [data-dt-retry]');
    const skip = $('[data-dt-skip]');
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
      paint(
        `<div class="dt-player__msg">
          <h2 class="ld-h2">${esc(T('session.dt_heading', null, 'Dual Translation'))}</h2>
          <div class="ld-note ld-note--warn" data-dt-submit-error role="alert">${esc(
            T(
              'session.dt_grading_incomplete',
              null,
              'Grading didn’t finish, so nothing was saved. Try again to get your grade.'
            )
          )}</div>
        </div>`,
        `<button class="ld-btn" type="button" data-dt-retry>${esc(
          T('session.dt_retry', null, 'Try again')
        )}</button>
        <button class="ld-link ld-link--quiet" type="button" data-dt-skip>${esc(
          T('session.skip_for_now', null, 'Skip for now')
        )}</button>`
      );
      $('[data-dt-retry]').onclick = () => gradeReproduction(state.reproduction);
      $('[data-dt-skip]').onclick = finish;
      return;
    }

    const bandClass = band >= 1 && band <= 4 ? ` b${Math.round(band)}` : '';
    paint(
      `<div class="dt-player__graded">
        <h2 class="ld-h2">${esc(T('session.dt_graded', null, 'Translation graded'))}</h2>
        ${
          grade.provisional
            ? `<div class="ld-note ld-note--warn">${esc(
                T(
                  'dual_translation.grading_incomplete',
                  null,
                  'Grading didn’t finish — submit again to get full feedback.'
                )
              )}</div>`
            : ''
        }
        <div class="dt-player__score${bandClass}"><span class="dt-player__n">${esc(String(band))}</span><span class="dt-player__of">/4</span></div>
        <p class="ld-eyebrow">${esc(T('dual_translation.overall_band', null, 'Overall band'))}</p>
        ${renderTargetWords(grade.target_words)}
      </div>`,
      `<button class="ld-btn" type="button" data-dt-continue>${esc(
        T('session.continue', null, 'Continue')
      )}</button>
      <a class="ld-btn ld-btn--ghost" href="/dual-translation" target="_blank" rel="opener" data-dt-details>${esc(
        T('session.dt_see_details', null, 'See full feedback')
      )}</a>`
    );
    // The standalone page renders this exact grade (diff, errors, dimensions)
    // instead of pulling a new passage. localStorage, not sessionStorage: the
    // link opens a new tab so the session keeps its place.
    $('[data-dt-details]').onclick = () => stashFeedback(grade);
    $('[data-dt-continue]').onclick = finish;
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
      st === 'produced' ? 'ld-tag--ok' : st === 'variant' ? 'ld-tag--warn' : 'ld-tag--bad';
    return `<div class="dt-player__words"><p class="ld-eyebrow">${esc(
      T('prestudy.produce_words', null, 'Your primed words')
    )}</p><ul class="ld-card dt-player__wordlist">${rows
      .map(
        (r) =>
          `<li><span class="ld-tl">${esc(r.lemma || '')}</span><span class="ld-tag ${cls(r.status)}">${esc(label(r.status))}</span></li>`
      )
      .join('')}</ul></div>`;
  }

  function finish() {
    if (state.destroyed) return;
    if (ctx.onComplete) ctx.onComplete({ submission_id: state.submissionId });
  }
}
