"""Grading-provider refusals (quota / key limit / auth) for Dual Translation.

Every grader path swallows model-call exceptions on purpose: a failed call
"fails open" for that role and the grade comes back provisional, so the learner
can re-submit (TASK-628). That is right for a timeout or a malformed response,
and wrong when the provider has *refused* the call: an exhausted key limit
(OpenRouter 403), no credits (402), a revoked key (401) or a used-up daily quota
(429 "free-models-per-day"). Those never succeed on an immediate retry, so the
submit route must say "grading is temporarily unavailable" instead.

This module records, per grading request, what each model call did, without
changing the grader functions' return contracts:

    with provider_errors.capture() as calls:
        contract = grade_submission(...)
    if calls.refused_without_answer():
        ...  # GRADING_UNAVAILABLE, nothing saved

The grader call sites (``grader_cascade._call_tier`` / ``_invoke_model`` and
``single_call_grader._attempt``) call ``note_answer`` when the provider returned
a response (even an unusable one) and ``note_failure`` when the call raised.
Outside ``capture()`` both are no-ops. The recorder lives in a ``ContextVar``;
code that hands a call to a worker thread must run it in
``contextvars.copy_context()`` (the copy shares the same recorder object).
"""

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
from dataclasses import dataclass, field
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

# Stable error code the submit route returns and the clients key on.
ERROR_CODE = "GRADING_UNAVAILABLE"

# Kinds of refusal (logged for the operator).
KIND_AUTH = "auth"            # 401: key missing, invalid or revoked
KIND_CREDITS = "credits"      # 402: no credits / payment required
KIND_FORBIDDEN = "forbidden"  # 403: key limit reached (OpenRouter), key disabled
KIND_QUOTA = "quota"          # 429 whose message names a daily quota / credits

# 429 is usually a short per-minute rate limit (transient: the existing
# provisional/retry path is right for it). It is a refusal only when the
# provider says a quota or credit limit is exhausted.
_QUOTA_MARKERS = (
    "per-day", "per day", "perday", "daily", "quota", "credit", "insufficient",
    "key limit", "billing", "exceeded your", "limit exceeded for key",
)
# A 403 that is a content-moderation verdict is not a key/limit problem.
_MODERATION_MARKERS = ("moderation", "flagged")

_MESSAGE_CAP = 300


@dataclass
class Refusal:
    status: int
    kind: str
    slug: str
    role: str
    message: str

    def as_log_dict(self) -> dict:
        return {"status": self.status, "kind": self.kind, "slug": self.slug,
                "role": self.role, "message": self.message}


@dataclass
class CallRecorder:
    """What the model calls of one grading request did."""
    answered: int = 0
    failed: int = 0
    refusals: list = field(default_factory=list)

    def refused_without_answer(self) -> bool:
        """True when at least one call was refused by the provider and no call
        got any response at all — i.e. nothing graded this submission and an
        immediate retry would be refused again. A refusal followed by another
        model's answer (even a malformed one) is NOT this case: that grade, or
        its provisional state, stands as before."""
        return bool(self.refusals) and self.answered == 0

    def summary(self) -> list[dict]:
        return [r.as_log_dict() for r in self.refusals]


_recorder: contextvars.ContextVar[Optional[CallRecorder]] = contextvars.ContextVar(
    "dt_grading_call_recorder", default=None,
)


@contextlib.contextmanager
def capture() -> Iterator[CallRecorder]:
    """Record the model calls made inside the block."""
    recorder = CallRecorder()
    token = _recorder.set(recorder)
    try:
        yield recorder
    finally:
        _recorder.reset(token)


def note_answer(slug: str = "", role: str = "") -> None:
    """The provider returned a response for this call (usable or not)."""
    rec = _recorder.get()
    if rec is not None:
        rec.answered += 1


def note_failure(exc: BaseException, slug: str = "", role: str = "") -> Optional[Refusal]:
    """A model call raised. Records (and returns) a ``Refusal`` when ``exc`` is
    a provider refusal, else counts it as an ordinary failure. Never raises."""
    try:
        refusal = classify(exc, slug=slug, role=role)
    except Exception:  # noqa: BLE001 — classification must never break grading
        refusal = None
    rec = _recorder.get()
    if rec is not None:
        if refusal is not None:
            rec.refusals.append(refusal)
        else:
            rec.failed += 1
    return refusal


def classify(exc: BaseException, *, slug: str = "", role: str = "") -> Optional[Refusal]:
    """A ``Refusal`` when ``exc`` is a quota / auth / limit refusal from the
    provider, else None (timeouts, connection errors, 5xx, per-minute 429s,
    anything that is not an HTTP status error)."""
    status = _status_code(exc)
    if status is None:
        return None
    text = _error_text(exc)
    lowered = text.lower()
    if status == 401:
        kind = KIND_AUTH
    elif status == 402:
        kind = KIND_CREDITS
    elif status == 403:
        if any(m in lowered for m in _MODERATION_MARKERS):
            return None
        kind = KIND_FORBIDDEN
    elif status == 429:
        if not any(m in lowered for m in _QUOTA_MARKERS):
            return None
        kind = KIND_QUOTA
    else:
        return None
    return Refusal(status=status, kind=kind, slug=slug or "", role=role or "",
                   message=text[:_MESSAGE_CAP])


def _status_code(exc: BaseException) -> Optional[int]:
    """The HTTP status of an OpenAI-SDK ``APIStatusError`` (or anything shaped
    like one: ``status_code`` on the error or on its ``response``)."""
    for candidate in (getattr(exc, "status_code", None),
                      getattr(getattr(exc, "response", None), "status_code", None)):
        if isinstance(candidate, int):
            return candidate
    return None


def _error_text(exc: BaseException) -> str:
    parts = [str(exc)]
    body = getattr(exc, "body", None)
    if body is not None:
        try:
            parts.append(json.dumps(body, ensure_ascii=False, default=str))
        except (TypeError, ValueError):
            parts.append(str(body))
    return " ".join(p for p in parts if p)
