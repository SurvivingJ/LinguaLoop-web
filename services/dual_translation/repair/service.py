"""Guided-repair orchestration used by ``routes/dt_repair.py`` and ``hooks.py``
(tech 3.3, 4, 7). Routes stay thin: they authenticate, check the flag and map
``RepairError`` to an error response; every rule lives here.

Model boundary: ``recheck.recheck_sentence``. DB boundary: ``store`` (plus
``budget`` and ``sentences.l1_context``). Clock: ``_now()``; learner-local day:
``_local_today()``.
"""

from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from services.dual_translation.repair import (
    budget, classify, hints, planner, recheck, scheduling, sentences, settings, store,
)
from services.dual_translation.tier0 import _normalize_l2

logger = logging.getLogger(__name__)

PASS = "repair_pass"
DAILY = "daily_practice"
SURFACES = (PASS, DAILY)
SINCE_PREV_MAX_MS = 3_600_000
PASS_OUTCOMES_FIXED = ("self_repaired", "repaired_alternative")


class RepairError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# ---------------------------------------------------------------------------
# Small helpers (monkeypatchable)
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _local_today(db, user_id: str, l2_language_id: int) -> date:
    from services import day_boundary
    return date.fromisoformat(day_boundary.plan_today_iso(db, user_id, l2_language_id))


def _local_date_of(db, user_id: str, l2_language_id: int, instant) -> Optional[str]:
    """Learner-local ISO date of an instant (``from_date``)."""
    try:
        from services import day_boundary
        tz = day_boundary.plan_timezone(db, user_id, l2_language_id)
        return day_boundary.local_today_iso(tz, scheduling._ts(instant))
    except Exception:  # noqa: BLE001
        return str(instant)[:10] if instant else None


def _lang_code(language_id) -> Optional[str]:
    try:
        from services.dimension_service import DimensionService
        code = DimensionService.get_language_code(language_id)
        if code:
            return code
    except Exception:  # noqa: BLE001
        pass
    from services.dual_translation.sentence_refs import LANG_CODE
    return LANG_CODE.get(language_id)


def _taxonomy(db) -> Optional[dict]:
    try:
        from services.dual_translation import grader_cascade
        return grader_cascade.get_active_taxonomy(db)
    except Exception:  # noqa: BLE001 - only a label fallback
        return None


def _credit(db, user_id, language_id, seconds, source_table, source_id) -> None:
    from services.study_time import credit_study_time
    credit_study_time(db, user_id, language_id, "dual_translation", seconds, source_table, source_id)


def normalize_text(value: str) -> str:
    """Tech 4.6 input normalisation: NFC, line breaks/tabs -> space, runs of
    spaces collapsed, trimmed."""
    text = unicodedata.normalize("NFC", value)
    text = re.sub(r"\r\n|\n|\r|\t", " ", text)
    return re.sub(r" {2,}", " ", text).strip()


def _since_prev(body: dict) -> Optional[int]:
    value = (body or {}).get("since_prev_ms")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(max(0, min(SINCE_PREV_MAX_MS, value)))


def _opt_ms(value) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return int(min(value, 2_000_000_000))


def _surface(body: dict) -> str:
    surface = (body or {}).get("surface")
    if surface not in SURFACES:
        raise RepairError(400, "BAD_REQUEST", "surface must be 'repair_pass' or 'daily_practice'")
    return surface


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Context, rungs, steps
# ---------------------------------------------------------------------------

def _ctx(db, item: dict) -> dict:
    sub = store.get_submission(db, item["submission_id"])
    if not sub:
        raise RepairError(404, "NOT_FOUND", "submission not found")
    passage = store.get_passage(db, sub["passage_id"])
    if not passage:
        raise RepairError(404, "NOT_FOUND", "passage not found")
    reproduction = sub.get("reproduction") or ""
    gold = passage.get("l2_text") or ""
    return {
        "submission": sub, "passage": passage,
        "learner": reproduction[item["repro_start"]:item["repro_end"]],
        "reference": gold[item["ref_start"]:item["ref_end"]],
        "l1_id": sub["l1_language_id"], "l2_id": passage["l2_language_id"],
        "l1": _lang_code(sub["l1_language_id"]) or "en", "l2": _lang_code(passage["l2_language_id"]) or "en",
    }


def _pair(item: dict) -> sentences.PairModel:
    return sentences.PairModel(item["sentence_index"], item["repro_start"], item["repro_end"],
                               item["ref_start"], item["ref_end"], item["ref_start"], item["ref_end"])


def _rungs(item: dict) -> list:
    if item.get("step_kind") in ("direct", "unsure"):
        return []
    return hints.rungs(item.get("ladder"), bool(item.get("location_available")))


def _cap(surface: str) -> int:
    return settings.DT_REPAIR_CHECK_CAP_DAILY if surface == DAILY else settings.DT_REPAIR_CHECK_CAP_PASS


def _current_text(item: dict, ctx: dict) -> str:
    return item.get("last_text") or ctx["learner"]


def _where(item: dict, ctx: dict) -> Optional[dict]:
    """The Where object when the learner is entitled to it (rung 1 taken, or an
    unsure step with a location)."""
    rungs = _rungs(item)
    entitled = ((int(item.get("hint_level") or 0) >= 1 and 1 in rungs)
                or (item.get("step_kind") == "unsure" and item.get("location_available")))
    if not entitled or not isinstance(item.get("active"), dict):
        return None
    return classify.where_for(item["active"], _current_text(item, ctx))


