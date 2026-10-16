"""
Study Plan Service — Tier B (weekly) adapter.

Implements the orchestration documented in [[features/study-plans.tech]]
and [[algorithms/study-plan-adaptation.tech]]:

  - compute_weekly_plan(user_id, language_id, week_start)
      → loads signals via compute_weekly_plan_load_signals,
        runs the weakness/value/bandit pipeline (Python because of
        deterministic Beta sampling per R3.2), persists via
        compute_weekly_plan_persist.

  - _run_weekly_plan_recompute()
      → APScheduler entry point (registered in app.py). Iterates every
        user_study_plans row and calls compute_weekly_plan, guarded by a
        Postgres advisory lock (same pattern as _run_irt_calibration).

  - build_daily_session(user_id, language_id, date)
      → Thin Python wrapper over the SQL RPC. Logged + error-handled so
        callers don't have to. See phase13_build_daily_session.sql for
        the actual greedy resolver.

Tier C (daily resolver) is implemented in SQL — see
phase13_build_daily_session.sql — because greedy fill is natural in SQL
window functions and there is no random sampling involved.

The weakness signal helpers (`weakness`, `value`, `bandit_score`,
`allocate_test_counts`, `rebalance_practice`) live in this module's private
section. They are deterministic given fixed inputs + a fixed seed.
"""

from __future__ import annotations

import hashlib
import logging
import math
from decimal import Decimal, ROUND_FLOOR
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from config import Config
from services.day_boundary import plan_today
from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)

# ============================================================================
# Constants — mirror wiki/algorithms/study-plan-adaptation.tech.md.
# ============================================================================

# Weakness-signal weights (Section 6a)
W_ELO   = 0.40
W_ACC   = 0.25
W_LAD   = 0.20
W_FSRS  = 0.15

# Diminishing-returns anchor (R2.7-ish; spec Section 6b)
DIM_ELO_FLOOR  = 1800     # below this: no diminishing
DIM_ELO_CEIL   = 2400     # at this: fully diminished
DIM_ELO_RANGE  = DIM_ELO_CEIL - DIM_ELO_FLOOR

# ELO-gap normalization range (Section 6a)
ELO_GAP_SPAN = 200.0

# Accuracy-trend target (Section 6a)
ACC_TREND_TARGET = 0.75

# Cold-start gate (R2.6)
COLD_START_MIN_ATTEMPTS = 5
COLD_START_WEAKNESS     = 0.50

# Bandit prior (R3.2)
BETA_PRIOR_ALPHA = 2.0
BETA_PRIOR_BETA  = 2.0

