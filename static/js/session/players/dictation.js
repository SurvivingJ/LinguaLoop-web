// static/js/session/players/dictation.js
// Dictation player for the daily-session runner. Ported from
// templates/test_dictation.html. Renders into a provided container, scopes DOM
// lookups to it, and calls ctx.onComplete(result) on finish instead of linking
// back to /tests.

const SPEED_OPTIONS = [1.0, 0.75, 0.5];

const t = (key, fallback) => {
  if (window.LinguaI18n && typeof LinguaI18n.t === 'function') {
    const v = LinguaI18n.t(key);
    if (v && v !== key) return v;
  }
  return fallback;
};

const nativeName = (code) =>
  (window.LinguaMetadata && LinguaMetadata.getNativeName && LinguaMetadata.getNativeName(code)) ||
  (code ? String(code).toUpperCase() : '');

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
      state.idempotencyKey =
        window.crypto && crypto.randomUUID
          ? crypto.randomUUID()
          : '' + Date.now() + '-' + Math.random().toString(16).slice(2);

      await loadTestData();
      setupAudio();
      setupInputHandlers();

      q('dictationHeader').style.display = 'block';
      q('mainUi').style.display = 'block';
      q('dictActions').style.display = 'block';
      showLoading(false);
    } catch (err) {
      console.error('Dictation init error:', err);
      showError(err.message || 'Failed to load test');
      showLoading(false);
    }
  }

  async function loadTestData() {
    const resp = await window.authFetch(`/api/tests/test/${state.slug}?mode=dictation`);
    if (!resp.ok) throw new Error(`Failed to load test (HTTP ${resp.status})`);
    const data = await resp.json();
    state.testData = data.test_data;
    state.audioUrl = state.testData && state.testData.audio_url;
    if (!state.audioUrl) throw new Error(t('dictation.error.no_audio', 'This test has no audio.'));

    const titleEl = q('testTitle');
    if (titleEl && state.testData.title) titleEl.textContent = state.testData.title;
    const langEl = q('testLanguage');
    if (langEl)
      langEl.textContent =
        nativeName(state.testData.language) || state.testData.language_name || '';
  }

  function setupAudio() {
    const audio = q('audioElement');
    audio.src = state.audioUrl;
    audio.playbackRate = state.playbackRate;

    const playBtn = q('playBtn');
    const playIcon = () =>
      (playBtn.innerHTML = audio.paused
        ? '<i class="fas fa-play"></i>'
        : '<i class="fas fa-pause"></i>');

    on(playBtn, 'click', () => {
      if (state.submitted) return;
      if (audio.paused) {
        state.replayCount += 1;
        state.hasPlayed = true;
        if (!state.startTime) state.startTime = Date.now();
        q('replayCount').textContent = state.replayCount;
        if (state.replayCount > 3) q('replayCounter').classList.add('warn');
        audio.play();
      } else {
        audio.pause();
      }
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

    on(input, 'input', () => {
      const len = input.value.length;
      charCount.textContent = len;
      submitBtn.disabled = len === 0 || !state.hasPlayed || state.isSubmitting;
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
      '<span class="spinner-icon" style="width:16px;height:16px;border-width:2px;display:inline-block;vertical-align:middle;margin:0 8px 0 0;"></span><span>' +
      t('dictation.submitting', 'Grading...') +
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
      submitBtn.innerHTML = '<span>' + t('dictation.submit', 'Submit') + '</span>';
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

    const mins = Math.floor(timeSec / 60);
    const secs = timeSec % 60;
    const timeStr = `${mins}:${secs.toString().padStart(2, '0')}`;

    const eloChange = (result.user_elo_change && result.user_elo_change.change) || 0;
    const eloSign = eloChange >= 0 ? '+' : '';
    const eloCls = eloChange >= 0 ? 'text-success' : 'text-danger';

    const replayFactor = result.replay_factor;
    const factorBadge =
      replayFactor !== null && replayFactor !== undefined && replayFactor < 1.0
        ? `<span class="badge bg-warning text-dark ms-2" title="Replay penalty applied">${replayFactor.toFixed(2)}× ELO</span>`
        : '';

    const diffHtml = renderDiff(Array.isArray(result.diff) ? result.diff : []);

    const html = `
            <div class="dict-results-card">
                <div class="dict-results-headline">
                    <div class="dict-accuracy ${grade}">${accuracy.toFixed(1)}%</div>
                    <h2 class="h4">${label}</h2>
                    <p class="text-muted mb-0">${t('dictation.result.accuracy', 'Word Accuracy')}</p>
                </div>
                <div class="dict-stats-grid">
                    <div class="dict-stat-box"><div class="dict-stat-value">${result.word_correct}/${result.word_total}</div><div class="dict-stat-label">${t('dictation.stat.words', 'Words')}</div></div>
                    <div class="dict-stat-box"><div class="dict-stat-value">${result.replay_count}</div><div class="dict-stat-label">${t('dictation.replays', 'Plays')}</div></div>
                    <div class="dict-stat-box"><div class="dict-stat-value">${timeStr}</div><div class="dict-stat-label">${t('dictation.result.time', 'Time')}</div></div>
                    <div class="dict-stat-box"><div class="dict-stat-value ${eloCls}">${eloSign}${eloChange}${factorBadge}</div><div class="dict-stat-label">ELO</div></div>
                </div>
                <div class="dict-legend">
                    <span><span class="dict-word dict-word-equal">${t('dictation.result.legend.correct', 'Correct')}</span></span>
                    <span><span class="dict-word dict-word-replace">${t('dictation.result.legend.wrong', 'Wrong')}</span></span>
                    <span><span class="dict-word dict-word-delete">${t('dictation.result.legend.missing', 'Missing')}</span></span>
                    <span><span class="dict-word dict-word-insert">${t('dictation.result.legend.extra', 'Extra')}</span></span>
                </div>
                <div class="dict-diff">${diffHtml}</div>
                <div class="dict-results-actions">
                    <button class="btn btn-primary" type="button" data-session-next>
                        <span>${t('session.next_item', 'Next')}</span><i class="fas fa-arrow-right ms-1"></i>
                    </button>
                </div>
            </div>`;

    const overlay = q('resultsOverlay');
    overlay.innerHTML = html;
    overlay.style.display = 'block';
    const nextBtn = overlay.querySelector('[data-session-next]');
    if (nextBtn) nextBtn.onclick = () => ctx.onComplete(raw || result);
    window.scrollTo(0, 0);
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

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showLoading(show) {
    const el = q('loadingOverlay');
    if (el) el.style.display = show ? 'flex' : 'none';
  }

  function showError(msg) {
    const err = q('errorState');
    if (err) {
      err.style.display = 'block';
      q('errorMessage').textContent = msg;
    }
    ['dictationHeader', 'mainUi', 'dictActions'].forEach((id) => {
      const el = q(id);
      if (el) el.style.display = 'none';
    });
  }
}

// ========================================================================
// MARKUP — includes scoped styles so the player is self-contained in /session
// ========================================================================
const MARKUP = `
<style>
    .dictation-header { background: var(--bg-surface); border-bottom: 2px solid var(--border-default); position: sticky; top: 0; z-index: 40; box-shadow: var(--shadow-sm); }
    .dictation-container { max-width: 720px; margin: 0 auto; padding: 24px 20px 120px; }
    .dict-audio-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px; margin-bottom: 20px; text-align: center; }
    .dict-audio-row { display: flex; align-items: center; justify-content: center; gap: 16px; flex-wrap: wrap; }
    .dict-play-btn { width: 64px; height: 64px; border-radius: 50%; background: var(--primary); color: #fff; border: none; font-size: 22px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; transition: background .15s ease, transform .1s ease; }
    .dict-play-btn:hover { background: var(--primary-hover); }
    .dict-play-btn:active { transform: scale(.95); }
    .dict-play-btn:disabled { background: var(--slate-400); cursor: not-allowed; }
    .dict-speed-btn { padding: 8px 14px; border: 2px solid var(--border-strong); border-radius: 8px; background: var(--bg-surface); font-weight: 600; cursor: pointer; transition: border-color .15s ease; }
    .dict-speed-btn:hover { border-color: var(--primary); color: var(--primary); }
    .dict-replay-counter { font-size: 14px; color: var(--text-muted); margin-top: 12px; }
    .dict-replay-counter.warn { color: var(--warning); font-weight: 600; }
    .dict-input-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 12px; padding: 20px; }
    .dict-input { width: 100%; min-height: 200px; padding: 14px; border: 2px solid var(--border-strong); border-radius: 8px; font-size: 16px; line-height: 1.6; font-family: inherit; resize: vertical; background: var(--bg-body); color: var(--text-primary); }
    .dict-input:focus { outline: none; border-color: var(--primary); }
    .dict-input:disabled { background: var(--slate-100); color: var(--text-muted); }
    .dict-char-count { margin-top: 6px; font-size: 12px; color: var(--text-muted); text-align: right; }
    .dict-actions { position: fixed; bottom: 0; left: 0; right: 0; background: var(--bg-surface); border-top: 1px solid var(--border-default); padding: 14px 20px; z-index: 50; box-shadow: 0 -2px 8px rgba(0,0,0,.04); }
    .dict-actions-row { max-width: 720px; margin: 0 auto; display: flex; gap: 12px; align-items: center; }
    .dict-submit-btn { flex: 1; height: 52px; font-size: 16px; font-weight: 600; background: var(--primary); color: #fff; border: none; border-radius: 10px; cursor: pointer; transition: background .15s ease; }
    .dict-submit-btn:hover:not(:disabled) { background: var(--primary-hover); }
    .dict-submit-btn:disabled { background: var(--slate-400); cursor: not-allowed; }
    .dict-results-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--bg-body); z-index: 60; overflow-y: auto; padding: 20px; }
    .dict-results-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 16px; box-shadow: var(--shadow-lg); padding: 28px; max-width: 720px; margin: 0 auto; }
    .dict-results-headline { text-align: center; margin-bottom: 16px; }
    .dict-accuracy { font-size: 3.5rem; font-weight: 800; margin: 8px 0; }
    .dict-accuracy.excellent { color: var(--success); }
    .dict-accuracy.good { color: #F57C00; }
    .dict-accuracy.fair { color: var(--warning); }
    .dict-accuracy.poor { color: var(--danger); }
    .dict-stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; margin: 20px 0; }
    .dict-stat-box { background: var(--bg-muted); padding: 12px; border-radius: 8px; text-align: center; }
    .dict-stat-value { font-size: 1.3rem; font-weight: 700; }
    .dict-stat-label { font-size: .78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; }
    .dict-diff { background: var(--bg-body); border: 1px solid var(--border-default); border-radius: 8px; padding: 16px; line-height: 2; font-size: 16px; margin: 12px 0 20px; }
    .dict-word { display: inline-block; padding: 2px 4px; margin: 2px 1px; border-radius: 4px; }
    .dict-word-equal { color: var(--text-primary); }
    .dict-word-replace { color: var(--danger); text-decoration: line-through; background: rgba(229,57,53,.08); }
    .dict-word-delete { background: rgba(245,124,0,.10); color: #F57C00; text-decoration: underline dotted; }
    .dict-word-insert { color: var(--text-muted); font-style: italic; opacity: .7; }
    .dict-legend { display: flex; flex-wrap: wrap; gap: 12px; font-size: 13px; margin-bottom: 12px; color: var(--text-muted); }
    .dict-legend .dict-word { font-size: 13px; padding: 1px 6px; margin: 0; }
    .dict-results-actions { display: flex; gap: 12px; margin-top: 16px; }
    .dict-results-actions .btn { flex: 1; }
    .loading-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15,23,42,.4); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; z-index: 9999; }
    .loading-spinner { background: var(--bg-surface); padding: 24px 36px; border-radius: 12px; box-shadow: var(--shadow-lg); text-align: center; }
    .spinner-icon { border: 3px solid var(--border-default); border-top-color: var(--primary); border-radius: 50%; width: 36px; height: 36px; animation: spin .8s linear infinite; margin: 0 auto 10px; }
    @keyframes spin { to { transform: rotate(360deg); } }
</style>

<div id="loadingOverlay" class="loading-overlay" style="display:none;">
    <div class="loading-spinner"><div class="spinner-icon"></div><p class="mb-0" data-i18n="dictation.loading">Loading...</p></div>
</div>

<div id="errorState" class="container py-5" style="display:none;">
    <div class="alert alert-danger">
        <h2 class="h5"><i class="fas fa-exclamation-triangle me-2"></i><span data-i18n="dictation.error.title">Error</span></h2>
        <p id="errorMessage" class="mb-2"></p>
    </div>
</div>

<div class="dictation-header" id="dictationHeader" style="display:none;">
    <div class="container py-3">
        <div class="row align-items-center">
            <div class="col"><h1 class="mb-0 h5"><i class="bi bi-keyboard text-primary me-2"></i><span id="testTitle">Dictation</span></h1></div>
            <div class="col-auto"><span class="badge bg-primary me-2" id="testLanguage"></span><span class="badge bg-info" data-i18n="dictation.badge">Dictation</span></div>
        </div>
    </div>
</div>

<div class="dictation-container" id="mainUi" style="display:none;">
    <div class="dict-audio-card">
        <div class="dict-audio-row">
            <button id="playBtn" class="dict-play-btn" type="button" aria-label="Play"><i class="fas fa-play"></i></button>
            <button id="speedBtn" class="dict-speed-btn" type="button"><i class="bi bi-speedometer2 me-1"></i><span id="speedLabel">1.0x</span></button>
        </div>
        <div class="dict-replay-counter" id="replayCounter"><span data-i18n="dictation.replays">Plays</span>: <span id="replayCount">0</span></div>
        <audio id="audioElement" preload="metadata"></audio>
    </div>
    <div class="dict-input-card">
        <h2 class="mb-2 h6"><i class="bi bi-pencil-square text-primary me-2"></i><span data-i18n="test.type_what_you_hear">Type what you hear</span></h2>
        <textarea id="dictationInput" class="dict-input" data-i18n-placeholder="test.dictation_placeholder" placeholder="Start typing the text you hear from the audio..." maxlength="5000" autocomplete="off" autocorrect="off" spellcheck="false"></textarea>
        <div class="dict-char-count"><span id="charCount">0</span> / 5000</div>
    </div>
</div>

<div class="dict-actions" id="dictActions" style="display:none;">
    <div class="dict-actions-row">
        <button id="submitBtn" class="dict-submit-btn" type="button" disabled><span data-i18n="dictation.submit">Submit</span></button>
    </div>
</div>

<div id="resultsOverlay" class="dict-results-overlay" style="display:none;"></div>
`;
