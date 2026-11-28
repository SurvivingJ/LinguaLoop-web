// static/js/session/players/prestudy.js
// Test prestudy block in the daily session (wiki/features/test-prestudy.md, Triggers).
//
// The server inserts a `kind: 'prestudy'` item before a new test over 25% unknown
// words (full), a new test between 5% and 25% (light: reading and meaning only) and every
// retry slot, when the learner's setting is "auto". This card says what it costs
// and opens the prestudy page for that test; the page completes the block
// (POST /api/study-session/complete-block) and returns here, where the session
// resumes on the test itself. "Take it cold" completes the block and moves on:
// prestudy never blocks a test.

import { T, escapeHtml as esc } from '../dom.js';

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
      ? T(
          'session.prestudy.why_retry',
          null,
          'You are retrying this test. Study its key words first.'
        )
      : light
        ? T(
            'session.prestudy.why_light',
            { pct },
            `${pct}% of this test's key words are new to you: a quick warm-up on the words you don't know yet.`
          )
        : T(
            'session.prestudy.why_full',
            { pct },
            `${pct}% of this test's key words are new to you. Learn them first, then take the test.`
          );

  const lang = window.LinguaLanguages.codeOf(Number(ctx.languageId));
  // The runner's header names the test type and title (seal 学); the eyebrow
  // says what this card is, and the stage keeps the test title so it reads on its own.
  // One task screen: the explanation in the stage, both choices in the dock.
  container.innerHTML = `
    <div class="ld-screen ps-block">
      <div class="ld-stage">
        <div class="ps-block-wm" aria-hidden="true">学</div>
        <p class="ld-eyebrow ps-block-eyebrow">${esc(T('session.prestudy.title', null, 'Study first'))}</p>
        ${item.title ? `<h2 class="ld-h1 ps-block-title"${lang ? ` lang="${lang}"` : ''}>${esc(item.title)}</h2>` : ''}
        <p class="ps-block-why">${esc(why)}</p>
        <div class="ld-wrap">
          <span class="ld-tag">${esc(T('session.prestudy.minutes', { n: minutes }, `About ${minutes} min`))}</span>
          <span class="ld-tag">${esc(T('session.prestudy.elo', null, 'Your first attempt then counts at half weight'))}</span>
          ${dropped ? `<span class="ld-tag ld-tag--warn">${esc(T('session.prestudy.dropped', { count: dropped }, dropped === 1 ? '1 fewer test today' : `${dropped} fewer tests today`))}</span>` : ''}
        </div>
      </div>
      <div class="ld-dock">
        <a class="ld-btn" data-prestudy-start href="${esc(prestudyUrl(item, ctx.languageId))}">
          <i class="bi bi-play-circle-fill" aria-hidden="true"></i>${esc(T('session.prestudy.start', null, 'Start studying'))}
        </a>
        <button type="button" class="ld-btn ld-btn--ghost" data-prestudy-cold>${esc(T('session.prestudy.cold', null, 'Take it cold'))}</button>
      </div>
    </div>`;

  const cold = container.querySelector('[data-prestudy-cold]');
  if (cold) cold.onclick = () => ctx.onComplete && ctx.onComplete({ skipped: true });

  return {
    destroy() {
      /* nothing to clean up */
    },
  };
}
