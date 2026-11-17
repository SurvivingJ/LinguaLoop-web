/**
 * LinguaDojo Test Intro — first-time explainer popup + info button.
 *
 * Every test-taking page (test.html, test_dictation.html, test_pinyin.html,
 * test_pitch_accent.html, classifier_drill.html, counter_drill.html) calls
 * LinguaTestIntro.init({testType}) once it knows which test type it's
 * rendering. That:
 *   - injects a small "i" button that reopens the explainer modal on demand
 *     (in the task header on one-task pages, floating elsewhere), and
 *   - auto-opens the modal once, the first time this user reaches that
 *     test type, using GET/POST /api/test-intros/seen (see
 *     routes/test_intros.py) so the "seen" flag persists across devices —
 *     mirrors users.has_seen_welcome, just per test type instead of global.
 *
 * Content comes from i18n keys `test_intro.<test_type>.title` /
 * `test_intro.<test_type>.body` (see static/i18n/*.json) so this one module
 * covers every test type without per-page markup.
 */
(function () {
  'use strict';

  let seenSet = null;
  let seenFetchPromise = null;
  let currentTestType = null;
  let modalEl = null;
  let bsModal = null;

  function t(key, params) {
    return window.LinguaI18n && window.LinguaI18n.t ? window.LinguaI18n.t(key, params) : key;
  }

  // Styles live in static/css/redesign/tests.css (section 4), which base.html
  // loads on every page; kept as a no-op hook for existing callers.
  function ensureStyles() {}

  function ensureModal() {
    if (modalEl) return;
    modalEl = document.createElement('div');
    modalEl.className = 'modal fade';
    modalEl.id = 'testIntroModal';
    modalEl.tabIndex = -1;
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.setAttribute('aria-labelledby', 'testIntroHeading');
    modalEl.innerHTML =
      '<div class="modal-dialog modal-dialog-centered">' +
      '<div class="modal-content">' +
      '<div class="modal-header border-0">' +
      '<h2 class="modal-title ld-h2" id="testIntroHeading"><i class="fas fa-circle-info text-primary me-2" aria-hidden="true"></i>' +
      '<span id="testIntroTitle"></span></h2>' +
      '<button type="button" class="btn-close" data-bs-dismiss="modal"></button>' +
      '</div>' +
      '<div class="modal-body" id="testIntroBody"></div>' +
      '<div class="modal-footer border-0">' +
      '<button type="button" class="ld-btn ld-btn--block" data-bs-dismiss="modal" id="testIntroCloseBtn"></button>' +
      '</div>' +
      '</div>' +
      '</div>';
    document.body.appendChild(modalEl);

    modalEl.addEventListener('shown.bs.modal', function () {
      if (modalEl.dataset.pendingMark === '1') {
        markSeen(modalEl.dataset.testType);
        modalEl.dataset.pendingMark = '0';
      }
    });
  }

  function ensureButton() {
    let btn = document.querySelector('.test-intro-btn');
    if (btn) return btn;
    btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'test-intro-btn';
    // Before the bundle loads t() returns the key itself: start from English;
    // LinguaI18n.applyToDOM re-labels [data-i18n-aria] on load and on a switch.
    const label = t('test_intro.info_aria');
    btn.setAttribute('aria-label', label !== 'test_intro.info_aria' ? label : 'About this test');
    btn.setAttribute('data-i18n-aria', 'test_intro.info_aria');
    btn.innerHTML = '<i class="fas fa-info" aria-hidden="true"></i>';
    btn.addEventListener('click', function () {
      show(currentTestType, { auto: false });
    });
    // One-task pages (body.ld-task) have a task header: the button sits at its
    // right end, after the clock. Elsewhere it floats (tests.css section 4).
    const taskbar = document.getElementById('ldTaskbar');
    if (taskbar && document.body.classList.contains('ld-task')) taskbar.appendChild(btn);
    else document.body.appendChild(btn);
    return btn;
  }

  function fetchSeen() {
    if (seenFetchPromise) return seenFetchPromise;
    const fetcher = window.authFetch || window.fetch;
    seenFetchPromise = fetcher('/api/test-intros/seen', { method: 'GET' })
      .then(function (res) {
        return res.ok ? res.json() : { seen: [] };
      })
      .then(function (data) {
        seenSet = new Set(data.seen || []);
        return seenSet;
      })
      .catch(function () {
        seenSet = new Set();
        return seenSet;
      });
    return seenFetchPromise;
  }

  function markSeen(testType) {
    if (!testType) return;
    try {
      const fetcher = window.authFetch || window.fetch;
      fetcher('/api/test-intros/seen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test_type: testType }),
      }).catch(function () {
        /* best effort */
      });
      if (seenSet) seenSet.add(testType);
    } catch (e) {
      /* best effort — a failed write just means the popup may reappear once */
    }
  }

  /**
   * Show the explainer modal for a test type.
   * @param {string} testType
   * @param {Object} [opts]
   * @param {boolean} [opts.auto] - true when auto-shown for a first-time
   *   user; marks the intro seen once the modal actually finishes opening.
   *   Omit (or false) for a manual open via the info button — already-seen
   *   users don't need a re-write, though it's idempotent either way.
   */
  function show(testType, opts) {
    opts = opts || {};
    if (!testType) return;
    ensureStyles();
    ensureModal();

    document.getElementById('testIntroTitle').textContent = t('test_intro.' + testType + '.title');
    document.getElementById('testIntroBody').innerHTML = t('test_intro.' + testType + '.body');
    document.getElementById('testIntroCloseBtn').textContent = t('test_intro.got_it');

    if (!bsModal) bsModal = new bootstrap.Modal(modalEl);

    modalEl.dataset.testType = testType;
    modalEl.dataset.pendingMark = opts.auto ? '1' : '0';
    bsModal.show();
  }

  /**
   * Wire up a test-taking page. Call once the page knows its test type.
   * @param {Object} config
   * @param {string} config.testType - e.g. 'reading', 'pitch_accent', 'classifier_drill'
   */
  function init(config) {
    if (!config || !config.testType) return;
    currentTestType = config.testType;
    ensureStyles();
    ensureButton();

    fetchSeen().then(function (seen) {
      if (!seen.has(currentTestType)) {
        show(currentTestType, { auto: true });
      }
    });
  }

  window.LinguaTestIntro = { init: init, show: show };
})();
