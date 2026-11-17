"""TASK-988 (ADR-047): the battery readers hydrate exercise content.

Appendix A rows 7-8. The speed round picks its <= 20 rows first and hydrates
only those (it used to read content for every mastered sense); the gate /
stress-test batteries hydrate their one sense's rows before picking.
``store.read_mode`` and ``store.hydrate`` are monkeypatched (the storage
reader lands in TASK-978); the fake hydrate follows the ADR-047 section 9
contract and records its calls. No network, no Supabase.
"""

from __future__ import annotations

import copy
import random
from types import SimpleNamespace

import pytest

from services.exercise_content import store
from services.vocabulary_ladder.ladder_service import LadderService
from services.vocabulary_ladder.speed_round import (
    MAX_BATTERY, MAX_ITEMS_PER_SENSE, MIN_BATTERY, SpeedRoundComposer, _to_item,
)

LANG = 3

SPEED_TEMPLATE_DB = 'id, exercise_type, content, ladder_level, word_sense_id, complexity_tier'
SPEED_TEMPLATE_STORAGE = ('id, exercise_type, content_version, ladder_level, word_sense_id, '
                          'complexity_tier')
BATTERY_DB = 'id, exercise_type, content, complexity_tier, ladder_level, tags, word_sense_id'
BATTERY_STORAGE = ('id, exercise_type, content_version, complexity_tier, ladder_level, tags, '
                   'word_sense_id')


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeHydrate:
    """``store.hydrate`` stand-in: content comes from ``contents[item[id_key]]``;
    ``missing`` ids are dropped (or set to None with drop_missing=False)."""

    def __init__(self, contents=None, missing=(), raises=None):
        self.contents = contents
        self.missing = set(missing)
        self.raises = raises
        self.calls = []

    def __call__(self, items, *, language_id=None, id_key='id', sense_key='word_sense_id',
                 db=None, drop_missing=True, max_senses=None, deadline_s=None):
        self.calls.append({
            'ids': [i.get(id_key) for i in items if isinstance(i, dict)],
            'senses': [i.get(sense_key) for i in items if isinstance(i, dict)],
            'language_id': language_id, 'id_key': id_key, 'sense_key': sense_key,
            'db': db, 'drop_missing': drop_missing,
        })
        if self.raises is not None:
            raise self.raises
        report = store.HydrationReport(mode='storage')
        keep = []
        for item in items:
            if not (isinstance(item, dict) and item.get(id_key)):
                keep.append(item)
                continue
            report.items += 1
            if item.get('content') is not None:
                keep.append(item)
                continue
            key = item[id_key]
            if key in self.missing:
                report.missing_ids.append(key)
                if drop_missing:
                    report.dropped += 1
                    continue
                item['content'] = None
            elif self.contents is not None:
                item['content'] = copy.deepcopy(self.contents[key])
            else:
                item['content'] = {'hydrated': key}
            keep.append(item)
        items[:] = keep
        return report


class _Query:
    def __init__(self, rows, log):
        self._rows, self._log = rows, log

    def select(self, columns, **_kwargs):
        self._log.append(('select', columns))
        return self

    def eq(self, column, value):
        self._log.append(('eq', column, value))
        return self

    def in_(self, column, values):
        self._log.append(('in', column, tuple(values)))
        return self

    def is_(self, column, value):
        self._log.append(('is', column, value))
        return self

    @property
    def not_(self):
        self._log.append(('not',))
        return self

    def execute(self):
        return SimpleNamespace(data=[dict(r) for r in self._rows])


class FakeDB:
    def __init__(self, tables):
        self.tables = tables
        self.log: dict[str, list] = {}

    def table(self, name):
        return _Query(self.tables.get(name, []), self.log.setdefault(name, []))

    def selects(self, name):
        return [e[1] for e in self.log.get(name, []) if e[0] == 'select']