# Practice-pressure constants (Section 6e; scaled by daily_minutes per R3.1)
def target_review_rate(daily_minutes: int) -> int:
    """FSRS reviews-per-day target."""
    return max(1, daily_minutes // 2)

def target_active_pool(daily_minutes: int) -> int:
    """Active-ladder-words target."""
    return max(1, daily_minutes)

def target_new_rate(daily_minutes: int) -> int:
    """New-words-per-week target."""
    return max(1, daily_minutes // 6)


# Maintenance / Acquisition share bounds (ADR-009)
MAINT_SHARE_FLOOR = 0.15
MAINT_SHARE_CEIL  = 0.50
ACQ_SHARE_FLOOR   = 0.50
ACQ_SHARE_CEIL    = 0.85

# Carry-over decay (R3.4)
CARRY_OVER_DECAY = 0.5

# Catch-all minutes for a skill nobody seeded. Mirrors the SQL
# test_time_estimate `ELSE 5.0`. Named rather than inlined so the test that
# pins "no plannable surface may land here" (ADR-021) can reference it.
UNSEEDED_SKILL_MINUTES = 5

# Surfaces the planner budgets that are NOT dim_test_types rows and never
# resolve to an ELO-rated `tests` row (ADR-021 / TASK-714). Kept here because
# Tier B allocation walks weekly_test_counts without caring what a key is;
# the distinction only matters to the Tier C resolver and the session runner.
PLANNABLE_SURFACE_SKILLS = ('flashcards', 'dual_translation')

# Explicitly outside the planner (ADR-021). Both ARE dim_test_types rows, which
# is a modelling artefact, not an intent to schedule them — long-form
# exploratory content does not belong in a minute budget. Pinned by
# tests/test_plannable_surfaces.py.
UNPLANNED_TEST_TYPES = ('listening_lab', 'mystery')


# ----------------------------------------------------------------------------
# Session modules (ADR-032) and budget settings (ADR-033)
# wiki/features/session-modules.tech.md, session-budget-settings.tech.md
# ----------------------------------------------------------------------------

MODULE_PRACTICE = 'practice'
# Module vocabulary. MUST equal the SQL CHECK
# user_study_plans_excluded_modules_known (migrations/session_module_exclusions.sql);
# tests/test_session_modules.py pins that they agree.
ALL_MODULES = (
    'reading', 'listening', 'dictation', 'pinyin', 'classifier_drill',
    'pitch_accent', 'flashcards', 'dual_translation', MODULE_PRACTICE,
)
# Modules whose weekly count is NOT rescaled when others are excluded:
# flashcards is one review block a day whose real size is set by due cards.
NON_SCALABLE_MODULES = ('flashcards',)

# Must equal the SQL CHECK user_study_plans_budget_scope_known (test-pinned).
BUDGET_SCOPES = ('tests_and_review', 'tests_only')
DEFAULT_BUDGET_SCOPE = 'tests_and_review'
NEW_WORDS_MAX_PER_DAY = 50
# tests_only: review_target_minutes <= daily*7*0.5 (a weekly TARGET for the tail, not a budget)
REVIEW_TAIL_CAP_FRACTION = 0.5
# Assumed (OPEN): review_share = base * (OFFSET + maint_pressure)
REVIEW_PRESSURE_OFFSET = 0.5
DEFAULT_WEEKDAY_SHAPE = (1.0,) * 7
# Max minutes of tail chunks offered per "Keep going?" round (tunable).
TAIL_OFFER_MAX_MIN = Config.TAIL_OFFER_MAX_MIN

# Review-load governor levels
GOVERNOR_LEVELS = ('normal', 'reduced', 'paused')


# ============================================================================
# Pure helpers (numerical; pytest-friendly)
# ============================================================================

def _clamp(lo: float, x: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _clamp01(x: float) -> float:
    return _clamp(0.0, x, 1.0)


def weakness(skill_data: Dict[str, Any], ladder_stagnation: float,
             fsrs_lapse_rate: float, user_mean_elo: float) -> float:
    """Composite weakness signal for one test skill.

    skill_data shape (from compute_weekly_plan_load_signals.skills[<code>]):
        { elo, tests_taken, first_attempt_correct_28d, first_attempt_wrong_28d }

    Cold-start: when total first-attempt count over 28 days is < 5, returns
    COLD_START_WEAKNESS (0.50). The wide bandit prior (Beta(2,2)) then
    handles exploration.
    """
    n = (skill_data.get('first_attempt_correct_28d', 0)
         + skill_data.get('first_attempt_wrong_28d', 0))
    if n < COLD_START_MIN_ATTEMPTS:
        return COLD_START_WEAKNESS

    elo = skill_data.get('elo', 1200) or 1200
    elo_gap = _clamp01((user_mean_elo - elo) / ELO_GAP_SPAN)

    acc = skill_data['first_attempt_correct_28d'] / max(n, 1)
    accuracy_trend = _clamp01(ACC_TREND_TARGET - acc)

    return (W_ELO  * elo_gap
            + W_ACC  * accuracy_trend
            + W_LAD  * ladder_stagnation
            + W_FSRS * fsrs_lapse_rate)


def value(weakness_score: float, elo: float, override: float = 1.0) -> float:
    """value(s) = weakness · (1 − diminishing) · skill_weight_override."""
    diminishing = _clamp01((elo - DIM_ELO_FLOOR) / DIM_ELO_RANGE)
    return weakness_score * (1.0 - diminishing) * override


def bandit_score(value_s: float, alpha: float, beta: float, seed: int) -> float:
    """value(s) · (1 − accuracy_sample) with deterministic Beta sample.

    Single sample per (user, week, skill) tuple; seed determinism makes
    compute_weekly_plan idempotent (R3.8).
    """
    rng = np.random.default_rng(seed)
    acc_sample = float(rng.beta(alpha, beta))
    return value_s * (1.0 - acc_sample)


def make_seed(user_id: str, week_start: date, skill: str) -> int:
    """Deterministic 32-bit seed per (user, week, skill)."""
    h = hashlib.sha256(
        f'{user_id}|{week_start.isoformat()}|{skill}'.encode('utf-8')
    ).hexdigest()
    return int(h[:8], 16)   # 32 bits


def allocate_test_counts(
    weekly_counts_template: Dict[str, int],
    scores: Dict[str, float],
) -> Dict[str, int]:
    """Water-fill: proportional to bandit_score, clamped to template ±50%.

    Algorithm per [[algorithms/study-plan-adaptation.tech#4]]:
      1. Compute raw proportional shares.
      2. Round + clamp to [⌈t·0.5⌉, ⌈t·1.5⌉] per skill.
      3. Redistribute overflow/underflow to highest/lowest-scoring
         unsaturated skills.
    """
    skills = list(weekly_counts_template.keys())
    if not skills:
        return {}
    total = sum(weekly_counts_template.values())
    total_score = sum(scores.get(s, 0.0) for s in skills) or 1.0
    raw = {
        s: scores.get(s, 0.0) / total_score * total
        for s in skills
    }
    floors   = {s: math.ceil(weekly_counts_template[s] * 0.5) for s in skills}
    ceilings = {s: math.ceil(weekly_counts_template[s] * 1.5) for s in skills}
    counts = {
        s: max(floors[s], min(ceilings[s], round(raw[s])))
        for s in skills
    }
    diff = total - sum(counts.values())
    while diff != 0:
        if diff > 0:
            cand = [s for s in skills if counts[s] < ceilings[s]]
            if not cand:
                break
            target = max(cand, key=lambda s: scores.get(s, 0.0))
            counts[target] += 1
            diff -= 1
        else:
            cand = [s for s in skills if counts[s] > floors[s]]
            if not cand:
                break
            target = min(cand, key=lambda s: scores.get(s, 0.0))
            counts[target] -= 1
            diff += 1
    return counts


def rebalance_practice(
    daily_minutes: int,
    practice_total_minutes: int,
    flex_pct: float,
    base_maintenance_share: float,
    fsrs: Dict[str, int],
    bkt: Dict[str, int],
    weakness_global: float,
    cap_minutes: int,
) -> Tuple[int, int, float]:
    """Return (practice_minutes, review_minutes, review_share).

    Sizes the practice pool and the review share inside it (ADR-033 revision
    (b)). There is no acquisition pressure any more: new-word minutes are
    whatever of the pool the learner's quota needs, decided by the caller.

    ``practice_total_minutes`` is the template's ORIGINAL value (not the
    exclusion-adjusted one, which is 0 under tests_only), so tests_only can still
    size a weekly review tail target. ``cap_minutes`` is ``daily_minutes * 7``.
    """
    trr = target_review_rate(daily_minutes)
    known_words = max(bkt.get('known_count_p80', 0), 1)

    maint_pressure = (
        _clamp01(fsrs.get('due_7d_lookahead', 0) / max(trr * 7, 1))
        + 0.5 * _clamp01(bkt.get('decayed_count', 0) / known_words)
    )   # range 0..1.5

    review_share = _clamp(
        MAINT_SHARE_FLOOR,
        base_maintenance_share * (REVIEW_PRESSURE_OFFSET + maint_pressure),
        MAINT_SHARE_CEIL,
    )

    # +/- flex_pct from template based on global weakness
    flex_factor = 1.0 + flex_pct * (2.0 * weakness_global - 1.0)
    practice_minutes = round(practice_total_minutes * flex_factor)
    practice_minutes = int(_clamp(0, practice_minutes, cap_minutes))

    if practice_minutes <= 0:
        return 0, 0, round(review_share, 2)
    review_minutes = int(round(practice_minutes * review_share))
    return practice_minutes, review_minutes, round(review_share, 2)


# ----------------------------------------------------------------------------
# Module exclusions (session-modules.tech.md)
# ----------------------------------------------------------------------------

def apply_module_exclusions(
    weekly_counts: Dict[str, int],
    practice_total_minutes: int,
    excluded: Iterable[str],
    minutes_of: Callable[[str], float],
) -> Tuple[Dict[str, int], int]:
    """Drop excluded modules from the template and rescale the scalable rest.

    One common factor ``k`` preserves the template's total minutes and its
    relative mix. ``flashcards`` (NON_SCALABLE_MODULES) is never rescaled.
    Scalable counts use largest-remainder rounding with a deterministic
    (remainder desc, skill key asc) tie-break. Pure; no DB access.

    Returns ``(adjusted_weekly_counts, adjusted_practice_total_minutes)``.
    When nothing in ``excluded`` touches the template the inputs are returned
    unchanged (the same dict object), so the default plan is a strict no-op.
    """
    ex = set(excluded or ())
    if not ex.intersection(set(weekly_counts) | {MODULE_PRACTICE}):
        return weekly_counts, practice_total_minutes

    kept = {s: c for s, c in weekly_counts.items() if s not in ex}
    practice_kept = 0 if MODULE_PRACTICE in ex else practice_total_minutes

    m_total = (
        sum(c * minutes_of(s) for s, c in weekly_counts.items())
        + practice_total_minutes
    )
    fixed = {s: c for s, c in kept.items() if s in NON_SCALABLE_MODULES}
    scalable = {s: c for s, c in kept.items() if s not in NON_SCALABLE_MODULES}
    m_fixed = sum(c * minutes_of(s) for s, c in fixed.items())
    m_scalable = sum(c * minutes_of(s) for s, c in scalable.items()) + practice_kept

    if m_scalable == 0:
        # Only flashcards (or nothing) left: no redistribution.
        return dict(kept), 0

    k = (m_total - m_fixed) / m_scalable

    raw = {s: c * k for s, c in scalable.items()}
    floors = {s: int(math.floor(v + 1e-9)) for s, v in raw.items()}
    spare = int(round(sum(raw.values()))) - sum(floors.values())
    order = sorted(raw, key=lambda s: (-(raw[s] - floors[s]), s))
    counts = dict(floors)
    for s in order:
        if spare <= 0:
            break
        counts[s] += 1
        spare -= 1

    adjusted = {**fixed, **counts}
    # Preserve the template's key order for stable downstream iteration.
    adjusted = {s: adjusted[s] for s in weekly_counts if s in adjusted}
    return adjusted, int(round(practice_kept * k))


# ----------------------------------------------------------------------------
# New-word quota helpers (session-budget-settings.tech.md)
# ----------------------------------------------------------------------------

def new_words_for_day(new_words_per_day: int, weight: float) -> int:
    """The day's new-word quota Q for a weekday weight.

    ``floor(x + 0.5)``, NOT ``round()`` (banker's rounding would disagree with
    the SQL helper at .5 ties). Mirrors SQL ``public.new_words_for_day``;
    a test evaluates both on a grid.
    """
    if weight is None or weight <= 0 or new_words_per_day is None or new_words_per_day <= 0:
        return 0
    # Decimal, not float: SQL does this in exact numeric (25 * 0.58 + 0.5 = 15.0 there, but
    # 25 * 0.58 is 14.499999999999998 in binary floating point -> 14). str() gives the
    # shortest repr of the weight, i.e. the decimal literal the JSON/SQL side holds.
    x = Decimal(str(new_words_per_day)) * Decimal(str(weight)) + Decimal('0.5')
    return int(x.to_integral_value(rounding=ROUND_FLOOR))


def new_words_week_target(
    new_words_per_day: int, shape: Optional[Sequence[float]],
) -> int:
    """Weekly quota = sum of the 7 daily quotas under the plan's weekday shape."""
    weights = shape or DEFAULT_WEEKDAY_SHAPE
    return sum(new_words_for_day(new_words_per_day, float(w)) for w in weights)


def derived_shares(review_minutes: int, acq_minutes: int) -> Tuple[float, float]:
    """(maintenance_share, acquisition_share), persisted for observability only.

    maintenance = round(review / (review + acq), 2); acquisition = round(1 -
    maintenance, 2) so the pair always sums to 1.00 (relaxed shares CHECK).
    1.00 / 0.00 when there is nothing to split.
    """
    denom = review_minutes + acq_minutes
    if denom <= 0:
        return 1.0, 0.0
    maint = round(review_minutes / denom, 2)
    return maint, round(1.0 - maint, 2)


# ----------------------------------------------------------------------------
# Review-load governor and forecast (pure mirrors of the SQL helpers)
# ----------------------------------------------------------------------------

def review_governor_level(backlog_min: float, threshold_min: float) -> str:
    """'normal' | 'reduced' | 'paused'. Mirrors SQL ``review_governor_level``."""
    if threshold_min is None or threshold_min <= 0:
        return 'normal'
    if backlog_min <= threshold_min:
        return 'normal'
    if backlog_min <= 2 * threshold_min:
        return 'reduced'
    return 'paused'


def effective_new_words(quota: int, level: str) -> int:
    """quota | floor(quota / 2) | 0. Mirrors SQL ``new_words_effective``."""
    q = max(int(quota), 0)
    if level == 'paused':
        return 0
    if level == 'reduced':
        return q // 2
    return q


def review_forecast_min_per_day(
    avg_new_words_per_day: float, item_seconds: float,
) -> float:
    """Steady-state extra review minutes/day a month after introducing
    ``avg_new_words_per_day`` words a day.

    Each new word needs N = Config.REVIEWS_PER_NEW_WORD_30D reviews in its first
    30 days, spread evenly; 30 * n words are inside that window, each costing
    N / 30 reviews/day, so reviews/day = n * N (the 30 cancels; there is NO
    further division by 30). 5 words/day at 20 s -> 11.67 min/day. N = 7 and
    the steady-state reading are OPEN; ``item_seconds`` is a v1 estimate.
    """
    return (
        float(avg_new_words_per_day)
        * Config.REVIEWS_PER_NEW_WORD_30D
        * float(item_seconds)
        / 60.0
    )


def _empty_governor() -> Dict[str, Any]:
    return {
        'level': 'normal',
        'overdue_items': 0, 'overdue_minutes': 0.0,
        'due_items': 0, 'due_minutes': 0.0,
        'threshold_minutes': 0.0,
        'item_seconds': float(Config.REVIEW_ITEM_SECONDS_DEFAULT),
    }


def get_review_governor(
    db, user_id: str, language_id: int, plan_date,
) -> Dict[str, Any]:
    """Call RPC ``review_governor_state``; any failure -> level 'normal', zeros.

    Never raises. ``item_seconds`` falls back to the default (not 0) so callers
    that convert items to minutes stay meaningful.
    """
    result = _empty_governor()
    try:
        iso = plan_date.isoformat() if hasattr(plan_date, 'isoformat') else str(plan_date)
        resp = db.rpc('review_governor_state', {
            'p_user_id':     user_id,
            'p_language_id': language_id,
            'p_date':        iso,
        }).execute()
        data = resp.data
        if isinstance(data, list) and len(data) == 1:
            data = data[0]
        if not isinstance(data, dict):
            return result
        level = data.get('level')
        result['level'] = level if level in GOVERNOR_LEVELS else 'normal'
        for key in ('overdue_items', 'due_items'):
            result[key] = int(data.get(key) or 0)
        for key in ('overdue_minutes', 'due_minutes', 'threshold_minutes'):
            result[key] = float(data.get(key) or 0.0)
        item_seconds = float(data.get('item_seconds') or 0.0)
        if item_seconds > 0:
            result['item_seconds'] = item_seconds
        return result
    except Exception as exc:
        logger.warning(
            'review_governor_state failed for user=%s lang=%s: %s',
            user_id, language_id, exc,
        )
        return _empty_governor()


def get_minutes_per_new_word(db, language_id: int) -> float:
    """dim_languages.new_word_minutes_est, else Config.NEW_WORD_MINUTES_DEFAULT.

    Mirror of SQL ``public.new_word_minutes``. Missing row, NULL, non-positive,
    non-finite value or a failed read all fall back to the default.
    """
    try:
        resp = (
            db.table('dim_languages')
            .select('new_word_minutes_est')
            .eq('id', language_id)
            .limit(1)
            .execute()
        )
        if resp.data:
            raw = resp.data[0].get('new_word_minutes_est')
            if raw is not None:
                val = float(raw)
                if math.isfinite(val) and val > 0:
                    return val
    except Exception as exc:
        logger.debug('get_minutes_per_new_word read failed: %s', exc)
    return float(Config.NEW_WORD_MINUTES_DEFAULT)


def _test_time_estimate(skill: str, db) -> float:
    """Minutes per budgeted slot of ``skill``, preferring the observed P50.

    Python mirror of the SQL ``public.test_time_estimate``. The two MUST agree:
    this one sizes ``total_weekly_minutes`` at Tier B, the SQL one sizes the
    daily greedy fill at Tier C, and a divergence shows up as a week that never
    fits its own days.

    Unknown skills fall back to 5 minutes — the same catch-all ADR-021 flags as
    a silent wrong answer. We keep the fallback (a plan must still solve) but
    WARN, so a newly planned surface nobody seeded is visible in the logs rather
    than quietly budgeted at 5 minutes forever.
    """
    try:
        resp = (
            db.table('dim_test_types')
            .select('expected_minutes_p50')
            .eq('type_code', skill)
            .limit(1)
            .execute()
        )
        if resp.data:
            p50 = resp.data[0].get('expected_minutes_p50')
            if p50 is not None:
                return float(p50)
    except Exception:
        pass

    seeded = Config.TEST_TYPE_MINUTES.get(skill)
    if seeded is None:
        logger.warning(
            'test_time_estimate: no seeded minutes for skill=%r; budgeting at '
            '%s min/slot. Seed it in Config.TEST_TYPE_MINUTES *and* the SQL '
            'test_time_estimate CASE (ADR-021).',
            skill, UNSEEDED_SKILL_MINUTES,
        )
        return float(UNSEEDED_SKILL_MINUTES)
    return float(seeded)


# ============================================================================
# Tier B orchestration
# ============================================================================

class StudyPlanService:
    """Tier B adapter + Tier C wrapper + cron entry point."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()
        # Stage code of the last compute_weekly_plan failure (None on success).
        # Lets callers report WHICH step failed without exposing exception text.
        self.last_failure: Optional[str] = None

    # ------------------------------------------------------------------
    # Public: compute_weekly_plan
    # ------------------------------------------------------------------

    def compute_weekly_plan(
        self,
        user_id: str,
        language_id: int,
        week_start: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """Recompute the (user, language, week) plan and persist.

        Returns the persisted weekly_plan_states row as a dict, or None on
        error (logged). Idempotent: same DB state + same week_start →
        same target_counts thanks to deterministic Beta seeding.
        """
        self.last_failure = None
        if not Config.STUDY_PLAN_ENABLED:
            self.last_failure = 'disabled'
            return None

        week_start = week_start or _monday_of(date.today())

        # 1. Load plan
        plan_resp = (
            self.db.table('user_study_plans')
            .select(
                'template_id, daily_minutes, skill_weight_overrides, '
                'weekday_shape, excluded_modules, budget_scope, new_words_per_day'
            )
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .limit(1)
            .execute()
        )
        if not plan_resp.data:
            logger.debug('no user_study_plan for user=%s lang=%s', user_id, language_id)
            self.last_failure = 'no_plan'
            return None
        plan = plan_resp.data[0]

        # 2. Load template (for weekly_test_counts shape + flex + base_maint)
        template_resp = (
            self.db.table('dim_study_plan_templates')
            .select(
                'template_id, daily_minutes, weekly_test_counts, '
                'practice_total_minutes, base_maintenance_share, '
                'practice_minutes_flex_pct'
            )
            .eq('template_id', plan['template_id'])
            .limit(1)
            .execute()
        )
        # .limit(1) (not .single(), which RAISES on 0/duplicate rows) so a
        # missing/dangling template_id is handled gracefully, not thrown.
        if not template_resp.data:
            logger.error('template_id=%s not found for user=%s', plan['template_id'], user_id)
            self.last_failure = 'template_missing'
            return None
        template = template_resp.data[0]

        # 3. Load signals
        try:
            signals_resp = self.db.rpc('compute_weekly_plan_load_signals', {
                'p_user_id':     user_id,
                'p_language_id': language_id,
                'p_week_start':  week_start.isoformat(),
            }).execute()
            signals = signals_resp.data
        except Exception as e:
            logger.error('load_signals failed for user=%s lang=%s: %s', user_id, language_id, e)
            self.last_failure = 'load_signals_failed'
            return None
        if not isinstance(signals, dict):
            logger.error('load_signals returned non-dict: %r', signals)
            self.last_failure = 'load_signals_invalid'
            return None

        # 4. Compute weakness per skill, then value
        overrides = plan.get('skill_weight_overrides') or {}
        user_mean = float(signals.get('user_mean_elo', 1200))
        ladder = signals.get('ladder', {}) or {}
        subscribed = max(int(ladder.get('subscribed', 0)), 1)
        ladder_stagnation = _clamp01(int(ladder.get('stagnant_14d', 0)) / subscribed)
        fsrs = signals.get('fsrs', {}) or {}
        reviews_28d = max(int(fsrs.get('reviews_28d', 0)), 1)
        fsrs_lapse_rate = _clamp01(int(fsrs.get('lapses_28d', 0)) / reviews_28d)
        bkt = signals.get('bkt', {}) or {}

        skills_signals = signals.get('skills', {}) or {}

        # 4a. Module exclusions + budget scope (ADR-032 / ADR-033).
        daily_minutes = int(plan['daily_minutes'])
        weekly_ceiling = daily_minutes * 7
        excluded = {m for m in (plan.get('excluded_modules') or []) if isinstance(m, str)}
        scope = plan.get('budget_scope')
        if scope not in BUDGET_SCOPES:
            scope = DEFAULT_BUDGET_SCOPE
        practice_in = (scope == 'tests_and_review' and MODULE_PRACTICE not in excluded)
        # tests_only: the vocabulary pool leaves the in-budget plan, so its
        # template minutes go to tests/surfaces exactly like an exclusion.
        eff_excluded = set(excluded)
        if scope == 'tests_only':
            eff_excluded.add(MODULE_PRACTICE)

        minutes_cache: Dict[str, float] = {}

        def minutes_of(skill: str) -> float:
            if skill not in minutes_cache:
                minutes_cache[skill] = _test_time_estimate(skill, self.db)
            return minutes_cache[skill]

        weekly_template, _discarded_practice = apply_module_exclusions(
            template['weekly_test_counts'],
            int(template['practice_total_minutes']),
            eff_excluded,
            minutes_of,
        )

        skill_weakness: Dict[str, float] = {}
        skill_values: Dict[str, float] = {}
        for skill in weekly_template.keys():
            sdata = skills_signals.get(skill, {
                'elo': 1200, 'first_attempt_correct_28d': 0, 'first_attempt_wrong_28d': 0,
            })
            w = weakness(sdata, ladder_stagnation, fsrs_lapse_rate, user_mean)
            v = value(w, float(sdata.get('elo', 1200) or 1200),
                      float(overrides.get(skill, 1.0)))
            skill_weakness[skill] = w
            skill_values[skill]   = round(v, 6)

        # 5. Bandit allocation
        scores = {
            s: bandit_score(
                skill_values[s],
                BETA_PRIOR_ALPHA + skills_signals.get(s, {}).get('first_attempt_correct_28d', 0),
                BETA_PRIOR_BETA  + skills_signals.get(s, {}).get('first_attempt_wrong_28d', 0),
                make_seed(user_id, week_start, s),
            )
            for s in weekly_template.keys()
        }
        target_counts = allocate_test_counts(weekly_template, scores)

        # 6. Practice pool + review share. Skipped when the learner turned
        # Vocabulary review off. The ORIGINAL template minutes are used: under
        # tests_only the review target is still sized (as a weekly tail target).
        weakness_global = (
            sum(skill_weakness.values()) / len(skill_weakness)
            if skill_weakness else 0.5
        )
        prior_week = signals.get('prior_week')
        if MODULE_PRACTICE in excluded:
            practice_pool = 0
            review = 0
        else:
            practice_pool, review, _review_share = rebalance_practice(
                daily_minutes=daily_minutes,
                practice_total_minutes=int(template['practice_total_minutes']),
                flex_pct=float(template['practice_minutes_flex_pct']),
                base_maintenance_share=float(template['base_maintenance_share']),
                fsrs=fsrs, bkt=bkt,
                weakness_global=weakness_global,
                cap_minutes=weekly_ceiling,
            )
            review_cap = (
                weekly_ceiling if scope == 'tests_and_review'
                else int(math.floor(weekly_ceiling * REVIEW_TAIL_CAP_FRACTION))
            )
            # Review carry-over. New-word minutes are NOT carried: they are a
            # daily quota and an unmet quota is a shortfall, not a debt.
            if prior_week:
                left = max(
                    0,
                    int(prior_week.get('review_target_minutes', 0) or 0)
                    - int(prior_week.get('practice_completed_maint_min', 0) or 0),
                )
                review = review + round(CARRY_OVER_DECAY * left)
            review = min(review, review_cap)

        # 5b. New words (a count, converted to minutes by the per-language cost).
        mpnw = get_minutes_per_new_word(self.db, language_id)
        new_words_target = new_words_week_target(
            int(plan.get('new_words_per_day') or 0), plan.get('weekday_shape'),
        )
        acq_quota_min = int(round(new_words_target * mpnw))

        # 6b. In-budget practice pool P and its new-word minutes.
        if practice_in:
            practice_target = int(min(max(practice_pool, review), weekly_ceiling))
            acq_target_minutes = int(max(0, min(acq_quota_min, practice_target - review)))
        else:
            practice_target = 0
            acq_target_minutes = 0

        # 7. Test carry-over decay (iterates target_counts, so excluded skills
        # get none). No scale-up: tests are not rescaled to absorb freed minutes.
        if prior_week:
            prev_targets   = prior_week.get('target_counts', {}) or {}
            prev_completed = prior_week.get('completed_counts', {}) or {}
            for s in list(target_counts.keys()):
                remaining = max(
                    0,
                    int(prev_targets.get(s, 0)) - int(prev_completed.get(s, 0)),
                )
                if remaining > 0:
                    target_counts[s] += round(CARRY_OVER_DECAY * remaining)

        # 8. Total weekly minutes (the in-budget total)
        test_minutes = sum(
            target_counts[s] * minutes_of(s)
            for s in target_counts
        )
        total_weekly_minutes = int(round(test_minutes + practice_target))

        # TASK-714 / ADR-021: cap the week at what the learner actually
        # committed to. Bringing flashcards and dual_translation into
        # target_counts adds real minutes to the sum above -- but the learner
        # was already spending those minutes, unseen. Without this clamp,
        # counting them would LENGTHEN their day (today_budget derives from
        # total_weekly_minutes) instead of making the existing day honest.
        # With it, the new surfaces compete with test slots inside the same
        # budget, which is exactly what ADR-021 means by "dual_translation
        # competes directly with test time".
        total_weekly_minutes = min(total_weekly_minutes, weekly_ceiling)

        # 9. Persist. maintenance/acquisition shares are DERIVED, observability only.
        maint_share, acq_share = derived_shares(review, acq_target_minutes)
        computed = {
            'target_counts':           target_counts,
            'skill_values':            skill_values,
            'practice_target_minutes': int(practice_target),
            'maintenance_share':       float(maint_share),
            'acquisition_share':       float(acq_share),
            'total_weekly_minutes':    total_weekly_minutes,
            'budget_scope':            scope,
            'review_target_minutes':   int(review),
            'new_words_target':        int(new_words_target),
            'acq_target_minutes':      int(acq_target_minutes),
        }
        try:
            persist_resp = self.db.rpc('compute_weekly_plan_persist', {
                'p_user_id':     user_id,
                'p_language_id': language_id,
                'p_week_start':  week_start.isoformat(),
                'p_computed':    computed,
            }).execute()
        except Exception as e:
            logger.error(
                'persist failed for user=%s lang=%s week=%s: %s',
                user_id, language_id, week_start, e,
            )
            self.last_failure = 'persist_failed'
            return None

        logger.info(
            'compute_weekly_plan: user=%s lang=%s week=%s scope=%s counts=%s '
            'practice=%dmin review=%dmin acq=%dmin new_words=%d (M:%.2f A:%.2f)',
            user_id, language_id, week_start, scope,
            target_counts, practice_target, review, acq_target_minutes,
            new_words_target, maint_share, acq_share,
        )
        return persist_resp.data if isinstance(persist_resp.data, dict) else computed

    # ------------------------------------------------------------------
    # Public: build_daily_session (thin RPC wrapper)
    # ------------------------------------------------------------------

    def build_daily_session(
        self,
        user_id: str,
        language_id: int,
        target_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Wrap the build_daily_session RPC with logging + error shape.

        Returns the RPC jsonb verbatim. Errors with codes E_NOPLAN or
        E_NOWEEK indicate the caller should fall back to legacy daily-load.

        ``target_date`` defaults to the learner's LOCAL date (ADR-022), not
        ``date.today()`` — the old default was the process's local date, a
        third independent derivation of "today" on top of the two UTC ones.
        Callers that already resolved the local date should pass it, so a
        single request never derives it twice.
        """
        target_date = target_date or plan_today(self.db, user_id, language_id)
        try:
            resp = self.db.rpc('build_daily_session', {
                'p_user_id':     user_id,
                'p_language_id': language_id,
                'p_date':        target_date.isoformat(),
            }).execute()
        except Exception as e:
            logger.error(
                'build_daily_session RPC failed for user=%s lang=%s date=%s: %s',
                user_id, language_id, target_date, e,
            )
            return {'error': 'rpc_failed', 'code': 'E_RPC', 'detail': str(e)}
        return resp.data if isinstance(resp.data, dict) else {
            'error': 'malformed_response', 'code': 'E_SHAPE',
        }

    # ------------------------------------------------------------------
    # Public: rebuild_today (settings change -> re-resolve today)
    # ------------------------------------------------------------------

    def rebuild_today(self, user_id: str, language_id: int) -> bool:
        """Re-resolve today's not-yet-completed slots after a settings change.

        If a ``daily_test_loads`` row exists for the learner's LOCAL today, call
        ``build_daily_session`` for it (TASK-705 re-entrancy keeps completed
        slots) and return True unless the result carries an ``error``. With no
        row, return False: the next ``GET /api/study-session`` builds a fresh
        day anyway. Never raises.
        """
        try:
            local_today = plan_today(self.db, user_id, language_id)
            resp = (
                self.db.table('daily_test_loads')
                .select('load_date')
                .eq('user_id', user_id)
                .eq('language_id', language_id)
                .eq('load_date', local_today.isoformat())
                .limit(1)
                .execute()
            )
            if not resp.data:
                return False
            result = self.build_daily_session(user_id, language_id, local_today)
        except Exception as exc:
            logger.warning(
                'rebuild_today failed for user=%s lang=%s: %s',
                user_id, language_id, exc,
            )
            return False
        return not (isinstance(result, dict) and 'error' in result)


def typical_day_inputs(db, language_id: int, plan: Dict[str, Any],
                       week: Dict[str, Any]) -> Dict[str, float]:
    """The two numbers of a typical day that do NOT depend on the new-words input.

    Lets the settings card preview any ``new_words_per_day`` client-side. ``week``
    is a ``weekly_plan_states`` row. Returns
    ``{practice_room_min_per_day, review_min_per_day}``::

        test_min     = sum(week.target_counts[s] * minutes_of(s))
        practice_day = (total_weekly_minutes / 7) * P / (P + test_min)   (P > 0)
        review_min_per_day        = review_target_minutes / 7
        practice_room_min_per_day = max(0, practice_day - review_min_per_day)  (P > 0, else 0)
    """
    cache: Dict[str, float] = {}

    def minutes_of(skill: str) -> float:
        if skill not in cache:
            cache[skill] = _test_time_estimate(skill, db)
        return cache[skill]

    counts = week.get('target_counts') or {}
    test_min = sum(int(c) * minutes_of(s) for s, c in counts.items())
    pool = float(week.get('practice_target_minutes') or 0)
    total = float(week.get('total_weekly_minutes') or 0)
    review_per_day = float(week.get('review_target_minutes') or 0) / 7.0

    if pool > 0 and (pool + test_min) > 0:
        practice_day = (total / 7.0) * pool / (pool + test_min)
        room = max(0.0, practice_day - review_per_day)
    else:
        room = 0.0
    return {
        'practice_room_min_per_day': room,
        'review_min_per_day':        review_per_day,
    }


# ============================================================================
# Cron entry point (registered in app.py)
# ============================================================================

def _try_advisory_lock(db) -> bool:
    """Best-effort cross-worker mutex for the weekly recompute. Wraps the
    Study-Plan advisory-lock key server-side (key 'StPP', see
    migrations/study_plan_advisory_lock.sql). Same shape as the IRT
    calibrator's _try_advisory_lock. Falls through to True if the RPC is
    unavailable (e.g. not yet deployed) so a misconfigured environment still
    runs — Tier B UPSERTs are idempotent, the only cost is ~2× compute.
    """
    try:
        resp = db.rpc('pg_try_advisory_lock_for_study_plan', {}).execute()
        data = resp.data
        if isinstance(data, list) and data:
            return bool(data[0])
        if data is not None:
            return bool(data)
    except Exception as exc:
        logger.warning(
            'Study-plan advisory lock unavailable, proceeding without it: %s', exc,
        )
    return True


def _release_advisory_lock(db) -> None:
    try:
        db.rpc('pg_advisory_unlock_for_study_plan', {}).execute()
    except Exception as exc:
        logger.warning('Study-plan advisory unlock failed: %s', exc)


def _run_weekly_plan_recompute(min_users: int = 0) -> Dict[str, Any]:
    """APScheduler entry point — fired Sundays at 23:00 UTC.

    Iterates every user_study_plans row; calls compute_weekly_plan per row;
    aggregates a summary. Per-row errors are logged and the loop continues.

    Returns: { fired, succeeded, failed, week_start }
    """
    db = get_supabase_admin()
    svc = StudyPlanService(db=db)
    # Fired Sunday 23:00 UTC (app.py CronTrigger). Seed the *upcoming* week,
    # not the outgoing one: today+1 lands on Monday of next week, so a fresh
    # Monday-morning request finds a weekly_plan_states row already present and
    # never has to fall back to the lazy compute / legacy 3-test load.
    week_start = _monday_of(date.today() + timedelta(days=1))

    # Cross-worker mutex (F7): APScheduler runs in every gunicorn worker, but
    # only the one that takes the advisory lock runs the sweep. The rest skip.
    # The recompute is idempotent, so this is purely to avoid N× DB load.
    if not _try_advisory_lock(db):
        logger.info(
            'Another worker holds the study-plan recompute lock; skipping (week=%s).',
            week_start,
        )
        return {
            'week_start': week_start.isoformat(),
            'fired':      0,
            'succeeded':  0,
            'failed':     0,
            'skipped':    True,
        }

    # Pull plans in pages to avoid loading 100K+ rows at once.
    page_size = 1000
    offset = 0
    fired = 0
    succeeded = 0
    failed = 0

    try:
        while True:
            resp = (
                db.table('user_study_plans')
                .select('user_id, language_id')
                .range(offset, offset + page_size - 1)
                .execute()
            )
            rows = resp.data or []
            if not rows:
                break
            for row in rows:
                fired += 1
                try:
                    result = svc.compute_weekly_plan(
                        row['user_id'], int(row['language_id']), week_start,
                    )
                    if result is not None:
                        succeeded += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    logger.exception(
                        'compute_weekly_plan crashed for user=%s lang=%s: %s',
                        row.get('user_id'), row.get('language_id'), e,
                    )
            offset += page_size
            if len(rows) < page_size:
                break
    finally:
        _release_advisory_lock(db)

    logger.info(
        '_run_weekly_plan_recompute complete: week=%s fired=%d succeeded=%d failed=%d',
        week_start, fired, succeeded, failed,
    )
    return {
        'week_start': week_start.isoformat(),
        'fired':      fired,
        'succeeded':  succeeded,
        'failed':     failed,
        'skipped':    False,
    }


def _refresh_exercise_time_estimates() -> Dict[str, Any]:
    """APScheduler entry point — fired daily at 04:05 UTC.

    Delegates to refresh_practice_time_estimates RPC
    (migrations/phase13_refresh_practice_time_estimates.sql) which atomically
    updates both:
      - dim_exercise_types.expected_seconds_p50 (from exercise_attempts.time_taken_ms)
      - dim_test_types.expected_minutes_p50    (from test_attempts.duration_ms)
    over the last 30 days, requiring ≥30 samples per type.

    Then (TASK-870) calls refresh_new_word_minutes, which writes
    dim_languages.new_word_minutes_est, and merges ``languages_updated`` into
    the summary.

    Returns the RPC's jsonb summary as a Python dict, or an error dict on
    failure (logged).
    """
    db = get_supabase_admin()
    try:
        resp = db.rpc('refresh_practice_time_estimates', {}).execute()
        summary = resp.data if isinstance(resp.data, dict) else {}
        logger.info(
            '_refresh_exercise_time_estimates: %d exercise types, %d test types updated',
            summary.get('exercise_types_updated', 0),
            summary.get('test_types_updated', 0),
        )
    except Exception as e:
        logger.error('refresh_practice_time_estimates RPC failed: %s', e)
        return {'error': str(e), 'exercise_types_updated': 0, 'test_types_updated': 0}

    # TASK-870: per-language minutes-per-new-word, AFTER the exercise-type P50s
    # are fresh (the RPC reads dim_exercise_types.expected_seconds_p50). Its
    # failure must not turn a successful time-estimate refresh into an error.
    try:
        nw = db.rpc('refresh_new_word_minutes', {}).execute()
        nw_data = nw.data if isinstance(nw.data, dict) else {}
        summary['languages_updated'] = int(nw_data.get('languages_updated', 0) or 0)
        logger.info(
            '_refresh_exercise_time_estimates: %d languages new_word_minutes_est updated',
            summary['languages_updated'],
        )
    except Exception as e:
        logger.error('refresh_new_word_minutes RPC failed: %s', e)
        summary['languages_updated'] = 0
        summary['new_word_minutes_error'] = str(e)
    return summary


# ============================================================================
# Date helpers
# ============================================================================

def _monday_of(d: date) -> date:
    """Return the Monday of d's ISO week (Mon=0..Sun=6)."""
    return d - timedelta(days=d.weekday())
