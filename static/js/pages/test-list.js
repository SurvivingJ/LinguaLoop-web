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

  /** Translation with an English fallback (new keys may not be in every bundle yet). */
  function tr(key, params, fallback) {
    const v = window.LinguaI18n && LinguaI18n.t ? LinguaI18n.t(key, params) : key;
    if (v && v !== key) return v;
    return String(fallback || key).replace(/\{(\w+)\}/g, (m, k) =>
      params && k in params ? params[k] : m
    );
  }

  // Static text that may not have a key in the bundle yet: [data-tl-t].
  function localizePage() {
    document.querySelectorAll('[data-tl-t]').forEach((el) => {
      if (!el.dataset.tlEn) el.dataset.tlEn = el.textContent;
      el.textContent = tr(el.getAttribute('data-tl-t'), null, el.dataset.tlEn);
    });
  }

  /** The study language's code ('zh', 'ja', ...) for a lang attribute. */
  function langCodeById(id) {
    const cache = window.LinguaMetadata && LinguaMetadata._cache;
    const lang = cache && (cache.languages || []).find((l) => l.id === Number(id));
    return (lang && lang.language_code) || '';
  }

  function langAttr(id) {
    const code = langCodeById(id);
    return code ? ` lang="${escapeHtml(code)}"` : '';
  }

  function typeLabel(testType) {
    return tr('test_list.' + testType, null, capitalizeFirst(testType));
  }

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
    const title = test.title || test.topic || 'Untitled Test';
    const glyph = Array.from(title)[0] || '·';
    const tags = [
      test.is_custom
        ? `<span class="ld-tag ld-tag--info">${escapeHtml(tr('test_list.custom', null, 'Custom'))}</span>`
        : '',
      test.is_featured
        ? `<span class="ld-tag ld-tag--brand">${escapeHtml(tr('test_list.featured', null, 'Featured'))}</span>`
        : '',
    ].join('');
    const firstLine = [test.topic, getDifficultyText(eloRating)].filter(Boolean).map(escapeHtml);
    const secondLine = [
      escapeHtml(LinguaMetadata.getNativeNameById(test.language_id) || 'N/A'),
      `ELO: ${escapeHtml(eloRating)}`,
      escapeHtml(LinguaI18n.t('test_list.attempts', { count: test.total_attempts || 0 })),
    ];

    return `
            <button type="button" class="test-card ld-trow" data-slug="${escapeHtml(test.slug || '')}">
                <span class="ld-trow__glyph"${langAttr(test.language_id)} aria-hidden="true">${escapeHtml(glyph)}</span>
                <span class="ld-trow__mid">
                    <span class="tl-row-title"${langAttr(test.language_id)}>${escapeHtml(title)}</span>
                    <small>${firstLine.join(' · ')}</small>
                    <small class="ld-num">${secondLine.join(' · ')}</small>
                    ${tags ? `<span class="ld-wrap">${tags}</span>` : ''}
                </span>
                <span class="ld-trow__end" aria-hidden="true">›</span>
            </button>
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

      // Show error message (the app's toast; a dialog where it is missing)
      if (typeof window.showToast === 'function') {
        window.showToast(LinguaI18n.t('test_list.random_failed'), 'error');
      } else {
        alert(LinguaI18n.t('test_list.random_failed'));
      }
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

    // Remove existing skeleton cards (and an earlier empty/error card)
    const skeletonCards = suggestedGrid.querySelectorAll('.skeleton-card, .tl-rec-note');
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
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'tl-pick suggested-card recommended-card';
    card.onclick = () => goToTestPreviewRecommended(test.slug, test.test_type);

    const testTypeIcon = getTestTypeIcon(test.test_type);
    const testTypeLabel = typeLabel(test.test_type || 'listening');
    const tierBadge =
      test.tier !== 'free-tier'
        ? `<span class="ld-tag ld-tag--warn tier-badge premium">${escapeHtml(tr('test_list.premium', null, 'Premium'))}</span>`
        : '';

    card.innerHTML = `
            <span class="ld-wrap recommended-header">
                <span class="ld-tag test-type-badge ${escapeHtml(test.test_type || '')}">${testTypeIcon} ${escapeHtml(testTypeLabel)}</span>
                ${tierBadge}
            </span>
            <span class="tl-pick__title recommended-title"${langAttr(localStorage.getItem('selectedLanguageId'))}>${escapeHtml(test.title)}</span>
            <span class="tl-pick__meta recommended-meta">
                <span>${escapeHtml(getDifficultyText(test.elo_rating))}</span>
                <b class="ld-num elo-info">ELO ${escapeHtml(test.elo_rating)}</b>
            </span>
            <span class="visually-hidden">${escapeHtml(LinguaI18n.t('test_list.start_test'))}</span>
        `;

    return card;
  }

  function getTestTypeIcon(testType) {
    const icons = {
      listening: '<i class="fa-solid fa-headphones" aria-hidden="true"></i>',
      reading: '<i class="fa-solid fa-book-open" aria-hidden="true"></i>',
      dictation: '<i class="fa-solid fa-keyboard" aria-hidden="true"></i>',
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

  // Empty / error: the first placeholder becomes a note card, the others go.
  function recommendedNote(cls, html) {
    const skeletonCards = document.querySelectorAll('.skeleton-card');
    let note = null;
    skeletonCards.forEach((card, index) => {
      if (index === 0) {
        card.classList.remove('skeleton-card', 'tl-skel');
        card.classList.add('tl-rec-note');
        card.removeAttribute('aria-hidden');
        card.innerHTML = `<div class="${cls}">${html}</div>`;
        note = card;
      } else {
        card.remove();
      }
    });
    return note;
  }

  function showRecommendedEmpty() {
    recommendedNote(
      'recommended-empty',
      `<p>${escapeHtml(LinguaI18n.t('test_list.recommended_empty'))}</p>`
    );
  }

  function showRecommendedError() {
    const note = recommendedNote(
      'recommended-error',
      `<p>${escapeHtml(LinguaI18n.t('test_list.recommended_error'))}</p>
                        <button type="button" class="ld-btn ld-btn--sm ld-btn--ghost">${escapeHtml(LinguaI18n.t('test_list.retry'))}</button>`
    );
    const retry = note && note.querySelector('button');
    if (retry) retry.addEventListener('click', () => loadRecommendedTests());
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
    localizePage();

    // Update progress
    updateDailyProgress(dailyLoad.progress);

    const allComplete = dailyLoad.progress.completed >= dailyLoad.progress.total;

    dailyLoad.tests.forEach(function (test, index) {
      const card = createDailyLoadCard(test, index);
      grid.appendChild(card);
    });

    // Show congrats message if all complete (above the cards)
    const old = section.querySelector('.daily-all-complete');
    if (old) old.remove();
    if (allComplete) {
      const completeMsg = document.createElement('p');
      completeMsg.className = 'ld-note ld-note--ok mb-0 daily-all-complete';
      completeMsg.textContent =
        '🎉 ' + tr('test_list.daily_done', null, 'Great job! You’ve completed today’s test load!');
      section.insertBefore(completeMsg, grid);
    }
  }

  function createDailyLoadCard(test, index) {
    const card = document.createElement('div');
    const isCompleted = test.is_completed;
    card.className = 'tl-pick daily-card' + (isCompleted ? ' is-done daily-card-completed' : '');

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

    const type = test.test_type || 'listening';
    const testTypeIcon = getTestTypeIcon(type);
    const elo = test.elo_rating || 1400;
    const isRetry = test.slot_type === 'retry';
    const slotLabel = isRetry
      ? tr('test_list.slot_retry', null, 'Retry')
      : tr('test_list.slot_new', null, 'New');

    let originalScoreHtml = '';
    if (isRetry && test.original_percentage != null) {
      const pct = Math.round(test.original_percentage);
      originalScoreHtml =
        '<span class="ld-small ld-muted daily-original-score">' +
        escapeHtml(tr('test_list.previously_scored', { pct }, 'Previously scored {pct}%')) +
        '</span>';
    }

    const buttonHtml = isCompleted
      ? '<button class="ld-btn ld-btn--sm daily-card-btn" type="button" disabled>' +
        '<i class="fas fa-check" aria-hidden="true"></i> ' +
        escapeHtml(tr('test_list.completed', null, 'Completed')) +
        '</button>'
      : '<button class="ld-btn ld-btn--sm daily-card-btn" type="button">' +
        escapeHtml(tr('test_list.start_test', null, 'Start Test')) +
        '</button>';

    card.innerHTML =
      '<span class="ld-wrap daily-card-header">' +
      '<span class="ld-tag ' +
      (isCompleted ? 'ld-tag--ok' : 'ld-tag--brand') +
      ' daily-card-number">' +
      (isCompleted ? '&#10003;' : index + 1) +
      '</span>' +
      '<span class="ld-tag test-type-badge ' +
      escapeHtml(type) +
      '">' +
      testTypeIcon +
      ' ' +
      escapeHtml(typeLabel(type)) +
      '</span>' +
      '<span class="ld-tag ' +
      (isRetry ? 'ld-tag--warn slot-badge-retry' : 'ld-tag--info slot-badge-new') +
      ' slot-badge">' +
      escapeHtml(slotLabel) +
      '</span>' +
      '</span>' +
      '<span class="tl-pick__title daily-card-title"' +
      langAttr(localStorage.getItem('selectedLanguageId')) +
      '>' +
      escapeHtml(test.title || 'Test') +
      '</span>' +
      '<span class="tl-pick__meta daily-card-meta">' +
      '<span>' +
      escapeHtml(getDifficultyText(elo)) +
      '</span>' +
      '<b class="ld-num elo-info">ELO ' +
      escapeHtml(elo) +
      '</b>' +
      '</span>' +
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

  // Controls (no inline handlers in the template).
  difficultyFilter?.addEventListener('change', applyFilters);
  testTypeFilter?.addEventListener('change', applyFilters);
  document.getElementById('filter-form')?.addEventListener('submit', (e) => e.preventDefault());
  document
    .querySelectorAll('[data-tl-reset]')
    .forEach((b) => b.addEventListener('click', resetFilters));
  document
    .querySelectorAll('[data-tl-retry]')
    .forEach((b) => b.addEventListener('click', () => loadTests()));
  document.getElementById('randomTestBtn')?.addEventListener('click', getRandomTest);
  testsGrid?.addEventListener('click', (e) => {
    const card = e.target.closest('.test-card');
    if (card && card.dataset.slug) goToTestPreview(card.dataset.slug);
  });
  renderReady.then(localizePage);

  // Initial load. The head script's early redirect covers the no-token case,
  // and authFetch handles refresh/device-restore/redirect on 401.
  loadTests();
  loadRecommendedTests();
  loadDailyLoad();
})();