def _hints_used(item: dict, surface: str) -> int:
    rungs = _rungs(item)
    used = sum(1 for r in rungs if r <= int(item.get("hint_level") or 0))
    if surface == DAILY and 1 in rungs and used:
        used -= 1  # the daily sitting opens with the location already shown (SPEC 8.3)
    return used


def _pass_closed(item: dict) -> bool:
    return item.get("outcome") is not None


def _step(item: dict, ctx: dict, *, surface: str, prompt_l1: Optional[str], position: int,
          state: Optional[str] = None, outcome: Optional[str] = None,
          from_date: Optional[str] = None) -> dict:
    if surface == PASS:
        state = state or ("closed" if _pass_closed(item) else "open")
        outcome = item.get("outcome") if outcome is None else outcome
    return {
        "item_id": item["id"],
        "position": position,
        "sentence_index": item["sentence_index"],
        "step_kind": item["step_kind"],
        "ladder": item["ladder"],
        "prompt_l1": prompt_l1,
        "learner_sentence": ctx["learner"],
        "hint_rungs": _rungs(item),
        "hint_level": int(item.get("hint_level") or 0),
        "where": _where(item, ctx),
        "last_text": item.get("last_text"),
        "checks_used": int(item.get("checks_used") or 0),
        "check_cap": _cap(surface),
        "state": state or "open",
        "outcome": outcome,
        "from_date": from_date,
    }


