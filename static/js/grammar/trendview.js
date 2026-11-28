// static/js/grammar/trendview.js
// Grammar drills: the progress views as HTML strings (inline SVG, no chart
// library). The figures come from trends.js; nothing here reads the DOM.
// Styles: .gd-trend* in static/css/redesign/grammar.css.
//
// Each chart shows one measure on its own scale (accuracy and recall time are
// two small charts, never one chart with two axes), names its latest value in
// text beside it, and carries an aria-label plus a <title> per point, so no
// reading depends on colour or on hovering.

import { escapeHtml } from '../session/dom.js';
import { t } from './render.js';
import { hubSummary, linePoints, needsWork, topicSeries, trendOf } from './trends.js';

const W = 160;
const H = 44;
const PAD = 6;

const one = (x) => (Math.round(x * 10) / 10).toFixed(1);
const signed = (text, x) => (x > 0 ? '+' : x < 0 ? '−' : '±') + text;

/** '2026-11-27' -> '27 Nov' in the browser's language. */
export function dayLabel(day) {
  try {
    const d = new Date(String(day).slice(0, 10) + 'T12:00:00Z');
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', timeZone: 'UTC' });
  } catch {
    return String(day);
  }
}

const pctText = (v) => Math.round(v) + '%';
const secText = (v) => t('seconds', { n: one(v) }, '{n} s');

function deltaText(trend, kind) {
  if (!trend || trend.delta == null) return '';
  const amount =
    kind === 'acc'
      ? t('progress_points', { n: Math.abs(Math.round(trend.delta)) }, '{n} pts')
      : secText(Math.abs(trend.delta));
  const rounded = kind === 'acc' ? Math.round(trend.delta) : Number(one(trend.delta));
  const delta = signed(amount, rounded);
  return trend.versus === 'week'
    ? t('progress_vs_first_week', { delta }, '{delta} since your first week')
    : t('progress_vs_first_day', { delta }, '{delta} since your first day');
}

/** One measure: label, latest value, change in words, and its line. */
function measureHtml(kind, trend, label) {
  const fmt = kind === 'acc' ? pctText : secText;
  if (!trend) {
    return (
      '<div class="gd-trend__m"><p class="ld-eyebrow">' +
      escapeHtml(label) +
      '</p><p class="gd-trend__v ld-num">–</p><p class="gd-trend__d">' +
      escapeHtml(t('progress_no_recall', null, 'No timed answers yet.')) +
      '</p></div>'
    );
  }
  const values = trend.values.map((p) => p.value);
  // Accuracy: 50-100% unless a day fell lower. Recall time: from zero.
  const scale =
    kind === 'acc'
      ? { min: Math.min(50, ...values), max: 100 }
      : { min: 0, max: Math.max(...values) * 1.1 || 1 };
  const { points, d } = linePoints(values, { w: W, h: H, pad: PAD, ...scale });
  const last = points[points.length - 1];
  const aria = t(
    kind === 'acc' ? 'progress_chart_acc' : 'progress_chart_recall',
    { n: values.length, first: fmt(values[0]), last: fmt(values[values.length - 1]) },
    kind === 'acc'
      ? 'Accuracy over {n} practised days, from {first} to {last}'
      : 'Average recall time over {n} practised days, from {first} to {last}'
  );
  const hits = points
    .map(
      (p, k) =>
        '<circle class="gd-trend__hit" cx="' +
        p.x +
        '" cy="' +
        p.y +
        '" r="7"><title>' +
        escapeHtml(dayLabel(trend.values[k].day) + ': ' + fmt(values[k])) +
        '</title></circle>'
    )
    .join('');
  const svg =
    '<svg class="gd-trend__svg" viewBox="0 0 ' +
    W +
    ' ' +
    H +
    '" role="img" aria-label="' +
    escapeHtml(aria) +
    '"><line class="gd-trend__base" x1="0" y1="' +
    (H - 1) +
    '" x2="' +
    W +
    '" y2="' +
    (H - 1) +
    '"/>' +
    (points.length > 1 ? '<path class="gd-trend__line" d="' + d + '"/>' : '') +
    '<circle class="gd-trend__dot" cx="' +
    last.x +
    '" cy="' +
    last.y +
    '" r="4"/>' +
    hits +
    '</svg>';
  return (
    '<div class="gd-trend__m" data-measure="' +
    kind +
    '"><p class="ld-eyebrow">' +
    escapeHtml(label) +
    '</p><p class="gd-trend__v ld-num">' +
    escapeHtml(fmt(trend.latest)) +
    '</p>' +
    svg +
    '<p class="gd-trend__d">' +
    escapeHtml(deltaText(trend, kind)) +
    '</p></div>'
  );
}

