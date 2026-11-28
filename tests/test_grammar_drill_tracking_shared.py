"""The shared grammar-drill tracking, Japanese profile (ADR-068).

One structure (grammar_drill_daily, grammar_drill_state, record_grammar_drill_round)
serves every language; services/grammar_drill_tracking.Profile says what a
language may record. The Chinese profile is covered by
tests/test_grammar_drill_tracking_routes.py.
"""
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from services import grammar_drill_tracking as tracking

NOW = datetime(2026, 11, 28, 3, 0, tzinfo=timezone.utc)
STAMP = int(NOW.timestamp())
KEY = '33333333-3333-4333-8333-333333333333'


def _state(level=3, **over):
    ladder = {'l': level, 'la': 4, 'e': 0.9, 'n': 12, 'c': 10, 'rt': 2500, 'due': None, 'iv': 0,
              'last': STAMP * 1000, 'miss': ['0123456789']}
    ladder.update(over)
    return {'u': max(level, 1), 'l': STAMP, 's': ladder}


def _entry(topic='wa-topic', **over):
    entry = {'topic': topic, 'answers': 10, 'correct': 8, 'timed': 8, 'ms_sum': 20000,
             'stage': 3, 'instant': False, 'sub_misses': {}, 'state': _state()}
    entry.update(over)
    return entry


def _body(*entries, **over):
    body = {'language_id': 3, 'round_key': KEY, 'mode': 'round', 'played_at': STAMP,
            'topics': list(entries) or [_entry()]}
    body.update(over)
    return body


@pytest.fixture(autouse=True)
def _fresh():
    tracking.reset()
    yield
    tracking.reset()


def test_languages_with_a_profile():
    assert tracking.profile_for(1).name == 'Chinese'
    assert tracking.profile_for(3).name == 'Japanese'
    for other in (2, 0, None, True, '3'):
        assert tracking.profile_for(other) is None


def test_japanese_topics_are_skills_of_both_courses_and_the_two_generated_families():
    ja = tracking.profile_for(3)
    assert ja.topic('wa-topic') == (frozenset(), 7)            # particle course
    assert ja.topic('pt-wake') == (frozenset(), 7)             # grammar course
    assert ja.topic('conj-causative-passive') == (frozenset(), 4)
    assert ja.topic('conj-te') == (frozenset(), 4)
    assert ja.topic('read-num100') == (frozenset(), 4)
    for bad in ('nope', 'conj-', 'read-', 'conj-UP', 'read-a-b', 'ba', 'wa_topic'):
        assert ja.topic(bad) is None, bad
    # a Chinese topic is not a Japanese one, and the reverse
    zh_topic = next(iter(tracking.topic_subs()))
    assert tracking.profile_for(1).topic(zh_topic) and ja.topic(zh_topic) is None
    assert tracking.profile_for(1).topic('wa-topic') is None


def test_a_japanese_round_validates_and_keeps_its_language():
    round_ = tracking.validate_round(_body(_entry(), _entry('conj-te', stage=2, state=_state(2))), NOW)
    assert round_['language_id'] == 3 and round_['mode'] == 'round'
    assert [t['topic'] for t in round_['topics']] == ['wa-topic', 'conj-te']
    assert round_['topics'][0]['state']['s']['miss'] == ['0123456789']
    assert round_['practice_day'].isoformat() == '2026-11-28'


def test_skills_have_seven_stages_generated_topics_four():
    top = _entry(stage=7, instant=True, state=_state(7))
    assert tracking.validate_round(_body(top), NOW)['topics'][0]['instant'] is True
    with pytest.raises(tracking.ValidationError, match='stage'):
        tracking.validate_round(_body(_entry(stage=8, state=_state(7))), NOW)
    with pytest.raises(tracking.ValidationError, match='instant needs the last stage'):
        tracking.validate_round(_body(_entry(stage=4, instant=True, state=_state(4))), NOW)
    conj = _entry('conj-te', stage=4, instant=True, state=_state(4))
    assert tracking.validate_round(_body(conj), NOW)['topics'][0]['stage'] == 4
    with pytest.raises(tracking.ValidationError, match='stage'):
        tracking.validate_round(_body(_entry('conj-te', stage=5, state=_state(4))), NOW)
    with pytest.raises(tracking.ValidationError, match='state.u'):
        tracking.validate_round(_body(_entry('read-price', stage=2, state=_state(5))), NOW)


