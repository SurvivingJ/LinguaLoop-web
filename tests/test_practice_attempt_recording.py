"""Practice attempt write path: the record_exercise_attempt RPC is the only path.

The RPC (migrations/record_exercise_attempt.sql) does the first-attempt check
under an advisory lock, the attempt insert, the exercise counters, prestudy
follow-ups, BKT with frequency inference and the p_known capture, the ladder,
study time and plan progress in one transaction. Python sends the arguments,
rates the returned flashcard with FSRS, applies the lapse penalty, and reports
the ladder (with the new-word-drill restart). The SQL half is pinned at the end
of this file against the migration text.
"""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

from config import Config
from services import intro_drill
from services.practice_session_service import PracticeSessionService

CARD = {'id': 9, 'stability': 3.0, 'difficulty': 5.0, 'due_date': '2026-11-01',
        'last_review': '2026-10-20T08:00:00+00:00', 'reps': 4, 'lapses': 0, 'state': 'review'}
LADDER = {'family': 'meaning_recall', 'current_ring': 2, 'word_state': 'active',
          'gate_pending': None, 'stress_test_ready': False, 'demoted': False, 'is_lapse': False}
LADDER_KEYS = ('family', 'current_ring', 'word_state', 'gate_pending',
               'stress_test_ready', 'demoted', 'is_lapse')
BKT = {'out_sense_id': 42, 'out_p_known_before': 0.4, 'out_p_known_after': 0.6,
       'out_status': 'learning'}
SQL = (Path(__file__).resolve().parent.parent / 'migrations' / 'record_exercise_attempt.sql').read_text()


def _rpc_answer(**over):
    return {'attempt_id': 'attempt-1', 'is_first_attempt': True, 'exercise_type': 'definition_match',
            'sense_id': 42, 'language_id': 1, 'bkt_update': BKT, 'ladder': LADDER,
            'flashcard': dict(CARD), 'warnings': [], **over}


class _Q:
    def __init__(self, db, table):
        self.db, self.table, self.op, self.payload, self.filters = db, table, 'select', None, []

    def update(self, row):
        self.op, self.payload = 'update', row
        return self

    def eq(self, col, val):
        self.filters.append(('eq', col, val))
        return self

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        self.db.log.append((self.table, self.op, self.payload, tuple(self.filters)))
        return SimpleNamespace(data=[])


class _DB:
    """Records every table operation and RPC in order."""

    def __init__(self, rpc=None):
        self.rpc_data = {'record_exercise_attempt': _rpc_answer(), **(rpc or {})}
        self.log = []

    def table(self, name):
        return _Q(self, name)

    def rpc(self, name, params):
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
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', True)
    monkeypatch.setattr(intro_drill, 'restart_if_demoted', lambda *a: False)


def _svc(db):
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = db
    return s


def _record(db, *args, **kwargs):
    return _svc(db).record_attempt_with_updates('u', 'ex-1', *args, **kwargs)


# -- arguments and response ----------------------------------------------------

def test_arguments_and_response_shape():
    db = _DB()
    out = _record(db, True, time_taken_ms=9000, session_mode='acquisition', expected_seconds=20,
                  is_tail=True, exercise_context='gate')
    assert out == {
        'attempt_id': 'attempt-1', 'is_correct': True, 'exercise_type': 'definition_match',
        'is_first_attempt': True, 'bkt_update': BKT,
        'ladder': {k: LADDER[k] for k in LADDER_KEYS},
    }
    (params,) = db.rpcs('record_exercise_attempt')
    assert params == {
        'p_user_id': 'u', 'p_exercise_id': 'ex-1', 'p_is_correct': True, 'p_user_response': {},
        'p_time_taken_ms': 9000, 'p_language_id': None, 'p_credit_seconds': 9,
        'p_plan_kind': 'practice_acq', 'p_is_tail': True, 'p_exercise_context': 'gate'}
    # One RPC plus the FSRS write: no other table writes or RPCs.
    assert [e[:2] for e in db.log] == [('rpc', 'record_exercise_attempt'), ('user_flashcards', 'update')]