/**
 * The topic screen's Progress card. `subs` is the topic's [{ key, label }].
 * '' when there is no server progress at all (`progress` null).
 */
export function topicProgressHtml(progress, slug, subs) {
  if (!progress) return '';
  const head = '<h2 class="ld-h2">' + escapeHtml(t('progress_title', null, 'Progress')) + '</h2>';
  const series = topicSeries(progress.daily, slug);
  if (!series.length) {
    return (
      '<section class="ld-card gd-trend" data-days="0">' +
      head +
      '<p class="gd-note">' +
      escapeHtml(
        t('progress_empty', null, 'Nothing recorded for this topic yet. Finish a round to start.')
      ) +
      '</p></section>'
    );
  }
  const labels = new Map((subs || []).map((s) => [s.key, s.label]));
  const needs = needsWork(progress.daily, slug, { today: progress.today });
  const needsHtml =
    '<div class="gd-trend__needs"><h3 class="ld-eyebrow">' +
    escapeHtml(t('progress_needs_work', null, 'Needs work · last 14 days')) +
    '</h3>' +
    (needs.length
      ? '<ul>' +
        needs
          .map(
            (n) =>
              '<li><span>' +
              escapeHtml(labels.get(n.key) || n.key) +
              '</span><b class="ld-num">' +
              escapeHtml(t('progress_misses_n', { n: n.misses }, '{n} missed')) +
              '</b></li>'
          )
          .join('') +
        '</ul>'
      : '<p class="gd-note">' +
        escapeHtml(t('progress_no_misses', null, 'No misses in the last 14 days.')) +
        '</p>') +
    '</div>';
  return (
    '<section class="ld-card gd-trend" data-days="' +
    series.length +
    '">' +
    head +
    '<div class="gd-trend__grid">' +
    measureHtml('acc', trendOf(series, 'acc'), t('progress_accuracy', null, 'Accuracy')) +
    measureHtml('secs', trendOf(series, 'secs'), t('progress_recall', null, 'Recall time')) +
    '</div><p class="gd-note">' +
    escapeHtml(
      series.length === 1
        ? t(
            'progress_one_day',
            null,
            'One day recorded so far. Practise on another day to see a trend.'
          )
        : t(
            'progress_days_n',
            { n: series.length },
            'Each point is one day you practised ({n} days).'
          )
    ) +
    '</p>' +
    needsHtml +
    '</section>'
  );
}

/**
 * The hub's progress card: days practised, answers, instant topics and a
 * strip of the last 30 days. '' when there is no server progress or nothing
 * has been recorded.
 */
export function hubProgressHtml(progress, instantCount) {
  if (!progress) return '';
  const sum = hubSummary(progress.daily, { today: progress.today });
  if (!sum.answers) return '';
  const stat = (n, label) =>
    '<div class="ld-stat"><div class="ld-stat__n">' +
    escapeHtml(String(n)) +
    '</div><small>' +
    escapeHtml(label) +
    '</small></div>';
  const cell = 8;
  const gap = 2;
  const width = sum.strip.length * (cell + gap) - gap;
  const strip =
    '<svg class="gd-trend__strip" viewBox="0 0 ' +
    width +
    ' 14" role="img" aria-label="' +
    escapeHtml(t('hub_strip_label', { n: sum.days }, 'Practice on {n} of the last 30 days')) +
    '">' +
    sum.strip
      .map(
        (d, k) =>
          '<rect class="gd-trend__cell gd-trend__cell--' +
          d.level +
          '" x="' +
          k * (cell + gap) +
          '" y="0" width="' +
          cell +
          '" height="14" rx="2"><title>' +
          escapeHtml(
            t('hub_strip_day', { day: dayLabel(d.day), n: d.answers }, '{day}: {n} answers')
          ) +
          '</title></rect>'
      )
      .join('') +
    '</svg>';
  return (
    '<section class="gd-trend gd-trend--hub"><h2 class="ld-h2">' +
    escapeHtml(t('hub_progress_title', null, 'Your progress')) +
    '</h2><div class="ld-stats">' +
    stat(sum.days, t('hub_days', null, 'Days practised, last 30')) +
    stat(sum.answers.toLocaleString(), t('hub_answers', null, 'Answers')) +
    stat(instantCount, t('hub_instant', null, 'Instant topics')) +
    '</div>' +
    strip +
    '<p class="gd-note gd-trend__cap"><span>' +
    escapeHtml(dayLabel(sum.strip[0].day)) +
    '</span><span>' +
    escapeHtml(dayLabel(sum.strip[sum.strip.length - 1].day)) +
    '</span></p></section>'
  );
}
