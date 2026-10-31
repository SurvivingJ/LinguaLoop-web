"""services/study_time.py (weekly-minutes, TASK-888). RPCs are mocked."""

from datetime import date
from types import SimpleNamespace

import pytest

from services import study_time as st
from services.attempt_timing import MAX_CREDITED_ATTEMPT_SECONDS
from services.practice_session_service import PRACTICE_ATTEMPT_MAX_SECONDS


class RpcDB:
    def __init__(self, data=True, raises=None):
        self.calls, self.data, self.raises = [], data, raises

    def rpc(self, name, params):
        self.calls.append((name, params))
        outer = self

        class _Q:
            def execute(self_inner):
                if outer.raises:
                    raise outer.raises
                return SimpleNamespace(data=outer.data)
        return _Q()


def test_caps_reuse_existing_constants():
    assert st.KIND_CAPS_SECONDS == {
        'test': MAX_CREDITED_ATTEMPT_SECONDS, 'drill': MAX_CREDITED_ATTEMPT_SECONDS,
        'practice': PRACTICE_ATTEMPT_MAX_SECONDS, 'flashcard': 120,
        'dual_translation': 900, 'prestudy': 900,
    }
    assert MAX_CREDITED_ATTEMPT_SECONDS == 1200 and PRACTICE_ATTEMPT_MAX_SECONDS == 300


@pytest.mark.parametrize('value', [None, True, False, 'abc', '', float('nan'), -5, 0, [], {}, float('-inf')])
def test_clamp_active_ms_junk_is_zero(value):
    assert st.clamp_active_ms('flashcard', value) == 0


@pytest.mark.parametrize('kind,ms,expected', [
    ('flashcard', 45_500, 45), ('flashcard', 10**9, 120), ('flashcard', float('inf'), 120),
    ('dual_translation', 10**9, 900), ('practice', 400_000, 300),
    ('test', 10**9, 1200), ('drill', '30000', 30), ('nope', 5000, 0),
])
def test_clamp_active_ms(kind, ms, expected):
    assert st.clamp_active_ms(kind, ms) == expected


@pytest.mark.parametrize('value,expected', [
    ('7b9e1d8e-4c1a-4f0a-9d6e-0a1b2c3d4e5f', '7b9e1d8e-4c1a-4f0a-9d6e-0a1b2c3d4e5f'),
    ('7B9E1D8E-4C1A-4F0A-9D6E-0A1B2C3D4E5F', '7b9e1d8e-4c1a-4f0a-9d6e-0a1b2c3d4e5f'),
    ('nope', None), ('', None), (None, None), (12, None), (True, None),
])
def test_parse_client_event_id(value, expected):
    assert st.parse_client_event_id(value) == expected


def test_credit_calls_rpc_with_spec_args():
    db = RpcDB(True)
    assert st.credit_study_time(db, 'u1', 3, 'test', 90, 'test_attempts', 'a1') is True
    assert db.calls == [('credit_study_time', {
        'p_user_id': 'u1', 'p_language_id': 3, 'p_kind': 'test', 'p_seconds': 90,
        'p_source_table': 'test_attempts', 'p_source_id': 'a1',
    })]


def test_credit_clamps_before_rpc():
    db = RpcDB(True)
    st.credit_study_time(db, 'u1', 1, 'flashcard', 9999, 'flashcard_review', 'e')
    assert db.calls[0][1]['p_seconds'] == 120


def test_credit_duplicate_returns_false():
    assert st.credit_study_time(RpcDB(False), 'u1', 1, 'test', 5, 't', 'x') is False


@pytest.mark.parametrize('kwargs', [
    dict(seconds=0), dict(seconds=-3), dict(seconds=None), dict(seconds=True),
    dict(source_id=''), dict(source_id=None), dict(user_id=None), dict(language_id=None),
    dict(kind='bogus'),
])
def test_credit_skips_without_calling_rpc(kwargs):
    base = dict(user_id='u', language_id=1, kind='test', seconds=10,
                source_table='test_attempts', source_id='a')
    base.update(kwargs)
    db = RpcDB(True)
    assert st.credit_study_time(db, base['user_id'], base['language_id'], base['kind'],
                                base['seconds'], base['source_table'], base['source_id']) is False
    assert db.calls == []


def test_credit_never_raises():
    assert st.credit_study_time(RpcDB(raises=RuntimeError('boom')), 'u', 1, 'test', 10, 't', 'a') is False


def test_summary_shape_and_rounding():
    db = RpcDB({'test': 900, 'practice': 600, 'flashcard': 300, 'dual_translation': 240, 'drill': 0})
    out = st.weekly_study_summary(db, 'u1', 1, date(2026, 10, 12), 210)
    assert db.calls == [('get_weekly_study_seconds', {
        'p_user_id': 'u1', 'p_language_id': 1, 'p_week_start': '2026-10-12'})]
    assert out == {
        'week_start_date': '2026-10-12', 'studied_seconds': 2040, 'studied_minutes': 34,
        'target_minutes': 210,
        'by_kind': {
            'test': {'seconds': 900, 'minutes': 15},
            'practice': {'seconds': 600, 'minutes': 10},
            'flashcard': {'seconds': 300, 'minutes': 5},
            'dual_translation': {'seconds': 240, 'minutes': 4},
            'drill': {'seconds': 0, 'minutes': 0},
            'prestudy': {'seconds': 0, 'minutes': 0},
        },
    }
    assert list(out['by_kind']) == ['test', 'practice', 'flashcard', 'dual_translation', 'drill', 'prestudy']


def test_summary_missing_keys_default_zero_and_null_target():
    out = st.weekly_study_summary(RpcDB({'test': 30}), 'u', 1, date(2026, 10, 12), None)
    assert out['target_minutes'] is None
    assert out['by_kind']['test'] == {'seconds': 30, 'minutes': 1}   # 0.5 min rounds up
    assert out['by_kind']['drill'] == {'seconds': 0, 'minutes': 0}
    assert out['studied_minutes'] == 1


@pytest.mark.parametrize('db', [RpcDB(raises=RuntimeError('x')), RpcDB(None), RpcDB([1])])
def test_summary_none_on_failure(db):
    assert st.weekly_study_summary(db, 'u', 1, date(2026, 10, 12), 10) is None