def _speed_rows(n_senses, per_sense=1, with_content=False, start=100):
    rows = []
    for sid in range(start, start + n_senses):
        for k in range(per_sense):
            row = {'id': f'ex-{sid}-{k}', 'exercise_type': 'definition_match',
                   'ladder_level': 2, 'word_sense_id': sid, 'complexity_tier': 'T2'}
            if with_content:
                row['content'] = {'word': f'w{sid}', 'k': k}
            else:
                row['content_version'] = 7
            rows.append(row)
    return rows


def _speed_db(rows):
    senses = sorted({r['word_sense_id'] for r in rows})
    return FakeDB({'user_word_ladder': [{'sense_id': s} for s in senses], 'exercises': rows})


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setattr(store, 'read_mode', lambda: 'storage')


# ---------------------------------------------------------------------------
# Speed round
# ---------------------------------------------------------------------------

def test_storage_mode_hydrates_only_the_picked_rows(storage, monkeypatch):
    fake = FakeHydrate()
    monkeypatch.setattr(store, 'hydrate', fake)
    rows = _speed_rows(30, per_sense=3)                 # 90 candidates over 30 senses
    db = _speed_db(rows)
    composer = SpeedRoundComposer(db)
    battery = composer.compose('u', LANG)

    assert db.selects('exercises') == [SPEED_TEMPLATE_STORAGE]
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert len(call['ids']) == MAX_BATTERY < len(rows)
    assert len(set(call['senses'])) == MAX_BATTERY       # one row per sense
    assert set(call['ids']) <= {r['id'] for r in rows}
    assert (call['language_id'], call['id_key'], call['sense_key'], call['db']) == \
        (LANG, 'id', 'word_sense_id', db)
    assert call['drop_missing'] is True
    assert [i['exercise_id'] for i in battery.items] == call['ids']
    assert all(i['content'] == {'hydrated': i['exercise_id']} for i in battery.items)
    assert battery.reason is None and battery.mastered_sense_count == 30


def test_a_smaller_size_hydrates_fewer_rows(storage, monkeypatch):
    fake = FakeHydrate()
    monkeypatch.setattr(store, 'hydrate', fake)
    battery = SpeedRoundComposer(_speed_db(_speed_rows(30, per_sense=2))).compose(
        'u', LANG, size=MIN_BATTERY)
    assert len(fake.calls[0]['ids']) == MIN_BATTERY == len(battery.items)


def test_dropped_rows_leave_a_smaller_battery(storage, monkeypatch):
    rows = _speed_rows(15)
    fake = FakeHydrate(missing={'ex-100-0', 'ex-105-0', 'ex-110-0'})
    monkeypatch.setattr(store, 'hydrate', fake)
    battery = SpeedRoundComposer(_speed_db(rows)).compose('u', LANG)
    assert len(fake.calls[0]['ids']) == 15
    assert len(battery.items) == 12
    assert {i['exercise_id'] for i in battery.items}.isdisjoint(fake.missing)
    assert all(i['content'] is not None for i in battery.items)


def test_too_few_rows_after_hydration_is_no_battery(storage, monkeypatch):
    rows = _speed_rows(12)
    monkeypatch.setattr(store, 'hydrate', FakeHydrate(
        missing={f'ex-{s}-0' for s in range(100, 105)}))
    battery = SpeedRoundComposer(_speed_db(rows)).compose('u', LANG)
    assert battery.items == []
    assert battery.reason == 'too_few_items_for_a_battery'
    assert battery.mastered_sense_count == 12
    assert battery.to_payload()['no_content_reason'] == 'too_few_items_for_a_battery'


def test_a_failing_hydrate_in_storage_mode_serves_only_rows_with_content(storage, monkeypatch):
    monkeypatch.setattr(store, 'hydrate', FakeHydrate(raises=RuntimeError('reader bug')))
    battery = SpeedRoundComposer(_speed_db(_speed_rows(15))).compose('u', LANG)
    assert battery.items == [] and battery.reason == 'too_few_items_for_a_battery'


