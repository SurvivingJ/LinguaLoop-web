"""TASK-533 — the timed_speed_round serve-time composer.

No Supabase: the composer's two queries are driven by a stub client that
records the filters it was given, so the tests can assert on *what was asked
for* as well as on what came back. That matters here — the acceptance
criterion is a negative one ("non-mastered senses never appear"), and a test
that only inspected the output would pass against a composer that filtered
nothing but happened to be handed clean data.
"""

import pytest

from services.vocabulary_ladder import speed_round
from services.vocabulary_ladder.speed_round import (
    MASTERED, MAX_BATTERY, MIN_BATTERY, RECOGNITION_LEVELS,
    UPDATES_FAMILY_CONFIDENCE, Battery, SpeedRoundComposer,
)

LANG_ZH, LANG_EN = 1, 2


# ---------------------------------------------------------------------------
# Stub client
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _StubTable:
    """Records every filter applied, then returns the canned rows."""

    def __init__(self, rows, log, raises=False):
        self._rows = rows
        self._log = log
        self._raises = raises
        self._not = False

    def select(self, *args, **_kwargs):
        self._log.append(('select', args[0] if args else ''))
        return self

    def eq(self, column, value):
        self._log.append(('eq', column, value))
        return self

    def in_(self, column, values):
        self._log.append(('in', column, tuple(values)))
        return self

    def is_(self, column, value):
        self._log.append(('not_is' if self._not else 'is', column, value))
        self._not = False
        return self

    @property
    def not_(self):
        self._not = True
        return self

    def execute(self):
        if self._raises:
            raise RuntimeError('connection reset')
        return _Resp(self._rows)


class _StubDB:
    def __init__(self, ladder_rows=None, exercise_rows=None, raises=False):
        self.ladder_rows = ladder_rows or []
        self.exercise_rows = exercise_rows if exercise_rows is not None else []
        self.raises = raises
        self.calls: dict[str, list] = {'user_word_ladder': [], 'exercises': []}

    def table(self, name):
        rows = self.ladder_rows if name == 'user_word_ladder' else self.exercise_rows
        return _StubTable(rows, self.calls.setdefault(name, []), self.raises)


def _ladder(*sense_ids):
    return [{'sense_id': sid} for sid in sense_ids]


def _exercises(sense_ids, per_sense=1, level=2, exercise_type='definition_match'):
    rows = []
    for sid in sense_ids:
        for n in range(per_sense):
            rows.append({
                'id': f'ex-{sid}-{n}',
                'exercise_type': exercise_type,
                'content': {'word': f'w{sid}', 'options': ['a', 'b', 'c', 'd']},
                'ladder_level': level,
                'word_sense_id': sid,
                'complexity_tier': 'T2',
            })
    return rows


@pytest.fixture(autouse=True)
def _stable_shuffle(monkeypatch):
    """Determinism: the composer shuffles, the assertions should not care."""
    monkeypatch.setattr(speed_round.random, 'shuffle', lambda seq: None)
    monkeypatch.setattr(speed_round.random, 'sample', lambda seq, k: list(seq)[:k])


# ---------------------------------------------------------------------------
# The mastered-only restriction
# ---------------------------------------------------------------------------

def test_the_pool_query_filters_on_mastered_and_language():
    """AC: 'batteries only from word_state=mastered senses'.

    Asserted on the query rather than only on the result — a composer that
    filtered nothing would still pass an output-only test given clean rows.
    """
    senses = list(range(1, 21))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))

    SpeedRoundComposer(db).compose('user-1', LANG_EN)

    ladder_filters = db.calls['user_word_ladder']
    assert ('eq', 'word_state', MASTERED) in ladder_filters
    assert ('eq', 'user_id', 'user-1') in ladder_filters
    # A learner studying two languages must not get a battery mixing both.
    assert ('eq', 'dim_word_senses.dim_vocabulary.language_id', LANG_EN) in ladder_filters


def test_non_mastered_senses_never_reach_the_battery():
    """AC verification: 'non-mastered senses never appear'.

    The ladder query returns only the mastered senses; the exercise query is
    then constrained to exactly those ids, so an unmastered sense has no path
    into the battery even though items exist for it.
    """
    mastered = list(range(1, 21))
    unmastered = [999]
    db = _StubDB(
        ladder_rows=_ladder(*mastered),
        # Items exist for the unmastered sense too — they must not be asked for.
        exercise_rows=_exercises(mastered + unmastered),
    )

    battery = SpeedRoundComposer(db).compose('user-1', LANG_EN)

    requested = [c for c in db.calls['exercises'] if c[0] == 'in' and c[1] == 'word_sense_id']
    assert requested, 'the item query must constrain word_sense_id'
    assert 999 not in requested[0][2]
    assert all(item['sense_id'] in mastered for item in battery.items)


def test_only_recognition_levels_are_requested():
    """L4+ ask the learner to produce something, which a clock cannot fairly test."""
    senses = list(range(1, 21))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))

    SpeedRoundComposer(db).compose('user-1', LANG_EN)

    levels = [c for c in db.calls['exercises'] if c[0] == 'in' and c[1] == 'ladder_level']
    assert levels and levels[0][2] == RECOGNITION_LEVELS


def test_legacy_items_are_excluded():
    """A battery must not surface content the judges never saw."""
    senses = list(range(1, 21))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))

    SpeedRoundComposer(db).compose('user-1', LANG_EN)

    assert ('not_is', 'word_asset_id', 'null') in db.calls['exercises']


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------

