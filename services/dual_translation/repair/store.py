"""Every DB read/write of guided repair (tech 3, 9). Each function is a
monkeypatch boundary for tests; nothing else in the package touches ``db``
except ``budget`` and ``sentences.l1_prompts``.

Supabase query-builder chains, as in ``routes/dual_translation.py``.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

SESSION_COLUMNS = (
    "id, submission_id, user_id, l2_language_id, l1_language_id, status, n_sentences, n_flagged, "
    "n_steps, grade_tier, prompt_version, hint_version, settings, closed_early, total_ms, "
    "created_at, finished_at"
)
ITEM_COLUMNS = "*"
ERROR_COLUMNS = (
    "id, sentence_index, span_reproduction, span_reference, subtype, severity, confidence, "
    "confidence_label, span_source, correction_source, learner_form, corrected_form, "
    "explanation, model_note, explanation_source"
)


class DuplicateCheck(Exception):
    """An event with this (item_id, client_check_id) already exists."""


# ── availability: migrations/dt_guided_self_repair.sql not applied ─────────
# Until the owner applies the migration every insert into dt_repair_session
# fails. The submit hook must then serve today's result without logging an
# error on every submission: the first failure that names a missing repair table
# marks the tables unavailable for MISSING_TABLES_RETRY_S (the hooks and the
# daily-block count skip the DB entirely meanwhile), and is logged ONCE per
# process as a warning. After the pause the tables are probed again, so applying
# the migration needs no restart.
MISSING_TABLES_RETRY_S = 600
_availability = {"unavailable_until": 0.0, "warned": False}


def is_missing_table_error(exc: BaseException) -> bool:
    """PostgREST's answer for a table that does not exist: PGRST205 ("Could not
    find the table 'public.dt_repair_session' in the schema cache") or Postgres
    42P01 ("relation ... does not exist")."""
    text = str(exc)
    if "PGRST205" in text or "42P01" in text:
        return True
    return "dt_repair_" in text and ("does not exist" in text or "Could not find the table" in text)


def tables_available() -> bool:
    return time.monotonic() >= _availability["unavailable_until"]


def note_missing_tables(exc: BaseException) -> None:
    _availability["unavailable_until"] = time.monotonic() + MISSING_TABLES_RETRY_S
    if not _availability["warned"]:
        _availability["warned"] = True
        logger.warning(
            "dt_repair: the guided-repair tables are missing (%s). Is "
            "migrations/dt_guided_self_repair.sql applied? Submissions get today's result view; "
            "retrying every %d s. Logged once per process.", exc, MISSING_TABLES_RETRY_S)
    else:
        logger.debug("dt_repair: repair tables still missing: %s", exc)


def reset_availability() -> None:
    """Tests: forget a recorded missing-tables failure."""
    _availability.update(unavailable_until=0.0, warned=False)


def _one(resp) -> Optional[dict]:
    data = getattr(resp, "data", None) or []
    return data[0] if data else None


# ── existing tables (read only) ─────────────────────────────────────────────

def get_submission(db, submission_id: int) -> Optional[dict]:
    return _one(db.table("dt_submission")
                .select("id, user_id, passage_id, l1_language_id, reproduction, created_at")
                .eq("id", submission_id).limit(1).execute())


def get_passage(db, passage_id: int) -> Optional[dict]:
    return _one(db.table("dt_passage")
                .select("id, l2_text, l2_language_id, age_tier, status, source_ref_id, "
                        "sentence_start, sentence_end")
                .eq("id", passage_id).limit(1).execute())


def get_grade(db, submission_id: int) -> Optional[dict]:
    return _one(db.table("dt_grade").select("scores, overall_band, grader_trace")
                .eq("submission_id", submission_id).limit(1).execute())


def get_error_rows(db, submission_id: int) -> list:
    """dt_error_instance rows with ids and the grading-asset columns. Raises when
    the asset columns are missing (the caller treats that as ineligible)."""
    return (db.table("dt_error_instance").select(ERROR_COLUMNS)
            .eq("submission_id", submission_id).execute()).data or []


def get_l1_passage_text(db, passage_id: int, l1_language_id: int) -> Optional[str]:
    row = _one(db.table("dt_passage_reference").select("l1_text")
               .eq("passage_id", passage_id).eq("l1_language_id", l1_language_id)
               .limit(1).execute())
    return (row or {}).get("l1_text")


# ── dt_repair_session ───────────────────────────────────────────────────────

def insert_session(db, row: dict) -> dict:
    """Insert; on a UNIQUE(submission_id) conflict return the existing row."""
    try:
        created = _one(db.table("dt_repair_session").insert(row).execute())
        if created:
            return created
    except Exception:
        existing = get_session_by_submission(db, row["submission_id"])
        if existing:
            return existing
        raise
    existing = get_session_by_submission(db, row["submission_id"])
    if existing is None:
        raise RuntimeError("dt_repair_session insert returned no row")
    return existing


def get_session(db, session_id: int) -> Optional[dict]:
    return _one(db.table("dt_repair_session").select(SESSION_COLUMNS)
                .eq("id", session_id).limit(1).execute())


def get_session_by_submission(db, submission_id: int) -> Optional[dict]:
    return _one(db.table("dt_repair_session").select(SESSION_COLUMNS)
                .eq("submission_id", submission_id).limit(1).execute())


def update_session(db, session_id: int, fields: dict) -> None:
    db.table("dt_repair_session").update(fields).eq("id", session_id).execute()


def open_sessions(db, user_id: str, limit: int = 20) -> list:
    return (db.table("dt_repair_session").select(SESSION_COLUMNS)
            .eq("user_id", user_id).eq("status", "open")
            .order("created_at").limit(limit).execute()).data or []


# ── dt_repair_item ──────────────────────────────────────────────────────────

def insert_items(db, rows: list) -> list:
    if not rows:
        return []
    return db.table("dt_repair_item").insert(rows).execute().data or []


def get_item(db, item_id: int) -> Optional[dict]:
    return _one(db.table("dt_repair_item").select(ITEM_COLUMNS).eq("id", item_id).limit(1).execute())


def get_items(db, session_id: int) -> list:
    return (db.table("dt_repair_item").select(ITEM_COLUMNS)
            .eq("session_id", session_id).order("id").execute()).data or []


def update_item(db, item_id: int, fields: dict) -> None:
    db.table("dt_repair_item").update(fields).eq("id", item_id).execute()


def due_candidates(db, user_id: str, l2_language_id: int) -> list:
    """Every queue_status='due' item of (user, L2); the due predicate and the
    ordering are applied in Python (scheduling.is_due / due_order_key)."""
    return (db.table("dt_repair_item").select(ITEM_COLUMNS)
            .eq("user_id", user_id).eq("l2_language_id", l2_language_id)
            .eq("queue_status", "due").execute()).data or []


def expire_items(db, user_id: str, l2_language_id: int, now_iso: str) -> None:
    (db.table("dt_repair_item").update({"queue_status": "expired"})
     .eq("user_id", user_id).eq("l2_language_id", l2_language_id)
     .eq("queue_status", "due").lte("expires_at", now_iso).execute())


def acquire_check_lock(db, item_id: int, now_iso: str, until_iso: str) -> bool:
    """Tech 4.6 step 1: conditional UPDATE; acquired iff a row came back."""
    resp = (db.table("dt_repair_item").update({"check_lock_until": until_iso})
            .eq("id", item_id)
            .or_(f"check_lock_until.is.null,check_lock_until.lt.{now_iso}")
            .execute())
    return bool(getattr(resp, "data", None))


def release_check_lock(db, item_id: int) -> None:
    db.table("dt_repair_item").update({"check_lock_until": None}).eq("id", item_id).execute()


# ── dt_repair_event ─────────────────────────────────────────────────────────

def insert_event(db, row: dict) -> Optional[dict]:
    try:
        return _one(db.table("dt_repair_event").insert(row).execute())
    except Exception as exc:
        text = str(exc)
        if row.get("client_check_id") and ("23505" in text or "duplicate key" in text.lower()):
            raise DuplicateCheck(text) from exc
        raise


def get_check_event(db, item_id: int, client_check_id: str) -> Optional[dict]:
    return _one(db.table("dt_repair_event").select("*")
                .eq("item_id", item_id).eq("client_check_id", client_check_id)
                .limit(1).execute())


def last_episode_event(db, item_id: int) -> Optional[dict]:
    return _one(db.table("dt_repair_event").select("*")
                .eq("item_id", item_id).eq("kind", "episode_closed")
                .order("id", desc=True).limit(1).execute())
