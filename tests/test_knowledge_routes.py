"""routes/knowledge.py — /api/knowledge/summary (TASK-1039) and /prestudy-suggestion (TASK-1041).

Tech spec §6.2 guards, in order: JWT (401) → language_id required (400) → learner token (403 for
a non-UUID identity such as the batch service account) → language ∈ {1, 2, 3} (400) →
RPC available (503). The report is always on (no feature switch). The RPCs are faked behind ``get_db``
(tests/_knowledge_fakes.py); auth goes through the conftest mock (pattern:
tests/test_word_list_import_routes.py).
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

import routes.knowledge as knowledge_routes
from middleware.auth import clear_auth_cache
from services import optional_rpc
from services.vocabulary import knowledge_report as kr
from tests._knowledge_fakes import FRAMES, USER, FakeDB, de6_summary_rpc, tier_row
from web.rate_limits import ENDPOINT_LIMITS

AUTH = {'Authorization': 'Bearer learner-token'}


@pytest.fixture(autouse=True)
def _state(monkeypatch):
    clear_auth_cache()
    optional_rpc.reset()
    kr.reset_frame_cache()
    monkeypatch.setattr(kr, '_billing_entitlements', lambda: None)
    yield
    clear_auth_cache()
    optional_rpc.reset()
    kr.reset_frame_cache()


@pytest.fixture()
def learner(app, mock_supabase):
    """The conftest mock authenticates every token as this UUID learner."""
    mock_supabase.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id=USER, email='learner@example.com'))
    return app


@pytest.fixture()
def fake_db(monkeypatch):
    db = FakeDB(tables={'users': [tier_row()]},
                rpc_results={'knowledge_report_summary': de6_summary_rpc(),
                             'knowledge_frame_bands': FRAMES})
    monkeypatch.setattr(knowledge_routes, 'get_db', lambda: db)
    return db


def _get(client, path, headers=AUTH):
    return client.get(path, headers=headers)


# ---------------------------------------------------------------- guards

def test_summary_requires_a_token(learner, client, fake_db):
    resp = client.get('/api/knowledge/summary?language_id=3')
    assert resp.status_code == 401
    assert fake_db.rpcs == []


@pytest.mark.parametrize('query', ['', '?language_id=', '?language_id=abc', '?language_id=0'])
def test_summary_requires_language_id(learner, client, fake_db, query):
    resp = _get(client, f'/api/knowledge/summary{query}')
    assert resp.status_code == 400
    assert resp.get_json()['error_code'] == 'BAD_REQUEST'


def test_summary_rejects_an_unknown_language(learner, client, fake_db):
    resp = _get(client, '/api/knowledge/summary?language_id=9')
    assert resp.status_code == 400 and resp.get_json()['error'] == 'Unsupported language_id'
    assert fake_db.rpcs == []


def test_batch_service_token_is_forbidden(learner, client, fake_db, monkeypatch):
    monkeypatch.setenv('BATCH_SERVICE_TOKEN', 'batch-secret')
    resp = _get(client, '/api/knowledge/summary?language_id=3',
                headers={'Authorization': 'Bearer batch-secret'})
    assert resp.status_code == 403
    assert resp.get_json() == {'status': 'error', 'error': 'Learner token required', 'error_code': 'FORBIDDEN'}
    assert fake_db.rpcs == []


def test_non_uuid_learner_is_forbidden(app, client, fake_db):
    # The conftest mock's default user id is not a UUID.
    assert _get(client, '/api/knowledge/summary?language_id=3').status_code == 403


def test_rpc_missing_is_503(learner, client, fake_db):
    fake_db.rpc_errors['knowledge_report_summary'] = "{'code': 'PGRST202'}"
    resp = _get(client, '/api/knowledge/summary?language_id=3')
    assert resp.status_code == 503
    assert resp.get_json()['error_code'] == 'SERVICE_UNAVAILABLE'


def test_rpc_returning_nothing_is_503(learner, client, fake_db):
    fake_db.rpc_results['knowledge_report_summary'] = None
    assert _get(client, '/api/knowledge/summary?language_id=3').status_code == 503


def test_unexpected_error_is_a_500_with_the_routes_message(learner, client, fake_db, monkeypatch):
    learner.debug = False

    def boom(*_a, **_k):
        raise RuntimeError('kaboom')
    monkeypatch.setattr(kr, 'summary', boom)
    resp = _get(client, '/api/knowledge/summary?language_id=3')
    assert resp.status_code == 500
    assert resp.get_json()['error'] == 'Failed to load your vocabulary summary'
    assert resp.headers['Cache-Control'] == 'private, no-store'


# ---------------------------------------------------------------- summary

def test_summary_envelope_and_headers(learner, client, fake_db):
    resp = _get(client, '/api/knowledge/summary?language_id=3')
    assert resp.status_code == 200
    assert resp.headers['Cache-Control'] == 'private, no-store'
    body = resp.get_json()
    assert body['status'] == 'success'
    for key in ('language_id', 'as_of', 'detail', 'estimate', 'rated_known_words', 'tracked_words',
                'groups', 'lists', 'lists_unavailable', 'watchlist', 'growth', 'skills',
                'missed_recent', 'next_steps', 'pro_teaser'):
        assert key in body, key
    assert body['detail'] == {'level': 0, 'enforced': False, 'preview': True}
    assert (body['estimate']['lo'], body['estimate']['hi'], body['estimate']['label']) == (850, 1400, 'medium')
    assert body['lists'] == [] and body['lists_unavailable'] is False


def test_p_user_id_is_always_the_callers(learner, client, fake_db):
    resp = _get(client, '/api/knowledge/summary?language_id=3&user_id=00000000-0000-0000-0000-000000000000'
                        '&p_user_id=00000000-0000-0000-0000-000000000000')
    assert resp.status_code == 200
    calls = fake_db.rpc_calls('knowledge_report_summary')
    assert calls == [{'p_user_id': USER, 'p_language_id': 3, 'p_cal_since': []}]
    users_reads = [q for q in fake_db.queries if q[0] == 'users']
    assert users_reads and all(('id', '==', USER) in q[1] for q in users_reads)
    snap_reads = [q for q in fake_db.queries if q[0] == 'user_knowledge_snapshots']
    assert snap_reads and all(('user_id', '==', USER) in q[1] for q in snap_reads)


def test_stub_ignores_entitlements_enforced(learner, client, fake_db, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, 'ENTITLEMENTS_ENFORCED', True)
    monkeypatch.setattr(kr, '_stub_warned', False)
    body = _get(client, '/api/knowledge/summary?language_id=3').get_json()
    assert body['detail'] == {'level': 0, 'enforced': False, 'preview': True}


def test_summary_never_returns_402(learner, client, fake_db, monkeypatch):
    from config import Config

    class _Billing:
        @staticmethod
        def limit(_key):
            return 0
    monkeypatch.setattr(kr, '_billing_entitlements', lambda: _Billing)
    monkeypatch.setattr(Config, 'ENTITLEMENTS_ENFORCED', True)
    resp = _get(client, '/api/knowledge/summary?language_id=3')
    assert resp.status_code == 200
    assert resp.get_json()['detail'] == {'level': 0, 'enforced': True, 'preview': False}


def test_rate_limits_are_registered_as_specified():
    assert ENDPOINT_LIMITS['knowledge.summary'][0][0] == '30 per minute; 600 per hour'
    assert ENDPOINT_LIMITS['knowledge.prestudy_suggestion'][0][0] == '30 per minute; 300 per hour'


# ---------------------------------------------------------------- page and Me row (TASK-1040)

def test_knowledge_page_serves_its_template(app, client):
    resp = client.get('/knowledge')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for element_id in ('knEstimate', 'knGroups', 'knGrowth', 'knSkills', 'knNext', 'knProTeaser', 'knSheet'):
        assert f'id="{element_id}"' in html
    assert 'js/pages/knowledge.js' in html and 'css/pages/knowledge.css' in html
    stage = html[html.index('ld-screen kn-page'):html.index('id="knSheet"')]
    assert 'style=' not in stage                                   # tokens and classes only


def test_me_row_is_first(app, client):
    html = client.get('/profile').get_data(as_text=True)
    hub = html[html.index('me-links'):]
    assert 'meKnowledgeRow' in hub
    assert hub.index('meKnowledgeRow') < hub.index('href="/study-plan"')     # first study tool
    assert 'data-i18n="common.nav.knowledge"' in html and 'data-i18n="me.knowledge_sub"' in html


# ---------------------------------------------------------------- prestudy suggestion (TASK-1041)

def test_prestudy_suggestion_route_returns_the_suggestion(learner, client, fake_db, monkeypatch):
    seen = {}

    def fake(db, user_id, language_id):
        seen.update(db=db, user_id=user_id, language_id=language_id)
        return {'test_id': 't', 'slug': 'a-day-out', 'title': 'A day out', 'test_type': 'reading',
                'unknown': 13, 'n': 50, 'unknown_share': 0.26}
    monkeypatch.setattr(kr, 'prestudy_suggestion', fake)
    resp = _get(client, '/api/knowledge/prestudy-suggestion?language_id=3')
    assert resp.status_code == 200
    assert resp.headers['Cache-Control'] == 'private, no-store'
    assert resp.get_json()['suggestion']['slug'] == 'a-day-out'
    assert seen == {'db': fake_db, 'user_id': USER, 'language_id': 3}


def test_prestudy_suggestion_rpc_error_is_null_not_5xx(learner, client, fake_db, caplog):
    fake_db.rpc_errors['get_recommended_tests'] = 'statement timeout'
    with caplog.at_level(logging.INFO):
        resp = _get(client, '/api/knowledge/prestudy-suggestion?language_id=3')
    assert resp.status_code == 200
    assert resp.get_json() == {'status': 'success', 'suggestion': None}


def test_prestudy_suggestion_guards(learner, client, fake_db, monkeypatch):
    assert client.get('/api/knowledge/prestudy-suggestion?language_id=3').status_code == 401
    assert _get(client, '/api/knowledge/prestudy-suggestion').status_code == 400
    assert _get(client, '/api/knowledge/prestudy-suggestion?language_id=7').status_code == 400
    monkeypatch.setenv('BATCH_SERVICE_TOKEN', 'batch-secret')
    assert _get(client, '/api/knowledge/prestudy-suggestion?language_id=3',
                headers={'Authorization': 'Bearer batch-secret'}).status_code == 403
