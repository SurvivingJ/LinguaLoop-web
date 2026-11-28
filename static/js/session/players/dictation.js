// static/js/session/players/dictation.js
// Dictation player. Used by the daily-session runner and by the standalone
// dictation page (static/js/pages/test-dictation.js). Renders into a provided
// container, scopes DOM lookups to it, and calls ctx.onComplete(result) on
// finish.
//
// Page-level options on ctx (all optional; the session runner passes none):
//   ready          promise awaited before the test is requested
//   audioPreload   preload value for the <audio>
//   backHref       adds a "Back" link to the footer and the error state
//   resultActions  (actionsEl, response, { slug, testData }) => void: fills the
//                  results card's actions instead of "Next" -> ctx.onComplete
//   pageHeader     true: the player also fills the task header's title,
//                  subtitle and seal (the session runner fills those itself)
// ctx.frame (optional, see session-frame): the task header.
//
// Layout (2026-11 redesign): one .ld-screen — the task (.ld-stage: audio card,
// text box) with Submit pinned in the .ld-dock; then the results in place of
// it (score, stats, diff) with their actions in the dock. Styles:
// static/css/redesign/tests.css (.dict-player).

const SPEED_OPTIONS = [1.0, 0.75, 0.5];

import {
  T,
  nativeName,
  escapeHtml,
  formatTime,
  showLoading as setLoading,
  showError as setError,
} from '../dom.js';
import { prefetchJson, takePrefetch, warmAudio, adoptAudio } from '../prefetch.js';

const t = (key, fallback) => T(key, null, fallback);

// Header seal per study language (the session runner's GLYPHS, for the page).
const SEALS = { zh: '写', ja: '書' };

/** Text for [data-t] nodes: the translation when the bundle has one, else the English in place. */
function localize(root) {
  root.querySelectorAll('[data-t]').forEach((el) => {
    if (!el.dataset.tEn) el.dataset.tEn = el.textContent;
    el.textContent = T(el.getAttribute('data-t'), null, el.dataset.tEn);
  });
  root.querySelectorAll('[data-t-aria]').forEach((el) => {
    const en = el.dataset.tAriaEn || el.getAttribute('aria-label') || '';
    if (!el.dataset.tAriaEn) el.dataset.tAriaEn = en;
    el.setAttribute('aria-label', T(el.getAttribute('data-t-aria'), null, en));
  });
}

const testUrl = (slug) => `/api/tests/test/${slug}?mode=dictation`;

/** Session prefetch hook: the test payload and its audio (static content). */
export async function prefetch(item) {
  if (!item || !item.slug) return { ok: false };
  const res = await prefetchJson(testUrl(item.slug));
  if (res.ok && res.data.test_data) res.audio = warmAudio(res.data.test_data.audio_url);
  return res;
}

