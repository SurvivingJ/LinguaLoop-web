"""Placement service and routes (TASK-1080, vocab-placement tech §8, §14) against the in-memory SQL fake."""
import json
from datetime import timedelta

import pytest

from services import calibration_placement as cp
from services import placement_design as pd
from services import placement_evidence as pe
from tests.placement_fakes import FakePlacementSQL

USER = 'user-a'


@pytest.fixture
def fake(monkeypatch):
    return FakePlacementSQL(words_per_band=40, seed=1).install(monkeypatch)


def _play(fake, lang, dlang, policy, *, user=USER, end_at=None, max_steps=200):
    """Run a placement with a scripted learner. ``policy(item, fake) -> position|None``."""
    out = cp.start(user, lang, dlang)
    sid, item = out['session_id'], out['item']
    last = out
    for _ in range(max_steps):
        if end_at is not None and last.get('progress', {}).get('scored', 0) >= end_at and last.get('can_stop'):
            return sid, cp.end(user, sid)
        last = cp.answer(user, sid, item['response_id'], policy(item, fake), 6000)
        if last['done']:
            return sid, last
        item = last['next_item']
        assert item is not None
    raise AssertionError('placement did not finish')


def knows_common(item, fake):
    """Knows bands 5–7 (meaning and reading; zh tones too), says IDK elsewhere."""
    if item['band'] >= 5:
        roles = fake.roles_of(item['response_id'])
        return roles.index('K') if roles else fake.key_of(item['response_id'])
    return None


def tone_trouble(item, fake):
    roles = fake.roles_of(item['response_id'])
    if roles:
        return roles.index('KT')                                # right syllables, wrong tones
    return fake.key_of(item['response_id']) if item['band'] >= 4 else None


@pytest.mark.parametrize('lang,dlang', [(1, 2), (3, 2), (2, 2)])
def test_scripted_learner_reaches_a_frozen_result(fake, lang, dlang):
    sid, last = _play(fake, lang, dlang, knows_common)
    res = last['result']
    assert res and res['stop_reason'] in ('precision', 'cap', 'time', 'exhausted')
    assert res['word_language_id'] == lang and res['frame_n'] == sum(fake.rpc('knowledge_frame_bands', {})[f'{lang}:{dlang}'])
    assert len(json.dumps(res, separators=(',', ':')).encode()) <= cp.RESULT_MAX_BYTES
    assert fake.sessions[sid]['result'] == res
    assert res['this']['m'] is not None
    if lang == 2:
        assert res['this']['mr'] is None and 'meaning_only' not in res['words']
    else:
        assert res['this']['mr'] is not None
    assert len(fake.evidence_calls) == 1 and fake.evidence_calls[0][1] == sid
    if lang in (1, 3):
        assert res['items']['scored'] <= 61
    else:
        assert res['items']['scored'] <= 40


def test_reveal_only_when_word_complete_and_no_keys_in_payloads(fake):
    out = cp.start(USER, 1, 2)
    item = out['item']
    assert 'key_position' not in item and 'option_roles' not in item
    r = cp.answer(USER, out['session_id'], item['response_id'], fake.key_of(item['response_id']), 5000)
    if item['band'] >= 1 and r['next_item'] and r['next_item']['kind'] == 'reading':
        assert r['reveal'] is None                              # meaning right → reading next, no reveal yet
        nxt = r['next_item']
        assert 'option_roles' not in nxt and 'key_position' not in nxt
        r2 = cp.answer(USER, out['session_id'], nxt['response_id'], fake.roles_of(nxt['response_id']).index('KT'), 5000)
        assert r2['reveal'] is not None and r2['reveal']['parts'][0]['tone_only_miss'] is True


def test_tone_misses_form_their_own_group(fake):
    sid, last = _play(fake, 1, 2, tone_trouble)
    words = last['result']['words']
    assert words['tones_not_yet'] > 0 and words['both'] == 0
    lists = cp.result(USER, sid)['words']
    assert len(lists['tones_not_yet']) == words['tones_not_yet']


