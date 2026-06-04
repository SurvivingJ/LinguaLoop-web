// static/js/session/players/pinyin.js
// Pinyin tone-trainer player for the daily-session runner. Ported from
// templates/test_pinyin.html. Container-scoped, leak-free teardown (document
// keydown + timer are tracked), error-modal buttons wired via listeners (no
// window globals), and ctx.onComplete() on finish instead of linking to /tests.

const TONE_NAMES = {
  1: '1st (flat)',
  2: '2nd (rising)',
  3: '3rd (dip)',
  4: '4th (falling)',
  5: 'Neutral',
};

const T = (key, params, fallback) =>
  window.LinguaI18n && typeof LinguaI18n.t === 'function'
    ? LinguaI18n.t(key, params) || fallback || key
    : fallback || key;

const nativeName = (code) =>
  (window.LinguaMetadata && LinguaMetadata.getNativeName && LinguaMetadata.getNativeName(code)) ||
  (code ? String(code).toUpperCase() : '');

function escapeHtml(text) {
  if (text == null) return '';
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

function applyToneMark(syllable, tone) {
  const TONE_TABLE = {
    a: ['ā', 'á', 'ǎ', 'à'],
    e: ['ē', 'é', 'ě', 'è'],
    i: ['ī', 'í', 'ǐ', 'ì'],
    o: ['ō', 'ó', 'ǒ', 'ò'],
    u: ['ū', 'ú', 'ǔ', 'ù'],
    ü: ['ǖ', 'ǘ', 'ǚ', 'ǜ'],
    v: ['ǖ', 'ǘ', 'ǚ', 'ǜ'],
  };
  if (tone < 1 || tone > 4) return syllable.replace(/v/g, 'ü');
  const idx = tone - 1;
  if (syllable.includes('a')) return syllable.replace('a', TONE_TABLE['a'][idx]);
  if (syllable.includes('e')) return syllable.replace('e', TONE_TABLE['e'][idx]);
  if (syllable.includes('ou')) return syllable.replace('o', TONE_TABLE['o'][idx]);
  for (let i = syllable.length - 1; i >= 0; i--) {
    const ch = syllable[i];
    if (TONE_TABLE[ch]) return syllable.slice(0, i) + TONE_TABLE[ch][idx] + syllable.slice(i + 1);
  }
  return syllable.replace(/v/g, 'ü');
}

export function mount(container, ctx) {
  const state = {
    slug: ctx.item.slug,
    testData: null,
    allTokens: [],
    playableTokens: [],
    playableIndices: [],
    currentIndex: 0,
    correctCount: 0,
    errorCount: 0,
    errors: [],
    startTime: null,
    timerInterval: null,
    isComplete: false,
    isPaused: false,
  };

  const cleanup = [];
  const on = (el, ev, fn, opts) => {
    el.addEventListener(ev, fn, opts);
    cleanup.push(() => el.removeEventListener(ev, fn, opts));
  };
  const q = (id) => container.querySelector('#' + id);
  const qs = (sel) => container.querySelector(sel);

  container.innerHTML = MARKUP;
  init();

  return {
    destroy() {
      if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
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
      await loadTestData();
      renderPassage();
      setupInputHandlers();
      startTimer();
      q('pinyinHeader').style.display = 'block';
      q('passageContainer').style.display = 'block';
      q('controlsHint').style.display = 'block';
      q('touchArea').style.display = 'block';
      highlightCurrent();
      showLoading(false);
    } catch (err) {
      console.error('Pinyin init error:', err);
      showError(err.message);
      showLoading(false);
    }
  }

  async function loadTestData() {
    const resp = await window.authFetch(`/api/tests/test/${state.slug}`);
    if (!resp.ok)
      throw new Error(T('pinyin.error.load_failed', { status: resp.statusText }, 'Failed to load'));
    const data = await resp.json();
    state.testData = data.test_data;
    if (!data.pinyin_payload || data.pinyin_payload.length === 0) {
      throw new Error(T('pinyin.error.no_data', null, 'No pinyin data for this test.'));
    }
    state.allTokens = data.pinyin_payload;
    state.allTokens.forEach((tok, i) => {
      if (!tok.is_punctuation) {
        state.playableIndices.push(i);
        state.playableTokens.push(tok);
      }
    });
    if (state.playableTokens.length === 0) {
      throw new Error(T('pinyin.error.no_chars', null, 'No characters to play.'));
    }
    q('testTitle').textContent =
      state.testData.title || T('pinyin.title', null, 'Pinyin Tone Trainer');
    q('testLanguage').textContent = nativeName(state.testData.language) || 'Chinese';
  }

  function renderPassage() {
    const grid = q('passageGrid');
    grid.innerHTML = '';
    state.allTokens.forEach((token, idx) => {
      const el = document.createElement('span');
      el.className = 'char-token';
      el.dataset.index = idx;
      if (token.is_punctuation) {
        el.classList.add('punctuation');
        el.innerHTML = `<span class="char-display">${escapeHtml(token.char)}</span>`;
      } else {
        el.classList.add('upcoming');
        el.innerHTML = `<span class="char-display">${escapeHtml(token.char)}</span><span class="char-pinyin">&nbsp;</span>`;
      }
      grid.appendChild(el);
    });
  }

  function highlightCurrent() {
    if (state.isComplete) return;
    const prev = qs('.char-token.current');
    if (prev) prev.classList.remove('current');
    const allIdx = state.playableIndices[state.currentIndex];
    const el = qs(`.char-token[data-index="${allIdx}"]`);
    if (el) {
      el.classList.remove('upcoming');
      el.classList.add('current');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    updateProgress();
  }

  function colorChar(playableIdx, tone) {
    const allIdx = state.playableIndices[playableIdx];
    const el = qs(`.char-token[data-index="${allIdx}"]`);
    const token = state.allTokens[allIdx];
    if (el) {
      el.classList.remove('current', 'upcoming');
      el.classList.add('completed', `tone-${tone}`);
      const pinyinEl = el.querySelector('.char-pinyin');
      if (pinyinEl) pinyinEl.textContent = applyToneMark(token.pinyin_text, token.context_tone);
      el.classList.add('correct-flash');
      setTimeout(() => el.classList.remove('correct-flash'), 200);
    }
  }

  function flashError(playableIdx) {
    const allIdx = state.playableIndices[playableIdx];
    const el = qs(`.char-token[data-index="${allIdx}"]`);
    if (el) {
      el.classList.add('error-flash');
      setTimeout(() => el.classList.remove('error-flash'), 300);
    }
  }

  function updateProgress() {
    const total = state.playableTokens.length;
    const pct = total > 0 ? (state.currentIndex / total) * 100 : 0;
    q('progressFill').style.width = pct + '%';
  }

  function handleToneInput(guessedTone) {
    if (state.isComplete || state.isPaused) return;
    const token = state.playableTokens[state.currentIndex];
    if (!token) return;
    if (guessedTone === token.context_tone) {
      colorChar(state.currentIndex, token.context_tone);
      state.correctCount++;
      state.currentIndex++;
      if (state.currentIndex >= state.playableTokens.length) completeGame();
      else highlightCurrent();
    } else {
      state.errorCount++;
      flashError(state.currentIndex);
      state.errors.push({
        char: token.char,
        word: token.word,
        pinyin: token.pinyin_text,
        expected: token.context_tone,
        guessed: guessedTone,
        is_sandhi: token.is_sandhi,
        sandhi_rule: token.sandhi_rule,
      });
      showErrorModal(token, guessedTone);
    }
  }

  function setupInputHandlers() {
    on(document, 'keydown', (e) => {
      const map = { ArrowRight: 1, ArrowUp: 2, ArrowLeft: 3, ArrowDown: 4, ' ': 5 };
      if (map[e.key] !== undefined) {
        e.preventDefault();
        handleToneInput(map[e.key]);
      }
      if (e.key === 'Enter' && state.isPaused) dismissErrorModal();
    });

    const touchArea = q('touchArea');
    let startX, startY, startTime;
    on(
      touchArea,
      'touchstart',
      (e) => {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        startTime = Date.now();
      },
      { passive: true }
    );
    on(
      touchArea,
      'touchend',
      (e) => {
        if (startX === undefined) return;
        const dx = e.changedTouches[0].clientX - startX;
        const dy = e.changedTouches[0].clientY - startY;
        const absDx = Math.abs(dx),
          absDy = Math.abs(dy);
        const elapsed = Date.now() - startTime;
        const threshold = 30;
        if (absDx < threshold && absDy < threshold && elapsed < 300) handleToneInput(5);
        else if (absDx > absDy) handleToneInput(dx > 0 ? 1 : 3);
        else handleToneInput(dy < 0 ? 2 : 4);
        startX = startY = undefined;
      },
      { passive: true }
    );
    on(
      touchArea,
      'touchmove',
      (e) => {
        e.preventDefault();
      },
      { passive: false }
    );
  }

  function showErrorModal(token, guessedTone) {
    state.isPaused = true;
    const toneColor = (tn) => `var(--tone-${tn})`;
    let sandhiHtml = '';
    if (token.is_sandhi && token.sandhi_rule) {
      sandhiHtml = `<div class="sandhi-explanation"><strong><i class="bi bi-info-circle me-1"></i>${T('pinyin.sandhi_rule', null, 'Tone sandhi')}</strong><br>${escapeHtml(token.sandhi_rule)}</div>`;
    }
    const html = `
            <div class="error-backdrop" data-pinyin-dismiss></div>
            <div class="error-modal">
                <div class="error-char" style="color: ${toneColor(token.context_tone)}">${escapeHtml(token.char)}</div>
                <div class="error-pinyin">${escapeHtml(applyToneMark(token.pinyin_text, token.context_tone))}<span style="color: var(--text-muted); margin-left: 4px;">(${escapeHtml(token.word)})</span></div>
                <div class="error-tones">
                    <div class="tone-label"><div class="tone-num" style="color: ${toneColor(guessedTone)}">${guessedTone}</div><div class="tone-desc">${T('pinyin.your_answer', null, 'Your answer')}</div></div>
                    <div style="font-size: 1.5rem; color: var(--text-muted); align-self: center;"><i class="bi bi-arrow-right"></i></div>
                    <div class="tone-label"><div class="tone-num" style="color: ${toneColor(token.context_tone)}">${token.context_tone}</div><div class="tone-desc">${T('pinyin.correct', null, 'Correct')}</div></div>
                </div>
                ${sandhiHtml}
                <button class="error-continue-btn" type="button" data-pinyin-dismiss>${T('pinyin.continue', null, 'Continue')} <span style="font-size: 0.8em; opacity: 0.7;">(Enter)</span></button>
            </div>`;
    const cont = q('errorModalContainer');
    cont.innerHTML = html;
    cont.querySelectorAll('[data-pinyin-dismiss]').forEach((el) => {
      el.addEventListener('click', dismissErrorModal);
    });
  }

  function dismissErrorModal() {
    q('errorModalContainer').innerHTML = '';
    state.isPaused = false;
  }

  function completeGame() {
    state.isComplete = true;
    clearInterval(state.timerInterval);
    q('touchArea').style.display = 'none';
    q('controlsHint').style.display = 'none';
    const total = state.playableTokens.length;
    const accuracy = total > 0 ? (Math.max(0, total - state.errorCount) / total) * 100 : 0;
    const timeSec = Math.floor((Date.now() - state.startTime) / 1000);
    submitResults(accuracy, timeSec);
    showResults(accuracy, timeSec);
  }

  async function submitResults(accuracy, timeSec) {
    try {
      const startedAtIso = state.startTime ? new Date(state.startTime).toISOString() : null;
      const finishedAtIso = new Date().toISOString();
      const resp = await window.authFetch(`/api/tests/${state.slug}/submit-pinyin`, {
        method: 'POST',
        body: JSON.stringify({
          correct_chars: Math.max(0, state.playableTokens.length - state.errorCount),
          total_chars: state.playableTokens.length,
          time_taken: timeSec,
          errors: state.errors.slice(0, 50),
          started_at: startedAtIso,
          finished_at: finishedAtIso,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.result) updateResultsWithElo(data.result);
      }
    } catch (err) {
      console.error('Pinyin submit error:', err);
    }
  }

  function showResults(accuracy, timeSec) {
    let grade = 'poor',
      label = T('pinyin.grade.poor', null, 'Keep Practicing');
    if (accuracy >= 95) {
      grade = 'excellent';
      label = T('pinyin.grade.excellent', null, 'Excellent!');
    } else if (accuracy >= 80) {
      grade = 'good';
      label = T('pinyin.grade.good', null, 'Great Job!');
    } else if (accuracy >= 60) {
      grade = 'fair';
      label = T('pinyin.grade.fair', null, 'Good Effort');
    }

    const minutes = Math.floor(timeSec / 60);
    const seconds = timeSec % 60;
    const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    const html = `
            <div class="results-overlay">
                <div class="results-card">
                    <h2 class="h3">${label}</h2>
                    <div class="results-accuracy ${grade}">${accuracy.toFixed(1)}%</div>
                    <p style="color: var(--text-secondary); margin-bottom: 20px;">${T('pinyin.tone_accuracy', null, 'Tone accuracy')}</p>
                    <div class="results-stats">
                        <div class="stat-box"><div class="stat-value">${state.correctCount}/${state.playableTokens.length}</div><div class="stat-label">${T('pinyin.stat.characters', null, 'Characters')}</div></div>
                        <div class="stat-box"><div class="stat-value">${timeStr}</div><div class="stat-label">${T('pinyin.stat.time', null, 'Time')}</div></div>
                        <div class="stat-box"><div class="stat-value">${state.errorCount}</div><div class="stat-label">${T('pinyin.stat.mistakes', null, 'Mistakes')}</div></div>
                        <div class="stat-box"><div class="stat-value" id="eloChangeDisplay">--</div><div class="stat-label">${T('pinyin.stat.elo_change', null, 'ELO')}</div></div>
                    </div>
                    <div class="d-flex gap-2 mt-3">
                        <button class="btn btn-primary flex-fill" type="button" data-session-next>
                            <span>${T('session.next_item', null, 'Next')}</span><i class="bi bi-arrow-right ms-1"></i>
                        </button>
                    </div>
                </div>
            </div>`;
    q('resultsContainer').innerHTML = html;
    const nextBtn = q('resultsContainer').querySelector('[data-session-next]');
    if (nextBtn) nextBtn.onclick = () => ctx.onComplete({ accuracy });
  }

  function updateResultsWithElo(result) {
    const eloEl = q('eloChangeDisplay');
    if (eloEl && result.user_elo_change) {
      const change = result.user_elo_change.change || 0;
      const sign = change >= 0 ? '+' : '';
      eloEl.textContent = sign + change;
      eloEl.className = 'stat-value ' + (change >= 0 ? 'text-success' : 'text-danger');
    }
  }

  function startTimer() {
    state.startTime = Date.now();
    const el = q('elapsedTime');
    state.timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
      const m = Math.floor(elapsed / 60),
        s = elapsed % 60;
      if (el) el.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }, 1000);
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
    ['pinyinHeader', 'passageContainer', 'controlsHint', 'touchArea'].forEach((id) => {
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
    .session-stage { --tone-1:#E53935; --tone-2:#F57C00; --tone-3:#43A047; --tone-4:#1E88E5; --tone-5:#9E9E9E; }
    .pinyin-header { background: var(--bg-surface); border-bottom: 2px solid var(--border-default); position: sticky; top: 0; z-index: 40; box-shadow: var(--shadow-sm); }
    .pinyin-progress-bar { height: 6px; background: var(--border-default); position: absolute; bottom: 0; left: 0; right: 0; }
    .pinyin-progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary) 0%, var(--info) 100%); transition: width .3s ease; }
    .passage-container { max-width: 720px; margin: 0 auto; padding: 32px 20px; }
    .passage-grid { display: flex; flex-wrap: wrap; font-size: 2rem; line-height: 2.2; justify-content: flex-start; user-select: none; -webkit-user-select: none; }
    .char-token { display: inline-flex; flex-direction: column; align-items: center; transition: all .2s ease; padding: 2px 1px; position: relative; cursor: default; }
    .char-token .char-display { position: relative; z-index: 1; }
    .char-token .char-pinyin { font-size: .4em; color: var(--text-muted); line-height: 1; margin-top: -4px; opacity: 0; transition: opacity .2s ease; }
    .char-token.completed .char-pinyin { opacity: 1; }
    .char-token.upcoming { color: var(--slate-400); }
    .char-token.current { transform: scale(1.25); margin: 0 6px; }
    .char-token.current .char-display { border-bottom: 3px solid var(--primary); padding-bottom: 2px; }
    .char-token.completed { opacity: 1; }
    .char-token.error-flash { animation: shake .3s ease; }
    .char-token.correct-flash { animation: pop .2s ease; }
    .char-token.tone-1 .char-display, .char-token.tone-1 .char-pinyin { color: var(--tone-1); }
    .char-token.tone-2 .char-display, .char-token.tone-2 .char-pinyin { color: var(--tone-2); }
    .char-token.tone-3 .char-display, .char-token.tone-3 .char-pinyin { color: var(--tone-3); }
    .char-token.tone-4 .char-display, .char-token.tone-4 .char-pinyin { color: var(--tone-4); }
    .char-token.tone-5 .char-display, .char-token.tone-5 .char-pinyin { color: var(--tone-5); }
    .char-token.punctuation { color: var(--slate-500); }
    @keyframes shake { 0%,100% { transform: translateX(0); } 25% { transform: translateX(-4px); } 75% { transform: translateX(4px); } }
    @keyframes pop { 0% { transform: scale(1.25); } 50% { transform: scale(1.4); } 100% { transform: scale(1); } }
    .controls-hint { position: fixed; bottom: 0; left: 0; right: 0; background: var(--bg-surface); border-top: 1px solid var(--border-default); padding: 12px 20px; z-index: 50; }
    .controls-grid { display: flex; justify-content: center; gap: 16px; flex-wrap: wrap; max-width: 600px; margin: 0 auto; }
    .control-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-secondary); }
    .control-key { display: inline-flex; align-items: center; justify-content: center; min-width: 32px; height: 28px; padding: 0 8px; border: 2px solid var(--border-strong); border-radius: 6px; font-size: 12px; font-weight: 700; background: var(--bg-surface); color: var(--text-primary); }
    .tone-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    .error-backdrop { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15,23,42,.4); z-index: 200; }
    .error-modal { position: fixed; z-index: 201; background: var(--bg-surface); border-radius: 16px; box-shadow: var(--shadow-lg); padding: 28px 24px; width: 90%; max-width: 420px; top: 50%; left: 50%; transform: translate(-50%, -50%); }
    @media (max-width: 480px) { .error-modal { top: auto; bottom: 0; left: 0; right: 0; transform: none; width: 100%; max-width: 100%; border-radius: 16px 16px 0 0; } }
    .error-char { font-size: 3rem; font-weight: 700; text-align: center; margin-bottom: 8px; }
    .error-pinyin { text-align: center; font-size: 1.1rem; color: var(--text-secondary); margin-bottom: 16px; }
    .error-tones { display: flex; justify-content: center; gap: 24px; margin-bottom: 16px; }
    .tone-label { text-align: center; }
    .tone-label .tone-num { font-size: 1.5rem; font-weight: 700; }
    .tone-label .tone-desc { font-size: .8rem; color: var(--text-muted); }
    .sandhi-explanation { background: var(--info-bg); border-left: 4px solid var(--info); border-radius: 8px; padding: 12px; font-size: .9rem; color: var(--slate-700); margin-bottom: 16px; }
    .error-continue-btn { width: 100%; padding: 14px; border: none; border-radius: 10px; background: var(--primary); color: #fff; font-size: 1rem; font-weight: 600; cursor: pointer; }
    .error-continue-btn:hover { background: var(--primary-hover); }
    .results-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--bg-body); z-index: 300; display: flex; align-items: center; justify-content: center; }
    .results-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 16px; box-shadow: var(--shadow-lg); padding: 32px; width: 90%; max-width: 480px; text-align: center; }
    .results-accuracy { font-size: 4rem; font-weight: 800; margin: 16px 0 8px; }
    .results-accuracy.excellent { color: var(--success); }
    .results-accuracy.good { color: var(--tone-2); }
    .results-accuracy.fair { color: var(--warning); }
    .results-accuracy.poor { color: var(--danger); }
    .results-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 20px 0; }
    .stat-box { padding: 12px; background: var(--bg-muted); border-radius: 8px; }
    .stat-box .stat-value { font-size: 1.4rem; font-weight: 700; }
    .stat-box .stat-label { font-size: .8rem; color: var(--text-muted); }
    .loading-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15,23,42,.6); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999; }
    .loading-spinner { background: var(--bg-surface); padding: 32px; border-radius: 12px; box-shadow: var(--shadow-lg); text-align: center; }
    .spinner-icon { border: 4px solid var(--border-default); border-top-color: var(--primary); border-radius: 50%; width: 48px; height: 48px; animation: spin .8s linear infinite; margin: 0 auto 16px; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .touch-area { position: fixed; top: 60px; left: 0; right: 0; bottom: 70px; z-index: 10; touch-action: none; -webkit-touch-callout: none; }
    @media (max-width: 768px) { .passage-grid { font-size: 1.6rem; line-height: 2; } .char-token.current { transform: scale(1.15); margin: 0 4px; } }
</style>

<div id="loadingOverlay" class="loading-overlay" style="display:none;">
    <div class="loading-spinner"><div class="spinner-icon"></div><p class="mb-0 text-slate-600" data-i18n="pinyin.loading">Loading pinyin data...</p></div>
</div>

<div id="errorState" class="container py-5" style="display:none;">
    <div class="alert alert-danger">
        <h2 class="h5"><i class="fas fa-exclamation-triangle me-2"></i><span data-i18n="pinyin.error.title">Error</span></h2>
        <p id="errorMessage" class="mb-2"></p>
    </div>
</div>

<div class="pinyin-header" id="pinyinHeader" style="display:none;">
    <div class="container py-3">
        <div class="row align-items-center">
            <div class="col"><h1 class="mb-0 h5"><i class="bi bi-translate text-primary me-2"></i><span id="testTitle" data-i18n="pinyin.title">Pinyin Tone Trainer</span></h1></div>
            <div class="col-auto"><span class="badge bg-primary me-2" id="testLanguage"></span><span class="badge bg-info" data-i18n="pinyin.badge">Pinyin</span><span class="ms-2 text-slate-500"><i class="far fa-clock me-1"></i><span id="elapsedTime">00:00</span></span></div>
        </div>
    </div>
    <div class="pinyin-progress-bar"><div class="pinyin-progress-fill" id="progressFill" style="width:0%"></div></div>
</div>

<div class="touch-area" id="touchArea" style="display:none;"></div>

<div class="passage-container" id="passageContainer" style="display:none;">
    <div class="passage-grid" id="passageGrid"></div>
</div>

<div class="controls-hint" id="controlsHint" style="display:none;">
    <div class="controls-grid">
        <div class="control-item"><span class="control-key"><i class="bi bi-arrow-right"></i></span><span class="tone-dot" style="background: var(--tone-1);"></span><span>T1</span></div>
        <div class="control-item"><span class="control-key"><i class="bi bi-arrow-up"></i></span><span class="tone-dot" style="background: var(--tone-2);"></span><span>T2</span></div>
        <div class="control-item"><span class="control-key"><i class="bi bi-arrow-left"></i></span><span class="tone-dot" style="background: var(--tone-3);"></span><span>T3</span></div>
        <div class="control-item"><span class="control-key"><i class="bi bi-arrow-down"></i></span><span class="tone-dot" style="background: var(--tone-4);"></span><span>T4</span></div>
        <div class="control-item"><span class="control-key" data-i18n="pinyin.space">Space</span><span class="tone-dot" style="background: var(--tone-5);"></span><span data-i18n="pinyin.neutral">Neutral</span></div>
    </div>
</div>

<div id="errorModalContainer"></div>
<div id="resultsContainer"></div>
`;
