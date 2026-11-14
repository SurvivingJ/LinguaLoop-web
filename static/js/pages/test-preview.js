// Test preview page (/test/<slug>/preview): test details, mode picker, start.
(function () {
  'use strict';

  // Global state
  let testData = null;
  let skillRatings = null;
  let selectedTestType = 'listening';
  const PRESTUDY_TYPES = ['listening', 'reading'];
  let testSlug = null;

  /**
   * Parse URL parameters
   */
  function parseUrlParams() {
    const pathParts = window.location.pathname.split('/');
    // URL format: /test/{slug}/preview
    const slugIndex = pathParts.indexOf('test') + 1;
    testSlug = pathParts[slugIndex];

    const urlParams = new URLSearchParams(window.location.search);
    selectedTestType = urlParams.get('type') || 'listening';

    debugLog('Parsed URL - Slug:', testSlug, 'Type:', selectedTestType);
    return { testSlug, selectedTestType };
  }

  /**
   * Show error state
   */
  function showError(message) {
    document.getElementById('pageLoading').classList.add('d-none');
    document.getElementById('mainContent').classList.add('d-none');
    const errorDiv = document.getElementById('pageError');
    errorDiv.classList.remove('d-none');
    document.getElementById('errorMessage').textContent = message;
  }

  /**
   * Show main content
   */
  function showContent() {
    document.getElementById('pageLoading').classList.add('d-none');
    document.getElementById('pageError').classList.add('d-none');
    document.getElementById('mainContent').classList.remove('d-none');
  }

  /**
   * Fetch test data from API
   */
  async function fetchTestData(slug) {
    try {
      const response = await window.authFetch(`/api/tests/${slug}`, { method: 'GET' });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      debugLog('Test data received:', result);

      if (result.status === 'success' && result.test) {
        return result.test;
      } else {
        throw new Error(result.error || 'Invalid response format');
      }
    } catch (error) {
      console.error('Error fetching test:', error);
      throw error;
    }
  }

  /**
   * Fetch skill ratings from API
   */
  async function fetchSkillRatings(slug) {
    try {
      const response = await window.authFetch(`/api/tests/test/${slug}`, { method: 'GET' });

      if (!response.ok) {
        console.warn('Skill ratings endpoint returned:', response.status);
        // Return default ratings if endpoint fails
        return {
          listening: { elo_rating: 1400, volatility: 1.0, total_attempts: 0 },
          reading: { elo_rating: 1400, volatility: 1.0, total_attempts: 0 },
          dictation: { elo_rating: 1400, volatility: 1.0, total_attempts: 0 },
        };
      }

      const result = await response.json();
      debugLog('Skill ratings received:', result);
      // Hand the full payload to the test page so "Start" does not
      // download the same test again (read once, 10-minute expiry).
      try {
        sessionStorage.setItem(
          'ld_test_payload:' + slug,
          JSON.stringify({ at: Date.now(), body: result })
        );
      } catch (_) {
        /* storage full or blocked: the test page fetches */
      }
      return result.skill_ratings || {};
    } catch (error) {
      console.warn('Error fetching skill ratings:', error);
      // Return default ratings
      return {
        listening: { elo_rating: 1400, volatility: 1.0, total_attempts: 0 },
        reading: { elo_rating: 1400, volatility: 1.0, total_attempts: 0 },
        dictation: { elo_rating: 1400, volatility: 1.0, total_attempts: 0 },
      };
    }
  }

  /**
   * Populate page with test data
   */
  function populateTestInfo(test) {
    // Title and breadcrumb
    document.getElementById('testTitle').textContent = test.title || test.topic || 'Untitled Test';
    document.getElementById('breadcrumbTitle').textContent =
      test.title || test.topic || 'Test Preview';
    document.title = `${test.title || 'Test Preview'} | LinguaDojo`;

    // Custom badge
    if (test.is_custom) {
      document.getElementById('customBadge').classList.remove('d-none');
    }

    // Metadata
    document.getElementById('testLanguage').textContent =
      LinguaMetadata.getNativeName(test.language) || (test.language || 'unknown').toUpperCase();
    document.getElementById('testTopic').textContent = test.topic || 'General';

    // Show pinyin option for Chinese tests only
    if (test.language === 'zh' || test.language_id === 1) {
      document.getElementById('pinyinOptionWrapper').style.display = 'block';
    }

    // Show pitch accent option for Japanese tests only
    if (test.language === 'ja' || test.language_id === 3) {
      document.getElementById('pitchAccentOptionWrapper').style.display = 'block';
    }

    // Audio availability
    if (test.audio_generated || test.audio_url) {
      document.getElementById('audioAvailable').classList.remove('d-none');
    }

    // Attempts
    if (test.total_attempts && test.total_attempts > 0) {
      const attemptsEl = document.getElementById('attemptsMeta');
      attemptsEl.classList.remove('d-none');
      document.getElementById('testAttempts').textContent = LinguaI18n.t('test_preview.attempts', {
        count: test.total_attempts,
      });
    }
  }

  /**
   * Get difficulty level and color based on ELO rating
   */
  function getDifficultyInfo(rating) {
    // One scale for every page: the age tiers in static/js/utils.js.
    const info = window.LinguaUtils.getDifficultyInfo(rating);
    return { level: info.band.toLowerCase(), label: info.label, color: info.color };
  }

  /**
   * Update difficulty display when test type changes
   */
  function updateDifficultyDisplay(testType) {
    selectedTestType = testType;

    // --- Update Button UI Immediately ---
    const testTypeKey = 'test_preview.' + testType;
    const testTypeLabel = LinguaI18n.t(testTypeKey);
    const buttonTextEl = document.getElementById('buttonText');

    if (buttonTextEl) {
      buttonTextEl.textContent = LinguaI18n.t('test_preview.start_type_test', {
        type: testTypeLabel,
      });
    }

    // Prestudy is offered for the comprehension modes (listening, reading)
    const studyBlock = document.getElementById('studyFirstBlock');
    if (studyBlock) {
      studyBlock.hidden = !PRESTUDY_TYPES.includes(testType);
    }

    // Reset button state for all test types
    const startBtn = document.getElementById('startTestBtn');
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.title = '';
    }
    // --------------------------------------------------

    if (!skillRatings) {
      console.warn('Skill ratings not loaded yet');
      return;
    }

    // Get rating for selected test type (with case-insensitive fallback)
    const rating =
      skillRatings[testType] ||
      skillRatings[
        Object.keys(skillRatings).find((k) => k.toLowerCase() === testType.toLowerCase())
      ];

    if (!rating) {
      console.error('No rating found for test type:', testType);
      return;
    }

    const eloRating = rating.elo_rating || 1400;
    const difficultyInfo = getDifficultyInfo(eloRating);

    // Update badge
    const badge = document.getElementById('difficultyBadge');
    badge.className = `difficulty-badge ${difficultyInfo.level}`;

    // Update label
    document.getElementById('difficultyLabel').textContent = difficultyInfo.label;
    // The metadata row shows the same band (it used to show the stored
    // generation level, "Level 5", a different scale).
    document.getElementById('testDifficulty').textContent = difficultyInfo.label;

    // Update ELO text
    document.getElementById('eloRating').innerHTML = `ELO Rating: <strong>${eloRating}</strong>`;

    // Update icon color
    const icon = document.getElementById('difficultyIcon');
    icon.style.color = difficultyInfo.color;

    // Update stats if available
    if (rating.total_attempts > 0) {
      const statsRow = document.getElementById('statsRow');
      statsRow.style.display = 'block';
      document.getElementById('attemptsText').textContent = LinguaI18n.t(
        'test_preview.your_attempts',
        { count: rating.total_attempts }
      );
      // The API doesn't currently return a `volatility` field on skill
      // ratings, so guard against it being missing/non-numeric instead
      // of crashing the whole page init on `.toFixed()`.
      const volatilityEl = document.getElementById('volatilityText');
      const volatilitySepEl = document.getElementById('volatilitySep');
      if (typeof rating.volatility === 'number') {
        volatilityEl.textContent = LinguaI18n.t('test_preview.volatility', {
          value: rating.volatility.toFixed(2),
        });
        volatilitySepEl.style.display = '';
      } else {
        volatilityEl.textContent = '';
        volatilitySepEl.style.display = 'none';
      }
    } else {
      document.getElementById('statsRow').style.display = 'none';
    }
  }

  /**
   * Start the test - Navigate to test taking screen
   */
  async function startTest() {
    const btn = document.getElementById('startTestBtn');
    const buttonText = document.getElementById('buttonText');
    const originalText = buttonText.textContent;

    // Disable button and show loading
    btn.disabled = true;
    buttonText.innerHTML = '<span class="spinner-btn"></span> Loading...';

    try {
      // Store test data and type in sessionStorage for test screen
      sessionStorage.setItem('currentTest', JSON.stringify(testData));
      sessionStorage.setItem('currentTestType', selectedTestType);

      // Navigate to test taking screen
      if (selectedTestType === 'pinyin') {
        window.location.href = `/test/${testSlug}/pinyin`;
      } else if (selectedTestType === 'pitch_accent') {
        window.location.href = `/test/${testSlug}/pitch-accent`;
      } else if (selectedTestType === 'dictation') {
        window.location.href = `/test/${testSlug}/dictation`;
      } else {
        window.location.href = `/test/${testSlug}?type=${selectedTestType}`;
      }
    } catch (error) {
      console.error('Error starting test:', error);

      // Show error alert
      const alertDiv = document.createElement('div');
      alertDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
      alertDiv.innerHTML = `
                <strong>Error:</strong> ${escapeHtml(error.message || 'Failed to start test. Please try again.')}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

      // Insert alert at top of main content
      const mainContent = document.getElementById('mainContent');
      mainContent.insertBefore(alertDiv, mainContent.firstChild);

      // Re-enable button
      btn.disabled = false;
      buttonText.textContent = originalText;
    }
  }

  /**
   * Open the prestudy page for this test in the selected comprehension mode.
   */
  function startPrestudy() {
    if (!testSlug || !PRESTUDY_TYPES.includes(selectedTestType)) return;
    window.location.href = `/test/${encodeURIComponent(testSlug)}/prestudy?type=${encodeURIComponent(selectedTestType)}`;
  }

  /**
   * Initialize the page
   */
  async function initializePage() {
    try {
      // Language metadata + UI translations, awaited with the data below.
      const metadataReady = LinguaMetadata.load();

      // Parse URL
      const { testSlug: slug, selectedTestType: initialType } = parseUrlParams();

      if (!slug) {
        showError('No test specified in URL');
        return;
      }

      // Fetch test data and skill ratings in parallel
      const [test, ratings] = await Promise.all([
        fetchTestData(slug),
        fetchSkillRatings(slug),
        metadataReady,
      ]);

      if (!test) {
        showError('Failed to load test data');
        return;
      }

      // Store in global state
      testData = test;
      skillRatings = ratings;
      selectedTestType = initialType;

      // Populate page
      populateTestInfo(test);

      // Set initial test type selection
      const radioButton = document.getElementById(`${initialType}Option`);
      if (radioButton) {
        radioButton.checked = true;
      }

      // Update difficulty display
      updateDifficultyDisplay(selectedTestType);

      // Show content
      showContent();
    } catch (error) {
      console.error('Initialization error:', error);
      showError(error.message || 'Failed to load test preview');
    }
  }

  document.querySelectorAll('input[name="testType"]').forEach((radio) => {
    radio.addEventListener('change', () => updateDifficultyDisplay(radio.value));
  });
  document.getElementById('startTestBtn').addEventListener('click', startTest);
  document.getElementById('studyFirstBtn').addEventListener('click', startPrestudy);

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePage);
  } else {
    initializePage();
  }
})();
