// static/js/session/controller.js
// Daily Study Session controller — drives an ordered queue of player modules
// (tests + practice) inside one page, persists completion, and resumes from
// server state. See plan we-now-have-the-swirling-haven.md.

import { getPlayer } from './player_registry.js';

const $ = (id) => document.getElementById(id);
const T = (key, params, fallback) =>
  window.LinguaI18n && typeof window.LinguaI18n.t === 'function'
    ? window.LinguaI18n.t(key, params)
    : fallback || key;

// Looks up a dim_languages language_code (e.g. 'zh', 'ja') from a numeric
// language_id, using the metadata LinguaMetadata.load() already cached
// during init(). Returns '' (never a stale/wrong code) if metadata hasn't
// loaded or the id isn't found, so the [lang] attribute is simply absent
// rather than misleading.
function resolveLanguageCode(languageId) {
  const cache = window.LinguaMetadata && LinguaMetadata._cache;
  if (!cache || !Array.isArray(cache.languages)) return '';
  const lang = cache.languages.find((l) => l.id === languageId);
  return (lang && lang.language_code) || '';
}

const session = {
  languageId: null,
  queue: [], // [{ kind:'test'|'practice', id, slug?, test_type?, mode?, is_completed }]
  index: 0,
  player: null, // { destroy() } handle for the currently-mounted player
  _completing: false, // re-entrancy latch for onItemComplete (M3)
  // Practice-only mode (`/session?mode=practice`, nav "Practice" link): the
  // queue is the same daily-session queue, just with every `kind:'test'` item
  // dropped client-side before it ever renders. This needs no server change —
  // completion still POSTs per-item exactly as it does today — but it does
  // mean next_index (computed server-side over the FULL queue) can't be
  // trusted once we've filtered; see loadSession().
  practiceOnly: false,
};

document.addEventListener('DOMContentLoaded', init);

async function init() {
  const params = new URLSearchParams(window.location.search);
  session.practiceOnly = params.get('mode') === 'practice';
  applyModeLabels();

  session.languageId = parseInt(localStorage.getItem('selectedLanguageId') || '0', 10);
  if (!session.languageId) {
    window.location.href = '/language-selection';
    return;
  }
  try {
    if (window.LinguaMetadata && typeof LinguaMetadata.load === 'function') {
      await LinguaMetadata.load();
    }
    await loadSession();
  } catch (e) {
    console.error(e);
    showError(e.message || 'Failed to load session.');
  }
}

// Swap the page's static "Daily Session" copy for practice-mode copy. Called
// once, before the queue is fetched, so it doesn't depend on session data —
// only on the `mode` query param. No-op outside practice mode, leaving the
// template's default (i18n-applied) text untouched.
//
// i18n-manager.js loads translations asynchronously and, once loaded, calls
// applyToDOM() — which re-derives every [data-i18n] element's textContent
// from ITS OWN attribute value, discarding whatever we set here. Setting
// textContent alone would get silently overwritten the moment translations
// finish loading (or on any later language switch). Repointing the
// `data-i18n` attribute itself is what makes the override stick.
function applyModeLabels() {
  if (!session.practiceOnly) return;

  const header = $('sessionHeaderLabel');
  if (header) {
    header.setAttribute('data-i18n', 'session.header_practice');
    header.textContent = T('session.header_practice', null, 'Practice');
  }

  const title = $('sessionStartTitle');
  if (title) {
    title.setAttribute('data-i18n', 'session.start_title_practice');
    title.textContent = T('session.start_title_practice', null, "Today's Practice");
  }

  const browseLink = $('sessionBrowseInsteadLink');
  if (browseLink) {
    browseLink.setAttribute('data-i18n', 'session.browse_instead_practice');
    browseLink.textContent = T('session.browse_instead_practice', null, 'Back to daily session');
    browseLink.setAttribute('href', '/session');
  }

  const doneLink = $('sessionDoneBrowseLink');
  if (doneLink) {
    doneLink.setAttribute('data-i18n', 'session.done_browse_practice');
    doneLink.textContent = T('session.done_browse_practice', null, 'Back to daily session');
    doneLink.setAttribute('href', '/session');
  }

  document.title = `${T('session.header_practice', null, 'Practice')} | LinguaDojo`;
}

