"""TASK-1019 (ADR-049): the daily-session readers hydrate exercise content.

Appendix A rows 3-6: ``get_practice_session`` / ``get_review_ahead_items``
callers, the prestudy follow-up select, the serve-time content rewrites and
the intro-drill block. ``store.hydrate`` is mostly monkeypatched: the fake
hydrate follows the ADR-049 section 9 contract (only dicts with a truthy
``id_key``, content already present is kept, a missing one is dropped in place)
and records every call. A few tests run the real store over the conftest's
``InMemoryBackend``. No network, no Supabase.
"""

from __future__ import annotations

import copy
import logging
from datetime import date
from types import SimpleNamespace

import pytest

from services import intro_drill, prestudy
from services.exercise_content import store
from services.practice import session_assembly
from services.practice_session_service import PracticeSessionService

SELECT_FOLLOWUP = 'id, word_sense_id, exercise_type, content_version, ladder_level'


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeHydrate:
    """``store.hydrate`` stand-in: content comes from ``contents[item[id_key]]``."""

    def __init__(self, contents=None, order=None, raises=None):
        self.contents = contents or {}
        self.order = order
        self.raises = raises
        self.calls = []

    def __call__(self, items, *, language_id=None, id_key='id', sense_key='word_sense_id',
                 db=None, drop_missing=True, max_senses=None, deadline_s=None):
        self.calls.append({
            'items': [dict(i) if isinstance(i, dict) else i for i in items],
            'language_id': language_id, 'id_key': id_key, 'sense_key': sense_key,
            'db': db, 'drop_missing': drop_missing,
        })
        if self.order is not None:
            self.order.append('hydrate')
        if self.raises is not None:
            raise self.raises
        report = store.HydrationReport(mode='storage')
        groups = set()
        keep = []
        for item in items:
            if not (isinstance(item, dict) and item.get(id_key)):
                keep.append(item)
                continue
            report.items += 1
            if item.get('content') is not None:
                keep.append(item)
                continue
            groups.add((language_id, item.get(sense_key), item.get('content_version')))
            content = self.contents.get(item[id_key])
            if content is None:
                report.missing_ids.append(item[id_key])
                if drop_missing:
                    report.dropped += 1
                    continue
                item['content'] = None
                keep.append(item)
                continue
            item['content'] = copy.deepcopy(content)
            keep.append(item)
        report.groups = report.fetched = len(groups)
        items[:] = keep
        return report


class _Query:
    """A PostgREST-style chain over ``db.tables[name]`` that records every call."""

    def __init__(self, db, name):
        self.db, self.name, self.log = db, name, []
        db.queries.append((name, self.log))

    def __getattr__(self, attr):
        def chain(*args, **_kwargs):
            self.log.append((attr,) + args)
            return self
        return chain

    def execute(self):
        rows = self.db.tables.get(self.name, [])
        return SimpleNamespace(data=[dict(r) for r in rows])


class FakeDB:
    """Tables for ``.table()`` reads and canned ``.rpc()`` answers, all recorded."""

    def __init__(self, tables=None, rpc_data=None):
        self.tables = tables or {}
        self.rpc_data = rpc_data or {}
        self.queries = []
        self.rpc_calls = []

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params):
        self.rpc_calls.append((name, dict(params)))
        data = self.rpc_data.get(name, {'items': []})
        data = data(params) if callable(data) else copy.deepcopy(data)
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=data))

    def selects(self, table):
        return [entry[1] for name, log in self.queries if name == table
                for entry in log if entry[0] == 'select']


def _service(db):
    s = PracticeSessionService.__new__(PracticeSessionService)
    s.db = db
    s._maybe_top_up_ladder = lambda u, lang: []
    s._order_items = lambda *a: None
    s._most_overdue_first = lambda items, u: None
    s._exercise_preferences = lambda u: {}
    return s


def _item(eid, sid, exercise_type='definition_match', mode='maintenance', **extra):
    return {'exercise_id': eid, 'sense_id': sid, 'exercise_type': exercise_type,
            'mode': mode, 'content_version': 0, **extra}


