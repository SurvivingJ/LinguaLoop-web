"""Signed primed-sense tokens for the prestudy Produce stage (TASK-909/910).

``POST /api/dual-translation/passage-from-sentences`` is handed the sense ids
the learner primed in Study; the grader needs them back at submit time as
target words. Rather than a per-user cache table, the server signs them into a
token the client echoes on ``POST /<submission_id>/submit`` — the same
``itsdangerous`` pattern ``services.vocabulary_ladder.battery_token`` uses for
gate batteries, so the client cannot invent or widen the target list and
nothing has to be stored.

The token is bound to (user, passage): a token for another learner's session
or another passage is rejected.
"""

from __future__ import annotations

from typing import Any, Iterable

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = 'dt-primed-senses-v1'
#: Study -> Test -> Follow-up -> Produce is about 18 minutes; allow a long pause.
PRIMED_TOKEN_MAX_AGE_SECONDS = 6 * 3600
#: Hard cap on the target list, matching the prestudy prime of at most 8 words
#: with headroom for the unknown-word fallback.
MAX_PRIMED_SENSES = 24


class PrimedTokenError(ValueError):
    """Token missing/invalid/expired or bound to another user or passage."""


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=_SALT)


def issue(user_id: str, passage_id: int, sense_ids: Iterable[Any]) -> str:
    ids: list[int] = []
    for s in sense_ids:
        try:
            v = int(s)
        except (TypeError, ValueError):
            continue
        if v > 0 and v not in ids:
            ids.append(v)
    return _serializer().dumps({'u': str(user_id), 'p': int(passage_id), 's': ids[:MAX_PRIMED_SENSES]})


def load(token: Any, user_id: str, passage_id: int) -> list[int]:
    """Return the primed sense ids carried by ``token`` for this (user, passage)."""
    if not isinstance(token, str) or not token:
        raise PrimedTokenError("primed_token required")
    try:
        payload = _serializer().loads(token, max_age=PRIMED_TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired:
        raise PrimedTokenError("primed_token expired")
    except BadSignature:
        raise PrimedTokenError("primed_token invalid")
    if payload.get('u') != str(user_id) or payload.get('p') != int(passage_id):
        raise PrimedTokenError("primed_token does not match this submission")
    return [int(s) for s in (payload.get('s') or [])]
