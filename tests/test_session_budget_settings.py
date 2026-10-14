"""Session budget settings (ADR-033): Tier B quota model, governor, forecast.

Spec: wiki/features/session-budget-settings.tech.md (Testing Strategy, Worked
Example), wiki/tasklist/session-budget-settings.tasks.md TASK-870 / TASK-874.
"""

import math
import re
from fractions import Fraction
from datetime import date
from pathlib import Path

import pytest

from config import Config
from services import study_plan_service as sps
from services.study_plan_service import (
    BUDGET_SCOPES,
    DEFAULT_WEEKDAY_SHAPE,
    StudyPlanService,
    allocate_test_counts,
    bandit_score,
    derived_shares,
    effective_new_words,
    get_minutes_per_new_word,
    get_review_governor,
    make_seed,
    new_words_for_day,
    new_words_week_target,
    rebalance_practice,
    review_forecast_min_per_day,
    review_governor_level,
    typical_day_inputs,
    value,
)
from tests._study_plan_fakes import (
    ZH30_MINUTES,
    ZH30_PRACTICE_TOTAL,
    ZH30_WEEKLY_COUNTS,
    FakeDb,
    zh30_db,
)

REPO = Path(__file__).resolve().parents[1]
MIG = REPO / 'migrations'
WEEK = date(2026, 10, 12)       # a Monday


def _sql(name):
    return (MIG / name).read_text(encoding='utf-8')


def _compute(**kw):
    db = zh30_db(**kw)
    out = StudyPlanService(db=db).compute_weekly_plan('u1', 1, WEEK)
    assert out is not None
    return db.persisted(), db


# ---------------------------------------------------------------------------
# new_words_for_day / new_words_week_target
# ---------------------------------------------------------------------------

class TestNewWordsForDay:
    def test_half_ties_round_up_not_bankers(self):
        assert new_words_for_day(5, 1.1) == 6      # 5.5 -> 6 (round() gives 6 too, via even)
        assert new_words_for_day(1, 0.5) == 1      # 0.5 -> 1 (round(0.5) == 0)
        assert new_words_for_day(5, 0.5) == 3      # 2.5 -> 3 (round(2.5) == 2)
        assert new_words_for_day(3, 0.5) == 2      # 1.5 -> 2

    def test_zero_cases(self):
        assert new_words_for_day(5, 0) == 0
        assert new_words_for_day(5, -1.0) == 0
        assert new_words_for_day(0, 1.4) == 0
        assert new_words_for_day(-3, 1.0) == 0
        assert new_words_for_day(5, None) == 0

    def test_default_shape_is_identity(self):
        assert new_words_for_day(5, 1.0) == 5
        assert DEFAULT_WEEKDAY_SHAPE == (1.0,) * 7

    def test_returns_int(self):
        assert isinstance(new_words_for_day(5, 1.4), int)

    def test_python_matches_sql_formula_on_grid(self):
        """The SQL helper is FLOOR(npd * w + 0.5); evaluate that exact form here."""
        sql = _sql('session_module_exclusions.sql')
        assert re.search(r'FLOOR\(\s*p_new_words_per_day\s*\*\s*p_weight\s*\+\s*0\.5\s*\)', sql)
        assert re.search(r'p_weight\s+IS\s+NULL\s+OR\s+p_weight\s*<=\s*0\s+OR\s+p_new_words_per_day\s*<=\s*0', sql)
        for npd in range(0, 51):
            for w in (0, 0.25, 0.5, 0.7, 1.0, 1.1, 1.4, 1.75, 2.0):
                # exact decimal arithmetic, like SQL numeric (binary floats disagree at ties)
                x = Fraction(npd) * Fraction(str(w)) + Fraction(1, 2)
                expect = 0 if (w <= 0 or npd <= 0) else x.numerator // x.denominator
                assert new_words_for_day(npd, w) == expect


