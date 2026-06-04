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

const session = {
  languageId: null,
  queue: [], // [{ kind:'test'|'practice', id, slug?, test_type?, mode?, is_completed }]
  index: 0,
  player: null, // { destroy() } handle for the currently-mounted player
};

document.addEventListener('DOMContentLoaded', init);

async function init() {
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

async function loadSession() {
  const res = await window.authFetch(`/api/study-session?language_id=${session.languageId}`);
  if (!res.ok) throw new Error(`Session load failed (${res.status})`);
  const body = await res.json();
  const data = body.data || body;

  session.queue = data.queue || [];
  session.index = typeof data.next_index === 'number' ? data.next_index : 0;
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
  const practice = session.queue.filter((q) => q.kind === 'practice').length;

  if (remaining === 0) {
    // already finished today's load
    showSummary();
    return;
  }

  $('sessionStartSummary').textContent = T(
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
  window.scrollTo({ top: 0, behavior: 'auto' });

  const player = getPlayer(item);
  session.player = player.mount(stage, {
    item,
    languageId: session.languageId,
    onComplete: (result) => onItemComplete(item, result),
    onSkip: () => advance(), // advance WITHOUT marking complete (stays in resume)
  });

  // Translate the data-i18n markup the player just injected into the stage
  // (applyToDOM normally runs only at page load, before the stage exists).
  if (window.LinguaI18n && typeof LinguaI18n.applyToDOM === 'function') {
    LinguaI18n.applyToDOM(stage);
  }
}

async function onItemComplete(item, result) {
  try {
    if (item.kind === 'test') {
      await window.authFetch('/api/tests/daily-load/complete', {
        method: 'POST',
        body: JSON.stringify({ test_id: item.id, language_id: session.languageId }),
      });
    } else if (item.kind === 'practice') {
      await window.authFetch('/api/study-session/complete-block', {
        method: 'POST',
        body: JSON.stringify({ block_id: item.id, language_id: session.languageId }),
      });
    }
  } catch (e) {
    // Best-effort: the user already finished; don't block advancing.
    console.error('Failed to persist completion:', e);
  }
  item.is_completed = true;
  advance();
}

function advance() {
  session.index++;
  runCurrent();
}

function updateProgressHeader() {
  const total = session.queue.length;
  const done = session.queue.filter((q) => q.is_completed).length;
  $('sessionProgressCount').textContent = `${done}/${total}`;
  $('sessionProgressFill').style.width = total ? `${(done / total) * 100}%` : '0%';
  $('sessionDots').innerHTML = session.queue
    .map((q, i) => {
      const cls = q.is_completed ? 'done' : i === session.index ? 'current' : '';
      return `<span class="session-dot ${cls}" title="${q.kind}"></span>`;
    })
    .join('');
}

function showSummary() {
  $('sessionProgress').classList.add('d-none');
  $('sessionStart').classList.add('d-none');
  $('sessionStage').innerHTML = '';
  const total = session.queue.length;
  const done = session.queue.filter((q) => q.is_completed).length;
  $('sessionSummaryBody').innerHTML =
    `<p class="lead mb-1">${done} / ${total}</p>` +
    `<p class="text-muted">${T('session.done_line', null, 'Nice work — you finished today’s load.')}</p>`;
  $('sessionSummary').classList.remove('d-none');
}

function showEmpty() {
  $('sessionStart').classList.remove('d-none');
  $('sessionStartSummary').textContent = T(
    'session.empty',
    null,
    'No session items for today. Check your Study Plan or browse tests.'
  );
  $('sessionStartBtn').classList.add('d-none');
}

function showError(msg) {
  $('sessionLoading').classList.add('d-none');
  $('sessionErrorMsg').textContent = msg;
  $('sessionError').classList.remove('d-none');
}
