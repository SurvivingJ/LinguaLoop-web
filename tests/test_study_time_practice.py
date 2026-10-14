"""TASK-890: every vocabulary practice attempt credits the study-time ledger."""

from types import SimpleNamespace

import pytest

from config import Config
from services.practice_session_service import PracticeSessionService
from services.vocabulary.knowledge_service import VocabularyKnowledgeService


class _Q:
    def __init__(self, data=None, sink=None, name=None):
        self._data, self._sink, self._name = data, sink, name

    def __getattr__(self, _n):
        return lambda *a, **k: self

    def insert(self, row):
        self._data = [{'id': 'attempt-1'}]
        return self

    def execute(self):
        return SimpleNamespace(data=self._data)


class _DB:
    def __init__(self, exercise, credit_raises=False):
        self.exercise, self.rpcs, self.seen = exercise, [], set()
        self.credit_raises = credit_raises

    def table(self, name):
        return _Q(self.exercise) if name == 'exercises' else _Q([], None, name)

    def rpc(self, name, args):
        self.rpcs.append((name, args))
        if name == 'credit_study_time':
            if self.credit_raises:
                raise RuntimeError('ledger down')
            key = (args['p_kind'], args['p_source_table'], args['p_source_id'])
            data = key not in self.seen
            self.seen.add(key)
            return _Q(data)
        return _Q(None)

    def credits(self):
        return [a for n, a in self.rpcs if n == 'credit_study_time']

    def progress(self):
        return [a for n, a in self.rpcs if n == 'record_session_progress']


@pytest.fixture
def make_svc(monkeypatch):
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', True)
    monkeypatch.setattr(VocabularyKnowledgeService, '__init__', lambda self, db=None: None)
    monkeypatch.setattr(VocabularyKnowledgeService, 'update_from_word_test', lambda self, **k: None)
    monkeypatch.setattr(PracticeSessionService, '_update_fsrs_for_exercise', lambda *a, **k: None)

    def _make(**kw):
        s = PracticeSessionService.__new__(PracticeSessionService)
        s.db = _DB({'id': 'ex-1', 'exercise_type': 'definition_match', 'word_sense_id': 42,
                    'attempt_count': 0, 'correct_count': 0, 'language_id': 1}, **kw)
        return s
    return _make


def test_attempt_without_session_context_credits_ledger(make_svc):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=12_400)
    (c,) = svc.db.credits()
    assert c == {'p_user_id': 'u', 'p_language_id': 1, 'p_kind': 'practice', 'p_seconds': 12,
                 'p_source_table': 'exercise_attempts', 'p_source_id': 'attempt-1'}
    assert svc.db.progress() == []


def test_attempt_with_session_credits_both_and_progress_unchanged(make_svc):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=20_000,
                                    session_mode='acquisition', language_id=1)
    (c,) = svc.db.credits()
    (p,) = svc.db.progress()
    assert c['p_seconds'] == 20 and p['p_delta_seconds'] == 20
    assert p['p_kind'] == 'practice_acq' and p['p_delta_count'] == 0 and p['p_sense_id'] == 42


def test_credits_even_when_study_plan_disabled(make_svc, monkeypatch):
    monkeypatch.setattr(Config, 'STUDY_PLAN_ENABLED', False)
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=8_000, session_mode='acquisition')
    assert len(svc.db.credits()) == 1 and svc.db.progress() == []


@pytest.mark.parametrize('ms', [None, 0, 900_000])
def test_estimate_fallback_seconds_are_credited(make_svc, ms):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=ms, expected_seconds=25)
    assert svc.db.credits()[0]['p_seconds'] == 25


def test_estimate_clamped_at_practice_cap(make_svc):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=None, expected_seconds=9999)
    assert svc.db.credits()[0]['p_seconds'] == 300


def test_same_attempt_id_credits_once(make_svc):
    svc = make_svc()
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=5_000)
    svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=5_000)  # same fake attempt id
    assert len(svc.db.seen) == 1


def test_credit_failure_never_fails_attempt(make_svc):
    svc = make_svc(credit_raises=True)
    out = svc.record_attempt_with_updates('u', 'ex-1', True, time_taken_ms=5_000,
                                          session_mode='maintenance', language_id=1)
    assert out['attempt_id'] == 'attempt-1' and len(svc.db.progress()) == 1
