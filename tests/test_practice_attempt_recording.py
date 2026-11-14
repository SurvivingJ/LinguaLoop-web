"""Practice attempt write path: first-attempt flag, exercise counters, step
ordering, and the record_exercise_attempt RPC path behind its env flag."""

import threading
from types import SimpleNamespace

import pytest

from config import Config
from services import intro_drill
from services import practice_session_service as pss
from services.practice import attempt_recording
from services.practice_session_service import PracticeSessionService
from services.vocabulary.knowledge_service import VocabularyKnowledgeService

CARD = {'id': 9, 'stability': 3.0, 'difficulty': 5.0, 'due_date': '2026-11-01',
        'last_review': '2026-10-20T08:00:00+00:00', 'reps': 4, 'lapses': 0, 'state': 'review'}
LADDER = {'family': 'meaning_recall', 'current_ring': 2, 'word_state': 'active',
          'gate_pending': None, 'stress_test_ready': False, 'demoted': False, 'is_lapse': False}
BKT = {'out_sense_id': 42, 'out_p_known_before': 0.4, 'out_p_known_after': 0.6,
       'out_status': 'learning'}


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.op, self.payload, self.filters = db, table, 'select', None, []
        self.one = False

    def single(self):
        self.one = True
        return self

    def select(self, *_a, **_k):
        return self

    def insert(self, row):
        self.op, self.payload = 'insert', row
        return self

    def update(self, row):
        self.op, self.payload = 'update', row
        return self

    def eq(self, col, val):
        self.filters.append(('eq', col, val))
        return self

    def is_(self, col, val):
        self.filters.append(('is', col, val))
        return self

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        return SimpleNamespace(data=self.db.answer(self))


class _DB:
    """Records every table operation and RPC in completion order."""

    def __init__(self, exercise=None, prior=(), card=None, rpc=None, counter_conflicts=0):
        self.exercise = exercise if exercise is not None else {
            'id': 'ex-1', 'exercise_type': 'definition_match', 'word_sense_id': 42,
            'attempt_count': 7, 'correct_count': 3, 'language_id': 1}
        self.prior, self.card = list(prior), card
        self.rpc_data = rpc or {}
        self.counter_conflicts = counter_conflicts
        self.log, self.lock = [], threading.Lock()

    def table(self, name):
        return _Q(self, name)

    def answer(self, q):
        with self.lock:
            self.log.append((q.table, q.op, q.payload, tuple(q.filters)))
        if q.table == 'exercises' and q.op == 'select':
            if q.one:
                return self.exercise
            # the counter re-read after a conflicting write
            return [dict(self.exercise, attempt_count=self.exercise['attempt_count'] + 1)]
        if q.table == 'exercises' and q.op == 'update':
            conditional = any(f[1] == 'attempt_count' for f in q.filters)
            if conditional and self.counter_conflicts > 0:
                self.counter_conflicts -= 1
                return []
            return [{'id': 'ex-1'}]
        if q.table == 'exercise_attempts':
            if q.op == 'insert':
                return [{'id': 'attempt-1'}]
            return self.prior if q.op == 'select' else []
        if q.table == 'user_flashcards' and q.op == 'select':
            return [self.card] if self.card else []
        return []

    def rpc(self, name, params):
        with self.lock:
            self.log.append(('rpc', name, params, ()))
        data = self.rpc_data.get(name)
        if isinstance(data, Exception):
            raise data
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))

    def ops(self, table, op):
        return [e for e in self.log if e[0] == table and e[1] == op]

    def rpcs(self, name):
        return [e[2] for e in self.log if e[0] == 'rpc' and e[1] == name]

    def position(self, table_or_rpc, op):
        return next(i for i, e in enumerate(self.log) if e[0] == table_or_rpc and e[1] == op)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv(pss.ATTEMPT_RPC_ENV_FLAG, raising=False)
    monkeypatch.setattr(attempt_recording, '_attempt_rpc_missing_until', 0.0)
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', True)
    monkeypatch.setattr(intro_drill, 'restart_if_demoted', lambda *a: False)
    monkeypatch.setattr(VocabularyKnowledgeService, '_trigger_frequency_inference',
                        lambda self, *a: None)


def _svc(db):
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = db
    return s


def _default_rpcs(**extra):
    return {'update_vocabulary_from_word_test': [BKT], 'ladder_apply_progress': LADDER,
            'credit_study_time': True, 'record_session_progress': True, **extra}


# -- first-attempt flag ------------------------------------------------------

