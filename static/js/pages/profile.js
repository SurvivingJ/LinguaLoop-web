(function () {
  'use strict';

  let profileData = null;
  let selectedLang = null;
  let selectedSkill = null;
  const testHistory = {};
  const historyOffset = {};
  const HISTORY_PAGE_SIZE = 25;

  const SKILL_ICONS = {
    listening: '🎧',
    reading: '📖',
    dictation: '✍️',
    pinyin: '🀄',
    pitch_accent: '🎵',
    classifier_drill: '🧮',
  };
  function skillIcon(skillCode) {
    return SKILL_ICONS[skillCode] || '📖';
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadProfile();
    loadNativeLanguage();
    loadScriptVariant();

    // Wire up load more button
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', function () {
        loadTestHistory();
      });
    }
  });

  async function loadProfile() {
    try {
      const res = await window.authFetch('/api/users/elo');

      if (!res.ok) {
        throw new Error(`Failed to load profile: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();

      profileData = data.ratings;

      document.getElementById('loadingState').classList.add('d-none');

      if (!profileData || Object.keys(profileData).length === 0) {
        document.getElementById('emptyState').classList.remove('d-none');
      } else {
        document.getElementById('profileContent').classList.remove('d-none');

        renderLanguages();

        const firstLang = Object.keys(profileData)[0];
        window.selectLanguage(firstLang);
      }
    } catch (error) {
      console.error('=== LOAD PROFILE ERROR ===');
      console.error('Error type:', error.constructor.name);
      console.error('Error message:', error.message);
      console.error('Error stack:', error.stack);
      document.getElementById('loadingState').innerHTML =
        '<div class="alert alert-danger">Failed to load profile. Please refresh.</div>';
    }
  }

  function renderLanguages() {
    const container = document.getElementById('languageList');

    const langs = Object.entries(profileData);

    const html = langs
      .map(([code, data]) => {
        return `
            <div class="col-md-4">
                <div class="card language-card h-100 p-3" onclick="selectLanguage('${code}')">
                    <div class="d-flex align-items-center">
                        <span class="fs-1 me-3">${getFlag(code)}</span>
                        <div>
                            <h6 class="mb-1">${data.native_name || data.language_name}</h6>
                            <small class="text-muted">
                                ${LinguaI18n.t('profile.skills_count', { count: Object.keys(data.skills).length })}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `;
      })
      .join('');

    container.innerHTML = html;
  }

  function renderSkillTabs() {
    const container = document.getElementById('skillTabs');

    const skills = Object.entries(selectedLang.skills);

    const html = skills
      .map(([skillCode, skill], index) => {
        return `
            <li class="nav-item" role="presentation">
                <button
                    class="nav-link ${index === 0 ? 'active' : ''}"
                    id="${skillCode}-tab"
                    data-skill="${skillCode}"
                    data-test-type-id="${skill.test_type_id}"
                    type="button"
                    role="tab">
                    ${skillIcon(skillCode)} ${window.LinguaI18n ? window.LinguaI18n.t('test_list.' + skillCode) : skill.skill_name}
                </button>
            </li>
        `;
      })
      .join('');

    container.innerHTML = html;

    // Add click handlers
    const tabs = container.querySelectorAll('.nav-link');
    tabs.forEach((tab) => {
      tab.addEventListener('click', function () {
        // Remove active from all tabs
        container.querySelectorAll('.nav-link').forEach((t) => t.classList.remove('active'));
        this.classList.add('active');

        // Select skill
        const skillCode = this.dataset.skill;
        selectSkill(skillCode);
      });
    });
  }

  window.selectLanguage = function (langCode) {
    selectedLang = profileData[langCode];

    // Update active state. Scoped to the study-language list: the native-
    // language cards below share the class, and an unscoped, index-matched
    // query highlighted 中文 there depending on which section loaded first.
    const cards = document.querySelectorAll('#languageList .language-card');
    cards.forEach((el, i) => {
      el.classList.remove('active');
      if (Object.keys(profileData)[i] === langCode) {
        el.classList.add('active');
      }
    });

    const statsSection = document.getElementById('statsSection');
    statsSection.classList.remove('d-none');

    // Render skill tabs
    renderSkillTabs();

    // Auto-select first skill
    const skills = Object.keys(selectedLang.skills);
    const firstSkill = skills[0];
    selectSkill(firstSkill);
  };

  function selectSkill(skillCode) {
    selectedSkill = selectedLang.skills[skillCode];

    selectedSkill.code = skillCode; // Store skill code for later use

    renderStats();

    loadTestHistory();
  }

  function renderStats() {
    const container = document.getElementById('statsGrid');

    const skill = selectedSkill;
    const skillCode = skill.code;

    const html = `
            <div class="col-12">
                <div class="card stat-card p-4">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <div>
                            <small class="text-muted text-uppercase fw-semibold">${window.LinguaI18n ? window.LinguaI18n.t('test_list.' + skillCode) : skill.skill_name}</small>
                            <div class="h1 mb-0 mt-2">${skill.elo_rating}</div>
                            <small class="text-muted">${LinguaI18n.t('profile.elo_rating')}</small>
                        </div>
                        <span style="font-size: 3rem;">${skillIcon(skillCode)}</span>
                    </div>
                    <div class="row mt-3 pt-3 border-top">
                        <div class="col-md-6 text-center">
                            <h3 class="mb-0">${skill.tests_taken}</h3>
                            <small class="text-muted">${LinguaI18n.t('profile.tests_taken')}</small>
                        </div>
                        <div class="col-md-6 text-center">
                            <h3 class="mb-0">${formatDate(skill.last_test_date)}</h3>
                            <small class="text-muted">${LinguaI18n.t('profile.last_test')}</small>
                        </div>
                    </div>
                </div>
            </div>
        `;

    container.innerHTML = html;
  }

  async function loadTestHistory() {
    try {
      const cacheKey = `${selectedLang.language_id}_${selectedSkill.test_type_id}`;

      // Initialize cache for this language+skill if needed
      if (!testHistory[cacheKey]) {
        testHistory[cacheKey] = [];
        historyOffset[cacheKey] = 0;
      }

      const offset = historyOffset[cacheKey];

      const url = `/api/tests/history?language_id=${selectedLang.language_id}&test_type_id=${selectedSkill.test_type_id}&limit=${HISTORY_PAGE_SIZE}&offset=${offset}`;

      const res = await window.authFetch(url);

      if (!res.ok) {
        const errorText = await res.text();
        console.error('History request failed:', errorText);
        throw new Error(`Failed to load history: ${res.status}`);
      }

      const data = await res.json();

      const newTests = data.tests || [];

      // Append to cache
      testHistory[cacheKey] = [...testHistory[cacheKey], ...newTests];
      historyOffset[cacheKey] += newTests.length;

      const historySection = document.getElementById('historySection');
      historySection.classList.remove('d-none');

      const historyCount = document.getElementById('historyCount');
      historyCount.textContent = LinguaI18n.t('profile.tests_count', {
        count: testHistory[cacheKey].length,
      });

      renderHistory(cacheKey);

      const loadMoreContainer = document.getElementById('loadMoreContainer');
      if (newTests.length === HISTORY_PAGE_SIZE) {
        loadMoreContainer.classList.remove('d-none');
      } else {
        loadMoreContainer.classList.add('d-none');
      }
    } catch (error) {
      console.error('=== LOAD TEST HISTORY ERROR ===');
      console.error('Error type:', error.constructor.name);
      console.error('Error message:', error.message);
      console.error('Error stack:', error.stack);
    }
  }

  function renderHistory(cacheKey) {
    const container = document.getElementById('historyList');

    const history = testHistory[cacheKey] || [];

    if (history.length === 0) {
      container.innerHTML = `<div class="alert alert-info">${LinguaI18n.t('profile.no_skill_tests', { skill: selectedSkill.skill_name.toLowerCase() })}</div>`;
      return;
    }

    const html = history
      .map((test) => {
        const scoreClass =
          test.percentage >= 80
            ? 'success'
            : test.percentage >= 60
              ? 'primary'
              : test.percentage >= 40
                ? 'warning'
                : 'danger';
        const isPinyin =
          (selectedSkill && selectedSkill.code === 'pinyin') ||
          test.test_type_id ===
            (selectedLang &&
              selectedLang.skills &&
              selectedLang.skills.pinyin &&
              selectedLang.skills.pinyin.test_type_id);
        const isPitchAccent =
          (selectedSkill && selectedSkill.code === 'pitch_accent') ||
          test.test_type_id ===
            (selectedLang &&
              selectedLang.skills &&
              selectedLang.skills.pitch_accent &&
              selectedLang.skills.pitch_accent.test_type_id);
        const isClassifierDrill =
          (selectedSkill && selectedSkill.code === 'classifier_drill') ||
          test.test_type_id ===
            (selectedLang &&
              selectedLang.skills &&
              selectedLang.skills.classifier_drill &&
              selectedLang.skills.classifier_drill.test_type_id);
        const scoreLabel = isPinyin
          ? `${test.score}/${test.total_questions} chars`
          : isPitchAccent
            ? `${test.score}/${test.total_questions} words`
            : isClassifierDrill
              ? `${test.score}/${test.total_questions} classifiers`
              : `${test.score}/${test.total_questions}`;

        // Reduced-volatility repeat badge: elo_reduction_factor is set
        // only when a daily-load retry-slot repeat earned reduced ELO.
        const factor = test.elo_reduction_factor;
        const reviewBadge =
          factor != null
            ? `<span class="badge bg-info text-dark ms-1" title="${LinguaI18n.t('profile.review_badge_tooltip', { factor: factor.toFixed(2) })}">${LinguaI18n.t('profile.review_badge', { factor: factor.toFixed(2) })}</span>`
            : '';

        return `
                <div class="card mb-2">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">${escapeHtml(test.test_title || 'Unknown Test')}${reviewBadge}</h6>
                                <small class="text-muted">
                                    <i class="far fa-calendar me-1"></i>${formatDate(test.created_at)}
                                </small>
                            </div>
                            <div class="text-end ms-3">
                                <h5 class="mb-0 text-${scoreClass}">${scoreLabel}</h5>
                                <small class="text-muted">ELO: ${test.user_elo_after || 'N/A'}</small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
      })
      .join('');

    container.innerHTML = html;
  }

  // -----------------------------------------------------------------------
  // Native language (L1) settings — TASK-619.
  // Distinct from the per-language ELO cards above: this is the user's own
  // native language, persisted on users.native_language_id via the new
  // /api/users/native-language endpoints. NULL ("not set") is legitimate.
  // -----------------------------------------------------------------------
  const NATIVE_LANGUAGES = [
    { id: 1, flag: '🇨🇳', name: '中文' },
    { id: 2, flag: '🇺🇸', name: 'English' },
    { id: 3, flag: '🇯🇵', name: '日本語' },
  ];
  let currentNativeLanguageId = null;

  function nativeLanguageName(id) {
    const lang = NATIVE_LANGUAGES.find((l) => l.id === id);
    return lang ? `${lang.flag} ${lang.name}` : null;
  }

  function renderNativeCurrent() {
    const el = document.getElementById('nativeLanguageCurrent');
    if (!el) return;
    const name = nativeLanguageName(currentNativeLanguageId);
    if (name) {
      // A concrete language name isn't translatable copy — pin it so a
      // later applyToDOM() (fires on UI-language switch) can't clobber it.
      el.removeAttribute('data-i18n');
      el.textContent = name;
    } else {
      // Keep it i18n-managed so it re-localizes on language switch.
      el.setAttribute('data-i18n', 'profile.native_not_set');
      el.textContent = window.LinguaI18n ? LinguaI18n.t('profile.native_not_set') : 'Not set';
    }
    // Reflect the active card.
    document.querySelectorAll('#nativeLanguageCards .language-card').forEach((card) => {
      card.classList.toggle('active', parseInt(card.dataset.id, 10) === currentNativeLanguageId);
    });
  }

  function renderNativeCards() {
    const container = document.getElementById('nativeLanguageCards');
    if (!container) return;
    container.innerHTML = NATIVE_LANGUAGES.map(
      (lang) => `
            <div class="col-md-4">
                <div class="card language-card h-100 p-3" data-id="${lang.id}" role="button" tabindex="0">
                    <div class="d-flex align-items-center">
                        <span class="fs-2 me-3">${lang.flag}</span>
                        <h6 class="mb-0">${lang.name}</h6>
                    </div>
                </div>
            </div>
        `
    ).join('');
    container.querySelectorAll('.language-card').forEach((card) => {
      const handler = () => saveNativeLanguage(parseInt(card.dataset.id, 10));
      card.addEventListener('click', handler);
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handler();
        }
      });
    });
  }

  async function loadNativeLanguage() {
    renderNativeCards();
    try {
      const res = await window.authFetch('/api/users/native-language');
      if (res.ok) {
        const data = await res.json();
        currentNativeLanguageId = data.native_language_id || null;
      }
    } catch (err) {
      console.error('loadNativeLanguage failed:', err);
    }
    renderNativeCurrent();
  }

  async function saveNativeLanguage(languageId) {
    const status = document.getElementById('nativeLanguageStatus');
    const previous = currentNativeLanguageId;
    // Optimistic: reflect the choice immediately, roll back on failure.
    currentNativeLanguageId = languageId;
    renderNativeCurrent();
    if (status)
      status.textContent = window.LinguaI18n ? LinguaI18n.t('profile.native_saving') : 'Saving…';
    try {
      const res = await window.authFetch('/api/users/native-language', {
        method: 'PATCH',
        body: JSON.stringify({ language_id: languageId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (status)
        status.textContent = window.LinguaI18n ? LinguaI18n.t('profile.native_saved') : 'Saved';
    } catch (err) {
      console.error('saveNativeLanguage failed:', err);
      currentNativeLanguageId = previous;
      renderNativeCurrent();
      if (status)
        status.textContent = window.LinguaI18n
          ? LinguaI18n.t('profile.native_save_failed')
          : 'Could not save — try again';
    }
  }

  // ---------------------------------------------------------------
  // Chinese script variant (TASK-526)
  // ---------------------------------------------------------------
  // Reads and writes users.exercise_preferences.script_variant. The
  // practice session service does the field selection server-side over the
  // dual-stored content.hant mirror; the toggle only records the choice.

  async function loadScriptVariant() {
    const cb = document.getElementById('scriptVariantToggle');
    if (!cb) return;
    try {
      const res = await window.authFetch('/api/users/preferences');
      if (res.ok) {
        const body = await res.json();
        const prefs = (body && (body.data || body).exercise_preferences) || {};
        cb.checked = prefs.script_variant === 'traditional';
      }
    } catch (err) {
      console.error('loadScriptVariant failed:', err);
    }
    cb.addEventListener('change', () => saveScriptVariant(cb.checked));
  }

  async function saveScriptVariant(traditional) {
    const cb = document.getElementById('scriptVariantToggle');
    const status = document.getElementById('scriptVariantStatus');
    const variant = traditional ? 'traditional' : 'simplified';
    if (status)
      status.textContent = window.LinguaI18n ? LinguaI18n.t('profile.script_saving') : 'Saving…';
    try {
      const res = await window.authFetch('/api/users/preferences', {
        method: 'PATCH',
        body: JSON.stringify({ script_variant: variant }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (status)
        status.textContent = window.LinguaI18n ? LinguaI18n.t('profile.script_saved') : 'Saved';
    } catch (err) {
      console.error('saveScriptVariant failed:', err);
      // Roll the switch back so it never shows a preference the server
      // did not accept.
      if (cb) cb.checked = !traditional;
      if (status)
        status.textContent = window.LinguaI18n
          ? LinguaI18n.t('profile.script_save_failed')
          : 'Could not save — try again';
    }
  }

  function getFlag(langCode) {
    // Support both short codes (cn, jp, en) and full names (chinese, japanese, english)
    const flags = {
      zh: '🇨🇳',
      chinese: '🇨🇳',
      en: '🇺🇸',
      english: '🇺🇸',
      ja: '🇯🇵',
      japanese: '🇯🇵',
      ko: '🇰🇷',
      korean: '🇰🇷',
      fr: '🇫🇷',
      french: '🇫🇷',
    };
    const flag = flags[langCode?.toLowerCase()] || '🌐';
    return flag;
  }

  function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    const days = Math.floor((new Date() - date) / (1000 * 60 * 60 * 24));
    if (days === 0) return LinguaI18n.t('profile.today');
    if (days === 1) return LinguaI18n.t('profile.yesterday');
    if (days < 7) return LinguaI18n.t('profile.days_ago', { count: days });
    if (days < 30) return LinguaI18n.t('profile.weeks_ago', { count: Math.floor(days / 7) });
    return date.toLocaleDateString();
  }
})();
