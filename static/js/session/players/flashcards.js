// static/js/session/players/flashcards.js
// Flashcards player for the daily-session runner (TASK-714 / ADR-021).
//
// FSRS reviews are due-driven and inherently daily, which made them the single
// largest source of study time the weekly plan could not see. One queue item is
// one review BLOCK of ctx.item.cards cards (15 by default, mirroring
// routes/study_session.py::_FLASHCARD_CARDS_PER_BLOCK and the 7.0-minute seed
// in test_time_estimate).
//
// Reuses the existing standalone endpoints unchanged:
//   GET  /api/flashcards/due?language_id=L   -> { cards: [...], total }
//   POST /api/flashcards/review              -> { next_due, new_state, ... }
// The block's own completion is persisted by the controller via
// POST /api/study-session/complete-block, which is also what credits the
// weekly counter (record_session_progress p_kind='surface').

const T = (key, params, fallback) =>
  window.LinguaI18n && typeof LinguaI18n.t === 'function'
    ? LinguaI18n.t(key, params) || fallback || key
    : fallback || key;

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : s;
  return d.innerHTML;
}

// FSRS ratings, matching routes/flashcards.py (1=again .. 4=easy).
const RATINGS = [
  { value: 1, key: 'session.fc_again', fallback: 'Again', cls: 'btn-outline-danger' },
  { value: 2, key: 'session.fc_hard', fallback: 'Hard', cls: 'btn-outline-warning' },
  { value: 3, key: 'session.fc_good', fallback: 'Good', cls: 'btn-outline-success' },
  { value: 4, key: 'session.fc_easy', fallback: 'Easy', cls: 'btn-outline-primary' },
];

export function mount(container, ctx) {
  const limit = (ctx.item && ctx.item.cards) || 15;
  const state = { cards: [], index: 0, revealed: false, reviewed: 0, destroyed: false };

  container.innerHTML = `
    <div class="session-card"><div class="card"><div class="card-body p-4">
      <div id="fcBody" class="text-center">
        <div class="spinner-border" role="status" aria-hidden="true"></div>
      </div>
    </div></div></div>`;

  const body = () => container.querySelector('#fcBody');

  load();

  return {
    destroy() {
      state.destroyed = true;
    },
  };

  async function load() {
    try {
      const res = await window.authFetch(
        `/api/flashcards/due?language_id=${encodeURIComponent(ctx.languageId)}`
      );
      const payload = await res.json();
      const data = payload.data || payload;
      if (!res.ok) throw new Error(`due fetch failed (${res.status})`);
      state.cards = (data.cards || []).slice(0, limit);
    } catch (e) {
      // Fail forward: the learner should never be stuck on a block we could
      // not populate. Offer the standalone page and let them skip.
      console.error('flashcards: failed to load due cards', e);
      renderUnavailable();
      return;
    }
    if (state.destroyed) return;

    if (state.cards.length === 0) {
      // The resolver clamps the budget to what is due, so this normally means
      // the deck emptied between solve and play (e.g. reviewed on the
      // standalone page). Nothing to do — count the block done and move on.
      finish();
      return;
    }
    renderCard();
  }

  function renderUnavailable() {
    if (state.destroyed) return;
    body().innerHTML = `
      <h2 class="h5 mb-2">${esc(T('session.flashcards_heading', null, 'Flashcards'))}</h2>
      <p class="text-muted">${esc(
        T('session.flashcards_unavailable', null, 'Couldn’t load your review cards right now.')
      )}</p>
      <a class="btn btn-outline-primary me-2" href="/flashcards/page">${esc(
        T('session.open_page', null, 'Open page')
      )}</a>
      <button class="btn btn-secondary" type="button" data-fc-skip>${esc(
        T('session.skip_for_now', null, 'Skip for now')
      )}</button>`;
    const skip = body().querySelector('[data-fc-skip]');
    if (skip) skip.onclick = () => ctx.onSkip && ctx.onSkip();
  }

  function renderCard() {
    if (state.destroyed) return;
    const card = state.cards[state.index];
    state.revealed = false;

    body().innerHTML = `
      <p class="text-muted small mb-2">${esc(
        T(
          'session.flashcards_progress',
          { current: state.index + 1, total: state.cards.length },
          `Card ${state.index + 1} of ${state.cards.length}`
        )
      )}</p>
      <h2 class="display-6 mb-3">${esc(card.lemma)}</h2>
      <div id="fcBack" class="d-none">
        <p class="text-muted mb-1">${esc(card.pronunciation || '')}</p>
        <p class="lead mb-2">${esc(card.definition || '')}</p>
        <p class="fst-italic text-muted">${esc(card.example_sentence || '')}</p>
      </div>
      <div id="fcActions" class="mt-3">
        <button class="btn btn-primary" type="button" data-fc-reveal>${esc(
          T('session.flashcards_reveal', null, 'Show answer')
        )}</button>
      </div>`;

    body().querySelector('[data-fc-reveal]').onclick = reveal;
  }

  function reveal() {
    if (state.destroyed || state.revealed) return;
    state.revealed = true;
    body().querySelector('#fcBack').classList.remove('d-none');
    const actions = body().querySelector('#fcActions');
    actions.innerHTML = RATINGS.map(
      (r) =>
        `<button class="btn ${r.cls} me-1 mb-1" type="button" data-fc-rating="${r.value}">${esc(
          T(r.key, null, r.fallback)
        )}</button>`
    ).join('');
    actions.querySelectorAll('[data-fc-rating]').forEach((btn) => {
      btn.onclick = () => rate(parseInt(btn.dataset.fcRating, 10), actions);
    });
  }

  async function rate(rating, actions) {
    // Latch the buttons: a double-click would post two reviews and advance the
    // FSRS schedule twice.
    actions.querySelectorAll('button').forEach((b) => {
      b.disabled = true;
    });
    const card = state.cards[state.index];
    try {
      const res = await window.authFetch('/api/flashcards/review', {
        method: 'POST',
        body: JSON.stringify({ card_id: card.card_id, rating }),
      });
      if (!res || !res.ok) throw new Error(`review failed (${res && res.status})`);
      state.reviewed += 1;
    } catch (e) {
      // Surface but keep going — the block is about doing the reviews, and a
      // lost schedule update self-heals on the next due pass.
      console.error('flashcards: review POST failed', e);
      if (typeof window.showToast === 'function') {
        window.showToast(
          T('session.save_failed', null, 'Couldn’t save your progress — check your connection.')
        );
      }
    }
    if (state.destroyed) return;
    state.index += 1;
    if (state.index >= state.cards.length) {
      finish();
      return;
    }
    renderCard();
  }

  function finish() {
    if (state.destroyed) return;
    if (ctx.onComplete) ctx.onComplete({ reviewed: state.reviewed });
  }
}
