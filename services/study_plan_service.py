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
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import Config
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
    ladder: Dict[str, int],
    fsrs: Dict[str, int],
    bkt: Dict[str, int],
    weakness_global: float,
) -> Tuple[int, float, float]:
    """Return (practice_minutes, maint_share, acq_share).

    Inputs are the relevant slices from compute_weekly_plan_load_signals.
    Math mirrors Section 6e exactly.
    """
    trr = target_review_rate(daily_minutes)
    tap = target_active_pool(daily_minutes)
    tnr = target_new_rate(daily_minutes)
    known_words = max(bkt.get('known_count_p80', 0), 1)

    maint_pressure = (
        _clamp01(fsrs.get('due_7d_lookahead', 0) / max(trr * 7, 1))
        + 0.5 * _clamp01(bkt.get('decayed_count', 0) / known_words)
    )
    acq_pressure = (
        _clamp01(ladder.get('stuck_count', 0) / max(tap, 1))
        + 0.3 * _clamp01(ladder.get('new_intro_7d', 0) / max(tnr, 1))
    )

    psum = maint_pressure + acq_pressure
    if psum == 0:
        acq_share = 1.0 - base_maintenance_share
    else:
        raw_ratio = acq_pressure / psum
        acq_share = _clamp(ACQ_SHARE_FLOOR, raw_ratio, ACQ_SHARE_CEIL)
    maint_share = 1.0 - acq_share

    # ±flex_pct from template based on global weakness
    flex_factor = 1.0 + flex_pct * (2.0 * weakness_global - 1.0)
    practice_minutes = round(practice_total_minutes * flex_factor)
    practice_minutes = min(practice_minutes, daily_minutes * 7)
    practice_minutes = max(practice_minutes, 0)

    return practice_minutes, round(maint_share, 2), round(acq_share, 2)


def _test_time_estimate(skill: str, db) -> float:
    """Minutes-per-test for the given skill, preferring observed P50."""
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
    return float(Config.TEST_TYPE_MINUTES.get(skill, 5))


# ============================================================================
# Tier B orchestration
# ============================================================================

class StudyPlanService:
    """Tier B adapter + Tier C wrapper + cron entry point."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()

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
        if not Config.STUDY_PLAN_ENABLED:
            return None

        week_start = week_start or _monday_of(date.today())

        # 1. Load plan
        plan_resp = (
            self.db.table('user_study_plans')
            .select('template_id, daily_minutes, skill_weight_overrides')
            .eq('user_id', user_id)
            .eq('language_id', language_id)
            .limit(1)
            .execute()
        )
        if not plan_resp.data:
            logger.debug('no user_study_plan for user=%s lang=%s', user_id, language_id)
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
            return None
        if not isinstance(signals, dict):
            logger.error('load_signals returned non-dict: %r', signals)
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
        weekly_template = template['weekly_test_counts']

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

        # 6. Practice rebalance
        weakness_global = (
            sum(skill_weakness.values()) / len(skill_weakness)
            if skill_weakness else 0.5
        )
        practice_minutes, maint_share, acq_share = rebalance_practice(
            daily_minutes=int(plan['daily_minutes']),
            practice_total_minutes=int(template['practice_total_minutes']),
            flex_pct=float(template['practice_minutes_flex_pct']),
            base_maintenance_share=float(template['base_maintenance_share']),
            ladder=ladder, fsrs=fsrs, bkt=bkt,
            weakness_global=weakness_global,
        )

        # 7. Carry-over decay
        prior_week = signals.get('prior_week')
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
            prev_practice_left = max(
                0,
                int(prior_week.get('practice_target_minutes', 0))
                - int(prior_week.get('practice_completed_maint_min', 0))
                - int(prior_week.get('practice_completed_acq_min',   0)),
            )
            if prev_practice_left > 0:
                practice_minutes += round(CARRY_OVER_DECAY * prev_practice_left)
                practice_minutes = min(
                    practice_minutes,
                    int(plan['daily_minutes']) * 7,
                )

        # 8. Total weekly minutes
        test_minutes = sum(
            target_counts[s] * _test_time_estimate(s, self.db)
            for s in target_counts
        )
        total_weekly_minutes = int(round(test_minutes + practice_minutes))

        # 9. Persist
        computed = {
            'target_counts':           target_counts,
            'skill_values':            skill_values,
            'practice_target_minutes': int(practice_minutes),
            'maintenance_share':       float(maint_share),
            'acquisition_share':       float(acq_share),
            'total_weekly_minutes':    total_weekly_minutes,
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
            return None

        logger.info(
            'compute_weekly_plan: user=%s lang=%s week=%s counts=%s practice=%dmin (M:%.2f A:%.2f)',
            user_id, language_id, week_start,
            target_counts, practice_minutes, maint_share, acq_share,
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
        """
        target_date = target_date or date.today()
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


# ============================================================================
# Cron entry point (registered in app.py)
# ============================================================================

_ADVISORY_LOCK_KEY = 0x577D7950  # 'StPP' — Study Plan Pacer

def _try_advisory_lock(db) -> bool:
    try:
        resp = db.rpc('irt_try_lock').execute()  # reuse generic try-lock? no
    except Exception:
        pass
    # Use a Study-Plan-specific advisory lock via raw SQL
    try:
        resp = db.rpc('pg_try_advisory_lock_for_study_plan').execute()
        if resp.data is not None:
            return bool(resp.data)
    except Exception:
        pass
    # Fallback: skip the lock and just run — Tier B is idempotent so
    # double-runs produce the same UPSERT result. Cost is ~2× compute.
    return True


def _release_advisory_lock(db) -> None:
    try:
        db.rpc('pg_advisory_unlock_for_study_plan').execute()
    except Exception:
        pass


def _run_weekly_plan_recompute(min_users: int = 0) -> Dict[str, Any]:
    """APScheduler entry point — fired Sundays at 23:00 UTC.

    Iterates every user_study_plans row; calls compute_weekly_plan per row;
    aggregates a summary. Per-row errors are logged and the loop continues.

    Returns: { fired, succeeded, failed, week_start }
    """
    db = get_supabase_admin()
    svc = StudyPlanService(db=db)
    week_start = _monday_of(date.today())

    # Pull plans in pages to avoid loading 100K+ rows at once.
    page_size = 1000
    offset = 0
    fired = 0
    succeeded = 0
    failed = 0

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

    logger.info(
        '_run_weekly_plan_recompute complete: week=%s fired=%d succeeded=%d failed=%d',
        week_start, fired, succeeded, failed,
    )
    return {
        'week_start': week_start.isoformat(),
        'fired':      fired,
        'succeeded':  succeeded,
        'failed':     failed,
    }


def _refresh_exercise_time_estimates() -> Dict[str, Any]:
    """APScheduler entry point — fired daily at 04:05 UTC.

    Delegates to refresh_practice_time_estimates RPC
    (migrations/phase13_refresh_practice_time_estimates.sql) which atomically
    updates both:
      - dim_exercise_types.expected_seconds_p50 (from exercise_attempts.time_taken_ms)
      - dim_test_types.expected_minutes_p50    (from test_attempts.duration_ms)
    over the last 30 days, requiring ≥30 samples per type.

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
        return summary
    except Exception as e:
        logger.error('refresh_practice_time_estimates RPC failed: %s', e)
        return {'error': str(e), 'exercise_types_updated': 0, 'test_types_updated': 0}


# ============================================================================
# Date helpers
# ============================================================================

def _monday_of(d: date) -> date:
    """Return the Monday of d's ISO week (Mon=0..Sun=6)."""
    return d - timedelta(days=d.weekday())