class TestNewWordsWeekTarget:
    def test_all_ones_is_seven_times(self):
        for npd in (0, 1, 5, 50):
            assert new_words_week_target(npd, DEFAULT_WEEKDAY_SHAPE) == 7 * npd

    def test_none_or_empty_shape_uses_default(self):
        assert new_words_week_target(5, None) == 35
        assert new_words_week_target(5, []) == 35

    def test_five_day_shape_keeps_weekly_total(self):
        assert new_words_week_target(5, [1.4] * 5 + [0, 0]) == 35

    def test_rest_days_give_zero(self):
        assert new_words_week_target(5, [1, 1, 1, 1, 1, 0, 0]) == 25


# ---------------------------------------------------------------------------
# rebalance_practice
# ---------------------------------------------------------------------------

def _rp(**over):
    args = dict(
        daily_minutes=30, practice_total_minutes=90, flex_pct=0.2,
        base_maintenance_share=0.30, fsrs={}, bkt={'known_count_p80': 10},
        weakness_global=0.5, cap_minutes=210,
    )
    args.update(over)
    return rebalance_practice(**args)


class TestRebalancePractice:
    def test_worked_example_review_share(self):
        p, review, share = _rp(bkt={'known_count_p80': 10, 'decayed_count': 10})
        assert (p, review, share) == (90, 27, 0.30)

    def test_review_share_clamps_low(self):
        # no pressure: 0.30 * 0.5 = 0.15 -> exactly the floor; base 0.1 goes below it
        _, _, share = _rp(base_maintenance_share=0.10)
        assert share == 0.15

    def test_review_share_clamps_high(self):
        p, review, share = _rp(
            fsrs={'due_7d_lookahead': 10_000},
            bkt={'known_count_p80': 1, 'decayed_count': 99},
            base_maintenance_share=0.9,
        )
        assert share == 0.50
        assert review == round(p * 0.5)

    def test_practice_clamped_to_cap(self):
        p, review, _ = _rp(practice_total_minutes=1000, cap_minutes=210)
        assert p == 210 and review <= 105

    def test_flex_scales_with_weakness(self):
        hi, _, _ = _rp(weakness_global=1.0)      # factor 1.2
        lo, _, _ = _rp(weakness_global=0.0)      # factor 0.8
        assert (lo, hi) == (72, 108)

    def test_zero_template_minutes(self):
        p, review, _ = _rp(practice_total_minutes=0)
        assert (p, review) == (0, 0)

    def test_signature_has_no_ladder_argument(self):
        import inspect
        params = list(inspect.signature(rebalance_practice).parameters)
        assert 'ladder' not in params
        assert params[-1] == 'cap_minutes'


# ---------------------------------------------------------------------------
# derived shares
# ---------------------------------------------------------------------------

class TestDerivedShares:
    def test_worked_example(self):
        assert derived_shares(27, 63) == (0.30, 0.70)

    def test_zero_denominator(self):
        assert derived_shares(0, 0) == (1.0, 0.0)

    def test_review_only_and_acq_only(self):
        assert derived_shares(27, 0) == (1.0, 0.0)
        assert derived_shares(0, 40) == (0.0, 1.0)

    @pytest.mark.parametrize('r,a', [(1, 2), (7, 13), (27, 63), (5, 3), (100, 1)])
    def test_always_sums_to_one(self, r, a):
        m, q = derived_shares(r, a)
        assert abs(m + q - 1.0) < 1e-9
        assert 0.0 <= m <= 1.0 and 0.0 <= q <= 1.0


# ---------------------------------------------------------------------------
# compute_weekly_plan: scenarios A and B of the worked example
# ---------------------------------------------------------------------------

