"""Session modules (ADR-032): apply_module_exclusions + compute_weekly_plan wiring.

Spec: wiki/features/session-modules.tech.md (Testing Strategy, Worked Example),
wiki/tasklist/session-modules.tasks.md TASK-864.
"""

import re
from pathlib import Path

import pytest

from services import study_plan_service as sps
from services.study_plan_service import (
    ALL_MODULES,
    MODULE_PRACTICE,
    NON_SCALABLE_MODULES,
    StudyPlanService,
    apply_module_exclusions,
)
from tests._study_plan_fakes import (
    ZH30_PRACTICE_TOTAL,
    ZH30_WEEKLY_COUNTS,
    minutes_of,
    zh30_db,
)

REPO = Path(__file__).resolve().parents[1]
MIGRATION = REPO / 'migrations' / 'session_module_exclusions.sql'


def _total_minutes(counts, practice):
    return sum(c * minutes_of(s) for s, c in counts.items()) + practice


# ---------------------------------------------------------------------------
# apply_module_exclusions (pure)
# ---------------------------------------------------------------------------

class TestApplyModuleExclusions:
    def test_empty_exclusion_is_identity(self):
        counts = dict(ZH30_WEEKLY_COUNTS)
        out, practice = apply_module_exclusions(counts, 90, [], minutes_of)
        assert out is counts                     # byte-identical default
        assert practice == 90

    def test_unknown_or_absent_keys_ignored(self):
        counts = dict(ZH30_WEEKLY_COUNTS)
        out, practice = apply_module_exclusions(
            counts, 90, ['pitch_accent', 'bogus'], minutes_of)
        assert out is counts and practice == 90

    def test_zh30_worked_example_exclude_listening(self):
        out, practice = apply_module_exclusions(
            dict(ZH30_WEEKLY_COUNTS), 90, ['listening'], minutes_of)
        assert out == {
            'reading': 7, 'dictation': 3, 'pinyin': 1, 'classifier_drill': 1,
            'flashcards': 7, 'dual_translation': 2,
        }
        assert practice == 103
        assert 'listening' not in out
        # 42 + 18 + 4 + 4 + 49 + 24 + 103 = 244, same as before
        assert _total_minutes(out, practice) == 244

    def test_practice_only_exclusion_scenario_b(self):
        """Scenario B of session-budget-settings (tests_only => practice excluded)."""
        out, practice = apply_module_exclusions(
            dict(ZH30_WEEKLY_COUNTS), 90, [MODULE_PRACTICE], minutes_of)
        assert out == {
            'reading': 11, 'listening': 9, 'dictation': 4, 'pinyin': 2,
            'classifier_drill': 2, 'flashcards': 7, 'dual_translation': 4,
        }
        assert practice == 0
        assert _total_minutes(out, practice) == 248      # 244 +- one slot of rounding

    def test_all_tests_excluded_except_practice(self):
        ex = [s for s in ZH30_WEEKLY_COUNTS]
        out, practice = apply_module_exclusions(
            dict(ZH30_WEEKLY_COUNTS), 90, ex, minutes_of)
        assert out == {}
        assert practice == 244          # k = 244 / 90 -> the whole day goes to practice

    def test_flashcards_only_has_no_redistribution(self):
        ex = [s for s in ZH30_WEEKLY_COUNTS if s != 'flashcards'] + [MODULE_PRACTICE]
        out, practice = apply_module_exclusions(
            dict(ZH30_WEEKLY_COUNTS), 90, ex, minutes_of)
        assert out == {'flashcards': 7}
        assert practice == 0

    def test_flashcards_never_rescaled(self):
        assert 'flashcards' in NON_SCALABLE_MODULES
        for ex in (['reading'], ['dictation', 'practice'], ['dual_translation']):
            out, _ = apply_module_exclusions(
                dict(ZH30_WEEKLY_COUNTS), 90, ex, minutes_of)
            assert out['flashcards'] == 7

    def test_every_kept_skill_keeps_at_least_its_count(self):
        out, _ = apply_module_exclusions(
            dict(ZH30_WEEKLY_COUNTS), 90, ['listening', 'dictation'], minutes_of)
        for s, c in out.items():
            assert c >= ZH30_WEEKLY_COUNTS[s] >= 1

    def test_deterministic_tie_break_is_key_ascending(self):
        # Two skills with identical remainders: the alphabetically first wins the spare unit.
        counts = {'dictation': 1, 'reading': 1, 'listening': 1}
        mins = {'dictation': 1.0, 'reading': 1.0, 'listening': 1.0}
        # exclude listening: k = 3/2 -> raw 1.5 each, N = round(3.0) = 3, floors 1+1
        out, _ = apply_module_exclusions(
            counts, 0, ['listening'], lambda s: mins[s])
        assert out == {'dictation': 2, 'reading': 1}
        again, _ = apply_module_exclusions(
            counts, 0, ['listening'], lambda s: mins[s])
        assert again == out

    @pytest.mark.parametrize('ex', [
        ['reading'], ['listening', 'pinyin'], ['practice'], ['dual_translation', 'dictation'],
    ])
    def test_total_minutes_preserved_within_one_slot(self, ex):
        out, practice = apply_module_exclusions(
            dict(ZH30_WEEKLY_COUNTS), 90, ex, minutes_of)
        before = _total_minutes(ZH30_WEEKLY_COUNTS, 90)
        after = _total_minutes(out, practice)
        assert abs(after - before) <= max(minutes_of(s) for s in out) + 1