async function loadSession() {
  const res = await window.authFetch(`/api/study-session?language_id=${session.languageId}`);
  if (!res.ok) throw new Error(`Session load failed (${res.status})`);
  const body = await res.json();
  const data = body.data || body;

  let queue = data.queue || [];
  if (session.practiceOnly) {
    queue = queue.filter((q) => q.kind !== 'test');
  }
  session.queue = queue;

  if (session.practiceOnly) {
    // Server's next_index indexes the FULL queue (tests included), which no
    // longer lines up once test items are filtered out — recompute it over
    // what's actually left.
    const firstIncomplete = queue.findIndex((q) => !q.is_completed);
    session.index = firstIncomplete === -1 ? queue.length : firstIncomplete;
  } else {
    session.index = typeof data.next_index === 'number' ? data.next_index : 0;
  }
  $('sessionLoading').classList.add('d-none');

  if (session.queue.length === 0) {
    showEmpty();
    return;
  }
  renderStart();
}

function renderStart() {
  const total = session.queue.length;
  const done = session.queue.filter((q) => q.is_completed).length;
  const remaining = total - done;
  const tests = session.queue.filter((q) => q.kind === 'test').length;
  // TASK-714: surface blocks (flashcards / dual_translation) count alongside
  // practice in the "X tests · Y practice" line rather than vanishing from the
  // summary — the whole point of planning them is that they are visible study.
  const practice = session.queue.filter((q) => q.kind !== 'test').length;

  if (remaining === 0) {
    // already finished today's load
    showSummary();
    return;
  }

  $('sessionStartSummary').textContent = session.practiceOnly
    ? T(
        'session.summary_line_practice',
        { practice, remaining },
        `${practice} practice · ${remaining} left today`
      )
    : T(
        'session.summary_line',
        { tests, practice, remaining },
        `${tests} tests · ${practice} practice · ${remaining} left today`
      );
  const resuming = done > 0;
  $('sessionStartBtnLabel').textContent = resuming
    ? T('session.resume_button', null, 'Resume session')
    : T('session.start_button', null, 'Start session');

  const start = $('sessionStart');
  start.classList.remove('d-none');
  $('sessionStartBtn').onclick = () => {
    start.classList.add('d-none');
    runCurrent();
  };
}

function runCurrent() {
  // Skip past anything already completed (resume / re-entrancy safety).
  while (session.index < session.queue.length && session.queue[session.index].is_completed) {
    session.index++;
  }
  if (session.index >= session.queue.length) {
    showSummary();
    return;
  }

  const item = session.queue[session.index];
  $('sessionProgress').classList.remove('d-none');
  updateProgressHeader();

  // Tear down the previous player before mounting the next.
  if (session.player && typeof session.player.destroy === 'function') {
    try {
      session.player.destroy();
    } catch (_) {
      /* non-fatal */
    }
  }
  const stage = $('sessionStage');
  stage.innerHTML = '';
  // Tag the stage with the item's study-language code so styles.css can
  // pick CJK-correct fonts per :lang() scope (see the per-language font
  // override block there) — without this, Chinese and Japanese text share
  // one font stack and one of them always renders in the other's glyphs.
  stage.lang = resolveLanguageCode(item.language_id || session.languageId) || '';
  window.scrollTo({ top: 0, behavior: 'auto' });

  const player = getPlayer(item);
  session.player = player.mount(stage, {
    item,
    languageId: session.languageId,
    onComplete: (result) => onItemComplete(item, result),
    onSkip: () => onItemSkip(item), // advance WITHOUT marking complete (stays in resume)
  });

  // Translate the data-i18n markup the player just injected into the stage
  // (applyToDOM normally runs only at page load, before the stage exists).
  if (window.LinguaI18n && typeof LinguaI18n.applyToDOM === 'function') {
    LinguaI18n.applyToDOM(stage);
  }
}

