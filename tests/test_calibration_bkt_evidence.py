"""TASK-873 -- calibration writes BKT evidence at /end (definition mode only).

Pins ``calibration_service.apply_calibration_to_vocabulary`` and its wiring in
``end_session``, plus the ``side_effects`` keyword on
``VocabularyKnowledgeService.update_from_word_tests_batch``:

  * definition mode sends the answered anchors once, with ``side_effects=False``;
  * pronunciation mode never does; a second /end does not (``bkt_applied_at``);
  * the predicate ``answered_at IS NOT NULL AND is_correct IS NOT NULL``: an
    explicit skip ("I don't know") is a wrong answer, an unanswered item is
    ignored;
  * a failure resets the marker and never fails /end;
  * ``side_effects=False`` skips flashcards / ladder seeding / frequency
    inference while the default keeps all three (dictation unchanged).

The exercise-type equality (bkt_update_exercise 'definition_match' ==
bkt_update_word_test) is a SQL fact; it is pinned in
tests/sql/test_session_budget_settings.sql.
"""

import logging
from unittest.mock import MagicMock

import pytest

from services import calibration_service as cs
from services.vocabulary.knowledge_service import VocabularyKnowledgeService

USER = 'user-1'
POOLED = {'ability_zipf': 5.0, 'ability_se': 0.2, 'items_answered': 60,
          'sessions_pooled': 1, 'bands': []}


def _session(mode='definition'):
    return {'id': 'session-1', 'word_language_id': 3, 'mode': mode}


class _Chain:
    def __init__(self, db, table):
        self.db, self.table, self.op, self.payload, self.filters = db, table, 'select', None, []

    def update(self, payload):
        self.op, self.payload = 'update', payload
        return self

    def select(self, *_a, **_k):
        return self

    @property
    def not_(self):
        return self

    def is_(self, col, val):
        self.filters.append(('is', col, val))
        return self

    def eq(self, col, val):
        self.filters.append(('eq', col, val))
        return self

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        return self.db.run(self)


class FakeDB:
    """calibration_sessions claim semantics + canned calibration_responses."""

    def __init__(self, responses=(), applied=False, claim_fails=False):
        self.responses = list(responses)
        self.applied = applied
        self.updates = []
        self.claim_fails = claim_fails

    def table(self, name):
        return _Chain(self, name)

    def rpc(self, name, args):
        return _Chain(self, 'rpc:' + name)

    def run(self, q):
        if q.table == 'calibration_sessions' and q.op == 'update':
            self.updates.append(dict(q.payload))
            if 'bkt_applied_at' in q.payload and q.payload['bkt_applied_at'] == 'now()':
                if self.claim_fails:
                    raise RuntimeError('column bkt_applied_at does not exist')
                if self.applied:
                    return MagicMock(data=[])
                self.applied = True
                return MagicMock(data=[{'id': 'session-1'}])
            if q.payload.get('bkt_applied_at', 1) is None:
                self.applied = False
            return MagicMock(data=[{'id': 'session-1'}])
        if q.table == 'calibration_responses':
            return MagicMock(data=[r for r in self.responses
                                   if r.get('answered_at') is not None
                                   and r.get('is_correct') is not None])
        return MagicMock(data=[])


@pytest.fixture
def batch(monkeypatch):
    """Capture update_from_word_tests_batch calls; default to success."""
    calls = []

    def fake(self, user_id, language_id, results, side_effects=True):
        calls.append({'user_id': user_id, 'language_id': language_id,
                      'results': results, 'side_effects': side_effects})
        return fake.rows

    fake.rows = [{'out_sense_id': 1}]
    monkeypatch.setattr(VocabularyKnowledgeService, 'update_from_word_tests_batch', fake)
    monkeypatch.setattr(VocabularyKnowledgeService, '__init__', lambda self, db=None: None)
    batch_ctl = type('Ctl', (), {'calls': calls, 'fake': fake})
    return batch_ctl


def _use(monkeypatch, db):
    monkeypatch.setattr(cs, 'get_supabase_admin', lambda: db)
    return db


def _resp(sense, correct, answered='2026-10-13T00:00:00Z'):
    return {'anchor_sense_id': sense, 'is_correct': correct, 'answered_at': answered}


# ---------------------------------------------------------------------------
# apply_calibration_to_vocabulary
# ---------------------------------------------------------------------------

def test_definition_mode_sends_answered_anchors_once_without_side_effects(monkeypatch, batch):
    db = _use(monkeypatch, FakeDB([_resp(11, True), _resp(12, False)]))
    out = cs.apply_calibration_to_vocabulary(USER, _session())
    assert out == {'sent': 2}
    assert len(batch.calls) == 1
    call = batch.calls[0]
    assert call['side_effects'] is False
    assert call['language_id'] == 3
    assert call['results'] == [{'sense_id': 11, 'is_correct': True},
                               {'sense_id': 12, 'is_correct': False}]
    assert db.applied is True


