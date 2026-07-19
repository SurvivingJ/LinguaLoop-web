/* Dual Translation — error-profile self-regulation dashboard (TASK-611).
 *
 * Consumes GET /api/dual-translation/profile ->
 *   { entries: [{ subtype, l1_language, l2_language, count, severity_rank,
 *                 remediation_status, trend }] }
 *
 * The list arrives pre-ranked by severity_rank (frequency x severity) from
 * the server. This UI deliberately never renders severity_rank itself —
 * per the feature's self-regulation design, the dashboard gamifies the
 * *shrinking profile* (patterns trending down, patterns reaching
 * "resolved"), never a raw score the learner could optimize for its own
 * sake.
 */
(function () {
  'use strict';

  const el = {};

  function tr(key, params) {
    return window.LinguaI18n && window.LinguaI18n.t ? window.LinguaI18n.t(key, params) : key;
  }

  function label(key, fallback) {
    const v = tr(key);
    return v == null || v === key ? fallback : v;
  }

  function escapeHtml(s) {
    if (window.LinguaUtils && window.LinguaUtils.escapeHtml) {
      return window.LinguaUtils.escapeHtml(String(s == null ? '' : s));
    }
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Open-ended taxonomy axis — humanize rather than ship N x 4 i18n rows
  // (matches static/js/dual_translation.js's convention).
  function humanize(slug) {
    if (!slug) return '';
    return String(slug)
      .replace(/_/g, ' ')
      .replace(/^\w/, (c) => c.toUpperCase());
  }

  async function init() {
    cacheEls();
    try {
      if (window.LinguaI18n && window.LinguaI18n.init) {
        await window.LinguaI18n.init();
      }
    } catch (e) {
      /* i18n is best-effort; fall back to embedded defaults */
    }
    await load();
  }

  function cacheEls() {
    [
      'dtpLoading',
      'dtpError',
      'dtpEmpty',
      'dtpResolvedBanner',
      'dtpActiveLabel',
      'dtpActiveList',
      'dtpResolvedSection',
      'dtpResolvedList',
    ].forEach(function (id) {
      const key = id.charAt(3).toLowerCase() + id.slice(4);
      el[key] = document.getElementById(id);
    });
  }

  async function load() {
    let resp;
    try {
      resp = await window.authFetch('/api/dual-translation/profile');
    } catch (e) {
      return showError(tr('dual_translation.profile.error_load'));
    }
    if (!resp || !resp.ok) {
      return showError(
        tr('dual_translation.profile.error_load') + (resp ? ' (' + resp.status + ')' : '')
      );
    }
    const data = await resp.json();
    el.loading.style.display = 'none';
    render(data.entries || []);
  }

  function showError(message) {
    el.loading.style.display = 'none';
    el.error.textContent = message;
    el.error.style.display = 'block';
  }

  function render(entries) {
    if (!entries.length) {
      el.empty.style.display = 'block';
      return;
    }

    // Server order is severity_rank DESC; split into active vs. resolved
    // while preserving that order within each group, so the "watching" list
    // stays ranked and the resolved list reads as a trophy case.
    const active = entries.filter((e) => e.remediation_status !== 'resolved');
    const resolved = entries.filter((e) => e.remediation_status === 'resolved');

    if (resolved.length) {
      el.resolvedBanner.style.display = 'flex';
      el.resolvedBanner.textContent =
        '🎉 ' + tr('dual_translation.profile.resolved_banner', { count: resolved.length });
    }

    if (active.length) {
      el.activeLabel.style.display = 'block';
      el.activeList.innerHTML = active.map(buildCard).join('');
    }

    if (resolved.length) {
      el.resolvedSection.style.display = 'block';
      el.resolvedList.innerHTML = resolved.map(buildCard).join('');
    }
  }

  function statusLabel(status) {
    return label('dual_translation.profile.status.' + status, humanize(status));
  }

  // Never shows the raw delta_pct number in a way that reads as "your score
  // is X" — frames it purely as fewer/more occurrences this window, and a
  // learner with no prior-window baseline just sees the pair/subtype card
  // with no trend line (nothing to compare against yet).
  function trendMarkup(trend) {
    if (!trend || trend.delta_pct == null) return '';
    const improving = trend.delta_pct < 0;
    const flat = trend.delta_pct === 0;
    const cls = flat ? 'flat' : improving ? 'down' : 'up';
    const text = flat
      ? tr('dual_translation.profile.trend_flat')
      : improving
        ? tr('dual_translation.profile.trend_down', { pct: Math.abs(trend.delta_pct) })
        : tr('dual_translation.profile.trend_up', { pct: Math.abs(trend.delta_pct) });
    return '<span class="dtp-trend ' + cls + '">' + escapeHtml(text) + '</span>';
  }

  function buildCard(entry) {
    const status = entry.remediation_status || 'watching';
    const pair =
      (entry.l1_language || '?').toUpperCase() + ' → ' + (entry.l2_language || '?').toUpperCase();
    return (
      '<div class="dtp-card status-' +
      escapeHtml(status) +
      '">' +
      '<div class="dtp-card-main">' +
      '<div class="dtp-subtype">' +
      escapeHtml(humanize(entry.subtype)) +
      '</div>' +
      '<div class="dtp-pair">' +
      escapeHtml(pair) +
      '</div>' +
      '</div>' +
      '<span class="dtp-status status-' +
      escapeHtml(status) +
      '">' +
      escapeHtml(statusLabel(status)) +
      '</span>' +
      trendMarkup(entry.trend) +
      '</div>'
    );
  }

  document.addEventListener('DOMContentLoaded', init);
})();
