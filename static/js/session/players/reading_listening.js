// static/js/session/players/reading_listening.js
// Reading + Listening comprehension player for the daily-session runner.
// Ported from templates/test.html (the dictation branch is handled by a
// dedicated player). Renders into a provided container, scopes all DOM lookups
// to it, tracks listeners/timers for clean teardown, and calls
// ctx.onComplete(result) when the learner finishes instead of redirecting.

const LANGUAGE_LOCALE_MAP = { cn: 'zh', jp: 'ja', en: 'en', es: 'es' };

const T = (key, params, fallback) =>
  window.LinguaI18n && typeof window.LinguaI18n.t === 'function'
    ? window.LinguaI18n.t(key, params)
    : fallback || key;

const nativeName = (code) =>
  (window.LinguaMetadata && LinguaMetadata.getNativeName && LinguaMetadata.getNativeName(code)) ||
  (code ? String(code).toUpperCase() : '');

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
  };

  // --- lifecycle plumbing -------------------------------------------------
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
      if (state._timer) {
        clearInterval(state._timer);
        state._timer = null;
      }
      if (state.audioElement) {
        try {
          state.audioElement.pause();
        } catch (_) {}
      }
      cleanup.forEach((fn) => {
        try {
          fn();
        } catch (_) {}
      });
    },
  };

  // ====================================================================
  // INIT
  // ====================================================================
  async function init() {
    try {
      showLoading(true);
      await loadTestData();
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
    const response = await window.authFetch(`/api/tests/test/${state.slug}`);
    if (!response.ok) throw new Error(`Failed to load test (${response.status})`);
    const data = await response.json();
    const payload = data.data || data;
    if (!payload.test_data || !payload.questions_data) {
      throw new Error('Invalid test data received');
    }
    state.testData = payload.test_data;
    state.testId = payload.test_data.id;
    state.vocabTokenMap = payload.vocab_token_map || [];
    state.definitions = payload.definitions || {};
    state.furiganaPayload = payload.furigana_payload || null;
    state.questions = payload.questions_data.map((qd) => ({
      id: qd.id,
      text: qd.question_text,
      choices: Array.isArray(qd.choices) ? qd.choices : JSON.parse(qd.choices || '[]'),
      correctAnswer: qd.correct_answer,
      explanation: qd.answer_explanation,
      type: qd.question_type,
    }));
  }

  // ====================================================================
  // FURIGANA
  // ====================================================================
  function escapeHtmlForFurigana(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

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

    try {
      const resp = await window.authFetch('/api/users/preferences', { method: 'GET' });
      if (resp && resp.ok) {
        const body = await resp.json();
        const prefs = (body && (body.data || body).exercise_preferences) || {};
        state.furiganaEnabled = !!prefs.furigana_enabled;
      }
    } catch (_) {
      /* default off */
    }

    cb.checked = state.furiganaEnabled;
    if (state.furiganaEnabled) state.furiganaUsedThisAttempt = true;

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
        const t = q('transcriptText');
        if (t)
          t.innerHTML = renderJpText(
            state.testData.transcript,
            state.furiganaPayload && state.furiganaPayload.transcript
          );
      }
      renderQuestions();
    });
  }

  // ====================================================================
  // UI
  // ====================================================================
  function initializeUI() {
    q('testTitleText').textContent = state.testData.title || state.testData.topic;
    q('testLanguage').textContent = nativeName(state.testData.language);
    q('testDifficulty').textContent = T(
      'test.level',
      { level: state.testData.difficulty },
      `Level ${state.testData.difficulty}`
    );
    q('testType').textContent = state.mode.charAt(0).toUpperCase() + state.mode.slice(1);

    setupFuriganaToggle();

    if (state.mode === 'reading') initializeReadingTest();
    else initializeListeningTest();

    renderQuestions();
    renderQuestionNavigation();
    setupEventListeners();
    wordPopover.init();
    updateProgress();
  }

  function initializeReadingTest() {
    q('transcriptCard').style.display = 'block';
    q('transcriptText').innerHTML = renderJpText(
      state.testData.transcript,
      state.furiganaPayload && state.furiganaPayload.transcript
    );
  }

  function initializeListeningTest() {
    q('audioPlayerCard').style.display = 'block';
    state.audioElement = q('audioElement');
    state.audioElement.src = state.testData.audio_url;
    setupAudioPlayer();
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

  function createQuestionCard(question, index) {
    const card = document.createElement('div');
    card.className = 'question-card mb-4';
    card.id = `question-${index}`;
    card.style.display = 'none';

    const isAnswered = state.answers[question.id] !== undefined;
    const selectedAnswer = state.answers[question.id];

    const qFuri =
      (state.furiganaPayload &&
        state.furiganaPayload.questions &&
        state.furiganaPayload.questions[index]) ||
      null;
    const textHtml = renderJpText(question.text, qFuri && qFuri.text);

    card.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <span class="badge bg-primary">${T('test.question_of', { current: index + 1, total: state.questions.length }, `Question ${index + 1} of ${state.questions.length}`)}</span>
                ${isAnswered ? '<span class="badge bg-success"><i class="fas fa-check me-1"></i>' + T('test.answered', null, 'Answered') + '</span>' : ''}
            </div>
            <h3 class="mb-4 h5">${textHtml}</h3>
            <div class="answer-options" id="answers-${index}">
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
                            <input type="radio" name="question-${index}" id="q${index}-${choiceIndex}"
                                   value="${choiceAttr}" ${isSelected ? 'checked' : ''}>
                            <label for="q${index}-${choiceIndex}" class="ms-2 mb-0">
                                <strong>${choiceLetter}.</strong> ${choiceHtml}
                            </label>
                        </div>`;
                  })
                  .join('')}
            </div>
            ${
              state.isSubmitted && question.explanation
                ? `
                <div class="answer-explanation">
                    <strong><i class="fas fa-lightbulb me-2"></i>${T('test.explanation', null, 'Explanation')}</strong>
                    ${question.explanation}
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
      btn.className = 'question-nav-btn';
      btn.textContent = index + 1;
      btn.dataset.index = index;
      if (index === state.currentQuestionIndex) btn.classList.add('active');
      if (state.answers[question.id] !== undefined) btn.classList.add('answered');
      btn.addEventListener('click', () => showQuestion(index));
      nav.appendChild(btn);
    });
  }

  function showQuestion(index) {
    state.questions.forEach((_, i) => {
      const c = q(`question-${i}`);
      if (c) c.style.display = 'none';
    });
    const target = q(`question-${index}`);
    if (target) {
      target.style.display = 'block';
      state.currentQuestionIndex = index;
      updateNavigationButtons();
      renderQuestionNavigation();
      updateProgress();
      window.scrollTo({ top: 0, behavior: 'smooth' });
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

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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
        renderQuestionNavigation();
        updateProgress();
      }
    });

    on(q('prevBtn'), 'click', () => {
      if (state.currentQuestionIndex > 0) showQuestion(state.currentQuestionIndex - 1);
    });
    on(q('nextBtn'), 'click', () => {
      if (state.currentQuestionIndex < state.questions.length - 1)
        showQuestion(state.currentQuestionIndex + 1);
    });
    on(q('submitBtn'), 'click', confirmSubmit);

    const toggleBtn = q('toggleTranscript');
    if (toggleBtn) {
      on(toggleBtn, 'click', function () {
        const transcriptText = q('transcriptText');
        if (transcriptText.style.display === 'none') {
          transcriptText.style.display = 'block';
          this.innerHTML = '<i class="fas fa-eye me-1"></i>' + T('test.hide', null, 'Hide');
        } else {
          transcriptText.style.display = 'none';
          this.innerHTML = '<i class="fas fa-eye-slash me-1"></i>' + T('test.show', null, 'Show');
        }
      });
    }
  }

  function updateNavigationButtons() {
    q('prevBtn').disabled = state.currentQuestionIndex === 0;
    q('nextBtn').disabled = state.currentQuestionIndex === state.questions.length - 1;
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
    q('submitBtn').disabled = answered < total;
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
        }),
      });
      if (!response.ok) throw new Error('Failed to submit test');
      const result = await response.json();
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
      q('transcriptText').innerHTML = renderJpText(
        state.testData.transcript,
        state.furiganaPayload && state.furiganaPayload.transcript
      );
    }
    wrapTranscriptWords();
    const transcriptCard = q('transcriptCard');
    if (transcriptCard && !q('wordHint')) {
      const hint = document.createElement('p');
      hint.className = 'word-hint';
      hint.id = 'wordHint';
      hint.innerHTML =
        '<i class="fas fa-info-circle"></i><span>' +
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

    // Replace the Submit button with a "Next" button that advances the
    // session (clone to drop the submit listener).
    const submitBtn = q('submitBtn');
    const nextBtn = submitBtn.cloneNode(true);
    submitBtn.replaceWith(nextBtn);
    nextBtn.disabled = false;
    nextBtn.classList.remove('btn-success');
    nextBtn.classList.add('btn-primary');
    nextBtn.innerHTML =
      '<span>' +
      T('session.next_item', null, 'Next') +
      '</span><i class="fas fa-arrow-right ms-2"></i>';
    nextBtn.onclick = () => ctx.onComplete(result);

    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (res && res.word_quiz) {
      setTimeout(() => wordQuiz.show(res.word_quiz), 600);
    }
  }

  // ====================================================================
  // WORD DEFINITION POPOVER
  // ====================================================================
  function wrapTranscriptWords() {
    const transcriptEl = q('transcriptText');
    const tokenMap = state.vocabTokenMap;
    transcriptEl.innerHTML = '';
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
      q('popoverPOS').textContent = def.part_of_speech || '';
      q('popoverDefinition').textContent = def.definition;
      const readingEl = q('popoverReading');
      if (def.reading) {
        readingEl.textContent = def.reading;
        readingEl.style.display = 'block';
      } else readingEl.style.display = 'none';
      q('popoverBody').style.display = 'block';
      this.el.style.display = 'block';
      this.position(wordSpan);
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
      const pronEl = q('quizPronunciation');
      if (item.pronunciation) {
        pronEl.textContent = item.pronunciation;
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
    const el = q('loadingOverlay');
    if (el) el.style.display = show ? 'flex' : 'none';
  }

  function showError(message) {
    const err = q('errorState');
    if (err) {
      err.style.display = 'block';
      q('errorMessage').textContent = message;
    }
    const tc = q('testContainer');
    if (tc) tc.style.display = 'none';
    const ta = q('testActions');
    if (ta) ta.style.display = 'none';
  }

  function startTimer() {
    state._timer = setInterval(() => {
      if (!state.isSubmitted && state.startTime) {
        const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
        const m = Math.floor(elapsed / 60),
          s = elapsed % 60;
        const el = q('elapsedTime');
        if (el)
          el.textContent = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
      }
    }, 1000);
  }
}