@pytest.mark.parametrize('prior, expected', [([], True), ([{'id': 'old'}], False)])
def test_inserted_row_carries_is_first_attempt(prior, expected):
    db = _DB(prior=prior, rpc=_default_rpcs())
    out = _svc(db).record_attempt_with_updates('u', 'ex-1', True)
    (_, _, row, _), = db.ops('exercise_attempts', 'insert')
    assert row['is_first_attempt'] is expected
    assert out['is_first_attempt'] is expected
    # BKT only on a first attempt; the ladder RPC is told which it was.
    assert len(db.rpcs('update_vocabulary_from_word_test')) == (1 if expected else 0)
    assert db.rpcs('ladder_apply_progress')[0]['p_is_first_attempt'] is expected


def test_response_shape_is_unchanged():
    db = _DB(card=dict(CARD), rpc=_default_rpcs())
    out = _svc(db).record_attempt_with_updates(
        'u', 'ex-1', True, time_taken_ms=9000, session_mode='acquisition')
    assert out == {
        'attempt_id': 'attempt-1', 'is_correct': True, 'exercise_type': 'definition_match',
        'is_first_attempt': True, 'bkt_update': BKT,
        'ladder': {k: LADDER[k] for k in ('family', 'current_ring', 'word_state', 'gate_pending',
                                          'stress_test_ready', 'demoted', 'is_lapse')},
    }
    assert len(db.rpcs('credit_study_time')) == 1 and len(db.rpcs('record_session_progress')) == 1
    assert db.ops('exercise_attempts', 'update')[0][2] == {'p_known_before': 0.4, 'p_known_after': 0.6}


# -- ordering ----------------------------------------------------------------

def test_lapse_penalty_and_ladder_run_after_bkt():
    db = _DB(card=dict(CARD), rpc=_default_rpcs())
    _svc(db).record_attempt_with_updates('u', 'ex-1', False)      # wrong answer on a review card: a lapse
    bkt = db.position('rpc', 'update_vocabulary_from_word_test')
    assert db.position('rpc', 'bkt_apply_lapse_penalty') > bkt
    assert db.position('rpc', 'ladder_apply_progress') > bkt
    assert db.position('exercise_attempts', 'insert') < bkt
    assert len(db.ops('user_flashcards', 'update')) == 1


def test_no_lapse_penalty_without_a_lapse():
    db = _DB(card=dict(CARD), rpc=_default_rpcs())
    _svc(db).record_attempt_with_updates('u', 'ex-1', True)
    assert db.rpcs('bkt_apply_lapse_penalty') == []


def test_best_effort_failures_do_not_fail_the_attempt():
    boom = RuntimeError('down')
    db = _DB(card=dict(CARD), rpc={'update_vocabulary_from_word_test': boom,
                                   'ladder_apply_progress': boom, 'credit_study_time': boom,
                                   'record_session_progress': boom})
    out = _svc(db).record_attempt_with_updates('u', 'ex-1', True, session_mode='maintenance')
    assert out == {'attempt_id': 'attempt-1', 'is_correct': True,
                   'exercise_type': 'definition_match', 'is_first_attempt': True}


# -- exercise counters ---------------------------------------------------------

def test_counter_write_is_conditional_on_the_count_that_was_read():
    db = _DB(rpc=_default_rpcs())
    _svc(db).record_attempt_with_updates('u', 'ex-1', True)
    (_, _, payload, filters), = db.ops('exercises', 'update')
    assert payload == {'attempt_count': 8, 'correct_count': 4}
    assert ('eq', 'attempt_count', 7) in filters


def test_wrong_answer_leaves_correct_count_alone():
    db = _DB(rpc=_default_rpcs())
    _svc(db).record_attempt_with_updates('u', 'ex-1', False)
    assert db.ops('exercises', 'update')[0][2] == {'attempt_count': 8}


def test_counter_write_retries_from_a_fresh_read_when_another_attempt_got_in():
    db = _DB(rpc=_default_rpcs(), counter_conflicts=1)
    _svc(db).record_attempt_with_updates('u', 'ex-1', True)
    first, second = db.ops('exercises', 'update')
    assert first[2]['attempt_count'] == 8 and second[2]['attempt_count'] == 9
    assert ('eq', 'attempt_count', 8) in second[3]


def test_counter_write_matches_a_null_count():
    db = _DB(exercise={'id': 'ex-1', 'exercise_type': 'x', 'word_sense_id': None,
                       'attempt_count': None, 'correct_count': None, 'language_id': 1})
    _svc(db).record_attempt_with_updates('u', 'ex-1', True)
    (_, _, payload, filters), = db.ops('exercises', 'update')
    assert payload == {'attempt_count': 1, 'correct_count': 1}
    assert ('is', 'attempt_count', 'null') in filters