def test_cache_miss_builds_the_next_item_with_one_extra_call(fake):
    out = cp.start(USER, 3, 2)
    sid, item = out['session_id'], out['item']
    cp._cache.clear()                                           # another worker answers
    before = fake.rpc_calls.count('calibration_placement_next_item')
    r = cp.answer(USER, sid, item['response_id'], None, 4000)   # IDK → word complete
    assert r['reveal'] is not None and r['next_item'] is not None
    assert fake.rpc_calls.count('calibration_placement_next_item') == before + 1
    before = fake.rpc_calls.count('calibration_placement_next_item')
    r = cp.answer(USER, sid, r['next_item']['response_id'], None, 4000)   # cache warm now: one round trip
    assert fake.rpc_calls.count('calibration_placement_next_item') == before


def test_end_now_needs_warmup_and_20_items(fake):
    out = cp.start(USER, 2, 2)
    sid, item = out['session_id'], out['item']
    for _ in range(5):
        r = cp.answer(USER, sid, item['response_id'], None, 4000)
        item = r['next_item']
    early = cp.end(USER, sid)
    assert early['not_enough'] and early['needed'] > 0
    sid2, done = _play(fake, 2, 2, lambda i, f: None, user='user-b', end_at=20)
    assert done['result']['stop_reason'] == 'learner' and done['result']['ended_early']


def test_resume_within_24h_and_abandon_after(fake):
    out = cp.start(USER, 3, 2)
    again = cp.start(USER, 3, 2)
    assert again['resumed'] and again['session_id'] == out['session_id']
    assert again['item']['response_id'] == out['item']['response_id']
    # answer enough for eligibility (c), then let the session go stale
    sid, item = out['session_id'], out['item']
    for _ in range(25):
        r = cp.answer(USER, sid, item['response_id'], None, 4000)
        item = r['next_item']
    fake.sessions[sid]['last_activity'] -= timedelta(hours=25)
    latest = cp.latest(USER, 3)
    assert fake.sessions[sid]['stop_reason'] == 'abandoned'
    assert latest['unseen'] and latest['result']['stop_reason'] == 'abandoned'
    assert cp.latest(USER, 3)['unseen'] is False


def test_retake_comparison_and_daily_cap(fake):
    _play(fake, 2, 2, lambda i, f: None)
    _, second = _play(fake, 2, 2, lambda i, f: f.key_of(i['response_id']))
    prev = second['result']['previous']
    assert prev and prev['verdict'] == 'clearly_up'
    _play(fake, 2, 2, lambda i, f: None)
    with pytest.raises(cp.PlacementError) as e:
        cp.start(USER, 2, 2)
    assert e.value.status == 429


def test_disabled_language_is_404(fake, monkeypatch):
    monkeypatch.setattr(cp.Config, 'PLACEMENT_ENABLED_LANGS', '1')
    with pytest.raises(cp.PlacementError) as e:
        cp.start(USER, 3, 2)
    assert e.value.status == 404


def test_foreign_session_is_404(fake):
    out = cp.start(USER, 3, 2)
    with pytest.raises(cp.PlacementError) as e:
        cp.answer('someone-else', out['session_id'], out['item']['response_id'], 0, 1000)
    assert e.value.status == 404


def test_evidence_items_follow_the_table():
    words = [dict(sense_id=1, meaning='right', reading_ready=True, reading='K'),
             dict(sense_id=2, meaning='right', reading_ready=True, reading='KT'),
             dict(sense_id=3, meaning='right', reading_ready=True, reading='idk'),
             dict(sense_id=4, meaning='wrong'), dict(sense_id=5, meaning='idk'),
             dict(sense_id=6, meaning='right', reading_ready=False),
             dict(sense_id=7, meaning='right', reading_ready=True, reading='right')]
    assert pe.items_for(words) == [{'sense_id': 1, 'is_correct': True}, {'sense_id': 4, 'is_correct': False},
                                   {'sense_id': 5, 'is_correct': False}, {'sense_id': 6, 'is_correct': True},
                                   {'sense_id': 7, 'is_correct': True}]


