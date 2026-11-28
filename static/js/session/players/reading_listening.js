// static/js/session/players/reading_listening.js
// Reading + Listening comprehension player. Used by the daily-session runner
// and by the standalone test page (static/js/pages/test.js). Renders into a
// provided container, scopes all DOM lookups to it, tracks listeners/timers
// for clean teardown, and calls ctx.onComplete(result) when the learner
// finishes.
//
// Page-level options on ctx (all optional; the session runner passes none):
//   payload          test payload already in hand, used instead of a request
//   ready            promise awaited (with the test data) before rendering
//   sentences        false: plain transcript, no sentence rows are requested
//   audioPreload     preload value for a listening test's <audio>
//   popoverBackdrop  dim the page behind the word popover on phones
//   resultActions    options for the post-test prestudy action, replacing the
//                    session's "save completion, then return to the session"
//   finishButton     (button, result, { testId }) => void: sets up the button that
//                    replaces Submit, instead of "Next" -> ctx.onComplete
//   pageHeader       true: the player also fills the task header's title,
//                    subtitle and seal (the session runner fills those itself)
// ctx.frame (optional, see session-frame): the task header. The player puts the
// elapsed-time clock in its right-hand slot.
// The returned handle also has rerender(), for a UI-language switch.
//
// Layout (2026-11 redesign): one .ld-screen with a scrolling .ld-stage (one
// question at a time, or the passage) and a pinned .ld-dock (prev / next /
// Submit). Styles: static/css/redesign/tests.css (.rl-player).

import {
  fetchTestSentences,
  resolveSentences,
  renderSentenceBlocks,
  hasVisibleReferences,
  hasTokenSpans,
  deriveTokenSpans,
  setReferencesVisible,
} from '../sentences.js';
import {
  T,
  nativeName,
  escapeHtml as escapeHtmlForFurigana,
  formatTime,
  formatClock,
  showLoading as setLoading,
} from '../dom.js';
import { prefetchJson, takePrefetch, warmAudio, adoptAudio } from '../prefetch.js';
import { formatPinyin, displayPronunciation } from '../pinyin-format.js';

// Header seal per study language (the session runner's GLYPHS, for the page).
const SEALS = {
  zh: { reading: '读', listening: '听' },
  ja: { reading: '読', listening: '聴' },
};

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

const testUrl = (slug) => `/api/tests/test/${slug}`;
const sentenceMode = (item) => (item && item.prestudy_stage === 'produce' ? 'produce' : null);

/**
 * Session prefetch hook: the test payload, its sentence rows and, for a
 * listening test, the audio — all static content, safe to load early.
 */
export async function prefetch(item) {
  if (!item || !item.slug) return { ok: false };
  const res = await prefetchJson(testUrl(item.slug));
  if (!res.ok) return res;
  const payload = res.data.data || res.data;
  const test = payload.test_data;
  if (!test) return res;
  if (item.test_type === 'listening') res.audio = warmAudio(test.audio_url);
  try {
    res.sentences = await fetchTestSentences(item.slug, {
      mode: sentenceMode(item),
      transcript: test.transcript || '',
    });
  } catch {
    /* the player falls back to its own request */
  }
  return res;
}

