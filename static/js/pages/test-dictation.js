// Standalone dictation page (/test/<slug>/dictation): mounts the dictation
// player the daily session uses, with this page's navigation.
import { mount } from '../session/players/dictation.js';
import { T, applyI18n, escapeHtml } from '../session/dom.js';

const parts = window.location.pathname.split('/');
const slug = parts[parts.indexOf('test') + 1];
// Set when a daily-load card opened the test (through /test/<slug>?type=dictation).
const daily = new URLSearchParams(window.location.search).get('daily') === 'true';

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

function resultActions(actions, _response, info) {
  if (daily) markDailyLoadComplete(info.testData && info.testData.id);
  actions.innerHTML = `
    <a href="/test/${escapeHtml(slug)}/preview" class="btn btn-outline-primary">
        <i class="bi bi-arrow-repeat me-1"></i>${escapeHtml(T('dictation.retry', null, 'Retry'))}
    </a>
    <a href="/tests" class="btn btn-primary">
        <i class="bi bi-list-ul me-1"></i>${escapeHtml(T('dictation.all_tests', null, 'All Tests'))}
    </a>`;
}

if (window.LinguaTestIntro) window.LinguaTestIntro.init({ testType: 'dictation' });

const stage = document.getElementById('testStage');
const ready = window.LinguaMetadata.load();
mount(stage, {
  item: { slug },
  languageId: parseInt(localStorage.getItem('selectedLanguageId')) || 0,
  ready,
  audioPreload: 'metadata',
  backHref: '/tests',
  resultActions,
  onComplete() {},
});
ready.then(() => applyI18n(stage));