@pytest.mark.parametrize('change, message', [
    (lambda e: e.update(topic='ba-zi'), 'unknown topic'),
    (lambda e: e.update(sub_misses={'x': 1}), 'unknown sub-point'),
    (lambda e: e['state'].pop('s'), 'u, l and s'),
    (lambda e: e['state'].update(r=['', '', '', '']), 'u, l and s'),
    (lambda e: e['state']['s'].update(extra=1), 'unknown fields'),
    (lambda e: e['state']['s'].update(e=1.5), 'out of range'),
    (lambda e: e['state']['s'].update(e='0.5'), 'must be a number'),
    (lambda e: e['state']['s'].update(n=-1), 'state.s.n'),
    (lambda e: e['state']['s'].update(miss=['x' * 10]), 'item ids'),
    (lambda e: e['state']['s'].update(miss=['0123456789'] * 13), 'item ids'),
    (lambda e: e['state']['s'].update(last=10 ** 15), 'out of range'),
    (lambda e: e['state'].update(l=STAMP + 3 * 86400), 'state.l'),
    (lambda e: e.update(ms_sum=8 * 30000 + 1), 'ms_sum'),
])
def test_bad_japanese_entries_are_rejected(change, message):
    entry = _entry()
    change(entry)
    with pytest.raises(tracking.ValidationError, match=message):
        tracking.validate_round(_body(entry), NOW)


def test_a_sync_entry_uploads_state_without_answers():
    entry = _entry(answers=0, correct=0, timed=0, ms_sum=0)
    round_ = tracking.validate_round(_body(entry, mode='sync'), NOW)
    assert round_['topics'][0]['answers'] == 0 and round_['topics'][0]['state']['u'] == 3
    with pytest.raises(tracking.ValidationError):
        tracking.validate_round(_body(_entry(), mode='sync'), NOW)        # answers in a sync


def test_routes_take_japanese(client, auth_headers):
    with patch('routes.grammar_drill.tracking.record_round',
               return_value={'recorded': 1, 'replayed': 0}) as record:
        resp = client.post('/api/grammar-drill/round', json=_body(played_at=None), headers=auth_headers)
    assert resp.status_code == 200, resp.data
    assert record.call_args.args[2]['language_id'] == 3
    with patch('routes.grammar_drill.tracking.load_progress',
               return_value={'today': '2026-11-28', 'days': 1, 'states': {}, 'daily': []}) as load:
        resp = client.get('/api/grammar-drill/progress?language_id=3&days=1', headers=auth_headers)
    assert resp.status_code == 200
    assert load.call_args.kwargs['language_id'] == 3
    assert client.get('/api/grammar-drill/progress?language_id=2', headers=auth_headers).status_code == 400
    assert client.post('/api/grammar-drill/round', json=_body(language_id=2),
                       headers=auth_headers).status_code == 400


def test_the_migration_allows_seven_stages_and_the_old_table_is_gone():
    root = Path(tracking.__file__).resolve().parent.parent
    sql = (root / 'migrations' / 'grammar_drill_tracking.sql').read_text()
    assert 'CHECK (stage BETWEEN 1 AND 7)' in sql
    assert 'LEAST(7, GREATEST(1,' in sql and 'v_u := LEAST(7,' in sql
    assert 'LEAST(4' not in sql and 'BETWEEN 1 AND 4' not in sql
    assert tracking.DB_MAX_STAGE == tracking.JA_SKILL_STAGES == 7
    assert not (root / 'migrations' / 'particle_drill_progress.sql').exists()
    assert not (root / 'services' / 'particle_drill' / 'progress.py').exists()