export function mount(container, ctx) {
  const mode = ctx.item.test_type === 'listening' ? 'listening' : 'reading';

  const state = {
    slug: ctx.item.slug,
    mode,
    testId: null,
    testData: null,
    vocabTokenMap: [],
    definitions: {},
    questions: [],
    currentQuestionIndex: 0,
    answers: {},
    startTime: null,
    isSubmitted: false,
    audioElement: null,
    playbackSpeed: 1.0,
    furiganaPayload: null,
    furiganaEnabled: false,
    furiganaUsedThisAttempt: false,
    _timer: null,
    // TASK-911: server sentence spans (test_sentences) or the client split; the
    // transcript renders as per-sentence blocks with a hidden-by-default L1
    // reference line. `produce` (the prestudy Produce stage) never shows it.
    sentences: null,
    sentenceSource: null,
    sentenceMode: sentenceMode(ctx.item),
    referencesShown: false,
    // Which stage pane shows: 'passage' (reading passage / transcript) or
    // 'questions'. A listening test has only questions until it is submitted.
    tab: mode === 'reading' ? 'passage' : 'questions',
  };
  const frame = ctx.frame || null;

  // --- lifecycle plumbing -------------------------------------------------
  const cleanup = [];
  const on = (el, ev, fn, opts) => {
    el.addEventListener(ev, fn, opts);
    cleanup.push(() => el.removeEventListener(ev, fn, opts));
  };
  const q = (id) => container.querySelector('#' + id);

  // static/css/styles.css scopes every reading/listening rule (.test-header,
  // .transcript-card, .audio-player-card, .question-card, .answer-option,
  // .word-popover, ...) under body.test-page — the class templates/test.html
  // sets via its body_class block. The daily-session runner's body carries
  // study-session-page instead, so without this the whole player mounts
  // completely unstyled: MARKUP is in the DOM (title, furigana checkbox,
  // etc. still show since those come from global/Bootstrap rules) but the
  // transcript, audio player and questions have no layout/background/borders
  // and effectively read as a blank page. Standalone page sets the class for
  // its own lifetime; here we set/clear it around this player's mount/destroy
  // so it never leaks onto other players sharing the same session body.
  // Mirrors the identical fix in players/pitch_accent.js.
  document.body.classList.add('test-page');

  container.innerHTML = MARKUP;
  const root = container.querySelector('.rl-player');
  root.dataset.mode = mode;
  // The task header shows title and clock; the in-stage title block is then
  // only for screen readers (its ids stay, other code fills them).
  if (frame) root.classList.add('rl-player--framed');
  // The passage pane is the reading passage, or (listening, after submit)
  // the transcript.
  ['rlPassageLabel', 'rlTabPassage'].forEach((id) => {
    q(id).setAttribute('data-t', mode === 'reading' ? 'test.reading_passage' : 'test.transcript');
    q(id).textContent = mode === 'reading' ? 'Reading Passage' : 'Transcript';
  });
  localize(container);
  renderPrestudyOffer();

  init();

  // NOTE: the object returned by mount() must be built at the END of this
  // function body, not here. `return` halts execution of the enclosing
  // function immediately — any `const`/`function` declared textually AFTER
  // an early return in the same scope never runs. wordPopover and wordQuiz
  // below are exactly that: both are declared further down as `const`, so
  // an early return here left them permanently in the temporal dead zone.
  // init() resumes asynchronously (after its first `await`), by which time
  // mount()'s synchronous body — everything up to the real return at the
  // bottom — has already finished running, so wordPopover.init() and
  // wordQuiz.show() see fully-initialized objects instead of throwing
  // "Cannot access 'wordPopover' before initialization". This silently
  // killed every word-definition popover and vocab quiz in this player
  // (init() caught the throw and rendered the generic error state instead).

  // ====================================================================
  // INIT
  // ====================================================================
  async function init() {
    try {
      showLoading(true);
      await Promise.all([loadTestData(), ctx.ready]);
      await loadSentences();
      initializeUI();
      state.startTime = Date.now();
      startTimer();
      showLoading(false);
    } catch (e) {
      console.error('Player init error:', e);
      showError(e.message || 'Failed to load test');
      showLoading(false);
    }
  }

  async function loadTestData() {
    const pre = await takePrefetch(ctx.item);
    let data = (pre && pre.data) || ctx.payload;
    if (pre) {
      state.warmAudio = pre.audio || null;
      if ('sentences' in pre) state.prefetchedSentences = { rows: pre.sentences };
    } else if (!data) {
      const response = await window.authFetch(testUrl(state.slug));
      if (!response.ok) throw new Error(`Failed to load test (${response.status})`);
      data = await response.json();
    }
    const payload = data.data || data;
    if (!payload.test_data || !payload.questions_data) {
      throw new Error('Invalid test data received');
    }
    state.testData = payload.test_data;
    state.skillRatings = payload.skill_ratings || {};
    state.testId = payload.test_data.id;
    state.vocabTokenMap = payload.vocab_token_map || [];
    state.definitions = payload.definitions || {};
    state.furiganaPayload = payload.furigana_payload || null;
    state.questions = payload.questions_data.map((qd) => ({
      id: qd.id,
      text: qd.question_text,
      choices: Array.isArray(qd.choices) ? qd.choices : JSON.parse(qd.choices || '[]'),
      // Answer key + explanation are NOT in the pre-submit payload (TASK-882);
      // they arrive in the submit response's question_results.
      correctAnswer: null,
      explanation: null,
      type: qd.question_type,
    }));
  }

  // ====================================================================
  // SENTENCES (TASK-911)
  // ====================================================================
  async function loadSentences() {
    if (ctx.sentences === false) return;
    const transcript = (state.testData && state.testData.transcript) || '';
    let serverRows = null;
    try {
      serverRows = state.prefetchedSentences
        ? state.prefetchedSentences.rows
        : await fetchTestSentences(state.slug, {
            mode: state.sentenceMode,
            transcript,
          });
    } catch (e) {
      console.warn('sentences: unexpected failure, using client split', e);
    }
    const resolved = resolveSentences(transcript, serverRows);
    state.sentences = resolved.sentences;
    state.sentenceSource = resolved.source;
  }

  // Whole-transcript furigana is positional over the full text, so when it is
  // on we keep the single-block rendering; otherwise the transcript is a list
  // of sentence blocks sharing the same container (and word-popover handlers).
  function renderTranscript() {
    const el = q('transcriptText');
    if (!el) return;
    const transcript = state.testData.transcript || '';
    const furiganaTokens = state.furiganaPayload && state.furiganaPayload.transcript;
    const furiganaOn =
      state.furiganaEnabled && Array.isArray(furiganaTokens) && furiganaTokens.length;
    if (!state.sentences || !state.sentences.length || furiganaOn) {
      el.innerHTML = renderJpText(transcript, furiganaTokens);
      updateReferenceToggle(false);
      return;
    }
    renderSentenceBlocks(el, state.sentences, {
      mode: state.sentenceMode,
      renderText: (t) => escapeHtmlForFurigana(t),
      showReferences: state.referencesShown,
    });
    updateReferenceToggle(true);
  }

  function updateReferenceToggle(sentenceView) {
    const btn = q('toggleReferences');
    if (!btn) return;
    const show = sentenceView && hasVisibleReferences(state.sentences, state.sentenceMode);
    btn.style.display = show ? '' : 'none';
    btn.setAttribute('aria-pressed', state.referencesShown ? 'true' : 'false');
    btn.innerHTML =
      '<i class="fas fa-language" aria-hidden="true"></i>' +
      (state.referencesShown
        ? T('test.hide_translation', null, 'Hide translation')
        : T('test.show_translation', null, 'Show translation'));
  }

  // ====================================================================
  // FURIGANA
  // ====================================================================
  function renderFuriganaTokens(tokens) {
    if (!Array.isArray(tokens)) return '';
    const parts = [];
    for (const tok of tokens) {
      if (!tok) continue;
      if (tok.kind === 'plain') {
        parts.push(escapeHtmlForFurigana(tok.text));
        continue;
      }
      if (tok.kind === 'ruby') {
        const segs =
          Array.isArray(tok.segments) && tok.segments.length
            ? tok.segments
            : [{ base: tok.base, rt: tok.rt }];
        parts.push('<ruby>');
        for (const seg of segs) {
          parts.push(escapeHtmlForFurigana(seg.base));
          parts.push('<rt>' + escapeHtmlForFurigana(seg.rt || '') + '</rt>');
        }
        parts.push('</ruby>');
      }
    }
    return parts.join('');
  }

  function renderJpText(plainText, tokens) {
    if (state.furiganaEnabled && Array.isArray(tokens) && tokens.length) {
      return renderFuriganaTokens(tokens);
    }
    return escapeHtmlForFurigana(plainText);
  }

  async function setupFuriganaToggle() {
    const wrap = q('furiganaToggleLabel');
    const cb = q('furiganaToggle');
    if (!wrap || !cb) return;
    if (!state.furiganaPayload) {
      wrap.classList.remove('visible');
      return;
    }
    wrap.classList.add('visible');

    // Always start unselected. Furigana is a per-attempt opt-in (it halves
    // the ELO change), so a prior test's choice must never carry over —
    // restoring it from the stored preference here previously left the
    // checkbox showing checked without the transcript actually rendering
    // furigana (the initial render already ran before this async fetch
    // resolved), which was worse than just not restoring it at all.
    state.furiganaEnabled = false;
    cb.checked = false;

    on(cb, 'change', () => {
      state.furiganaEnabled = cb.checked;
      if (cb.checked) state.furiganaUsedThisAttempt = true;
      try {
        window.authFetch('/api/users/preferences', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ furigana_enabled: cb.checked }),
        });
      } catch (_) {
        /* non-fatal */
      }
      if (state.mode === 'reading') {
        if (state.isSubmitted) wrapTranscriptWords();
        else renderTranscript();
      }
      renderQuestions();
    });
  }

  // ====================================================================
  // UI
  // ====================================================================
  function langCode() {
    const code = String((state.testData && state.testData.language) || '').toLowerCase();
    return window.LinguaLanguages.codeOf(code, code); // legacy 'cn' / 'jp' -> 'zh' / 'ja'
  }

  function modeLabel() {
    return state.mode === 'reading'
      ? T('test_list.reading', null, 'Reading')
      : T('test_list.listening', null, 'Listening');
  }

  // Task header: the session runner fills title / subtitle / seal itself; a
  // standalone page asks for them (ctx.pageHeader). The clock is always ours.
  function fillHeader() {
    if (!frame || typeof frame.setHeader !== 'function') return;
    const h = { end: q('elapsedTime') ? q('elapsedTime').textContent : '' };
    if (ctx.pageHeader && state.testData) {
      const parts = [
        nativeName(state.testData.language),
        q('testDifficulty').textContent,
        modeLabel(),
      ];
      h.title = state.testData.title || state.testData.topic || '';
      h.subtitle = parts.filter(Boolean).join(' · ');
      const seals = SEALS[langCode()];
      h.glyph = (seals && seals[state.mode]) || modeLabel().charAt(0);
    }
    frame.setHeader(h);
  }

  function initializeUI() {
    q('testTitleText').textContent = state.testData.title || state.testData.topic;
    q('testLanguage').textContent = nativeName(state.testData.language);
    // Same difficulty scale as the test list and preview (static/js/utils.js
    // ELO_RANGES); it used to show the stored generation level ("Level 5").
    const U = window.LinguaUtils;
    const difficultyText =
      U && U.getTestDifficultyText ? U.getTestDifficultyText(state.skillRatings, state.mode) : '';
    q('testDifficulty').textContent = difficultyText;
    q('testDifficulty').classList.toggle('d-none', !difficultyText);
    q('testType').textContent = state.mode.charAt(0).toUpperCase() + state.mode.slice(1);
    const lang = langCode();
    if (lang) q('transcriptText').setAttribute('lang', lang);

    setupFuriganaToggle();

    if (state.mode === 'reading') initializeReadingTest();
    else initializeListeningTest();

    renderQuestions();
    renderQuestionNavigation();
    setupEventListeners();
    wordPopover.init();
    updateProgress();
    renderTabs();
    localize(container);
    fillHeader();
  }

  function initializeReadingTest() {
    q('transcriptCard').style.display = 'block';
    renderTranscript();
  }

  function initializeListeningTest() {
    q('audioPlayerCard').style.display = 'block';
    if (ctx.audioPreload) q('audioElement').preload = ctx.audioPreload;
    state.audioElement = adoptAudio(q('audioElement'), state.warmAudio, state.testData.audio_url);
    setupAudioPlayer();
  }

  // ====================================================================
  // PANES (passage / questions)
  // ====================================================================
  // Reading: Passage | Questions. Listening: questions only until submitted,
  // then Questions | Transcript.
  function renderTabs() {
    const tabs = q('rlTabs');
    if (!tabs) return;
    const reading = state.mode === 'reading';
    const show = reading || state.isSubmitted;
    tabs.hidden = !show;
    const order = reading ? ['passage', 'questions'] : ['questions', 'passage'];
    order.forEach((name) => tabs.appendChild(tabs.querySelector(`[data-rl-tab="${name}"]`)));
    if (!show) state.tab = 'questions';
    setTab(state.tab);
  }

  function setTab(tab) {
    state.tab = tab;
    const passage = q('rlPassagePane');
    const questions = q('rlQuestionsPane');
    if (passage) passage.hidden = tab !== 'passage';
    if (questions) questions.hidden = tab !== 'questions';
    container.querySelectorAll('[data-rl-tab]').forEach((b) => {
      const on = b.dataset.rlTab === tab;
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.tabIndex = on ? 0 : -1;
    });
    const hint = q('rlPassageHint');
    if (hint) hint.hidden = state.isSubmitted || state.mode !== 'reading';
    updateNavigationButtons();
    scrollStageTop();
  }

  function scrollStageTop() {
    const stage = q('testContainer');
    if (stage) stage.scrollTop = 0;
  }

  // ====================================================================
  // QUESTIONS
  // ====================================================================
  function renderQuestions() {
    const containerEl = q('questionsContainer');
    containerEl.innerHTML = '';
    state.questions.forEach((question, index) => {
      containerEl.appendChild(createQuestionCard(question, index));
    });
    showQuestion(state.currentQuestionIndex || 0);
  }

  function answeredMark() {
    return (
      '<span class="rl-q__answered"> · <i class="fas fa-check" aria-hidden="true"></i> ' +
      escapeHtmlForFurigana(T('test.answered', null, 'Answered')) +
      '</span>'
    );
  }

  function createQuestionCard(question, index) {
    const card = document.createElement('div');
    card.className = 'question-card rl-q';
    card.id = `question-${index}`;
    card.style.display = 'none';

    const isAnswered = state.answers[question.id] !== undefined;
    const selectedAnswer = state.answers[question.id];
    const lang = langCode();
    const langAttr = lang ? ` lang="${escapeHtmlForFurigana(lang)}"` : '';

    const qFuri =
      (state.furiganaPayload &&
        state.furiganaPayload.questions &&
        state.furiganaPayload.questions[index]) ||
      null;
    const textHtml = renderJpText(question.text, qFuri && qFuri.text);

    card.innerHTML = `
            <p class="ld-eyebrow rl-q__eyebrow"><span>${T('test.question_of', { current: index + 1, total: state.questions.length }, `Question ${index + 1} of ${state.questions.length}`)}</span>${isAnswered && !state.isSubmitted ? answeredMark() : ''}</p>
            <h3 class="ld-qtext rl-q__text" id="question-${index}-text"${langAttr}>${textHtml}</h3>
            <div class="answer-options rl-opts" id="answers-${index}" role="radiogroup" aria-labelledby="question-${index}-text">
                ${question.choices
                  .map((choice, choiceIndex) => {
                    const choiceLetter = String.fromCharCode(65 + choiceIndex);
                    const isSelected = selectedAnswer === choice;
                    const choiceFuri =
                      (qFuri && qFuri.choices && qFuri.choices[choiceIndex]) || null;
                    const choiceHtml = renderJpText(choice, choiceFuri);
                    const choiceAttr = escapeHtmlForFurigana(choice);
                    return `
                        <div class="answer-option ${isSelected ? 'selected' : ''}"
                             data-question-id="${question.id}"
                             data-choice="${choiceAttr}">
                            <input type="radio" class="rl-opt__radio" name="question-${index}" id="q${index}-${choiceIndex}"
                                   value="${choiceAttr}" ${isSelected ? 'checked' : ''}>
                            <label for="q${index}-${choiceIndex}" class="rl-opt__label">
                                <span class="ld-opt__key" aria-hidden="true">${choiceLetter}</span><span class="rl-opt__text"${langAttr}>${choiceHtml}</span>
                            </label>
                        </div>`;
                  })
                  .join('')}
            </div>
            ${
              state.isSubmitted && question.explanation
                ? `
                <div class="answer-explanation">
                    <strong><i class="fas fa-lightbulb me-2" aria-hidden="true"></i>${T('test.explanation', null, 'Explanation')}</strong>
                    ${escapeHtmlForFurigana(question.explanation)}
                </div>`
                : ''
            }`;
    return card;
  }

  function renderQuestionNavigation() {
    const nav = q('questionNavigation');
    nav.innerHTML = '';
    state.questions.forEach((question, index) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'rl-qnav__btn';
      btn.textContent = index + 1;
      btn.dataset.index = index;
      btn.setAttribute(
        'aria-label',
        T(
          'test.question_of',
          { current: index + 1, total: state.questions.length },
          `Question ${index + 1} of ${state.questions.length}`
        )
      );
      if (index === state.currentQuestionIndex && state.tab === 'questions') {
        btn.classList.add('active');
        btn.setAttribute('aria-current', 'step');
      }
      if (state.isSubmitted && typeof question.isCorrect === 'boolean') {
        btn.classList.add(question.isCorrect ? 'is-good' : 'is-bad');
      } else if (state.answers[question.id] !== undefined) {
        btn.classList.add('answered');
      }
      btn.addEventListener('click', () => {
        if (state.tab !== 'questions') setTab('questions');
        showQuestion(index);
      });
      nav.appendChild(btn);
    });
  }

  function showQuestion(index) {
    state.questions.forEach((_, i) => {
      const c = q(`question-${i}`);
      if (c) {
        c.style.display = 'none';
        c.classList.remove('is-current');
      }
    });
    const target = q(`question-${index}`);
    if (target) {
      target.style.display = 'block';
      target.classList.add('is-current');
      state.currentQuestionIndex = index;
      updateNavigationButtons();
      renderQuestionNavigation();
      updateProgress();
      scrollStageTop();
    }
  }

  // ====================================================================
  // AUDIO
  // ====================================================================
  function setupAudioPlayer() {
    const audio = state.audioElement;
    const playBtn = q('audioPlayBtn');
    const progressBar = q('audioProgressBar');
    const progressFill = q('audioProgressFill');
    const currentTimeEl = q('audioCurrentTime');
    const durationEl = q('audioDuration');
    const speedBtn = q('audioSpeedBtn');

    on(playBtn, 'click', () => {
      if (audio.paused) {
        audio.play();
        playBtn.innerHTML = '<i class="fas fa-pause"></i>';
      } else {
        audio.pause();
        playBtn.innerHTML = '<i class="fas fa-play"></i>';
      }
    });
    on(audio, 'timeupdate', () => {
      const progress = (audio.currentTime / audio.duration) * 100;
      progressFill.style.width = `${progress}%`;
      currentTimeEl.textContent = formatTime(audio.currentTime);
    });
    on(audio, 'loadedmetadata', () => {
      durationEl.textContent = formatTime(audio.duration);
    });
    // An audio element warmed ahead of the player has its metadata already.
    if (audio.readyState >= 1 && Number.isFinite(audio.duration)) {
      durationEl.textContent = formatTime(audio.duration);
    }
    on(progressBar, 'click', (e) => {
      const rect = progressBar.getBoundingClientRect();
      audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
    });
    on(speedBtn, 'click', () => {
      const speeds = [1.0, 1.25, 1.5, 0.75];
      const next = (speeds.indexOf(state.playbackSpeed) + 1) % speeds.length;
      state.playbackSpeed = speeds[next];
      audio.playbackRate = state.playbackSpeed;
      speedBtn.textContent = `${state.playbackSpeed}x`;
    });
    on(audio, 'ended', () => {
      playBtn.innerHTML = '<i class="fas fa-play"></i>';
    });
  }

  // ====================================================================
  // EVENTS
  // ====================================================================
  function setupEventListeners() {
    // Answer selection — scoped to this player's container (not document).
    on(container, 'click', (e) => {
      const answerOption = e.target.closest('.answer-option');
      if (answerOption && !state.isSubmitted) {
        const questionId = answerOption.dataset.questionId;
        state.answers[questionId] = answerOption.dataset.choice;
        answerOption.parentElement
          .querySelectorAll('.answer-option')
          .forEach((opt) => opt.classList.remove('selected'));
        answerOption.classList.add('selected');
        const radio = answerOption.querySelector('input[type="radio"]');
        if (radio) radio.checked = true;
        const eyebrow = answerOption.closest('.question-card');
        const mark = eyebrow && eyebrow.querySelector('.rl-q__eyebrow');
        if (mark && !mark.querySelector('.rl-q__answered')) {
          mark.insertAdjacentHTML('beforeend', answeredMark());
        }
        renderQuestionNavigation();
        updateProgress();
      }
    });

    // Passage | Questions switch (a tablist: arrows move between the tabs).
    container.querySelectorAll('[data-rl-tab]').forEach((tabBtn) => {
      on(tabBtn, 'click', () => setTab(tabBtn.dataset.rlTab));
      on(tabBtn, 'keydown', (e) => {
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
        const tabs = [...container.querySelectorAll('[data-rl-tab]')];
        const next =
          tabs[
            (tabs.indexOf(tabBtn) + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length
          ];
        e.preventDefault();
        setTab(next.dataset.rlTab);
        next.focus();
      });
    });

    on(q('prevBtn'), 'click', () => {
      if (state.currentQuestionIndex > 0) showQuestion(state.currentQuestionIndex - 1);
    });
    on(q('nextBtn'), 'click', () => {
      if (state.currentQuestionIndex < state.questions.length - 1)
        showQuestion(state.currentQuestionIndex + 1);
    });
    on(q('submitBtn'), 'click', confirmSubmit);

    const refBtn = q('toggleReferences');
    if (refBtn) {
      on(refBtn, 'click', () => {
        if (state.sentenceMode === 'produce') return;
        state.referencesShown = setReferencesVisible(q('transcriptText'), !state.referencesShown);
        updateReferenceToggle(true);
      });
    }

    const toggleBtn = q('toggleTranscript');
    if (toggleBtn) {
      on(toggleBtn, 'click', function () {
        const transcriptText = q('transcriptText');
        if (transcriptText.style.display === 'none') {
          transcriptText.style.display = 'block';
          this.innerHTML =
            '<i class="fas fa-eye" aria-hidden="true"></i>' +
            escapeHtmlForFurigana(T('test.hide', null, 'Hide'));
        } else {
          transcriptText.style.display = 'none';
          this.innerHTML =
            '<i class="fas fa-eye-slash" aria-hidden="true"></i>' +
            escapeHtmlForFurigana(T('test.show', null, 'Show'));
        }
      });
    }
  }

  function updateNavigationButtons() {
    // Previous / Next step through the questions; they rest while the
    // passage is on stage.
    const onQuestions = state.tab === 'questions';
    q('prevBtn').disabled = !onQuestions || state.currentQuestionIndex === 0;
    q('nextBtn').disabled =
      !onQuestions || state.currentQuestionIndex === state.questions.length - 1;
  }

  // ====================================================================
  // PROGRESS / SUBMIT
  // ====================================================================
  function updateProgress() {
    const total = state.questions.length;
    const answered = Object.keys(state.answers).length;
    const pct = total > 0 ? (answered / total) * 100 : 0;
    q('testProgressFill').style.width = `${pct}%`;
    q('progressText').textContent = T(
      'test.of_answered',
      { answered, total },
      `${answered}/${total} answered`
    );
    q('answeredCount').textContent = T(
      'test.answered_count',
      { answered, total },
      `${answered}/${total} answered`
    );
    // Submit stays locked until every question has an answer. After submit
    // the same id is the finish button, which must stay enabled.
    if (!state.isSubmitted) q('submitBtn').disabled = answered < total;
  }

  function confirmSubmit() {
    const total = state.questions.length;
    const answered = Object.keys(state.answers).length;
    if (answered < total) {
      if (
        !window.confirm(
          T('test.confirm_submit', null, 'You have unanswered questions. Submit anyway?')
        )
      )
        return;
    }
    submitTest();
  }

  // Test prestudy (wiki/features/test-prestudy.md): "Study first" on the
  // session test card. Opt-in from here is always available; the server marks
  // the offer `recommended` for hard tests when the learner chose "ask".
  function renderPrestudyOffer() {
    const offer = ctx.item && ctx.item.prestudy_offer;
    const L = window.LinguaPrestudyLinks;
    if (!offer || !ctx.item.slug || (L && L.isPrestudied(ctx.item.slug))) return;
    const pct = Math.round((Number(offer.unknown_share) || 0) * 100);
    const minutes = Number(offer.minutes_est) || 2;
    const params = new URLSearchParams({ type: mode, trigger: 'opt_in', return: 'session' });
    const bar = document.createElement('div');
    bar.className = `ld-note ${offer.recommended ? 'ld-note--warn' : ''} rl-offer`;
    bar.dataset.prestudyOffer = '1';
    bar.innerHTML = `<i class="bi bi-book-half" aria-hidden="true"></i>
        <span class="rl-offer__text"></span>
        <a class="ld-btn ld-btn--sm ${offer.recommended ? '' : 'ld-btn--ghost'}"></a>`;
    bar.querySelector('span').textContent = offer.recommended
      ? T(
          'session.prestudy.offer_recommended',
          { pct, n: minutes },
          `${pct}% of the key words are new to you. Study first? About ${minutes} min.`
        )
      : T(
          'session.prestudy.offer',
          { pct, n: minutes },
          `${pct}% of the key words are new to you. Study first (about ${minutes} min).`
        );
    const a = bar.querySelector('a');
    a.textContent = T('session.prestudy.title', null, 'Study first');
    a.href = `/test/${encodeURIComponent(ctx.item.slug)}/prestudy?${params.toString()}`;
    // First thing on the stage, under the answered count.
    const meta = q('rlMeta');
    if (meta && meta.parentNode) meta.parentNode.insertBefore(bar, meta.nextSibling);
  }

  async function submitTest() {
    try {
      showLoading(true);
      const responses = state.questions.map((question) => ({
        question_id: question.id,
        selected_answer: state.answers[question.id] || '',
      }));
      const timeTaken = Math.floor((Date.now() - state.startTime) / 1000);
      const startedAtIso = state.startTime ? new Date(state.startTime).toISOString() : null;
      const finishedAtIso = new Date().toISOString();

      const response = await window.authFetch(`/api/tests/${state.slug}/submit`, {
        method: 'POST',
        body: JSON.stringify({
          test_id: state.testId,
          test_mode: state.mode,
          responses,
          time_taken: timeTaken,
          furigana_used: state.furiganaUsedThisAttempt,
          started_at: startedAtIso,
          finished_at: finishedAtIso,
          prestudied: !!(
            window.LinguaPrestudyLinks && window.LinguaPrestudyLinks.isPrestudied(state.slug)
          ),
        }),
      });
      if (!response.ok) throw new Error('Failed to submit test');
      const result = await response.json();
      if (window.LinguaPrestudyLinks) window.LinguaPrestudyLinks.clearMarker(state.slug);
      state.isSubmitted = true;
      showResults(result);
      showLoading(false);
    } catch (e) {
      console.error('Submit error:', e);
      showLoading(false);
      alert(T('test.submit_failed', null, 'Failed to submit test.'));
    }
  }

  // ====================================================================
  // RESULTS
  // ====================================================================
  function showResults(result) {
    state.isSubmitted = true;
    const res = result && result.data ? result.data.result : result.result;

    // Reveal transcript for listening, make words clickable + add hint.
    if (state.mode !== 'reading') {
      q('transcriptCard').style.display = 'block';
    }
    wrapTranscriptWords();
    const transcriptCard = q('transcriptCard');
    if (transcriptCard && !q('wordHint')) {
      const hint = document.createElement('p');
      hint.className = 'word-hint ld-hint';
      hint.id = 'wordHint';
      hint.innerHTML =
        '<i class="fas fa-info-circle" aria-hidden="true"></i><span>' +
        T('test.tap_word_hint', null, 'Tap any word for its definition') +
        '</span>';
      transcriptCard.appendChild(hint);
    }

    // Mark correct/incorrect from the server's question_results.
    const resultsMap = new Map(
      ((res && res.question_results) || []).map((qr) => [qr.question_id, qr])
    );
    state.questions.forEach((question, index) => {
      const answersContainer = q(`answers-${index}`);
      if (!answersContainer) return;
      answersContainer.parentElement.classList.add('results-shown');
      const qResult = resultsMap.get(question.id);
      if (!qResult) return;
      question.correctAnswer = qResult.correct_answer;
      question.explanation = qResult.answer_explanation || null;
      question.isCorrect = !!qResult.is_correct;
      const answered = answersContainer.parentElement.querySelector('.rl-q__answered');
      if (answered) answered.remove();
      if (
        question.explanation &&
        !answersContainer.parentElement.querySelector('.answer-explanation')
      ) {
        const exp = document.createElement('div');
        exp.className = 'answer-explanation';
        const strong = document.createElement('strong');
        strong.innerHTML = '<i class="fas fa-lightbulb me-2" aria-hidden="true"></i>';
        strong.appendChild(document.createTextNode(T('test.explanation', null, 'Explanation')));
        exp.appendChild(strong);
        exp.appendChild(document.createTextNode(' ' + question.explanation));
        answersContainer.parentElement.appendChild(exp);
      }
      answersContainer.querySelectorAll('.answer-option').forEach((option) => {
        const choice = option.dataset.choice;
        if (choice === qResult.correct_answer) option.classList.add('correct');
        if (choice === qResult.selected_answer && !qResult.is_correct)
          option.classList.add('incorrect');
      });
    });

    // Success banner.
    const score = (res && res.score) || 0;
    const total = (res && res.total_questions) || state.questions.length;
    const percentage = total ? Math.round((score / total) * 100) : 0;
    q('successScoreText').textContent = T(
      'test.success_score',
      { score, total, percentage },
      `${score}/${total} (${percentage}%)`
    );
    q('successMessage').style.display = 'block';
    const offerBar = container.querySelector('[data-prestudy-offer]');
    if (offerBar) offerBar.remove();

    // Test prestudy: follow-up prime on the words behind wrong answers, then
    // Produce. Leaving the session for it completes this test first, so the
    // session resumes on the next item when the learner comes back.
    if (window.LinguaPrestudyLinks && !container.querySelector('[data-prestudy-actions]')) {
      window.LinguaPrestudyLinks.renderResultActions(q('successScoreText').parentElement, {
        slug: state.slug,
        type: state.mode,
        wrong: Math.max(0, total - score),
        prestudied: !!(res && res.prestudied),
        ...(ctx.resultActions || {
          returnTo: 'session',
          beforeLeave: () =>
            window.authFetch('/api/tests/daily-load/complete', {
              method: 'POST',
              body: JSON.stringify({ test_id: ctx.item.id, language_id: ctx.languageId }),
            }),
        }),
      });
    }

    // Replace the Submit button with a "Next" button that advances the
    // session (clone to drop the submit listener).
    const submitBtn = q('submitBtn');
    const nextBtn = submitBtn.cloneNode(true);
    submitBtn.replaceWith(nextBtn);
    nextBtn.disabled = false;
    if (typeof ctx.finishButton === 'function') {
      ctx.finishButton(nextBtn, result, { testId: state.testId });
    } else {
      nextBtn.classList.remove('btn-success', 'ld-btn--ok');
      nextBtn.classList.add('btn-primary');
      nextBtn.innerHTML =
        '<span>' +
        T('session.next_item', null, 'Next') +
        '</span><i class="fas fa-arrow-right ms-2" aria-hidden="true"></i>';
      nextBtn.onclick = () => ctx.onComplete(result);
    }

    // Review from the first question, with the score on top. A listening test
    // now gets its transcript as a second pane.
    state.currentQuestionIndex = 0;
    renderTabs();
    setTab('questions');
    showQuestion(0);

    if (res && res.word_quiz) {
      const quizTimer = setTimeout(() => wordQuiz.show(res.word_quiz), 600);
      cleanup.push(() => clearTimeout(quizTimer));
    }
  }

  // ====================================================================
  // WORD DEFINITION POPOVER
  // ====================================================================
  function wrapTranscriptWords() {
    const transcriptEl = q('transcriptText');
    const tokenMap = state.vocabTokenMap;
    // TASK-911: with server token spans the clickable view keeps the sentence
    // blocks (and their reference lines); the fallback is the flat token list.
    // Without server spans, derive them client-side so the translation toggle
    // and clickable words can coexist.
    if (tokenMap && tokenMap.length && state.sentences && !hasTokenSpans(state.sentences)) {
      const derived = deriveTokenSpans(state.sentences, tokenMap);
      if (derived) state.sentences = derived;
    }
    if (tokenMap && tokenMap.length && state.sentences && hasTokenSpans(state.sentences)) {
      renderSentenceBlocks(transcriptEl, state.sentences, {
        mode: state.sentenceMode,
        tokenMap,
        showReferences: state.referencesShown,
      });
      updateReferenceToggle(true);
      return;
    }
    transcriptEl.innerHTML = '';
    updateReferenceToggle(false);
    if (!tokenMap || !tokenMap.length) {
      transcriptEl.textContent = state.testData.transcript;
      return;
    }
    tokenMap.forEach(([text, senseId]) => {
      if (senseId) {
        const span = document.createElement('span');
        span.className = 'word-clickable';
        span.textContent = text;
        span.dataset.senseId = String(senseId);
        span.setAttribute('role', 'button');
        span.setAttribute('tabindex', '0');
        transcriptEl.appendChild(span);
      } else {
        transcriptEl.appendChild(document.createTextNode(text));
      }
    });
  }

  function getDefinition(senseId) {
    const key = String(senseId);
    return (state.definitions && state.definitions[key]) || null;
  }

  const wordPopover = {
    el: null,
    activeWord: null,
    backdrop: null,

    init() {
      this.el = q('wordDefinitionPopover');
      const transcriptText = q('transcriptText');

      on(transcriptText, 'click', (e) => {
        const wordSpan = e.target.closest('.word-clickable');
        if (wordSpan && state.isSubmitted) {
          e.stopPropagation();
          this.show(wordSpan);
        }
      });
      on(transcriptText, 'touchend', (e) => {
        const wordSpan = e.target.closest('.word-clickable');
        if (wordSpan && state.isSubmitted) {
          e.preventDefault();
          this.show(wordSpan);
        }
      });
      on(transcriptText, 'keydown', (e) => {
        if (
          (e.key === 'Enter' || e.key === ' ') &&
          e.target.classList.contains('word-clickable') &&
          state.isSubmitted
        ) {
          e.preventDefault();
          this.show(e.target);
        }
      });
      on(document, 'click', (e) => {
        if (
          this.el &&
          this.el.style.display !== 'none' &&
          !this.el.contains(e.target) &&
          !e.target.closest('.word-clickable')
        ) {
          this.hide();
        }
      });
      on(document, 'keydown', (e) => {
        if (e.key === 'Escape' && this.el && this.el.style.display !== 'none') this.hide();
      });
      const reposition = () => {
        if (this.activeWord) this.position(this.activeWord);
      };
      on(window, 'scroll', reposition, { passive: true });
      // The page itself does not scroll in task mode: the stage does.
      on(container, 'scroll', reposition, { capture: true, passive: true });
      on(window, 'resize', reposition);
    },

    show(wordSpan) {
      const senseId = wordSpan.dataset.senseId;
      if (!senseId) return;
      if (this.activeWord === wordSpan && this.el.style.display !== 'none') {
        this.hide();
        return;
      }
      if (this.activeWord) this.activeWord.classList.remove('word-active');
      this.activeWord = wordSpan;
      wordSpan.classList.add('word-active');

      const def = getDefinition(senseId);
      if (!def) return;
      q('popoverLoading').style.display = 'none';
      q('popoverError').style.display = 'none';
      q('popoverWord').textContent = def.word;
      if (langCode()) q('popoverWord').setAttribute('lang', langCode());
      q('popoverPOS').textContent = def.part_of_speech || '';
      q('popoverDefinition').textContent = def.definition;
      const readingEl = q('popoverReading');
      // Chinese: tone marks only (the server already sends that form; this
      // also covers a response cached from before it did).
      const reading = displayPronunciation(def.reading, langCode());
      if (reading) {
        readingEl.textContent = reading;
        readingEl.style.display = 'block';
      } else readingEl.style.display = 'none';
      q('popoverBody').style.display = 'block';
      this.el.style.display = 'block';
      if (ctx.popoverBackdrop && window.innerWidth <= 768) this.showBackdrop();
      this.position(wordSpan);
    },

    showBackdrop() {
      if (!this.backdrop) {
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'word-popover-backdrop';
        on(this.backdrop, 'click', () => this.hide());
        document.body.appendChild(this.backdrop);
        cleanup.push(() => this.backdrop.remove());
      }
      this.backdrop.style.display = 'block';
    },

    position(wordSpan) {
      const rect = wordSpan.getBoundingClientRect();
      const isMobile = window.innerWidth <= 768;
      if (isMobile) {
        Object.assign(this.el.style, {
          position: 'fixed',
          bottom: '0',
          left: '0',
          right: '0',
          top: 'auto',
        });
        this.el.classList.add('word-popover-mobile');
        this.el.classList.remove('word-popover-above');
      } else {
        this.el.classList.remove('word-popover-mobile');
        const popHeight = this.el.offsetHeight;
        const popWidth = 300;
        const spaceAbove = rect.top;
        const spaceBelow = window.innerHeight - rect.bottom;
        let top;
        if (spaceBelow >= popHeight + 8 || spaceBelow >= spaceAbove) {
          top = rect.bottom + 8;
          this.el.classList.remove('word-popover-above');
        } else {
          top = rect.top - popHeight - 8;
          this.el.classList.add('word-popover-above');
        }
        let left = rect.left + rect.width / 2 - popWidth / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - popWidth - 8));
        Object.assign(this.el.style, {
          position: 'fixed',
          top: `${top}px`,
          left: `${left}px`,
          bottom: 'auto',
          right: 'auto',
        });
      }
    },

    hide() {
      if (!this.el) return;
      this.el.style.display = 'none';
      this.el.classList.remove('word-popover-mobile', 'word-popover-above');
      if (this.activeWord) {
        this.activeWord.classList.remove('word-active');
        this.activeWord = null;
      }
      if (this.backdrop) this.backdrop.style.display = 'none';
    },
  };

  // ====================================================================
  // WORD QUIZ MODAL
  // ====================================================================
  const wordQuiz = {
    candidates: [],
    currentIndex: 0,
    results: [],
    attemptId: null,
    languageId: null,
    startTime: 0,

    show(quizData) {
      if (!quizData || !quizData.candidates || quizData.candidates.length === 0) return;
      this.candidates = quizData.candidates;
      this.attemptId = quizData.attempt_id || null;
      this.languageId = state.testData?.language_id || ctx.languageId || 1;
      this.currentIndex = 0;
      this.results = [];
      q('wordQuizBackdrop').style.display = 'block';
      q('wordQuizModal').style.display = 'block';
      q('quizSkipBtn').onclick = () => this.close();
      q('quizNextBtn').onclick = () => this.advance();
      q('quizNextBtn').style.display = 'none';
      this.renderQuestion();
    },

    renderQuestion() {
      const item = this.candidates[this.currentIndex];
      if (!item) return;
      q('quizLemma').textContent = item.lemma;
      if (langCode()) q('quizLemma').setAttribute('lang', langCode());
      const pronEl = q('quizPronunciation');
      // Chinese: tone-marked pinyin only, never "biàn dé (bian4 de2)".
      const pron =
        window.LinguaLanguages.hasFeature(this.languageId, 'pinyin') ||
        window.LinguaLanguages.hasFeature(langCode(), 'pinyin')
          ? formatPinyin(item.pronunciation)
          : item.pronunciation;
      if (pron) {
        pronEl.textContent = pron;
        pronEl.style.display = 'block';
      } else pronEl.style.display = 'none';
      q('quizProgress').textContent = `${this.currentIndex + 1} / ${this.candidates.length}`;
      const optionsEl = q('quizOptions');
      optionsEl.innerHTML = '';
      item.options.forEach((option) => {
        const btn = document.createElement('button');
        btn.className = 'quiz-option';
        btn.textContent = option;
        btn.type = 'button';
        btn.onclick = () => this.selectAnswer(option, item);
        optionsEl.appendChild(btn);
      });
      this.startTime = Date.now();
    },

    selectAnswer(selected, item) {
      const isCorrect = selected === item.correct_definition;
      this.results.push({
        sense_id: item.sense_id,
        selected_answer: selected,
        correct_answer: item.correct_definition,
        is_correct: isCorrect,
        response_time_ms: Date.now() - this.startTime,
      });
      q('quizOptions')
        .querySelectorAll('.quiz-option')
        .forEach((btn) => {
          btn.classList.add('quiz-answered');
          if (btn.textContent === item.correct_definition) btn.classList.add('quiz-correct');
          if (btn.textContent === selected && !isCorrect) btn.classList.add('quiz-incorrect');
        });
      if (isCorrect) setTimeout(() => this.advance(), 800);
      else q('quizNextBtn').style.display = '';
    },

    advance() {
      q('quizNextBtn').style.display = 'none';
      this.currentIndex++;
      if (this.currentIndex < this.candidates.length) this.renderQuestion();
      else this.submitAndClose();
    },

    async submitAndClose() {
      this.close();
      if (this.results.length === 0) return;
      try {
        await window.authFetch('/api/vocabulary/word-quiz', {
          method: 'POST',
          body: JSON.stringify({
            attempt_id: this.attemptId,
            language_id: this.languageId,
            results: this.results,
          }),
        });
      } catch (e) {
        console.error('Word quiz submission failed:', e);
      }
    },

    close() {
      const bd = q('wordQuizBackdrop');
      if (bd) bd.style.display = 'none';
      const md = q('wordQuizModal');
      if (md) md.style.display = 'none';
    },
  };

  // ====================================================================
  // UTILITIES
  // ====================================================================
  function showLoading(show) {
    setLoading(container, show);
  }

  function showError(message) {
    // errorState lives INSIDE testContainer (see MARKUP), so hiding
    // testContainer must not happen before errorState is unhidden — doing it
    // in the other order (or hiding the shared parent at all) hides the error
    // message along with everything else, which is exactly what made a
    // failed load look like a blank page instead of an error.
    const tc = q('testContainer');
    const err = q('errorState');
    if (err) {
      q('errorMessage').textContent = message;
      err.style.display = 'block';
    }
    if (tc) {
      Array.from(tc.children).forEach((child) => {
        if (child !== err) child.style.display = 'none';
      });
    }
    // Nothing to answer or submit: the dock goes too.
    const dock = q('testActions');
    if (dock) dock.style.display = 'none';
  }

  function startTimer() {
    state._timer = setInterval(() => {
      if (!state.isSubmitted && state.startTime) {
        const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
        const el = q('elapsedTime');
        if (el) el.textContent = formatClock(elapsed);
        if (frame && typeof frame.setHeader === 'function') {
          frame.setHeader({ end: formatClock(elapsed) });
        }
      }
    }, 1000);
  }

  return {
    rerender() {
      if (!state.testData) return;
      renderQuestions();
      renderQuestionNavigation();
      updateProgress();
      localize(container);
      fillHeader();
    },
    destroy() {
      if (state._timer) {
        clearInterval(state._timer);
        state._timer = null;
      }
      if (state.audioElement) {
        try {
          state.audioElement.pause();
        } catch (_) {}
      }
      document.body.classList.remove('test-page');
      cleanup.forEach((fn) => {
        try {
          fn();
        } catch (_) {}
      });
    },
  };
}

