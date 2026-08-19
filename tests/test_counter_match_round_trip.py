"""
`counter_match` from generation through to a recorded ladder attempt (TASK-530).

test_deterministic_generators.py already checks that the builder produces a
well-formed item. It stops there. This carries the item the builder actually
emitted into LadderService.record_attempt and asserts on what reaches the
`ladder_record_attempt` RPC — the join the 2026-08-08 session flagged as
untested end to end for its Mandarin twin.

The join is where the interesting failures live: an item can be perfectly built
and still be recorded under the wrong type_code or a null ladder_level, in which
case the ladder advances the wrong family, or nothing at all, and no test that
looks only at `content` would notice.
"""

import pytest

from services.vocabulary_ladder import deterministic as det
from services.vocabulary_ladder.ladder_service import LadderService

from tests.test_deterministic_generators import (
    install_dictionary,
    make_core,
    make_ctx,
)

JA = 3

COUNTERS = [
    (1, '本', 'ほん', 'long thin objects', 10, 'long-thin', 1),
    (2, '枚', 'まい', 'flat objects',      20, 'flat',      1),
    (3, '匹', 'ひき', 'small animals',     30, 'animals',   1),
    (4, '台', 'だい', 'machines',          40, 'machines',  1),
    (5, '冊', 'さつ', 'bound volumes',     20, 'flat',      2),
]


class _RecordingDB:
    """Captures the ladder_record_attempt call and replays a canned envelope."""

    def __init__(self, envelope=None, raises=None):
        self.calls = []
        self._envelope = envelope if envelope is not None else {
            'is_correct': True,
            'family': 'counter',
            'family_confidence': 0.62,
            'current_ring': 2,
            'word_state': 'learning',
            'requeue': False,
        }
        self._raises = raises

    def rpc(self, name, params):
        self.calls.append((name, params))
        db = self

        class _Q:
            def execute(self_inner):
                if db._raises:
                    raise db._raises
                return type('R', (), {'data': db._envelope})()

        return _Q()


def _build_counter_item(lemma='鉛筆', pairs=(('鉛筆', 1),)):
    install_dictionary('counter', JA, COUNTERS, list(pairs))
    ctx = make_ctx(db=object(), language_id=JA, lemma=lemma,
                   core=make_core(pronunciation='えんぴつ'),
                   pronunciation='えんぴつ')
    items, skips = det.generate(ctx, type_codes={'counter_match'})
    return items, skips, ctx


# ---------------------------------------------------------------------------
# Generation half
# ---------------------------------------------------------------------------

def test_builder_emits_one_usable_item():
    items, skips, _ = _build_counter_item()
    assert len(items) == 1, skips
    content = items[0].content
    assert content['correct_answer'] == '本'
    assert content['correct_answer'] in content['options']
    assert len(content['options']) == 4
    assert len(set(content['options'])) == 4, 'a duplicated option is a free item'


def test_item_is_tagged_as_ladder_level_four():
    """L4 is what routes it into the ladder; a null level records nothing."""
    items, _, _ = _build_counter_item()
    assert items[0].ladder_level == 4
    assert items[0].type_code == 'counter_match'


# ---------------------------------------------------------------------------
# The round trip
# ---------------------------------------------------------------------------

def test_attempt_reaches_the_rpc_with_the_item_it_was_built_from():
    items, _, ctx = _build_counter_item()
    item = items[0]
    db = _RecordingDB()

    result = LadderService(db).record_attempt(
        user_id='11111111-1111-1111-1111-111111111111',
        sense_id=ctx.sense_id,
        exercise_id='22222222-2222-2222-2222-222222222222',
        is_correct=True,
        is_first_attempt=True,
        time_taken_ms=4200,
        language_id=JA,
        exercise_type=item.type_code,
        ladder_level=item.ladder_level,
    )

    assert len(db.calls) == 1
    name, params = db.calls[0]
    assert name == 'ladder_record_attempt'
    assert params['p_exercise_type'] == 'counter_match'
    assert params['p_ladder_level'] == 4
    assert params['p_language_id'] == JA
    assert params['p_sense_id'] == ctx.sense_id
    assert params['p_is_correct'] is True
    assert params['p_is_first_attempt'] is True
    assert params['p_time_taken_ms'] == 4200

    assert result['family'] == 'counter'
    assert result['requeue'] is False


def test_a_wrong_first_attempt_requeues():
    items, _, ctx = _build_counter_item()
    db = _RecordingDB(envelope={'is_correct': False, 'requeue': True,
                                'family': 'counter'})

    result = LadderService(db).record_attempt(
        user_id='11111111-1111-1111-1111-111111111111',
        sense_id=ctx.sense_id,
        exercise_id='22222222-2222-2222-2222-222222222222',
        is_correct=False,
        is_first_attempt=True,
        language_id=JA,
        exercise_type=items[0].type_code,
        ladder_level=items[0].ladder_level,
    )

    assert db.calls[0][1]['p_is_correct'] is False
    assert result['requeue'] is True


def test_an_rpc_outage_still_returns_a_verdict():
    """The learner answered; losing the ladder write must not lose the answer."""
    items, _, ctx = _build_counter_item()
    db = _RecordingDB(raises=RuntimeError('connection reset'))

    result = LadderService(db).record_attempt(
        user_id='11111111-1111-1111-1111-111111111111',
        sense_id=ctx.sense_id,
        exercise_id='22222222-2222-2222-2222-222222222222',
        is_correct=False,
        is_first_attempt=True,
        language_id=JA,
        exercise_type=items[0].type_code,
        ladder_level=items[0].ladder_level,
    )

    assert result['is_correct'] is False
    assert result['requeue'] is True
    assert 'error' in result


# ---------------------------------------------------------------------------
# Multi-acceptable answers survive the whole trip
# ---------------------------------------------------------------------------

def test_every_acceptable_counter_survives_to_the_item():
    """兎 takes both 匹 and 羽. Dropping one teaches a falsehood."""
    items, skips, _ = _build_counter_item(
        lemma='鉛筆', pairs=(('鉛筆', 1), ('鉛筆', 5)))
    assert len(items) == 1, skips
    assert set(items[0].content['accepted_answers']) == {'本', '冊'}


def test_a_noun_outside_the_dictionary_emits_nothing_and_says_why():
    items, skips, _ = _build_counter_item(lemma='猫', pairs=(('鉛筆', 1),))
    assert items == []
    assert any('counter dictionary' in s.reason for s in skips)
