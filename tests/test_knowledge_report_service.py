"""services/vocabulary/knowledge_report.py — entitlement seam, 402 helper, demand log (TASK-1038),
the summary service (TASK-1039) and the prestudy suggestion (TASK-1041).

Tech spec: wiki/features/knowledge-report.tech.md §6.3, §6.4, §9, §13. RPCs are faked
(tests/_knowledge_fakes.py); nothing reaches the network.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import pytest
from flask import Flask
from werkzeug.datastructures import MultiDict

from config import Config
from services import optional_rpc
from services.vocabulary import knowledge_estimate as ke
from services.vocabulary import knowledge_report as kr
from tests._knowledge_fakes import (
    DE6_JA, FRAMES, USER, FakeDB, de6_summary_rpc, empty_summary_rpc, tier_row,
)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
TODAY = NOW.date()


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    optional_rpc.reset()
    kr.reset_frame_cache()
    monkeypatch.setattr(kr, '_stub_warned', False)
    monkeypatch.setattr(Config, 'ENTITLEMENTS_ENFORCED', False)
    monkeypatch.setattr(kr, '_billing_entitlements', lambda: None)
    yield
    optional_rpc.reset()
    kr.reset_frame_cache()


@pytest.fixture()
def flask_app():
    return Flask(__name__)


def _db(summary=None, analytics=False, **kw):
    results = {'knowledge_report_summary': de6_summary_rpc() if summary is None else summary,
               'knowledge_frame_bands': FRAMES}
    results.update(kw.pop('rpc_results', {}))
    return FakeDB(tables={'users': [tier_row(analytics=analytics)], **kw.pop('tables', {})},
                  rpc_results=results, **kw)


class _Billing:
    """Stand-in for billing TASK-980's ``services.billing.entitlements``."""

    def __init__(self, limits=None, used=None):
        self.limits = limits or {}
        self.used = used or {}

    def limit(self, key):
        return self.limits.get(key)

    def usage_this_week(self, key):
        return self.used.get(key, 0)


# ---------------------------------------------------------------- 402 helper (TASK-1038)

def test_payment_required_builds_the_app_envelope_with_status_402(flask_app):
    from utils.responses import payment_required
    with flask_app.app_context():
        resp, status = payment_required('PLAN_REQUIRED', 'The word-by-word view is part of Pro.',
                                        entitlement='bkt_report_detail', required=1, current=0)
    assert status == 402
    assert resp.get_json() == {
        'status': 'error', 'error': 'The word-by-word view is part of Pro.',
        'error_code': 'PLAN_REQUIRED', 'upgrade': True,
        'entitlement': 'bkt_report_detail', 'required': 1, 'current': 0,
    }


def test_errors_table_maps_402():
    from web.errors import _API_ERRORS
    assert _API_ERRORS[402] == ('PAYMENT_REQUIRED', None)


def test_feature_flags_default_off_and_parse_env(monkeypatch):
    import config as config_module
    monkeypatch.delenv('KNOWLEDGE_REPORT_ENABLED', raising=False)
    monkeypatch.delenv('ENTITLEMENTS_ENFORCED', raising=False)
    assert config_module._env_bool('KNOWLEDGE_REPORT_ENABLED', False) is False
    assert config_module._env_bool('ENTITLEMENTS_ENFORCED', False) is False
    assert isinstance(Config.KNOWLEDGE_REPORT_ENABLED, bool) and isinstance(Config.ENTITLEMENTS_ENFORCED, bool)
    for raw, expected in (('true', True), ('1', True), ('YES', True), ('false', False), ('0', False),
                          ('', False), ('maybe', False)):
        monkeypatch.setenv('KR_TEST_FLAG', raw)
        assert config_module._env_bool('KR_TEST_FLAG', False) is expected
    monkeypatch.delenv('KR_TEST_FLAG')
    assert config_module._env_bool('KR_TEST_FLAG', True) is True