class TestComputeWeeklyPlanScenarios:
    def test_scenario_a_tests_and_review(self):
        out, _ = _compute()
        assert out['budget_scope'] == 'tests_and_review'
        assert out['practice_target_minutes'] == 90
        assert out['review_target_minutes'] == 27
        assert out['new_words_target'] == 35
        assert out['acq_target_minutes'] == 63            # min(105, 90 - 27)
        assert out['total_weekly_minutes'] == 210
        assert (out['maintenance_share'], out['acquisition_share']) == (0.30, 0.70)

    def test_scenario_b_tests_only(self):
        out, _ = _compute(plan_overrides={'budget_scope': 'tests_only'})
        assert out['budget_scope'] == 'tests_only'
        assert out['practice_target_minutes'] == 0
        assert out['acq_target_minutes'] == 0
        assert out['review_target_minutes'] == 27         # weekly TAIL target, within cap 105
        assert out['new_words_target'] == 35
        assert out['total_weekly_minutes'] == 210
        assert (out['maintenance_share'], out['acquisition_share']) == (1.0, 0.0)
        # freed practice minutes went to tests/surfaces as in an exclusion:
        # 11+9+4+2+2+7+4 = 39 slots (the water-fill preserves the total)
        assert sum(out['target_counts'].values()) == 39

    def test_new_words_zero_gives_zero_acq(self):
        out, _ = _compute(plan_overrides={'new_words_per_day': 0})
        assert out['new_words_target'] == 0
        assert out['acq_target_minutes'] == 0
        assert out['practice_target_minutes'] == 90        # P unchanged; spare returns to tests daily
        assert (out['maintenance_share'], out['acquisition_share']) == (1.0, 0.0)

    def test_acq_is_capped_by_room_in_pool(self):
        out, _ = _compute(plan_overrides={'new_words_per_day': 50})
        assert out['acq_target_minutes'] == 90 - 27

    def test_small_quota_not_padded(self):
        out, _ = _compute(plan_overrides={'new_words_per_day': 1})
        assert out['acq_target_minutes'] == 21             # 7 words * 3.0 min

    def test_per_language_minutes_per_new_word_used(self):
        out, _ = _compute(language_rows=[{'new_word_minutes_est': 2.0}])
        assert out['acq_target_minutes'] == min(35 * 2, 90 - 27)

    def test_practice_excluded_with_new_words_allowed(self):
        out, _ = _compute(plan_overrides={'excluded_modules': ['practice']})
        assert out['practice_target_minutes'] == 0
        assert out['acq_target_minutes'] == 0
        assert out['review_target_minutes'] == 0
        assert out['new_words_target'] == 35               # served in the tail

    def test_weekday_shape_reaches_new_words_target(self):
        out, _ = _compute(plan_overrides={'weekday_shape': [1.4] * 5 + [0, 0]})
        assert out['new_words_target'] == 35
        out, _ = _compute(plan_overrides={'weekday_shape': [1, 1, 1, 1, 1, 0, 0]})
        assert out['new_words_target'] == 25

    def test_unknown_scope_falls_back_to_default(self):
        out, _ = _compute(plan_overrides={'budget_scope': 'bogus'})
        assert out['budget_scope'] == 'tests_and_review'
        assert out['practice_target_minutes'] == 90

    def test_persist_payload_has_all_keys(self):
        out, db = _compute()
        for key in ('target_counts', 'skill_values', 'practice_target_minutes',
                    'maintenance_share', 'acquisition_share', 'total_weekly_minutes',
                    'budget_scope', 'review_target_minutes', 'new_words_target',
                    'acq_target_minutes'):
            assert key in out
        name, params = [c for c in db.rpc_calls if c[0] == 'compute_weekly_plan_persist'][-1]
        assert params['p_week_start'] == WEEK.isoformat()

    @pytest.mark.parametrize('overrides', [
        {}, {'budget_scope': 'tests_only'}, {'new_words_per_day': 0},
        {'excluded_modules': ['practice']}, {'excluded_modules': ['listening']},
        {'new_words_per_day': 50},
    ])
    def test_shares_are_valid_for_the_relaxed_check(self, overrides):
        """weekly_plan_states_shares_sum: each in [0,1], sum within 0.011 of 1."""
        out, _ = _compute(plan_overrides=overrides)
        m, a = out['maintenance_share'], out['acquisition_share']
        assert 0 <= m <= 1 and 0 <= a <= 1 and abs(m + a - 1.0) <= 0.011
        assert out['total_weekly_minutes'] <= 210