// Persist one item's completion. Returns true only on an acknowledged 2xx.
// authFetch resolves (not rejects) on 4xx/5xx, so we must check res.ok —
// otherwise a server rejection looks identical to success.
//
// Test slots go to the daily-load endpoint; EVERY other kind (practice chunks
// and the TASK-714 surface blocks) goes to complete-block, which is also where
// surfaces get their weekly counter credited. This branches on
// `kind === 'test'` rather than enumerating the others so a future queue kind
// is credited by default instead of silently completing nowhere — the F2 /
// TASK-701 failure mode.
async function persistCompletion(item) {
  const [url, payload] =
    item.kind === 'test'
      ? ['/api/tests/daily-load/complete', { test_id: item.id, language_id: session.languageId }]
      : [
          '/api/study-session/complete-block',
          { block_id: item.id, language_id: session.languageId },
        ];
  const res = await window.authFetch(url, { method: 'POST', body: JSON.stringify(payload) });
  return !!(res && res.ok);
}

async function onItemComplete(item, result) {
  // Re-entrancy latch (M3): players can fire onComplete more than once (e.g. a
  // second click during the await). Without this, completion POSTs twice and
  // ELO can be awarded twice.
  if (session._completing) return;
  session._completing = true;
  try {
    // Every queue kind persists — surfaces included. An allow-list here would
    // have to be widened for each new kind, and forgetting to is invisible:
    // the item completes on screen and no counter ever moves (F2 / TASK-701).
    if (item.kind) {
      let ok = false;
      try {
        ok = await persistCompletion(item);
        if (!ok) ok = await persistCompletion(item); // one silent retry (M2)
      } catch (e) {
        console.error('Failed to persist completion:', e);
      }
      if (!ok && typeof window.showToast === 'function') {
        // Surface the failure but still advance — the learner already finished.
        window.showToast(
          T('session.save_failed', null, 'Couldn’t save your progress — check your connection.')
        );
      }
    }
    item.is_completed = true;
    advance();
  } finally {
    session._completing = false;
  }
}

function advance() {
  session.index++;
  runCurrent();
}

// Learner chose to skip: leave is_completed false (so it re-appears on resume)
// but flag it so the progress dots and end-of-session summary can show it as
// skipped rather than merely "not done".
function onItemSkip(item) {
  item.skipped = true;
  advance();
}

function updateProgressHeader() {
  const total = session.queue.length;
  const done = session.queue.filter((q) => q.is_completed).length;
  $('sessionProgressCount').textContent = `${done}/${total}`;
  $('sessionProgressFill').style.width = total ? `${(done / total) * 100}%` : '0%';
  $('sessionDots').innerHTML = session.queue
    .map((q, i) => {
      let cls = '';
      if (q.is_completed) cls = 'done';
      else if (i === session.index) cls = 'current';
      else if (q.skipped) cls = 'skipped';
      const type = itemTypeLabel(q);
      const state = dotStateLabel(q, i);
      const label = T('session.dot_label', { type, state }, `${type} — ${state}`);
      return `<span class="session-dot ${cls}" role="listitem" aria-label="${escapeHtml(label)}"></span>`;
    })
    .join('');
}

// ---- Labels & escaping (shared by dots + summary) ----------------------------

// Human label for an item's type: the localized test type (Listening, Reading…)
// or "Practice". Falls back to the raw value so an unmapped type still reads.
// TASK-714: surface kinds carry no test_type, so they must be labelled off
// `kind`. Without this they fell through to the `|| 'listening'` default and a
// flashcards block was announced to screen readers as "Listening".
const KIND_LABELS = {
  practice: ['session.practice_heading', 'Practice'],
  flashcards: ['session.flashcards_heading', 'Flashcards'],
  dual_translation: ['session.dt_heading', 'Dual Translation'],
  // TASK-533. Omitting this is not cosmetic — an unmapped kind falls through
  // to the `|| 'listening'` default below and the block is announced as
  // "Listening", the exact TASK-714 defect this map was created to fix.
  speed_round: ['session.speed_round_heading', 'Speed Round'],
};