# ---------------------------------------------------------------- entitlement seam (TASK-1038)

def test_stub_free_tier_is_level_0_and_never_enforced():
    assert kr.report_detail_level(_db(analytics=False), USER) == (0, False)


def test_stub_admin_tier_is_level_1():
    assert kr.report_detail_level(_db(analytics=True), USER) == (1, False)


def test_stub_failed_tier_read_is_level_0():
    db = _db(table_errors={'users': RuntimeError('boom')})
    assert kr.report_detail_level(db, USER) == (0, False)


def test_stub_forces_enforced_false_and_warns_once(monkeypatch, caplog):
    monkeypatch.setattr(Config, 'ENTITLEMENTS_ENFORCED', True)
    with caplog.at_level(logging.WARNING, logger=kr.__name__):
        assert kr.report_detail_level(_db(), USER) == (0, False)
        assert kr.report_detail_level(_db(), USER) == (0, False)
    assert caplog.text.count('knowledge_entitlement_stub_enforce_ignored') == 1


def test_one_tier_read_per_request(flask_app):
    db = _db()
    with flask_app.test_request_context('/api/knowledge/summary', method='GET'):
        kr.report_detail_level(db, USER)
        kr.report_detail_level(db, USER)
    assert [q[0] for q in db.queries].count('users') == 1


def test_billing_module_decides_level_and_enforcement(monkeypatch):
    monkeypatch.setattr(kr, '_billing_entitlements', lambda: _Billing({'bkt_report_detail': 1}))
    monkeypatch.setattr(Config, 'ENTITLEMENTS_ENFORCED', True)
    assert kr.report_detail_level(_db(), USER) == (1, True)
    monkeypatch.setattr(kr, '_billing_entitlements', lambda: _Billing({'bkt_report_detail': 0}))
    assert kr.report_detail_level(_db(), USER) == (0, True)


def test_detail_payload_preview_only_when_level_0_and_not_enforced():
    assert kr.detail_payload(0, False) == {'level': 0, 'enforced': False, 'preview': True}
    assert kr.detail_payload(0, True)['preview'] is False
    assert kr.detail_payload(1, False)['preview'] is False


def test_gate_serves_level_1_and_logs_shadow_deny_for_level_0(flask_app, caplog):
    with flask_app.app_context():
        assert kr.entitlement_gate(_db(analytics=True), USER, 'knowledge.words') is None
        with caplog.at_level(logging.INFO, logger=kr.__name__):
            assert kr.entitlement_gate(_db(analytics=False), USER, 'knowledge.words') is None
    assert f'entitlement_shadow_deny key=bkt_report_detail route=knowledge.words user={USER[:8]}' in caplog.text
    assert USER not in caplog.text


def test_gate_enforced_level_0_returns_the_exact_402(flask_app, monkeypatch):
    monkeypatch.setattr(kr, '_billing_entitlements', lambda: _Billing({'bkt_report_detail': 0}))
    monkeypatch.setattr(Config, 'ENTITLEMENTS_ENFORCED', True)
    with flask_app.app_context():
        resp, status = kr.entitlement_gate(_db(), USER, 'knowledge.words')
    assert status == 402
    assert resp.get_json() == {'status': 'error', 'error': 'The word-by-word view is part of Pro.',
                               'error_code': 'PLAN_REQUIRED', 'upgrade': True,
                               'entitlement': 'bkt_report_detail', 'required': 1, 'current': 0}


# ---------------------------------------------------------------- demand log (TASK-1038)

