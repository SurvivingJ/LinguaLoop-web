(function () {
  'use strict';

  let profileData = null;
  let selectedLang = null;
  let selectedSkill = null;
  let selectedLangCode = null;
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

  // i18n helper with an English fallback: a key that is not in the locale
  // files yet (static/i18n/_redesign/settings.json) keeps the given text.
  function tf(key, fallback, params) {
    if (!window.LinguaI18n || typeof window.LinguaI18n.t !== 'function') return fallback;
    const v = window.LinguaI18n.t(key, params);
    return v && v !== key ? v : fallback;
  }

  // [data-me-t] / [data-me-t-aria]: new Me-hub strings. The English in the
  // markup is remembered and kept until the key exists.
  function localizeNewStrings() {
    document.querySelectorAll('[data-me-t]').forEach(function (el) {
      if (el.dataset.meEn === undefined) el.dataset.meEn = el.textContent;
      el.textContent = tf(el.dataset.meT, el.dataset.meEn);
    });
    document.querySelectorAll('[data-me-t-aria]').forEach(function (el) {
      if (el.dataset.meEnAria === undefined) {
        el.dataset.meEnAria = el.getAttribute('aria-label') || '';
      }
      el.setAttribute('aria-label', tf(el.dataset.meTAria, el.dataset.meEnAria));
    });
    syncThemeRows();
  }

  // Colour theme row: name of the current theme. Appearance row: says when a
  // named theme decides the scheme (the segmented control then shows no choice).
  function syncThemeRows() {
    const LT = window.LinguaTheme;
    const nameEl = document.getElementById('meThemeCurrent');
    const noteEl = document.getElementById('meModeNote');
    const modeRow = document.getElementById('meModeRow');
    if (!LT || typeof LT.current !== 'function') return;
    const id = LT.current();
    const theme = (LT.list() || []).find(function (th) {
      return th.id === id;
    });
    if (nameEl) {
      nameEl.textContent = theme ? tf(theme.nameKey, theme.name) : '';
    }
    const named = id !== 'default';
    if (modeRow) modeRow.classList.toggle('is-locked', named);
    if (noteEl) {
      if (noteEl.dataset.meEn === undefined) noteEl.dataset.meEn = noteEl.textContent;
      noteEl.textContent = named
        ? tf('theme.mode_locked', 'Set by the colour theme')
        : tf('me.appearance_sub', noteEl.dataset.meEn);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadProfile();
    loadNativeLanguage();
    loadScriptVariant();

    localizeNewStrings();
    if (window.LinguaI18n && typeof window.LinguaI18n.init === 'function') {
      window.LinguaI18n.init().then(localizeNewStrings, function () {});
    }
    document.addEventListener('languageChanged', function () {
      localizeNewStrings();
      if (profileData && selectedLang) {
        renderLanguages();
        markActiveLanguage();
        renderSkillTabs();
        if (selectedSkill) {
          renderStats();
          const cacheKey = selectedLang.language_id + '_' + selectedSkill.test_type_id;
          if (testHistory[cacheKey]) renderHistory(cacheKey);
        }
      }
    });
    document.addEventListener('lingua:themechange', syncThemeRows);

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
        '<div class="ld-note ld-note--bad">Failed to load profile. Please refresh.</div>';
    }
  }

  function renderLanguages() {
    const container = document.getElementById('languageList');

    const langs = Object.entries(profileData);

    const html = langs
      .map(([code, data]) => {
        return `
            <button type="button" class="ld-chip language-card" data-lang="${escapeHtml(code)}" aria-pressed="false">
                <span aria-hidden="true">${getFlag(code)}</span>
                <span>${escapeHtml(data.native_name || data.language_name)}</span>
                <span class="ld-muted">· ${LinguaI18n.t('profile.skills_count', { count: Object.keys(data.skills).length })}</span>
            </button>
        `;
      })
      .join('');

    container.innerHTML = html;
    container.querySelectorAll('.language-card').forEach((chip) => {
      chip.addEventListener('click', () => window.selectLanguage(chip.dataset.lang));
    });
  }

  // Highlight the selected study language. Scoped to the study-language list:
  // the native-language buttons share the class.
  function markActiveLanguage() {
    const code = selectedLang ? selectedLangCode : null;
    document.querySelectorAll('#languageList .language-card').forEach((el) => {
      const on = el.dataset.lang === code;
      el.classList.toggle('active', on);
      el.classList.toggle('is-on', on);
      el.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function renderSkillTabs() {
    const container = document.getElementById('skillTabs');

    const skills = Object.entries(selectedLang.skills);

    const current = selectedSkill && selectedSkill.code;
    const html = skills
      .map(([skillCode, skill], index) => {
        const on = current ? skillCode === current : index === 0;
        return `
                <button
                    class="ld-chip nav-link ${on ? 'active' : ''}"
                    id="${skillCode}-tab"
                    data-skill="${skillCode}"
                    data-test-type-id="${skill.test_type_id}"
                    type="button"
                    role="tab"
                    aria-controls="statsGrid"
                    aria-selected="${on ? 'true' : 'false'}"
                    tabindex="${on ? '0' : '-1'}">
                    <span aria-hidden="true">${skillIcon(skillCode)}</span> ${skillLabel(skillCode, skill)}
                </button>
        `;
      })
      .join('');

    container.innerHTML = html;

    const tabs = Array.from(container.querySelectorAll('[role="tab"]'));
    function activate(tab) {
      tabs.forEach((t) => {
        const on = t === tab;
        t.classList.toggle('active', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
      });
      selectSkill(tab.dataset.skill);
    }
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => activate(tab));
      // Arrow keys move between skills (WAI-ARIA tabs pattern).
      tab.addEventListener('keydown', (e) => {
        let next = null;
        if (e.key === 'ArrowRight') next = tabs[(i + 1) % tabs.length];
        else if (e.key === 'ArrowLeft') next = tabs[(i - 1 + tabs.length) % tabs.length];
        else if (e.key === 'Home') next = tabs[0];
        else if (e.key === 'End') next = tabs[tabs.length - 1];
        if (!next) return;
        e.preventDefault();
        next.focus();
        activate(next);
      });
    });
  }

  function skillLabel(skillCode, skill) {
    const fallback = (skill && skill.skill_name) || skillCode;
    if (!window.LinguaI18n) return escapeHtml(fallback);
    const v = window.LinguaI18n.t('test_list.' + skillCode);
    return escapeHtml(v && v !== 'test_list.' + skillCode ? v : fallback);
  }

  window.selectLanguage = function (langCode) {
    selectedLang = profileData[langCode];
    selectedLangCode = langCode;
    selectedSkill = null;

    markActiveLanguage();

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
            <div class="ld-stats stat-card" aria-label="${skillLabel(skillCode, skill)}">
                <div class="ld-stat">
                    <div class="ld-stat__n">${escapeHtml(skill.elo_rating)}</div>
                    <small>${LinguaI18n.t('profile.elo_rating')}</small>
                </div>
                <div class="ld-stat">
                    <div class="ld-stat__n">${escapeHtml(skill.tests_taken)}</div>
                    <small>${LinguaI18n.t('profile.tests_taken')}</small>
                </div>
                <div class="ld-stat">
                    <div class="ld-stat__n me-stat__date">${escapeHtml(formatDate(skill.last_test_date))}</div>
                    <small>${LinguaI18n.t('profile.last_test')}</small>
                </div>
            </div>
        `;

    container.innerHTML = html;
    container.setAttribute('aria-labelledby', skillCode + '-tab');
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
      container.innerHTML = `<div class="ld-note">${LinguaI18n.t('profile.no_skill_tests', { skill: escapeHtml(selectedSkill.skill_name.toLowerCase()) })}</div>`;
      return;
    }

    const histLang = selectedLangCode || '';
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
            ? ` · <span class="ld-tag ld-tag--warn" title="${LinguaI18n.t('profile.review_badge_tooltip', { factor: factor.toFixed(2) })}">${LinguaI18n.t('profile.review_badge', { factor: factor.toFixed(2) })}</span>`
            : '';

        return `
                <div class="ld-trow me-hist">
                    <span class="ld-trow__mid">
                        <b class="me-hist__title" lang="${escapeHtml(histLang)}">${escapeHtml(test.test_title || 'Unknown Test')}</b>
                        <small>${formatDate(test.created_at)}${reviewBadge}</small>
                    </span>
                    <span class="ld-trow__end">
                        <span class="me-hist__score text-${scoreClass}">${scoreLabel}</span>
                        <small class="d-block">ELO: ${escapeHtml(test.user_elo_after || 'N/A')}</small>
                    </span>
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
      const on = parseInt(card.dataset.id, 10) === currentNativeLanguageId;
      card.classList.toggle('active', on);
      card.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function renderNativeCards() {
    const container = document.getElementById('nativeLanguageCards');
    if (!container) return;
    container.innerHTML = NATIVE_LANGUAGES.map(
      (lang) => `
            <button type="button" class="ld-stat language-card me-native" data-id="${lang.id}" aria-pressed="false">
                <span class="me-native__flag" aria-hidden="true">${lang.flag}</span>
                <span class="me-native__name">${lang.name}</span>
            </button>
        `
    ).join('');
    // Native <button>s: Enter and Space activate them without a key handler.
    container.querySelectorAll('.language-card').forEach((card) => {
      card.addEventListener('click', () => saveNativeLanguage(parseInt(card.dataset.id, 10)));
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

  function escapeHtml(value) {
    const s = String(value == null ? '' : value);
    if (window.LinguaUtils && window.LinguaUtils.escapeHtml)
      return window.LinguaUtils.escapeHtml(s);
    return s.replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]
    );
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
