// static/js/session/controller.js
// Daily Study Session controller — drives an ordered queue of player modules
// (tests + practice) inside one page, persists completion, and resumes from
// server state. See plan we-now-have-the-swirling-haven.md.

import { getPlayer, preloadPlayers, prefetchItem } from './player_registry.js';
import { createSaveQueue } from './save_queue.js';
import { T, escapeHtml, applyI18n, toastSaveFailed } from './dom.js';
import {
  hasTail,
  tailCounts,
  tailPromptKey,
  governorKey,
  countKey,
  appendTailRound,
  requiredProgress,
  normalizeExtraChoice,
  isRunnableExtraChoice,
  extraBeyondQuota,
  makeExtraItem,
  splitPracticeQueue,
} from './tail.js';

const $ = (id) => document.getElementById(id);

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

// The app shell (templates/base.html). Absent in unit tests and on any page
// without the redesign shell, so every use is guarded.
const shell = () => window.LinguaShell || null;

// One-character seals for each item type, in the study language (the mockup's
// glyph set). Other languages show the type label's initial.
const GLYPHS = {
  zh: {
    listening: '听',
    reading: '读',
    dictation: '写',
    practice: '练',
    dual_translation: '译',
    classifier_drill: '量',
    pinyin: '调',
    pitch_accent: '调',
    flashcards: '卡',
    prestudy: '学',
    dt_repair: '改',
    speed_round: '速',
    today: '今天',
    done: '完成',
  },
  ja: {
    listening: '聴',
    reading: '読',
    dictation: '書',
    practice: '練',
    dual_translation: '訳',
    classifier_drill: '数',
    pinyin: '音',
    pitch_accent: '音',
    flashcards: '札',
    prestudy: '学',
    dt_repair: '直',
    speed_round: '速',
    today: '今日',
    done: '完了',
  },
};

function studyCode() {
  return resolveLanguageCode(session.languageId) || '';
}

function glyphFor(key, fallback) {
  const set = GLYPHS[studyCode()];
  return (set && set[key]) || fallback || '';
}

// Seal for a queue item: by kind, else by test type.
function itemGlyph(item) {
  const key = GLYPHS.zh[item.kind] ? item.kind : item.test_type || 'listening';
  return glyphFor(key, itemTypeLabel(item).charAt(0).toUpperCase());
}

const session = {
  languageId: null,
  // True while an item's player is on stage (task mode, Back pill live).
  running: false,
  queue: [], // [{ kind:'test'|'practice', id, slug?, test_type?, mode?, is_completed }]
  index: 0,
  player: null, // { destroy() } handle for the currently-mounted player
  // Practice-only mode (`/session?mode=practice`, nav "Practice" link):
  // exercises only. The queue is the daily-session queue filtered client-side
  // to its review (maintenance) practice chunks — tests, flashcards, dual
  // translation, speed round and prestudy never render here. Today's new-word
  // (acquisition) chunks are held in `newWordItems` and offered only once the
  // exercises are done ("Learn new words"). Completion still POSTs per-item
  // exactly as in the daily session, but next_index (computed server-side over
  // the FULL queue) can't be trusted once we've filtered; see loadSession().
  practiceOnly: false,
  newWordItems: [],
  newWordsDeclined: false,
  // Optional end-of-session tail (session-budget-settings). The learner said
  // "Done for today"; stop re-offering until the page is reloaded.
  tailDeclined: false,
  _tailToken: 0, // guards a slow GET from painting over a newer summary
  // Practice extra rounds (ADR-036, practice mode only): the learner's last
  // choice (pre-selected next time), a round counter for ids, the latest tail
  // (for the beyond-quota warning) and whether they said "Done".
  extraChoice: { reviews: true, newWords: 0 },
  extraRounds: 0,
  extraTail: null,
  extraDeclined: false,
  // `/session?mode=practice&extra=reviews` (the knowledge page's "Review in Practice",
  // TASK-1043): start a reviews round at once when nothing required is left today.
  extraDeepLink: false,
};

document.addEventListener('DOMContentLoaded', init);

// Strings added by the 2026-11 redesign may not be in the locale bundles yet,
// and LinguaI18n.applyToDOM would print a missing [data-i18n] key verbatim.
// Those elements carry data-ld-i18n instead: translated when the bundle has
// the key, else they keep their English text.
function localizeNew(root = document) {
  root.querySelectorAll('[data-ld-i18n]').forEach((el) => {
    if (el.dataset.ldFallback === undefined) el.dataset.ldFallback = el.textContent;
    el.textContent = T(el.dataset.ldI18n, null, el.dataset.ldFallback);
  });
}
document.addEventListener('languageChanged', () => {
  localizeNew();
  paintDecor();
});