@pytest.mark.parametrize('endpoint,args,expected', [
    ('knowledge.words', {}, None),                                      # the page's first load
    ('knowledge.words', {'sort': 'useful'}, None),
    ('knowledge.words', {'limit': '50', 'language_id': '3'}, None),
    ('knowledge.words', {'q': '不'}, 'search'),
    ('knowledge.words', {'q': '   '}, None),
    ('knowledge.words', {'states': 'missed_last'}, 'filter'),
    ('knowledge.words', {'bands': '6,7'}, 'filter'),
    ('knowledge.words', {'idle_days': '60'}, 'filter'),
    ('knowledge.words', {'checked_several': '1'}, 'filter'),
    ('knowledge.words', {'checked_several': '0'}, None),
    ('knowledge.words', {'list': 'hsk30_2025', 'level': '1'}, 'filter'),
    ('knowledge.words', {'sort': 'recent'}, 'sort'),
    ('knowledge.words', {'cursor': 'WyIiLDAsMCwxLDFd'}, 'load_more'),
    ('knowledge.words', {'cursor': 'WyIiXQ', 'q': 'a'}, 'load_more'),
    ('knowledge.word_detail', {}, 'word_sheet'),
    ('knowledge.list_words', {'level': 'N5'}, 'lists_tab'),
    ('knowledge.export', {'format': 'csv'}, 'export_csv'),
    ('knowledge.export', {'format': 'anki'}, 'export_anki'),
    ('knowledge.export', {'format': 'csv', 'cursor': 'abc'}, None),    # later chunks
    ('knowledge.summary', {}, None),
    ('knowledge.prestudy_suggestion', {}, None),
])
def test_pro_intent_action(endpoint, args, expected):
    assert kr.pro_intent_action(endpoint, MultiDict(args)) == expected


def test_log_pro_intent_uses_eight_characters(caplog):
    with caplog.at_level(logging.INFO, logger=kr.__name__):
        kr.log_pro_intent('search', USER)
        kr.log_pro_intent(None, USER)
    assert caplog.text.count('knowledge_pro_intent') == 1
    assert f'knowledge_pro_intent action=search user={USER[:8]}' in caplog.text


# ---------------------------------------------------------------- frame cache (§9)

