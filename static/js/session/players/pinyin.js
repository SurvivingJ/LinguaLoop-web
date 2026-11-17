// static/js/session/players/pinyin.js
// Pinyin tone trainer: an item of the daily session, and the whole of the
// standalone page /test/<slug>/pinyin (static/js/pages/test-pinyin.js mounts it
// with ctx.standalone). Container-scoped, leak-free teardown (document keydown
// + timer are tracked), error-modal buttons wired via listeners. In the session
// it finishes through ctx.onComplete(); the page links to Retry / All tests.

import { T, nativeName, escapeHtml } from '../dom.js';
import { createTrainer, prefetchTest, applyLocalKeys } from './_syllable_trainer.js';

export const prefetch = prefetchTest;

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
  const trainer = createTrainer(container, ctx, {
    tokenClass: 'char-token',
    errorHideIds: ['pinyinHeader', 'passageContainer', 'controlsHint', 'touchArea'],
  });
  const { state, on, q, showLoading, showError, startTimer, updateProgress, flashError } = trainer;
  const dismissErrorModal = trainer.dismissErrorModal;

  // Styles: static/css/redesign/trainers.css (loaded on every page), scoped
  // to .syl-trainer--pinyin, so the session and the page share them.
  container.innerHTML = trainer.standalone ? MARKUP : trainer.compact(MARKUP);
  if (trainer.frame) q('pinyinRootScreen').classList.add('is-framed');
  trainer.addBackLink();
  init();

  return { destroy: trainer.destroy };

  async function init() {
    try {
      showLoading(true);
      if (!state.slug) throw new Error('No test slug');
      if (trainer.standalone) await trainer.prepare();
      applyLocalKeys(container);
      await loadTestData();
      renderPassage();
      renderTonePad();
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
    const data = await trainer.fetchTest((resp) =>
      T('pinyin.error.load_failed', { status: resp.statusText }, 'Failed to load')
    );
    state.testData = data.test_data;
    if (!data.pinyin_payload || data.pinyin_payload.length === 0) {
      throw new Error(T('pinyin.error.no_data', null, 'No pinyin data for this test.'));
    }
    trainer.setTokens(data.pinyin_payload, (tok) => !tok.is_punctuation);
    if (state.playableTokens.length === 0) {
      throw new Error(T('pinyin.error.no_chars', null, 'No characters to play.'));
    }
    q('testTitle').textContent =
      state.testData.title || T('pinyin.title', null, 'Pinyin Tone Trainer');
    q('testLanguage').textContent = nativeName(state.testData.language) || 'Chinese';
    if (state.testData.title) trainer.setHeader({ subtitle: state.testData.title });
  }

  /**
   * The on-screen tone buttons in the dock: the same five answers as the
   * arrow keys, swipes and tap (1-4 and neutral).
   */
  function renderTonePad() {
    const pad = q('tonePad');
    if (!pad) return;
    const neutral = T('pinyin.neutral', null, 'Neutral');
    pad.setAttribute('aria-label', T('trainers.tone_pad', null, 'Tones'));
    pad.innerHTML = TONE_PAD.map(
      ([tone, mark, key]) =>
        `<button type="button" class="tone-btn" data-tone="${tone}" aria-label="${escapeHtml(
          tone === 5 ? neutral : T('trainers.tone_n', { n: tone }, `Tone ${tone}`)
        )}"><b class="tone-c${tone}" lang="zh-Latn">${mark}</b><span>${
          tone === 5 ? escapeHtml(neutral) : tone
        }</span><kbd aria-hidden="true">${key}</kbd></button>`
    ).join('');
    pad.querySelectorAll('button[data-tone]').forEach((btn) => {
      on(btn, 'click', () => handleToneInput(parseInt(btn.dataset.tone, 10)));
    });
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
    trainer.markCurrent();
    updateProgress();
  }

  function colorChar(playableIdx, tone) {
    const el = trainer.tokenEl(playableIdx);
    const token = state.playableTokens[playableIdx];
    if (el) {
      el.classList.remove('current', 'upcoming');
      el.classList.add('completed', `tone-${tone}`);
      const pinyinEl = el.querySelector('.char-pinyin');
      if (pinyinEl) pinyinEl.textContent = applyToneMark(token.pinyin_text, token.context_tone);
      trainer.flashCorrect(el);
    }
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
      // Space is "neutral", as it always was. The one exception: a tone
      // button reached with the keyboard (:focus-visible) is pressed by Space
      // like any button. A button that merely kept focus after a tap or click
      // does not steal Space.
      if (e.key === ' ' && isKeyboardFocusedToneButton(e.target)) return;
      const map = { ArrowRight: 1, ArrowUp: 2, ArrowLeft: 3, ArrowDown: 4, ' ': 5 };
      if (map[e.key] !== undefined) {
        e.preventDefault();
        handleToneInput(map[e.key]);
      }
      if (e.key === 'Enter' && state.isPaused) {
        // Without this the browser also "clicks" whatever has focus (a dock
        // tone button), answering again the moment the sheet closes.
        e.preventDefault();
        dismissErrorModal();
      }
    });

    const SWIPE_TONE = { right: 1, up: 2, left: 3, down: 4 };
    trainer.bindSwipe(
      q('touchArea'),
      (direction) => handleToneInput(SWIPE_TONE[direction]),
      () => handleToneInput(5)
    );
  }

  function isKeyboardFocusedToneButton(target) {
    if (!target || !target.closest || !target.closest('#tonePad button')) return false;
    try {
      return target.matches(':focus-visible');
    } catch {
      return false;
    }
  }

  function showErrorModal(token, guessedTone) {
    const toneColor = (tn) => `var(--tone-${tn})`;
    let sandhiHtml = '';
    if (token.is_sandhi && token.sandhi_rule) {
      sandhiHtml = `<div class="sandhi-explanation"><strong><i class="bi bi-info-circle me-1"></i>${T('pinyin.sandhi_rule', null, 'Tone sandhi')}</strong><br>${escapeHtml(token.sandhi_rule)}</div>`;
    }
    const html = `
            <div class="error-backdrop" data-pinyin-dismiss></div>
            <div class="error-modal" role="dialog" aria-modal="true">
                <div class="error-char" lang="zh" style="color: ${toneColor(token.context_tone)}">${escapeHtml(token.char)}</div>
                <div class="error-pinyin">${escapeHtml(applyToneMark(token.pinyin_text, token.context_tone))}${trainer.standalone ? ' ' : ''}<span class="error-word-ctx">(${escapeHtml(token.word)})</span></div>
                <div class="error-tones">
                    <div class="tone-label"><div class="tone-num" style="color: ${toneColor(guessedTone)}">${guessedTone}</div><div class="tone-desc">${T('pinyin.your_answer', null, 'Your answer')}</div></div>
                    <div class="tone-arrow" aria-hidden="true"><i class="bi bi-arrow-right"></i></div>
                    <div class="tone-label"><div class="tone-num" style="color: ${toneColor(token.context_tone)}">${token.context_tone}</div><div class="tone-desc">${T('pinyin.correct', null, 'Correct')}</div></div>
                </div>
                ${sandhiHtml}
                <button class="error-continue-btn ld-btn" type="button" data-pinyin-dismiss>${T('pinyin.continue', null, 'Continue')} <span class="error-continue-key" aria-hidden="true">(Enter)</span></button>
                <p class="error-again">${T('trainers.answer_again_char', null, 'You’ll answer this character again.')}</p>
            </div>`;
    trainer.showErrorModal(html, 'data-pinyin-dismiss');
  }

  function completeGame() {
    state.isComplete = true;
    if (document.activeElement && container.contains(document.activeElement)) {
      document.activeElement.blur();
    }
    q('touchArea').style.display = 'none';
    q('controlsHint').style.display = 'none';
    const gradeLabels = {
      excellent: T('pinyin.grade.excellent', null, 'Excellent!'),
      good: T('pinyin.grade.good', null, 'Great Job!'),
      fair: T('pinyin.grade.fair', null, 'Good Effort'),
      poor: T('pinyin.grade.poor', null, 'Keep Practicing'),
    };
    trainer.complete({
      submitUrl: `/api/tests/${state.slug}/submit-pinyin`,
      logName: 'Pinyin',
      buildBody: ({ correct, total, timeSec, errors, startedAt, finishedAt }) => ({
        correct_chars: correct,
        total_chars: total,
        time_taken: timeSec,
        errors,
        started_at: startedAt,
        finished_at: finishedAt,
      }),
      results: {
        labelHtml: (grade) => gradeLabels[grade],
        accuracyLabel: T('pinyin.tone_accuracy', null, 'Tone accuracy'),
        unitsLabel: T('pinyin.stat.characters', null, 'Characters'),
        timeLabel: T('pinyin.stat.time', null, 'Time'),
        mistakesLabel: T('pinyin.stat.mistakes', null, 'Mistakes'),
        eloLabel: T('pinyin.stat.elo_change', null, 'ELO'),
        retryLabel: T('pinyin.retry', null, 'Retry'),
        allTestsLabel: T('pinyin.all_tests', null, 'All Tests'),
      },
    });
  }
}

