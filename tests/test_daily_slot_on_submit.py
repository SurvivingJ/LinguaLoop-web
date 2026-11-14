"""A daily-load slot is marked complete when the test is submitted.

Before, only the results card's "Next" button marked it (POST
/api/tests/daily-load/complete). Leaving from the results card re-served the
same test, and a re-submit was scored again (2026-11-11 walkthrough).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import services.test_service as ts
from services.test_service import TestService as _TestService


class LoadDB:
    """daily_test_loads fake: select returns ``row``; update records the patch."""

    def __init__(self, row):
        self.row, self.updates = row, []

    def table(self, name):
        assert name == 'daily_test_loads'
        db = self

        class Q:
            def __init__(s):
                s.patch = None

            def select(s, *_a):
                return s

            def update(s, patch):
                s.patch = patch
                return s

            def eq(s, *_a):
                return s

            def limit(s, *_a):
                return s

            def execute(s):
                if s.patch is not None:
                    db.updates.append(s.patch)
                    return SimpleNamespace(data=[])
                return SimpleNamespace(data=[db.row] if db.row else [])
        return Q()


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setattr(ts, 'plan_today_iso', lambda *a, **k: '2026-11-11')


def _mark(row, test_id='t2'):
    db = LoadDB(row)
    out = _TestService(supabase_admin=db).mark_daily_slot_complete_on_submit('u', 1, test_id)
    return out, db.updates


def test_marks_a_test_in_todays_load():
    out, updates = _mark({'id': 9, 'test_ids': ['t1', 't2'], 'completed_test_ids': ['t1']})
    assert out is True
    assert updates == [{'completed_test_ids': ['t1', 't2']}]


def test_marks_a_test_in_a_study_plan_load():
    # the Study Plan resolver stores slot objects, not plain ids
    slots = [{'test_id': 't1', 'slot_type': 'new', 'test_type': 'reading'},
             {'test_id': 't2', 'slot_type': 'new', 'test_type': 'dictation'}]
    out, updates = _mark({'id': 9, 'test_ids': slots, 'completed_test_ids': []})
    assert out is True
    assert updates == [{'completed_test_ids': ['t2']}]


def test_already_complete_is_not_rewritten():
    out, updates = _mark({'id': 9, 'test_ids': ['t2'], 'completed_test_ids': ['t2']})
    assert out is True and updates == []


def test_test_outside_the_load_changes_nothing():
    out, updates = _mark({'id': 9, 'test_ids': ['t1'], 'completed_test_ids': []})
    assert out is False and updates == []


def test_no_load_today_changes_nothing():
    out, updates = _mark(None)
    assert out is False and updates == []


# ---- route wiring --------------------------------------------------------

def _rpc_ok():
    return {'success': True, 'attempt_id': 'att-1', 'score': 1, 'total_questions': 1}


@pytest.fixture
def test_row_db(app, monkeypatch):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value \
        .single.return_value.execute.return_value = SimpleNamespace(data={
            'id': 'T7', 'language_id': 1,
            'pinyin_payload': [{'char': c, 'is_punctuation': False} for c in '一二三四']})
    monkeypatch.setattr('services.supabase_factory.get_supabase_admin', lambda: db)
    return db


def test_reading_submit_marks_the_slot(client, auth_headers, test_row_db):
    body = {'responses': [{'question_id': 'q', 'selected_answer': 'a'}], 'test_mode': 'reading'}
    with patch('routes.tests.submit._call_submission_rpc', return_value=_rpc_ok()), \
         patch('routes.tests.submit._update_vocabulary_tracking', return_value=None), \
         patch('routes.tests.submit._build_submission_response', return_value={}), \
         patch('routes.tests.submit._attach_explanations'), \
         patch('routes.tests.submit._apply_timing_and_progress'), \
         patch('routes.tests.DimensionService.get_test_type_id', return_value=1), \
         patch.object(_TestService, 'mark_daily_slot_complete_on_submit', return_value=True) as mark:
        r = client.post('/api/tests/slug/submit', json=body, headers=auth_headers)
    assert r.status_code == 200, r.data
    mark.assert_called_once()
    assert mark.call_args.args[1:] == (1, 'T7')


def test_pinyin_submit_marks_the_slot(client, auth_headers, test_row_db):
    with patch('routes.tests.submit._call_pinyin_submission_rpc', return_value=_rpc_ok()), \
         patch('routes.tests.submit._apply_timing_and_progress'), \
         patch('routes.tests.DimensionService.get_test_type_id', return_value=9), \
         patch.object(_TestService, 'mark_daily_slot_complete_on_submit', return_value=True) as mark:
        r = client.post('/api/tests/slug/submit-pinyin',
                        json={'correct_chars': 3, 'total_chars': 4}, headers=auth_headers)
    assert r.status_code == 200, r.data
    assert mark.call_args.args[1:] == (1, 'T7')


def test_slot_failure_does_not_fail_the_submission(client, auth_headers, test_row_db):
    with patch('routes.tests.submit._call_pinyin_submission_rpc', return_value=_rpc_ok()), \
         patch('routes.tests.submit._apply_timing_and_progress'), \
         patch('routes.tests.DimensionService.get_test_type_id', return_value=9), \
         patch.object(_TestService, 'mark_daily_slot_complete_on_submit',
                      side_effect=RuntimeError('db down')):
        r = client.post('/api/tests/slug/submit-pinyin',
                        json={'correct_chars': 3, 'total_chars': 4}, headers=auth_headers)
    assert r.status_code == 200