@pytest.fixture
def quiet_session(monkeypatch):
    """get_session's side reads switched off: no follow-ups, no intro words, no DT cards."""
    monkeypatch.setattr(session_assembly, 'plan_today_iso', lambda db, u, lang: '2026-11-17')
    monkeypatch.setattr(prestudy, 'due_followup_senses', lambda *a, **k: [])
    monkeypatch.setattr(prestudy, 'mark_followups', lambda *a, **k: None)
    monkeypatch.setattr(intro_drill, 'ENABLED', False)
    cards = []
    monkeypatch.setattr(
        'services.dual_translation.cards.select_error_exercises_for_practice',
        lambda *a, **k: [dict(c) for c in cards])
    return cards


# ---------------------------------------------------------------------------
# RPC arguments
# ---------------------------------------------------------------------------

SESSION_PARAMS = {'p_user_id', 'p_language_id', 'p_mode', 'p_target_minutes', 'p_user_theta',
                  'p_include_content'}
AHEAD_PARAMS = {'p_user_id', 'p_language_id', 'p_limit', 'p_exclude_recent_minutes',
                'p_exclude_sense_ids', 'p_include_content'}


def test_session_rpc_never_asks_for_content():
    db = FakeDB()                      # the real store
    _service(db)._practice_session_rpc('u', 1, 'auto', 15, 0.5)
    assert db.rpc_calls == [('get_practice_session', {
        'p_user_id': 'u', 'p_language_id': 1, 'p_mode': 'auto',
        'p_target_minutes': 15, 'p_user_theta': 0.5, 'p_include_content': False})]
    _service(db)._practice_session_rpc('u', 3, 'maintenance', 20)
    assert set(db.rpc_calls[1][1]) == SESSION_PARAMS


def test_review_ahead_call_never_asks_for_content(monkeypatch):
    monkeypatch.setattr(prestudy, 'mark_followups', lambda *a, **k: None)
    db = FakeDB(rpc_data={'get_practice_session': {'items': []},
                          'get_review_ahead_items': []})
    s = _service(db)
    s._inject_prestudy_followups = lambda payload, u, lang: 0
    s._extra_review_items('u', 1, {9})
    ahead = [p for n, p in db.rpc_calls if n == 'get_review_ahead_items']
    assert len(ahead) == 1
    assert set(ahead[0]) == AHEAD_PARAMS and ahead[0]['p_include_content'] is False
    session = [p for n, p in db.rpc_calls if n == 'get_practice_session']
    assert session[0]['p_include_content'] is False


# ---------------------------------------------------------------------------
# get_session: one hydrate call, before the content rewrites
# ---------------------------------------------------------------------------

def test_items_are_hydrated_once_before_script_variant_and_jumbled_prep(quiet_session,
                                                                         monkeypatch):
    order = []
    fake = FakeHydrate({'e1': {'q': 'one'}, 'e2': {'q': 'two'}}, order=order)
    monkeypatch.setattr(store, 'hydrate', fake)
    db = FakeDB(rpc_data={'get_practice_session': {'items': [_item('e1', 11), _item('e2', 12)]}})
    s = _service(db)
    seen = {}

    def script_variant(payload, user_id, language_id, preferences=None):
        order.append('script_variant')
        seen['script'] = [i.get('content') for i in payload['items']]

    def jumbled(items, language_id):
        order.append('jumbled')
        seen['jumbled'] = [i.get('content') for i in items]

    s._apply_script_variant = script_variant
    s._prepare_jumbled_items = jumbled
    payload = s.get_session('u', 3, mode='maintenance')

    assert order == ['hydrate', 'script_variant', 'jumbled']
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert (call['id_key'], call['sense_key'], call['language_id'], call['db']) == \
        ('exercise_id', 'sense_id', 3, db)
    assert call['drop_missing'] is True
    assert [i['exercise_id'] for i in call['items']] == ['e1', 'e2']
    assert seen['script'] == seen['jumbled'] == [{'q': 'one'}, {'q': 'two'}]
    assert [i['content'] for i in payload['items']] == [{'q': 'one'}, {'q': 'two'}]
    assert db.rpc_calls[0][1]['p_include_content'] is False
    assert 'no_content_reason' not in payload