def test_a_failing_hydrate_in_db_mode_changes_nothing(monkeypatch):
    monkeypatch.setattr(store, 'hydrate', FakeHydrate(raises=ValueError('bad argument')))
    battery = SpeedRoundComposer(_speed_db(_speed_rows(15, with_content=True))).compose('u', LANG)
    assert len(battery.items) == 15 and all(i['content'] for i in battery.items)


def _todays_select(candidates, size):
    """The pre-ADR-047 ``SpeedRoundComposer._select``, verbatim."""
    by_sense: dict = {}
    for item in candidates:
        by_sense.setdefault(item.get('word_sense_id'), []).append(item)
    picked: list[dict] = []
    for items in by_sense.values():
        picked.extend(random.sample(items, min(MAX_ITEMS_PER_SENSE, len(items))))
    random.shuffle(picked)
    return [_to_item(item) for item in picked[:size]]


@pytest.mark.parametrize('seed', [0, 1, 47047])
def test_pick_keeps_todays_sampling(seed):
    candidates = _speed_rows(25, per_sense=3, with_content=True)
    random.seed(seed)
    today = _todays_select(candidates, MAX_BATTERY)
    after_today = random.random()
    random.seed(seed)
    picked = SpeedRoundComposer._pick(candidates, MAX_BATTERY)
    assert random.random() == after_today          # same random calls, same order
    assert [_to_item(r) for r in picked] == today
    assert all(any(r is c for c in candidates) for r in picked)   # the rows themselves
    random.seed(seed)
    assert SpeedRoundComposer._select(candidates, MAX_BATTERY) == today


def test_db_mode_speed_round_is_todays(monkeypatch):
    """The real store in db mode: today's select string, content straight from the rows."""
    rows = _speed_rows(22, per_sense=2, with_content=True)
    db = _speed_db(rows)
    random.seed(5)
    battery = SpeedRoundComposer(db).compose('u', LANG)
    random.seed(5)
    assert battery.items == _todays_select(rows, MAX_BATTERY)
    assert db.selects('exercises') == [SPEED_TEMPLATE_DB]
    assert ('not',) in db.log['exercises'] and ('is', 'word_asset_id', 'null') in db.log['exercises']


# ---------------------------------------------------------------------------
# Gate / stress-test batteries
# ---------------------------------------------------------------------------

SENSE = 77


def _battery_rows(with_content):
    rows = [
        {'id': 'l3a', 'exercise_type': 'cloze_completion', 'complexity_tier': 'T1',
         'ladder_level': 3, 'tags': {'variant': 'A'}, 'word_sense_id': SENSE},
        {'id': 'l3b', 'exercise_type': 'cloze_completion', 'complexity_tier': 'T1',
         'ladder_level': 3, 'tags': {'variant': 'B'}, 'word_sense_id': SENSE},
        {'id': 'l5a', 'exercise_type': 'semantic_discrimination', 'complexity_tier': 'T2',
         'ladder_level': 5, 'tags': {'variant': 'A'}, 'word_sense_id': SENSE},
        {'id': 'l5b', 'exercise_type': 'semantic_discrimination', 'complexity_tier': 'T2',
         'ladder_level': 5, 'tags': {'variant': 'B'}, 'word_sense_id': SENSE},
    ]
    for r in rows:
        if with_content:
            r['content'] = {'db': r['id']}
        else:
            r['content_version'] = 12
    return rows


def _ladder(rows):
    return LadderService(FakeDB({'exercises': rows}))


