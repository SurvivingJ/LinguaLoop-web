"""Server-issued battery tokens for gate / stress-test results (TASK-882 / S14).

``POST /api/vocab-dojo/gate`` and ``/stress-test`` hand the browser a signed
token naming the exact exercises in the battery. The matching ``/result``
endpoints refuse a bare ``passed`` flag: the client reports per-item
outcomes, the server checks every item belongs to the issued battery, counts
correct answers itself and applies the configured pass threshold.

Residual (documented, not fixed here): per-item ``is_correct`` is still
client-reported for multiple-choice types because their answer key ships in
the exercise payload. Closing that needs server-side grading per type.
Replay is also not prevented: the same token can be submitted repeatedly
within BATTERY_MAX_AGE_SECONDS, and a caller can mark every issued item
correct. The S14 forgery of a bare ``passed`` flag is closed; forging
per-item outcomes is NOT (see ADR-034 / TASK-882 residual).
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = 'vocab-dojo-battery-v1'
#: A battery must be finished within an hour of being issued.
BATTERY_MAX_AGE_SECONDS = 3600


class BatteryError(ValueError):
    """Token missing/invalid/expired or results do not match the battery."""


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=_SALT)


def issue(user_id: str, kind: str, sense_id: int, gate_name: Optional[str],
          exercise_ids: Iterable[Any]) -> str:
    return _serializer().dumps({
        'u': str(user_id), 'k': kind, 's': int(sense_id), 'g': gate_name,
        'e': [str(i) for i in exercise_ids],
    })


def score(token: Any, user_id: str, kind: str, sense_id: int,
          gate_name: Optional[str], results: Any) -> tuple[int, int]:
    """Return ``(correct, battery_size)`` from the client's per-item results.

    Items not reported count as wrong. Unknown or duplicated exercise ids,
    or a token for another user/sense/gate/kind, raise ``BatteryError``.
    """
    if not isinstance(token, str) or not token:
        raise BatteryError("battery_token required")
    try:
        payload = _serializer().loads(token, max_age=BATTERY_MAX_AGE_SECONDS)
    except SignatureExpired:
        raise BatteryError("battery_token expired")
    except BadSignature:
        raise BatteryError("battery_token invalid")

    if (payload.get('u') != str(user_id) or payload.get('k') != kind
            or payload.get('s') != int(sense_id) or payload.get('g') != gate_name):
        raise BatteryError("battery_token does not match this request")

    issued = payload.get('e') or []
    if not isinstance(results, list):
        raise BatteryError("results must be a list")
    seen: set[str] = set()
    correct = 0
    for item in results:
        if not isinstance(item, dict):
            raise BatteryError("each result must be an object")
        ex_id = str(item.get('exercise_id'))
        if ex_id not in issued or ex_id in seen:
            raise BatteryError("result does not belong to the issued battery")
        seen.add(ex_id)
        if item.get('is_correct') is True:
            correct += 1
    return correct, len(issued)
