"""Daily-session read merges (ADR-043 option B, TASK-930).

Each merge must give exactly the result of the per-table reads it replaces,
and fall back to them when its bundle RPC is missing or fails.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import Flask

from services import optional_rpc, prestudy, request_cache
from tests.test_prestudy_session import T1, T2, _DB


@pytest.fixture(autouse=True)
def _reset_optional_rpc():
    optional_rpc.reset()
    yield
    optional_rpc.reset()


class _RpcDB(_DB):
    """_DB whose rpc() returns canned results per function name."""

    def __init__(self, tables=None, rpc_results=None, rpc_errors=None):
        super().__init__(tables)
        self.rpc_results = rpc_results or {}
        self.rpc_errors = rpc_errors or {}

    def rpc(self, name, params):
        self.rpcs.append((name, params))

        def execute():
            if name in self.rpc_errors:
                raise RuntimeError(self.rpc_errors[name])
            return SimpleNamespace(data=self.rpc_results.get(name))
        return SimpleNamespace(execute=execute)


# ---------------------------------------------------------------------------
# optional_rpc.call_bundle
# ---------------------------------------------------------------------------

class TestCallBundle:
    def test_returns_the_dict(self):
        db = _RpcDB(rpc_results={'f': {'a': 1}})
        assert optional_rpc.call_bundle(db, 'f', {}) == {'a': 1}

    def test_unwraps_a_one_row_list(self):
        db = _RpcDB(rpc_results={'f': [{'a': 1}]})
        assert optional_rpc.call_bundle(db, 'f', {}) == {'a': 1}

    def test_non_dict_is_none(self):
        assert optional_rpc.call_bundle(_RpcDB(rpc_results={'f': True}), 'f', {}) is None

    def test_missing_function_is_remembered(self):
        db = _RpcDB(rpc_errors={'f': "{'code': 'PGRST202', 'message': 'Could not find the function public.f'}"})
        assert optional_rpc.call_bundle(db, 'f', {}) is None
        assert optional_rpc.call_bundle(db, 'f', {}) is None
        assert len(db.rpcs) == 1          # second call skipped

    def test_other_errors_are_retried(self):
        db = _RpcDB(rpc_errors={'f': 'connection reset'})
        optional_rpc.call_bundle(db, 'f', {})
        optional_rpc.call_bundle(db, 'f', {})
        assert len(db.rpcs) == 2


# ---------------------------------------------------------------------------
# prestudy.plan_for_tests: bundle == per-table reads
# ---------------------------------------------------------------------------

TABLES = {
    'tests': [{'id': T1, 'vocab_sense_ids': [1, 2, 3, 4, 5]},
              {'id': T2, 'vocab_sense_ids': [5, 6]}],
    'user_vocabulary_knowledge': [
        {'user_id': 'u', 'sense_id': 1, 'p_known': 0.9, 'status': 'known', 'evidence_count': 3},
        {'user_id': 'u', 'sense_id': 2, 'p_known': 0.1, 'status': 'unknown', 'evidence_count': 3},
        {'user_id': 'u', 'sense_id': 6, 'p_known': 0.6, 'status': 'learning', 'evidence_count': 1}],
    'dim_word_senses': [{'id': 3, 'dim_vocabulary': {'frequency_rank': 7.0}},
                        {'id': 4, 'dim_vocabulary': {'frequency_rank': 2.0}},
                        {'id': 5, 'dim_vocabulary': None}],
    'user_calibration_state': [{'ability_zipf': 4.2}],
    'exercises': [{'word_sense_id': 2, 'is_active': True}, {'word_sense_id': 2, 'is_active': True},
                  {'word_sense_id': 4, 'is_active': True}, {'word_sense_id': 6, 'is_active': True}],
}

BUNDLE = {   # what prestudy_plan_inputs returns for TABLES
    'tests': TABLES['tests'],
    'knowledge': [{k: r[k] for k in ('sense_id', 'p_known', 'status', 'evidence_count')}
                  for r in TABLES['user_vocabulary_knowledge']],
    'freq': [{'id': 3, 'frequency_rank': 7.0}, {'id': 4, 'frequency_rank': 2.0},
             {'id': 5, 'frequency_rank': None}],
    'ability_zipf': 4.2,
    'with_exercises': [2, 4, 6],
}

TESTS = [{'id': T1, 'test_type': 'reading'}, {'id': T2, 'test_type': 'listening'},
         {'id': 'x', 'test_type': 'dictation'}]


class TestPrestudyBundle:
    def test_bundle_gives_the_same_plans_as_the_per_table_reads(self):
        per_table = prestudy.plan_for_tests(_RpcDB(TABLES), 'u', 3, TESTS)        # rpc -> None
        db = _RpcDB({}, rpc_results={'prestudy_plan_inputs': BUNDLE})             # no tables at all
        bundled = prestudy.plan_for_tests(db, 'u', 3, TESTS)
        assert per_table and bundled == per_table
        assert [n for n, _ in db.rpcs] == ['prestudy_plan_inputs']
        assert db.rpcs[0][1]['p_test_ids'] == [T1, T2]     # reading/listening only

    def test_missing_ability_uses_the_default(self):
        b = dict(BUNDLE, ability_zipf=None)
        t = dict(TABLES, user_calibration_state=[])
        assert prestudy.plan_for_tests(_RpcDB({}, rpc_results={'prestudy_plan_inputs': b}), 'u', 3, TESTS) \
            == prestudy.plan_for_tests(_RpcDB(t), 'u', 3, TESTS)

    def test_falls_back_when_the_bundle_errors(self):
        db = _RpcDB(TABLES, rpc_errors={'prestudy_plan_inputs': 'boom'})
        assert prestudy.plan_for_tests(db, 'u', 3, TESTS) == prestudy.plan_for_tests(_RpcDB(TABLES), 'u', 3, TESTS)


# ---------------------------------------------------------------------------
# new_word_state: one RPC instead of two
# ---------------------------------------------------------------------------

PLAN = {'user_id': 'u', 'language_id': 3, 'timezone': 'UTC', 'new_words_per_day': 10,
        'weekday_shape': [1.0] * 7, 'excluded_modules': []}
GOV = {'level': 'reduced', 'overdue_items': 40, 'due_items': 60, 'overdue_minutes': 9.5,
       'due_minutes': 14.0, 'threshold_minutes': 8.0, 'item_seconds': 14.0}
LADDER = {'unstarted': 3, 'started_today': 1, 'unstarted_sense_ids': [7, 8, 9]}


def _service(db):
    from services.practice_session_service import PracticeSessionService
    svc = PracticeSessionService.__new__(PracticeSessionService)
    svc.db = db
    return svc


class TestNewWordStateBundle:
    def test_bundle_matches_the_two_rpcs(self):
        two = _RpcDB({'user_study_plans': [PLAN]},
                     rpc_results={'review_governor_state': GOV, 'ladder_new_word_state': LADDER})
        one = _RpcDB({'user_study_plans': [PLAN]},
                     rpc_results={'new_word_state_inputs': {'governor': GOV, 'ladder': LADDER}})
        # make the two-RPC fake look "not deployed" for the bundle
        two.rpc_errors['new_word_state_inputs'] = 'PGRST202 Could not find the function'
        a = _service(two)._new_word_state('u', 3)
        optional_rpc.reset()     # `two` marked the bundle as not deployed
        b = _service(one)._new_word_state('u', 3)
        assert a == b and a['level'] == 'reduced' and a['unstarted'] == 3
        assert [n for n, _ in one.rpcs] == ['new_word_state_inputs']
        assert [n for n, _ in two.rpcs] == ['new_word_state_inputs', 'review_governor_state', 'ladder_new_word_state']

    def test_practice_excluded_skips_the_governor(self):
        plan = dict(PLAN, excluded_modules=['practice'])
        db = _RpcDB({'user_study_plans': [plan]},
                    rpc_results={'new_word_state_inputs': {'governor': None, 'ladder': LADDER}})
        state = _service(db)._new_word_state('u', 3)
        assert state['governor'] == {'level': 'normal'}
        assert db.rpcs[0][1]['p_with_governor'] is False


# ---------------------------------------------------------------------------
# Daily load: tests + ratings in one query; row shared with the route
# ---------------------------------------------------------------------------

class TestDailyLoadMerges:
    def _svc(self, data, fail_embed=False):
        from services.test_service import TestService
        svc = TestService.__new__(TestService)
        calls = []

        class Q:
            def __init__(self, table):
                self.table, self.sel = table, None

            def select(self, sel, **k):
                self.sel = sel
                return self

            def in_(self, *a):
                return self

            def execute(self):
                calls.append((self.table, self.sel))
                if fail_embed and 'test_skill_ratings(' in (self.sel or ''):
                    raise RuntimeError('embed not available')
                if self.table == 'tests':
                    embed = 'test_skill_ratings(' in self.sel
                    return SimpleNamespace(data=[
                        {**{k: v for k, v in t.items() if k != 'ratings'},
                         **({'test_skill_ratings': [{'test_type_id': 1, 'elo_rating': e,
                                                     'dim_test_types': {'type_code': c}}
                                                    for c, e in t['ratings'].items()]} if embed else {})}
                        for t in data])
                return SimpleNamespace(data=[{'test_id': t['id'], 'test_type_id': 1, 'elo_rating': e,
                                              'dim_test_types': {'type_code': c}}
                                             for t in data for c, e in t['ratings'].items()])

        svc._admin = SimpleNamespace(table=lambda name: Q(name))
        return svc, calls

    DATA = [{'id': 'a', 'slug': 'a', 'title': 'A', 'ratings': {'reading': 1300, 'listening': 1250}},
            {'id': 'b', 'slug': 'b', 'title': 'B', 'ratings': {'listening': 1400}}]
    ROW = {'load_date': '2026-11-11', 'completed_test_ids': ['b'],
           'test_ids': [{'test_id': 'a', 'test_type': 'listening', 'slot_type': 'new'},
                        {'test_id': 'b', 'test_type': 'listening', 'slot_type': 'retry'},
                        {'test_id': 'gone', 'test_type': 'reading', 'slot_type': 'new'}]}

    def test_one_query_and_same_result_as_two(self):
        embedded, calls_e = self._svc(self.DATA)
        separate, calls_s = self._svc(self.DATA, fail_embed=True)
        a = embedded._enrich_daily_load(self.ROW)
        b = separate._enrich_daily_load(self.ROW)
        assert a == b
        assert [t['elo_rating'] for t in a['tests']] == [1250, 1400]
        assert all('test_skill_ratings' not in t for t in a['tests'])
        assert len(calls_e) == 1 and len(calls_s) == 3   # failed embed + 2 fallback reads

    def test_route_reuses_the_row_the_service_read(self):
        from services.test_service import daily_load_row_key
        app = Flask(__name__)
        with app.test_request_context('/', method='GET'):
            request_cache.put(daily_load_row_key('u', 3, '2026-11-11'), {'completed_blocks': ['x']})
            loader_calls = []
            row = request_cache.memo(daily_load_row_key('u', '3', '2026-11-11'),
                                     lambda: loader_calls.append(1))
            assert row == {'completed_blocks': ['x']} and not loader_calls
            request_cache.invalidate('daily_load_row', 'u')
            request_cache.memo(daily_load_row_key('u', 3, '2026-11-11'), lambda: loader_calls.append(1))
            assert loader_calls == [1]


# ---------------------------------------------------------------------------
# minutes per new word: cached per client
# ---------------------------------------------------------------------------

class TestMinutesPerNewWordCache:
    def test_one_read_per_client_and_language(self):
        from services.study_plan_service import get_minutes_per_new_word
        db = _DB({'dim_languages': [{'id': 3, 'new_word_minutes_est': 1.7}]})
        reads = []
        orig = db.table
        db.table = lambda name: (reads.append(name), orig(name))[1]
        assert get_minutes_per_new_word(db, 3) == 1.7
        assert get_minutes_per_new_word(db, 3) == 1.7
        assert reads == ['dim_languages']

    def test_a_failed_read_is_not_cached(self):
        from config import Config
        from services.study_plan_service import get_minutes_per_new_word
        db = _DB(fail={'dim_languages': 'down'})
        assert get_minutes_per_new_word(db, 3) == float(Config.NEW_WORD_MINUTES_DEFAULT)
        db.fail = {}
        db.tables = {'dim_languages': [{'id': 3, 'new_word_minutes_est': 2.5}]}
        assert get_minutes_per_new_word(db, 3) == 2.5