// The dock's tone buttons: [tone, marked vowel, key].
const TONE_PAD = [
  [1, 'ā', '→'],
  [2, 'á', '↑'],
  [3, 'ǎ', '←'],
  [4, 'à', '↓'],
  [5, 'a', '␣'],
];

// ========================================================================
// MARKUP — one task screen (FOUNDATION.md): a progress strip, the passage in
// the scrolling stage (the swipe surface lies over it), the tone buttons in
// the pinned dock. Styles: static/css/redesign/trainers.css.
// ========================================================================
const MARKUP = `
<div class="ld-screen syl-trainer syl-trainer--pinyin" id="pinyinRootScreen">
<!-- Loading Overlay -->
<div id="loadingOverlay" class="loading-overlay" style="display: none;">
    <div class="loading-spinner" role="status">
        <div class="spinner-icon" aria-hidden="true"></div>
        <p class="mb-0" data-i18n="pinyin.loading">Loading pinyin data...</p>
    </div>
</div>

<!-- Error State -->
<div id="errorState" class="trainer-error" style="display: none;">
    <div class="alert alert-danger">
        <h2 class="h5"><i class="fas fa-exclamation-triangle me-2" aria-hidden="true"></i><span data-i18n="pinyin.error.title">Error</span></h2>
        <p id="errorMessage" class="mb-2"></p>
    </div>
</div>

<!-- Progress strip -->
<div class="trainer-strip" id="pinyinHeader" style="display: none;">
    <div class="trainer-strip__row">
        <h1 class="trainer-title"><span id="testTitle" data-i18n="pinyin.title">Pinyin Tone Trainer</span></h1>
        <span class="ld-tag ld-tag--brand" id="testLanguage"></span>
        <span class="ld-tag ld-tag--info" data-i18n="pinyin.badge">Pinyin</span>
        <span class="trainer-clock"><i class="far fa-clock" aria-hidden="true"></i> <span id="elapsedTime">00:00</span></span>
    </div>
    <div class="ld-bar trainer-bar"><i class="pinyin-progress-fill" id="progressFill" style="width: 0%"></i></div>
</div>

<div class="trainer-swipe">
    <div class="ld-stage trainer-stage">
        <!-- Passage Display -->
        <div class="passage-container" id="passageContainer" style="display: none;" lang="zh">
            <div class="passage-grid" id="passageGrid"></div>
            <p class="ld-hint trainer-hint" data-trk="trainers.pinyin_swipe_hint">Swipe on the passage: → 1st · ↑ 2nd · ← 3rd · ↓ 4th. Tap for neutral. The buttons below and the arrow keys work too.</p>
        </div>
    </div>
    <!-- Touch Area (for swipe detection): covers the passage, not the dock -->
    <div class="touch-area" id="touchArea" style="display: none;"></div>
</div>

<!-- Dock: tone buttons (+ the keyboard legend on wide screens) -->
<div class="ld-dock trainer-dock" id="controlsHint" style="display: none;">
    <div class="tonepad" id="tonePad" role="group"></div>
    <div class="controls-grid ld-wide-only" aria-hidden="true">
        <div class="control-item">
            <span class="control-key"><i class="bi bi-arrow-right"></i></span>
            <span class="tone-dot" style="background: var(--tone-1);"></span>
            <span>T1</span>
        </div>
        <div class="control-item">
            <span class="control-key"><i class="bi bi-arrow-up"></i></span>
            <span class="tone-dot" style="background: var(--tone-2);"></span>
            <span>T2</span>
        </div>
        <div class="control-item">
            <span class="control-key"><i class="bi bi-arrow-left"></i></span>
            <span class="tone-dot" style="background: var(--tone-3);"></span>
            <span>T3</span>
        </div>
        <div class="control-item">
            <span class="control-key"><i class="bi bi-arrow-down"></i></span>
            <span class="tone-dot" style="background: var(--tone-4);"></span>
            <span>T4</span>
        </div>
        <div class="control-item">
            <span class="control-key" data-i18n="pinyin.space">Space</span>
            <span class="tone-dot" style="background: var(--tone-5);"></span>
            <span data-i18n="pinyin.neutral">Neutral</span>
        </div>
    </div>
</div>

<!-- Error Modal (injected dynamically) -->
<div id="errorModalContainer"></div>

<!-- Results Screen (injected dynamically) -->
<div id="resultsContainer"></div>
</div>
`;