def test_a_mastered_learner_gets_a_battery():
    senses = list(range(1, 21))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))

    battery = SpeedRoundComposer(db).compose('user-1', LANG_EN)

    assert battery.available
    assert MIN_BATTERY <= len(battery.items) <= MAX_BATTERY
    assert battery.mastered_sense_count == 20


def test_at_most_one_item_per_sense():
    """Twenty items over eight words is a short-term memory test, not fluency."""
    senses = list(range(1, 21))
    db = _StubDB(
        ladder_rows=_ladder(*senses),
        exercise_rows=_exercises(senses, per_sense=4),
    )

    battery = SpeedRoundComposer(db).compose('user-1', LANG_EN)

    sense_ids = [item['sense_id'] for item in battery.items]
    assert len(sense_ids) == len(set(sense_ids))


def test_battery_size_is_clamped_to_the_supported_range():
    senses = list(range(1, 41))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))
    composer = SpeedRoundComposer(db)

    assert len(composer.compose('u', LANG_EN, size=99).items) == MAX_BATTERY
    assert len(composer.compose('u', LANG_EN, size=1).items) == MIN_BATTERY


def test_seconds_per_item_is_clamped():
    senses = list(range(1, 21))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))
    composer = SpeedRoundComposer(db)

    assert composer.compose('u', LANG_EN, seconds_per_item=900).seconds_per_item == 30
    assert composer.compose('u', LANG_EN, seconds_per_item=0).seconds_per_item == 8


def test_items_carry_what_the_player_needs():
    senses = list(range(1, 21))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))

    item = SpeedRoundComposer(db).compose('user-1', LANG_EN).items[0]

    assert set(item) == {
        'exercise_id', 'exercise_type', 'content', 'ladder_level',
        'sense_id', 'complexity_tier', 'is_speed_round',
    }
    assert item['is_speed_round'] is True
    # The clock is a property of the round, not of the item.
    assert 'seconds_per_item' not in item


# ---------------------------------------------------------------------------
# Empty states (AC: 'empty-state handled')
# ---------------------------------------------------------------------------

def test_no_mastered_words_is_an_explained_empty_state():
    battery = SpeedRoundComposer(_StubDB()).compose('user-1', LANG_EN)

    assert not battery.available
    payload = battery.to_payload()
    assert payload['no_content_reason'] == 'no_mastered_words'
    assert payload['items'] == []


def test_mastered_words_with_no_items_is_a_different_empty_state():
    db = _StubDB(ladder_rows=_ladder(1, 2, 3), exercise_rows=[])
    battery = SpeedRoundComposer(db).compose('user-1', LANG_EN)

    assert battery.to_payload()['no_content_reason'] == (
        'no_recognition_items_for_mastered_words'
    )
    assert battery.mastered_sense_count == 3


def test_too_few_items_yields_no_battery_rather_than_a_short_one():
    """The format only produces fluency pressure at length."""
    senses = [1, 2, 3]
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))

    battery = SpeedRoundComposer(db).compose('user-1', LANG_EN)

    assert not battery.available
    assert battery.to_payload()['no_content_reason'] == 'too_few_items_for_a_battery'


def test_a_db_failure_degrades_to_an_empty_battery():
    battery = SpeedRoundComposer(_StubDB(raises=True)).compose('user-1', LANG_EN)
    assert not battery.available


# ---------------------------------------------------------------------------
# Payload contract
# ---------------------------------------------------------------------------

def test_payload_declares_that_family_confidence_is_untouched():
    """The ladder must not move on a speed round — see the module docstring."""
    senses = list(range(1, 21))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))

    payload = SpeedRoundComposer(db).compose('user-1', LANG_EN).to_payload()

    assert payload['updates_family_confidence'] is False
    assert UPDATES_FAMILY_CONFIDENCE is False


def test_payload_reports_the_total_clock():
    senses = list(range(1, 21))
    db = _StubDB(ladder_rows=_ladder(*senses), exercise_rows=_exercises(senses))

    payload = SpeedRoundComposer(db).compose(
        'user-1', LANG_EN, size=MIN_BATTERY, seconds_per_item=5,
    ).to_payload()

    assert payload['mode'] == 'timed_speed_round'
    assert payload['seconds_per_item'] == 5
    assert payload['total_seconds'] == 5 * len(payload['items'])


def test_an_empty_battery_still_reports_a_mode():
    payload = Battery(reason='no_mastered_words').to_payload()
    assert payload['mode'] == 'timed_speed_round'
    assert payload['total_seconds'] == 0


# ---------------------------------------------------------------------------
# Matrix contract (AC: ladder_level = NULL respected)
# ---------------------------------------------------------------------------

def test_the_capability_row_keeps_it_out_of_the_ladder():
    """AC: 'capability-matrix row ladder_level=NULL respected'.

    A non-NULL level would put speed rounds into active_levels and therefore
    into the ordinary drill rotation, which is the opposite of the intent.
    """
    from services.vocabulary_ladder.config import (
        CAPABILITY_MATRIX, EXERCISE_TYPE_FAMILY, compute_active_levels,
    )

    rows = [c for c in CAPABILITY_MATRIX if c['type_code'] == 'timed_speed_round']
    assert rows, 'timed_speed_round must have capability rows'
    assert all(row['ladder_level'] is None for row in rows)

    for semantic_class in ('concrete', 'abstract', 'action', 'property'):
        for language_id in (1, 2, 3):
            levels = compute_active_levels(semantic_class, language_id)
            assert None not in levels

    # Its own family, not one of the five the ladder tracks.
    assert EXERCISE_TYPE_FAMILY['timed_speed_round'] == 'fluency'


def test_recognition_levels_are_the_receptive_ones():
    assert RECOGNITION_LEVELS == (1, 2, 3)