def test_hydrated_content_is_what_the_script_swap_and_jumbled_prep_rewrite(quiet_session,
                                                                            monkeypatch):
    contents = {
        'j1': {'chunks': ['我们', '一起', '去'], 'hant': {'chunks': ['我們', '一起', '去']}},
        'd1': {'sentence': '这个', 'hant': {'sentence': '這個'}},
    }
    monkeypatch.setattr(store, 'hydrate', FakeHydrate(contents))
    db = FakeDB(rpc_data={'get_practice_session': {'items': [
        _item('j1', 21, 'jumbled_sentence'), _item('d1', 22)]}})
    s = _service(db)
    s._exercise_preferences = lambda u: {'script_variant': 'traditional'}
    payload = s.get_session('u', 1, mode='maintenance')

    jumbled, definition = payload['items']
    assert jumbled['content']['chunks'] == ['我們', '一起', '去']
    assert jumbled['content']['correct_ordering'] == [0, 1, 2]
    assert definition['content']['sentence'] == '這個'
    assert payload['script_variant'] == 'traditional'
    # the fixture dicts were never handed out
    assert contents['j1'] == {'chunks': ['我们', '一起', '去'],
                              'hant': {'chunks': ['我們', '一起', '去']}}


def test_markers_and_error_cards_are_left_alone(quiet_session, monkeypatch):
    fake = FakeHydrate({'e1': {'q': 'one'}})
    monkeypatch.setattr(store, 'hydrate', fake)
    gate = {'is_gate_marker': True, 'gate_name': 'gate_a', 'sense_id': 31,
            'expected_seconds': 180, 'mode': 'acquisition'}
    stress = {'is_stress_test_marker': True, 'sense_id': 32, 'expected_seconds': 420,
              'mode': 'acquisition'}
    card = {'id': 'dt-error-7', 'exercise_type': 'dt_error', 'type': 'error_card',
            'is_error_exercise': True, 'word_sense_id': None, 'card_id': 7,
            'prompt_payload': {'p': 1}}
    quiet_session.append(card)
    db = FakeDB(rpc_data={'get_practice_session': {'items': [
        _item('e1', 11, mode='acquisition'), dict(gate), dict(stress)]}})
    payload = _service(db).get_session('u', 3, mode='acquisition')

    assert len(fake.calls) == 1
    hydrated = fake.calls[0]['items']
    assert gate in hydrated and stress in hydrated          # passed through, untouched
    assert not any(i.get('is_error_exercise') for i in hydrated)
    assert gate in payload['items'] and stress in payload['items']
    assert card in payload['items'] and payload['error_cards_injected'] == 1
    assert next(i for i in payload['items'] if i.get('exercise_id') == 'e1')['content'] == \
        {'q': 'one'}


def test_all_items_dropped_reports_content_unavailable(quiet_session, monkeypatch,
                                                       caplog):
    monkeypatch.setattr(store, 'hydrate', FakeHydrate({}))
    db = FakeDB(rpc_data={'get_practice_session': {'items': [_item('e1', 11), _item('e2', 12)]}})
    with caplog.at_level(logging.INFO, logger=session_assembly.__name__):
        payload = _service(db).get_session('u', 3, mode='maintenance')
    assert payload['items'] == []
    assert payload['no_content_reason'] == 'content_unavailable'
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1 and 'content unavailable' in errors[0].getMessage()
    infos = [r for r in caplog.records if r.levelno == logging.INFO
             and 'exercise content hydrated' in r.getMessage()]
    assert len(infos) == 1 and 'dropped=2' in infos[0].getMessage()


def test_a_partial_drop_keeps_the_rest_and_logs_one_info_line(quiet_session,
                                                              monkeypatch, caplog):
    monkeypatch.setattr(store, 'hydrate', FakeHydrate({'e2': {'q': 'two'}}))
    db = FakeDB(rpc_data={'get_practice_session': {'items': [_item('e1', 11), _item('e2', 12)]}})
    with caplog.at_level(logging.INFO, logger=session_assembly.__name__):
        payload = _service(db).get_session('u', 3, mode='maintenance')
    assert [i['exercise_id'] for i in payload['items']] == ['e2']
    assert 'no_content_reason' not in payload
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
    infos = [r.getMessage() for r in caplog.records if 'exercise content hydrated' in r.getMessage()]
    assert len(infos) == 1 and 'dropped=1' in infos[0] and 'fetched=2' in infos[0]


def test_an_empty_session_is_not_called_content_unavailable(quiet_session, monkeypatch):
    fake = FakeHydrate({})
    monkeypatch.setattr(store, 'hydrate', fake)
    db = FakeDB(rpc_data={'get_practice_session': {'items': [],
                                                   'no_content_reason': 'all_complete'}})
    payload = _service(db).get_session('u', 3, mode='maintenance')
    assert fake.calls == []
    assert payload['no_content_reason'] == 'all_complete'


