# tests/test_submission_rpc_error_envelope.py
"""Tests for the four submission-RPC wrappers (CR-04 — no SQLERRM leak).

CR-04 (code-review-2026-05-24): when ``process_test_submission`` (and its
sibling RPCs) catch an unexpected error they return
``{success:false, error:SQLERRM, error_detail:SQLSTATE}``. The wrapper
helpers in ``routes/tests.py`` then forward that payload (or the surrounding
caller surfaces ``rpc_result['error']`` verbatim), leaking Postgres internals
to clients.

Hardened contract for ``_call_*_submission_rpc``:

* RPC returns ``{success:true,...}`` -> helper returns the dict unchanged.
* RPC returns ``{success:false,...}`` (normal response OR via the supabase-py
  JSONB-throws-exception quirk) -> helper returns a Flask
  ``(jsonify({...}), 500)`` tuple whose body is a generic
  ``{error: "submission_failed", error_code: "..."}`` envelope. The body
  must NOT include raw SQLERRM text or table/column hints, and must NOT
  include the helper-internal ``error_detail`` or ``sqlstate`` payload that
  upstream produced.
* The full upstream payload must still be logged server-side so operators
  can debug.
"""

import json
from unittest.mock import MagicMock

import pytest

from routes.tests import (
    _call_submission_rpc,
    _call_dictation_submission_rpc,
    _call_pinyin_submission_rpc,
    _call_pitch_accent_submission_rpc,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SQLERRM_LEAK = (
    'duplicate key value violates unique constraint '
    '"test_attempts_pkey" — DETAIL: Key (id)=(...) already exists.'
)


def _make_rpc_client(return_data=None, raise_exc=None):
    """Build a mock Supabase client whose .rpc(...).execute() either returns
    a response object with `.data` set, or raises `raise_exc`."""
    client = MagicMock()
    rpc_chain = MagicMock()
    if raise_exc is not None:
        rpc_chain.execute.side_effect = raise_exc
    else:
        rpc_chain.execute.return_value = MagicMock(data=return_data)
    client.rpc.return_value = rpc_chain
    return client


def _parse_flask_error_tuple(result):
    """Helper assertions for the ``(response, status_code)`` error shape."""
    assert isinstance(result, tuple), (
        f'expected (response, status) tuple on error, got {result!r}'
    )
    response, status = result
    body = json.loads(response.get_data(as_text=True))
    return body, status


def _assert_no_sqlerrm_leak(body):
    """Body must not contain raw Postgres error text."""
    serialised = json.dumps(body)
    assert 'SQLERRM' not in serialised
    assert 'duplicate key value' not in serialised
    assert 'pkey' not in serialised
    assert 'DETAIL:' not in serialised
    assert 'error_detail' not in body


# ---------------------------------------------------------------------------
# process_test_submission
# ---------------------------------------------------------------------------

class TestCallSubmissionRPC:
    """_call_submission_rpc (process_test_submission)."""

    def test_success_response_returns_data(self, app):
        client = _make_rpc_client(return_data={
            'success': True,
            'attempt_id': 'abc-123',
            'score': 4,
            'total_questions': 5,
        })

        with app.app_context():
            result = _call_submission_rpc(
                client, 'user-1', 'test-1', 1, 1,
                db_responses=[], furigana_used=False,
            )

        assert result['success'] is True
        assert result['attempt_id'] == 'abc-123'

    def test_failure_response_does_not_forward_sqlerrm(self, app):
        """RED test for CR-04 — wrapper must NOT forward SQLERRM text."""
        client = _make_rpc_client(return_data={
            'success': False,
            'error': SQLERRM_LEAK,
            'error_detail': '23505',
        })

        with app.app_context():
            result = _call_submission_rpc(
                client, 'user-1', 'test-1', 1, 1,
                db_responses=[], furigana_used=False,
            )

        body, status = _parse_flask_error_tuple(result)
        assert status == 500
        assert body.get('error') == 'submission_failed'
        _assert_no_sqlerrm_leak(body)

    def test_jsonb_quirk_success_returns_data(self, app):
        """supabase-py raises on JSONB success responses — wrapper must
        unwrap that into a normal return."""
        class _FakeJsonbExc(Exception):
            def json(self):
                return {'success': True, 'attempt_id': 'jsonb-id'}

        client = _make_rpc_client(raise_exc=_FakeJsonbExc('jsonb response'))

        with app.app_context():
            result = _call_submission_rpc(
                client, 'user-1', 'test-1', 1, 1,
                db_responses=[], furigana_used=False,
            )

        assert isinstance(result, dict)
        assert result['success'] is True
        assert result['attempt_id'] == 'jsonb-id'

    def test_jsonb_quirk_failure_does_not_forward_sqlerrm(self, app):
        """When the supabase-py exception carries a SQLERRM payload, the
        wrapper must still return the generic envelope only."""
        class _FakeJsonbExc(Exception):
            def json(self):
                return {
                    'success': False,
                    'error': SQLERRM_LEAK,
                    'error_detail': '23505',
                }

        client = _make_rpc_client(raise_exc=_FakeJsonbExc('jsonb error'))

        with app.app_context():
            result = _call_submission_rpc(
                client, 'user-1', 'test-1', 1, 1,
                db_responses=[], furigana_used=False,
            )

        body, status = _parse_flask_error_tuple(result)
        assert status == 500
        assert body.get('error') == 'submission_failed'
        _assert_no_sqlerrm_leak(body)


# ---------------------------------------------------------------------------
# process_dictation_submission
# ---------------------------------------------------------------------------

class TestCallDictationSubmissionRPC:
    def test_success_response_returns_data(self, app):
        client = _make_rpc_client(return_data={
            'success': True, 'attempt_id': 'dict-1',
        })

        with app.app_context():
            result = _call_dictation_submission_rpc(
                client, 'user-1', 'test-1', 1, 1,
                word_correct=10, word_total=12, replay_count=0,
                diff_payload={}, idempotency_key='k',
            )

        assert result['success'] is True

    def test_failure_response_does_not_forward_sqlerrm(self, app):
        client = _make_rpc_client(return_data={
            'success': False,
            'error': SQLERRM_LEAK,
            'error_detail': '23505',
        })

        with app.app_context():
            result = _call_dictation_submission_rpc(
                client, 'user-1', 'test-1', 1, 1,
                word_correct=10, word_total=12, replay_count=0,
                diff_payload={}, idempotency_key='k',
            )

        body, status = _parse_flask_error_tuple(result)
        assert status == 500
        assert body.get('error') == 'submission_failed'
        _assert_no_sqlerrm_leak(body)


# ---------------------------------------------------------------------------
# process_pinyin_submission
# ---------------------------------------------------------------------------

class TestCallPinyinSubmissionRPC:
    def test_success_response_returns_data(self, app):
        client = _make_rpc_client(return_data={
            'success': True, 'attempt_id': 'py-1',
        })

        with app.app_context():
            result = _call_pinyin_submission_rpc(
                client, 'user-1', 'test-1', 1, 1,
                correct_chars=8, total_chars=10,
            )

        assert result['success'] is True

    def test_failure_response_does_not_forward_sqlerrm(self, app):
        client = _make_rpc_client(return_data={
            'success': False,
            'error': SQLERRM_LEAK,
            'error_detail': '23505',
        })

        with app.app_context():
            result = _call_pinyin_submission_rpc(
                client, 'user-1', 'test-1', 1, 1,
                correct_chars=8, total_chars=10,
            )

        body, status = _parse_flask_error_tuple(result)
        assert status == 500
        assert body.get('error') == 'submission_failed'
        _assert_no_sqlerrm_leak(body)


# ---------------------------------------------------------------------------
# process_pitch_accent_submission
# ---------------------------------------------------------------------------

class TestCallPitchAccentSubmissionRPC:
    def test_success_response_returns_data(self, app):
        client = _make_rpc_client(return_data={
            'success': True, 'attempt_id': 'pa-1',
        })

        with app.app_context():
            result = _call_pitch_accent_submission_rpc(
                client, 'user-1', 'test-1', 3, 1,
                correct_units=4, total_units=5, furigana_used=False,
            )

        assert result['success'] is True

    def test_failure_response_does_not_forward_sqlerrm(self, app):
        client = _make_rpc_client(return_data={
            'success': False,
            'error': SQLERRM_LEAK,
            'error_detail': '23505',
        })

        with app.app_context():
            result = _call_pitch_accent_submission_rpc(
                client, 'user-1', 'test-1', 3, 1,
                correct_units=4, total_units=5, furigana_used=False,
            )

        body, status = _parse_flask_error_tuple(result)
        assert status == 500
        assert body.get('error') == 'submission_failed'
        _assert_no_sqlerrm_leak(body)


# ---------------------------------------------------------------------------
# Caller-level guarantee: submit_test endpoint must not surface SQLERRM
# either, even if the wrapper changes shape.
# ---------------------------------------------------------------------------

def test_submit_test_endpoint_does_not_leak_sqlerrm(client, app):
    """RED test for CR-04 at the route boundary. When the RPC returns a
    failure envelope containing SQLERRM, the submit endpoint response body
    must not contain it."""
    rpc_chain = app.supabase_service.rpc.return_value
    rpc_chain.execute.return_value = MagicMock(data={
        'success': False,
        'error': SQLERRM_LEAK,
        'error_detail': '23505',
    })
    # Make the test-lookup query (used before the RPC) return something
    # usable so the endpoint reaches the RPC call.
    table_chain = app.supabase_service.table.return_value
    table_chain.select.return_value = table_chain
    table_chain.eq.return_value = table_chain
    table_chain.single.return_value = table_chain
    table_chain.execute.return_value = MagicMock(data={
        'id': 'test-id-1', 'language_id': 1,
    })

    resp = client.post(
        '/api/tests/some-slug/submit',
        data=json.dumps({
            'responses': [
                {'question_id': 'q1', 'selected_answer': 'A'},
            ],
            'test_mode': 'reading',
        }),
        content_type='application/json',
        headers={'Authorization': 'Bearer fake-jwt-token-for-testing'},
    )

    body_text = resp.get_data(as_text=True)
    assert 'duplicate key value' not in body_text, (
        f'SQLERRM leaked in response body: {body_text!r}'
    )
    assert 'pkey' not in body_text
    assert 'DETAIL:' not in body_text
