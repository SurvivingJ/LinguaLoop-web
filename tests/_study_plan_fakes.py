"""Shared stubs for the Tier B planner tests (no live DB).

Importable as ``tests._study_plan_fakes`` (tests/ is a package).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional

# ZH 30-minute template (id 101): the worked example in
# wiki/features/session-modules.tech.md and session-budget-settings.tech.md.
ZH30_WEEKLY_COUNTS = {
    'reading': 6, 'listening': 5, 'dictation': 2, 'pinyin': 1,
    'classifier_drill': 1, 'flashcards': 7, 'dual_translation': 2,
}
ZH30_MINUTES = {          # Config.TEST_TYPE_MINUTES seeds
    'reading': 6, 'listening': 5, 'dictation': 6, 'pinyin': 4,
    'classifier_drill': 4, 'pitch_accent': 4, 'flashcards': 7,
    'dual_translation': 12,
}
ZH30_PRACTICE_TOTAL = 90


def minutes_of(skill: str) -> float:
    return float(ZH30_MINUTES[skill])


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db: 'FakeDb', table: str):
        self._db, self._table = db, table

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        rows = self._db.tables.get(self._table, [])
        if isinstance(rows, Exception):
            raise rows
        return _Resp(list(rows))


class _Rpc:
    def __init__(self, db: 'FakeDb', name: str, params: Dict[str, Any]):
        self._db, self._name, self._params = db, name, params

    def execute(self):
        self._db.rpc_calls.append((self._name, self._params))
        out = self._db.rpcs.get(self._name)
        if callable(out):
            out = out(self._params)
        if isinstance(out, Exception):
            raise out
        return _Resp(out)


class FakeDb:
    """Minimal Supabase-like client: fixed rows per table, canned RPC results."""

    def __init__(self, tables: Optional[Dict[str, Any]] = None,
                 rpcs: Optional[Dict[str, Any]] = None):
        self.tables = tables or {}
        self.rpcs = rpcs or {}
        self.rpc_calls: List[Any] = []

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params=None):
        return _Rpc(self, name, params or {})

    def persisted(self) -> Dict[str, Any]:
        calls = [p for n, p in self.rpc_calls if n == 'compute_weekly_plan_persist']
        assert calls, 'compute_weekly_plan_persist was not called'
        return calls[-1]['p_computed']


def zh30_db(*, plan_overrides: Optional[Dict[str, Any]] = None,
            prior_week: Optional[Dict[str, Any]] = None,
            language_rows: Optional[list] = None,
            flex_pct: float = 0.2) -> FakeDb:
    """FakeDb for compute_weekly_plan on the ZH-30 fixture.

    Signals are chosen so weakness_global = 0.5 (flex_factor 1.0) and
    maint_pressure = 0.5 (review_share = 0.30 at base 0.30).
    """
    plan = {
        'template_id': 101, 'daily_minutes': 30, 'skill_weight_overrides': {},
        'weekday_shape': [1.0] * 7, 'excluded_modules': [],
        'budget_scope': 'tests_and_review', 'new_words_per_day': 5,
    }
    plan.update(plan_overrides or {})
    template = {
        'template_id': 101, 'daily_minutes': 30,
        'weekly_test_counts': dict(ZH30_WEEKLY_COUNTS),
        'practice_total_minutes': ZH30_PRACTICE_TOTAL,
        'base_maintenance_share': 0.30,
        'practice_minutes_flex_pct': flex_pct,
    }
    signals = {
        'user_mean_elo': 1200, 'skills': {}, 'ladder': {}, 'fsrs': {},
        'bkt': {'known_count_p80': 10, 'decayed_count': 10},
        'prior_week': prior_week,
    }
    return FakeDb(
        tables={
            'user_study_plans': [plan],
            'dim_study_plan_templates': [template],
            'dim_test_types': [],            # -> Config.TEST_TYPE_MINUTES seeds
            'dim_languages': language_rows if language_rows is not None else [],
        },
        rpcs={
            'compute_weekly_plan_load_signals': signals,
            'compute_weekly_plan_persist': lambda p: p['p_computed'],
        },
    )