class TestDefaultPlanIsNoOp:
    """With the defaults, counts and totals equal the pre-change planner."""

    def _legacy(self, flex_pct=0.2):
        # Re-implementation of the pre-change pipeline for the fixture (no prior
        # week): cold-start weakness 0.5 for every skill, value 0.5, bandit, water-fill.
        scores = {
            s: bandit_score(round(value(0.5, 1200.0, 1.0), 6), 2.0, 2.0,
                            make_seed('u1', WEEK, s))
            for s in ZH30_WEEKLY_COUNTS
        }
        counts = allocate_test_counts(dict(ZH30_WEEKLY_COUNTS), scores)
        practice = min(round(ZH30_PRACTICE_TOTAL * (1.0 + flex_pct * (2 * 0.5 - 1))), 210)
        total = min(int(round(
            sum(c * ZH30_MINUTES[s] for s, c in counts.items()) + practice)), 210)
        return counts, practice, total

    def test_counts_practice_and_total_match_pre_change(self):
        out, _ = _compute()
        counts, practice, total = self._legacy()
        assert out['target_counts'] == counts
        assert out['practice_target_minutes'] == practice
        assert out['total_weekly_minutes'] == total

    def test_matches_with_new_words_zero_too(self):
        out, _ = _compute(plan_overrides={'new_words_per_day': 0})
        counts, practice, total = self._legacy()
        assert (out['target_counts'], out['practice_target_minutes'],
                out['total_weekly_minutes']) == (counts, practice, total)


class TestCarryOver:
    PRIOR = {'target_counts': {}, 'completed_counts': {}}

    def test_review_carry_over_decays_by_half(self):
        prior = dict(self.PRIOR, review_target_minutes=30, practice_completed_maint_min=10)
        out, _ = _compute(prior_week=prior)
        assert out['review_target_minutes'] == 27 + 10      # round(0.5 * 20)

    def test_review_carry_over_respects_pool_cap(self):
        prior = dict(self.PRIOR, review_target_minutes=500, practice_completed_maint_min=0)
        out, _ = _compute(prior_week=prior)
        assert out['review_target_minutes'] == 210          # daily*7
        assert out['practice_target_minutes'] == 210        # P = min(max(P0, review), cap)

    def test_tests_only_review_cap_is_half_the_week(self):
        prior = dict(self.PRIOR, review_target_minutes=500, practice_completed_maint_min=0)
        out, _ = _compute(plan_overrides={'budget_scope': 'tests_only'}, prior_week=prior)
        assert out['review_target_minutes'] == 105          # floor(210 * 0.5)
        assert out['practice_target_minutes'] == 0

    def test_new_words_are_not_carried_over(self):
        prior = dict(self.PRIOR, review_target_minutes=27, practice_completed_maint_min=27,
                     practice_target_minutes=90, practice_completed_acq_min=0,
                     new_words_target=35, new_words_completed=0, acq_target_minutes=63)
        with_prior, _ = _compute(prior_week=prior)
        without, _ = _compute()
        assert with_prior['new_words_target'] == without['new_words_target'] == 35
        assert with_prior['acq_target_minutes'] == without['acq_target_minutes']


# ---------------------------------------------------------------------------
# typical_day_inputs
# ---------------------------------------------------------------------------

