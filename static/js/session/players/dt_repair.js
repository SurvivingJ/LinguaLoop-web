// static/js/session/players/dt_repair.js
// Daily-session player for the "dt_repair" block (wiki/features/dt-guided-self-repair.tech.md §8.8).
//
// The block appears when the learner has sentences from earlier Dual Translation passages that
// were not fixed on their own. It fetches the due items and shows them in the same single-step
// pop-up the repair pass uses (window.DTRepairSheet, static/js/dt-repair-sheet.js, mode 'daily').
//   GET /api/dual-translation/repair/practice/due?language_id=L -> { items: Step[], total_due }
// Nothing due completes the block at once. Closing the sheet early skips the block (it stays in
// resume); finishing every item completes it.

import { T, escapeHtml as esc } from '../dom.js';

export function mount(container, ctx) {
  const state = { destroyed: false, sheet: null };

  container.innerHTML = `
    <div class="session-card"><div class="card"><div class="card-body p-4 text-center">
      <h2 class="h5 mb-3">${esc(T('session.dt_repair_heading', null, 'Fix your sentences'))}</h2>
      <div data-dtr-body><div class="spinner-border" role="status" aria-hidden="true"></div></div>
    </div></div></div>`;
  const body = () => container.querySelector('[data-dtr-body]');

  load();

  return {
    destroy() {
      state.destroyed = true;
      if (state.sheet && typeof state.sheet.dispose === 'function') state.sheet.dispose();
    },
  };

  async function load() {
    let items;
    try {
      const res = await window.authFetch(
        `/api/dual-translation/repair/practice/due?language_id=${encodeURIComponent(ctx.languageId)}`
      );
      const payload = await res.json();
      if (!res.ok) throw new Error(`due failed (${res.status})`);
      items = (payload.data || payload).items || [];
    } catch (e) {
      console.error('dt_repair: failed to fetch due items', e);
      renderUnavailable();
      return;
    }
    if (state.destroyed) return;
    if (!items.length) {
      if (ctx.onComplete) ctx.onComplete({ dt_repair: 0 });
      return;
    }
    if (!window.DTRepairSheet) {
      console.error('dt_repair: DTRepairSheet global not loaded');
      renderUnavailable();
      return;
    }
    const l2 = container.closest('[lang]') ? container.closest('[lang]').lang : '';
    body().innerHTML = '';
    state.sheet = window.DTRepairSheet.open({
      mode: 'daily',
      items,
      l2: container.lang || l2 || '',
      fetch: window.authFetch,
      returnFocus: container,
      onDone: (r) => {
        if (state.destroyed) return;
        if (r && r.closedEarly) {
          if (ctx.onSkip) ctx.onSkip();
        } else if (ctx.onComplete) {
          ctx.onComplete({ dt_repair: (r && r.completed) || items.length });
        }
      },
    });
  }

  function renderUnavailable() {
    if (state.destroyed) return;
    body().innerHTML = `
      <p class="text-muted">${esc(T('session.dt_unavailable', null, 'Couldn’t load a translation passage right now.'))}</p>
      <button class="btn btn-secondary" type="button" data-dtr-skip>${esc(
        T('session.skip_for_now', null, 'Skip for now')
      )}</button>`;
    const skip = body().querySelector('[data-dtr-skip]');
    if (skip) skip.onclick = () => ctx.onSkip && ctx.onSkip();
  }
}
