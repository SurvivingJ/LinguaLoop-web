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

import { T, escapeHtml as esc, toastSaveFailed } from '../dom.js';
import { createSaveQueue } from '../save_queue.js';
import { prefetchJson, takePrefetch } from '../prefetch.js';

const dueUrl = (languageId) => `/api/flashcards/due?language_id=${encodeURIComponent(languageId)}`;

/**
 * Session prefetch hook: the due list, unless a flashcards block is running
 * (its reviews change what is due).
 */
export function prefetch(item, ctx) {
  const current = ctx && ctx.current;
  if (current && current.kind === 'flashcards') return null;
  return prefetchJson(dueUrl(ctx && ctx.languageId));
}

// FSRS ratings, matching routes/flashcards.py (1=again .. 4=easy).
// Active-time helper (static/js/active-timer.js, loaded by study_session.html).
// Optional: without it the review POST simply omits active_ms/client_event_id.
function newTimer() {
  return window.ActiveTimer && typeof window.ActiveTimer.create === 'function'
    ? window.ActiveTimer.create()
    : null;
}

const RATINGS = [
  {
    value: 1,
    key: 'session.fc_again',
    fallback: 'Again',
    cls: 'fc-r1',
    hint: ['flashcards.fail_hint', '< 1 min'],
  },
  {
    value: 2,
    key: 'session.fc_hard',
    fallback: 'Hard',
    cls: 'fc-r2',
    hint: ['flashcards.hard_hint', '~10 min'],
  },
  {
    value: 3,
    key: 'session.fc_good',
    fallback: 'Good',
    cls: 'fc-r3',
    hint: ['flashcards.good_hint', '~1 day'],
  },
  {
    value: 4,
    key: 'session.fc_easy',
    fallback: 'Easy',
    cls: 'fc-r4',
    hint: ['flashcards.easy_hint', '~4 days'],
  },
];

