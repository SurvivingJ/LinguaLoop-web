document.addEventListener('DOMContentLoaded', function () {
  const languageCards = document.querySelectorAll('.language-card');
  const continueBtn = document.getElementById('continue-btn');
  const browseTestsLink = document.getElementById('browse-tests-link');
  let selectedLanguage = null;

  // First run (straight from login / welcome, nothing chosen yet): there is
  // nothing to go back to, so the header's Back pill is hidden.
  (function hideBackOnFirstRun() {
    const back = document.getElementById('ldBack');
    if (!back) return;
    let fromAuth = !document.referrer;
    try {
      const ref = new URL(document.referrer);
      fromAuth =
        fromAuth || (ref.origin === location.origin && /^\/(login|welcome)\/?$/.test(ref.pathname));
    } catch {
      /* no referrer */
    }
    if (fromAuth && !localStorage.getItem('selectedLanguageId')) back.hidden = true;
  })();

  // Redesign strings (static/i18n/_redesign/auth.json) are not in the locale
  // files yet; until they are, keep the English text already in the markup
  // (LinguaI18n.t returns the key itself for a missing key).
  function applyRedesignStrings() {
    const i18n = window.LinguaI18n;
    document.querySelectorAll('[data-ld-i18n]').forEach(function (el) {
      if (!el.dataset.ldFallback) el.dataset.ldFallback = el.textContent.trim();
      const key = el.getAttribute('data-ld-i18n');
      const text = i18n && typeof i18n.t === 'function' ? i18n.t(key) : key;
      el.textContent = text && text !== key ? text : el.dataset.ldFallback;
    });
  }
  applyRedesignStrings();
  document.addEventListener('languageChanged', applyRedesignStrings);
  if (window.LinguaI18n && typeof window.LinguaI18n.init === 'function') {
    // init() returns the (shared) load promise.
    Promise.resolve(window.LinguaI18n.init()).then(applyRedesignStrings, function () {});
  }

  // Fetch native names from metadata
  LinguaMetadata.load().then(function (meta) {
    if (!meta || !meta.languages) return;
    languageCards.forEach(function (card) {
      const langId = parseInt(card.dataset.id);
      const lang = meta.languages.find(function (l) {
        return l.id === langId;
      });
      if (lang && lang.native_name) {
        const nativeEl = card.querySelector('.language-native');
        if (nativeEl) nativeEl.textContent = lang.native_name;
      }
    });
  });

  // Handle language card selection
  languageCards.forEach((card) => {
    card.addEventListener('click', function () {
      // Remove selection from all cards
      languageCards.forEach((c) => {
        c.classList.remove('selected');
        c.setAttribute('aria-pressed', 'false');
        c.querySelector('.check-icon').style.display = 'none';
      });

      // Add selection to clicked card
      this.classList.add('selected');
      this.setAttribute('aria-pressed', 'true');
      this.querySelector('.check-icon').style.display = 'block';

      // Store selected language ID
      selectedLanguage = {
        id: parseInt(this.dataset.id),
      };

      renderGate();

      // Enable continue button and the secondary browse-tests link
      continueBtn.disabled = false;
      if (browseTestsLink) {
        browseTestsLink.style.pointerEvents = 'auto';
        browseTestsLink.style.opacity = '1';
        browseTestsLink.removeAttribute('aria-disabled');
      }
    });
  });

  // ---- Onboarding gate (vocab-placement tech §8, TASK-1085) ----
  // Only for a learner who arrives from the welcome page (onboarding.js sets
  // the per-tab mark). "Have you studied {language} before?": "Yes" makes the
  // placement the main action and Start Daily Session the way to skip it; the
  // other two answers leave the page as it is. Nothing is stored or sent.
  const gate = document.getElementById('langGate');
  const gateTitle = document.getElementById('langGateTitle');
  const gateHint = document.getElementById('langGateHint');
  const placementBtn = document.getElementById('placement-btn');
  const gateOptions = gate ? gate.querySelectorAll('[data-studied]') : [];
  const LANG_CODES = { 1: 'zh', 2: 'en', 3: 'ja' };
  let studied = null;
  let onboarding = false;
  try {
    onboarding = sessionStorage.getItem('ld_onboarding') === '1';
  } catch {
    onboarding = false;
  }

  function gateText(key, params, fallback) {
    const i18n = window.LinguaI18n;
    const text = i18n && typeof i18n.t === 'function' ? i18n.t(key, params) : key;
    return text && text !== key ? text : fallback;
  }

  function renderGate() {
    if (!gate || !placementBtn || !onboarding || !selectedLanguage) return;
    const code = LANG_CODES[selectedLanguage.id];
    if (!code) return;
    const language = gateText('lang_select.name_' + code, null, code);
    gateTitle.textContent = gateText(
      'onboarding.studied_before',
      { language: language },
      'Have you studied ' + language + ' before?'
    );
    gate.hidden = false;
    gateOptions.forEach(function (btn) {
      btn.setAttribute('aria-checked', String(btn.dataset.studied === studied));
    });
    const offer = studied === 'yes';
    const time = gateText(
      code === 'en' ? 'placement.intro_time_en' : 'placement.intro_time_cjk',
      null,
      code === 'en' ? 'About 5 minutes' : 'About 7 minutes'
    );
    gateHint.textContent = gateText(
      'onboarding.placement_hint',
      { time: time },
      time + '. A short test finds your level, so you start with the right words. You can skip it.'
    );
    gateHint.hidden = !offer;
    placementBtn.hidden = !offer;
    placementBtn.href =
      placementBtn.dataset.placementUrl + '?lang=' + encodeURIComponent(selectedLanguage.id);
    continueBtn.classList.toggle('ld-btn--ghost', offer);
    if (browseTestsLink) browseTestsLink.hidden = offer;
  }

  gateOptions.forEach(function (btn) {
    btn.addEventListener('click', function () {
      studied = btn.dataset.studied;
      renderGate();
    });
  });
  document.addEventListener('languageChanged', renderGate);

  function endOnboarding() {
    try {
      sessionStorage.removeItem('ld_onboarding');
    } catch {
      /* non-fatal */
    }
  }

  if (placementBtn) {
    placementBtn.addEventListener('click', function () {
      persistSelectedLanguage();
      endOnboarding();
    });
  }

  // Persist the chosen language (1=Chinese, 2=English, 3=Japanese) before
  // navigating, so both the daily session and the tests page see it.
  function persistSelectedLanguage() {
    if (selectedLanguage) {
      localStorage.setItem('selectedLanguageId', selectedLanguage.id.toString());
    }
  }

  // Primary CTA: start the daily study session.
  continueBtn.addEventListener('click', function () {
    if (selectedLanguage) {
      persistSelectedLanguage();
      endOnboarding();
      window.location.href = continueBtn.dataset.sessionUrl;
    }
  });

  // Secondary CTA: browse tests. The href already points to the tests page;
  // this handler just persists the selection first (and no-ops until a
  // language is chosen, matching the disabled visual state).
  if (browseTestsLink) {
    browseTestsLink.addEventListener('click', function (e) {
      if (!selectedLanguage) {
        e.preventDefault();
        return;
      }
      persistSelectedLanguage();
      endOnboarding();
    });
  }

  // Check if language was previously selected
  const savedLanguageId = localStorage.getItem('selectedLanguageId');
  if (savedLanguageId) {
    const savedCard = document.querySelector(`.language-card[data-id="${savedLanguageId}"]`);
    if (savedCard) {
      savedCard.click();
    }
  }
});
