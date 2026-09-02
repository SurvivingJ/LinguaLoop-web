/**
 * LinguaDojo Test Intro — first-time explainer popup + info button.
 *
 * Every test-taking page (test.html, test_dictation.html, test_pinyin.html,
 * test_pitch_accent.html, classifier_drill.html, counter_drill.html) calls
 * LinguaTestIntro.init({testType}) once it knows which test type it's
 * rendering. That:
 *   - injects a small floating "i" button (top-right) that reopens the
 *     explainer modal on demand, and
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

  function ensureStyles() {
    if (document.getElementById('testIntroStyles')) return;
    const style = document.createElement('style');
    style.id = 'testIntroStyles';
    style.textContent =
      '.test-intro-btn{position:fixed;top:76px;right:16px;z-index:1040;' +
      'width:36px;height:36px;border-radius:50%;' +
      'border:2px solid var(--border-strong,#cbd5e1);background:var(--bg-surface,#fff);' +
      'color:var(--primary,#4f46e5);display:flex;align-items:center;justify-content:center;' +
      'font-size:18px;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,0.15);' +
      'transition:transform .15s ease,background .15s ease;padding:0;}' +
      '.test-intro-btn:hover{transform:scale(1.08);background:var(--bg-surface-hover,#f1f5f9);}' +
      '@media (max-width:576px){.test-intro-btn{top:auto;bottom:16px;}}';
    document.head.appendChild(style);
  }

  function ensureModal() {
    if (modalEl) return;
    modalEl = document.createElement('div');
    modalEl.className = 'modal fade';
    modalEl.id = 'testIntroModal';
    modalEl.tabIndex = -1;
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.innerHTML =
      '<div class="modal-dialog modal-dialog-centered">' +
      '<div class="modal-content">' +
      '<div class="modal-header border-0">' +
      '<h5 class="modal-title"><i class="fas fa-circle-info text-primary me-2"></i>' +
      '<span id="testIntroTitle"></span></h5>' +
      '<button type="button" class="btn-close" data-bs-dismiss="modal"></button>' +
      '</div>' +
      '<div class="modal-body" id="testIntroBody"></div>' +
      '<div class="modal-footer border-0">' +
      '<button type="button" class="btn btn-primary" data-bs-dismiss="modal" id="testIntroCloseBtn"></button>' +
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
    btn.setAttribute('aria-label', t('test_intro.info_aria'));
    btn.innerHTML = '<i class="fas fa-info" aria-hidden="true"></i>';
    btn.addEventListener('click', function () {
      show(currentTestType, { auto: false });
    });
    document.body.appendChild(btn);
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
