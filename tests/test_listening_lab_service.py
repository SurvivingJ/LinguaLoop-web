# tests/test_listening_lab_service.py
"""Unit tests for ListeningLabService.

The service is a thin wrapper around Supabase: table queries for reads,
RPC calls for the three stored procedures. These tests assert it calls
the right tables/RPCs with the right args and handles the standard
success/failure response shapes — they do NOT exercise the actual SQL,
which is covered by the Phase 7 MCP integration checks separately.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.listening_lab_service import ListeningLabService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chain(data, count=None):
    """Chainable MagicMock matching the Supabase client query shape."""
    chain = MagicMock()
    result = SimpleNamespace(data=data, count=count or 0)
    chain.execute.return_value = result
    for m in ('select', 'eq', 'neq', 'lt', 'lte', 'gt', 'gte', 'is_',
              'not_', 'single', 'order', 'or_', 'in_',
              'limit', 'offset', 'range', 'insert', 'update', 'delete',
              'filter', 'rpc'):
        getattr(chain, m).return_value = chain
    return chain


def _make_admin_with_rpc(rpc_data):
    """Build an admin mock whose rpc().execute() returns the supplied data."""
    admin = MagicMock()
    rpc_chain = MagicMock()
    rpc_chain.execute.return_value = SimpleNamespace(data=rpc_data)
    admin.rpc.return_value = rpc_chain
    return admin


def _service(admin=None):
    """ListeningLabService with both clients set to the same mock so we can
    assert against either property."""
    admin = admin or MagicMock()
    return ListeningLabService(supabase_client=admin, supabase_admin=admin)


# ---------------------------------------------------------------------------
# _flatten_passage (static)
# ---------------------------------------------------------------------------

class TestFlattenPassage:

    def test_pulls_test_columns_to_top_level(self):
        row = {
            'id': 'passage-1', 'test_id': 'test-1',
            'tests': {
                'slug': 'my-test', 'title': 'My Test',
                'difficulty': 5, 'transcript': 'hello world',
            },
        }
        flat = ListeningLabService._flatten_passage(row)
        assert flat['test_slug'] == 'my-test'
        assert flat['title'] == 'My Test'
        assert flat['difficulty'] == 5
        assert flat['transcript'] == 'hello world'
        # The embedded dict should be removed.
        assert 'tests' not in flat

    def test_handles_list_embed(self):
        """Sometimes Supabase returns the join as a single-element list."""
        row = {
            'id': 'p1',
            'tests': [{'slug': 's', 'title': 't', 'difficulty': 1}],
        }
        flat = ListeningLabService._flatten_passage(row)
        assert flat['test_slug'] == 's'
        assert flat['title'] == 't'

    def test_missing_tests_does_not_explode(self):
        flat = ListeningLabService._flatten_passage({'id': 'p1', 'tests': None})
        assert flat['test_slug'] is None
        assert flat['title'] is None


# ---------------------------------------------------------------------------
# list_passages
# ---------------------------------------------------------------------------

class TestListPassages:

    def test_filters_by_language_and_active(self):
        admin = MagicMock()
        chain = _make_chain([
            {'id': 'p1', 'test_id': 't1', 'language_id': 1, 'voice_id': 'v',
             'pool_size': 20, 'enrolled_at': '2026-05-17',
             'tests': {'slug': 's', 'title': 'T', 'difficulty': 3}},
        ])
        admin.table.return_value = chain

        result = _service(admin).list_passages(language_id=1)

        admin.table.assert_called_with('listening_lab_passages')
        chain.eq.assert_any_call('is_active', True)
        chain.eq.assert_any_call('language_id', 1)
        assert len(result) == 1
        assert result[0]['test_slug'] == 's'

    def test_applies_difficulty_filter(self):
        admin = MagicMock()
        chain = _make_chain([])
        admin.table.return_value = chain

        _service(admin).list_passages(language_id=1, difficulty=5)

        chain.eq.assert_any_call('tests.difficulty', 5)

    def test_swallows_errors_returning_empty(self):
        admin = MagicMock()
        admin.table.side_effect = Exception("boom")

        result = _service(admin).list_passages(language_id=1)
        assert result == []


# ---------------------------------------------------------------------------
# get_passage_by_slug
# ---------------------------------------------------------------------------

class TestGetPassageBySlug:

    def test_returns_none_for_empty_slug(self):
        result = _service().get_passage_by_slug('')
        assert result is None

    def test_returns_none_when_no_row(self):
        admin = MagicMock()
        admin.table.return_value = _make_chain([])
        result = _service(admin).get_passage_by_slug('missing-slug')
        assert result is None

    def test_flattens_test_metadata(self):
        admin = MagicMock()
        admin.table.return_value = _make_chain([{
            'id': 'p1', 'test_id': 't1', 'language_id': 1,
            'audio_url_075': 'r2/a.mp3', 'audio_url_090': 'r2/b.mp3',
            'audio_url_100': 'r2/c.mp3', 'audio_url_115': 'r2/d.mp3',
            'voice_id': 'v', 'pool_size': 20, 'is_active': True,
            'tests': {
                'slug': 'my-test', 'title': 'Title', 'difficulty': 5,
                'transcript': 'hi', 'language_id': 1,
            },
        }])

        result = _service(admin).get_passage_by_slug('my-test')
        assert result['id'] == 'p1'
        assert result['test_slug'] == 'my-test'
        assert result['title'] == 'Title'
        assert result['audio_url_075'] == 'r2/a.mp3'


# ---------------------------------------------------------------------------
# get_recommended
# ---------------------------------------------------------------------------

class TestGetRecommended:

    def test_calls_correct_rpc_with_user_and_language(self):
        admin = _make_admin_with_rpc([{'passage_id': 'p1', 'elo_gap': 12}])
        result = _service(admin).get_recommended('user-uuid', language_id=2)

        admin.rpc.assert_called_once_with(
            'get_listening_lab_recommendations',
            {'p_user_id': 'user-uuid', 'p_language_id': 2},
        )
        assert result == [{'passage_id': 'p1', 'elo_gap': 12}]

    def test_returns_empty_on_error(self):
        admin = MagicMock()
        admin.rpc.side_effect = Exception("rpc died")
        assert _service(admin).get_recommended('u', 1) == []


# ---------------------------------------------------------------------------
# get_active_session
# ---------------------------------------------------------------------------

class TestGetActiveSession:

    def test_returns_first_row_when_present(self):
        admin = MagicMock()
        admin.table.return_value = _make_chain([{'id': 'sess-1', 'current_tier': 2}])
        s = _service(admin).get_active_session('user', 'passage')
        assert s == {'id': 'sess-1', 'current_tier': 2}

    def test_returns_none_when_no_active_session(self):
        admin = MagicMock()
        admin.table.return_value = _make_chain([])
        assert _service(admin).get_active_session('user', 'passage') is None


# ---------------------------------------------------------------------------
# start_session
# ---------------------------------------------------------------------------

class TestStartSession:

    def test_returns_rpc_payload_on_success(self):
        admin = _make_admin_with_rpc({
            'success': True, 'session_id': 'sess-1', 'tier': 0,
            'speed': 0.75, 'audio_url': 'r2/x.mp3', 'questions': [],
        })
        result = _service(admin).start_session('user', 'passage')

        admin.rpc.assert_called_once_with(
            'start_listening_lab_session',
            {'p_user_id': 'user', 'p_passage_id': 'passage'},
        )
        assert result['session_id'] == 'sess-1'
        assert result['success'] is True

    def test_unwraps_list_payload(self):
        """SECURITY DEFINER functions sometimes return their jsonb wrapped
        in a single-element list. The service should normalize that."""
        admin = MagicMock()
        rpc_chain = MagicMock()
        rpc_chain.execute.return_value = SimpleNamespace(
            data=[{'success': True, 'session_id': 'sess-1'}]
        )
        admin.rpc.return_value = rpc_chain

        result = _service(admin).start_session('user', 'passage')
        assert result['session_id'] == 'sess-1'

    def test_returns_failure_envelope_on_rpc_error_payload(self):
        admin = _make_admin_with_rpc({
            'success': False, 'error': 'Passage not found or inactive',
        })
        result = _service(admin).start_session('user', 'passage')
        assert result['success'] is False
        assert 'not found' in result['error'].lower()


# ---------------------------------------------------------------------------
# submit_tier
# ---------------------------------------------------------------------------

class TestSubmitTier:

    def test_calls_submit_listening_lab_tier_with_correct_args(self):
        admin = _make_admin_with_rpc({
            'success': True, 'tier': 0, 'score': 4, 'passed': True,
        })
        responses = [{'question_id': 'q1', 'selected_answer': 'A'}]

        _service(admin).submit_tier(
            'user-id', 'sess-id', tier=0, responses=responses,
            idempotency_key='idem-1',
        )

        admin.rpc.assert_called_once()
        rpc_name, params = admin.rpc.call_args[0]
        assert rpc_name == 'submit_listening_lab_tier'
        assert params['p_user_id'] == 'user-id'
        assert params['p_session_id'] == 'sess-id'
        assert params['p_tier'] == 0
        assert params['p_responses'] == responses
        assert params['p_idempotency_key'] == 'idem-1'

    def test_generates_idempotency_key_when_not_provided(self):
        admin = _make_admin_with_rpc({'success': True})
        _service(admin).submit_tier('u', 's', 0, [{'question_id': 'q'}])

        params = admin.rpc.call_args[0][1]
        # Should be a stringified UUID, not None.
        assert params['p_idempotency_key']
        assert isinstance(params['p_idempotency_key'], str)
        assert len(params['p_idempotency_key']) >= 32

    def test_coerces_tier_to_int(self):
        """Routes pass tier as int already, but the service should be defensive
        — Supabase chokes on numpy ints or numeric strings."""
        admin = _make_admin_with_rpc({'success': True})
        _service(admin).submit_tier('u', 's', tier='2', responses=[{'q': 1}])
        assert admin.rpc.call_args[0][1]['p_tier'] == 2


# ---------------------------------------------------------------------------
# abandon_session
# ---------------------------------------------------------------------------

class TestAbandonSession:

    def test_returns_true_when_row_updated(self):
        admin = MagicMock()
        admin.table.return_value = _make_chain([{'id': 'sess-1'}])
        ok = _service(admin).abandon_session('user', 'sess-1')
        assert ok is True

    def test_returns_false_when_no_row_matched(self):
        admin = MagicMock()
        admin.table.return_value = _make_chain([])
        ok = _service(admin).abandon_session('user', 'sess-1')
        assert ok is False

    def test_returns_false_on_exception(self):
        admin = MagicMock()
        admin.table.side_effect = Exception("network")
        assert _service(admin).abandon_session('u', 's') is False
