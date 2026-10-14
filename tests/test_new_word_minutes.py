"""TASK-870: nightly job wiring for dim_languages.new_word_minutes_est.

The estimate itself is computed in SQL (migrations/new_word_minutes_estimate.sql);
here we pin the Python side: call order, summary merge and failure isolation.
"""

from unittest.mock import patch

from services import study_plan_service as sps
from tests._study_plan_fakes import FakeDb


def _run(rpcs):
    db = FakeDb(rpcs=rpcs)
    with patch.object(sps, 'get_supabase_admin', return_value=db):
        return sps._refresh_exercise_time_estimates(), db


def test_calls_new_word_refresh_after_time_estimates_and_merges_summary():
    out, db = _run({
        'refresh_practice_time_estimates': {'exercise_types_updated': 3, 'test_types_updated': 2},
        'refresh_new_word_minutes': {'languages_updated': 4},
    })
    assert [n for n, _ in db.rpc_calls] == [
        'refresh_practice_time_estimates', 'refresh_new_word_minutes']
    assert out['languages_updated'] == 4
    assert out['exercise_types_updated'] == 3 and out['test_types_updated'] == 2


def test_new_word_refresh_skipped_when_time_estimates_fail():
    out, db = _run({
        'refresh_practice_time_estimates': RuntimeError('boom'),
        'refresh_new_word_minutes': {'languages_updated': 4},
    })
    assert 'error' in out
    assert [n for n, _ in db.rpc_calls] == ['refresh_practice_time_estimates']


def test_new_word_refresh_failure_does_not_break_the_job():
    out, _ = _run({
        'refresh_practice_time_estimates': {'exercise_types_updated': 1, 'test_types_updated': 1},
        'refresh_new_word_minutes': RuntimeError('rpc missing'),
    })
    assert 'error' not in out
    assert out['exercise_types_updated'] == 1
    assert out['languages_updated'] == 0


def test_malformed_new_word_response_counts_zero():
    out, _ = _run({
        'refresh_practice_time_estimates': {},
        'refresh_new_word_minutes': None,
    })
    assert out['languages_updated'] == 0
