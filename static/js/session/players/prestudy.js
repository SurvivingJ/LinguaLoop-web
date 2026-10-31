// static/js/session/players/prestudy.js
// Test prestudy block in the daily session (wiki/features/test-prestudy.md, Triggers).
//
// The server inserts a `kind: 'prestudy'` item before a new test over 25% unknown
// words (full), a new test between 5% and 25% (light, about a minute) and every
// retry slot, when the learner's setting is "auto". This card says what it costs
// and opens the prestudy page for that test; the page completes the block
// (POST /api/study-session/complete-block) and returns here, where the session
// resumes on the test itself. "Take it cold" completes the block and moves on:
// prestudy never blocks a test.

const T = (key, params, fallback) => {
  if (window.LinguaI18n && typeof LinguaI18n.t === 'function') {
    const v = LinguaI18n.t(key, params);
    if (v && v !== key) return v;
  }
  return fallback || key;
};

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : s;
  return d.innerHTML;
}

export function prestudyUrl(item, languageId) {
  const p = new URLSearchParams({
    type: item.test_type === 'listening' ? 'listening' : 'reading',
    trigger: item.trigger || 'auto',
    block: item.id,
    plan: item.plan_mode || 'full',
    return: 'session',
  });
  if (item.tests_dropped_today) p.set('dropped', String(item.tests_dropped_today));
  if (languageId) p.set('language_id', String(languageId));
  return `/test/${encodeURIComponent(item.slug)}/prestudy?${p.toString()}`;
}

export function mount(container, ctx) {
  const item = ctx.item || {};
  const pct = Math.round((Number(item.unknown_share) || 0) * 100);
  const light = item.plan_mode === 'light';
  const minutes = Number(item.minutes_est) || (light ? 1 : 4);
  const dropped = Number(item.tests_dropped_today) || 0;
  const why =
    item.trigger === 'retry'
      ? T('session.prestudy.why_retry', null, 'You are retrying this test. Study its key words first.')
      : light
        ? T('session.prestudy.why_light', { pct }, `${pct}% of this test's key words are new to you: a one-minute warm-up on three of them.`)
        : T('session.prestudy.why_full', { pct }, `${pct}% of this test's key words are new to you. Learn them first, then take the test.`);

  container.innerHTML = `
    <div class="session-card"><div class="card"><div class="card-body p-4">
      <div class="d-flex align-items-center gap-2 mb-2">
        <i class="bi bi-book-half text-primary" aria-hidden="true"></i>
        <h2 class="h5 mb-0">${esc(T('session.prestudy.title', null, 'Study first'))}</h2>
      </div>
      <p class="mb-1 fw-semibold">${esc(item.title || '')}</p>
      <p class="text-muted mb-3">${esc(why)}</p>
      <div class="d-flex flex-wrap gap-2 mb-3">
        <span class="badge rounded-pill text-bg-light border">${esc(T('session.prestudy.minutes', { n: minutes }, `About ${minutes} min`))}</span>
        <span class="badge rounded-pill text-bg-light border">${esc(T('session.prestudy.elo', null, 'Your first attempt then counts at half weight'))}</span>
        ${dropped ? `<span class="badge rounded-pill text-bg-warning">${esc(T('session.prestudy.dropped', { count: dropped }, dropped === 1 ? '1 fewer test today' : `${dropped} fewer tests today`))}</span>` : ''}
      </div>
      <div class="d-flex flex-wrap gap-2">
        <a class="btn btn-primary" data-prestudy-start href="${esc(prestudyUrl(item, ctx.languageId))}">
          <i class="bi bi-play-circle-fill me-1" aria-hidden="true"></i>${esc(T('session.prestudy.start', null, 'Start studying'))}
        </a>
        <button type="button" class="btn btn-outline-secondary" data-prestudy-cold>${esc(T('session.prestudy.cold', null, 'Take it cold'))}</button>
      </div>
    </div></div></div>`;

  const cold = container.querySelector('[data-prestudy-cold]');
  if (cold) cold.onclick = () => ctx.onComplete && ctx.onComplete({ skipped: true });

  return {
    destroy() {
      /* nothing to clean up */
    },
  };
}