// ---- One-tap return from pages that leave the session (TASK-993) ----------
// A page that takes the learner out of a running session and sends them back
// to carry on (the prestudy page's "Take the test", the follow-up's "Back to
// today's session") adds a one-shot marker to the URL:
//   /session?resume=<slug>        open that test at once, if it is the next item
//   /session?resume_after=<slug>  open the next item, if it comes after that
//                                 (finished) test
// The marker is read once and removed from the address bar before anything
// else, so a reload or a Back navigation lands on the Today card as usual. It
// only skips the Today card when the queue the server returns still matches
// what the page expected; anything else (the item was done elsewhere, the
// block did not save, the queue was rebuilt) shows the Today card.
const RESUME_PARAMS = ['resume', 'resume_after'];

export function takeResumeMarker(loc = window.location, hist = window.history) {
  let params;
  try {
    params = new URLSearchParams(loc.search || '');
  } catch {
    return null;
  }
  const present = RESUME_PARAMS.filter((k) => params.has(k));
  if (!present.length) return null;
  const marker = params.get('resume')
    ? { slug: params.get('resume'), after: false }
    : params.get('resume_after')
      ? { slug: params.get('resume_after'), after: true }
      : null;
  present.forEach((k) => params.delete(k));
  const qs = params.toString();
  try {
    if (hist && typeof hist.replaceState === 'function') {
      hist.replaceState(hist.state, '', `${loc.pathname}${qs ? `?${qs}` : ''}${loc.hash || ''}`);
    }
  } catch {
    /* history blocked: the marker is still used only once per page load */
  }
  return marker;
}

// `extra=reviews` on a practice-mode URL: true once, and the parameter is removed so a
// reload does not start another round.
export function takeExtraDeepLink(loc = window.location, hist = window.history) {
  let params;
  try {
    params = new URLSearchParams(loc.search || '');
  } catch {
    return false;
  }
  if (params.get('extra') !== 'reviews') return false;
  params.delete('extra');
  const qs = params.toString();
  try {
    if (hist && typeof hist.replaceState === 'function') {
      hist.replaceState(hist.state, '', `${loc.pathname}${qs ? `?${qs}` : ''}${loc.hash || ''}`);
    }
  } catch {
    /* history blocked: still used only once per page load */
  }
  return true;
}

// The queue index to open straight away for `marker`, or -1 for the Today card.
// `start` is where the session would resume (server next_index); the item
// opened is the one Resume would open from there.
export function resumeIndex(marker, queue, start = 0) {
  if (!marker || !marker.slug || !Array.isArray(queue)) return -1;
  let next = Math.max(0, Number(start) || 0);
  while (next < queue.length && queue[next].is_completed) next++;
  const item = queue[next];
  if (!item) return -1;
  const isTest = (q) => q && q.kind === 'test' && q.slug === marker.slug;
  if (!marker.after) return isTest(item) ? next : -1;
  const at = queue.findIndex(isTest);
  return at !== -1 && at < next && queue[at].is_completed ? next : -1;
}