class TestTypicalDayInputs:
    WEEK_ROW = {
        'target_counts': dict(ZH30_WEEKLY_COUNTS),
        'total_weekly_minutes': 210, 'practice_target_minutes': 90,
        'review_target_minutes': 27,
    }

    def test_worked_example(self):
        out = typical_day_inputs(FakeDb({'dim_test_types': []}), 1, {}, self.WEEK_ROW)
        assert out['review_min_per_day'] == pytest.approx(27 / 7)
        assert out['practice_room_min_per_day'] == pytest.approx(7.21, abs=0.01)

    def test_no_practice_pool_gives_zero_room(self):
        row = dict(self.WEEK_ROW, practice_target_minutes=0)
        out = typical_day_inputs(FakeDb({'dim_test_types': []}), 1, {}, row)
        assert out['practice_room_min_per_day'] == 0
        assert out['review_min_per_day'] == pytest.approx(27 / 7)   # tail target still reported

    def test_room_never_negative(self):
        row = dict(self.WEEK_ROW, review_target_minutes=200)
        out = typical_day_inputs(FakeDb({'dim_test_types': []}), 1, {}, row)
        assert out['practice_room_min_per_day'] == 0


# ---------------------------------------------------------------------------
# Governor and forecast
# ---------------------------------------------------------------------------

class TestGovernor:
    T = 3.857

    def test_level_boundaries(self):
        assert review_governor_level(self.T, self.T) == 'normal'
        assert review_governor_level(0, self.T) == 'normal'
        assert review_governor_level(self.T + 0.001, self.T) == 'reduced'
        assert review_governor_level(2 * self.T, self.T) == 'reduced'
        assert review_governor_level(2 * self.T + 0.001, self.T) == 'paused'

    def test_non_positive_threshold_is_normal(self):
        assert review_governor_level(99, 0) == 'normal'
        assert review_governor_level(99, None) == 'normal'

    def test_worked_example_levels(self):
        assert review_governor_level(3.33, self.T) == 'normal'      # 10 items
        assert review_governor_level(6.0, self.T) == 'reduced'      # 18 items
        assert review_governor_level(15.0, self.T) == 'paused'      # 45 items

    def test_effective_new_words(self):
        assert effective_new_words(5, 'normal') == 5
        assert effective_new_words(5, 'reduced') == 2
        assert effective_new_words(1, 'reduced') == 0
        assert effective_new_words(5, 'paused') == 0
        assert effective_new_words(-2, 'normal') == 0
        assert effective_new_words(5, 'unknown-level') == 5

    def test_sql_level_logic_matches(self):
        sql = _sql('review_governor.sql')
        assert re.search(r'p_threshold_min\s+IS\s+NULL\s+OR\s+p_threshold_min\s*<=\s*0\s+THEN\s+\'normal\'', sql)
        assert re.search(r'p_backlog_min\s*<=\s*p_threshold_min\s+THEN\s+\'normal\'', sql)
        assert re.search(r'p_backlog_min\s*<=\s*2\s*\*\s*p_threshold_min\s+THEN\s+\'reduced\'', sql)
        assert re.search(r"ELSE\s+'paused'", sql)
        assert re.search(r"WHEN\s+'paused'\s+THEN\s+0", sql)
        assert re.search(r"WHEN\s+'reduced'\s+THEN\s+GREATEST\(p_quota,\s*0\)\s*/\s*2", sql)

    def test_get_review_governor_happy_path(self):
        state = {'level': 'reduced', 'overdue_items': 18, 'overdue_minutes': 6.0,
                 'due_items': 20, 'due_minutes': 6.7, 'threshold_minutes': 3.86,
                 'item_seconds': 20.0}
        db = FakeDb(rpcs={'review_governor_state': state})
        out = get_review_governor(db, 'u1', 1, date(2026, 10, 13))
        assert out['level'] == 'reduced' and out['overdue_items'] == 18
        name, params = db.rpc_calls[0]
        assert name == 'review_governor_state'
        assert params == {'p_user_id': 'u1', 'p_language_id': 1, 'p_date': '2026-10-13'}

    def test_get_review_governor_failure_returns_normal(self):
        db = FakeDb(rpcs={'review_governor_state': RuntimeError('boom')})
        out = get_review_governor(db, 'u1', 1, date(2026, 10, 13))
        assert out['level'] == 'normal'
        assert out['overdue_items'] == 0 and out['due_items'] == 0
        assert out['overdue_minutes'] == 0 and out['threshold_minutes'] == 0
        assert out['item_seconds'] == Config.REVIEW_ITEM_SECONDS_DEFAULT

    @pytest.mark.parametrize('data', [None, [], 'x', {'level': 'bogus'}])
    def test_get_review_governor_malformed_is_normal(self, data):
        db = FakeDb(rpcs={'review_governor_state': data})
        assert get_review_governor(db, 'u', 1, '2026-10-13')['level'] == 'normal'


