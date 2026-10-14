// static/js/weekly-study.js
// "Studied this week: X / Y min" block for the Study Plan page
// (wiki/features/weekly-minutes.tech.md, TASK-895).
//
// Input is the `weekly_study` field of GET /api/study-plan:
//   { week_start_date, studied_seconds, studied_minutes, target_minutes|null,
//     by_kind: { test, practice, flashcard, dual_translation, drill: {seconds, minutes} } }
// buildModel() is pure (unit-tested); render() writes with textContent only.
(function (root) {
  'use strict';

  const KIND_ORDER = ['test', 'practice', 'flashcard', 'dual_translation', 'drill'];

  function num(v) {
    const n = Number(v);
    return isFinite(n) && n > 0 ? Math.round(n) : 0;
  }

  // Returns null when there is nothing to show (weekly_study null/malformed).
  function buildModel(ws) {
    if (!ws || typeof ws !== 'object') return null;
    const done = num(ws.studied_minutes);
    const target =
      ws.target_minutes === null || ws.target_minutes === undefined ? null : num(ws.target_minutes);
    const byKind = ws.by_kind && typeof ws.by_kind === 'object' ? ws.by_kind : {};
    const kinds = KIND_ORDER.map(function (k) {
      const entry = byKind[k] || {};
      return { kind: k, minutes: num(entry.minutes), seconds: num(entry.seconds) };
    }).filter(function (k) {
      return k.minutes > 0;
    });
    return {
      done: done,
      target: target && target > 0 ? target : null,
      pct: target && target > 0 ? Math.min(100, Math.round((100 * done) / target)) : null,
      kinds: kinds,
    };
  }

  // t(key, params) is the page's i18n function.
  function render(container, ws, t) {
    if (!container) return;
    container.textContent = '';
    const model = buildModel(ws);
    if (!model) {
      container.hidden = true;
      return;
    }
    container.hidden = false;
    const doc = container.ownerDocument;

    const title = doc.createElement('div');
    title.className = 'fw-semibold mb-1';
    title.id = 'weeklyStudiedTitle';
    title.textContent =
      model.target === null
        ? t('study_plan.studied.progress_no_target', { done: model.done })
        : t('study_plan.studied.progress', { done: model.done, target: model.target });
    container.appendChild(title);

    if (model.pct !== null) {
      const bar = doc.createElement('div');
      bar.className = 'progress mb-2';
      bar.style.height = '.6rem';
      const fill = doc.createElement('div');
      fill.className = 'progress-bar';
      fill.setAttribute('role', 'progressbar');
      fill.style.width = model.pct + '%';
      fill.setAttribute('aria-valuenow', String(model.pct));
      fill.setAttribute('aria-valuemin', '0');
      fill.setAttribute('aria-valuemax', '100');
      bar.appendChild(fill);
      container.appendChild(bar);
    }

    const heading = doc.createElement('div');
    heading.className = 'text-muted small';
    heading.textContent = t('study_plan.studied.breakdown_title');
    container.appendChild(heading);

    if (model.kinds.length === 0) {
      const empty = doc.createElement('div');
      empty.className = 'text-muted small';
      empty.textContent = t('study_plan.studied.empty');
      container.appendChild(empty);
      return;
    }
    const list = doc.createElement('ul');
    list.className = 'list-unstyled small mb-0';
    model.kinds.forEach(function (k) {
      const li = doc.createElement('li');
      li.dataset.kind = k.kind;
      li.textContent = t('study_plan.studied.kind.' + k.kind) + ': ' + t('study_plan.studied.minutes', { n: k.minutes });
      list.appendChild(li);
    });
    container.appendChild(list);
  }

  root.WeeklyStudy = { KIND_ORDER: KIND_ORDER, buildModel: buildModel, render: render };
})(typeof window !== 'undefined' ? window : globalThis);