// ========================================================================
// MARKUP (reading + listening; dictation handled by its own player)
// One .ld-screen: a scrolling .ld-stage (#testContainer) and a pinned
// .ld-dock (#testActions). Styles: static/css/redesign/tests.css.
// ========================================================================
const MARKUP = `
<div class="ld-screen rl-player">
<div id="loadingOverlay" class="loading-overlay rl-loading" style="display:none;">
    <div class="loading-spinner" role="status"><div class="spinner-icon"></div>
        <p class="mb-0" data-i18n="test.loading">Loading test...</p></div>
</div>

<div class="ld-stage rl-stage" id="testContainer">
    <div id="errorState" class="ld-note ld-note--bad rl-error" role="alert" style="display:none;">
        <h2 class="ld-h2"><i class="fas fa-exclamation-triangle me-2" aria-hidden="true"></i><span data-i18n="test.error_title">Error Loading Test</span></h2>
        <p id="errorMessage" class="mb-2"></p>
    </div>

    <div class="rl-head" id="rlHead">
        <h1 class="ld-h2 mb-0" id="testTitle"><span id="testTitleText" data-i18n="common.loading">Loading...</span></h1>
        <div class="ld-wrap">
            <span class="ld-tag" id="testLanguage"></span>
            <span class="ld-tag" id="testDifficulty"></span>
            <span class="ld-tag ld-tag--brand" id="testType"></span>
            <span class="ld-tag ld-num" id="timerText"><i class="far fa-clock me-1" aria-hidden="true"></i><span id="elapsedTime">00:00</span></span>
        </div>
    </div>

    <div class="ld-row ld-between rl-meta" id="rlMeta">
        <span class="ld-small ld-num rl-meta__count" id="progressText" aria-live="polite"></span>
        <label class="furigana-toggle" id="furiganaToggleLabel" title="Furigana over kanji (halves ELO change)">
            <input type="checkbox" id="furiganaToggle" role="switch">
            <span class="rl-sw" aria-hidden="true"></span><span lang="ja">ふりがな</span>
        </label>
    </div>
    <div class="ld-bar rl-progress" aria-hidden="true"><i class="test-progress-fill" id="testProgressFill" style="width:0%"></i></div>

    <div id="successMessage" class="rl-success" style="display:none;">
        <div class="ld-note ld-note--ok ld-col" role="status">
            <b data-i18n="test.success_title">Test submitted successfully!</b>
            <p class="mb-0" id="successScoreText"></p>
        </div>
    </div>

    <div id="audioPlayerCard" class="rl-audio" style="display:none;">
        <h2 class="visually-hidden" data-i18n="test.audio">Audio</h2>
        <div class="audio-controls rl-audio__row">
            <button class="rl-audio__play" id="audioPlayBtn" type="button" aria-label="Play or pause audio" data-t-aria="test.play_pause"><i class="fas fa-play" aria-hidden="true"></i></button>
            <div class="rl-audio__track">
                <div class="rl-audio__bar" id="audioProgressBar"><div class="rl-audio__fill" id="audioProgressFill"></div></div>
                <div class="rl-audio__times ld-num"><span id="audioCurrentTime">0:00</span><span id="audioDuration">0:00</span></div>
            </div>
            <button class="ld-chip ld-num rl-audio__speed" id="audioSpeedBtn" type="button" aria-label="Playback speed" data-t-aria="test.playback_speed">1.0x</button>
        </div>
        <audio id="audioElement" preload="auto"></audio>
    </div>

    <div class="ld-seg rl-tabs" id="rlTabs" role="tablist" hidden>
        <button type="button" role="tab" id="rlTabPassage" data-rl-tab="passage" aria-controls="rlPassagePane">Reading Passage</button>
        <button type="button" role="tab" id="rlTabQuestions" data-rl-tab="questions" aria-controls="rlQuestionsPane" data-i18n="test.questions">Questions</button>
    </div>

    <div id="rlPassagePane" class="rl-pane" role="tabpanel" aria-labelledby="rlTabPassage">
        <div id="transcriptCard" class="rl-passage" style="display:none;">
            <div class="rl-passage__head">
                <h2 class="ld-eyebrow" id="rlPassageLabel">Reading Passage</h2>
                <div class="rl-passage__actions">
                    <button class="ld-chip" id="toggleReferences" type="button" style="display:none;">
                        <i class="fas fa-language" aria-hidden="true"></i><span data-i18n="test.show_translation">Show translation</span>
                    </button>
                    <button class="ld-chip" id="toggleTranscript" type="button">
                        <i class="fas fa-eye" aria-hidden="true"></i><span data-i18n="test.hide">Hide</span>
                    </button>
                </div>
            </div>
            <div class="transcript-text rl-passage__text" id="transcriptText"></div>
        </div>
        <p class="ld-hint rl-passage__hint" id="rlPassageHint" data-t="test.tap_after_submit" hidden>Words become tappable after you submit.</p>
    </div>

    <div id="rlQuestionsPane" class="rl-pane" role="tabpanel" aria-labelledby="rlTabQuestions">
        <h2 class="visually-hidden" data-i18n="test.questions">Questions</h2>
        <div class="rl-qnav" id="questionNavigation" role="group" aria-label="Questions" data-t-aria="test.questions"></div>
        <div id="questionsContainer"></div>
    </div>

    <div id="wordDefinitionPopover" class="word-popover" role="dialog" aria-live="polite" style="display:none;">
        <div class="word-popover-content">
            <div class="word-popover-loading" id="popoverLoading">
                <div class="spinner-icon" style="width:24px;height:24px;border-width:3px;margin:0 auto;"></div>
            </div>
            <div class="word-popover-body" id="popoverBody" style="display:none;">
                <div class="word-popover-header">
                    <span class="word-popover-word" id="popoverWord"></span>
                    <span class="word-popover-pos" id="popoverPOS"></span>
                </div>
                <div class="word-popover-reading" id="popoverReading" style="display:none;"></div>
                <div class="word-popover-definition" id="popoverDefinition"></div>
            </div>
            <div class="word-popover-error" id="popoverError" style="display:none;">
                <i class="fas fa-exclamation-circle me-1" aria-hidden="true"></i><span data-i18n="test.definition_error">Could not load definition</span>
            </div>
        </div>
    </div>
</div>

<div id="wordQuizBackdrop" class="word-quiz-backdrop" style="display:none;"></div>
<div id="wordQuizModal" class="word-quiz-modal" role="dialog" aria-modal="false" aria-labelledby="wordQuizTitle" style="display:none;">
    <div class="word-quiz-header"><h2 id="wordQuizTitle" data-t="test.vocab_check.title">Quick Vocab Check</h2>
        <div class="quiz-subtitle" data-t="test.vocab_check.subtitle">Help us track your vocabulary!</div></div>
    <div class="word-quiz-word"><div class="quiz-lemma" id="quizLemma"></div><div class="quiz-pronunciation" id="quizPronunciation"></div></div>
    <div class="word-quiz-prompt" data-t="test.vocab_check.prompt">What does this word mean?</div>
    <div id="quizOptions"></div>
    <div class="word-quiz-footer">
        <span class="quiz-progress ld-num" id="quizProgress"></span>
        <button class="ld-btn ld-btn--sm" id="quizNextBtn" type="button" style="display:none;"><span data-i18n="test.next">Next</span> <i class="fas fa-arrow-right ms-1" aria-hidden="true"></i></button>
        <button class="ld-link ld-link--quiet quiz-skip-btn" id="quizSkipBtn" type="button" data-t="test.vocab_check.skip">Skip All</button>
    </div>
</div>

<div class="ld-dock rl-dock" id="testActions">
    <div class="ld-row">
        <button class="ld-btn ld-btn--ghost ld-btn--icon" id="prevBtn" type="button" aria-label="Previous" data-t-aria="test.previous" disabled><i class="fas fa-arrow-left" aria-hidden="true"></i></button>
        <button class="ld-btn ld-btn--ghost ld-btn--icon" id="nextBtn" type="button" aria-label="Next" data-t-aria="test.next"><i class="fas fa-arrow-right" aria-hidden="true"></i></button>
        <button class="ld-btn ld-btn--ok btn-success rl-submit" id="submitBtn" type="button" disabled><i class="fas fa-check-circle me-2" aria-hidden="true"></i><span data-i18n="test.submit_test">Submit Test</span></button>
    </div>
    <span id="answeredCount" hidden>0/0</span>
</div>
</div>
`;
