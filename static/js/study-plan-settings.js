/**
 * Pure helpers for the "Daily session" card on /study-plan
 * (session-budget-settings, TASK-868).
 *
 * No DOM access: templates/study_plan.html feeds these the GET /api/study-plan
 * payload plus the unsaved form values and renders the descriptors they return
 * (message key + params), so the arithmetic is unit-testable
 * (tests/unit/study-plan-settings.test.js).
 *
 * Mirrors services/study_plan_service.py: new_words_for_day, new_words_week_target,
 * effective_new_words. Rounding is floor(x + 0.5), NOT Math.round-on-negative /
 * banker's rounding, so JS, Python and SQL agree on .5 ties.
 *
 * Exposed as a plain global (window.StudyPlanSettings) like ExRenderers and
 * DTErrorCard: the page loads it with a classic <script> tag.
 */
const StudyPlanSettings = (function () {
  'use strict';

  const MODULE_PRACTICE = 'practice';
  const MODULE_FLASHCARDS = 'flashcards';
  const NEW_WORDS_MAX = 50;
  const DEFAULT_SHAPE = [1, 1, 1, 1, 1, 1, 1];

  const toNum = (v, fallback) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  };

  /** Round half up for non-negative values (matches SQL floor(x + 0.5)). */
  function roundHalfUp(x) {
    return Math.floor(x + 0.5);
  }

  /** Clamp a user-typed value to an integer in [0, 50]; NaN -> fallback. */
  function clampNewWords(value, fallback) {
    const n = parseInt(value, 10);
    if (Number.isNaN(n)) return fallback === undefined ? 0 : fallback;
    return Math.max(0, Math.min(NEW_WORDS_MAX, n));
  }

  /** The day's quota Q for a weekday weight (mirror of new_words_for_day). */
  function newWordsForDay(newWordsPerDay, weight) {
    const npd = toNum(newWordsPerDay, 0);
    const w = toNum(weight, 0);
    if (w <= 0 || npd <= 0) return 0;
    return roundHalfUp(npd * w);
  }

  /** Weekly quota across the 7 weekday weights (mirror of new_words_week_target). */
  function newWordsWeekTarget(newWordsPerDay, shape) {
    const weights = Array.isArray(shape) && shape.length ? shape : DEFAULT_SHAPE;
    return weights.reduce((sum, w) => sum + newWordsForDay(newWordsPerDay, w), 0);
  }

  /** Governor: effective quota E = Q | floor(Q / 2) | 0 (mirror of effective_new_words). */
  function effectiveNewWords(quota, level) {
    const q = Math.max(0, toNum(quota, 0));
    if (level === 'paused') return 0;
    if (level === 'reduced') return Math.floor(q / 2);
    return q;
  }

  /**
   * "~+X min/day of reviews in a month". The server supplies the constants
   * (reviews_per_new_word_30d, item_seconds); the client hard-codes neither.
   * X = round(avgNewWords * reviews_per_new_word_30d * item_seconds / 60).
   */
  function forecastMinutes(newWordsPerDay, shape, forecast) {
    if (!forecast) return 0;
    const avg = newWordsWeekTarget(newWordsPerDay, shape) / 7;
    const perWord = toNum(forecast.reviews_per_new_word_30d, 0);
    const itemSeconds = toNum(forecast.item_seconds, 0);
    return Math.round((avg * perWord * itemSeconds) / 60);
  }

  /** Include/exclude codes -> Set of included codes. */
  function includedSet(available, excluded) {
    const ex = new Set(excluded || []);
    return new Set((available || []).filter((c) => !ex.has(c)));
  }

  /**
   * Which module switches are disabled, and the "flashcards only" hint.
   *   - the last checked module is locked while new words are 0
   *     (new words > 0 count as an included module);
   *   - under tests_only the last checked NON-review module is locked too, because
   *     the API rejects tests_only without a test/surface module.
   */
  function moduleState(available, included, newWordsPerDay, scope) {
    const inc = included instanceof Set ? included : new Set(included || []);
    const npd = toNum(newWordsPerDay, 0);
    const locks = {};
    (available || []).forEach((code) => {
      let reason = null;
      if (inc.has(code)) {
        if (inc.size === 1 && npd <= 0) reason = 'last_one';
        else if (scope === 'tests_only' && code !== MODULE_PRACTICE) {
          const tests = [...inc].filter((c) => c !== MODULE_PRACTICE);
          if (tests.length === 1) reason = 'last_test';
        }
      }
      locks[code] = reason;
    });
    const flashcardsOnly = inc.size === 1 && inc.has(MODULE_FLASHCARDS) && npd <= 0;
    return { locks, flashcardsOnly };
  }

  /** tests_only is meaningless without a test or surface module included. */
  function testsOnlyDisabled(included) {
    const inc = included instanceof Set ? included : new Set(included || []);
    return [...inc].filter((c) => c !== MODULE_PRACTICE).length === 0;
  }

  /** i18n key suffix of the governor message, or null when level is normal. */
  function governorMessageKey(governor) {
    const level = governor && governor.level;
    if (level === 'paused') return 'paused';
    if (level === 'reduced') return 'reduced';
    return null;
  }

  /**
   * Everything the card shows for one set of (unsaved) form values.
   *
   * @param {object} p
   *   daily, scope, practiceIncluded, newWordsPerDay, shape,
   *   minutesPerNewWord, typicalDay ({practice_room_min_per_day, review_min_per_day} | null),
   *   governor ({level}), forecast
   */
  function computeCard(p) {
    const npd = clampNewWords(p.newWordsPerDay, 0);
    const mpnw = toNum(p.minutesPerNewWord, 0);
    const typical = p.typicalDay || null;
    const inBudgetMode = p.scope !== 'tests_only' && !!p.practiceIncluded;
    const room = typical ? Math.max(0, toNum(typical.practice_room_min_per_day, 0)) : 0;
    const reviewMin = typical ? Math.max(0, toNum(typical.review_min_per_day, 0)) : 0;
    const capacity = mpnw > 0 ? Math.floor(room / mpnw + 1e-9) : 0;

    // Spec: inBudgetWords is computed from the input itself (not the governor).
    const inBudgetWords = inBudgetMode ? Math.min(npd, capacity) : 0;
    const tailWords = npd - inBudgetWords;

    // Estimate line (mockup): what today looks like after the review-load governor.
    const level = (p.governor && p.governor.level) || 'normal';
    const effective = effectiveNewWords(npd, level);
    const fit = inBudgetMode ? Math.min(effective, capacity) : 0;
    const after = effective - fit;
    let estimate = 'split';
    if (npd === 0) estimate = 'off';
    else if (effective === 0) estimate = 'paused';

    return {
      npd,
      mode: inBudgetMode ? 'in_budget' : 'tail_only',
      inBudgetWords,
      tailWords,
      tailMinutes: Math.round(tailWords * mpnw),
      wordsMinutes: Math.round(npd * mpnw),
      reviewMinPerDay: Math.round(reviewMin),
      hasTypicalDay: !!typical,
      effective,
      estimate,
      fit,
      after,
      forecastMin: forecastMinutes(npd, p.shape, p.forecast),
      governorKey: governorMessageKey(p.governor),
      // #newWordsNoReviewWarning: Vocabulary review off AND new words > 0. Advisory only.
      noReviewWarning: !p.practiceIncluded && npd > 0,
    };
  }

  /**
   * Typical-day summary descriptor: { key, params, tail } where `tail` is an optional
   * second sentence { key, params }. null when there is no current week.
   * Keys are relative to study_plan.daily_session.
   */
  function typicalDaySummary(card, daily, practiceIncluded) {
    if (!card.hasTypicalDay) return null;
    if (card.mode === 'in_budget') {
      const base =
        card.npd > 0
          ? {
              key: 'typical_day',
              params: { daily, words: card.inBudgetWords, review: card.reviewMinPerDay },
            }
          : { key: 'typical_day_no_words', params: { daily, review: card.reviewMinPerDay } };
      const tail =
        card.tailWords > 0
          ? {
              key: 'typical_day_tail',
              params: { words: card.tailWords, minutes: card.tailMinutes },
            }
          : null;
      return Object.assign({}, base, { tail });
    }
    const wantsReview = !!practiceIncluded && card.reviewMinPerDay > 0;
    const params = {
      daily,
      review: card.reviewMinPerDay,
      words: card.npd,
      minutes: card.wordsMinutes,
    };
    if (wantsReview && card.npd > 0) return { key: 'typical_day_tests_only', params, tail: null };
    if (wantsReview) return { key: 'typical_day_tests_only_no_words', params, tail: null };
    if (card.npd > 0) return { key: 'typical_day_tests_only_no_review', params, tail: null };
    return { key: 'typical_day_tests_only_none', params, tail: null };
  }

  /** Hint under the new-words input: key suffix + params (relative to daily_session.new_words). */
  function hintDescriptor(card, daily) {
    if (card.mode === 'in_budget') {
      return { key: 'hint_in_budget', params: { words: card.inBudgetWords, daily } };
    }
    return { key: 'hint_tail_only', params: {} };
  }

  return {
    NEW_WORDS_MAX,
    clampNewWords,
    newWordsForDay,
    newWordsWeekTarget,
    effectiveNewWords,
    forecastMinutes,
    includedSet,
    moduleState,
    testsOnlyDisabled,
    governorMessageKey,
    computeCard,
    typicalDaySummary,
    hintDescriptor,
  };
})();

window.StudyPlanSettings = StudyPlanSettings;
