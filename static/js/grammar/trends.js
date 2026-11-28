// static/js/grammar/trends.js
// Grammar drills: shapes the server's daily summaries for the progress views.
// No DOM, no network. A daily row is
//   { topic, day: 'YYYY-MM-DD', answers, correct, timed, ms_sum, stage,
//     instant, sub_misses: { <sub key>: misses } }
// with counts over first answers; `timed` answers are the right ones and
// `ms_sum` their recall time in ms.

export const TREND_DAYS = 30;
export const NEEDS_WORK_DAYS = 14;
export const NEEDS_WORK_TOP = 3;
export const HUB_DAYS = 30;
const DAY_MS = 86400000;

const num = (x) => (Number.isFinite(Number(x)) ? Number(x) : 0);
const stamp = (day) => Date.parse(String(day).slice(0, 10) + 'T00:00:00Z');

/** Whole days from ISO day `a` to ISO day `b` (negative when b is earlier). */
export function dayDiff(a, b) {
  const d = (stamp(b) - stamp(a)) / DAY_MS;
  return Number.isFinite(d) ? Math.round(d) : NaN;
}

/** ISO day `n` days after `day`. */
export function addDays(day, n) {
  const t = stamp(day);
  return Number.isFinite(t) ? new Date(t + n * DAY_MS).toISOString().slice(0, 10) : '';
}

/**
 * One topic's last `limit` practised days, oldest first:
 * [{ day, answers, correct, timed, ms, acc (0-100), secs (seconds or null) }].
 * Rows for one day are added together.
 */
export function topicSeries(daily, slug, { limit = TREND_DAYS } = {}) {
  const byDay = new Map();
  (daily || []).forEach((row) => {
    if (!row || row.topic !== slug || !row.day || !(num(row.answers) > 0)) return;
    const d = byDay.get(row.day) || { day: row.day, answers: 0, correct: 0, timed: 0, ms: 0 };
    d.answers += num(row.answers);
    d.correct += num(row.correct);
    d.timed += num(row.timed);
    d.ms += num(row.ms_sum);
    byDay.set(row.day, d);
  });
  return [...byDay.values()]
    .sort((a, b) => (a.day < b.day ? -1 : 1))
    .slice(-limit)
    .map((d) => ({
      ...d,
      acc: (d.correct / d.answers) * 100,
      secs: d.timed > 0 ? d.ms / d.timed / 1000 : null,
    }));
}

function measure(days, field) {
  if (field === 'acc') {
    const answers = days.reduce((n, d) => n + d.answers, 0);
    return answers ? (days.reduce((n, d) => n + d.correct, 0) / answers) * 100 : null;
  }
  const timed = days.reduce((n, d) => n + d.timed, 0);
  return timed ? days.reduce((n, d) => n + d.ms, 0) / timed / 1000 : null;
}

/**
 * The trend of 'acc' or 'secs' over a series from topicSeries:
 *   { values: [{ day, value }], latest, base, delta, versus }
 * `values` leaves out days without the measure. `base` is the measure over
 * the first week (the seven days from the first practised day), and `versus`
 * is 'week'; while the latest day is still inside that week, `base` is the
 * first day and `versus` is 'day'. With one day there is nothing to compare:
 * delta null, versus ''. Null when no day has the measure.
 */
export function trendOf(series, field) {
  const days = (series || []).filter((d) => d[field] != null);
  if (!days.length) return null;
  const values = days.map((d) => ({ day: d.day, value: d[field] }));
  const last = days[days.length - 1];
  const out = { values, latest: last[field], base: null, delta: null, versus: '' };
  if (days.length < 2) return out;
  const week = days.filter((d) => dayDiff(days[0].day, d.day) < 7);
  const inFirstWeek = week.includes(last);
  out.base = inFirstWeek ? days[0][field] : measure(week, field);
  out.versus = inFirstWeek ? 'day' : 'week';
  out.delta = out.base == null ? null : last[field] - out.base;
  return out;
}

/**
 * The sub-points missed most in the `days` up to and including `today`:
 * [{ key, misses }], most missed first, at most `top`.
 */