def test_a_failing_hydrate_serves_only_items_with_content(quiet_session, monkeypatch):
    monkeypatch.setattr(store, 'hydrate', FakeHydrate(raises=RuntimeError('reader bug')))
    db = FakeDB(rpc_data={'get_practice_session': {'items': [
        _item('e1', 11), _item('e2', 12, content={'q': 'kept'}),
        {'is_gate_marker': True, 'sense_id': 13, 'mode': 'acquisition'}]}})
    payload = _service(db).get_session('u', 3, mode='maintenance')
    assert [i.get('exercise_id') for i in payload['items']] == ['e2', None]


def test_items_that_carry_content_pass_through_the_real_store(quiet_session, monkeypatch,
                                                               caplog):
    """The real store: items that already carry content need no file, so no Storage call;
    the RPC payload passes through unchanged."""
    calls = []
    real = store.hydrate

    def spy(items, **kwargs):
        report = real(items, **kwargs)
        calls.append(report)
        return report

    monkeypatch.setattr(store, 'hydrate', spy)
    items = [_item('e1', 11, content={'q': 'one'}), _item('e2', 12, content={'q': 'two'}),
             {'is_gate_marker': True, 'sense_id': 13, 'mode': 'maintenance'}]
    db = FakeDB(rpc_data={'get_practice_session': {'items': items}})
    with caplog.at_level(logging.INFO, logger=session_assembly.__name__):
        payload = _service(db).get_session('u', 3, mode='maintenance')
    assert payload == {'items': items}
    assert set(db.rpc_calls[0][1]) == SESSION_PARAMS
    assert [(c.mode, c.items, c.groups, c.dropped) for c in calls] == [('storage', 2, 0, 0)]
    assert store.backend().calls == []
    assert not [r for r in caplog.records if 'exercise content' in r.getMessage()]


# ---------------------------------------------------------------------------
# Prestudy follow-ups
# ---------------------------------------------------------------------------

def _followup_db():
    rows = [
        {'id': 'f5', 'word_sense_id': 5, 'exercise_type': 'definition_match', 'ladder_level': 2},
        {'id': 'f5b', 'word_sense_id': 5, 'exercise_type': 'cloze_completion', 'ladder_level': 3},
        {'id': 'f6', 'word_sense_id': 6, 'exercise_type': 'definition_match', 'ladder_level': 2},
    ]
    for r in rows:
        r['content_version'] = 40 + r['word_sense_id']
    return FakeDB(tables={'exercises': rows})


def test_followup_items_carry_content_version(monkeypatch):
    monkeypatch.setattr(prestudy, 'mark_followups', lambda *a, **k: None)
    db = _followup_db()
    payload = {'items': [_item('e1', 1)]}
    assert _service(db)._inject_prestudy_followups(payload, 'u', 1, due=[5, 6]) == 2
    assert db.selects('exercises') == [SELECT_FOLLOWUP]
    extras = [i for i in payload['items'] if i.get('prestudy_followup')]
    assert [(i['exercise_id'], i['content_version'], i['content']) for i in extras] == \
        [('f5', 45, None), ('f6', 46, None)]
    assert extras[0] == {
        'exercise_id': 'f5', 'sense_id': 5, 'exercise_type': 'definition_match',
        'family': None, 'content': None, 'ladder_level': 2, 'p_known': None,
        'expected_seconds': session_assembly.PRESTUDY_FOLLOWUP_EXPECTED_SECONDS,
        'mode': 'maintenance', 'prestudy_followup': True, 'content_version': 45,
    }


def test_followups_are_hydrated_with_the_session_items(quiet_session, monkeypatch):
    fake = FakeHydrate({'e1': {'q': 'one'}, 'f5': {'q': 'five'}})
    monkeypatch.setattr(store, 'hydrate', fake)
    monkeypatch.setattr(prestudy, 'due_followup_senses', lambda *a, **k: [5])
    db = _followup_db()
    db.rpc_data = {'get_practice_session': {'items': [_item('e1', 1)]}}
    payload = _service(db).get_session('u', 1, mode='maintenance')
    assert len(fake.calls) == 1
    assert [(i['exercise_id'], i['content_version']) for i in fake.calls[0]['items']] == \
        [('e1', 0), ('f5', 45)]
    assert {i['exercise_id']: i['content'] for i in payload['items']} == \
        {'e1': {'q': 'one'}, 'f5': {'q': 'five'}}