# ---------------------------------------------------------------------------
# Constants vs the SQL CHECK
# ---------------------------------------------------------------------------

class TestModuleVocabulary:
    def test_all_modules_equals_sql_check_list(self):
        sql = MIGRATION.read_text(encoding='utf-8')
        m = re.search(
            r"user_study_plans_excluded_modules_known\s+CHECK\s*\(excluded_modules\s*<@\s*ARRAY\[(.*?)\]",
            sql, re.S)
        assert m, 'excluded_modules CHECK not found in the migration'
        sql_modules = re.findall(r"'([a-z_]+)'", m.group(1))
        assert set(sql_modules) == set(ALL_MODULES)
        assert len(sql_modules) == len(set(sql_modules))

    def test_practice_constant_and_membership(self):
        assert MODULE_PRACTICE == 'practice'
        assert MODULE_PRACTICE in ALL_MODULES
        assert ALL_MODULES[-1] == MODULE_PRACTICE
        assert set(NON_SCALABLE_MODULES) <= set(ALL_MODULES)

    def test_every_template_skill_is_a_module(self):
        assert set(ZH30_WEEKLY_COUNTS) <= set(ALL_MODULES)


# ---------------------------------------------------------------------------
# compute_weekly_plan (stubbed DB)
# ---------------------------------------------------------------------------

class TestComputeWeeklyPlanExclusions:
    def _run(self, **kw):
        db = zh30_db(**kw)
        svc = StudyPlanService(db=db)
        from datetime import date
        assert svc.compute_weekly_plan('u1', 1, date(2026, 10, 12)) is not None
        return db.persisted()

    def test_excluded_skill_absent_from_persisted_counts(self):
        out = self._run(plan_overrides={'excluded_modules': ['listening']})
        assert 'listening' not in out['target_counts']
        assert 'listening' not in out['skill_values']

    def test_practice_excluded_zeroes_review_and_practice(self):
        out = self._run(plan_overrides={'excluded_modules': ['practice']})
        assert out['review_target_minutes'] == 0
        assert out['acq_target_minutes'] == 0
        assert out['practice_target_minutes'] == 0
        assert (out['maintenance_share'], out['acquisition_share']) == (1.0, 0.0)

    def test_practice_excluded_ignores_review_carry_over(self):
        prior = {'target_counts': {}, 'completed_counts': {},
                 'review_target_minutes': 40, 'practice_completed_maint_min': 0}
        out = self._run(plan_overrides={'excluded_modules': ['practice']},
                        prior_week=prior)
        assert out['review_target_minutes'] == 0

    def test_no_test_carry_over_for_excluded_skills(self):
        prior = {'target_counts': {'listening': 5, 'reading': 6},
                 'completed_counts': {'listening': 0, 'reading': 0},
                 'review_target_minutes': 0, 'practice_completed_maint_min': 0}
        base = self._run(plan_overrides={'excluded_modules': ['listening']})
        carried = self._run(plan_overrides={'excluded_modules': ['listening']},
                            prior_week=prior)
        assert 'listening' not in carried['target_counts']
        assert carried['target_counts']['reading'] == base['target_counts']['reading'] + 3

    def test_default_exclusions_empty_is_noop_on_counts(self):
        a = self._run(plan_overrides={'excluded_modules': []})
        b = self._run(plan_overrides={'excluded_modules': ['pitch_accent']})   # not in template
        assert a['target_counts'] == b['target_counts']
        assert a['total_weekly_minutes'] == b['total_weekly_minutes']


def test_sps_exports_exist():
    for name in ('apply_module_exclusions', 'ALL_MODULES', 'NON_SCALABLE_MODULES', 'MODULE_PRACTICE'):
        assert hasattr(sps, name)