export function needsWork(
  daily,
  slug,
  { today, days = NEEDS_WORK_DAYS, top = NEEDS_WORK_TOP } = {}
) {
  const totals = new Map();
  (daily || []).forEach((row) => {
    if (!row || row.topic !== slug || !row.sub_misses) return;
    const age = today ? dayDiff(row.day, today) : 0;
    if (!(age >= 0 && age < days)) return;
    Object.keys(row.sub_misses).forEach((key) => {
      const n = num(row.sub_misses[key]);
      if (n > 0) totals.set(key, (totals.get(key) || 0) + n);
    });
  });
  return [...totals.entries()]
    .map(([key, misses]) => ({ key, misses }))
    .sort((a, b) => b.misses - a.misses || (a.key < b.key ? -1 : 1))
    .slice(0, top);
}

/**
 * The hub's figures: { days, answers, strip, max }.
 *   days     days with any practice among the last `days` (ending `today`)
 *   answers  first answers over everything in `daily`
 *   strip    one entry per day of the window, oldest first:
 *            { day, answers, level } with level 0 (none) to 4
 */
export function hubSummary(daily, { today, days = HUB_DAYS } = {}) {
  const perDay = new Map();
  let answers = 0;
  (daily || []).forEach((row) => {
    if (!row || !row.day) return;
    const n = num(row.answers);
    answers += n;
    perDay.set(row.day, (perDay.get(row.day) || 0) + n);
  });
  const strip = [];
  if (today) {
    for (let k = days - 1; k >= 0; k--) {
      const day = addDays(today, -k);
      strip.push({ day, answers: perDay.get(day) || 0, level: 0 });
    }
  }
  const max = strip.reduce((m, d) => Math.max(m, d.answers), 0);
  strip.forEach((d) => {
    d.level = d.answers > 0 ? Math.max(1, Math.ceil((d.answers / max) * 4)) : 0;
  });
  return { days: strip.filter((d) => d.answers > 0).length, answers, strip, max };
}

/**
 * Points of a small line chart for `values` (numbers, oldest first) inside a
 * `w` x `h` box with `pad` on every side. `min` / `max` fix the scale; left
 * out, the data's own range is used. One value sits in the middle of the box.
 * Returns { points: [{ x, y }], d } with `d` the SVG path.
 */
export function linePoints(values, { w, h, pad = 0, min, max } = {}) {
  const list = (values || []).map(num);
  if (!list.length) return { points: [], d: '' };
  const lo = min != null ? min : Math.min(...list);
  const hi = max != null ? max : Math.max(...list);
  const span = hi - lo;
  const round = (x) => Math.round(x * 10) / 10;
  const points = list.map((v, k) => ({
    x: round(list.length === 1 ? w / 2 : pad + (k * (w - 2 * pad)) / (list.length - 1)),
    y: round(
      span > 0 ? h - pad - ((Math.min(hi, Math.max(lo, v)) - lo) / span) * (h - 2 * pad) : h / 2
    ),
  }));
  return { points, d: points.map((p, k) => (k ? 'L' : 'M') + p.x + ' ' + p.y).join(' ') };
}

/**
 * The progress after a round the server has just taken: its counts added to
 * `day`'s rows. `topics` are the entries that were sent. Returns a new object.
 */
export function applyRound(progress, day, topics) {
  if (!progress) return progress;
  const daily = (progress.daily || []).map((row) => ({ ...row }));
  const states = { ...(progress.states || {}) };
  (topics || []).forEach((t) => {
    if (!t || !t.topic) return;
    if (t.state) states[t.topic] = t.state;
    if (!(num(t.answers) > 0)) return;
    let row = daily.find((r) => r.topic === t.topic && r.day === day);
    if (!row) {
      row = {
        topic: t.topic,
        day,
        answers: 0,
        correct: 0,
        timed: 0,
        ms_sum: 0,
        stage: 1,
        sub_misses: {},
      };
      daily.push(row);
    }
    row.answers = num(row.answers) + num(t.answers);
    row.correct = num(row.correct) + num(t.correct);
    row.timed = num(row.timed) + num(t.timed);
    row.ms_sum = num(row.ms_sum) + num(t.ms_sum);
    row.stage = Math.max(num(row.stage) || 1, num(t.stage) || 1);
    row.instant = !!t.instant;
    row.sub_misses = { ...(row.sub_misses || {}) };
    Object.keys(t.sub_misses || {}).forEach((key) => {
      row.sub_misses[key] = num(row.sub_misses[key]) + num(t.sub_misses[key]);
    });
  });
  const today = progress.today && progress.today > day ? progress.today : day;
  return { ...progress, today, daily, states };
}
