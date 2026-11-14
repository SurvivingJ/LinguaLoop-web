"""Every DB read/write of guided repair (tech 3, 9). Each function is a
monkeypatch boundary for tests; nothing else in the package touches ``db``
except ``budget`` and ``sentences.l1_prompts``.

Supabase query-builder chains, as in ``routes/dual_translation.py``.
"""

from __future__ import annotations

from typing import Optional

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
