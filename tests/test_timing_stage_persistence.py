"""services.timing.log_stage_seconds — best-effort persistence of a completed
stage() bucket to generation_stage_timings (TASK-758).

Mirrors tests/test_llm_call_cost_logging.py's doubles-and-patch pattern: no
real DB, no real generation pipeline — just pin the contract (row shape,
never-raises, one row per stage name, empty bucket is a no-op).
"""

from unittest.mock import patch

import services.timing as svc


class _Table:
    def __init__(self, store):
        self._store = store

    def insert(self, rows):
        self._store.extend(rows)
        return self

    def execute(self):
        return None


class _DB:
    def __init__(self, store):
        self._store = store

    def table(self, name):
        assert name == 'generation_stage_timings'
        return _Table(self._store)


class _RaisingDB:
    """Simulates a DB outage — every call raises."""

    def table(self, name):
        raise RuntimeError('connection refused')


def test_writes_one_row_per_stage_name():
    store = []
    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB(store)):
        svc.log_stage_seconds(
            {'prose': 12.3, 'questions': 45.6},
            pipeline='test_gen', language_code='zh',
            artifact_id='11111111-1111-1111-1111-111111111111',
            run_id='22222222-2222-2222-2222-222222222222',
        )

    assert len(store) == 2
    names = {row['stage_name'] for row in store}
    assert names == {'prose', 'questions'}
    for row in store:
        assert row['pipeline'] == 'test_gen'
        assert row['language_code'] == 'zh'
        assert row['artifact_id'] == '11111111-1111-1111-1111-111111111111'
        assert row['run_id'] == '22222222-2222-2222-2222-222222222222'


def test_converts_seconds_to_integer_milliseconds():
    store = []
    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB(store)):
        svc.log_stage_seconds({'audio': 2.5}, pipeline='test_gen')

    assert store[0]['duration_ms'] == 2500


def test_empty_bucket_is_a_noop_and_never_touches_the_client():
    calls = []

    class _TrackedDB:
        def table(self, name):
            calls.append(name)
            raise AssertionError('should never be called for an empty bucket')

    with patch('services.supabase_factory.get_supabase_admin', lambda: _TrackedDB()):
        svc.log_stage_seconds({}, pipeline='test_gen')

    assert calls == []


def test_db_outage_never_raises():
    """Observability must never break the calling generation pipeline — same
    contract as services.llm_service._log_llm_call."""
    with patch('services.supabase_factory.get_supabase_admin', lambda: _RaisingDB()):
        # Must not raise.
        svc.log_stage_seconds({'prose': 1.0}, pipeline='test_gen')


def test_optional_fields_default_to_none():
    store = []
    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB(store)):
        svc.log_stage_seconds({'p1_generate': 3.0}, pipeline='vocab_ladder')

    row = store[0]
    assert row['language_code'] is None
    assert row['artifact_id'] is None
    assert row['run_id'] is None


def test_no_supabase_client_available_is_silent():
    with patch('services.supabase_factory.get_supabase_admin', lambda: None), \
         patch('services.supabase_factory.get_supabase', lambda: None):
        # Must not raise even when neither client is available.
        svc.log_stage_seconds({'prose': 1.0}, pipeline='test_gen')