export function mount(container, ctx) {
  const limit = (ctx.item && ctx.item.cards) || 15;
  const state = { cards: [], index: 0, revealed: false, reviewed: 0, destroyed: false };
  const timer = newTimer();
  // One id per card showing, reused if the same review is ever re-sent.
  let eventId = null;
  // Reviews are saved in the background (in order, with retries) so the next
  // card shows at once; finish() waits for them before completing the block.
  const reviews = createSaveQueue({
    onFail: () => {
      // Surface but keep going — the block is about doing the reviews, and a
      // lost schedule update self-heals on the next due pass.
      console.error('flashcards: review POST failed');
      toastSaveFailed();
    },
  });

  // Redesign 2026-11 (session-frame.md): progress + card in a scrolling stage,
  // Show answer / the four ratings pinned in the dock.
  container.innerHTML = `
    <div class="ld-screen fc-player">
      <div class="ld-stage fc-player__stage">
        <div id="fcBody" class="fc-player__body">
          <div class="fc-player__spin"><div class="spinner-border" role="status" aria-hidden="true"></div></div>
        </div>
      </div>
      <div class="ld-dock fc-player__dock" id="fcActions" hidden></div>
    </div>`;

  const body = () => container.querySelector('#fcBody');
  const actionsEl = () => container.querySelector('#fcActions');
  const setDock = (html) => {
    const a = actionsEl();
    a.innerHTML = html || '';
    a.hidden = !html;
  };

  load();

  return {
    destroy() {
      state.destroyed = true;
      if (timer) timer.reset();
      reviews.hurry();
    },
  };

  async function load() {
    try {
      const pre = await takePrefetch(ctx.item);
      let payload = pre && pre.data;
      if (!pre) {
        const res = await window.authFetch(dueUrl(ctx.languageId));
        payload = await res.json();
        if (!res.ok) throw new Error(`due fetch failed (${res.status})`);
      }
      const data = payload.data || payload;
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
      <div class="fc-player__msg">
        <h2 class="ld-h2">${esc(T('session.flashcards_heading', null, 'Flashcards'))}</h2>
        <p class="ld-muted">${esc(
          T('session.flashcards_unavailable', null, 'Couldn’t load your review cards right now.')
        )}</p>
      </div>`;
    setDock(`<a class="ld-btn ld-btn--ghost" href="/flashcards/page">${esc(
      T('session.open_page', null, 'Open page')
    )}</a>
      <button class="ld-link ld-link--quiet" type="button" data-fc-skip>${esc(
        T('session.skip_for_now', null, 'Skip for now')
      )}</button>`);
    const skip = container.querySelector('[data-fc-skip]');
    if (skip) skip.onclick = () => ctx.onSkip && ctx.onSkip();
  }

  function renderCard() {
    if (state.destroyed) return;
    const card = state.cards[state.index];
    state.revealed = false;
    eventId = window.ActiveTimer ? window.ActiveTimer.newEventId() : null;
    if (timer) timer.start();

    const progress = T(
      'session.flashcards_progress',
      { current: state.index + 1, total: state.cards.length },
      `Card ${state.index + 1} of ${state.cards.length}`
    );
    // The runner header carries "Card n of N" when there is a frame; the
    // in-stage line is only for hosts without one (no duplicate on /session).
    const framed = !!(ctx.frame && typeof ctx.frame.setHeader === 'function');
    if (framed) ctx.frame.setHeader({ subtitle: progress });
    const pct = Math.round((state.index / state.cards.length) * 100);
    body().innerHTML = `
      <p class="ld-eyebrow fc-player__prog"${framed ? ' hidden' : ''}>${esc(progress)}</p>
      <div class="ld-bar" role="presentation"><i style="width:${pct}%"></i></div>
      <div class="fc-player__card ld-fill" data-fc-card>
        <h2 class="fc-player__word ld-tl">${esc(card.lemma)}</h2>
        <p class="fc-player__pron ld-muted">${esc(card.pronunciation || '')}</p>
        <div id="fcBack" class="fc-player__back d-none">
          <p class="fc-player__def">${esc(card.definition || '')}</p>
          <p class="fc-player__ex ld-tl ld-muted">${esc(card.example_sentence || '')}</p>
        </div>
      </div>`;
    setDock(
      `<button class="ld-btn" type="button" data-fc-reveal>${esc(
        T('session.flashcards_reveal', null, 'Show answer')
      )}</button>`
    );

    container.querySelector('[data-fc-reveal]').onclick = reveal;
    // Tapping the card also reveals it (the mockup's flip).
    const cardEl = body().querySelector('[data-fc-card]');
    if (cardEl) cardEl.onclick = reveal;
    const st = container.querySelector('.fc-player__stage');
    if (st) st.scrollTop = 0;
  }

  function reveal() {
    if (state.destroyed || state.revealed) return;
    state.revealed = true;
    body().querySelector('#fcBack').classList.remove('d-none');
    const cardEl = body().querySelector('[data-fc-card]');
    if (cardEl) cardEl.classList.add('is-revealed');
    const actions = actionsEl();
    actions.innerHTML = `<div class="fc-rate">${RATINGS.map(
      (r) =>
        `<button class="fc-rate__btn ${r.cls}" type="button" data-fc-rating="${r.value}">${esc(
          T(r.key, null, r.fallback)
        )}<small>${esc(T(r.hint[0], null, r.hint[1]))}</small></button>`
    ).join('')}</div>`;
    actions.hidden = false;
    actions.querySelectorAll('[data-fc-rating]').forEach((btn) => {
      btn.onclick = () => rate(parseInt(btn.dataset.fcRating, 10), actions);
    });
  }

  function rate(rating, actions) {
    // Latch the buttons: a double-click would post two reviews and advance the
    // FSRS schedule twice.
    actions.querySelectorAll('button').forEach((b) => {
      b.disabled = true;
    });
    const card = state.cards[state.index];
    const payload = { card_id: card.card_id, rating };
    if (timer && eventId) {
      payload.active_ms = timer.stop();
      payload.client_event_id = eventId;
    }
    const body = JSON.stringify(payload);
    reviews
      .enqueue(async () => {
        const res = await window.authFetch('/api/flashcards/review', {
          method: 'POST',
          body,
          keepalive: true,
        });
        return !!(res && res.ok);
      }, card.card_id)
      .then((ok) => {
        if (ok) state.reviewed += 1;
      });
    state.index += 1;
    if (state.index >= state.cards.length) {
      finish();
      return;
    }
    renderCard();
  }

  async function finish() {
    if (state.destroyed) return;
    if (reviews.pending) {
      body().innerHTML =
        '<div class="fc-player__spin"><div class="spinner-border" role="status" aria-hidden="true"></div></div>';
      setDock('');
    }
    await reviews.settle();
    if (state.destroyed) return;
    if (ctx.onComplete) ctx.onComplete({ reviewed: state.reviewed });
  }
}
