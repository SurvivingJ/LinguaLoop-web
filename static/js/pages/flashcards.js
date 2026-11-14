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
  };

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
      } else {
        filterCards('reading');
      }
    } catch (e) {
      console.error('Flashcard load error:', e);
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

    if (state.filteredCards.length === 0) {
      els.flashcardArea.style.display = 'none';
      els.keyboardHint.style.display = 'none';
      els.sessionComplete.style.display = 'none';
      els.empty.style.display = 'block';
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
    els.sessionComplete.style.display = 'block';

    const i18n = window.LinguaI18n;
    els.sessionStats.innerHTML =
      '<div class="flashcard-stat"><div class="flashcard-stat-value" style="color:var(--danger)">' +
      (state.ratings[1] || 0) +
      '</div><div class="flashcard-stat-label">' +
      (i18n ? i18n.t('flashcards.again') : 'Again') +
      '</div></div>' +
      '<div class="flashcard-stat"><div class="flashcard-stat-value" style="color:var(--warning)">' +
      (state.ratings[2] || 0) +
      '</div><div class="flashcard-stat-label">' +
      (i18n ? i18n.t('flashcards.hard') : 'Hard') +
      '</div></div>' +
      '<div class="flashcard-stat"><div class="flashcard-stat-value" style="color:var(--success)">' +
      (state.ratings[3] || 0) +
      '</div><div class="flashcard-stat-label">' +
      (i18n ? i18n.t('flashcards.good') : 'Good') +
      '</div></div>' +
      '<div class="flashcard-stat"><div class="flashcard-stat-value" style="color:var(--primary)">' +
      (state.ratings[4] || 0) +
      '</div><div class="flashcard-stat-label">' +
      (i18n ? i18n.t('flashcards.easy') : 'Easy') +
      '</div></div>';
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
  loadCards();
})();