@pytest.mark.parametrize('first', [True, False])
def test_is_first_attempt_comes_from_the_rpc(first):
    db = _DB({'record_exercise_attempt': _rpc_answer(
        is_first_attempt=first, bkt_update=BKT if first else None)})
    out = _record(db, True)
    assert out['is_first_attempt'] is first
    assert ('bkt_update' in out) is first


def test_user_response_and_language_override_are_forwarded():
    db = _DB()
    _record(db, False, user_response={'choice': 2}, language_id=3)
    (params,) = db.rpcs('record_exercise_attempt')
    assert params['p_user_response'] == {'choice': 2} and params['p_language_id'] == 3
    assert params['p_is_correct'] is False


# -- plan progress and study time ----------------------------------------------

@pytest.mark.parametrize('mode, kind', [('acquisition', 'practice_acq'),
                                        ('maintenance', 'practice_maint'),
                                        (None, None)])
def test_plan_kind_follows_the_session_mode(mode, kind):
    db = _DB()
    _record(db, True, session_mode=mode)
    assert db.rpcs('record_exercise_attempt')[0]['p_plan_kind'] == kind


def test_no_plan_progress_when_study_plan_is_disabled(monkeypatch):
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', False)
    db = _DB()
    _record(db, True, session_mode='acquisition')
    assert db.rpcs('record_exercise_attempt')[0]['p_plan_kind'] is None


@pytest.mark.parametrize('ms, expected, secs', [
    (12_400, None, 12), (20_000, None, 20),
    (None, 25, 25), (0, 25, 25), (900_000, 25, 25),     # estimate fallback
    (None, 9999, 300),                                    # estimate clamped at the practice cap
])
def test_credit_seconds(ms, expected, secs):
    db = _DB()
    _record(db, True, time_taken_ms=ms, expected_seconds=expected)
    assert db.rpcs('record_exercise_attempt')[0]['p_credit_seconds'] == secs


def test_tail_flag_defaults_to_false():
    db = _DB()
    _record(db, True, session_mode='acquisition')
    assert db.rpcs('record_exercise_attempt')[0]['p_is_tail'] is False


# -- FSRS and the lapse penalty --------------------------------------------------

def test_lapse_penalty_follows_the_rpc_and_the_fsrs_write():
    db = _DB()
    _record(db, False)              # wrong answer on a review card: a lapse
    rpc = db.position('rpc', 'record_exercise_attempt')
    fsrs = db.position('user_flashcards', 'update')
    assert rpc < fsrs < db.position('rpc', 'bkt_apply_lapse_penalty')
    assert db.rpcs('bkt_apply_lapse_penalty') == [{'p_user_id': 'u', 'p_sense_id': 42}]
    assert len(db.ops('user_flashcards', 'update')) == 1


def test_no_lapse_penalty_without_a_lapse():
    db = _DB()
    _record(db, True)
    assert len(db.ops('user_flashcards', 'update')) == 1
    assert db.rpcs('bkt_apply_lapse_penalty') == []


def test_no_flashcard_means_no_fsrs_write():
    db = _DB({'record_exercise_attempt': _rpc_answer(flashcard=None)})
    out = _record(db, False)
    assert db.ops('user_flashcards', 'update') == [] and db.rpcs('bkt_apply_lapse_penalty') == []
    assert out['ladder']['current_ring'] == 2


def test_fsrs_failure_does_not_fail_the_attempt():
    db = _DB()

    def boom(*_a, **_k):
        raise RuntimeError('fsrs write down')
    db.table = boom
    out = _record(db, False)
    assert out['attempt_id'] == 'attempt-1'
    assert db.rpcs('bkt_apply_lapse_penalty') == []


# -- untracked exercises, exercise_type NULL --------------------------------------

