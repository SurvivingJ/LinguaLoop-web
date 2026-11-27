// static/js/grammar/ladder.js
// Grammar drills: the four-stage ladder of a topic. No DOM.
//
//   1 Recognise  cloze with the item's options, judge
//   2 Build      + order and rewrite (half the round)
//   3 Recall     cloze answered from the topic's answer bank, or typed
//   4 Speed      everything against a per-item countdown
//
// A stage unlocks the next when the last WINDOW answers at it are at least
// UNLOCK_ACC correct. A topic is "instant" at stage 4 with INSTANT_ACC and a
// median answer time under INSTANT_MS.

import { median } from './text.js';

export const ALL_TYPES = ['cloze', 'judge', 'order', 'rewrite'];

export const STAGES = [
  { n: 1, key: 'recognise', types: ['cloze', 'judge'] },
  { n: 2, key: 'build', types: ALL_TYPES, focus: ['order', 'rewrite'], focusShare: 0.5 },
  { n: 3, key: 'recall', types: ALL_TYPES, focus: ['cloze'], focusShare: 0.6, recall: true },
  { n: 4, key: 'speed', types: ALL_TYPES, recall: true, timed: true },
];

export const LAST_STAGE = STAGES.length;
export const WINDOW = 30;
export const UNLOCK_ACC = 0.85;
export const INSTANT_ACC = 0.9;
export const INSTANT_MS = 3000;

export const SPEED_START_MS = 8000;
export const SPEED_MIN_MS = 4000;
export const SPEED_STEP_MS = 500;
/** Right answers in a row before the countdown tightens one step. */
export const SPEED_STREAK = 5;
/** Extra time per tile for order / rewrite items. */
export const SPEED_PER_TILE_MS = 1200;

const MAX_MS = 600000;

export function stageDef(n) {
  return STAGES[Math.min(LAST_STAGE, Math.max(1, n | 0 || 1)) - 1];
}

/** One answer as a signed integer: +ms when right, -ms when wrong. */
export function encodeResult(ok, ms) {
  const t = Math.min(MAX_MS, Math.max(1, Math.round(ms) || 1));
  return ok ? t : -t;
}

/** { n, correct, acc, medianMs } for a list of encoded results. */
export function stageStats(results) {
  const list = results || [];
  const correct = list.filter((r) => r > 0).length;
  return {
    n: list.length,
    correct,
    acc: list.length ? correct / list.length : 0,
    medianMs: median(list.map((r) => Math.abs(r))),
  };
}

/** The last WINDOW answers at a stage are enough to open the next one. */
export function unlocksNext(results) {
  const s = stageStats((results || []).slice(-WINDOW));
  return s.n >= WINDOW && s.acc >= UNLOCK_ACC;
}

/** `topic` is the store's view: { unlocked, results: { 1: [...], ... } }. */
export function isInstant(topic) {
  if (!topic || topic.unlocked < LAST_STAGE) return false;
  const s = stageStats((topic.results[LAST_STAGE] || []).slice(-WINDOW));
  return s.n >= WINDOW && s.acc >= INSTANT_ACC && s.medianMs < INSTANT_MS;
}

/**
 * Highest item level (1-3) to draw from. Level 1 to begin with; level 2 after
 * ten answers at 75%; level 3 after thirty at 80%. Judged on the highest stage
 * that has at least ten answers, else on everything recorded.
 */
export function levelCap(topic) {
  if (!topic) return 1;
  let recent = [];
  for (let n = LAST_STAGE; n >= 1; n--) {
    const r = topic.results[n] || [];
    if (r.length >= 10) {
      recent = r;
      break;
    }
  }
  const all = STAGES.reduce((sum, s) => sum + (topic.results[s.n] || []).length, 0);
  if (!recent.length) recent = STAGES.flatMap((s) => topic.results[s.n] || []);
  const { n, acc } = stageStats(recent);
  if (n < 10 || acc < 0.75) return 1;
  if (all < 30 || acc < 0.8) return 2;
  return 3;
}

/** Countdown for one item at the speed stage. */
export function speedLimit(baseMs, item) {
  const base = baseMs || SPEED_START_MS;
  const tiles =
    item && (item.type === 'order' || item.type === 'rewrite')
      ? (item.tokens || []).length + (item.extra || []).length
      : 0;
  return base + tiles * SPEED_PER_TILE_MS;
}

/**
 * The base countdown after an answer: one step tighter after SPEED_STREAK
 * right in a row, one step looser after a miss. `streak` counts the answer
 * just given.
 */
export function nextSpeedBase(baseMs, ok, streak) {
  const base = baseMs || SPEED_START_MS;
  if (!ok) return Math.min(SPEED_START_MS, base + SPEED_STEP_MS);
  if (streak > 0 && streak % SPEED_STREAK === 0) {
    return Math.max(SPEED_MIN_MS, base - SPEED_STEP_MS);
  }
  return base;
}

/** 'new' | 'recognise' | 'build' | 'recall' | 'speed' | 'instant' for the hub. */
export function topicStatus(topic) {
  if (!topic || !topic.answers) return 'new';
  if (isInstant(topic)) return 'instant';
  return stageDef(topic.stage).key;
}
