# tests/test_ai_service_moderation.py
"""Unit tests for AIService.moderate_content (CR-03 fail-closed contract).

CR-03 (code-review-2026-05-24): the moderation helper previously returned
``{'is_safe': True}`` on any OpenAI moderation error, which silently passed
unsafe content through during outages. The hardened contract is:

* Happy path returns a dict with ``is_safe`` reflecting the moderation result.
* Empty content returns a dict with ``is_safe: False`` (pre-existing guard).
* Any underlying API/transport error raises ``ModerationServiceError`` so the
  caller can surface a 503 instead of fail-open.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from openai import APIConnectionError, APITimeoutError, RateLimitError

from services.ai_service import AIService, ModerationServiceError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_moderation_result(flagged: bool, categories: dict | None = None,
                            scores: dict | None = None):
    """Build a fake OpenAI moderation API result object."""
    categories = categories or {
        'hate': False, 'harassment': False, 'self-harm': False,
        'sexual': False, 'violence': False,
    }
    scores = scores or {k: 0.0 for k in categories}
    return SimpleNamespace(
        results=[SimpleNamespace(
            flagged=flagged,
            categories=SimpleNamespace(**categories),
            category_scores=SimpleNamespace(**scores),
        )]
    )


def _make_service(client):
    """Build an AIService with mocked client and no real R2 init."""
    fake_config = SimpleNamespace(
        R2_ACCOUNT_ID='x', R2_ACCESS_KEY_ID='x',
        R2_SECRET_ACCESS_KEY='x', R2_BUCKET_NAME='x',
    )
    fake_prompt = MagicMock()
    svc = AIService.__new__(AIService)  # bypass __init__ to skip R2 boto setup
    svc.client = client
    svc.config = fake_config
    svc.prompt_service = fake_prompt
    svc.use_openrouter = False
    svc.r2_client = MagicMock()
    svc.r2_bucket = 'x'
    return svc


def _make_request_error(exc_class):
    """OpenAI 1.x errors require a real httpx request object — build a minimal one."""
    if exc_class is APIConnectionError:
        return exc_class(request=MagicMock())
    if exc_class is APITimeoutError:
        return exc_class(request=MagicMock())
    if exc_class is RateLimitError:
        return exc_class(
            message='rate limited',
            response=MagicMock(status_code=429, request=MagicMock()),
            body={'error': {'message': 'rate limited'}},
        )
    raise AssertionError(f'unsupported exc class {exc_class!r}')


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_safe_content_returns_is_safe_true():
    client = MagicMock()
    client.moderations.create.return_value = _make_moderation_result(flagged=False)
    svc = _make_service(client)

    result = svc.moderate_content('this is fine')

    assert result['is_safe'] is True
    assert result['flagged_categories'] == []
    assert result['error'] is None


def test_flagged_content_returns_is_safe_false_with_categories():
    client = MagicMock()
    client.moderations.create.return_value = _make_moderation_result(
        flagged=True,
        categories={'hate': True, 'harassment': False, 'violence': False,
                    'sexual': False, 'self-harm': False},
        scores={'hate': 0.97, 'harassment': 0.1, 'violence': 0.05,
                'sexual': 0.05, 'self-harm': 0.05},
    )
    svc = _make_service(client)

    result = svc.moderate_content('hateful payload')

    assert result['is_safe'] is False
    assert 'hate' in result['flagged_categories']
    assert result['category_scores']['hate'] == 0.97


def test_empty_content_returns_is_safe_false_empty_content():
    client = MagicMock()
    svc = _make_service(client)

    result = svc.moderate_content('   ')

    assert result['is_safe'] is False
    assert result['flagged_categories'] == ['empty_content']
    client.moderations.create.assert_not_called()


# ---------------------------------------------------------------------------
# CR-03 — fail-closed RED tests
# ---------------------------------------------------------------------------

def test_api_connection_error_raises_moderation_service_error():
    """RED test for CR-03 — must raise instead of returning is_safe: True."""
    client = MagicMock()
    client.moderations.create.side_effect = _make_request_error(APIConnectionError)
    svc = _make_service(client)

    with pytest.raises(ModerationServiceError) as excinfo:
        svc.moderate_content('any content')

    assert excinfo.value.__cause__ is not None
    assert isinstance(excinfo.value.__cause__, APIConnectionError)


def test_api_timeout_error_raises_moderation_service_error():
    client = MagicMock()
    client.moderations.create.side_effect = _make_request_error(APITimeoutError)
    svc = _make_service(client)

    with pytest.raises(ModerationServiceError):
        svc.moderate_content('any content')


def test_rate_limit_error_raises_moderation_service_error():
    client = MagicMock()
    client.moderations.create.side_effect = _make_request_error(RateLimitError)
    svc = _make_service(client)

    with pytest.raises(ModerationServiceError):
        svc.moderate_content('any content')


def test_generic_exception_raises_moderation_service_error():
    """Any unexpected error must also fail-closed via the same exception."""
    client = MagicMock()
    client.moderations.create.side_effect = RuntimeError('upstream broke')
    svc = _make_service(client)

    with pytest.raises(ModerationServiceError):
        svc.moderate_content('any content')