# ---------------------------------------------------------------------------
# Extra rounds
# ---------------------------------------------------------------------------

def test_extra_round_asks_without_content_and_hydrates_once(monkeypatch):
    monkeypatch.setattr(intro_drill, 'ENABLED', False)
    monkeypatch.setattr(session_assembly, 'plan_today_iso', lambda db, u, lang: '2026-11-17')
    monkeypatch.setattr(prestudy, 'due_followup_senses', lambda *a, **k: [5])
    monkeypatch.setattr(prestudy, 'mark_followups', lambda *a, **k: None)
    order = []
    fake = FakeHydrate({'f5': {'q': 'five'}, 'm1': {'q': 'm'}, 'r1': {'q': 'ahead'}},
                       order=order)
    monkeypatch.setattr(store, 'hydrate', fake)
    db = _followup_db()
    db.rpc_data = {
        'get_practice_session': {'items': [_item('m1', 7)]},
        'get_review_ahead_items': [_item('r1', 8), _item('gone', 9)],
    }
    s = _service(db)
    s._apply_script_variant = lambda *a, **k: order.append('script_variant')
    s._prepare_jumbled_items = lambda *a, **k: order.append('jumbled')
    payload = s.get_extra_round('u', 1, reviews=True, new_words=0)

    assert order == ['hydrate', 'script_variant', 'jumbled']
    for name, params in db.rpc_calls:
        assert params['p_include_content'] is False, name
    assert {n for n, _ in db.rpc_calls} == {'get_practice_session', 'get_review_ahead_items'}
    call = fake.calls[0]
    assert (call['id_key'], call['sense_key'], call['language_id']) == \
        ('exercise_id', 'sense_id', 1)
    assert [i['exercise_id'] for i in call['items']] == ['f5', 'm1', 'r1', 'gone']
    assert call['items'][0]['content_version'] == 45
    assert [(i['exercise_id'], i['content']) for i in payload['items']] == \
        [('f5', {'q': 'five'}), ('m1', {'q': 'm'}), ('r1', {'q': 'ahead'})]
    assert payload['no_content_reason'] is None


def test_extra_round_with_every_item_dropped_says_so(monkeypatch):
    monkeypatch.setattr(intro_drill, 'ENABLED', False)
    monkeypatch.setattr(store, 'hydrate', FakeHydrate({}))
    db = FakeDB(rpc_data={'get_practice_session': {'items': [_item('m1', 7)]},
                          'get_review_ahead_items': []})
    s = _service(db)
    s._inject_prestudy_followups = lambda payload, u, lang: 0
    payload = s.get_extra_round('u', 3, reviews=True, new_words=0)
    assert payload['items'] == [] and payload['no_content_reason'] == 'content_unavailable'


# ---------------------------------------------------------------------------
# Intro-drill block
# ---------------------------------------------------------------------------

def _intro_setup(monkeypatch):
    import services.vocabulary.gloss_lookup as gloss_lookup
    monkeypatch.setattr(gloss_lookup, 'get_user_definition_language_id', lambda db, u: 2)
    monkeypatch.setattr(prestudy, '_load_senses', lambda db, sids, gl: {
        str(s): {'lemma': f'w{s}', 'pos': 'noun', 'reading': None,
                 'glosses': {'2': {'def': f'meaning {s}', 'ex': f'a w{s} here'}}}
        for s in sids})
    monkeypatch.setattr(intro_drill, '_distractor_pool', lambda *a, **k: [])
    monkeypatch.setattr(intro_drill, '_today', lambda *a: date(2026, 11, 17))
    rows = [
        {'id': 'x1', 'word_sense_id': 41, 'exercise_type': 'cloze_completion', 'ladder_level': 3},
        {'id': 'x2', 'word_sense_id': 41, 'exercise_type': 'semantic_discrimination',
         'ladder_level': 5},
        {'id': 'x3', 'word_sense_id': 42, 'exercise_type': 'cloze_completion', 'ladder_level': 3},
    ]
    return rows


def _ladder_rows(*sids):
    return [{'sense_id': s, 'intro_stage': 2} for s in sids]