def test_exercise_without_a_sense_reports_no_ladder_and_rates_no_card(monkeypatch):
    seen = []
    db = _DB({'record_exercise_attempt': _rpc_answer(
        sense_id=None, bkt_update=None, ladder=None, flashcard=None)})
    monkeypatch.setattr(intro_drill, 'restart_if_demoted', lambda *a: seen.append(a) or True)
    out = _record(db, True)
    assert out == {'attempt_id': 'attempt-1', 'is_correct': True,
                   'exercise_type': 'definition_match', 'is_first_attempt': True}
    assert [e[:2] for e in db.log] == [('rpc', 'record_exercise_attempt')]
    assert seen == []


def test_null_exercise_type_is_reported_as_none():
    db = _DB({'record_exercise_attempt': _rpc_answer(exercise_type=None)})
    assert _record(db, True)['exercise_type'] is None


# -- ladder and the new-word-drill restart ---------------------------------------

def test_skipped_ladder_is_not_reported():
    db = _DB({'record_exercise_attempt': _rpc_answer(ladder={'skipped': 'retry'})})
    assert 'ladder' not in _record(db, True)


def test_ring2_demotion_restarts_the_drill_with_the_rpc_language(monkeypatch):
    seen = []
    monkeypatch.setattr(intro_drill, 'restart_if_demoted',
                        lambda db, u, sid, lang, ladder: seen.append((u, sid, lang, ladder['demoted'])) or True)
    db = _DB({'record_exercise_attempt': _rpc_answer(
        language_id=3, ladder={'current_ring': 1, 'demoted': True, 'word_state': 'active'})})
    out = _record(db, False)
    assert seen == [('u', 42, 3, True)]
    assert out['ladder']['intro_restart'] is True and out['ladder']['demoted'] is True


def test_drill_restart_failure_is_non_fatal(monkeypatch):
    def boom(*_a):
        raise RuntimeError('down')
    monkeypatch.setattr(intro_drill, 'restart_if_demoted', boom)
    out = _record(_DB(), True)
    assert out['ladder']['current_ring'] == 2 and 'intro_restart' not in out['ladder']


# -- best-effort steps, errors ---------------------------------------------------

def test_step_warnings_do_not_fail_the_attempt(caplog):
    warnings = [{'step': s, 'error': 'down'} for s in
                ('bkt', 'ladder', 'study_time', 'session_progress', 'prestudy_followups')]
    db = _DB({'record_exercise_attempt': _rpc_answer(
        bkt_update=None, ladder=None, flashcard=None, warnings=warnings)})
    with caplog.at_level('INFO'):
        out = _record(db, True, session_mode='maintenance')
    assert out == {'attempt_id': 'attempt-1', 'is_correct': True,
                   'exercise_type': 'definition_match', 'is_first_attempt': True}
    assert sum('failed (non-fatal)' in r.getMessage() for r in caplog.records) == 5


def test_unknown_exercise():
    db = _DB({'record_exercise_attempt': {'error': 'exercise_not_found'}})
    assert _record(db, True) == {'error': 'Exercise not found'}


def test_a_single_row_list_answer_is_unwrapped():
    db = _DB({'record_exercise_attempt': [_rpc_answer()]})
    assert _record(db, True)['attempt_id'] == 'attempt-1'


@pytest.mark.parametrize('answer', [None, [], 'x'])
def test_a_malformed_answer_raises(answer):
    with pytest.raises(RuntimeError):
        _record(_DB({'record_exercise_attempt': answer}), True)


@pytest.mark.parametrize('exc', [
    RuntimeError('statement timeout'),
    RuntimeError("{'code': 'PGRST202', 'message': 'Could not find the function'}"),
])
def test_rpc_errors_propagate_and_nothing_else_is_written(exc):
    db = _DB({'record_exercise_attempt': exc})
    with pytest.raises(RuntimeError):
        _record(db, True)
    assert [e[:2] for e in db.log] == [('rpc', 'record_exercise_attempt')]


@pytest.mark.parametrize('value', ['0', '1', 'false', 'true', ''])
def test_the_retired_env_flag_is_ignored(monkeypatch, value):
    monkeypatch.setenv('PRACTICE_ATTEMPT_RPC_ENABLED', value)
    db = _DB()
    assert _record(db, True)['attempt_id'] == 'attempt-1'
    assert len(db.rpcs('record_exercise_attempt')) == 1


