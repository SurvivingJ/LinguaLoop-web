# tests/test_listening_lab_routes.py
"""Blueprint smoke tests for the Listening Lab routes.

These exercise request validation, response shape, and that the route
handlers call the service with the right args. The service itself is
mocked — its behavior is tested separately in test_listening_lab_service.py.
"""

import json
import pytest
from unittest.mock import MagicMock, patch


def resp_json(resp):
    return json.loads(resp.data)


@pytest.fixture()
def mock_service():
    """A ListeningLabService mock with stub methods that return empty/None."""
    svc = MagicMock()
    svc.list_passages.return_value = []
    svc.get_recommended.return_value = []
    svc.get_passage_by_slug.return_value = None
    svc.get_active_session.return_value = None
    svc.start_session.return_value = {'success': True, 'session_id': 'sess-1'}
    svc.submit_tier.return_value = {'success': True, 'tier': 0, 'score': 4, 'passed': True}
    svc.abandon_session.return_value = True
    return svc


def _patch_service(svc):
    """Context manager that swaps the singleton-getter for the duration of the call."""
    return patch('routes.listening_lab.get_listening_lab_service', return_value=svc)


# ---------------------------------------------------------------------------
# GET /api/listening-lab/
# ---------------------------------------------------------------------------

class TestListPassages:

    def test_requires_language_id(self, client, auth_headers, mock_service):
        with _patch_service(mock_service):
            resp = client.get('/api/listening-lab/', headers=auth_headers)
        assert resp.status_code == 400
        assert 'language_id' in resp_json(resp).get('error', '').lower()

    def test_returns_passages(self, client, auth_headers, mock_service):
        mock_service.list_passages.return_value = [
            {'id': 'p1', 'test_slug': 'my-test', 'title': 'My Test',
             'difficulty': 5, 'language_id': 1, 'voice_id': 'v', 'pool_size': 20},
        ]
        with _patch_service(mock_service):
            resp = client.get('/api/listening-lab/?language_id=1', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['status'] == 'success'
        assert len(data['passages']) == 1
        assert data['passages'][0]['test_slug'] == 'my-test'

    def test_forwards_difficulty_and_limit(self, client, auth_headers, mock_service):
        with _patch_service(mock_service):
            resp = client.get(
                '/api/listening-lab/?language_id=1&difficulty=5&limit=25',
                headers=auth_headers,
            )
        assert resp.status_code == 200
        mock_service.list_passages.assert_called_once()
        kwargs = mock_service.list_passages.call_args.kwargs
        args = mock_service.list_passages.call_args.args
        assert (args and args[0] == 1) or kwargs.get('language_id') == 1
        assert kwargs.get('difficulty') == 5
        assert kwargs.get('limit') == 25


# ---------------------------------------------------------------------------
# GET /api/listening-lab/recommended
# ---------------------------------------------------------------------------

class TestRecommended:

    def test_requires_language_id(self, client, auth_headers, mock_service):
        with _patch_service(mock_service):
            resp = client.get('/api/listening-lab/recommended', headers=auth_headers)
        assert resp.status_code == 400

    def test_passes_current_user_id_to_service(self, client, auth_headers, mock_service):
        mock_service.get_recommended.return_value = [{'passage_id': 'p1'}]
        with _patch_service(mock_service):
            resp = client.get(
                '/api/listening-lab/recommended?language_id=2',
                headers=auth_headers,
            )
        assert resp.status_code == 200
        mock_service.get_recommended.assert_called_once()
        # First positional arg should be the authenticated user id.
        call_args = mock_service.get_recommended.call_args.args
        assert call_args[0] == 'test-user-id-123'


# ---------------------------------------------------------------------------
# GET /api/listening-lab/<slug>
# ---------------------------------------------------------------------------

class TestGetPassage:

    def test_404_when_slug_not_found(self, client, auth_headers, mock_service):
        mock_service.get_passage_by_slug.return_value = None
        with _patch_service(mock_service):
            resp = client.get('/api/listening-lab/no-such-slug', headers=auth_headers)
        assert resp.status_code == 404

    def test_returns_passage_and_active_session(self, client, auth_headers, mock_service):
        mock_service.get_passage_by_slug.return_value = {
            'id': 'p1', 'test_slug': 'my-test', 'title': 'T',
            'audio_url_075': 'r2/a.mp3',
        }
        mock_service.get_active_session.return_value = {
            'id': 'sess-1', 'current_tier': 1, 'tiers_passed': [0],
        }
        with _patch_service(mock_service):
            resp = client.get('/api/listening-lab/my-test', headers=auth_headers)
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['passage']['id'] == 'p1'
        assert data['active_session']['current_tier'] == 1


# ---------------------------------------------------------------------------
# POST /api/listening-lab/<slug>/start
# ---------------------------------------------------------------------------

class TestStartSession:

    def test_404_when_slug_not_found(self, client, auth_headers, mock_service):
        mock_service.get_passage_by_slug.return_value = None
        with _patch_service(mock_service):
            resp = client.post(
                '/api/listening-lab/missing/start',
                json={}, headers=auth_headers,
            )
        assert resp.status_code == 404

    def test_400_when_service_returns_failure(self, client, auth_headers, mock_service):
        mock_service.get_passage_by_slug.return_value = {'id': 'p1'}
        mock_service.start_session.return_value = {
            'success': False, 'error': 'Passage inactive',
        }
        with _patch_service(mock_service):
            resp = client.post(
                '/api/listening-lab/p1/start',
                json={}, headers=auth_headers,
            )
        assert resp.status_code == 400
        assert 'inactive' in resp_json(resp).get('error', '').lower()

    def test_returns_session_payload_on_success(self, client, auth_headers, mock_service):
        mock_service.get_passage_by_slug.return_value = {'id': 'p1'}
        mock_service.start_session.return_value = {
            'success': True, 'session_id': 'sess-1', 'tier': 0,
            'speed': 0.75, 'audio_url': 'r2/a.mp3', 'questions': [],
        }
        with _patch_service(mock_service):
            resp = client.post(
                '/api/listening-lab/p1/start',
                json={}, headers=auth_headers,
            )
        assert resp.status_code == 200
        data = resp_json(resp)
        assert data['session_id'] == 'sess-1'
        assert data['speed'] == 0.75


# ---------------------------------------------------------------------------
# POST /api/listening-lab/session/<sid>/tier/<int:tier>/submit
# ---------------------------------------------------------------------------

class TestSubmitTier:

    def _submit(self, client, headers, sid, tier, body):
        return client.post(
            f'/api/listening-lab/session/{sid}/tier/{tier}/submit',
            json=body, headers=headers,
        )

    def test_rejects_negative_tier(self, client, auth_headers, mock_service):
        # Flask's int converter blocks negatives at the routing layer, so
        # this should not match any route.
        with _patch_service(mock_service):
            resp = self._submit(
                client, auth_headers, 'sess-1', -1, {'responses': [{'q': 1}]}
            )
        assert resp.status_code == 404

    def test_rejects_tier_above_three(self, client, auth_headers, mock_service):
        with _patch_service(mock_service):
            resp = self._submit(
                client, auth_headers, 'sess-1', 4, {'responses': [{'q': 1}]}
            )
        assert resp.status_code == 400

    def test_rejects_empty_responses(self, client, auth_headers, mock_service):
        with _patch_service(mock_service):
            resp = self._submit(
                client, auth_headers, 'sess-1', 0, {'responses': []}
            )
        assert resp.status_code == 400

    def test_rejects_missing_responses(self, client, auth_headers, mock_service):
        with _patch_service(mock_service):
            resp = self._submit(client, auth_headers, 'sess-1', 0, {})
        assert resp.status_code == 400

    def test_forwards_responses_and_idempotency_key(self, client, auth_headers, mock_service):
        mock_service.submit_tier.return_value = {
            'success': True, 'tier': 0, 'score': 4, 'passed': True,
            'next_tier': 1, 'next_speed': 0.9, 'next_audio_url': 'r2/b.mp3',
            'next_questions': [],
        }
        responses = [
            {'question_id': 'q1', 'selected_answer': 'A'},
            {'question_id': 'q2', 'selected_answer': 'B'},
        ]
        with _patch_service(mock_service):
            resp = self._submit(client, auth_headers, 'sess-1', 0, {
                'responses': responses,
                'idempotency_key': 'my-idem-key',
            })
        assert resp.status_code == 200
        kwargs = mock_service.submit_tier.call_args.kwargs
        args = mock_service.submit_tier.call_args.args
        # The handler calls submit_tier(user_id, sid, tier, responses, idempotency_key=...)
        assert args[0] == 'test-user-id-123'
        assert args[1] == 'sess-1'
        assert args[2] == 0
        assert args[3] == responses
        assert kwargs.get('idempotency_key') == 'my-idem-key'

    def test_400_when_service_returns_failure(self, client, auth_headers, mock_service):
        mock_service.submit_tier.return_value = {
            'success': False, 'error': 'Session not found',
        }
        with _patch_service(mock_service):
            resp = self._submit(
                client, auth_headers, 'sess-1', 0,
                {'responses': [{'q': 1}]},
            )
        assert resp.status_code == 400

    def test_completion_triggers_bkt_helper(self, client, auth_headers, mock_service):
        """When the RPC reports completed=True, the route helper for BKT runs."""
        mock_service.submit_tier.return_value = {
            'success': True, 'tier': 3, 'passed': True, 'completed': True,
            'final_attempt_id': 'attempt-uuid',
            'elo_result': {
                'attempt_id': 'attempt-uuid',
                'question_results': [
                    {'question_id': 'q1', 'is_correct': True},
                    {'question_id': 'q2', 'is_correct': False},
                ],
            },
        }
        with _patch_service(mock_service), \
             patch('routes.listening_lab._update_listening_lab_vocabulary') as bkt_helper:
            resp = self._submit(
                client, auth_headers, 'sess-1', 3,
                {'responses': [{'question_id': 'q1', 'selected_answer': 'A'}]},
            )
        assert resp.status_code == 200
        bkt_helper.assert_called_once()


# ---------------------------------------------------------------------------
# POST /api/listening-lab/session/<sid>/abandon
# ---------------------------------------------------------------------------

class TestAbandonSession:

    def test_returns_success_when_abandoned(self, client, auth_headers, mock_service):
        mock_service.abandon_session.return_value = True
        with _patch_service(mock_service):
            resp = client.post(
                '/api/listening-lab/session/sess-1/abandon',
                json={}, headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp_json(resp).get('abandoned') is True

    def test_400_when_service_returns_false(self, client, auth_headers, mock_service):
        mock_service.abandon_session.return_value = False
        with _patch_service(mock_service):
            resp = client.post(
                '/api/listening-lab/session/sess-1/abandon',
                json={}, headers=auth_headers,
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Feature-flag gating
# ---------------------------------------------------------------------------

class TestListeningLabDisabled:
    """When LISTENING_LAB_ENABLED is False, the blueprint and web routes are
    not registered at all — every URL under /listening-lab returns 404.

    This builds its own app instance because the `client` fixture from conftest
    uses TestConfig which keeps the flag ON for the rest of the suite.
    """

    @pytest.fixture()
    def disabled_client(self):
        from unittest.mock import patch, MagicMock
        from tests.conftest import TestConfig, _make_mock_supabase

        class DisabledConfig(TestConfig):
            LISTENING_LAB_ENABLED = False

        mock_supabase = _make_mock_supabase()
        with patch('services.supabase_factory.SupabaseFactory') as MockFactory, \
             patch('services.supabase_factory.get_supabase', return_value=mock_supabase), \
             patch('services.supabase_factory.get_supabase_admin', return_value=mock_supabase), \
             patch('services.dimension_service.DimensionService'), \
             patch('app.DimensionService'), \
             patch('app.ServiceFactory'), \
             patch('app.R2Service'), \
             patch('app.PromptService'), \
             patch('app.AuthService'):
            MockFactory.initialize = MagicMock()
            MockFactory.get_anon_client.return_value = mock_supabase
            MockFactory.get_service_client.return_value = mock_supabase

            from app import create_app
            disabled_app = create_app(DisabledConfig)
            yield disabled_app.test_client()

    def test_list_endpoint_404s(self, disabled_client, auth_headers):
        resp = disabled_client.get('/api/listening-lab/?language_id=1', headers=auth_headers)
        assert resp.status_code == 404

    def test_player_web_route_404s(self, disabled_client):
        resp = disabled_client.get('/listening-lab/some-slug')
        # Flask redirects unauthenticated traffic to /login via the 404 handler,
        # so accept either a 404 or a redirect away from /listening-lab.
        assert resp.status_code in (302, 404)
        if resp.status_code == 302:
            assert '/listening-lab' not in resp.headers.get('Location', '')