def test_explicit_skip_is_wrong_and_unanswered_items_are_ignored(monkeypatch, batch):
    # A skip: chosen_sense_id NULL, is_correct False, answered_at set.
    rows = [_resp(21, False),
            {'anchor_sense_id': 22, 'is_correct': None, 'answered_at': None},
            {'anchor_sense_id': 23, 'is_correct': None, 'answered_at': '2026-10-13T00:00:00Z'},
            {'anchor_sense_id': 24, 'is_correct': True, 'answered_at': None}]
    _use(monkeypatch, FakeDB(rows))
    cs.apply_calibration_to_vocabulary(USER, _session())
    assert batch.calls[0]['results'] == [{'sense_id': 21, 'is_correct': False}]


def test_pronunciation_mode_never_calls_the_batch(monkeypatch, batch):
    db = _use(monkeypatch, FakeDB([_resp(11, False)]))
    assert cs.apply_calibration_to_vocabulary(USER, _session('pronunciation')) is None
    assert batch.calls == []
    assert db.updates == []          # not even the claim


def test_a_second_end_is_a_no_op(monkeypatch, batch):
    _use(monkeypatch, FakeDB([_resp(11, False)]))
    cs.apply_calibration_to_vocabulary(USER, _session())
    assert cs.apply_calibration_to_vocabulary(USER, _session()) is None
    assert len(batch.calls) == 1


def test_a_batch_failure_resets_the_marker_and_does_not_raise(monkeypatch, batch, caplog):
    batch.fake.rows = []             # the wrapper swallows errors and returns []
    db = _use(monkeypatch, FakeDB([_resp(11, False)]))
    with caplog.at_level(logging.WARNING):
        assert cs.apply_calibration_to_vocabulary(USER, _session()) is None
    assert db.applied is False       # reset: a retried /end can try again
    assert any('not written' in r.message for r in caplog.records)
    # ...and the retry now succeeds.
    batch.fake.rows = [{'out_sense_id': 11}]
    assert cs.apply_calibration_to_vocabulary(USER, _session()) == {'sent': 1}


def test_an_unmigrated_column_is_non_fatal(monkeypatch, batch):
    _use(monkeypatch, FakeDB([_resp(11, False)], claim_fails=True))
    assert cs.apply_calibration_to_vocabulary(USER, _session()) is None
    assert batch.calls == []


def test_a_session_with_no_answered_anchors_skips_the_rpc(monkeypatch, batch):
    _use(monkeypatch, FakeDB([]))
    assert cs.apply_calibration_to_vocabulary(USER, _session()) == {'sent': 0}
    assert batch.calls == []


# ---------------------------------------------------------------------------
# end_session wiring
# ---------------------------------------------------------------------------

@pytest.fixture
def wired(monkeypatch):
    applied = []
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = {'decisions': []}
    monkeypatch.setattr(cs, 'get_supabase_admin', lambda: db)
    monkeypatch.setattr(cs, 'ability', lambda u, s, fit=True: {'answered': 60})
    monkeypatch.setattr(cs, 'write_calibration_state', lambda *a, **k: dict(POOLED))
    monkeypatch.setattr(cs, 'apply_calibration_to_vocabulary',
                        lambda user_id, session: applied.append(session['mode']))
    return applied


def test_end_session_applies_evidence_in_definition_mode(wired):
    cs.end_session(USER, _session('definition'))
    assert wired == ['definition']


def test_end_session_hook_is_gated_to_definition_mode(wired):
    cs.end_session(USER, _session('pronunciation'))
    assert wired == []


# ---------------------------------------------------------------------------
# side_effects on the knowledge-service wrapper
# ---------------------------------------------------------------------------

def _service_with_rpc(rows):
    svc = VocabularyKnowledgeService.__new__(VocabularyKnowledgeService)
    svc.db = MagicMock()
    svc.db.rpc.return_value.execute.return_value.data = rows
    for name in ('_auto_create_flashcards', '_seed_ladder_for_new_words',
                 '_trigger_frequency_inference'):
        setattr(svc, name, MagicMock())
    return svc


ROWS = [{'out_sense_id': 1, 'out_p_known_before': 0.3, 'out_p_known_after': 0.1,
         'out_status': 'learning'}]


def test_side_effects_false_skips_the_three_helpers():
    svc = _service_with_rpc(ROWS)
    out = svc.update_from_word_tests_batch(
        USER, 3, [{'sense_id': 1, 'is_correct': False}], side_effects=False)
    assert out == ROWS
    svc.db.rpc.assert_called_once()
    svc._auto_create_flashcards.assert_not_called()
    svc._seed_ladder_for_new_words.assert_not_called()
    svc._trigger_frequency_inference.assert_not_called()


def test_default_keeps_the_side_effects_for_dictation():
    svc = _service_with_rpc(ROWS)
    svc.update_from_word_tests_batch(USER, 3, [{'sense_id': 1, 'is_correct': True}])
    svc._auto_create_flashcards.assert_called_once()
    svc._seed_ladder_for_new_words.assert_called_once()
    svc._trigger_frequency_inference.assert_called_once()
