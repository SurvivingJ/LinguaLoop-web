"""services/knowledge_snapshots.py — the nightly snapshot job (TASK-1037, ADR-053, tech §7, §13)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest

from services import knowledge_snapshots as ks
from services.vocabulary import knowledge_estimate as ke
from tests._knowledge_fakes import (
    DE6_JA, FRAMES, OTHER_USER, USER, FakeDB, de6_summary_rpc, empty_summary_rpc,
)

# 23:30 in New York on the 16th is already the 17th in UTC: the snapshot day is the UTC date.
NOW = datetime(2026, 11, 17, 4, 25, tzinfo=timezone.utc)
PAIRS = [{'user_id': USER, 'language_id': 3}, {'user_id': OTHER_USER, 'language_id': 1}]


def _db(pairs=PAIRS, summaries=None, errors=None):
    summaries = summaries or {}

    def summary(params):
        key = (params['p_user_id'], params['p_language_id'])
        if key in (errors or {}):
            raise RuntimeError(errors[key])
        return summaries.get(key, de6_summary_rpc() if params['p_language_id'] == 3
                             else empty_summary_rpc(params['p_language_id']))
    return FakeDB(rpc_results={'knowledge_active_pairs': pairs, 'knowledge_frame_bands': FRAMES,
                               'knowledge_report_summary': summary, 'knowledge_snapshots_prune': 4})


def _rows(db):
    return db.tables.get(ks.TABLE, [])


def test_one_upsert_per_pair_with_every_column():
    db = _db()
    result = ks.run_nightly(db, now=NOW)
    assert result == {'pairs': 2, 'written': 2, 'failed': 0, 'pruned': 4}
    assert len(db.upserts) == 2
    assert all(u[0] == ks.TABLE and u[2] == 'user_id,language_id,snapshot_date' for u in db.upserts)

    row = next(r for r in _rows(db) if r['user_id'] == USER)
    assert row['snapshot_date'] == '2026-11-17'
    assert (row['method_version'], row['source']) == (ke.METHOD_VERSION, 'nightly')
    assert (row['tracked_words'], row['tracked_meanings'], row['rated_known_words']) == (251, 251, 69)
    assert (row['checked_meanings'], row['missed_recent_meanings'], row['idle60_meanings']) == (109, 10, 95)
    assert (row['practised_30_meanings'], row['direct_checks_30']) == (41, 164)
    assert row['cal_definition_language_id'] == 2
    assert len(row['cal_bands']) == 21 and len(row['frame_bands']) == 7
    assert ke.snapshot_bands(row) == DE6_JA
    assert row['frame_bands'] == FRAMES['3:2']
    assert row['cal_answers'] == 172
    assert row['cal_first_answer_at'].startswith('2026-09-13')
    assert row['cal_last_answer_at'].startswith('2026-11-15')
    # The estimate outputs: 850–1,400, kind range (1), label medium (2).
    assert (row['est_kind'], row['est_lo'], row['est_hi'], row['est_label']) == (1, 850, 1400, 2)
    expected_columns = {
        'user_id', 'language_id', 'snapshot_date', 'method_version', 'tracked_words', 'tracked_meanings',
        'rated_known_words', 'checked_meanings', 'missed_recent_meanings', 'idle60_meanings',
        'practised_30_meanings', 'direct_checks_30', 'cal_definition_language_id', 'cal_bands',
        'frame_bands', 'cal_answers', 'cal_first_answer_at', 'cal_last_answer_at', 'est_kind', 'est_lo',
        'est_hi', 'est_label', 'source', 'computed_at'}
    assert set(row) == expected_columns


def test_a_pair_without_check_answers_stores_no_calibration_inputs():
    db = _db()
    ks.run_nightly(db, now=NOW)
    row = next(r for r in _rows(db) if r['user_id'] == OTHER_USER)
    assert row['cal_definition_language_id'] is None
    assert row['cal_bands'] is None and row['frame_bands'] is None
    assert (row['est_kind'], row['est_lo'], row['est_hi'], row['est_label']) == (0, None, None, None)
    assert row['cal_answers'] == 0


def test_the_rpcs_get_one_as_of_and_the_window_start():
    db = _db()
    ks.run_nightly(db, now=NOW)
    assert db.rpc_calls('knowledge_active_pairs') == [
        {'p_since': (NOW - timedelta(days=180)).isoformat()}]
    calls = db.rpc_calls('knowledge_report_summary')
    assert {c['p_as_of'] for c in calls} == {NOW.isoformat()}
    assert all(c['p_cal_since'] == [] for c in calls)
    assert [(c['p_user_id'], c['p_language_id']) for c in calls] == [(USER, 3), (OTHER_USER, 1)]
    assert len(db.rpc_calls('knowledge_frame_bands')) == 1


def test_running_twice_on_the_same_day_leaves_one_row_per_pair():
    db = _db()
    ks.run_nightly(db, now=NOW)
    ks.run_nightly(db, now=NOW + timedelta(hours=1))
    assert len(_rows(db)) == 2
    assert len({(r['user_id'], r['language_id'], r['snapshot_date']) for r in _rows(db)}) == 2


def test_next_day_adds_a_row():
    db = _db()
    ks.run_nightly(db, now=NOW)
    ks.run_nightly(db, now=NOW + timedelta(days=1))
    assert sorted(r['snapshot_date'] for r in _rows(db) if r['user_id'] == USER) == ['2026-11-17', '2026-11-18']


def test_a_failing_pair_is_logged_and_skipped(caplog):
    db = _db(errors={(USER, 3): 'statement timeout'})
    with caplog.at_level(logging.WARNING, logger=ks.__name__):
        result = ks.run_nightly(db, now=NOW)
    assert result == {'pairs': 2, 'written': 1, 'failed': 1, 'pruned': 4}
    assert f'knowledge_snapshot_failed user={USER[:8]} lang=3' in caplog.text
    assert USER not in caplog.text
    assert [r['user_id'] for r in _rows(db)] == [OTHER_USER]


def test_prune_keeps_120_days_of_daily_rows():
    db = _db()
    ks.run_nightly(db, now=NOW)
    assert db.rpc_calls('knowledge_snapshots_prune') == [{'p_keep_daily_days': 120}]
    assert db.rpcs[-1][0] == 'knowledge_snapshots_prune'


def test_snapshot_date_is_the_utc_date():
    late_evening_new_york = datetime(2026, 11, 16, 23, 30, tzinfo=timezone(timedelta(hours=-5)))
    db = _db()
    ks.run_nightly(db, now=late_evening_new_york)
    assert {r['snapshot_date'] for r in _rows(db)} == {'2026-11-17'}


def test_no_pairs_still_prunes():
    db = _db(pairs=[])
    assert ks.run_nightly(db, now=NOW) == {'pairs': 0, 'written': 0, 'failed': 0, 'pruned': 4}


def test_skipped_before_the_foundation_migration():
    db = FakeDB(rpc_errors={'knowledge_active_pairs':
                            "{'code': 'PGRST202', 'message': 'Could not find the function'}"})
    assert ks.run_nightly(db, now=NOW) == {'skipped': True, 'reason': 'knowledge_active_pairs not deployed'}
    assert db.upserts == []


def test_other_pair_listing_errors_propagate():
    db = FakeDB(rpc_errors={'knowledge_active_pairs': 'connection reset'})
    with pytest.raises(RuntimeError):
        ks.run_nightly(db, now=NOW)


def test_manual_run_writes_source_manual(monkeypatch, capsys):
    db = _db()
    monkeypatch.setattr('services.supabase_factory.get_supabase_admin', lambda: db)
    assert ks.main(['--once']) == 0
    assert {r['source'] for r in _rows(db)} == {'manual'}
    assert '"written": 2' in capsys.readouterr().out


def test_manual_run_needs_once():
    with pytest.raises(SystemExit):
        ks.main([])


def test_scheduler_registers_the_job_after_the_sweep():
    from web import scheduler as sched
    ids = [job.id for job in sched.JOBS]
    job = sched.JOBS[ids.index('knowledge_snapshots_nightly')]
    assert ids.index('knowledge_snapshots_nightly') == ids.index('word_upload_watchlist_sweep_nightly') + 1
    assert (job.target, job.cron, job.label) == (
        'services.knowledge_snapshots:run_nightly', {'hour': 4, 'minute': 25}, 'Knowledge snapshots')
    assert job.report is sched._log_skippable and job.args is sched._admin_client
    assert job.when == '04:25 UTC'
