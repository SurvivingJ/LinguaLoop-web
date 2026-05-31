# tests/test_classifier_drill_progress.py
"""Regression test for the Phase-13 Study Plan progress hook on the
measure-word (classifier) drill.

The drill historically wrote `test_attempts` + ELO but never called the
Study Plan progress hook, so completions never reached
`weekly_plan_states.completed_counts`. The submit handler now mirrors the
standard submission handlers in routes/tests.py by calling
`_apply_timing_and_progress(...)` after a successful submission RPC.

These are unit/route tests — the submission service and the progress hook
are mocked; no live Supabase is touched.
"""

import json
from unittest.mock import patch, MagicMock


def resp_json(resp):
    return json.loads(resp.data)


def _success_rpc(attempt_id='attempt-xyz'):
    """A minimal successful process_classifier_drill_submission payload."""
    return {
        'success': True,
        'attempt_id': attempt_id,
        'is_first_attempt': True,
        'user_elo_before': 1000, 'user_elo_after': 1010, 'user_elo_change': 10,
        'test_elo_before': 1000, 'test_elo_after': 995, 'test_elo_change': -5,
        'mastery_updates': [],
    }


def _valid_body():
    return {'language_id': 1, 'correct_items': 4, 'total_items': 5,
            'time_taken': 42, 'idempotency_key': 'idem-1'}


class TestClassifierDrillProgressHook:

    def test_successful_submit_invokes_progress_hook(self, client, auth_headers):
        """A successful drill submission calls _apply_timing_and_progress
        with the attempt_id returned by the submission RPC."""
        with patch('routes.classifier_drill.submit_session',
                   return_value=_success_rpc('attempt-xyz')), \
             patch('routes.classifier_drill.DimensionService.get_test_type_id',
                   return_value=14), \
             patch('routes.tests._apply_timing_and_progress') as hook:
            resp = client.post('/api/classifier-drill/submit',
                               json=_valid_body(), headers=auth_headers)

        assert resp.status_code == 200
        hook.assert_called_once()
        # Signature: _apply_timing_and_progress(client, attempt_id, request_body)
        args = hook.call_args.args
        assert args[1] == 'attempt-xyz'
        # The request body is forwarded so the hook can read started_at/finished_at.
        assert args[2].get('total_items') == 5

    def test_failed_submit_does_not_invoke_progress_hook(self, client, auth_headers):
        """When the submission RPC reports failure, the hook must not run."""
        with patch('routes.classifier_drill.submit_session',
                   return_value={'success': False, 'error': 'boom'}), \
             patch('routes.classifier_drill.DimensionService.get_test_type_id',
                   return_value=14), \
             patch('routes.tests._apply_timing_and_progress') as hook:
            resp = client.post('/api/classifier-drill/submit',
                               json=_valid_body(), headers=auth_headers)

        assert resp.status_code == 500
        hook.assert_not_called()

    def test_validation_failure_does_not_invoke_progress_hook(self, client, auth_headers):
        """Bad input is rejected before the submission RPC, so no hook call."""
        with patch('routes.classifier_drill.submit_session') as submit, \
             patch('routes.tests._apply_timing_and_progress') as hook:
            resp = client.post('/api/classifier-drill/submit',
                               json={'language_id': 1, 'correct_items': 9,
                                     'total_items': 5}, headers=auth_headers)

        assert resp.status_code == 400
        submit.assert_not_called()
        hook.assert_not_called()