async function init() {
  const params = new URLSearchParams(window.location.search);
  session.practiceOnly = params.get('mode') === 'practice';
  // Consumed now, before any await: a reload never sees it again.
  const resume = takeResumeMarker();
  session.extraDeepLink = session.practiceOnly && takeExtraDeepLink();
  applyModeLabels();

  session.languageId = parseInt(localStorage.getItem('selectedLanguageId') || '0', 10);
  if (!session.languageId) {
    window.location.href = '/language-selection';
    return;
  }
  try {
    // Metadata is only needed when a player mounts (resolveLanguageCode), so
    // it loads alongside the session instead of in front of it. A metadata
    // failure only leaves the stage's [lang] attribute empty.
    const metadata =
      window.LinguaMetadata && typeof LinguaMetadata.load === 'function'
        ? Promise.resolve(LinguaMetadata.load()).catch((e) =>
            console.warn('[session] metadata:', e)
          )
        : Promise.resolve();
    const resumed = await loadSession({ resume: session.practiceOnly ? null : resume });
    await metadata;
    // Opened only now: the stage's [lang] (CJK fonts) needs the metadata.
    if (resumed) {
      $('sessionLoading').classList.add('d-none');
      runCurrent();
    }
    // Seals and watermarks need the language code, which metadata supplies.
    paintDecor();
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

  const quickTitle = $('sessionQuickTitle');
  if (quickTitle) {
    quickTitle.setAttribute('data-ld-i18n', 'session.more_practice');
    quickTitle.textContent = 'More practice';
    delete quickTitle.dataset.ldFallback;
  }

  const browseLink = $('sessionBrowseInsteadLink');
  if (browseLink) {
    browseLink.setAttribute('data-i18n', 'session.browse_instead_practice');
    browseLink.textContent = T('session.browse_instead_practice', null, 'Back to daily session');
    browseLink.setAttribute('href', '/session');
  }

  const doneTitle = $('sessionDoneTitle');
  if (doneTitle) {
    doneTitle.setAttribute('data-i18n', 'session.done_title_practice');
    doneTitle.textContent = T('session.done_title_practice', null, 'Exercises done!');
  }

  const doneLink = $('sessionDoneBrowseLink');
  if (doneLink) {
    doneLink.setAttribute('data-i18n', 'session.done_browse_practice');
    doneLink.textContent = T('session.done_browse_practice', null, 'Back to daily session');
    doneLink.setAttribute('href', '/session');
  }

  document.title = `${T('session.header_practice', null, 'Practice')} | LinguaDojo`;
}

// Practice mode still sends scope=practice; the server's tail gate now ignores
// test items in every mode, so it no longer changes the response.
function studySessionUrl() {
  const scope = session.practiceOnly ? '&scope=practice' : '';
  return `/api/study-session?language_id=${session.languageId}${scope}`;
}

// The page starts this request from an inline script, before the module graph
// has loaded (templates/study_session.html); use that response once.
function takeEarlySession(url) {
  const early = window.__ldSessionEarly;
  window.__ldSessionEarly = null;
  return early && early.url === url && early.promise ? early.promise : null;
}

async function fetchSession() {
  const url = studySessionUrl();
  const early = takeEarlySession(url);
  if (early) {
    try {
      const res = await early;
      if (res && res.ok) return res;
    } catch (e) {
      console.warn('[session] early session request failed, retrying:', e);
    }
  }
  return window.authFetch(url);
}

// Returns true when `resume` matched and the caller should open the item at
// session.index straight away (the Today card is not shown).
async function loadSession({ resume = null } = {}) {
  const res = await fetchSession();
  if (!res.ok) throw new Error(`Session load failed (${res.status})`);
  const body = await res.json();
  const data = body.data || body;
  // The start card is rendered with T(); make sure translations are in.
  if (window.LinguaMetadata && typeof LinguaMetadata.i18nReady === 'function') {
    await LinguaMetadata.i18nReady();
  }
  localizeNew();

  let queue = data.queue || [];
  if (session.practiceOnly) {
    const { exercises, newWords } = splitPracticeQueue(queue);
    queue = exercises;
    session.newWordItems = newWords;
  }
  session.queue = queue;
  // Start importing the players today's queue needs while the start card shows.
  preloadPlayers(queue.concat(session.newWordItems || []));

  if (session.practiceOnly) {
    // Server's next_index indexes the FULL queue (tests included), which no
    // longer lines up once test items are filtered out — recompute it over
    // what's actually left.
    const firstIncomplete = queue.findIndex((q) => !q.is_completed);
    session.index = firstIncomplete === -1 ? queue.length : firstIncomplete;
  } else {
    session.index = typeof data.next_index === 'number' ? data.next_index : 0;
  }

  const target = resumeIndex(resume, session.queue, session.index);
  if (target !== -1) {
    session.index = target;
    return true;
  }
  $('sessionLoading').classList.add('d-none');

  if (session.queue.length === 0) {
    showEmpty();
  } else {
    renderStart();
  }
  // The deep link applies to this first load only.
  session.extraDeepLink = false;
  return false;
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
    if (startDeepLinkedReviews()) return;
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

  showPracticeCount();

  const start = $('sessionStart');
  start.classList.remove('d-none');
  paintDecor();
  $('sessionStartBtn').onclick = () => {
    start.classList.add('d-none');
    runCurrent();
  };
}

// ---- Today card decoration (hero seals, watermark, "Up next") --------------
// Purely visual; every element is optional.

function firstPendingIndex() {
  let i = session.index;
  while (i < session.queue.length && session.queue[i].is_completed) i++;
  return i;
}

function paintDecor() {
  const code = studyCode();
  const wm = $('sessionStartWm');
  if (wm) {
    wm.textContent = glyphFor(session.practiceOnly ? 'practice' : 'today');
    wm.lang = code;
  }
  const doneWm = $('sessionDoneWm');
  if (doneWm) {
    doneWm.textContent = glyphFor('done');
    doneWm.lang = code;
  }
  const seals = $('sessionStartItems');
  const empty = !session.queue.length;
  const next = firstPendingIndex();
  if (seals) {
    seals.lang = code;
    // One seal per item: done, the one up next, the rest.
    seals.innerHTML = empty
      ? ''
      : session.queue
          .map((q, i) => {
            const cls = q.is_completed ? ' is-done' : i === next ? ' is-current' : '';
            return `<span class="ld-seal${cls}" title="${escapeHtml(itemTypeLabel(q))}">${escapeHtml(itemGlyph(q))}</span>`;
          })
          .join('');
    seals.classList.toggle('d-none', empty);
  }
  const up = $('sessionUpNext');
  if (up) {
    const item = session.queue[next];
    const startShown = $('sessionStart') && !$('sessionStart').classList.contains('d-none');
    up.classList.toggle('d-none', !item || !startShown || session.running);
    if (item) {
      const glyph = $('sessionUpNextGlyph');
      if (glyph) {
        glyph.textContent = itemGlyph(item);
        glyph.lang = code;
      }
      const title = itemTitle(item);
      const type = itemTypeLabel(item);
      const t = $('sessionUpNextTitle');
      if (t) t.textContent = title;
      const ty = $('sessionUpNextType');
      if (ty) ty.textContent = title === type ? '' : type;
    }
  }
}

// ---- Run frame (task mode + header + Back) ---------------------------------
// While an item runs the page is one task screen: the shell's Back-pill
// header, the progress strip, and #sessionStage filling the rest. Players get
// ctx.frame to set the header and hook Back (see session-frame in the
// redesign hand-off).

let backOffs = []; // Back handlers the current player registered

function releasePlayerBack() {
  backOffs.forEach((off) => {
    try {
      off();
    } catch {
      /* already gone */
    }
  });
  backOffs = [];
}

function teardownPlayer() {
  if (session.player && typeof session.player.destroy === 'function') {
    try {
      session.player.destroy();
    } catch {
      /* non-fatal */
    }
  }
  session.player = null;
  releasePlayerBack();
}

function sessionHref() {
  return session.practiceOnly ? '/session?mode=practice' : '/session';
}

function enterRun() {
  session.running = true;
  document.body.classList.add('session-running');
  const sh = shell();
  if (!sh) return;
  if (typeof sh.isTaskMode !== 'function' || !sh.isTaskMode()) sh.setTaskMode(true);
}

function leaveRun() {
  if (!session.running && !document.body.classList.contains('session-running')) return;
  session.running = false;
  document.body.classList.remove('session-running');
  const sh = shell();
  if (sh && typeof sh.setTaskMode === 'function') sh.setTaskMode(false);
}

// The header for an item: its type, its title (tests), its seal.
function headerFor(item) {
  const type = itemTypeLabel(item);
  const title = itemTitle(item);
  return {
    title: type,
    subtitle: title === type ? '' : title,
    glyph: itemGlyph(item),
    end: '',
    backHref: sessionHref(),
  };
}

function makeFrame(item, stage) {
  const live = () => session.running && session.queue[session.index] === item;
  return {
    stage,
    setHeader(opts) {
      const sh = shell();
      if (sh && live()) sh.setTaskHeader(opts || {});
    },
    onBack(fn) {
      const sh = shell();
      if (!sh || typeof sh.onBack !== 'function' || typeof fn !== 'function') return () => {};
      const off = sh.onBack((e) => (live() ? fn(e) : false));
      backOffs.push(off);
      return off;
    },
  };
}

// Back pill during a run: back to the Today card in-page (a reload would drop
// saves still retrying). Unfinished and skipped items come back on Resume.
// During an optional round (tail / extra) it returns to the summary instead.
function onShellBack() {
  if (!session.running) return false;
  const item = session.queue[session.index];
  teardownPlayer();
  $('sessionStage').innerHTML = '';
  // The player took the item's prefetch; let the start card load (and count)
  // it again, as it would on a fresh visit.
  if (item && !item.prefetch) delete item._prefetched;
  if (item && item.is_tail) {
    showSummary();
    return true;
  }
  $('sessionProgress').classList.add('d-none');
  leaveRun();
  const first = session.queue.findIndex((q) => !q.is_completed);
  session.index = first === -1 ? session.queue.length : first;
  renderStart();
  return true;
}

(function hookBack() {
  const sh = shell();
  if (sh && typeof sh.onBack === 'function') sh.onBack(onShellBack);
})();

// Start card: load the first item's data now, so it is ready when the learner
// presses Start. When that item is a practice round, also say how many
// exercises it holds (the player's `describePrefetch` hook), so the learner
// knows the size before starting.
function showPracticeCount() {
  const el = $('sessionStartCount');
  let i = session.index;
  while (i < session.queue.length && session.queue[i].is_completed) i++;
  const next = session.queue[i];
  if (!next) {
    if (el) el.classList.add('d-none');
    return;
  }
  const counted = !!el && next.kind === 'practice' && !next.is_extra;
  if (el) {
    el.textContent = counted ? T('session.count_loading', null, 'Counting exercises…') : '';
    el.classList.toggle('d-none', !counted);
  }
  const moreRounds = session.queue
    .slice(i + 1)
    .filter((q) => q.kind === 'practice' && !q.is_completed).length;
  prefetchItem(next, { languageId: session.languageId, current: null }).then((mod) => {
    if (!counted) return;
    const describe = mod && mod.describePrefetch;
    if (typeof describe !== 'function' || !next.prefetch) {
      el.classList.add('d-none');
      return;
    }
    next.prefetch.then((res) => {
      const text = describe(res, { moreRounds, t: T });
      el.textContent = text;
      el.classList.toggle('d-none', !text);
    });
  });
}

// While an item is in progress, let the next one start loading its data.
function prefetchUpcoming(current) {
  let i = session.index + 1;
  while (i < session.queue.length && session.queue[i].is_completed) i++;
  const next = session.queue[i];
  if (next) prefetchItem(next, { languageId: session.languageId, current });
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
  enterRun();
  $('sessionProgress').classList.remove('d-none');
  updateProgressHeader();

  // Tear down the previous player before mounting the next.
  teardownPlayer();
  const sh = shell();
  if (sh && typeof sh.setTaskHeader === 'function') sh.setTaskHeader(headerFor(item));
  const stage = $('sessionStage');
  stage.innerHTML = '';
  // Tag the stage with the item's study-language code so styles.css can
  // pick CJK-correct fonts per :lang() scope (see the per-language font
  // override block there) — without this, Chinese and Japanese text share
  // one font stack and one of them always renders in the other's glyphs.
  stage.lang = resolveLanguageCode(item.language_id || session.languageId) || '';
  window.scrollTo({ top: 0, behavior: 'auto' });
  stage.scrollTop = 0;

  const player = getPlayer(item);
  session.player = player.mount(stage, {
    item,
    languageId: session.languageId,
    onComplete: (result) => onItemComplete(item, result),
    onSkip: () => onItemSkip(item), // advance WITHOUT marking complete (stays in resume)
    frame: makeFrame(item, stage),
  });

  // Translate the data-i18n markup the player just injected into the stage
  // (applyToDOM normally runs only at page load, before the stage exists).
  applyI18n(stage);
  prefetchUpcoming(item);
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
  // Extra rounds are not daily blocks: their attempts already credited the
  // weekly counters (as tail work), so there is nothing to persist here.
  if (item.is_extra) return true;
  const [url, payload] =
    item.kind === 'test'
      ? ['/api/tests/daily-load/complete', { test_id: item.id, language_id: session.languageId }]
      : [
          '/api/study-session/complete-block',
          { block_id: item.id, language_id: session.languageId },
        ];
  // keepalive: the save outlives the page if the learner leaves right away.
  const res = await window.authFetch(url, {
    method: 'POST',
    body: JSON.stringify(payload),
    keepalive: true,
  });
  return !!(res && res.ok);
}

// Completions are saved in the background so the next item shows at once.
// Each is retried; one that still fails stays in the queue, raises the save
// banner (with Retry) and is tried again before the session's last step.
const saves = createSaveQueue({
  onFail: () => {
    // The banner says it and stays; the toast is only for pages without one.
    if (!$('sessionSaveStatus')) toastSaveFailed();
  },
  onChange: renderSaveStatus,
});

function renderSaveStatus({ failed }) {
  const box = $('sessionSaveStatus');
  if (!box) return;
  box.classList.toggle('d-none', !failed);
  box.classList.toggle('d-flex', !!failed);
  const retry = $('sessionSaveRetry');
  if (retry) {
    retry.disabled = false;
    retry.onclick = () => {
      retry.disabled = true;
      saves.retryFailed();
    };
  }
}

// Resolves once every completion is saved or has finally failed; failed ones
// get one more round first. True when nothing is left unsaved.
async function settleSaves() {
  if (await saves.settle()) return true;
  return saves.retryFailed();
}

// A backoff in progress is cut short when the page is being left.
window.addEventListener('pagehide', () => saves.hurry());

function onItemComplete(item) {
  // Players can fire onComplete more than once (a second click, a late
  // callback from a player already torn down). Only the item on stage, and
  // only once, may complete — otherwise completion POSTs twice (M3) or a
  // stale callback skips the item that replaced it.
  if (item.is_completed || session.queue[session.index] !== item) return;
  item.is_completed = true;
  // Every queue kind persists — surfaces included. An allow-list here would
  // have to be widened for each new kind, and forgetting to is invisible:
  // the item completes on screen and no counter ever moves (F2 / TASK-701).
  if (item.kind) saves.enqueue(() => persistCompletion(item), item.id);
  advance();
}

function advance() {
  session.index++;
  runCurrent();
}

// Learner chose to skip: leave is_completed false (so it re-appears on resume)
// but flag it so the progress dots and end-of-session summary can show it as
// skipped rather than merely "not done".
function onItemSkip(item) {
  if (session.queue[session.index] !== item) return;
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
      if (q.is_completed) cls = 'is-done';
      else if (i === session.index) cls = 'is-current';
      else if (q.skipped) cls = 'is-skipped';
      const type = itemTypeLabel(q);
      const state = dotStateLabel(q, i);
      const label = T('session.dot_label', { type, state }, `${type} — ${state}`);
      return `<i class="session-dot ${cls}" role="listitem" aria-label="${escapeHtml(label)}"></i>`;
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
  dt_repair: ['session.dt_repair_heading', 'Fix your sentences'],
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

function showSummary() {
  teardownPlayer();
  leaveRun();
  $('sessionProgress').classList.add('d-none');
  $('sessionStart').classList.add('d-none');
  $('sessionStage').innerHTML = '';
  // Optional tail items never count toward completion.
  const { done, total } = requiredProgress(session.queue);

  const rows = session.queue
    .map((q) => {
      const isDone = !!q.is_completed;
      const state = isDone
        ? T('session.item_done', null, 'Done')
        : T('session.item_skipped', null, 'Skipped');
      const icon = isDone ? 'fa-circle-check' : 'fa-circle-minus';
      const title = itemTitle(q);
      const type = itemTypeLabel(q);
      return (
        `<li class="ld-trow ${isDone ? 'is-done' : 'is-skipped is-faded'}">` +
        `<span class="ld-seal" aria-hidden="true">${escapeHtml(itemGlyph(q))}</span>` +
        `<span class="ld-trow__mid">` +
        `<b class="r-title">${escapeHtml(title)}</b>` +
        (title === type ? '' : `<small class="r-type">${escapeHtml(type)}</small>`) +
        `<small class="r-state"><i class="fas ${icon}" aria-hidden="true"></i> ${escapeHtml(state)}</small>` +
        `</span>` +
        `</li>`
      );
    })
    .join('');

  const resultsLabel = T('session.results_title', null, 'Your results');
  const head =
    `<p class="session-score ld-num">${done} / ${total}</p>` +
    `<p class="ld-muted mb-0">${escapeHtml(doneLine())}</p>`;
  const list = $('sessionResults');
  if (list) {
    // The list sits below the prompts, so the next action stays in view.
    $('sessionSummaryBody').innerHTML = head;
    list.setAttribute('aria-label', resultsLabel);
    list.innerHTML = rows;
    const wrap = $('sessionResultsWrap');
    if (wrap) wrap.classList.toggle('d-none', !rows);
  } else {
    $('sessionSummaryBody').innerHTML =
      head + `<ul class="session-results" aria-label="${escapeHtml(resultsLabel)}">${rows}</ul>`;
  }
  $('sessionSummary').classList.remove('d-none', 'is-empty');
  paintDecor();
  hideTailPrompt();
  hideExtraPanel();
  renderNewWordsPrompt();
  // Practice mode: show "Keep practising" now. It must not wait on (or depend
  // on) the tail fetch below, which re-builds the whole session server-side
  // and can fail or be slow; offerTail only refines it with today's quota.
  renderExtraPanel();
  offerTail();
}

function doneLine() {
  return session.practiceOnly
    ? T('session.done_line_practice', null, 'Nice work — you finished today’s exercises.')
    : T('session.done_line', null, 'Nice work — you finished today’s load.');
}

// ---- Learn new words (practice mode only) -----------------------------------
// Once the allotted exercises are done, offer today's new-word chunks. They are
// ordinary daily blocks, so they persist through complete-block as usual.

function newWordsPending() {
  return session.practiceOnly && !session.newWordsDeclined && session.newWordItems.length > 0;
}

function hideNewWordsPrompt() {
  const box = $('sessionNewWordsPrompt');
  if (box) box.classList.add('d-none');
}

function renderNewWordsPrompt() {
  const box = $('sessionNewWordsPrompt');
  if (!box) return;
  if (!newWordsPending()) {
    box.classList.add('d-none');
    return;
  }
  $('sessionNewWordsStart').onclick = startNewWords;
  $('sessionNewWordsLater').onclick = () => {
    session.newWordsDeclined = true;
    hideNewWordsPrompt();
    renderExtraPanel();
  };
  box.classList.remove('d-none');
}

function startNewWords() {
  const items = session.newWordItems;
  if (!items.length) return;
  session.newWordItems = [];
  // Drop skipped (still incomplete) optional items, as appendTailRound does.
  const kept = session.queue.filter((q) => !(q.is_tail && !q.is_completed));
  session.queue = kept.concat(items);
  session.index = kept.length;
  hideNewWordsPrompt();
  hideTailPrompt();
  hideExtraPanel();
  $('sessionSummary').classList.add('d-none');
  runCurrent();
}

// ---- Optional tail ("Session done — N reviews and M new words left today") ---

function hideTailPrompt() {
  const box = $('sessionTailPrompt');
  if (box) box.classList.add('d-none');
}

// Phrase like "6 reviews" / "1 new word" (the i18n bundle has no plural support).
function countPhrase(kind, n) {
  const fallback = kind === 'reviews' ? `${n} reviews` : `${n} new words`;
  return T(countKey(kind, n), { n }, fallback);
}

// Ask the server whether anything optional is left. The tail is computed live
// and only once every required non-test item is complete, so it is fetched here (at
// summary time) rather than carried on the initial load. Best-effort: a failure
// just leaves the plain summary.
async function offerTail({ fromEmpty = false } = {}) {
  if (session.tailDeclined) {
    renderExtraPanel();
    return;
  }
  const token = ++session._tailToken;
  let data;
  try {
    // The server only offers the tail once every required item is recorded
    // complete, so the completions still being saved go first.
    await settleSaves();
    const res = await window.authFetch(studySessionUrl());
    if (!res || !res.ok) {
      if (token === session._tailToken) renderExtraPanel();
      return;
    }
    const body = await res.json();
    data = body.data || body;
  } catch (e) {
    console.warn('Could not check for optional work:', e);
    if (token === session._tailToken) renderExtraPanel();
    return;
  }
  if (token !== session._tailToken) return;
  session.extraTail = data && data.tail ? data.tail : null;
  if (!hasTail(data)) {
    renderExtraPanel();
    return;
  }
  if (fromEmpty) showEmptyWithTail();
  renderTailPrompt(data);
  renderExtraPanel();
}

function renderTailPrompt(data) {
  const box = $('sessionTailPrompt');
  if (!box) return;
  const { reviews, words } = tailCounts(data.tail);
  const key = tailPromptKey(data.tail);
  if (!key) return;

  $('sessionTailMessage').textContent = T(
    key,
    { reviews: countPhrase('reviews', reviews), words: countPhrase('words', words) },
    'Session done — keep going?'
  );

  // Governor: say why new words are fewer / paused (only when it matters).
  const gKey = governorKey(data.governor);
  const gEl = $('sessionTailGovernor');
  if (gEl) {
    const overdue = (data.governor && data.governor.overdue_items) || 0;
    gEl.textContent = gKey ? T(gKey, { reviews: countPhrase('reviews', overdue) }, '') : '';
    gEl.classList.toggle('d-none', !gKey);
  }

  $('sessionTailKeepGoing').onclick = () => keepGoing(data.tail_queue);
  $('sessionTailDone').onclick = () => {
    session.tailDeclined = true;
    hideTailPrompt();
  };
  box.classList.remove('d-none');
}

// "Keep going": run this round's chunks through the normal runner. They are
// persisted through complete-block like any practice chunk (ids tail_maint_k /
// tail_acq_k), so they credit weekly progress without ever being required.
function keepGoing(tailQueue) {
  const { queue, firstIndex } = appendTailRound(session.queue, tailQueue);
  session.queue = queue;
  session.index = firstIndex;
  hideTailPrompt();
  $('sessionSummary').classList.add('d-none');
  runCurrent();
}

// ---- Practice extra rounds ("Keep practising", practice mode only) ----------

function hideExtraPanel() {
  const box = $('sessionExtraPanel');
  if (box) box.classList.add('d-none');
}

function renderExtraPanel() {
  const box = $('sessionExtraPanel');
  if (!box || !session.practiceOnly || session.extraDeclined) return;
  // Today's allotted new words come first; extra rounds are for after.
  if (newWordsPending()) return;
  // Re-rendered when the tail fetch lands (to refresh the quota warning); only
  // reset the controls on first show so a selection in progress is kept.
  if (box.classList.contains('d-none')) {
    const choice = normalizeExtraChoice(session.extraChoice);
    $('sessionExtraReviews').checked = choice.reviews;
    $('sessionExtraNewWords').value = String(choice.newWords);
  }

  const update = () => {
    const c = readExtraChoice();
    const beyond = extraBeyondQuota(c, session.extraTail);
    const warn = $('sessionExtraWarning');
    warn.textContent = beyond
      ? T(
          'session.extra.beyond_quota',
          { n: beyond },
          `${beyond} of these words go beyond today's goal — they add to your future reviews.`
        )
      : '';
    warn.classList.toggle('d-none', !beyond);
    $('sessionExtraStart').disabled = !isRunnableExtraChoice(c);
  };
  $('sessionExtraReviews').onchange = update;
  $('sessionExtraNewWords').onchange = update;
  $('sessionExtraNewWords').oninput = update;
  update();

  $('sessionExtraStart').onclick = () => startExtraRound(readExtraChoice());
  $('sessionExtraDone').onclick = () => {
    session.extraDeclined = true;
    hideExtraPanel();
  };
  box.classList.remove('d-none');
}

function readExtraChoice() {
  return normalizeExtraChoice({
    reviews: $('sessionExtraReviews').checked,
    newWords: $('sessionExtraNewWords').value,
  });
}

// One round through the normal runner; at its end showSummary() brings the
// learner back to this panel with the same choice pre-selected.
function startExtraRound(choice) {
  if (!isRunnableExtraChoice(choice)) return;
  session.extraChoice = choice;
  const last = [...session.queue].reverse().find((q) => q.is_extra);
  const exclude = (last && last.served_sense_ids) || [];
  session.extraRounds += 1;
  // Drop skipped (still incomplete) optional items, as appendTailRound does.
  const kept = session.queue.filter((q) => !(q.is_tail && !q.is_completed));
  session.queue = kept.concat([makeExtraItem(choice, session.extraRounds, exclude)]);
  session.index = kept.length;
  hideTailPrompt();
  hideExtraPanel();
  $('sessionSummary').classList.add('d-none');
  runCurrent();
}

function emptyMessage() {
  return session.practiceOnly
    ? T('session.empty_practice_page', null, 'No exercises due right now.')
    : T(
        'session.empty',
        null,
        'No session items for today. Check your Study Plan or browse tests.'
      );
}

// Practice mode with nothing required left and no new words waiting: the deep link starts the
// reviews round the extra-round panel would offer, once, instead of waiting for a click.
function startDeepLinkedReviews() {
  if (!session.extraDeepLink) return false;
  session.extraDeepLink = false;
  if (!session.practiceOnly || newWordsPending()) return false;
  const choice = normalizeExtraChoice({ reviews: true, newWords: 0 });
  if (!isRunnableExtraChoice(choice)) return false;
  $('sessionLoading').classList.add('d-none');
  $('sessionStart').classList.add('d-none');
  startExtraRound(choice);
  return true;
}

function showEmpty() {
  leaveRun();
  if (session.practiceOnly) {
    // Practice mode always has something to offer: open-ended extra rounds.
    $('sessionLoading').classList.add('d-none');
    if (startDeepLinkedReviews()) return;
    showEmptyWithTail();
    renderNewWordsPrompt();
    renderExtraPanel();
    offerTail();
    return;
  }
  $('sessionStart').classList.remove('d-none');
  $('sessionStart').classList.add('is-empty');
  $('sessionStartSummary').textContent = emptyMessage();
  $('sessionStartBtn').classList.add('d-none');
  paintDecor();
  // An empty required queue (e.g. a weekday-weight-0 day with reviews due) still
  // has optional work: offer the tail here too, not only from showSummary.
  offerTail({ fromEmpty: true });
}

// Empty required queue + optional work left: swap the empty card for the summary
// card (which hosts the tail prompt) showing the same empty message.
function showEmptyWithTail() {
  $('sessionStart').classList.add('d-none');
  $('sessionSummaryBody').innerHTML = `<p class="ld-muted mb-0">${escapeHtml(emptyMessage())}</p>`;
  const wrap = $('sessionResultsWrap');
  if (wrap) wrap.classList.add('d-none');
  $('sessionSummary').classList.remove('d-none');
  $('sessionSummary').classList.add('is-empty');
}

function showError(msg) {
  teardownPlayer();
  leaveRun();
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