export function mount(container, ctx) {
  const state = {
    slug: ctx.item.slug,
    testData: null,
    audioUrl: null,
    replayCount: 0,
    playbackRate: 1.0,
    speedIdx: 0,
    startTime: null,
    hasPlayed: false,
    isSubmitting: false,
    submitted: false,
    idempotencyKey: null,
  };

  const cleanup = [];
  const on = (el, ev, fn, opts) => {
    el.addEventListener(ev, fn, opts);
    cleanup.push(() => el.removeEventListener(ev, fn, opts));
  };
  const q = (id) => container.querySelector('#' + id);

  container.innerHTML = MARKUP;
  const frame = ctx.frame || null;
  if (frame) container.querySelector('.dict-player').classList.add('dict-player--framed');
  localize(container);
  let refreshSubmit = () => {};
  setupSkip();
  setupBack();
  init();

  return {
    destroy() {
      const a = q('audioElement');
      if (a) {
        try {
          a.pause();
        } catch (_) {}
      }
      cleanup.forEach((fn) => {
        try {
          fn();
        } catch (_) {}
      });
    },
  };

  async function init() {
    try {
      showLoading(true);
      if (!state.slug) throw new Error('No test slug');
      await ctx.ready;
      localize(container);
      state.idempotencyKey =
        window.crypto && crypto.randomUUID
          ? crypto.randomUUID()
          : '' + Date.now() + '-' + Math.random().toString(16).slice(2);

      await loadTestData();
      setupAudio();
      setupInputHandlers();

      q('dictationHeader').style.display = '';
      q('mainUi').style.display = 'block';
      q('dictActions').style.display = '';
      fillHeader();
      showLoading(false);
    } catch (err) {
      console.error('Dictation init error:', err);
      showError(err.message || 'Failed to load test');
      showLoading(false);
    }
  }

  async function loadTestData() {
    const pre = await takePrefetch(ctx.item);
    let data = pre && pre.data;
    if (pre) {
      state.warmAudio = pre.audio || null;
    } else {
      const resp = await window.authFetch(testUrl(state.slug));
      if (!resp.ok) throw new Error(`Failed to load test (HTTP ${resp.status})`);
      data = await resp.json();
    }
    state.testData = data.test_data;
    state.audioUrl = state.testData && state.testData.audio_url;
    if (!state.audioUrl) throw new Error(t('dictation.error.no_audio', 'This test has no audio.'));

    const titleEl = q('testTitle');
    if (titleEl && state.testData.title) titleEl.textContent = state.testData.title;
    const langEl = q('testLanguage');
    if (langEl)
      langEl.textContent =
        nativeName(state.testData.language) || state.testData.language_name || '';
    const code = langCode();
    if (code) q('dictationInput').setAttribute('lang', code);
  }

  function langCode() {
    const code = String((state.testData && state.testData.language) || '').toLowerCase();
    return window.LinguaLanguages.codeOf(code, code); // legacy 'cn' / 'jp' -> 'zh' / 'ja'
  }

  // Task header: the session runner fills title / subtitle / seal itself; a
  // standalone page asks for them (ctx.pageHeader).
  function fillHeader() {
    if (!frame || typeof frame.setHeader !== 'function' || !ctx.pageHeader) return;
    const type = t('dictation.badge', 'Dictation');
    frame.setHeader({
      title: (state.testData && state.testData.title) || type,
      subtitle: [q('testLanguage').textContent, type].filter(Boolean).join(' · '),
      glyph: SEALS[langCode()] || type.charAt(0),
      end: '',
    });
  }

  function setupAudio() {
    if (ctx.audioPreload) q('audioElement').preload = ctx.audioPreload;
    const audio = adoptAudio(q('audioElement'), state.warmAudio, state.audioUrl);
    audio.playbackRate = state.playbackRate;

    const playBtn = q('playBtn');
    const playIcon = () =>
      (playBtn.innerHTML = audio.paused
        ? '<i class="fas fa-play"></i>'
        : '<i class="fas fa-pause"></i>');

    on(playBtn, 'click', () => {
      if (state.submitted) return;
      if (audio.paused) {
        // A play only counts (and only unlocks Submit) once audio really
        // starts: a failed load used to count as a play and unlock Submit
        // with nothing heard, and said nothing about the failure.
        const started = audio.play();
        const counted = () => {
          state.replayCount += 1;
          state.hasPlayed = true;
          if (!state.startTime) state.startTime = Date.now();
          q('replayCount').textContent = state.replayCount;
          if (state.replayCount > 3) q('replayCounter').classList.add('warn');
          hideAudioError();
          refreshSubmit();
        };
        if (started && typeof started.then === 'function') {
          started.then(counted, () => showAudioError());
        } else {
          counted();
        }
      } else {
        audio.pause();
      }
      playIcon();
    });
    on(audio, 'error', () => {
      showAudioError();
      playIcon();
    });
    on(audio, 'ended', playIcon);
    on(audio, 'pause', playIcon);
    on(audio, 'play', playIcon);

    const speedBtn = q('speedBtn');
    const speedLbl = q('speedLabel');
    on(speedBtn, 'click', () => {
      state.speedIdx = (state.speedIdx + 1) % SPEED_OPTIONS.length;
      state.playbackRate = SPEED_OPTIONS[state.speedIdx];
      audio.playbackRate = state.playbackRate;
      speedLbl.textContent = state.playbackRate.toFixed(2).replace(/\.?0+$/, '') + 'x';
    });
  }

  function setupInputHandlers() {
    const input = q('dictationInput');
    const charCount = q('charCount');
    const submitBtn = q('submitBtn');

    refreshSubmit = () => {
      submitBtn.disabled = input.value.length === 0 || !state.hasPlayed || state.isSubmitting;
    };
    on(input, 'input', () => {
      charCount.textContent = input.value.length;
      refreshSubmit();
    });
    on(input, 'keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        if (!submitBtn.disabled) submit();
      }
    });
    on(submitBtn, 'click', submit);
  }

  async function submit() {
    if (state.isSubmitting || state.submitted) return;
    const input = q('dictationInput');
    const userTranscript = input.value.trim();
    if (!userTranscript) return;

    state.isSubmitting = true;
    const submitBtn = q('submitBtn');
    submitBtn.disabled = true;
    submitBtn.innerHTML =
      '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span><span>' +
      escapeHtml(t('dictation.submitting', 'Grading...')) +
      '</span>';

    const audio = q('audioElement');
    if (!audio.paused) audio.pause();
    input.disabled = true;

    const timeTaken = state.startTime ? Math.floor((Date.now() - state.startTime) / 1000) : 0;
    const startedAtIso = state.startTime ? new Date(state.startTime).toISOString() : null;
    const finishedAtIso = new Date().toISOString();

    try {
      const resp = await window.authFetch(`/api/tests/${state.slug}/submit-dictation`, {
        method: 'POST',
        body: JSON.stringify({
          user_transcript: userTranscript,
          replay_count: Math.max(1, state.replayCount),
          time_taken: timeTaken,
          idempotency_key: state.idempotencyKey,
          started_at: startedAtIso,
          finished_at: finishedAtIso,
        }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.result) throw new Error(data.error || 'Submit failed');
      state.submitted = true;
      showResults(data.result, timeTaken, data);
    } catch (err) {
      console.error('Dictation submit failed:', err);
      alert(t('dictation.error.submit_failed', 'Failed to submit dictation') + ': ' + err.message);
      state.isSubmitting = false;
      input.disabled = false;
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>' + escapeHtml(t('dictation.submit', 'Submit')) + '</span>';
    }
  }

  function showResults(result, timeSec, raw) {
    const accuracy = result.accuracy || 0;
    let grade = 'poor',
      label = t('dictation.grade.poor', 'Keep Practicing');
    if (accuracy >= 95) {
      grade = 'excellent';
      label = t('dictation.grade.excellent', 'Excellent!');
    } else if (accuracy >= 80) {
      grade = 'good';
      label = t('dictation.grade.good', 'Great Job!');
    } else if (accuracy >= 60) {
      grade = 'fair';
      label = t('dictation.grade.fair', 'Good Effort');
    }

    const timeStr = formatTime(timeSec);

    const eloChange = (result.user_elo_change && result.user_elo_change.change) || 0;
    const eloSign = eloChange >= 0 ? '+' : '';
    const eloCls = eloChange >= 0 ? 'text-success' : 'text-danger';

    const replayFactor = result.replay_factor;
    const factorBadge =
      replayFactor !== null && replayFactor !== undefined && replayFactor < 1.0
        ? `<span class="ld-tag ld-tag--warn" title="${escapeHtml(t('dictation.replay_penalty', 'Replay penalty applied'))}">${replayFactor.toFixed(2)}× ELO</span>`
        : '';

    const diffHtml = renderDiff(Array.isArray(result.diff) ? result.diff : []);

    const lang = langCode();
    const html = `
            <div class="ld-stage dict-results-card">
                <div class="dict-score dict-results-headline">
                    <span class="dict-accuracy ld-num ${grade}">${accuracy.toFixed(1)}%</span>
                    <div><h2 class="dict-grade mb-0">${escapeHtml(label)}</h2>
                    <p class="ld-small ld-muted mb-0">${escapeHtml(t('dictation.result.accuracy', 'Word Accuracy'))}</p></div>
                </div>
                <div class="ld-stats ld-stats--four dict-stats-grid">
                    <div class="ld-stat dict-stat-box"><div class="ld-stat__n ld-num dict-stat-value">${result.word_correct}/${result.word_total}</div><small class="dict-stat-label">${escapeHtml(t('dictation.stat.words', 'Words'))}</small></div>
                    <div class="ld-stat dict-stat-box"><div class="ld-stat__n ld-num dict-stat-value">${result.replay_count}</div><small class="dict-stat-label">${escapeHtml(t('dictation.replays', 'Plays'))}</small></div>
                    <div class="ld-stat dict-stat-box"><div class="ld-stat__n ld-num dict-stat-value">${timeStr}</div><small class="dict-stat-label">${escapeHtml(t('dictation.result.time', 'Time'))}</small></div>
                    <div class="ld-stat dict-stat-box"><div class="ld-stat__n ld-num dict-stat-value ${eloCls}">${eloSign}${eloChange}</div><small class="dict-stat-label">ELO${factorBadge}</small></div>
                </div>
                <div class="dict-legend">
                    <span class="dict-word dict-word-equal">${escapeHtml(t('dictation.result.legend.correct', 'Correct'))}</span>
                    <span class="dict-word dict-word-replace">${escapeHtml(t('dictation.result.legend.wrong', 'Wrong'))}</span>
                    <span class="dict-word dict-word-delete">${escapeHtml(t('dictation.result.legend.missing', 'Missing'))}</span>
                    <span class="dict-word dict-word-insert">${escapeHtml(t('dictation.result.legend.extra', 'Extra'))}</span>
                </div>
                <div class="ld-card"><div class="dict-diff"${lang ? ` lang="${escapeHtml(lang)}"` : ''}>${diffHtml}</div></div>
            </div>
            <div class="ld-dock dict-results-dock">
                <div class="dict-results-actions">
                    <button class="ld-btn" type="button" data-session-next>
                        <span>${escapeHtml(t('session.next_item', 'Next'))}</span><i class="fas fa-arrow-right ms-1" aria-hidden="true"></i>
                    </button>
                </div>
            </div>`;

    // The results take the task's place (stage + dock), under the same header.
    const overlay = q('resultsOverlay');
    overlay.innerHTML = html;
    q('mainUi').style.display = 'none';
    q('dictActions').style.display = 'none';
    overlay.style.display = '';
    if (typeof ctx.resultActions === 'function') {
      const actions = overlay.querySelector('.dict-results-actions');
      actions.innerHTML = '';
      ctx.resultActions(actions, raw || result, { slug: state.slug, testData: state.testData });
    } else {
      const nextBtn = overlay.querySelector('[data-session-next]');
      if (nextBtn) nextBtn.onclick = () => ctx.onComplete(raw || result);
    }
    const stage = overlay.querySelector('.ld-stage');
    if (stage) stage.scrollTop = 0;
  }

  function renderDiff(diff) {
    const parts = [];
    for (const d of diff) {
      const op = d.op;
      const correct = escapeHtml(d.correct || '');
      const user = escapeHtml(d.user || '');
      if (op === 'equal') {
        parts.push(`<span class="dict-word dict-word-equal">${correct}</span>`);
      } else if (op === 'replace') {
        if (d.is_correct) {
          parts.push(`<span class="dict-word dict-word-equal" title="≈ ${user}">${correct}</span>`);
        } else {
          parts.push(
            `<span class="dict-word dict-word-replace" title="${t('dictation.your_diff', 'Your transcript')}: ${user}">${correct}</span>`
          );
        }
      } else if (op === 'delete') {
        parts.push(`<span class="dict-word dict-word-delete">${correct}</span>`);
      } else if (op === 'insert') {
        parts.push(`<span class="dict-word dict-word-insert">${user}</span>`);
      }
    }
    return parts.join(' ');
  }

  function showLoading(show) {
    setLoading(container, show);
  }

  function showAudioError() {
    const box = q('audioError');
    if (!box) return;
    box.style.display = 'block';
  }

  function hideAudioError() {
    const box = q('audioError');
    if (box) box.style.display = 'none';
  }

  function setupSkip() {
    // In the session runner a learner can always move on: an item skipped
    // stays incomplete and comes back on resume (controller onItemSkip).
    const canSkip = typeof ctx.onSkip === 'function';
    container.querySelectorAll('[data-dict-skip]').forEach((b) => {
      b.style.display = canSkip ? '' : 'none';
      if (canSkip) on(b, 'click', () => ctx.onSkip());
    });
    const retry = q('audioRetry');
    if (retry) {
      on(retry, 'click', () => {
        hideAudioError();
        const audio = q('audioElement');
        audio.load();
      });
    }
  }

  function setupBack() {
    if (!ctx.backHref) return;
    const link = (cls, gap) => {
      const a = document.createElement('a');
      a.href = ctx.backHref;
      a.className = cls;
      a.innerHTML = `<i class="fas fa-arrow-left ${gap}" aria-hidden="true"></i><span data-i18n="test.back_to_tests">Back</span>`;
      return a;
    };
    q('errorState')
      .querySelector('.alert')
      .appendChild(link('ld-btn ld-btn--sm btn-danger', 'me-2'));
    container
      .querySelector('.dict-actions-row')
      .prepend(link('ld-btn ld-btn--ghost dict-back', 'me-1'));
  }

  function showError(msg) {
    setError(container, msg, ['dictationHeader', 'mainUi', 'dictActions']);
  }
}

// ========================================================================
// MARKUP — one .ld-screen: the task (#mainUi stage + #dictActions dock), and
// the results (#resultsOverlay: stage + dock) that replace it. Styles live in
// static/css/redesign/tests.css (.dict-player), loaded on every page.
// ========================================================================
const MARKUP = `
<div class="ld-screen dict-player">
<div id="loadingOverlay" class="loading-overlay" style="display:none;">
    <div class="loading-spinner" role="status"><div class="spinner-icon"></div><p class="mb-0" data-i18n="dictation.loading">Loading...</p></div>
</div>

<div id="errorState" class="ld-stage" style="display:none;">
    <div class="alert alert-danger ld-col" role="alert">
        <h2 class="ld-h2 mb-0"><i class="fas fa-exclamation-triangle me-2" aria-hidden="true"></i><span data-i18n="dictation.error.title">Error</span></h2>
        <p id="errorMessage" class="mb-0"></p>
        <button class="ld-btn ld-btn--sm ld-btn--ghost" type="button" data-dict-skip data-i18n="session.skip_for_now">Skip for now</button>
    </div>
</div>

<div class="dict-main" id="mainUi" style="display:none;">
<div class="ld-stage dict-stage">
    <div class="dict-head" id="dictationHeader" style="display:none;">
        <h1 class="ld-h2 mb-0"><span id="testTitle">Dictation</span></h1>
        <div class="ld-wrap"><span class="ld-tag" id="testLanguage"></span><span class="ld-tag ld-tag--brand" data-i18n="dictation.badge">Dictation</span></div>
    </div>
    <div class="dict-audio dict-audio-card">
        <div class="dict-audio-row">
            <button id="playBtn" class="dict-play-btn" type="button" aria-label="Play" data-t-aria="test.play_pause"><i class="fas fa-play" aria-hidden="true"></i></button>
            <div class="dict-replay-counter ld-num" id="replayCounter"><span data-i18n="dictation.replays">Plays</span>: <span id="replayCount">0</span></div>
            <button id="speedBtn" class="ld-chip ld-num dict-speed-btn" type="button" aria-label="Playback speed" data-t-aria="test.playback_speed"><i class="bi bi-speedometer2" aria-hidden="true"></i><span id="speedLabel">1.0x</span></button>
        </div>
        <div id="audioError" class="ld-note ld-note--bad dict-audio-error" role="alert" style="display:none;">
            <p class="mb-0" data-i18n="dictation.audio_error">The audio couldn’t load. Check your connection and try again, or skip this one for now.</p>
            <button id="audioRetry" class="ld-btn ld-btn--sm ld-btn--ghost" type="button" data-i18n="dictation.retry">Retry</button>
            <button class="ld-link ld-link--quiet" type="button" data-dict-skip data-i18n="session.skip_for_now">Skip for now</button>
        </div>
        <audio id="audioElement" preload="auto"></audio>
    </div>
    <div class="dict-input-card ld-col">
        <label class="ld-eyebrow" for="dictationInput" data-i18n="test.type_what_you_hear">Type what you hear</label>
        <textarea id="dictationInput" class="dict-input" rows="5" data-i18n-placeholder="test.dictation_placeholder" placeholder="Start typing the text you hear from the audio..." maxlength="5000" autocomplete="off" autocorrect="off" spellcheck="false"></textarea>
        <div class="dict-char-count ld-num"><span id="charCount">0</span> / 5000</div>
    </div>
    <p class="ld-hint mb-0" data-t="dictation.submit_hint">Submit unlocks once the audio has played and you have typed something.</p>
</div>
</div>

<div class="ld-dock dict-actions" id="dictActions" style="display:none;">
    <div class="dict-actions-row">
        <button id="submitBtn" class="ld-btn dict-submit-btn" type="button" disabled><span data-i18n="dictation.submit">Submit</span></button>
    </div>
    <div class="dict-skip-row"><button class="ld-link ld-link--quiet" type="button" data-dict-skip data-i18n="session.skip_for_now">Skip for now</button></div>
</div>

<div id="resultsOverlay" class="ld-screen dict-results" style="display:none;"></div>
</div>
`;
