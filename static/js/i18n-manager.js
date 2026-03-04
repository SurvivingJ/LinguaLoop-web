/**
 * LinguaDojo Internationalization Manager
 * Handles UI language switching, translation loading, and live DOM updates.
 * Mirrors the theme-manager.js IIFE + localStorage + dropdown pattern.
 */
(function() {
    'use strict';

    var STORAGE_KEY = 'linguadojo-ui-lang';
    var DEFAULT_LANG = 'en';
    var SUPPORTED_LANGS = {
        'en': { name: 'English', nativeName: 'English', flag: '\uD83C\uDDFA\uD83C\uDDF8' },
        'zh': { name: 'Chinese', nativeName: '\u4E2D\u6587', flag: '\uD83C\uDDE8\uD83C\uDDF3' },
        'ja': { name: 'Japanese', nativeName: '\u65E5\u672C\u8A9E', flag: '\uD83C\uDDEF\uD83C\uDDF5' },
        'es': { name: 'Spanish', nativeName: 'Espa\u00F1ol', flag: '\uD83C\uDDEA\uD83C\uDDF8' }
    };

    var currentLang = DEFAULT_LANG;
    var translations = {};
    var fallbackTranslations = {};
    var isLoaded = false;
    var loadPromise = null;

    // Known server error messages mapped to i18n keys
    var ERROR_MAP = {
        'Server error occurred': 'error.server',
        'Valid email is required': 'login.error.invalid_email',
        'Invalid or expired OTP': 'login.error.invalid_code',
        'Invalid category': 'error.invalid_category',
        'Description too short': 'error.description_short',
        'User ID not found': 'error.unauthorized',
        'Please log in': 'error.unauthorized',
        'Submission failed': 'report.error.failed'
    };

    /**
     * Detect language from localStorage or browser setting.
     */
    function detectLanguage() {
        var saved = localStorage.getItem(STORAGE_KEY);
        if (saved && SUPPORTED_LANGS[saved]) return saved;

        var browserLang = (navigator.language || '').substring(0, 2);
        if (SUPPORTED_LANGS[browserLang]) return browserLang;

        return DEFAULT_LANG;
    }

    /**
     * Fetch a translation JSON file.
     */
    function loadTranslationFile(lang) {
        return fetch('/static/i18n/' + lang + '.json', { cache: 'no-cache' })
            .then(function(res) {
                if (!res.ok) throw new Error('Failed to load ' + lang + ' translations');
                return res.json();
            });
    }

    /**
     * Initialize: load English fallback + current language.
     * Returns a Promise that resolves when translations are ready.
     */
    function init() {
        if (loadPromise) return loadPromise;

        currentLang = detectLanguage();

        loadPromise = loadTranslationFile('en')
            .then(function(en) {
                fallbackTranslations = en;
                if (currentLang !== 'en') {
                    return loadTranslationFile(currentLang).then(function(data) {
                        translations = data;
                    });
                } else {
                    translations = en;
                }
            })
            .then(function() {
                isLoaded = true;
                applyToDOM();
                updateSwitcherUI();
            })
            .catch(function(err) {
                console.error('[i18n] Init error:', err);
                // Ensure we at least have fallback
                if (Object.keys(fallbackTranslations).length > 0) {
                    translations = fallbackTranslations;
                    isLoaded = true;
                    applyToDOM();
                }
            });

        return loadPromise;
    }

    /**
     * Core translation function.
     * @param {string} key - Translation key (e.g. 'common.nav.profile')
     * @param {Object} [params] - Interpolation values. Use {name} placeholders.
     *   For pluralization: "1 skill|{count} skills" with params.count
     * @returns {string} Translated string, or the key itself if not found.
     */
    function t(key, params) {
        var text = translations[key] || fallbackTranslations[key] || key;

        // Simple pluralization via | separator
        if (params && typeof params.count === 'number' && text.indexOf('|') !== -1) {
            var parts = text.split('|');
            text = params.count === 1 ? parts[0] : parts[1];
        }

        // Interpolation: replace {variableName} with params
        if (params) {
            var paramKeys = Object.keys(params);
            for (var i = 0; i < paramKeys.length; i++) {
                var pKey = paramKeys[i];
                text = text.replace(new RegExp('\\{' + pKey + '\\}', 'g'), params[pKey]);
            }
        }

        return text;
    }

    /**
     * Translate known server error messages to the current locale.
     * Falls back to the original message if no mapping exists.
     */
    function tError(serverMessage) {
        if (!serverMessage) return '';
        var key = ERROR_MAP[serverMessage];
        return key ? t(key) : serverMessage;
    }

    /**
     * Scan the DOM for data-i18n attributes and apply translations.
     */
    function applyToDOM() {
        if (!isLoaded) return;

        // data-i18n → textContent
        var els = document.querySelectorAll('[data-i18n]');
        for (var i = 0; i < els.length; i++) {
            var el = els[i];
            var key = el.getAttribute('data-i18n');
            var paramsAttr = el.getAttribute('data-i18n-params');
            var params = paramsAttr ? JSON.parse(paramsAttr) : undefined;
            el.textContent = t(key, params);
        }

        // data-i18n-html → innerHTML (for strings with markup)
        var htmlEls = document.querySelectorAll('[data-i18n-html]');
        for (var j = 0; j < htmlEls.length; j++) {
            var hel = htmlEls[j];
            var hkey = hel.getAttribute('data-i18n-html');
            var hparams = hel.getAttribute('data-i18n-params');
            hel.innerHTML = t(hkey, hparams ? JSON.parse(hparams) : undefined);
        }

        // data-i18n-placeholder → placeholder attribute
        var phEls = document.querySelectorAll('[data-i18n-placeholder]');
        for (var k = 0; k < phEls.length; k++) {
            phEls[k].placeholder = t(phEls[k].getAttribute('data-i18n-placeholder'));
        }

        // data-i18n-aria → aria-label attribute
        var ariaEls = document.querySelectorAll('[data-i18n-aria]');
        for (var l = 0; l < ariaEls.length; l++) {
            ariaEls[l].setAttribute('aria-label', t(ariaEls[l].getAttribute('data-i18n-aria')));
        }

        // Update document lang attribute
        document.documentElement.lang = currentLang;
    }

    /**
     * Switch the UI language. No page reload needed.
     * Fires a 'languageChanged' CustomEvent for JS-rendered pages to re-render.
     */
    function setLanguage(lang) {
        if (!SUPPORTED_LANGS[lang]) lang = DEFAULT_LANG;
        if (lang === currentLang && isLoaded) return Promise.resolve();

        currentLang = lang;
        localStorage.setItem(STORAGE_KEY, lang);

        var promise;
        if (lang === 'en') {
            translations = fallbackTranslations;
            promise = Promise.resolve();
        } else {
            promise = loadTranslationFile(lang).then(function(data) {
                translations = data;
            });
        }

        return promise.then(function() {
            applyToDOM();
            updateSwitcherUI();
            document.dispatchEvent(new CustomEvent('languageChanged', {
                detail: { language: lang }
            }));
        });
    }

    /**
     * Build the language switcher dropdown items.
     * Mirrors theme-manager.js setupSwitcher() exactly.
     */
    function setupSwitcher() {
        var dropdown = document.getElementById('langSwitcherMenu');
        if (!dropdown) return;

        dropdown.innerHTML = '';

        Object.keys(SUPPORTED_LANGS).forEach(function(code) {
            var info = SUPPORTED_LANGS[code];
            var li = document.createElement('li');
            var btn = document.createElement('button');
            btn.className = 'dropdown-item d-flex align-items-center gap-2';
            btn.type = 'button';
            btn.dataset.lang = code;
            btn.innerHTML = info.flag + ' ' + info.nativeName;
            btn.addEventListener('click', function() {
                setLanguage(code);
            });
            li.appendChild(btn);
            dropdown.appendChild(li);
        });

        updateSwitcherUI();
    }

    /**
     * Update active state on the language switcher dropdown items.
     */
    function updateSwitcherUI() {
        var items = document.querySelectorAll('#langSwitcherMenu .dropdown-item');
        items.forEach(function(item) {
            if (item.dataset.lang === currentLang) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        var triggerBtn = document.querySelector('#langSwitcherBtn .lang-flag');
        if (triggerBtn && SUPPORTED_LANGS[currentLang]) {
            triggerBtn.textContent = SUPPORTED_LANGS[currentLang].flag;
        }
    }

    // Initialize on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function() {
        setupSwitcher();
        init();
    });

    // Public API
    window.LinguaI18n = {
        t: t,
        tError: tError,
        setLanguage: setLanguage,
        currentLanguage: function() { return currentLang; },
        isReady: function() { return isLoaded; },
        applyToDOM: applyToDOM,
        init: init,
        SUPPORTED_LANGS: SUPPORTED_LANGS
    };
})();