def test_battery_rows_are_hydrated_before_picking(storage, monkeypatch):
    fake = FakeHydrate()
    monkeypatch.setattr(store, 'hydrate', fake)
    svc = _ladder(_battery_rows(with_content=False))
    out = svc._fetch_exercises_for_levels(SENSE, LANG, [3, 5], 2)

    assert svc.db.selects('exercises') == [BATTERY_STORAGE]
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call['ids'] == ['l3a', 'l3b', 'l5a', 'l5b']
    assert (call['language_id'], call['id_key'], call['sense_key'], call['db']) == \
        (LANG, 'id', 'word_sense_id', svc.db)
    # variant diversity unchanged: A at level 3, then B at level 5
    assert [(e['exercise_id'], e['content']) for e in out] == \
        [('l3a', {'hydrated': 'l3a'}), ('l5b', {'hydrated': 'l5b'})]
    assert out[0]['ladder_name'] and out[0]['sense_id'] == SENSE


def test_a_dropped_row_is_never_picked(storage, monkeypatch):
    monkeypatch.setattr(store, 'hydrate', FakeHydrate(missing={'l3a', 'l5a', 'l5b'}))
    out = _ladder(_battery_rows(with_content=False))._fetch_exercises_for_levels(
        SENSE, LANG, [3, 5], 2)
    assert [(e['exercise_id'], e['content']) for e in out] == [('l3b', {'hydrated': 'l3b'})]


def test_every_row_dropped_is_an_empty_battery(storage, monkeypatch):
    monkeypatch.setattr(store, 'hydrate', FakeHydrate(missing={'l3a', 'l3b', 'l5a', 'l5b'}))
    assert _ladder(_battery_rows(with_content=False))._fetch_exercises_for_levels(
        SENSE, LANG, [3, 5], 2) == []


def test_stress_test_battery_hydrates_its_sense_once(storage, monkeypatch):
    fake = FakeHydrate()
    monkeypatch.setattr(store, 'hydrate', fake)
    svc = _ladder(_battery_rows(with_content=False))
    svc._get_ladder_row = lambda u, s: {'active_levels': [3, 5]}
    out = svc.assemble_stress_test('u', SENSE, LANG)
    assert len(fake.calls) == 1 and fake.calls[0]['language_id'] == LANG
    assert out and all(e['content'] == {'hydrated': e['exercise_id']} for e in out)


def test_gate_battery_hydrates_its_sense_once(storage, monkeypatch):
    fake = FakeHydrate(missing={'g6a'})
    monkeypatch.setattr(store, 'hydrate', fake)
    rows = [{'id': gid, 'exercise_type': 'semantic_discrimination', 'complexity_tier': 'T2',
             'ladder_level': level, 'tags': {'variant': variant}, 'word_sense_id': SENSE,
             'content_version': 4}
            for gid, level, variant in (('g6a', 6, 'A'), ('g6b', 6, 'B'), ('g7a', 7, 'A'))]
    svc = _ladder(rows)
    svc._get_ladder_row = lambda u, s: {'active_levels': [1, 2, 3, 4, 5, 6, 7]}
    out = svc.assemble_gate('u', SENSE, LANG, 'gate_a')        # ring 3: levels 6 and 7
    assert len(fake.calls) == 1 and fake.calls[0]['ids'] == ['g6a', 'g6b', 'g7a']
    assert [(e['exercise_id'], e['content']) for e in out] == [
        ('g6b', {'hydrated': 'g6b'}), ('g7a', {'hydrated': 'g7a'})]


def test_db_mode_battery_is_todays():
    """The real store in db mode: today's select string and today's output."""
    svc = _ladder(_battery_rows(with_content=True))
    out = svc._fetch_exercises_for_levels(SENSE, LANG, [3, 5, 3], 3)
    assert svc.db.selects('exercises') == [BATTERY_DB]
    assert [(e['exercise_id'], e['content'], e['ladder_level']) for e in out] == [
        ('l3a', {'db': 'l3a'}, 3), ('l5b', {'db': 'l5b'}, 5), ('l3a', {'db': 'l3a'}, 3)]
    assert set(out[0]) == {'exercise_id', 'exercise_type', 'source_type', 'content',
                           'complexity_tier', 'ladder_level', 'ladder_name', 'family',
                           'sense_id'}