def test_route_turns_an_rpc_failure_into_the_attempt_failure_envelope(monkeypatch):
    import middleware.auth as auth
    import routes.practice as practice
    import services.practice_session_service as pss
    from web.errors import register_error_handlers

    db = _DB({'record_exercise_attempt': RuntimeError('statement timeout')})
    monkeypatch.setattr(auth, '_authenticate', lambda token: ({'sub': 'user-1'}, None))
    monkeypatch.setattr(pss, 'get_practice_session_service', lambda: _svc(db))
    monkeypatch.setattr(practice, '_grade_typed_if_needed', lambda eid, data: None)
    app = Flask(__name__)
    register_error_handlers(app)
    app.register_blueprint(practice.practice_bp, url_prefix='/api/practice')
    client = app.test_client()
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer fake'
    resp = client.post('/api/practice/attempt', json={'exercise_id': 'ex-1', 'is_correct': True})
    assert resp.status_code == 500
    body = resp.get_json()
    assert body == {'status': 'error', 'error': 'Failed to submit attempt', 'error_code': 'SERVER_ERROR'}


# -- the SQL half (migrations/record_exercise_attempt.sql) -------------------------

def _norm(text):
    return re.sub(r'\s+', ' ', text)


def test_sql_serialises_the_first_attempt_check():
    sql = _norm(SQL)
    lock = sql.index('pg_advisory_xact_lock')
    assert lock < sql.index('v_first := NOT EXISTS') < sql.index('INSERT INTO public.exercise_attempts')
    assert 'is_first_attempt, created_at) VALUES' in sql and 'v_sense, v_first, now()' in sql


def test_sql_increments_the_counters_atomically():
    sql = _norm(SQL)
    assert 'SET attempt_count = COALESCE(attempt_count, 0) + 1' in sql
    assert ('correct_count = CASE WHEN p_is_correct THEN COALESCE(correct_count, 0) + 1 '
            'ELSE correct_count END') in sql


def test_sql_applies_bkt_inference_and_capture_on_first_attempts_only():
    sql = _norm(SQL)
    gate = sql.index('IF v_sense IS NOT NULL AND v_lang IS NOT NULL AND v_first THEN')
    for step in ('update_vocabulary_from_word_test( p_user_id, v_sense, p_is_correct, v_lang, v_type)',
                 'IF v_after >= 0.90 AND v_before < 0.90 THEN',
                 'bkt_infer_from_frequency( p_user_id, v_lang, v_sense, v_after)',
                 'SET p_known_before = v_before, p_known_after = v_after'):
        assert sql.index(step) > gate, step


def test_sql_prestudy_ladder_study_time_and_plan_progress():
    sql = _norm(SQL)
    assert ('UPDATE public.prestudy_followups SET completed_at = now() WHERE user_id = p_user_id '
            'AND sense_id = v_sense AND completed_at IS NULL') in sql
    assert ("WHEN p_exercise_context IN ('standard', 'gate', 'stress_test') "
            "THEN p_exercise_context ELSE 'standard' END") in sql
    assert ("credit_study_time( p_user_id, v_lang, 'practice', v_secs, 'exercise_attempts', "
            "v_attempt_id::text)") in sql
    assert "IF v_lang IS NOT NULL AND p_plan_kind IN ('practice_acq', 'practice_maint') THEN" in sql
    assert "p_sense_id => CASE WHEN p_plan_kind = 'practice_acq' THEN v_sense::bigint END" in sql
    assert 'p_delta_seconds => v_secs' in sql and 'p_delta_count => 0' in sql


def test_sql_returns_the_flashcard_only_for_tracked_senses():
    sql = _norm(SQL)
    gate = sql.rindex('IF v_sense IS NOT NULL AND v_lang IS NOT NULL THEN')
    assert sql.index('FROM public.user_flashcards uf', gate) > gate
    for key in ('attempt_id', 'is_first_attempt', 'exercise_type', 'sense_id', 'language_id',
                'bkt_update', 'ladder', 'flashcard', 'warnings'):
        assert f"'{key}'," in sql