class TestForecast:
    def test_worked_example(self):
        assert review_forecast_min_per_day(5, 20.0) == pytest.approx(11.6667, abs=1e-3)

    def test_no_division_by_thirty(self):
        # a stray "/ 30" would give 0.39
        assert review_forecast_min_per_day(5, 20.0) > 10

    def test_scales_with_weekly_target_over_seven(self):
        n = new_words_week_target(5, [1.4] * 5 + [0, 0]) / 7
        assert review_forecast_min_per_day(n, 20.0) == pytest.approx(11.6667, abs=1e-3)

    def test_zero_words(self):
        assert review_forecast_min_per_day(0, 20.0) == 0


# ---------------------------------------------------------------------------
# get_minutes_per_new_word + Config mirrors
# ---------------------------------------------------------------------------

class TestMinutesPerNewWord:
    def test_reads_column(self):
        db = FakeDb({'dim_languages': [{'new_word_minutes_est': '4.25'}]})
        assert get_minutes_per_new_word(db, 1) == 4.25

    @pytest.mark.parametrize('rows', [[], [{'new_word_minutes_est': None}],
                                      [{'new_word_minutes_est': 0}],
                                      [{'new_word_minutes_est': -1}],
                                      [{'new_word_minutes_est': 'nan'}],
                                      [{'new_word_minutes_est': 'abc'}]])
    def test_falls_back_to_default(self, rows):
        assert get_minutes_per_new_word(FakeDb({'dim_languages': rows}), 1) == 3.0

    def test_read_failure_falls_back(self):
        assert get_minutes_per_new_word(FakeDb({'dim_languages': RuntimeError('x')}), 1) == 3.0


class TestMirrorPins:
    def test_budget_scopes_equal_sql_check(self):
        sql = _sql('session_module_exclusions.sql')
        found = re.findall(r"CHECK\s*\(budget_scope\s+IN\s*\(([^)]*)\)\)", sql)
        assert len(found) >= 1
        for group in found:
            assert tuple(re.findall(r"'([a-z_]+)'", group)) == BUDGET_SCOPES

    def test_new_word_minutes_default_equals_sql_fallback(self):
        sql = _sql('session_module_exclusions.sql')
        m = re.search(r"CREATE OR REPLACE FUNCTION public\.new_word_minutes.*?COALESCE\(.*?,\s*([0-9.]+)\)",
                      sql, re.S)
        assert m and float(m.group(1)) == Config.NEW_WORD_MINUTES_DEFAULT == 3.0

    def test_new_words_max_matches_sql_range(self):
        sql = _sql('session_module_exclusions.sql')
        assert f'BETWEEN 0 AND {sps.NEW_WORDS_MAX_PER_DAY}' in sql

    def test_governor_constants_equal_sql(self):
        sql = _sql('review_governor.sql')
        assert re.search(r'c_threshold_days\s+constant\s+numeric\s*:=\s*%s' % re.escape(str(Config.REVIEW_BACKLOG_THRESHOLD_DAYS)), sql)
        assert re.search(r'c_floor_min\s+constant\s+numeric\s*:=\s*%s' % re.escape(str(Config.REVIEW_ALLOWANCE_FLOOR_MIN)), sql)
        assert re.search(r'ELSE\s+%s\s+END' % re.escape(str(Config.REVIEW_ITEM_SECONDS_DEFAULT)), sql)

    def test_config_values(self):
        assert Config.NEW_WORD_MINUTES_DEFAULT == 3.0
        assert Config.REVIEW_BACKLOG_THRESHOLD_DAYS == 1.0
        assert Config.REVIEW_ALLOWANCE_FLOOR_MIN == 3.0
        assert Config.REVIEW_ITEM_SECONDS_DEFAULT == 20.0
        assert Config.REVIEWS_PER_NEW_WORD_30D == 7
        assert sps.REVIEW_TAIL_CAP_FRACTION == 0.5
        assert sps.REVIEW_PRESSURE_OFFSET == 0.5
        assert sps.TAIL_OFFER_MAX_MIN == 20 == Config.TAIL_OFFER_MAX_MIN
        assert sps.NEW_WORDS_MAX_PER_DAY == 50
        assert Config.RECENT_TEST_WINDOW_DAYS == 28
        assert Config.CALIBRATION_EVIDENCE_MAX_AGE_DAYS == 90