// ========================================================================
// MARKUP (reading + listening; dictation handled by its own player)
// ========================================================================
const MARKUP = `
<div id="loadingOverlay" class="loading-overlay" style="display:none;">
    <div class="loading-spinner"><div class="spinner-icon"></div>
        <p class="mb-0 text-slate-600" data-i18n="test.loading">Loading test...</p></div>
</div>

<div class="test-header">
    <div class="container py-3">
        <div class="row align-items-center">
            <div class="col-md-6">
                <h1 class="mb-0 h5" id="testTitle">
                    <i class="fas fa-book-open text-primary me-2"></i>
                    <span id="testTitleText" data-i18n="common.loading">Loading...</span>
                </h1>
            </div>
            <div class="col-md-6 text-md-end mt-2 mt-md-0">
                <span class="badge bg-primary me-2" id="testLanguage"></span>
                <span class="badge bg-secondary me-2" id="testDifficulty"></span>
                <span class="badge bg-info" id="testType"></span>
                <label class="furigana-toggle" id="furiganaToggleLabel" title="Furigana over kanji (halves ELO change)">
                    <input type="checkbox" id="furiganaToggle"><span>ふりがな</span>
                </label>
            </div>
        </div>
        <div class="row mt-2"><div class="col-12">
            <div class="d-flex justify-content-between text-sm text-slate-500">
                <span id="progressText"></span>
                <span id="timerText"><i class="far fa-clock me-1"></i><span id="elapsedTime">00:00</span></span>
            </div>
        </div></div>
    </div>
    <div class="test-progress-bar"><div class="test-progress-fill" id="testProgressFill" style="width:0%"></div></div>
</div>

<div id="successMessage" class="container my-3" style="display:none;">
    <div class="alert alert-success alert-dismissible fade show" role="alert">
        <div class="d-flex align-items-center">
            <i class="fas fa-check-circle me-3" style="font-size:24px;"></i>
            <div class="flex-grow-1">
                <h2 class="mb-2 h5" data-i18n="test.success_title">Test submitted successfully!</h2>
                <p class="mb-0" id="successScoreText"></p>
            </div>
        </div>
    </div>
</div>

<div class="container my-4" id="testContainer">
    <div id="errorState" class="alert alert-danger" style="display:none;">
        <h2 class="h5"><i class="fas fa-exclamation-triangle me-2"></i><span data-i18n="test.error_title">Error Loading Test</span></h2>
        <p id="errorMessage" class="mb-2"></p>
    </div>

    <div id="transcriptCard" class="transcript-card" style="display:none;">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h2 class="mb-0 h4"><i class="fas fa-file-alt text-primary me-2"></i><span data-i18n="test.reading_passage">Reading Passage</span></h2>
            <button class="btn btn-sm btn-secondary" id="toggleTranscript">
                <i class="fas fa-eye me-1"></i><span data-i18n="test.hide">Hide</span>
            </button>
        </div>
        <div class="transcript-text" id="transcriptText"></div>
    </div>

    <div id="audioPlayerCard" class="audio-player-card" style="display:none;">
        <h2 class="mb-3 h4"><i class="fas fa-headphones text-primary me-2"></i><span data-i18n="test.audio">Audio</span></h2>
        <div class="audio-controls">
            <button class="audio-play-button" id="audioPlayBtn"><i class="fas fa-play"></i></button>
            <div class="audio-progress-container">
                <div class="audio-progress-bar" id="audioProgressBar"><div class="audio-progress-fill" id="audioProgressFill"></div></div>
                <div class="audio-times"><span id="audioCurrentTime">0:00</span><span id="audioDuration">0:00</span></div>
            </div>
            <button class="audio-speed-btn" id="audioSpeedBtn">1.0x</button>
        </div>
        <audio id="audioElement" preload="metadata"></audio>
    </div>

    <div class="card mb-4"><div class="card-body">
        <h2 class="text-slate-500 mb-3 h6" data-i18n="test.questions">Questions</h2>
        <div class="question-navigation" id="questionNavigation"></div>
    </div></div>

    <div id="questionsContainer"></div>

    <div id="wordDefinitionPopover" class="word-popover" role="tooltip" aria-live="polite" style="display:none;">
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
                <i class="fas fa-exclamation-circle me-1"></i><span data-i18n="test.definition_error">Could not load definition</span>
            </div>
        </div>
    </div>
</div>

<div id="wordQuizBackdrop" class="word-quiz-backdrop" style="display:none;"></div>
<div id="wordQuizModal" class="word-quiz-modal" style="display:none;">
    <div class="word-quiz-header"><h2><i class="fas fa-spell-check me-2"></i>Quick Vocab Check</h2>
        <div class="quiz-subtitle">Help us track your vocabulary!</div></div>
    <div class="word-quiz-word"><div class="quiz-lemma" id="quizLemma"></div><div class="quiz-pronunciation" id="quizPronunciation"></div></div>
    <div class="word-quiz-prompt">What does this word mean?</div>
    <div id="quizOptions"></div>
    <div class="word-quiz-footer">
        <span class="quiz-progress" id="quizProgress"></span>
        <button class="btn btn-primary btn-sm" id="quizNextBtn" type="button" style="display:none;">Next <i class="fas fa-arrow-right ms-1"></i></button>
        <button class="quiz-skip-btn" id="quizSkipBtn" type="button">Skip All</button>
    </div>
</div>

<div class="test-actions" id="testActions">
    <div>
        <button class="btn btn-secondary" id="prevBtn" disabled><i class="fas fa-arrow-left me-2"></i><span data-i18n="test.previous">Previous</span></button>
        <button class="btn btn-secondary" id="nextBtn"><span data-i18n="test.next">Next</span><i class="fas fa-arrow-right ms-2"></i></button>
    </div>
    <div>
        <span class="text-slate-500 me-3" id="answeredCount">0/0</span>
        <button class="btn btn-success" id="submitBtn" disabled><i class="fas fa-check-circle me-2"></i><span data-i18n="test.submit_test">Submit Test</span></button>
    </div>
</div>
`;
