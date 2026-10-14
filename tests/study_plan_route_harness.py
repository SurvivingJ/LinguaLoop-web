"""Shared fakes for the /api/study-plan route tests.

Builds a minimal Flask app that mounts only ``study_plan_bp`` (no full
``create_app`` -> no external services), bypasses JWT auth, and swaps in a fake
Supabase admin plus a fake ``services.study_plan_service`` module, so the route
logic is exercised without a DB and independent of the concurrently developed
service helpers.
"""

import sys
import types
from types import SimpleNamespace

from flask import Flask

ALL_MODULES = (
    'reading', 'listening', 'dictation', 'pinyin', 'classifier_drill',
    'pitch_accent', 'flashcards', 'dual_translation', 'practice',
)

ZH_TEMPLATE_KEYS = {
    'reading': 6, 'listening': 5, 'dictation': 2, 'pinyin': 1,
    'classifier_drill': 1, 'flashcards': 7, 'dual_translation': 2,
}
ZH_AVAILABLE = [
    'reading', 'listening', 'dictation', 'pinyin', 'classifier_drill',
    'flashcards', 'dual_translation', 'practice',
]


class FakeQuery:
    def __init__(self, db, table):
        self.db, self.table, self.ops = db, table, []

    def _op(self, name, *args):
        self.ops.append((name, args))
        return self

    def select(self, *a, **k):
        return self._op('select', *a)

    def eq(self, *a, **k):
        return self._op('eq', *a)

    def limit(self, *a, **k):
        return self._op('limit', *a)

    def order(self, *a, **k):
        return self._op('order', *a)

    def update(self, payload):
        return self._op('update', payload)

    def execute(self):
        self.db.executed.append((self.table, list(self.ops)))
        for name, args in self.ops:
            if name == 'update':
                self.db.updates.append((self.table, args[0]))
        src = self.db.tables.get(self.table, [])
        data = src(self) if callable(src) else src
        return SimpleNamespace(data=data)


class FakeDB:
    def __init__(self, tables):
        self.tables = tables
        self.executed = []
        self.updates = []
        self.rpcs = []

    def table(self, name):
        return FakeQuery(self, name)

    def rpc(self, name, params):
        self.rpcs.append((name, params))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data={'applied': True}))

    def updates_for(self, table):
        return [p for t, p in self.updates if t == table]


def make_fake_service_module(*, rebuild_result=True, compute_raises=False, rebuild_raises=False):
    """A stand-in ``services.study_plan_service`` exposing the names the route uses."""
    calls = SimpleNamespace(compute=[], rebuild=[])

    class StudyPlanService:
        def __init__(self, db=None):
            self.db = db

        def compute_weekly_plan(self, user_id, language_id, week_start):
            calls.compute.append((user_id, language_id, week_start))
            if compute_raises:
                raise RuntimeError('boom')
            return {'ok': True}

        def rebuild_today(self, user_id, language_id):
            calls.rebuild.append((user_id, language_id))
            if rebuild_raises:
                raise RuntimeError('boom')
            return rebuild_result

    mod = types.ModuleType('services.study_plan_service')
    mod.ALL_MODULES = ALL_MODULES
    mod.StudyPlanService = StudyPlanService
    mod.get_minutes_per_new_word = lambda db, language_id: 3.0
    mod.typical_day_inputs = lambda db, language_id, plan, week: {
        'practice_room_min_per_day': 9.0, 'review_min_per_day': 4.0,
    }
    mod.get_review_governor = lambda db, user_id, language_id, d: {
        'level': 'normal', 'overdue_items': 0, 'overdue_minutes': 0.0,
        'threshold_minutes': 3.0, 'due_items': 0, 'due_minutes': 0.0, 'item_seconds': 20.0,
    }
    mod.new_words_week_target = lambda npd, shape: int(npd) * 7
    mod.review_forecast_min_per_day = lambda avg, item_seconds: avg * 7 * item_seconds / 60.0
    mod.REVIEWS_PER_NEW_WORD_30D = 7
    mod.calls = calls
    return mod


def install(monkeypatch, db, *, service=None, study_plan_enabled=True):
    """Return a Flask test client with fakes wired in."""
    import middleware.auth as auth
    import routes.study_plan as sp
    from config import Config

    service = service or make_fake_service_module()
    monkeypatch.setitem(sys.modules, 'services.study_plan_service', service)
    monkeypatch.setattr(auth, '_authenticate', lambda token: ({'sub': 'user-1'}, None))
    monkeypatch.setattr(sp, 'get_supabase_admin', lambda: db)
    monkeypatch.setattr(sp, 'plan_today', lambda d, u, l: __import__('datetime').date(2026, 10, 14))
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', study_plan_enabled, raising=False)

    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(sp.study_plan_bp, url_prefix='/api/study-plan')
    client = app.test_client()
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer fake'
    return client, service


def plan_tables(*, excluded=None, scope='tests_and_review', npd=5, daily=30, week=True,
                targets=None, templates=None):
    """Tables for a learner who has a plan row."""
    plan_row = {
        'user_id': 'user-1', 'language_id': 1, 'template_id': 101, 'daily_minutes': daily,
        'weekday_shape': [1.0] * 7, 'skill_weight_overrides': {}, 'goal_id': None,
        'timezone': 'UTC', 'excluded_modules': list(excluded or []),
        'budget_scope': scope, 'new_words_per_day': npd,
    }
    week_row = {
        'week_start_date': '2026-10-12', 'target_counts': {'reading': 6}, 'skill_values': {},
        'completed_counts': {}, 'practice_target_minutes': 60,
        'practice_completed_maint_min': 0, 'practice_completed_acq_min': 0,
        'maintenance_share': 0.3, 'acquisition_share': 0.7, 'total_weekly_minutes': 210,
        'computed_at': None, 'budget_scope': scope, 'review_target_minutes': 20,
        'new_words_target': npd * 7, 'new_words_completed': 3, 'acq_target_minutes': 40,
        'tail_completed_min': 0, 'tail_new_words_completed': 0,
    }
    return {
        'user_study_plans': [plan_row],
        'weekly_plan_states': [week_row] if week else [],
        'dim_study_plan_templates': (
            [{'template_id': 101, 'language_id': 1, 'daily_minutes': 30,
              'weekly_test_counts': ZH_TEMPLATE_KEYS}] if templates is None else templates
        ),
        'daily_test_loads': (
            [{'daily_session_targets': targets}] if targets is not None else []
        ),
    }