def test_stop_reasons_cap_and_exhausted(monkeypatch):
    fake = FakePlacementSQL(words_per_band=3, seed=2).install(monkeypatch)
    _, last = _play(fake, 2, 2, lambda i, f: None)
    assert last['result'] is None or last['result']['stop_reason'] == 'exhausted'
    fake2 = FakePlacementSQL(words_per_band=40, seed=3).install(monkeypatch)
    _, last2 = _play(fake2, 1, 2, lambda i, f: (f.roles_of(i['response_id']) or [None]).index('K')
                     if f.roles_of(i['response_id']) else f.key_of(i['response_id']) if i['band'] % 2 else None)
    assert last2['result']['stop_reason'] in ('cap', 'precision')


def test_time_cap(fake):
    out = cp.start(USER, 2, 2)
    sid, item = out['session_id'], out['item']
    for _ in range(60):
        r = cp.answer(USER, sid, item["response_id"], None, 30000)   # 30 s per answer: 540 s after 18
        if r['done']:
            break
        item = r['next_item']
    assert r['done'] and r['result']['stop_reason'] == 'time'


# ---------------------------------------------------------------- HTTP layer

def test_routes_validation_and_flag(client, auth_headers, monkeypatch, fake):
    r = client.post('/api/calibration/placement/start', json={'word_language_id': 9, 'definition_language_id': 2},
                    headers=auth_headers)
    assert r.status_code == 400
    monkeypatch.setattr(cp.Config, 'PLACEMENT_ENABLED_LANGS', '')
    r = client.post('/api/calibration/placement/start', json={'word_language_id': 3, 'definition_language_id': 2},
                    headers=auth_headers)
    assert r.status_code == 404
    monkeypatch.setattr(cp.Config, 'PLACEMENT_ENABLED_LANGS', '3')
    r = client.post('/api/calibration/placement/start', json={'word_language_id': 3, 'definition_language_id': 2},
                    headers=auth_headers)
    assert r.status_code == 201
    body = r.get_json()
    sid, item = body['session_id'], body['item']
    r = client.post('/api/calibration/placement/answer', json={'session_id': sid, 'response_id': item['response_id'],
                                                               'position': 7}, headers=auth_headers)
    assert r.status_code == 400
    r = client.post('/api/calibration/placement/answer', json={'session_id': sid, 'response_id': item['response_id'],
                                                               'position': None, 'latency_ms': 3000},
                    headers=auth_headers)
    assert r.status_code == 200 and 'progress' in r.get_json()
    r = client.post('/api/calibration/placement/end', json={'session_id': sid}, headers=auth_headers)
    assert r.status_code == 200 and r.get_json()['not_enough'] is True
    r = client.get('/api/calibration/placement/latest?word_language_id=3', headers=auth_headers)
    assert r.status_code == 200
    r = client.get('/api/calibration/placement/result', headers=auth_headers)
    assert r.status_code == 400


def test_unauthenticated_is_401(client):
    assert client.post('/api/calibration/placement/start', json={}).status_code == 401


def test_rate_limits_registered():
    from web.rate_limits import ENDPOINT_LIMITS
    assert 'calibration.placement_start' in ENDPOINT_LIMITS and 'calibration.placement_answer' in ENDPOINT_LIMITS


def test_config_cap_matches_owner_answer():
    assert pd.cap_for(1) == 60 and pd.cap_for(3) == 60 and pd.cap_for(2) == 40


def test_nightly_close_job(fake, monkeypatch):
    out = cp.start(USER, 3, 2)
    fake.sessions[out['session_id']]['last_activity'] -= timedelta(hours=30)
    assert cp.run_nightly_close() == {'closed': 1}
    monkeypatch.setattr(cp.Config, 'PLACEMENT_ENABLED_LANGS', '')
    assert cp.run_nightly_close()['skipped']
    from web.scheduler import JOBS
    job = next(j for j in JOBS if j.id == 'placement_close_stale_nightly')
    assert job.target == 'services.calibration_placement:run_nightly_close'
