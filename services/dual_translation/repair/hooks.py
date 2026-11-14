"""The two calls ``routes/dual_translation.submit`` makes (tech 3.3).

Both NEVER raise: on any failure (tables missing because the migration is not
applied yet, a DB error, a bug) they log and return the full contract
unchanged, which is exactly today's submit response.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from services.dual_translation.repair import planner, service, settings, store

logger = logging.getLogger(__name__)


def _response(db, session: Optional[dict], contract: dict) -> dict:
    if session is None:
        return contract
    if not isinstance(session.get("id"), int):
        raise ValueError(f"unusable dt_repair_session row: {session!r:.200}")
    payload = service.session_payload(db, session)
    # The payload must serialise (a broken row must cost the session, not the
    # learner's grade): checked here, inside the never-raise boundary.
    json.dumps(payload)
    if session.get("status") == "open":
        return {**service.redact(contract), "repair": payload}
    return {**contract, "repair": payload}


def after_grade(db, *, user_id: str, submission_row: dict, passage: dict, contract: dict,
                reproduction: Optional[str] = None) -> dict:
    """Create the repair session for a freshly persisted grade and return the
    dict to send (tech 4.1 table)."""
    try:
        if not settings.DT_GUIDED_REPAIR:
            return contract
        ok, _ = planner.is_eligible_trace(contract, contract.get("errors") or [])
        if not ok:
            return contract
        service.finish_stale(db, user_id)
        if reproduction is None:
            reproduction = (store.get_submission(db, submission_row["id"]) or {}).get("reproduction") or ""
        session = service.start_session(db, user_id=user_id, submission=submission_row,
                                        passage=passage, reproduction=reproduction, grade=contract)
        return _response(db, session, contract)
    except Exception as exc:  # noqa: BLE001 - the learner always gets their grade
        logger.error("dt_repair: after_grade failed for submission %s; serving the full result: %s",
                     (submission_row or {}).get("id"), exc, exc_info=True)
        return contract


def for_cached(db, user_id: str, submission_id: int, contract: dict) -> dict:
    """The idempotent re-submit path: the existing session (open -> redacted), or
    ``after_grade`` semantics when none exists (a crash between grade and session)."""
    try:
        if not settings.DT_GUIDED_REPAIR:
            return contract
        ok, _ = planner.is_eligible_trace(contract, contract.get("errors") or [])
        if not ok:
            return contract
        session = store.get_session_by_submission(db, submission_id)
        if session is not None:
            if session.get("status") == "open" and service._is_stale(session, service._now()):
                service._finish_session(db, session, status="abandoned", closed_early=None, body={})
            return _response(db, session, contract)
        submission = store.get_submission(db, submission_id)
        passage = store.get_passage(db, submission["passage_id"]) if submission else None
        if not submission or not passage:
            return contract
        new = service.start_session(db, user_id=user_id, submission=submission, passage=passage,
                                    reproduction=submission.get("reproduction") or "", grade=contract)
        return _response(db, new, contract)
    except Exception as exc:  # noqa: BLE001
        logger.error("dt_repair: for_cached failed for submission %s; serving the full result: %s",
                     submission_id, exc, exc_info=True)
        return contract
