(function () {
  const RATING_MAP = { 1: 'again', 2: 'hard', 3: 'good', 4: 'easy' };
  const languageId = parseInt(localStorage.getItem('selectedLanguageId')) || 1;

  // Weekly-minutes active-time measurement (one timer + event id per card showing).
  const cardTimer = window.ActiveTimer ? window.ActiveTimer.create() : null;
  let cardEventId = null;

  // State
  const state = {
    allCards: [],
    filteredCards: [],
    currentIndex: 0,
    currentType: 'reading',
    isFlipped: false,
    ratings: { 1: 0, 2: 0, 3: 0, 4: 0 },
    reviewed: 0,
  };

  // DOM refs
  const els = {
    flashcard: document.getElementById('flashcard'),
    scene: document.getElementById('flashcardScene'),
    flashcardArea: document.getElementById('flashcardArea'),
    frontWord: document.getElementById('frontWord'),
    frontPronunciation: document.getElementById('frontPronunciation'),
    frontAudio: document.getElementById('frontAudio'),
    backAnswer: document.getElementById('backAnswer'),
    backContext: document.getElementById('backContext'),
    cardTypeIcon: document.getElementById('cardTypeIcon'),
    cardTypeLabel: document.getElementById('cardTypeLabel'),
    currentCardNum: document.getElementById('currentCardNum'),
    totalCards: document.getElementById('totalCards'),
    progressFill: document.getElementById('progressFill'),
    sessionComplete: document.getElementById('sessionComplete'),
    sessionStats: document.getElementById('sessionStats'),
    keyboardHint: document.getElementById('keyboardHint'),
    flipBtn: document.getElementById('flipBtn'),
    playAudioBtn: document.getElementById('playAudioBtn'),
    tabReading: document.getElementById('tabReading'),
    tabListening: document.getElementById('tabListening'),
    loading: document.getElementById('flashcardLoading'),
    empty: document.getElementById('flashcardEmpty'),
    screen: document.getElementById('fcScreen'),
    progressText: document.getElementById('fcProgressText'),
    doneMark: document.getElementById('fcDoneMark'),
  };

  // Redesign 2026-11: the screen's state drives what the pinned dock shows
  // (Flip / the four ratings / Browse Tests / Continue Practicing) and whether
  // the header shows "Card n of N".
  // loading | card | flipped | empty | done | error
  function setView(view) {
    if (els.screen) els.screen.dataset.fcState = view;
    if (els.progressText) els.progressText.hidden = view !== 'card' && view !== 'flipped';
  }

  // Seal glyph and target-language text, from the study language (卡 / 札, as
  // in the mockup). Decorative: without metadata there is simply no seal.
  const SEALS = { zh: '卡', ja: '札' };
  function applyStudyLanguage() {
    if (!window.LinguaMetadata || typeof window.LinguaMetadata.load !== 'function') return;
    Promise.resolve(window.LinguaMetadata.load())
      .then(function (meta) {
        const row = ((meta && meta.languages) || []).find(function (l) {
          return l.id === languageId;
        });
        const code = row && row.language_code;
        if (!code) return;
        [els.frontWord, els.backContext].forEach(function (node) {
          if (node) node.lang = code;
        });
        if (SEALS[code]) {
          if (els.doneMark) {
            els.doneMark.textContent = SEALS[code];
            els.doneMark.lang = code;
          }
          if (window.LinguaShell && window.LinguaShell.setTaskHeader) {
            window.LinguaShell.setTaskHeader({ glyph: SEALS[code] });
          }
        }
      })
      .catch(function () {
        /* decorative only */
      });
  }

  async function loadCards() {
    try {
      const resp = await window.authFetch(`/api/flashcards/due?language_id=${languageId}`);

      if (!resp.ok) throw new Error('Failed to load flashcards');

      const data = await resp.json();
      const cards = data.cards || [];

      // Map API cards to internal format with reading/listening variants
      state.allCards = [];
      cards.forEach(function (c) {
        // Reading card: show word → reveal definition
        state.allCards.push({
          card_id: c.card_id,
          sense_id: c.sense_id,
          type: 'reading',
          front: c.lemma,
          pronunciation: c.pronunciation || '',
          back: c.definition,
          context: c.example_sentence || '',
          audio_url: c.audio_url,
        });

        // Listening card (only if audio available)
        if (c.audio_url) {
          state.allCards.push({
            card_id: c.card_id,
            sense_id: c.sense_id,
            type: 'listening',
            front: null,
            pronunciation: '',
            back: c.lemma + (c.pronunciation ? ` (${c.pronunciation})` : ''),
            context: c.definition,
            audio_url: c.audio_url,
          });
        }
      });

      els.loading.style.display = 'none';

      if (state.allCards.length === 0) {
        els.empty.style.display = 'block';
        setView('empty');
      } else {
        filterCards('reading');
      }
    } catch (e) {
      console.error('Flashcard load error:', e);
      setView('error');
      els.loading.innerHTML =
        '<p class="text-danger"><i class="fas fa-exclamation-circle me-2"></i>Failed to load flashcards</p>';
    }
  }

  function filterCards(type) {
    state.currentType = type;
    state.filteredCards = state.allCards.filter(function (c) {
      return c.type === type;
    });
    state.currentIndex = 0;
    state.isFlipped = false;
    state.ratings = { 1: 0, 2: 0, 3: 0, 4: 0 };
    state.reviewed = 0;

    // Update tabs
    els.tabReading.classList.toggle('active', type === 'reading');
    els.tabListening.classList.toggle('active', type === 'listening');
    els.tabReading.setAttribute('aria-pressed', type === 'reading' ? 'true' : 'false');
    els.tabListening.setAttribute('aria-pressed', type === 'listening' ? 'true' : 'false');

    if (state.filteredCards.length === 0) {
      els.flashcardArea.style.display = 'none';
      els.keyboardHint.style.display = 'none';
      els.sessionComplete.style.display = 'none';
      els.empty.style.display = 'block';
      setView('empty');
      return;
    }

    // Show card area
    els.empty.style.display = 'none';
    els.flashcardArea.style.display = 'flex';
    els.keyboardHint.style.display = '';
    els.sessionComplete.style.display = 'none';

    renderCard();
  }

  function renderCard() {
    if (state.currentIndex >= state.filteredCards.length) {
      showSessionComplete();
      return;
    }

    const card = state.filteredCards[state.currentIndex];

    // Reset flip
    state.isFlipped = false;
    els.flashcard.classList.remove('is-flipped');
    setView('card');
    if (cardTimer) {
      cardEventId = window.ActiveTimer.newEventId();
      cardTimer.start();
    }

    // Front content
    if (card.type === 'reading') {
      els.frontWord.textContent = card.front;
      els.frontWord.style.display = '';
      if (card.pronunciation) {
        els.frontPronunciation.textContent = card.pronunciation;
        els.frontPronunciation.style.display = '';
      } else {
        els.frontPronunciation.style.display = 'none';
      }
      els.frontAudio.style.display = 'none';
      els.cardTypeIcon.className = 'fas fa-book-open';
      els.cardTypeLabel.textContent = window.LinguaI18n
        ? window.LinguaI18n.t('flashcards.reading')
        : 'Reading';
    } else {
      els.frontWord.style.display = 'none';
      els.frontPronunciation.style.display = 'none';
      els.frontAudio.style.display = '';
      els.cardTypeIcon.className = 'fas fa-headphones';
      els.cardTypeLabel.textContent = window.LinguaI18n
        ? window.LinguaI18n.t('flashcards.listening')
        : 'Listening';
    }

    // Back content
    els.backAnswer.textContent = card.back;
    els.backContext.textContent = card.context || '';

    // Progress
    els.currentCardNum.textContent = state.currentIndex + 1;
    els.totalCards.textContent = state.filteredCards.length;
    els.progressFill.style.width =
      ((state.currentIndex + 1) / state.filteredCards.length) * 100 + '%';
  }

  function flipCard() {
    state.isFlipped = !state.isFlipped;
    els.flashcard.classList.toggle('is-flipped', state.isFlipped);
    setView(state.isFlipped ? 'flipped' : 'card');
    // Move focus into the dock's ratings so keyboard / switch users land on them.
    if (state.isFlipped && document.activeElement === els.flipBtn) {
      const first = document.querySelector('.flashcard-rating-btn');
      if (first) first.focus({ preventScroll: true });
    }
  }

  function rateCard(rating) {
    const card = state.filteredCards[state.currentIndex];
    if (!card) return;

    rating = parseInt(rating);
    state.ratings[rating] = (state.ratings[rating] || 0) + 1;
    state.reviewed++;

    // Submit review to API (fire-and-forget). active_ms / client_event_id
    // feed the weekly "Studied this week" minutes (static/js/active-timer.js).
    const reviewBody = { card_id: card.card_id, rating: rating };
    if (cardTimer) {
      reviewBody.active_ms = cardTimer.stop();
      reviewBody.client_event_id = cardEventId;
    }
    window
      .authFetch('/api/flashcards/review', {
        method: 'POST',
        body: JSON.stringify(reviewBody),
      })
      .catch(function (e) {
        console.error('Review submit failed:', e);
      });

    // If "again", re-add to end of queue
    if (rating === 1) {
      state.filteredCards.push(Object.assign({}, card));
    }

    // Slide out animation
    els.flashcard.classList.add('flashcard-exit');

    setTimeout(function () {
      state.currentIndex++;
      state.isFlipped = false;
      els.flashcard.classList.remove('is-flipped', 'flashcard-exit');

      if (state.currentIndex >= state.filteredCards.length) {
        showSessionComplete();
      } else {
        renderCard();
        els.flashcard.classList.add('flashcard-enter');
        setTimeout(function () {
          els.flashcard.classList.remove('flashcard-enter');
        }, 300);
      }
    }, 300);
  }

  function showSessionComplete() {
    els.flashcardArea.style.display = 'none';
    els.keyboardHint.style.display = 'none';
    els.sessionComplete.style.display = 'flex';
    setView('done');

    const i18n = window.LinguaI18n;
    const stat = function (rating, cls, key, fallback) {
      return (
        '<div class="flashcard-stat ld-stat ' +
        cls +
        '"><div class="flashcard-stat-value ld-stat__n">' +
        (state.ratings[rating] || 0) +
        '</div><small class="flashcard-stat-label">' +
        (i18n ? i18n.t(key) : fallback) +
        '</small></div>'
      );
    };
    els.sessionStats.innerHTML =
      stat(1, 'fc-stat-again', 'flashcards.again', 'Again') +
      stat(2, 'fc-stat-hard', 'flashcards.hard', 'Hard') +
      stat(3, 'fc-stat-good', 'flashcards.good', 'Good') +
      stat(4, 'fc-stat-easy', 'flashcards.easy', 'Easy');
  }

  // Play audio for listening cards
  function playAudio() {
    const card = state.filteredCards[state.currentIndex];
    if (!card || !card.audio_url) return;

    const audio = new Audio(card.audio_url);
    audio.play().catch(function (e) {
      console.error('Audio playback failed:', e);
    });
  }

  // Event listeners
  els.flashcard.addEventListener('click', function (e) {
    if (e.target.closest('.flashcard-rating-btn') || e.target.closest('.flashcard-audio-btn'))
      return;
    if (!state.isFlipped) {
      flipCard();
    }
  });

  els.flipBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    if (!state.isFlipped) flipCard();
  });

  // Rating buttons
  document.querySelectorAll('.flashcard-rating-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      rateCard(this.dataset.rating);
    });
  });

  // Audio button
  els.playAudioBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    playAudio();
  });

  // Type tabs
  els.tabReading.addEventListener('click', function () {
    filterCards('reading');
  });
  els.tabListening.addEventListener('click', function () {
    filterCards('listening');
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', function (e) {
    if (els.sessionComplete.style.display !== 'none') return;
    if (els.flashcardArea.style.display === 'none') return;

    if (e.code === 'Space' || e.code === 'Enter') {
      e.preventDefault();
      if (!state.isFlipped) flipCard();
    }

    if (state.isFlipped) {
      if (e.code === 'Digit1') rateCard(1);
      if (e.code === 'Digit2') rateCard(2);
      if (e.code === 'Digit3') rateCard(3);
      if (e.code === 'Digit4') rateCard(4);
    }
  });

  // Init — load cards from API
  setView('loading');
  applyStudyLanguage();
  loadCards();
})();
