(function () {
  'use strict';

  // DOM Elements
  const testsGrid = document.getElementById('tests-grid');
  const loadingSpinner = document.getElementById('loading-state');
  const errorAlert = document.getElementById('error-state');
  const emptyState = document.getElementById('empty-state');
  const difficultyFilter = document.getElementById('difficulty');
  const testTypeFilter = document.getElementById('test-type');

  // Requests are sent straight away; only rendering waits for this (the
  // metadata is embedded in the page, so it resolves once i18n has loaded).
  const renderReady = LinguaMetadata.load();

  // ELO Range Mapping
  function getEloRange(band) {
    // The filter uses the same bands as the badges (static/js/utils.js ELO_RANGES).
    const b =
      window.LinguaUtils && window.LinguaUtils.ELO_RANGES && window.LinguaUtils.ELO_RANGES[band];
    return b ? { min: b.min, max: b.max + 1, label: b.label } : null;
  }

  // Utility Functions
  function showLoading() {
    debugLog('⏳ Showing loading spinner');
    loadingSpinner?.classList.remove('d-none');
    testsGrid.innerHTML = '';
    hideError();
    hideEmpty();
  }

  function hideLoading() {
    debugLog('✅ Hiding loading spinner');
    loadingSpinner?.classList.add('d-none');
  }

  function showError(message = 'Failed to load tests. Please try again.') {
    debugLog('❌ Showing error:', message);
    errorAlert?.classList.remove('d-none');
    const errorMsg = errorAlert?.querySelector('#error-message');
    if (errorMsg) errorMsg.textContent = message;
    hideLoading();
  }

  function hideError() {
    debugLog('✅ Hiding error');
    errorAlert?.classList.add('d-none');
  }

  function showEmpty() {
    debugLog('📭 Showing empty state');
    emptyState?.classList.remove('d-none');
    hideLoading();
    hideError();
  }

  function hideEmpty() {
    debugLog('✅ Hiding empty state');
    emptyState?.classList.add('d-none');
  }

  // Get the appropriate ELO rating based on selected test type
  function getTestEloRating(test) {
    const selectedType = testTypeFilter?.value || 'listening';

    switch (selectedType.toLowerCase()) {
      case 'listening':
        return test.listening_rating || 1400;
      case 'reading':
        return test.reading_rating || 1400;
      case 'dictation':
        return test.dictation_rating || 1400;
      default:
        return test.listening_rating || 1400;
    }
  }

  // getDifficultyInfo / getDifficultyText come from static/js/utils.js (age tiers, one scale).

  function createTestCard(test) {
    const eloRating = getTestEloRating(test);
    const difficultyClass = getDifficultyInfo(eloRating).class;

    return `
            <div class="test-card" onclick="goToTestPreview('${test.slug}')">
                <div class="test-card-header">
                    <div class="test-card-title">
                        <span>${escapeHtml(test.title || test.topic || 'Untitled Test')}</span>
                        <div class="test-badges">
                            <span class="badge-difficulty ${difficultyClass}">${escapeHtml(getDifficultyText(eloRating))}</span>
                            ${test.is_custom ? '<span class="badge-difficulty badge-custom">Custom</span>' : ''}
                            ${test.is_featured ? '<span class="badge-difficulty badge-featured">Featured</span>' : ''}
                        </div>
                    </div>
                </div>

                <div class="test-card-body">
                    <div class="test-meta">
                        <div class="test-meta-item">
                            <svg class="test-meta-icon" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M11 5a3 3 0 1 1-6 0 3 3 0 0 1 6 0ZM8 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm.256 7a4.474 4.474 0 0 1-.5-8.38.5.5 0 1 1 .994.12 3.5 3.5 0 1 0 3.6 3.5.5.5 0 0 1 .994-.084 4.5 4.5 0 0 1-4.088 4.748Z"/>
                            </svg>
                            <span>${escapeHtml(LinguaMetadata.getNativeNameById(test.language_id) || 'N/A')}</span>
                        </div>

                        <div class="test-meta-item">
                            <svg class="test-meta-icon" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M3 14.5A1.5 1.5 0 0 1 1.5 13V3A1.5 1.5 0 0 1 3 1.5h8a.5.5 0 0 1 0 1H3a.5.5 0 0 0-.5.5v10a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V8a.5.5 0 0 1 1 0v5a1.5 1.5 0 0 1-1.5 1.5H3z"/>
                            </svg>
                            <span>ELO: ${eloRating}</span>
                        </div>

                        <div class="test-meta-item">
                            <svg class="test-meta-icon" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M3.5 0a.5.5 0 0 1 .5.5V1h8V.5a.5.5 0 0 1 1 0V1h1a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h1V.5a.5.5 0 0 1 .5-.5z"/>
                            </svg>
                            <span>${LinguaI18n.t('test_list.attempts', { count: test.total_attempts || 0 })}</span>
                        </div>
                    </div>

                    ${test.topic ? `<p class="test-description">${escapeHtml(test.topic)}</p>` : ''}
                </div>
            </div>
        `;
  }

  function displayTests(tests) {
    debugLog('🎨 displayTests() called with', tests?.length || 0, 'tests');

    if (!tests || tests.length === 0) {
      console.warn('⚠️ No tests to display');
      showEmpty();
      return;
    }

    // Apply client-side ELO-based difficulty filtering
    let filteredTests = tests;
    const selectedDifficulty = difficultyFilter?.value;
    const selectedTestType = testTypeFilter?.value;

    debugLog('🔍 Filters - Difficulty:', selectedDifficulty, 'TestType:', selectedTestType);

    if (selectedDifficulty && selectedDifficulty !== '') {
      const eloRange = getEloRange(selectedDifficulty);
      debugLog('📊 ELO range for difficulty', selectedDifficulty, ':', eloRange);

      if (eloRange) {
        const beforeCount = filteredTests.length;
        filteredTests = filteredTests.filter((test) => {
          // Get the appropriate ELO rating based on test type
          let testElo = test.reading_rating || 1400;

          if (selectedTestType === 'listening') {
            testElo = test.listening_rating || 1400;
          } else if (selectedTestType === 'dictation') {
            testElo = test.dictation_rating || 1400;
          }

          const matches = testElo >= eloRange.min && testElo < eloRange.max;
          return matches;
        });
        debugLog('🔍 Filtered from', beforeCount, 'to', filteredTests.length, 'tests by ELO');
      }
    }

    // Show empty state if no tests match filters
    if (filteredTests.length === 0) {
      console.warn('⚠️ No tests match filters');
      showEmpty();
      return;
    }

    debugLog('✅ Rendering', filteredTests.length, 'test cards');
    testsGrid.innerHTML = filteredTests.map((test) => createTestCard(test)).join('');
    debugLog('✅ Test cards rendered to DOM');

    hideLoading();
    hideError();
    hideEmpty();
  }

  function goToTestPreview(slug) {
    if (slug) {
      // Get selected test type for preview
      const testType = testTypeFilter?.value || 'listening';

      // Redirect to preview page with test type query parameter
      window.location.href = `/test/${slug}/preview?type=${testType}`;
    }
  }

  async function loadTests() {
    debugLog('🚀 loadTests() called');
    showLoading();

    try {
      // Get selected language ID from localStorage
      const languageId = localStorage.getItem('selectedLanguageId');
      debugLog('🌐 selectedLanguageId:', languageId);

      if (!languageId) {
        console.warn('⚠️ No selected language found, redirecting to language selection');
        window.location.href = '/language-selection';
        return;
      }

      // Build query string with language_id
      const params = new URLSearchParams();
      params.append('language_id', languageId);

      const url = `/api/tests${params.toString() ? '?' + params.toString() : ''}`;

      debugLog('📡 Fetching tests from:', url);

      const [response] = await Promise.all([window.authFetch(url, { method: 'GET' }), renderReady]);

      debugLog('📨 Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ HTTP error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      debugLog('✅ Response data:', data);
      debugLog('📊 Tests count:', data.tests ? data.tests.length : 0);

      if (data.status !== 'error' && data.tests) {
        debugLog('✅ Calling displayTests with', data.tests.length, 'tests');
        if (data.tests.length > 0) {
          debugLog('📋 First test sample:', data.tests[0]);
        }
        displayTests(data.tests);
      } else {
        console.warn('⚠️ No tests in response or success=false');
        showEmpty();
      }
    } catch (error) {
      console.error('❌ Error loading tests:', error);
      console.error('❌ Error stack:', error.stack);
      await renderReady;
      showError(LinguaI18n.t('test_list.error_default'));
    }
  }

  /**
   * Get a random test based on user's ELO and skill type
   */
  async function getRandomTest() {
    const btn = document.getElementById('randomTestBtn');
    const icon = btn.querySelector('.random-icon');

    try {
      // Add loading state
      btn.disabled = true;
      icon.classList.add('loading');

      // Get current filter values for context
      const testType = document.getElementById('test-type').value || 'listening';

      // Get user's selected language ID from localStorage
      const languageId = localStorage.getItem('selectedLanguageId');
      if (!languageId) {
        window.location.href = '/language-selection';
        return;
      }

      debugLog('🎲 Fetching random test...', { testType, languageId });

      const response = await window.authFetch(
        `/api/tests/random?language_id=${languageId}&skill_type=${testType}`,
        { method: 'GET' }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch random test: ${response.status}`);
      }

      const result = await response.json();
      debugLog('✅ Random test received:', result);

      if (result.test && result.test.slug) {
        // Navigate to the test page
        window.location.href = `/test/${result.test.slug}?type=${testType}`;
      } else {
        throw new Error('Invalid response format');
      }
    } catch (error) {
      console.error('❌ Error getting random test:', error);

      // Remove loading state
      btn.disabled = false;
      icon.classList.remove('loading');

      // Show error message
      alert(LinguaI18n.t('test_list.random_failed'));
    }
  }

  // ✅ NEW: Apply filters function
  function applyFilters() {
    debugLog('🔧 Applying filters...');
    loadTests();
  }

  // Reset filters function
  function resetFilters() {
    debugLog('🔧 Resetting filters...');

    // Reset filter dropdowns to default values
    if (difficultyFilter) difficultyFilter.value = '';
    if (testTypeFilter) testTypeFilter.value = '';

    // Reload tests with no filters
    loadTests();
  }

  // ============================================
  // RECOMMENDED TESTS FUNCTIONALITY
  // ============================================

  async function loadRecommendedTests() {
    try {
      const languageId = localStorage.getItem('selectedLanguageId');
      if (!languageId) {
        debugLog('No language selected for recommended tests');
        return;
      }

      debugLog('Fetching recommended tests...', { languageId });

      const [response] = await Promise.all([
        window.authFetch(`/api/tests/recommended?language_id=${languageId}`, { method: 'GET' }),
        renderReady,
      ]);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      debugLog('Recommended tests received:', data);

      if (data.status !== 'error' && data.recommended_tests && data.recommended_tests.length > 0) {
        displayRecommendedTests(data.recommended_tests);
      } else {
        showRecommendedEmpty();
      }
    } catch (error) {
      console.error('Error loading recommended tests:', error);
      await renderReady;
      showRecommendedError();
    }
  }

  function displayRecommendedTests(tests) {
    const suggestedGrid = document.querySelector('.suggested-grid');

    // Remove existing skeleton cards
    const skeletonCards = suggestedGrid.querySelectorAll('.skeleton-card');
    skeletonCards.forEach((card) => card.remove());

    // Take up to 3 recommended tests
    const testsToShow = tests.slice(0, 3);

    // Create and insert recommended cards before the random test card
    const randomCard = suggestedGrid.querySelector('.random-card');

    testsToShow.forEach((test) => {
      const card = createRecommendedCard(test);
      suggestedGrid.insertBefore(card, randomCard);
    });
  }

  function createRecommendedCard(test) {
    const card = document.createElement('div');
    card.className = 'suggested-card recommended-card';
    card.onclick = () => goToTestPreviewRecommended(test.slug, test.test_type);

    const testTypeIcon = getTestTypeIcon(test.test_type);
    const testTypeLabel = capitalizeFirst(test.test_type);
    const difficultyClass = getDifficultyInfo(test.elo_rating).class;
    const tierBadge =
      test.tier !== 'free-tier' ? '<span class="tier-badge premium">Premium</span>' : '';

    card.innerHTML = `
            <div class="recommended-header">
                <span class="test-type-badge ${test.test_type}">${testTypeIcon} ${testTypeLabel}</span>
                ${tierBadge}
            </div>
            <div class="recommended-title">${escapeHtml(test.title)}</div>
            <div class="recommended-meta">
                <span class="badge-difficulty ${difficultyClass}">${escapeHtml(getDifficultyText(test.elo_rating))}</span>
                <span class="elo-info">ELO ${test.elo_rating}</span>
            </div>
            <button class="btn btn-primary btn-sm recommended-btn" type="button">
                ${LinguaI18n.t('test_list.start_test')}
            </button>
        `;

    return card;
  }

  function getTestTypeIcon(testType) {
    const icons = {
      listening: '<i class="fa-solid fa-headphones"></i>',
      reading: '<i class="fa-solid fa-book-open"></i>',
      dictation: '<i class="fa-solid fa-keyboard"></i>',
    };
    return icons[testType] || icons.listening;
  }

  function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function goToTestPreviewRecommended(testId, testType) {
    // Must go through /preview (test_preview.html), same as goToTestPreview
    // above — it's the only place that dispatches pitch_accent/pinyin/
    // dictation to their dedicated trainer routes. Without /preview this
    // hits the generic /test/<slug> route (test.html), which only knows
    // 'reading'/'listening'/'dictation' and silently renders a pitch_accent
    // test as a multiple-choice quiz.
    window.location.href = `/test/${testId}/preview?type=${testType}`;
  }

  function showRecommendedEmpty() {
    const skeletonCards = document.querySelectorAll('.skeleton-card');
    skeletonCards.forEach((card, index) => {
      if (index === 0) {
        card.classList.remove('skeleton-card');
        card.innerHTML = `
                    <div class="recommended-empty">
                        <p>${LinguaI18n.t('test_list.recommended_empty')}</p>
                    </div>
                `;
      } else {
        card.remove();
      }
    });
  }

  function showRecommendedError() {
    const skeletonCards = document.querySelectorAll('.skeleton-card');
    skeletonCards.forEach((card, index) => {
      if (index === 0) {
        card.classList.remove('skeleton-card');
        card.innerHTML = `
                    <div class="recommended-error">
                        <p>${LinguaI18n.t('test_list.recommended_error')}</p>
                        <button class="btn btn-sm btn-secondary" onclick="loadRecommendedTests()">${LinguaI18n.t('test_list.retry')}</button>
                    </div>
                `;
      } else {
        card.remove();
      }
    });
  }

  // ============================================
  // DAILY TEST LOAD FUNCTIONALITY
  // ============================================

  async function loadDailyLoad() {
    try {
      const languageId = localStorage.getItem('selectedLanguageId');
      if (!languageId) return;

      debugLog('Fetching daily load...', { languageId });

      const [response] = await Promise.all([
        window.authFetch(`/api/tests/daily-load?language_id=${languageId}`, { method: 'GET' }),
        renderReady,
      ]);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      debugLog('Daily load received:', data);

      if (
        data.status !== 'error' &&
        data.daily_load &&
        data.daily_load.tests &&
        data.daily_load.tests.length > 0
      ) {
        displayDailyLoad(data.daily_load);
      }
    } catch (error) {
      console.error('Error loading daily load:', error);
      // Silently fail - the section just won't show
    }
  }

  function displayDailyLoad(dailyLoad) {
    const section = document.getElementById('dailyLoadSection');
    const grid = document.getElementById('dailyLoadGrid');

    section.style.display = '';
    grid.innerHTML = '';

    // Update progress
    updateDailyProgress(dailyLoad.progress);

    const allComplete = dailyLoad.progress.completed >= dailyLoad.progress.total;

    dailyLoad.tests.forEach(function (test, index) {
      const card = createDailyLoadCard(test, index);
      grid.appendChild(card);
    });

    // Show congrats message if all complete
    if (allComplete) {
      const completeMsg = document.createElement('div');
      completeMsg.className = 'daily-all-complete';
      completeMsg.innerHTML =
        '<div class="daily-all-complete-icon">&#127881;</div><div>Great job! You\'ve completed today\'s test load!</div>';
      grid.appendChild(completeMsg);
    }
  }

  function createDailyLoadCard(test, index) {
    const card = document.createElement('div');
    const isCompleted = test.is_completed;
    card.className = 'daily-card' + (isCompleted ? ' daily-card-completed' : '');

    if (!isCompleted) {
      card.onclick = function () {
        const testType = test.test_type || 'listening';
        // Mirrors goToTestPreviewRecommended's dispatch above: pitch_accent
        // and pinyin have dedicated trainer routes/templates and don't
        // understand the generic /test/<slug>?type= query param — sending
        // them there silently rendered a multiple-choice quiz instead of
        // the actual trainer. dictation IS understood by test.html, so it
        // stays on the generic route (matches test_preview.html's dictation
        // branch only diverging for its own daily-load-less flow).
        if (testType === 'pitch_accent') {
          window.location.href = '/test/' + test.slug + '/pitch-accent?daily=true';
        } else if (testType === 'pinyin') {
          window.location.href = '/test/' + test.slug + '/pinyin?daily=true';
        } else {
          window.location.href = '/test/' + test.slug + '?type=' + testType + '&daily=true';
        }
      };
    }

    const testTypeIcon = getTestTypeIcon(test.test_type || 'listening');
    const testTypeLabel = capitalizeFirst(test.test_type || 'listening');
    const diffClass = getDifficultyInfo(test.elo_rating || 1400).class;

    const slotBadgeClass = test.slot_type === 'retry' ? 'slot-badge-retry' : 'slot-badge-new';
    const slotLabel = test.slot_type === 'retry' ? 'Retry' : 'New';
    const numberBadgeHtml =
      '<div class="daily-card-number">' + (isCompleted ? '&#10003;' : index + 1) + '</div>';

    let originalScoreHtml = '';
    if (test.slot_type === 'retry' && test.original_percentage != null) {
      originalScoreHtml =
        '<div class="daily-original-score">Previously scored ' +
        Math.round(test.original_percentage) +
        '%</div>';
    }

    const completedBadge = isCompleted
      ? '<span class="slot-badge slot-badge-completed">Completed</span>'
      : '';

    const buttonHtml = isCompleted
      ? '<button class="btn btn-success btn-sm daily-card-btn" disabled>Completed</button>'
      : '<button class="btn btn-primary btn-sm daily-card-btn" type="button">Start Test</button>';

    card.innerHTML =
      numberBadgeHtml +
      '<div class="daily-card-header">' +
      '<span class="test-type-badge ' +
      (test.test_type || 'listening') +
      '">' +
      testTypeIcon +
      ' ' +
      testTypeLabel +
      '</span>' +
      '<span class="slot-badge ' +
      slotBadgeClass +
      '">' +
      slotLabel +
      '</span>' +
      completedBadge +
      '</div>' +
      '<div class="daily-card-title">' +
      escapeHtml(test.title || 'Test') +
      '</div>' +
      '<div class="daily-card-meta">' +
      '<span class="badge-difficulty ' +
      diffClass +
      '">' +
      escapeHtml(getDifficultyText(test.elo_rating || 1400)) +
      '</span>' +
      '<span class="elo-info">ELO ' +
      (test.elo_rating || 1400) +
      '</span>' +
      '</div>' +
      originalScoreHtml +
      buttonHtml;

    return card;
  }

  function updateDailyProgress(progress) {
    const text = document.getElementById('dailyProgressText');
    const bar = document.getElementById('dailyProgressBar');

    if (text) text.textContent = progress.completed + '/' + progress.total;
    if (bar) {
      const pct = progress.total > 0 ? (progress.completed / progress.total) * 100 : 0;
      bar.style.width = pct + '%';
    }
  }

  // Make functions globally accessible for inline event handlers
  window.goToTestPreview = goToTestPreview;
  window.applyFilters = applyFilters;
  window.resetFilters = resetFilters;
  window.loadTests = loadTests;
  window.getRandomTest = getRandomTest;
  window.loadRecommendedTests = loadRecommendedTests;
  window.goToTestPreviewRecommended = goToTestPreviewRecommended;
  window.loadDailyLoad = loadDailyLoad;

  // Initial load. The head script's early redirect covers the no-token case,
  // and authFetch handles refresh/device-restore/redirect on 401.
  loadTests();
  loadRecommendedTests();
  loadDailyLoad();
})();
