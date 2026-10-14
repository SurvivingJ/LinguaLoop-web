"""TASK-872 service side -- new-word accrual arguments and tail / unstarted-first
ordering in ``PracticeSessionService``.

``record_session_progress`` is a SQL RPC (agent-owned migration); here only the
Python call contract is pinned: ``p_sense_id`` is passed for acquisition attempts
only, ``p_is_tail`` follows the ``is_tail`` flag. Ordering is applied to the RPC's
items after the fact (the selection RPC is untouched).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from config import Config
from services import practice_session_service as pss
from services.practice_session_service import PracticeSessionService
from services.vocabulary.knowledge_service import VocabularyKnowledgeService


class _Q:
    def __init__(self, data=None, sink=None, name=None):
        self._data, self._sink, self._name = data, sink, name

    def __getattr__(self, _n):
        return lambda *a, **k: self

    def insert(self, row):
        self._sink.append(('insert', self._name, row))
        self._data = [{'id': 'attempt-1'}]
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


class _DB:
    def __init__(self, exercise, tables=None):
        self.exercise = exercise
        self.tables = tables or {}
        self.rpcs = []
        self.log = []

    def table(self, name):
        if name == 'exercises':
            q = _Q(self.exercise)      # .single().execute().data -> dict
            return q
        if name == 'exercise_attempts':
            return _Q([], self.log, name)
        return _Q(self.tables.get(name, []), self.log, name)

    def rpc(self, name, args):
        self.rpcs.append((name, args))
        return _Q(None)


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', True)
    # BKT / FSRS are not under test.
    monkeypatch.setattr(VocabularyKnowledgeService, '__init__', lambda self, db=None: None)
    monkeypatch.setattr(VocabularyKnowledgeService, 'update_from_word_test',
                        lambda self, **k: None)
    monkeypatch.setattr(PracticeSessionService, '_update_fsrs_for_exercise',
                        lambda *a, **k: None)
    db = _DB({'id': 'ex-1', 'exercise_type': 'definition_match', 'word_sense_id': 42,
              'attempt_count': 0, 'correct_count': 0, 'language_id': 1})
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = db
    return s


def _progress_args(svc):
    (name, args), = [r for r in svc.db.rpcs if r[0] == 'record_session_progress']
    return args


def test_acquisition_attempt_passes_the_sense_id(svc):
    svc.record_attempt_with_updates('u', 'ex-1', True, session_mode='acquisition',
                                    language_id=1)
    args = _progress_args(svc)
    assert args['p_kind'] == 'practice_acq'
    assert args['p_sense_id'] == 42
    assert args['p_is_tail'] is False


def test_maintenance_attempt_passes_no_sense_id(svc):
    svc.record_attempt_with_updates('u', 'ex-1', True, session_mode='maintenance',
                                    language_id=1)
    args = _progress_args(svc)
    assert args['p_kind'] == 'practice_maint' and args['p_sense_id'] is None


def test_tail_flag_is_forwarded(svc):
    svc.record_attempt_with_updates('u', 'ex-1', True, session_mode='acquisition',
                                    language_id=1, is_tail=True)
    assert _progress_args(svc)['p_is_tail'] is True


# ---------------------------------------------------------------------------
# ordering
# ---------------------------------------------------------------------------

def _svc_with(tables=None, state=None, monkeypatch=None):
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = _DB(None, tables)
    s.new_word_state = lambda u, l: state
    return s


def _acq(sense, n=1):
    return [{'mode': 'acquisition', 'sense_id': sense, 'exercise_id': f'{sense}-{i}'}
            for i in range(n)]


def test_unstarted_words_are_served_first_oldest_admission_first():
    items = _acq(7, 2) + _acq(5, 2) + _acq(9, 1) + _acq(3, 1)
    s = _svc_with(state={'unstarted_sense_ids': [9, 5]})
    payload = {'items': items}
    s._order_items(payload, 'u', 1, 'acquisition')
    assert [i['sense_id'] for i in payload['items']] == [9, 5, 5, 7, 7, 3]
    # one word's items stay contiguous and in order
    assert [i['exercise_id'] for i in payload['items']][1:3] == ['5-0', '5-1']


def test_no_unstarted_words_leaves_the_order_alone():
    items = _acq(7) + _acq(5)
    s = _svc_with(state={'unstarted_sense_ids': []})
    payload = {'items': list(items)}
    s._order_items(payload, 'u', 1, 'acquisition')
    assert payload['items'] == items


def test_maintenance_is_served_most_overdue_first():
    items = [{'mode': 'maintenance', 'sense_id': sid, 'exercise_id': f'm{sid}'}
             for sid in (1, 2, 3, 4)]
    tables = {
        'user_flashcards': [{'sense_id': 1, 'due_date': '2026-10-12'},
                            {'sense_id': 2, 'due_date': '2026-10-01'}],
        'user_word_ladder': [{'sense_id': 3, 'review_due_at': '2026-09-20T08:00:00+00:00'},
                             {'sense_id': 1, 'review_due_at': '2026-10-13T00:00:00+00:00'}],
    }
    s = _svc_with(tables=tables, state=None)
    payload = {'items': items}
    s._order_items(payload, 'u', 1, 'maintenance')
    # 3 (Sep 20) < 2 (Oct 1) < 1 (Oct 12, earliest source wins) < 4 (no due date)
    assert [i['sense_id'] for i in payload['items']] == [3, 2, 1, 4]


def test_ordering_failure_is_non_fatal_in_get_session(monkeypatch):
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = MagicMock()
    s.db.rpc.return_value.execute.return_value.data = {'items': _acq(1, 2)}
    s._maybe_top_up_ladder = lambda u, l: []
    s._apply_session_floor = lambda *a, **k: None
    s._apply_script_variant = lambda *a, **k: None
    s._prepare_jumbled_items = lambda *a, **k: None
    s._order_items = MagicMock(side_effect=RuntimeError('boom'))
    monkeypatch.setattr('services.dual_translation.cards.select_error_exercises_for_practice',
                        lambda *a, **k: [])
    payload = s.get_session('u', 1, mode='acquisition', tail=True)
    assert payload['tail'] is True and len(payload['items']) == 2