def test_frame_is_cached_for_an_hour(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(kr, '_clock', lambda: clock[0])
    db = _db()
    assert kr.frame_bands(db)['3:2'] == [577, 425, 621, 655, 537, 283, 77]
    clock[0] += kr.FRAME_TTL_S - 1
    kr.frame_bands(db)
    assert len(db.rpc_calls('knowledge_frame_bands')) == 1
    clock[0] += 2
    kr.frame_bands(db)
    assert len(db.rpc_calls('knowledge_frame_bands')) == 2


def test_frame_failure_is_not_cached(monkeypatch):
    db = FakeDB(rpc_errors={'knowledge_frame_bands': 'connection reset'})
    assert kr.frame_bands(db) is None
    db.rpc_errors.clear()
    db.rpc_results['knowledge_frame_bands'] = FRAMES
    assert kr.frame_bands(db) is not None


def test_frame_for_without_a_definition_language_prefers_english():
    assert kr.frame_for(FRAMES, 3, None) == FRAMES['3:2']
    assert kr.frame_for({'3:1': [1] * 7, '3:3': [2] * 7}, 3, None) == [1] * 7
    assert kr.frame_for(FRAMES, 3, 3) is None


# ---------------------------------------------------------------- summary (TASK-1039)

def test_summary_assembles_the_de6fd05b_payload():
    db = _db()
    s = kr.summary(db, USER, 3, now=NOW)
    est = s['estimate']
    assert (est['shown'], est['kind'], est['lo'], est['hi'], est['label']) == (True, 'range', 850, 1400, 'medium')
    assert est['rel'] == pytest.approx(0.232, abs=0.001)
    assert (est['universe_words'], est['answers'], est['tick']) == (3175, 172, 1111)
    assert (est['first_answer_at'], est['last_answer_at']) == ('2026-09-13', '2026-11-15')
    assert est['reason'] is None and est['disagreement'] is False and est['definition_language_id'] == 2
    assert (s['rated_known_words'], s['tracked_words']) == (69, 251)
    assert s['detail'] == {'level': 0, 'enforced': False, 'preview': True}
    assert s['lists'] == [] and s['lists_unavailable'] is False and s['watchlist'] is None
    assert s['language'] == {'id': 3, 'code': 'ja', 'name': 'Japanese'}
    assert s['state'] is None and s['stale_days'] is None and s['few_tracked'] is False

    groups = {g['group']: g for g in s['groups']}
    assert (groups['most_common']['share_lo'], groups['most_common']['share_hi']) == (0.73, 1.0)
    assert groups['common']['shown'] is False and groups['common']['universe'] == 820
    assert (groups['mid']['share_lo'], groups['mid']['share_hi']) == (0.17, 0.47)
    assert (groups['rare']['share_lo'], groups['rare']['share_hi']) == (0.08, 0.35)
    assert (groups['most_common']['tracked'], groups['most_common']['rated_known']) == (40, 18)
    assert (groups['common']['tracked'], groups['none']['tracked']) == (100, 3)

    fam = {f['family']: f for f in s['skills']['families']}
    assert (round(fam['form_recognition']['lo'], 2), round(fam['form_recognition']['hi'], 2)) == (0.87, 0.97)
    assert (round(fam['semantic_discrimination']['lo'], 2), round(fam['semantic_discrimination']['hi'], 2)) == (0.35, 0.71)
    assert fam['form_production']['shown'] is False and fam['form_production']['meanings'] == 9
    assert s['skills']['sentence'] == {'weak': 'semantic_discrimination', 'strong': 'form_recognition'}
    assert [f['family'] for f in s['skills']['families']] == [
        'form_recognition', 'form_production', 'semantic_discrimination']

    g30 = s['growth']['d30']
    assert (g30['practised'], g30['direct_checks'], g30['met_in_texts']) == (41, 164, 44)
    assert (s['growth']['d90']['practised'], s['growth']['d90']['direct_checks']) == (83, 318)
    assert s['growth']['idle60'] == 95
    assert g30['rated_known_delta'] is None and g30['first_trend_on'] == '2026-12-01'

    assert s['missed_recent'] == {'meanings': 10, 'flagged': 1}
    assert [(st['key'], st['href']) for st in s['next_steps']] == [
        ('knowledge.next.review_practice', '/session?mode=practice&extra=reviews'),
        ('knowledge.next.take_test', '/tests')]
    assert s['pro_teaser'] == {'tracked_meanings': 251, 'missed_recent': 10,
                               'missing_next_level': None, 'next_level': None}


def test_summary_passes_the_callers_id_and_no_cal_since_without_history():
    db = _db()
    kr.summary(db, USER, 3, now=NOW)
    assert db.rpc_calls('knowledge_report_summary') == [
        {'p_user_id': USER, 'p_language_id': 3, 'p_cal_since': []}]


def test_summary_is_none_when_the_rpc_is_missing():
    db = _db(rpc_errors={'knowledge_report_summary':
                         "{'code': 'PGRST202', 'message': 'Could not find the function'}"})
    assert kr.summary(db, USER, 3, now=NOW) is None


def test_summary_is_none_when_the_frame_is_missing():
    db = _db(rpc_errors={'knowledge_frame_bands': 'PGRST202'})
    assert kr.summary(db, USER, 3, now=NOW) is None


def test_nothing_yet_is_e0_with_the_check_first():
    s = kr.summary(_db(summary=empty_summary_rpc()), USER, 3, now=NOW)
    assert s['state'] == 'E0'
    assert s['estimate']['shown'] is False and s['estimate']['definition_language_id'] is None
    assert s['next_steps'][0]['key'] == 'knowledge.next.check'
    assert s['next_steps'][0]['params'] == {'n': 70}
    assert s['pro_teaser'] == {'tracked_meanings': None, 'missed_recent': None,
                               'missing_next_level': None, 'next_level': None}
    # The frequency groups still name their (English-definition) frame sizes; no share is shown.
    assert [g['universe'] for g in s['groups']] == [77, 820, 1276, 1002]
    assert not any(g['shown'] for g in s['groups'])


def test_too_few_answers_is_e1_with_have():
    rpc = de6_summary_rpc()
    rpc['calibration']['bands'][0] = [9, 5, 3]
    rpc['calibration']['alltime_n'][0] = 9
    s = kr.summary(_db(summary=rpc), USER, 3, now=NOW)
    assert s['state'] == 'E1'
    assert (s['estimate']['reason'], s['estimate']['have']) == ('too_few_answers', 69)
    assert s['next_steps'][0] == {'key': 'knowledge.next.check', 'href': '/calibration', 'params': {'n': 1}}


def test_out_of_date_is_e1c():
    rpc = de6_summary_rpc()
    rpc['calibration']['bands'] = [[5, 2, 2]] * 7
    s = kr.summary(_db(summary=rpc), USER, 3, now=NOW)
    assert s['state'] == 'E1c' and s['estimate']['reason'] == 'out_of_date'


def test_upper_only_has_no_lower_bound():
    prof = [0, 0, 0, .01, .03, .15, .5]
    rpc = de6_summary_rpc(language_id=1)
    rpc['calibration']['bands'] = [[20, 0, round(20 * (k + (1 - k) * ke.G))] for k in prof]
    s = kr.summary(_db(summary=rpc), USER, 1, now=NOW)
    est = s['estimate']
    assert (est['kind'], est['lo'], est['hi'], est['label'], est['universe_words']) == (
        'upper_only', None, 510, 'low', 3623)


def test_disagreement_when_rated_known_in_frame_exceeds_hi():
    rpc = de6_summary_rpc()
    rpc['calibration']['rated_known_in_frame'] = 1500
    assert kr.summary(_db(summary=rpc), USER, 3, now=NOW)['estimate']['disagreement'] is True


def test_placement_style_date_names_are_accepted():
    rpc = de6_summary_rpc()
    cal = rpc['calibration']
    cal['first_at'], cal['last_at'] = cal.pop('first_answer_at'), cal.pop('last_answer_at')
    est = kr.summary(_db(summary=rpc), USER, 3, now=NOW)['estimate']
    assert (est['first_answer_at'], est['last_answer_at']) == ('2026-09-13', '2026-11-15')


def test_stale_learner_gets_the_session_first_and_stale_days():
    rpc = de6_summary_rpc(last_seen_at='2026-10-01T08:00:00+00:00')
    s = kr.summary(_db(summary=rpc), USER, 3, now=NOW)
    assert s['stale_days'] == 47
    assert s['next_steps'][0]['key'] == 'knowledge.next.session'


def test_few_tracked_words_flag_and_watchlist():
    rpc = de6_summary_rpc(tracked={'words': 12, 'meanings': 12, 'rows': 12},
                          watchlist={'items': 4, 'rated_known': 1, 'seen_not_rated': 1, 'no_evidence': 2})
    s = kr.summary(_db(summary=rpc), USER, 3, now=NOW)
    assert s['few_tracked'] is True
    assert s['watchlist'] == {'items': 4, 'rated_known': 1, 'seen_not_rated': 1, 'no_evidence': 2}


# ---------------------------------------------------------------- growth from snapshots (§2.10)

def _snapshot(days_ago, **kw):
    row = {'user_id': USER, 'language_id': 3,
           'snapshot_date': (TODAY - timedelta(days=days_ago)).isoformat(),
           'method_version': ke.METHOD_VERSION, 'rated_known_words': 50,
           'cal_definition_language_id': 2, 'cal_bands': ke.bands_to_snapshot(DE6_JA),
           'frame_bands': FRAMES['3:2'], 'cal_first_answer_at': '2026-09-13T09:00:00+00:00',
           'cal_last_answer_at': '2026-10-17T10:00:00+00:00'}
    row.update(kw)
    return row


def _since_payload(bands):
    def respond(params):
        rpc = de6_summary_rpc()
        rpc['calibration']['since'] = [
            {'since': ts, 'bands': bands, 'first_answer_at': '2026-11-01T09:00:00+00:00',
             'last_answer_at': '2026-11-15T10:00:00+00:00'} for ts in params['p_cal_since']]
        return rpc
    return respond


def test_anchor_feeds_p_cal_since_and_the_estimate_comparison():
    db = _db(tables={'user_knowledge_snapshots': [_snapshot(30), _snapshot(91)]},
             rpc_results={'knowledge_report_summary': _since_payload([[30, 0, 29]] * 7)})
    s = kr.summary(db, USER, 3, now=NOW)
    assert db.rpc_calls('knowledge_report_summary')[0]['p_cal_since'] == ['2026-10-17T10:00:00+00:00']
    g30 = s['growth']['d30']
    assert g30['anchor_date'] == (TODAY - timedelta(days=30)).isoformat()
    assert g30['rated_known_delta'] == 19
    change = g30['estimate_change']
    assert change['verdict'] == 'higher'
    assert change['then'] == {'lo': 850, 'hi': 1400, 'kind': 'range',
                              'first_answer_at': '2026-09-13', 'last_answer_at': '2026-10-17'}
    assert (change['now']['first_answer_at'], change['now']['last_answer_at']) == ('2026-11-01', '2026-11-15')
    assert s['growth']['d90']['anchor_date'] == (TODAY - timedelta(days=91)).isoformat()


def test_comparison_dropped_when_the_definition_language_changed():
    db = _db(tables={'user_knowledge_snapshots': [_snapshot(30, cal_definition_language_id=1)]},
             rpc_results={'knowledge_report_summary': _since_payload([[30, 0, 29]] * 7)})
    g30 = kr.summary(db, USER, 3, now=NOW)['growth']['d30']
    assert g30['rated_known_delta'] == 19 and g30['estimate_change'] is None


def test_young_history_shows_the_first_trend_date():
    db = _db(tables={'user_knowledge_snapshots': [_snapshot(10)]})
    g30 = kr.summary(db, USER, 3, now=NOW)['growth']['d30']
    assert g30['anchor_date'] is None and g30['first_trend_on'] == (TODAY + timedelta(days=4)).isoformat()


def test_snapshot_read_fetches_the_earliest_row_only_when_a_window_has_no_anchor():
    full = _db(tables={'user_knowledge_snapshots': [_snapshot(30), _snapshot(91)]})
    kr.summary(full, USER, 3, now=NOW)
    assert [q[0] for q in full.queries].count('user_knowledge_snapshots') == 1
    gap = _db(tables={'user_knowledge_snapshots': [_snapshot(150, cal_last_answer_at=None), _snapshot(30)]})
    s = kr.summary(gap, USER, 3, now=NOW)
    assert [q[0] for q in gap.queries].count('user_knowledge_snapshots') == 2
    assert s['growth']['d90']['since'] is True
    assert s['growth']['d90']['anchor_date'] == (TODAY - timedelta(days=150)).isoformat()


def test_missing_snapshot_table_is_no_history():
    db = _db(table_errors={'user_knowledge_snapshots': RuntimeError('relation does not exist')})
    s = kr.summary(db, USER, 3, now=NOW)
    assert s['growth']['d30']['first_trend_on'] == '2026-12-01'


def test_snapshot_read_is_memoised_per_request(flask_app):
    db = _db(tables={'user_knowledge_snapshots': [_snapshot(30), _snapshot(91)]})
    with flask_app.test_request_context('/api/knowledge/summary', method='GET'):
        kr.load_snapshots(db, USER, 3, TODAY)
        kr.load_snapshots(db, USER, 3, TODAY)
    assert [q[0] for q in db.queries].count('user_knowledge_snapshots') == 1


# ---------------------------------------------------------------- prestudy suggestion (TASK-1041)

RECOMMENDED = [
    {'test_id': 'aaaaaaaa-0000-0000-0000-000000000001', 'slug': 'dictation-1', 'test_type': 'dictation',
     'title': 'D'},
    {'test_id': 'bbbbbbbb-0000-0000-0000-000000000002', 'slug': 'a-day-out', 'test_type': 'reading',
     'title': 'A day out'},
    {'test_id': 'cccccccc-0000-0000-0000-000000000003', 'slug': 'later', 'test_type': 'listening',
     'title': 'Later'},
]


def _plans(share, unknown=13, n=50):
    def plan_for_tests(db, user_id, language_id, tests):
        _plans.calls.append((user_id, language_id, tests))
        return {tests[0]['id']: {'unknown_share': share, 'unknown': unknown, 'n': n, 'plan_mode': 'full'}}
    return plan_for_tests


def test_prestudy_suggestion_strictly_above_a_quarter(monkeypatch):
    from services import prestudy
    _plans.calls = []
    db = FakeDB(rpc_results={'get_recommended_tests': RECOMMENDED})
    monkeypatch.setattr(prestudy, 'plan_for_tests', _plans(0.25))
    assert kr.prestudy_suggestion(db, USER, 3) is None
    monkeypatch.setattr(prestudy, 'plan_for_tests', _plans(0.26))
    assert kr.prestudy_suggestion(db, USER, 3) == {
        'test_id': 'bbbbbbbb-0000-0000-0000-000000000002', 'slug': 'a-day-out', 'title': 'A day out',
        'test_type': 'reading', 'unknown': 13, 'n': 50, 'unknown_share': 0.26}
    assert db.rpc_calls('get_recommended_tests')[0] == {'p_user_id': USER, 'p_language_id': 3}
    assert _plans.calls[-1] == (USER, 3, [{'id': 'bbbbbbbb-0000-0000-0000-000000000002',
                                           'test_type': 'reading'}])


def test_prestudy_suggestion_none_without_reading_or_listening(monkeypatch):
    from services import prestudy
    monkeypatch.setattr(prestudy, 'plan_for_tests', _plans(0.9))
    db = FakeDB(rpc_results={'get_recommended_tests': RECOMMENDED[:1]})
    assert kr.prestudy_suggestion(db, USER, 3) is None


def test_prestudy_suggestion_none_when_the_rpc_raises(monkeypatch, caplog):
    db = FakeDB(rpc_errors={'get_recommended_tests': 'statement timeout'})
    with caplog.at_level(logging.INFO, logger=kr.__name__):
        assert kr.prestudy_suggestion(db, USER, 3) is None
    assert 'get_recommended_tests failed' in caplog.text


def test_prestudy_suggestion_none_when_the_plan_raises(monkeypatch):
    from services import prestudy

    def boom(*_a, **_k):
        raise RuntimeError('timeout')
    monkeypatch.setattr(prestudy, 'plan_for_tests', boom)
    assert kr.prestudy_suggestion(FakeDB(rpc_results={'get_recommended_tests': RECOMMENDED}), USER, 3) is None


def test_prestudy_suggestion_respects_the_weekly_allowance_once_billing_exists(monkeypatch):
    from services import prestudy
    monkeypatch.setattr(prestudy, 'plan_for_tests', _plans(0.6))
    db = FakeDB(rpc_results={'get_recommended_tests': RECOMMENDED})
    monkeypatch.setattr(kr, '_billing_entitlements',
                        lambda: _Billing({'prestudy_per_week': 3}, {'prestudy_per_week': 3}))
    assert kr.prestudy_suggestion(db, USER, 3) is None
    monkeypatch.setattr(kr, '_billing_entitlements',
                        lambda: _Billing({'prestudy_per_week': 3}, {'prestudy_per_week': 2}))
    assert kr.prestudy_suggestion(db, USER, 3) is not None