def test_intro_block_is_hydrated_once(monkeypatch):
    rows = _intro_setup(monkeypatch)
    for r in rows:
        r['content_version'] = 3
    fake = FakeHydrate({'x1': {'q': 'one'}, 'x3': {'q': 'three'}})   # x2 is missing
    monkeypatch.setattr(store, 'hydrate', fake)
    db = FakeDB(tables={'exercises': rows})
    block = intro_drill.build_block(db, 'u', 2, _ladder_rows(41, 42))

    assert db.selects('exercises') == [
        'id, word_sense_id, exercise_type, content_version, ladder_level']
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert (call['id_key'], call['sense_key'], call['language_id'], call['db']) == \
        ('id', 'word_sense_id', 2, db)
    assert [r['id'] for r in call['items']] == ['x1', 'x2', 'x3']
    words = {w['sense_id']: w for w in block['words']}
    assert words[41]['exercises'] == {'use': [{
        'exercise_id': 'x1', 'sense_id': 41, 'exercise_type': 'cloze_completion',
        'content': {'q': 'one'}, 'ladder_level': 3}]}          # x2 dropped: no 'judge'
    assert 'ex_judge' not in words[41]['formats'] and 'ex_use' in words[41]['formats']
    assert words[42]['exercises']['use'][0]['content'] == {'q': 'three'}


def test_intro_block_with_the_real_store(monkeypatch):
    rows = _intro_setup(monkeypatch)
    for r in rows:
        r['content_version'] = 0
    store.backend().seed(store.content_path(2, 41, 0), store.encode_sense_file(
        41, 2, 0, {r['id']: {'q': r['id']} for r in rows if r['word_sense_id'] == 41}))
    db = FakeDB(tables={'exercises': rows})
    block = intro_drill.build_block(db, 'u', 2, _ladder_rows(41))
    assert db.selects('exercises') == [
        'id, word_sense_id, exercise_type, content_version, ladder_level']
    assert 'en/41.v0.json' in store.backend().calls_for('get')
    assert [w['sense_id'] for w in block['words']] == [41]
    assert block['words'][0]['exercises'] == {
        'use': [{'exercise_id': 'x1', 'sense_id': 41, 'exercise_type': 'cloze_completion',
                 'content': {'q': 'x1'}, 'ladder_level': 3}],
        'judge': [{'exercise_id': 'x2', 'sense_id': 41,
                   'exercise_type': 'semantic_discrimination', 'content': {'q': 'x2'},
                   'ladder_level': 5}],
    }


def test_a_session_request_makes_at_most_two_hydrate_calls(monkeypatch):
    """The intro block's rows and the final item list: two calls, never more."""
    rows = _intro_setup(monkeypatch)
    for r in rows:
        r['content_version'] = 0
    monkeypatch.setattr(session_assembly, 'plan_today_iso', lambda db, u, lang: '2026-11-17')
    monkeypatch.setattr(prestudy, 'due_followup_senses', lambda *a, **k: [])
    monkeypatch.setattr(intro_drill, 'ENABLED', True)
    monkeypatch.setattr(intro_drill, 'intro_sense_ids', lambda db, u: {41})
    monkeypatch.setattr(intro_drill, 'route_untaught',
                        lambda *a, **k: {'admitted': [], 'deferred': []})
    monkeypatch.setattr(intro_drill, 'block_for_session',
                        lambda svc, u, lang, mode: intro_drill.build_block(
                            svc.db, u, lang, _ladder_rows(41)))
    monkeypatch.setattr('services.dual_translation.cards.select_error_exercises_for_practice',
                        lambda *a, **k: [])
    fake = FakeHydrate({'x1': {'q': 'one'}, 'x2': {'q': 'two'}, 'e1': {'q': 'e'}})
    monkeypatch.setattr(store, 'hydrate', fake)
    db = FakeDB(tables={'exercises': rows},
                rpc_data={'get_practice_session': {'items': [
                    _item('e1', 50), _item('intro-word', 41)]}})
    payload = _service(db).get_session('u', 2, mode='maintenance')

    assert [c['id_key'] for c in fake.calls] == ['id', 'exercise_id']
    assert [i['exercise_id'] for i in fake.calls[1]['items']] == ['e1']   # intro word filtered first
    assert payload['intro_drill']['words'][0]['exercises']['judge'][0]['content'] == {'q': 'two'}
    assert payload['items'][0]['content'] == {'q': 'e'}
