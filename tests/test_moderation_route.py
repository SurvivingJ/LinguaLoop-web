# tests/test_moderation_route.py
"""Tests for POST /api/tests/moderate (CR-03 — must surface 503 on outage).

CR-03 (code-review-2026-05-24): when the moderation service is unavailable
the route used to return ``{is_safe: True}`` because of the underlying
fail-open default. The hardened behavior is:

* 200 with the moderation verdict on success.
* 503 ``{error: "moderation_unavailable"}`` when ``moderate_content`` raises
  ``ModerationServiceError``.
* The flagged-input audit insert must NOT be called when the moderation
  result is indeterminate (avoids polluting the abuse log with false
  positives during outages).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from services.ai_service import ModerationServiceError


AUTH_HEADERS = {'Authorization': 'Bearer fake-jwt-token-for-testing'}


def _post_moderate(client, content='hello world'):
    return client.post(
        '/api/tests/moderate',
        data=json.dumps({'content': content}),
        content_type='application/json',
        headers=AUTH_HEADERS,
    )


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_moderation_route_returns_200_for_safe_content(client, app):
    """Safe content -> 200, is_safe=True, no audit insert."""
    app.openai_service = MagicMock()
    app.openai_service.moderate_content.return_value = {
        'is_safe': True,
        'flagged_categories': [],
        'category_scores': {},
        'error': None,
    }

    with patch('routes.tests.get_test_service') as get_svc:
        resp = _post_moderate(client, 'totally fine')

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['is_safe'] is True
        assert data['status'] == 'success'
        get_svc.assert_not_called()


def test_moderation_route_returns_200_with_flagged_for_unsafe(client, app):
    """Unsafe content -> 200, is_safe=False, audit insert recorded."""
    app.openai_service = MagicMock()
    app.openai_service.moderate_content.return_value = {
        'is_safe': False,
        'flagged_categories': ['hate'],
        'category_scores': {'hate': 0.97},
        'error': None,
    }

    with patch('routes.tests.get_test_service') as get_svc:
        fake_test_service = MagicMock()
        get_svc.return_value = fake_test_service

        resp = _post_moderate(client, 'hateful payload')

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['is_safe'] is False
        assert 'hate' in data['flagged_categories']
        fake_test_service.record_flagged_input.assert_called_once()


# ---------------------------------------------------------------------------
# CR-03 — 503 RED tests
# ---------------------------------------------------------------------------

def test_moderation_route_returns_503_when_service_raises(client, app):
    """RED test for CR-03: when moderate_content raises, route returns 503
    and does NOT record a false-positive flagged input."""
    app.openai_service = MagicMock()
    app.openai_service.moderate_content.side_effect = ModerationServiceError(
        'OpenAI moderation timed out'
    )

    with patch('routes.tests.get_test_service') as get_svc:
        resp = _post_moderate(client, 'any content')

        assert resp.status_code == 503, (
            f'expected 503 on moderation outage, got {resp.status_code} '
            f'body={resp.data!r}'
        )
        data = json.loads(resp.data)
        assert data.get('error') == 'moderation_unavailable'
        assert data.get('status') == 'error'
        get_svc.assert_not_called()


def test_moderation_route_returns_400_for_empty_content(client, app):
    """Pre-existing guard — empty content stays a 400."""
    app.openai_service = MagicMock()

    resp = _post_moderate(client, '   ')

    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert 'error' in data