def test_counter_write_gives_up_on_the_condition_eventually():
    db = _DB(rpc=_default_rpcs(), counter_conflicts=99)
    _svc(db).record_attempt_with_updates('u', 'ex-1', True)
    writes = db.ops('exercises', 'update')
    assert len(writes) == pss.COUNTER_WRITE_ATTEMPTS
    assert not any(f[1] == 'attempt_count' for f in writes[-1][3])


# -- RPC path ------------------------------------------------------------------

def _rpc_answer(**over):
    return {'attempt_id': 'attempt-1', 'is_first_attempt': True, 'exercise_type': 'definition_match',
            'sense_id': 42, 'language_id': 1, 'bkt_update': BKT, 'ladder': LADDER,
            'flashcard': dict(CARD), 'warnings': [], **over}


def test_rpc_is_not_called_unless_the_flag_is_set():
    db = _DB(rpc=_default_rpcs(record_exercise_attempt=_rpc_answer()))
    _svc(db).record_attempt_with_updates('u', 'ex-1', True)
    assert db.rpcs('record_exercise_attempt') == []


def test_rpc_path_returns_the_same_response_as_the_default_path(monkeypatch):
    kwargs = dict(time_taken_ms=9000, session_mode='acquisition', expected_seconds=20, is_tail=True,
                  exercise_context='gate')
    default = _svc(_DB(card=dict(CARD), rpc=_default_rpcs())).record_attempt_with_updates(
        'u', 'ex-1', True, **kwargs)

    monkeypatch.setenv(pss.ATTEMPT_RPC_ENV_FLAG, '1')
    db = _DB(rpc={'record_exercise_attempt': _rpc_answer()})
    via_rpc = _svc(db).record_attempt_with_updates('u', 'ex-1', True, **kwargs)
    assert via_rpc == default

    (params,) = db.rpcs('record_exercise_attempt')
    assert params == {
        'p_user_id': 'u', 'p_exercise_id': 'ex-1', 'p_is_correct': True, 'p_user_response': {},
        'p_time_taken_ms': 9000, 'p_language_id': None, 'p_credit_seconds': 9,
        'p_plan_kind': 'practice_acq', 'p_is_tail': True, 'p_exercise_context': 'gate'}
    # One RPC plus the FSRS write; no per-step table writes or RPCs.
    assert [e[:2] for e in db.log] == [('rpc', 'record_exercise_attempt'), ('user_flashcards', 'update')]


def test_rpc_path_applies_the_lapse_penalty_and_skips_plan_when_disabled(monkeypatch):
    monkeypatch.setenv(pss.ATTEMPT_RPC_ENV_FLAG, 'true')
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', False)
    db = _DB(rpc={'record_exercise_attempt': _rpc_answer(
        is_first_attempt=False, bkt_update=None, ladder={'skipped': 'retry'})})
    out = _svc(db).record_attempt_with_updates('u', 'ex-1', False, session_mode='maintenance')
    assert out == {'attempt_id': 'attempt-1', 'is_correct': False,
                   'exercise_type': 'definition_match', 'is_first_attempt': False}
    assert db.rpcs('record_exercise_attempt')[0]['p_plan_kind'] is None
    assert len(db.rpcs('bkt_apply_lapse_penalty')) == 1


def test_rpc_path_reports_an_unknown_exercise(monkeypatch):
    monkeypatch.setenv(pss.ATTEMPT_RPC_ENV_FLAG, '1')
    db = _DB(rpc={'record_exercise_attempt': {'error': 'exercise_not_found'}})
    assert _svc(db).record_attempt_with_updates('u', 'nope', True) == {'error': 'Exercise not found'}


def test_missing_function_falls_back_and_is_remembered(monkeypatch):
    monkeypatch.setenv(pss.ATTEMPT_RPC_ENV_FLAG, '1')
    missing = RuntimeError("{'code': 'PGRST202', 'message': 'Could not find the function'}")
    db = _DB(rpc=_default_rpcs(record_exercise_attempt=missing))
    svc = _svc(db)
    assert svc.record_attempt_with_updates('u', 'ex-1', True)['attempt_id'] == 'attempt-1'
    assert len(db.ops('exercise_attempts', 'insert')) == 1
    svc.record_attempt_with_updates('u', 'ex-1', True)
    assert len(db.rpcs('record_exercise_attempt')) == 1      # not asked again


def test_other_rpc_errors_are_not_retried_on_the_default_path(monkeypatch):
    monkeypatch.setenv(pss.ATTEMPT_RPC_ENV_FLAG, '1')
    db = _DB(rpc={'record_exercise_attempt': RuntimeError('statement timeout')})
    with pytest.raises(RuntimeError):
        _svc(db).record_attempt_with_updates('u', 'ex-1', True)
    assert db.ops('exercise_attempts', 'insert') == []