def _prompts_for(db, ctx: dict, model=None):
    sub, passage = ctx["submission"], ctx["passage"]
    if model is None:
        model = sentences.sentence_model(passage.get("l2_text") or "", sub.get("reproduction") or "")
    try:
        l1_text = store.get_l1_passage_text(db, passage["id"], ctx["l1_id"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("dt_repair: L1 passage text unavailable: %s", exc)
        l1_text = None
    return sentences.l1_context(db, passage=passage, gold_l2=passage.get("l2_text") or "",
                                l1_language_id=ctx["l1_id"], l1_code=ctx["l1"], model=model,
                                l1_passage_text=l1_text)


def _event(db, item: dict, surface: str, kind: str, body: Optional[dict] = None, **fields) -> None:
    """Record one event; recording never blocks the learner (except the
    idempotency conflict, which the caller handles)."""
    row = {
        "item_id": item["id"], "user_id": item["user_id"], "surface": surface,
        "sitting": int(item.get("sitting") or 0), "kind": kind,
        "hint_level": int(item.get("hint_level") or 0), "since_prev_ms": _since_prev(body or {}),
    }
    row.update({k: v for k, v in fields.items() if v is not None})
    try:
        store.insert_event(db, row)
    except store.DuplicateCheck:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("dt_repair: event %s for item %s not recorded: %s", kind, item["id"], exc)


# ---------------------------------------------------------------------------
# Answer object (tech 4.7)
# ---------------------------------------------------------------------------

def _merge(spans: list) -> list:
    out: list = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def _first_sentence(text: str, limit: int = 160) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    m = re.search(r"^(.+?[.!?。！？])(\s|$)", text)
    return (m.group(1) if m else text[:limit]).strip()


def _answer(db, item: dict, ctx: dict, heading: str) -> dict:
    rows = []
    try:
        rows = [r for r in store.get_error_rows(db, item["submission_id"])
                if r.get("sentence_index") == item["sentence_index"]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("dt_repair: error rows unavailable for the answer: %s", exc)
    learner_marks, answer_marks = [], []
    for r in rows:
        if r.get("correction_source") == "reference_sentence" or r.get("span_source") == "sentence":
            continue
        ls = sentences.local_span(r.get("span_reproduction"), item["repro_start"], item["repro_end"])
        if ls and ls[1] > ls[0]:
            learner_marks.append(list(ls))
        rs = sentences.local_span(r.get("span_reference"), item["ref_start"], item["ref_end"])
        if rs and rs[1] > rs[0]:
            answer_marks.append(list(rs))
    primary = next((r for r in rows if r.get("id") == item.get("error_id")), rows[0] if rows else {})
    if primary.get("explanation_source") == "model" and primary.get("model_note"):
        explanation = primary["model_note"]
    else:
        explanation = primary.get("explanation") or ""
    explanation = _first_sentence(explanation)
    if not explanation:
        explanation = hints.render_kind(item.get("subtype") or "", ctx["l1"], None)[0]
    return {
        "heading": heading,
        "learner_sentence": ctx["learner"],
        "learner_marks": _merge(learner_marks),
        "answer_sentence": ctx["reference"],
        "answer_marks": _merge(answer_marks),
        "explanation": explanation,
        "explanation_lang": ctx["l1"],
        "l2": ctx["l2"],
    }


def _heading(outcome: Optional[str]) -> str:
    if outcome == "repaired_alternative":
        return "no_issue"
    if outcome == "disputed":
        return "disputed"
    return "compare"


# ---------------------------------------------------------------------------
# Loading + ownership
# ---------------------------------------------------------------------------

def _owned_item(db, user_id: str, item_id: int) -> dict:
    item = store.get_item(db, item_id)
    if not item:
        raise RepairError(404, "NOT_FOUND", "item not found")
    if item.get("user_id") != user_id:
        raise RepairError(403, "NOT_OWNER", "this item does not belong to you")
    return item


def _owned_session(db, user_id: str, session_id: int) -> dict:
    session = store.get_session(db, session_id)
    if not session:
        raise RepairError(404, "NOT_FOUND", "session not found")
    if session.get("user_id") != user_id:
        raise RepairError(403, "NOT_OWNER", "this session does not belong to you")
    return session


def _owned_submission(db, user_id: str, submission_id: int) -> dict:
    sub = store.get_submission(db, submission_id)
    if not sub:
        raise RepairError(404, "NOT_FOUND", "submission not found")
    if sub.get("user_id") != user_id:
        raise RepairError(403, "NOT_OWNER", "this submission does not belong to you")
    return sub


def _require_open(db, item: dict, surface: str, *, opened_code: str = "NOT_OPENED") -> None:
    """repair_pass: open session and open item. daily: a sitting in progress."""
    if surface == PASS:
        if _pass_closed(item):
            raise RepairError(409, "ITEM_CLOSED", "this sentence is already closed")
        session = store.get_session(db, item["session_id"])
        if not session or session.get("status") != "open":
            raise RepairError(409, "SESSION_CLOSED", "this repair session is closed")
    else:
        if not item.get("sitting_open"):
            raise RepairError(409, opened_code, "open the item first")


# ---------------------------------------------------------------------------
# Session creation (hooks) and payloads
# ---------------------------------------------------------------------------

def start_session(db, *, user_id: str, submission: dict, passage: dict, reproduction: str,
                  grade: dict) -> Optional[dict]:
    """Plan and persist a session for a freshly graded submission. Returns the
    session row, or None when the grade is not eligible (today's flow)."""
    ok, _ = planner.is_eligible_trace(grade, grade.get("errors") or [])
    if not ok:
        return None
    errors = store.get_error_rows(db, submission["id"]) if grade.get("errors") else []
    model = sentences.sentence_model(passage.get("l2_text") or "", reproduction or "")
    result = planner.plan(grade, errors, model, passage.get("age_tier"))
    if not result["eligible"]:
        logger.info("dt_repair: submission %s not eligible (%s)", submission["id"], result["reason"])
        return None
    now = _now()
    status = result["status"]
    trace = grade.get("grader_trace") or {}
    planned = result["steps"] or result["direct_items"]
    session_row = {
        "submission_id": submission["id"], "user_id": user_id,
        "l2_language_id": passage["l2_language_id"], "l1_language_id": submission["l1_language_id"],
        "status": status, "n_sentences": result["n_sentences"], "n_flagged": result["n_flagged"],
        "n_steps": len(result["steps"]), "grade_tier": trace.get("tier"),
        "prompt_version": (trace.get("single_call") or {}).get("prompt_version"),
        "hint_version": hints.version(), "settings": settings.snapshot(),
    }
    if status in (planner.STATUS_CLEAN, planner.STATUS_BYPASSED):
        session_row["finished_at"] = _iso(now)
        session_row["total_ms"] = 0
    session = store.insert_session(db, session_row)
    if not isinstance(session, dict) or not isinstance(session.get("id"), int):
        raise RuntimeError("dt_repair_session insert returned an unusable row")
    if session.get("submission_id") != submission["id"] or store.get_items(db, session["id"]):
        return session  # an existing session (race / re-submit): keep it as is
    local_today = _local_today(db, user_id, passage["l2_language_id"]) if status == planner.STATUS_BYPASSED else None
    rows = []
    for p in planned:
        pm = model[p["sentence_index"]]
        err = p["error"]
        span = p["span"]
        active = {k: v for k, v in p["active"].items() if k != "model_note"}
        row = {
            "session_id": session["id"], "user_id": user_id, "submission_id": submission["id"],
            "error_id": err["id"], "l2_language_id": passage["l2_language_id"],
            "sentence_index": p["sentence_index"], "step_order": p["step_order"],
            "step_kind": p["step_kind"], "ladder": p["ladder"],
            "location_available": bool(p["location_available"]),
            "subtype": err.get("subtype") or "", "severity": err.get("severity") or "minor",
            "confidence": err.get("confidence"),
            "repro_start": pm.repro_start, "repro_end": pm.repro_end,
            "ref_start": pm.ref_start, "ref_end": pm.ref_end,
            "span_start": span[0] if span else None, "span_end": span[1] if span else None,
            "active": active,
        }
        if status == planner.STATUS_BYPASSED:
            row.update(outcome="shown_directly", answer_reason="direct", max_hint_level=4,
                       hint_level=4, closed_at=_iso(now), n_checks=0, time_ms=0,
                       **scheduling.first_queue_state(local_today, now))
        rows.append(row)
    store.insert_items(db, rows)
    return session


def summary(items: list) -> dict:
    return {
        "fixed_yourself": sum(1 for i in items if i.get("outcome") in PASS_OUTCOMES_FIXED),
        "needed_help": sum(1 for i in items if i.get("outcome") == "answer_shown"),
        "saved_to_practice": sum(1 for i in items if i.get("queued_at")),
    }


def session_payload(db, session: dict, items: Optional[list] = None) -> dict:
    """The tech 4.2 session object."""
    if items is None:
        items = store.get_items(db, session["id"])
    sub = store.get_submission(db, session["submission_id"]) or {}
    passage = store.get_passage(db, sub.get("passage_id")) if sub else None
    status = session.get("status")
    l1 = _lang_code(session.get("l1_language_id")) or "en"
    l2 = _lang_code(session.get("l2_language_id")) or "en"
    steps = []
    prompts, whole = [], None
    if passage:
        ctx0 = {"submission": sub, "passage": passage, "l1_id": session["l1_language_id"], "l1": l1}
        prompts, whole = _prompts_for(db, ctx0)
    n_sentences = int(session.get("n_sentences") or 0)
    if status in ("open", "finished", "abandoned") and passage:
        reproduction = sub.get("reproduction") or ""
        gold = passage.get("l2_text") or ""
        ordered = sorted((i for i in items if i.get("step_order") is not None), key=lambda i: i["step_order"])
        for item in ordered:
            ctx = {"learner": reproduction[item["repro_start"]:item["repro_end"]],
                   "reference": gold[item["ref_start"]:item["ref_end"]], "l1": l1, "l2": l2}
            idx = item["sentence_index"]
            steps.append(_step(item, ctx, surface=PASS, prompt_l1=prompts[idx] if idx < len(prompts) else None,
                               position=item["step_order"]))
    clean = status == "finished" and int(session.get("n_flagged") or 0) == 0
    if status == "bypassed":
        steps = []
    return {
        "session_id": session["id"],
        "submission_id": session["submission_id"],
        "status": status,
        "clean": clean,
        "surface": PASS,
        "l1": l1,
        "l2": l2,
        "n_sentences": n_sentences,
        "n_clean": max(0, n_sentences - int(session.get("n_flagged") or 0)),
        "prompt_l1_passage": whole,
        "auto_advance_ms": settings.DT_REPAIR_AUTO_ADVANCE_MS,
        "steps": steps,
        "summary": summary(items) if status != "open" else None,
    }


def redact(contract: dict) -> dict:
    """Tech 3.3: what the submit response carries while a session is open."""
    out = {
        "scores": contract.get("scores"),
        "overall_band": contract.get("overall_band"),
        "provisional": bool(contract.get("provisional", False)),
        "errors": [], "diff": [], "highlights": [],
        "redacted": True,
        "n_errors": len(contract.get("errors") or []),
    }
    if "target_words" in contract:
        out["target_words"] = contract["target_words"]
    return out


def _is_stale(session: dict, now: datetime) -> bool:
    created = scheduling._ts(session.get("created_at"))
    return bool(created and now - created > timedelta(hours=settings.DT_REPAIR_SESSION_STALE_HOURS))


def finish_stale(db, user_id: str, limit: int = settings.DT_REPAIR_STALE_PER_CALL) -> int:
    """Finish this user's open sessions older than the stale window as
    ``abandoned`` (tech 7.4). Best effort; returns how many."""
    now = _now()
    done = 0
    try:
        for session in store.open_sessions(db, user_id):
            if done >= limit:
                break
            if _is_stale(session, now):
                _finish_session(db, session, status="abandoned", closed_early=None, body={})
                done += 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("dt_repair: finishing stale sessions failed: %s", exc)
    return done


# ---------------------------------------------------------------------------
# Closing
# ---------------------------------------------------------------------------

def _close(db, item: dict, ctx: dict, surface: str, outcome: str, *, answer_reason: Optional[str] = None,
           body: Optional[dict] = None, event_kind: Optional[str] = None, extra: Optional[dict] = None) -> None:
    """Close the current episode (repair-pass item, or daily sitting): write the
    action event (if any) and ``episode_closed``, update the row, queue it."""
    body = body or {}
    now = _now()
    if outcome in ("answer_shown", "shown_directly"):
        item["hint_level"] = 4
    opened = scheduling._ts(item.get("opened_at"))
    time_ms = int((now - opened).total_seconds() * 1000) if opened else None
    if event_kind:
        _event(db, item, surface, event_kind, body, **(extra or {}))
    fields: dict = {"hint_level": int(item.get("hint_level") or 0), "sitting_open": False,
                    "check_lock_until": None}
    level = int(item.get("hint_level") or 0)
    if surface == PASS:
        max_level = max(int(item.get("max_hint_level") or 0), level)
        fields.update(outcome=outcome, answer_reason=answer_reason, max_hint_level=max_level,
                      closed_at=_iso(now), time_ms=time_ms, n_checks=int(item.get("n_checks") or 0))
        if scheduling.queued_on_close(item.get("step_kind"), outcome, max_level):
            fields.update(scheduling.first_queue_state(_local_today(db, item["user_id"], item["l2_language_id"]), now))
    else:
        fields.update(scheduling.after_sitting(
            outcome=outcome, sitting_max_hint=level, sitting=int(item.get("sitting") or 0),
            failed_sittings=int(item.get("failed_sittings") or 0),
            hinted_sittings=int(item.get("hinted_sittings") or 0),
            local_today=_local_today(db, item["user_id"], item["l2_language_id"])))
        fields["last_practiced_at"] = _iso(now)
        max_level = level
    item.update(fields)
    _event(db, item, surface, "episode_closed", None, result_detail={
        "o": outcome, "t": time_ms,
        "n": int(item.get("n_checks") or 0) if surface == PASS else int(item.get("checks_used") or 0),
        "a": answer_reason, "h": max_level})
    store.update_item(db, item["id"], fields)
    if surface == DAILY:
        event_id = _parse_event_id(body.get("client_event_id"))
        seconds = min(settings.DT_REPAIR_DAILY_CREDIT_MAX_S, _seconds(body.get("active_ms")))
        if event_id and seconds > 0:
            _credit(db, item["user_id"], item["l2_language_id"], seconds, "dt_repair_event", event_id)


def _parse_event_id(value) -> Optional[str]:
    from services.study_time import parse_client_event_id
    return parse_client_event_id(value)


def _seconds(active_ms) -> int:
    from services.study_time import clamp_active_ms
    return clamp_active_ms("dual_translation", active_ms)


def _daily_last_outcome(db, item: dict) -> Optional[str]:
    try:
        ev = store.last_episode_event(db, item["id"])
    except Exception:  # noqa: BLE001
        return None
    return ((ev or {}).get("result_detail") or {}).get("o") if ev and int(ev.get("sitting") or 0) > 0 else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def get_session(db, user_id: str, submission_id: int) -> dict:
    _owned_submission(db, user_id, submission_id)
    session = store.get_session_by_submission(db, submission_id)
    if not session:
        raise RepairError(404, "NO_SESSION", "this submission has no repair session")
    if session.get("status") == "open" and _is_stale(session, _now()):
        _finish_session(db, session, status="abandoned", closed_early=None, body={})
        session = store.get_session(db, session["id"]) or session
    return session_payload(db, session)


def open_item(db, user_id: str, item_id: int, body: dict) -> dict:
    item = _owned_item(db, user_id, item_id)
    surface = _surface(body)
    ctx = _ctx(db, item)
    now = _now()
    if surface == PASS:
        _require_open(db, item, PASS)
        if not item.get("opened_at"):
            item["opened_at"] = _iso(now)
            store.update_item(db, item["id"], {"opened_at": item["opened_at"]})
            _event(db, item, PASS, "step_opened", body)
        prompts, _ = _prompts_for(db, ctx)
        return {"step": _step(item, ctx, surface=PASS, prompt_l1=_at(prompts, item["sentence_index"]),
                              position=item.get("step_order") or 0)}

    opened = scheduling._ts(item.get("opened_at"))
    resume = (item.get("sitting_open") and opened is not None
              and now - opened < timedelta(hours=settings.DT_REPAIR_SITTING_RESUME_HOURS))
    if not resume:
        if item.get("sitting_open"):
            # An abandoned sitting (> 2 h): record it as skipped and start afresh
            # now. The item was due when that sitting opened, so no due check and
            # no rescheduling (that would push it to tomorrow).
            _event(db, item, DAILY, "skipped", {})
            _event(db, item, DAILY, "episode_closed", None, result_detail={
                "o": "skipped", "t": None, "n": int(item.get("checks_used") or 0), "a": None,
                "h": int(item.get("hint_level") or 0)})
        else:
            local_today = _local_today(db, user_id, item["l2_language_id"])
            if not scheduling.is_due(item, local_today, now):
                raise RepairError(409, "NOT_DUE", "this item is not due")
        rungs = _rungs(item)
        fields = {
            "sitting": int(item.get("sitting") or 0) + 1, "sitting_open": True,
            "hint_level": 1 if 1 in rungs else 0, "checks_used": 0, "calls_used": 0,
            "last_text": None, "active": _original_active(db, item), "opened_at": _iso(now),
        }
        item.update(fields)
        store.update_item(db, item["id"], fields)
        _event(db, item, DAILY, "step_opened", body)
    prompts, _ = _prompts_for(db, ctx)
    return {"step": _step(item, ctx, surface=DAILY, prompt_l1=_at(prompts, item["sentence_index"]),
                          position=0, from_date=_local_date_of(db, user_id, item["l2_language_id"],
                                                               ctx["submission"].get("created_at")))}


def _at(seq, idx):
    return seq[idx] if seq and 0 <= idx < len(seq) else None


def _original_active(db, item: dict) -> dict:
    try:
        rows = store.get_error_rows(db, item["submission_id"])
        err = next((r for r in rows if r.get("id") == item.get("error_id")), None)
        if err:
            active = planner.active_from_error(err, _pair(item))
            active.pop("model_note", None)
            return active
    except Exception as exc:  # noqa: BLE001
        logger.warning("dt_repair: original error unavailable for item %s: %s", item["id"], exc)
    return item.get("active") or {}


def _render_hint(db, item: dict, ctx: dict, level: int) -> tuple[dict, dict]:
    """-> (hint object, event fields) for one rung."""
    active = item.get("active") or {}
    if level == hints.RUNG_WHERE:
        return {"type": "where", "text": None, "lang": None}, {"hint_source": hints.SOURCE_GRADER_SPAN}
    if level == hints.RUNG_KIND:
        text, lang, source, tid = hints.render_kind(active.get("subtype") or item.get("subtype") or "",
                                                    ctx["l1"], _taxonomy(db))
        return {"type": "kind", "text": text, "lang": lang}, {"hint_source": source, "hint_template_id": tid}
    current = _current_text(item, ctx)
    text, lang, source, tid, blocked = hints.render_clue(
        active.get("subtype") or item.get("subtype") or "", ctx["l1"],
        learner_form=active.get("form") or "", current_text=current,
        corrected_form=active.get("corrected_form") or "", l2_code=ctx["l2"],
        correction_source=active.get("correction_source"), reference_sentence=ctx["reference"],
        learner_sentence=current)
    extra = {"hint_source": source, "hint_template_id": tid}
    if blocked:
        extra["result_detail"] = {"leak_blocked": True}
    return {"type": "clue", "text": text, "lang": lang}, extra


def next_hint(db, user_id: str, item_id: int, body: dict) -> dict:
    item = _owned_item(db, user_id, item_id)
    surface = _surface(body)
    expected = body.get("expected_level")
    if isinstance(expected, bool) or not isinstance(expected, int):
        raise RepairError(400, "BAD_REQUEST", "expected_level must be an integer")
    _require_open(db, item, surface)
    ctx = _ctx(db, item)
    rungs = _rungs(item)
    level = int(item.get("hint_level") or 0)
    if level in rungs and expected <= level:
        hint, _ = _render_hint(db, item, ctx, level)
        return _hint_response(item, ctx, rungs, level, hint)
    nxt = next((r for r in rungs if r > level), None)
    if nxt is None:
        raise RepairError(409, "NO_MORE_HINTS", "no more hints; show the answer")
    item["hint_level"] = nxt
    hint, extra = _render_hint(db, item, ctx, nxt)
    fields = {"hint_level": nxt}
    if surface == PASS:
        fields["max_hint_level"] = max(int(item.get("max_hint_level") or 0), nxt)
    item.update(fields)
    store.update_item(db, item["id"], fields)
    _event(db, item, surface, "hint_shown", body, **extra)
    return _hint_response(item, ctx, rungs, nxt, hint)


def _hint_response(item, ctx, rungs, level, hint) -> dict:
    return {
        "item_id": item["id"],
        "hint_level": level,
        "hint_number": rungs.index(level) + 1,
        "hint_total": len(rungs),
        "hint": hint,
        "where": _where(item, ctx),
        "next": "hint" if any(r > level for r in rungs) else "answer",
    }


def _check_response(db, item, ctx, surface, result, *, reason=None, closed=False, outcome=None,
                    auto_reveal=False, answer=None) -> dict:
    where = None
    if result == classify.STILL and not closed:
        where = _where(item, ctx)
    return {
        "item_id": item["id"], "result": result, "reason": reason,
        "checks_used": int(item.get("checks_used") or 0), "check_cap": _cap(surface),
        "hints_used": _hints_used(item, surface), "where": where, "closed": closed,
        "outcome": outcome, "auto_reveal": auto_reveal, "answer": answer,
    }


def _validate_text(value, original: str) -> str:
    if not isinstance(value, str):
        raise RepairError(400, "BAD_REQUEST", "text must be a string")
    text = normalize_text(value)
    if not text:
        raise RepairError(400, "BAD_REQUEST", "text must not be empty")
    if len(text) > settings.DT_REPAIR_TEXT_MAX_CHARS or len(text) > 2 * len(original) + 40:
        raise RepairError(400, "TEXT_TOO_LONG", "text is too long")
    return text


def _uuid(value, field: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        raise RepairError(400, "BAD_REQUEST", f"{field} must be a uuid") from None


def _item_closed_for(item: dict, surface: str) -> bool:
    return _pass_closed(item) if surface == PASS else not item.get("sitting_open")


def _closed_outcome(db, item: dict, surface: str) -> Optional[str]:
    return item.get("outcome") if surface == PASS else _daily_last_outcome(db, item)


def check(db, user_id: str, item_id: int, body: dict) -> dict:
    item = _owned_item(db, user_id, item_id)
    surface = _surface(body)
    ccid = _uuid(body.get("client_check_id"), "client_check_id")
    prior = store.get_check_event(db, item_id, ccid)
    if prior:
        return _replay(db, item, prior, surface)
    ctx = _ctx(db, item)
    text = _validate_text(body.get("text"), ctx["learner"])
    _require_open(db, item, surface)
    now = _now()
    until = now + timedelta(seconds=settings.DT_REPAIR_CHECK_LOCK_S)
    if not store.acquire_check_lock(db, item_id, _iso(now), _iso(until)):
        raise RepairError(409, "CHECK_IN_PROGRESS", "a check is already running for this sentence")
    try:
        return _do_check(db, item, ctx, surface, text, ccid, body)
    except store.DuplicateCheck:
        prior = store.get_check_event(db, item_id, ccid)
        if prior:
            return _replay(db, store.get_item(db, item_id) or item, prior, surface)
        raise
    finally:
        try:
            store.release_check_lock(db, item_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("dt_repair: releasing the check lock of item %s failed: %s", item_id, exc)


def _do_check(db, item, ctx, surface, text, ccid, body) -> dict:
    current = _current_text(item, ctx)
    if normalize_text(text) == normalize_text(current):
        return _check_response(db, item, ctx, surface, "unchanged")

    cap = _cap(surface)
    if (int(item.get("calls_used") or 0) >= settings.DT_REPAIR_MAX_CALLS_PER_SITTING
            or not budget.recheck_allowed(db, item["user_id"])):
        item["hint_level"] = 4
        _close(db, item, ctx, surface, "answer_shown", answer_reason="budget", body=body,
               event_kind="answer_shown",
               extra={"text": text, "client_check_id": ccid, "result_detail": {"a": "budget"}})
        return _check_response(db, item, ctx, surface, "budget_exhausted", closed=True,
                               outcome="answer_shown", answer=_answer(db, item, ctx, "compare"))

    fields: dict = {}
    if body.get("first_edit_ms") is not None and item.get("first_edit_ms") is None:
        first_edit = _opt_ms(body.get("first_edit_ms"))
        if first_edit is not None:
            fields["first_edit_ms"] = item["first_edit_ms"] = first_edit

    active = item.get("active") or {}
    if _normalize_l2(text, ctx["l2"]) == _normalize_l2(ctx["reference"], ctx["l2"]):
        outcome_cls = {"result": classify.FIXED, "reason": None, "active": active,
                       "detail": {"r": None, "e": [], "t0": True}}
        call_fields = {"latency_ms": 0}
    else:
        rc = recheck.recheck_sentence(
            db, reference_sentence=ctx["reference"], revised_sentence=text, l2_code=ctx["l2"],
            l1_code=ctx["l1"], l2_language_id=ctx["l2_id"], l1_language_id=ctx["l1_id"])
        item["calls_used"] = int(item.get("calls_used") or 0) + 1
        fields["calls_used"] = item["calls_used"]
        call_fields = {
            "latency_ms": rc.get("latency_ms"), "tokens_in": (rc.get("tokens") or {}).get("in"),
            "tokens_out": (rc.get("tokens") or {}).get("out"), "cost_usd": rc.get("cost_usd"),
            "model_slug": rc.get("model"), "prompt_version": rc.get("prompt_version"),
        }
        if rc.get("status") != recheck.STATUS_OK:
            reason = "timeout" if rc.get("status") == recheck.STATUS_TIMEOUT else "call_failed"
            store.update_item(db, item["id"], fields)
            _event(db, item, surface, "revision_checked", body, text=text, result="error",
                   client_check_id=ccid, result_detail={"r": reason, "s": rc.get("status")}, **call_fields)
            return _check_response(db, item, ctx, surface, "error", reason=reason)
        outcome_cls = classify.classify(active, text, ctx["reference"], rc.get("errors") or [], ctx["l2"])

    result = outcome_cls["result"]
    new_active = {k: v for k, v in (outcome_cls["active"] or {}).items() if k != "model_note"}
    item["last_text"] = text
    item["active"] = new_active
    item["n_checks"] = int(item.get("n_checks") or 0) + 1
    if result == classify.STILL:
        item["checks_used"] = int(item.get("checks_used") or 0) + 1
    fields.update(last_text=text, active=new_active, n_checks=item["n_checks"],
                  checks_used=int(item.get("checks_used") or 0))
    _event(db, item, surface, "revision_checked", body, text=text, result=result, client_check_id=ccid,
           result_detail=outcome_cls["detail"], **call_fields)
    store.update_item(db, item["id"], fields)

    unsure = item.get("step_kind") == "unsure"
    if result == classify.FIXED:
        outcome = "unsure_revised" if unsure else "self_repaired"
        _close(db, item, ctx, surface, outcome, body=body)
        return _check_response(db, item, ctx, surface, result, closed=True, outcome=outcome)
    if result == classify.NO_ISSUE:
        outcome = "unsure_revised" if unsure else "repaired_alternative"
        _close(db, item, ctx, surface, outcome, body=body)
        return _check_response(db, item, ctx, surface, result, closed=True, outcome=outcome,
                               answer=_answer(db, item, ctx, _heading(outcome)))
    if int(item.get("checks_used") or 0) >= cap:
        _close(db, item, ctx, surface, "answer_shown", answer_reason="auto_cap", body=body,
               event_kind="answer_shown", extra={"result_detail": {"a": "auto_cap"}})
        return _check_response(db, item, ctx, surface, result, reason=outcome_cls["reason"], closed=True,
                               outcome="answer_shown", auto_reveal=True,
                               answer=_answer(db, item, ctx, "compare"))
    return _check_response(db, item, ctx, surface, result, reason=outcome_cls["reason"])


def _replay(db, item: dict, event: dict, surface: str) -> dict:
    """The stored result of an already-processed client_check_id; no new call."""
    ctx = _ctx(db, item)
    closed = _item_closed_for(item, surface)
    outcome = _closed_outcome(db, item, surface) if closed else None
    if event.get("kind") == "answer_shown":
        return _check_response(db, item, ctx, surface, "budget_exhausted", closed=True,
                               outcome="answer_shown", answer=_answer(db, item, ctx, "compare"))
    result = event.get("result") or "error"
    detail = event.get("result_detail") or {}
    if result == "error":
        return _check_response(db, item, ctx, surface, "error", reason=detail.get("r") or "call_failed")
    auto = (closed and result == classify.STILL and outcome == "answer_shown")
    answer = None
    if closed and (result == classify.NO_ISSUE or auto):
        answer = _answer(db, item, ctx, _heading(outcome))
    return _check_response(db, item, ctx, surface, result, reason=detail.get("r"), closed=closed,
                           outcome=outcome, auto_reveal=auto, answer=answer)


def reveal(db, user_id: str, item_id: int, body: dict) -> dict:
    item = _owned_item(db, user_id, item_id)
    surface = _surface(body)
    reason = body.get("reason")
    if reason not in ("asked", "grader_failed", "direct"):
        raise RepairError(400, "BAD_REQUEST", "reason must be asked, grader_failed or direct")
    ctx = _ctx(db, item)
    if _item_closed_for(item, surface):
        outcome = _closed_outcome(db, item, surface)
        if outcome is None:
            raise RepairError(409, "NOT_OPENED", "open the item first")
        return {"item_id": item["id"], "closed": True, "outcome": outcome,
                "answer": _answer(db, item, ctx, _heading(outcome))}
    _require_open(db, item, surface)
    outcome = "shown_directly" if reason == "direct" else "answer_shown"
    _close(db, item, ctx, surface, outcome, answer_reason=reason, body=body, event_kind="answer_shown",
           extra={"result_detail": {"a": reason}})
    return {"item_id": item["id"], "closed": True, "outcome": outcome,
            "answer": _answer(db, item, ctx, "compare")}


def dispute(db, user_id: str, item_id: int, body: dict) -> dict:
    item = _owned_item(db, user_id, item_id)
    surface = _surface(body)
    ctx = _ctx(db, item)
    if _item_closed_for(item, surface):
        outcome = _closed_outcome(db, item, surface)
        if outcome is None:
            raise RepairError(409, "NOT_OPENED", "open the item first")
        answer = None if outcome == "unsure_dismissed" else _answer(db, item, ctx, _heading(outcome))
        return {"item_id": item["id"], "closed": True, "outcome": outcome, "answer": answer}
    _require_open(db, item, surface)
    if item.get("step_kind") == "unsure":
        _close(db, item, ctx, surface, "unsure_dismissed", body=body, event_kind="kept")
        return {"item_id": item["id"], "closed": True, "outcome": "unsure_dismissed", "answer": None}
    _close(db, item, ctx, surface, "disputed", body=body, event_kind="disputed")
    return {"item_id": item["id"], "closed": True, "outcome": "disputed",
            "answer": _answer(db, item, ctx, "disputed")}


def skip(db, user_id: str, item_id: int, body: dict) -> dict:
    item = _owned_item(db, user_id, item_id)
    surface = _surface(body)
    if surface != DAILY:
        raise RepairError(400, "BAD_REQUEST", "repair_pass items are skipped by finishing the session")
    if item.get("sitting_open"):
        ctx = _ctx(db, item)
        _close(db, item, ctx, DAILY, "skipped", body=body, event_kind="skipped")
    return {"item_id": item["id"], "closed": True, "outcome": "skipped", "answer": None}


def _finish_session(db, session: dict, *, status: str, closed_early, body: dict) -> list:
    items = store.get_items(db, session["id"])
    sub = store.get_submission(db, session["submission_id"]) or {}
    passage = store.get_passage(db, sub.get("passage_id")) if sub else None
    for item in items:
        if _pass_closed(item):
            continue
        outcome = "unsure_skipped" if item.get("step_kind") == "unsure" else "skipped"
        ctx = {"learner": "", "reference": "", "l1": None, "l2": None}
        if passage:
            ctx["learner"] = (sub.get("reproduction") or "")[item["repro_start"]:item["repro_end"]]
        _close(db, item, ctx, PASS, outcome, body={}, event_kind="skipped")
    now = _now()
    created = scheduling._ts(session.get("created_at"))
    total_ms = int((now - created).total_seconds() * 1000) if created else None
    fields = {"status": status, "finished_at": _iso(now), "total_ms": total_ms,
              "closed_early": closed_early}
    store.update_session(db, session["id"], fields)
    session.update(fields)
    if status == "finished":
        seconds = min(settings.DT_REPAIR_PASS_CREDIT_MAX_S, _seconds((body or {}).get("active_ms")))
        if seconds > 0:
            _credit(db, session["user_id"], session["l2_language_id"], seconds,
                    "dt_repair_session", session["id"])
    return items


def finish(db, user_id: str, session_id: int, body: dict) -> dict:
    session = _owned_session(db, user_id, session_id)
    closed_early = body.get("closed_early")
    if not isinstance(closed_early, bool):
        raise RepairError(400, "BAD_REQUEST", "closed_early must be a boolean")
    if session.get("status") == "open":
        items = _finish_session(db, session, status="finished", closed_early=closed_early, body=body)
    else:
        items = store.get_items(db, session["id"])
    return {"session_id": session["id"], "session_status": session.get("status"),
            "summary": summary(items), "result_available": True}


def full_result(db, user_id: str, submission_id: int) -> dict:
    _owned_submission(db, user_id, submission_id)
    session = store.get_session_by_submission(db, submission_id)
    if session and session.get("status") == "open":
        if _is_stale(session, _now()):
            _finish_session(db, session, status="abandoned", closed_early=None, body={})
        else:
            raise RepairError(409, "REPAIR_IN_PROGRESS", "finish the repair session first")
    from routes.dual_translation import _cached_grade  # lazy: avoids an import cycle at load
    contract = _cached_grade(db, submission_id)
    if contract is None:
        raise RepairError(404, "NOT_FOUND", "this submission has no grade")
    return contract


def _due_items(db, user_id: str, language_id: int, *, write: bool) -> list:
    now = _now()
    local_today = _local_today(db, user_id, language_id)
    if write:
        try:
            store.expire_items(db, user_id, language_id, _iso(now))
        except Exception as exc:  # noqa: BLE001
            logger.warning("dt_repair: expiring items failed: %s", exc)
    open_subs = {s["submission_id"] for s in store.open_sessions(db, user_id)}
    rows = [r for r in store.due_candidates(db, user_id, language_id)
            if r.get("submission_id") not in open_subs
            and (scheduling.is_due(r, local_today, now) or r.get("sitting_open"))]
    rows.sort(key=scheduling.due_order_key)
    return rows


def practice_due(db, user_id: str, language_id: int) -> dict:
    finish_stale(db, user_id)
    rows = _due_items(db, user_id, language_id, write=True)
    items = []
    for position, item in enumerate(rows[:settings.DT_REPAIR_DAILY_ITEMS]):
        ctx = _ctx(db, item)
        view = dict(item)
        if not item.get("sitting_open"):
            rungs = _rungs(item)
            view.update(hint_level=1 if 1 in rungs else 0, checks_used=0, last_text=None,
                        active=_original_active(db, item))
        prompts, _ = _prompts_for(db, ctx)
        items.append(_step(view, ctx, surface=DAILY, prompt_l1=_at(prompts, item["sentence_index"]),
                           position=position, state="open",
                           from_date=_local_date_of(db, user_id, language_id,
                                                    ctx["submission"].get("created_at"))))
    return {"total_due": len(rows), "items": items}


def count_due(db, user_id: str, language_id: int, today: Optional[str] = None) -> int:
    """Due items for the daily-session block (read-only)."""
    if not settings.DT_GUIDED_REPAIR:
        return 0
    return len(_due_items(db, user_id, language_id, write=False))
