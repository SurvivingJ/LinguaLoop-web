// Standalone test page (/test/<slug>?type=reading|listening): mounts the
// reading/listening player the daily session uses, with this page's options.
import { mount } from '../session/players/reading_listening.js';
import { T, applyI18n, escapeHtml } from '../session/dom.js';

const params = new URLSearchParams(window.location.search);
const slug = params.get('slug') || window.location.pathname.split('/').pop();
const type = params.get('type') || 'reading';
const daily = params.get('daily') === 'true';

// The preview page leaves its copy of /api/tests/test/<slug> in sessionStorage.
// Use it once if it is fresh; otherwise (direct link, reload) the player fetches.
function takeHandedOffTest() {
  const key = 'ld_test_payload:' + slug;
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    sessionStorage.removeItem(key);
    const saved = JSON.parse(raw);
    if (!saved || Date.now() - saved.at > 10 * 60 * 1000) return null;
    const body = saved.body;
    return body && body.test_data && body.questions_data ? body : null;
  } catch {
    return null;
  }
}

function markDailyLoadComplete(testId) {
  const languageId = localStorage.getItem('selectedLanguageId');
  if (!languageId || !testId) return;
  window
    .authFetch('/api/tests/daily-load/complete', {
      method: 'POST',
      body: JSON.stringify({ test_id: testId, language_id: parseInt(languageId) }),
    })
    .catch((error) => console.error('Error marking daily load complete:', error));
}

function finishButton(btn, _result, info) {
  // The finish action is the primary (brand) button, not Submit's green.
  btn.classList.remove('ld-btn--ok', 'btn-success');
  if (daily) {
    markDailyLoadComplete(info.testId);
    btn.innerHTML =
      '<i class="fas fa-arrow-right me-2" aria-hidden="true"></i>' +
      escapeHtml(T('test.continue_daily_load', null, 'Continue Daily Load'));
  } else {
    btn.innerHTML =
      '<i class="fas fa-arrow-left me-2" aria-hidden="true"></i>' +
      escapeHtml(T('test.back_to_test_list', null, 'Back to Test List'));
  }
  btn.onclick = () => {
    window.location.href = '/tests';
  };
}

// Markup only this page has: the hint under the score, and a way out of the
// error state.
function addPageMarkup(stage) {
  const score = stage.querySelector('#successScoreText');
  score.className = 'mb-1';
  score.insertAdjacentHTML(
    'afterend',
    '<p class="mb-0 ld-small" data-i18n="test.success_hint">Use the "Back to Test List" button below to continue practicing.</p>'
  );
  stage
    .querySelector('#errorState')
    .insertAdjacentHTML(
      'beforeend',
      '<div class="ld-row"><button class="ld-btn ld-btn--sm" type="button" data-test-retry><i class="fas fa-redo me-2" aria-hidden="true"></i><span data-i18n="test.retry">Retry</span></button>' +
        '<a href="/tests" class="ld-btn ld-btn--sm ld-btn--ghost"><i class="fas fa-arrow-left me-2" aria-hidden="true"></i><span data-i18n="test.back_to_tests">Back to Tests</span></a></div>'
    );
  stage.querySelector('[data-test-retry]').addEventListener('click', () => location.reload());
}

function start() {
  // Dictation has its own page; the generic one used to carry an older copy.
  if (type === 'dictation') {
    window.location.replace(
      `/test/${encodeURIComponent(slug)}/dictation${daily ? '?daily=true' : ''}`
    );
    return;
  }
  if (window.LinguaTestIntro) window.LinguaTestIntro.init({ testType: type });

  const stage = document.getElementById('testStage');
  const ready = window.LinguaMetadata.load();
  // The task header (templates/base.html): the player fills title, subtitle,
  // seal and the clock through the same frame the session runner passes.
  const shell = window.LinguaShell;
  const frame = shell
    ? {
        stage,
        setHeader: (opts) => shell.setTaskHeader(opts || {}),
        onBack: (fn) => shell.onBack(fn),
      }
    : null;
  const player = mount(stage, {
    item: { slug, test_type: type },
    languageId: parseInt(localStorage.getItem('selectedLanguageId')) || 0,
    payload: takeHandedOffTest(),
    ready,
    sentences: false,
    audioPreload: 'metadata',
    popoverBackdrop: true,
    resultActions: {},
    finishButton,
    frame,
    pageHeader: true,
    onComplete() {},
  });
  addPageMarkup(stage);
  ready.then(() => applyI18n(stage));
  document.addEventListener('languageChanged', () => player.rerender());
}

start();