# ---------------------------------------------------------------------------
# rebuild_today
# ---------------------------------------------------------------------------

class TestRebuildToday:
    def _svc(self, load_rows, build_result):
        calls = []
        db = FakeDb(
            tables={'daily_test_loads': load_rows,
                    'user_study_plans': [{'timezone': 'UTC'}]},
            rpcs={'build_daily_session': lambda p: calls.append(p) or build_result},
        )
        return StudyPlanService(db=db), db, calls

    def test_rebuilds_when_row_exists(self):
        svc, db, calls = self._svc([{'load_date': 'x'}], {'ok': True})
        assert svc.rebuild_today('u1', 1) is True
        assert len(calls) == 1 and calls[0]['p_user_id'] == 'u1'

    def test_no_row_returns_false_without_building(self):
        svc, db, calls = self._svc([], {'ok': True})
        assert svc.rebuild_today('u1', 1) is False
        assert calls == []

    def test_error_result_returns_false(self):
        svc, _, _ = self._svc([{'load_date': 'x'}], {'error': 'x', 'code': 'E_NOWEEK'})
        assert svc.rebuild_today('u1', 1) is False

    def test_rpc_exception_returns_false(self):
        svc, _, _ = self._svc([{'load_date': 'x'}], RuntimeError('db down'))
        assert svc.rebuild_today('u1', 1) is False


class TestPriorWeekCarriesReviewTarget:
    """compute_weekly_plan reads prior_week['review_target_minutes'] for the review
    carry-over. compute_weekly_plan_load_signals returns prior_week as
    to_jsonb(weekly_plan_states row), so the key exists as soon as the column does
    (Migration 1); this pins that contract in the SQL source."""

    ROOT = Path(__file__).resolve().parent.parent / 'migrations'

    def test_load_signals_prior_week_is_the_whole_row(self):
        src = (self.ROOT / 'phase13_compute_weekly_plan_helpers.sql').read_text(encoding='utf-8')
        body = src[src.index('FUNCTION public.compute_weekly_plan_load_signals'):]
        body = body[:body.index('compute_weekly_plan_persist')]
        assert 'SELECT to_jsonb(wps.*) INTO v_prior' in body
        assert "'prior_week',    v_prior" in body

    def test_review_target_minutes_is_a_column_of_weekly_plan_states(self):
        src = (self.ROOT / 'session_module_exclusions.sql').read_text(encoding='utf-8')
        assert re.search(r'ADD COLUMN IF NOT EXISTS review_target_minutes\s+int', src)

    def test_carry_over_uses_the_prior_review_target(self):
        base, _ = _compute()
        out, _ = _compute(prior_week={
            'review_target_minutes': 40, 'practice_completed_maint_min': 0,
            'target_counts': {}, 'completed_counts': {},
        })
        assert out['review_target_minutes'] > base['review_target_minutes']