function itemTypeLabel(item) {
  const label = KIND_LABELS[item.kind];
  if (label) return T(label[0], null, label[1]);
  const tt = item.test_type || 'listening';
  return T('test_list.' + tt, null, tt);
}

// Display title for an item: the test's own title (or slug) for tests, the
// generic practice heading for practice blocks.
function itemTitle(item) {
  if (KIND_LABELS[item.kind]) return itemTypeLabel(item);
  return item.title || item.slug || itemTypeLabel(item);
}

// State word for a progress dot at position i, given the current cursor.
function dotStateLabel(item, i) {
  if (item.is_completed) return T('session.item_done', null, 'Done');
  if (item.skipped) return T('session.item_skipped', null, 'Skipped');
  if (i === session.index) return T('session.item_current', null, 'In progress');
  return T('session.item_pending', null, 'Not started');
}

// Escape a string for safe interpolation into innerHTML / attribute context.
// Item titles come from the server, so this guards the summary and dot labels
// against markup injection.
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function showSummary() {
  $('sessionProgress').classList.add('d-none');
  $('sessionStart').classList.add('d-none');
  $('sessionStage').innerHTML = '';
  const total = session.queue.length;
  const done = session.queue.filter((q) => q.is_completed).length;

  const rows = session.queue
    .map((q) => {
      const isDone = !!q.is_completed;
      const state = isDone
        ? T('session.item_done', null, 'Done')
        : T('session.item_skipped', null, 'Skipped');
      const icon = isDone ? 'fa-circle-check' : 'fa-circle-minus';
      return (
        `<li class="${isDone ? 'is-done' : 'is-skipped'}">` +
        `<span class="ico"><i class="fas ${icon}"></i></span>` +
        `<span class="meta">` +
        `<span class="r-title d-block">${escapeHtml(itemTitle(q))}</span>` +
        `<span class="r-type d-block">${escapeHtml(itemTypeLabel(q))}</span>` +
        `</span>` +
        `<span class="r-state">${escapeHtml(state)}</span>` +
        `</li>`
      );
    })
    .join('');

  const resultsLabel = T('session.results_title', null, 'Your results');
  $('sessionSummaryBody').innerHTML =
    `<p class="lead mb-1">${done} / ${total}</p>` +
    `<p class="text-muted">${escapeHtml(T('session.done_line', null, 'Nice work — you finished today’s load.'))}</p>` +
    `<ul class="session-results" aria-label="${escapeHtml(resultsLabel)}">${rows}</ul>`;
  $('sessionSummary').classList.remove('d-none');
}

function showEmpty() {
  $('sessionStart').classList.remove('d-none');
  $('sessionStartSummary').textContent = session.practiceOnly
    ? T('session.empty_practice_page', null, 'No practice due right now.')
    : T(
        'session.empty',
        null,
        'No session items for today. Check your Study Plan or browse tests.'
      );
  $('sessionStartBtn').classList.add('d-none');
}

function showError(msg) {
  $('sessionLoading').classList.add('d-none');
  $('sessionErrorMsg').textContent = msg;
  const retry = $('sessionErrorRetry');
  if (retry) retry.onclick = retryLoad;
  $('sessionError').classList.remove('d-none');
}

// Retry from the error card: hide the error, show the spinner, and re-run the
// session load. Any fresh failure re-renders the (still retryable) error card.
async function retryLoad() {
  $('sessionError').classList.add('d-none');
  $('sessionLoading').classList.remove('d-none');
  try {
    await loadSession();
  } catch (e) {
    console.error(e);
    showError(e.message || 'Failed to load session.');
  }
}
