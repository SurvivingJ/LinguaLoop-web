"""Guided self-repair settings (tech section 2).

Read from the environment at import - the same convention as
``routes/dual_translation.DT_ERROR_CARD_INTERLEAVE_EVERY`` - so ``config.py`` is not
touched. Tests monkeypatch the module attributes; every reader looks them up on
this module at call time (``settings.X``), never copies them at import.
"""

from __future__ import annotations

import os


def _bool(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _int_list(name: str, default: str) -> tuple:
    raw = os.environ.get(name, default)
    try:
        values = tuple(max(1, int(part)) for part in raw.split(",") if part.strip())
        return values or tuple(int(p) for p in default.split(","))
    except (TypeError, ValueError):
        return tuple(int(p) for p in default.split(","))


# Feature flag. Off -> no session, submit is exactly today's response, every
# /repair/* endpoint answers 503 REPAIR_DISABLED, no daily block.
DT_GUIDED_REPAIR = _bool("DT_GUIDED_REPAIR", "true")

DT_REPAIR_MAX_TARGETS = _int("DT_REPAIR_MAX_TARGETS", 3, 0)
DT_REPAIR_BYPASS_FLAGGED = _int("DT_REPAIR_BYPASS_FLAGGED", 5, 1)
# Provisional, untuned: with the grader's 0.9/0.6/0.3 mapping only `low`
# qualifies, and low entries exist only with DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE.
DT_REPAIR_UNSURE_CONFIDENCE_MAX = _float("DT_REPAIR_UNSURE_CONFIDENCE_MAX", 0.45)
DT_REPAIR_CHECK_CAP_PASS = _int("DT_REPAIR_CHECK_CAP_PASS", 4, 1)
DT_REPAIR_CHECK_CAP_DAILY = _int("DT_REPAIR_CHECK_CAP_DAILY", 3, 1)
DT_REPAIR_MAX_CALLS_PER_SITTING = _int("DT_REPAIR_MAX_CALLS_PER_SITTING", 6, 1)
DT_REPAIR_LOCATION_MAX_SHARE = _float("DT_REPAIR_LOCATION_MAX_SHARE", 0.4)
DT_REPAIR_RECHECK_TIMEOUT_S = _float("DT_REPAIR_RECHECK_TIMEOUT_S", 5.0)
DT_REPAIR_TEXT_MAX_CHARS = _int("DT_REPAIR_TEXT_MAX_CHARS", 400, 1)
DT_REPAIR_DAILY_ITEMS = _int("DT_REPAIR_DAILY_ITEMS", 3, 1)
DT_REPAIR_FIRST_DUE_MIN_HOURS = _int("DT_REPAIR_FIRST_DUE_MIN_HOURS", 20, 0)
DT_REPAIR_EXPIRY_DAYS = _int("DT_REPAIR_EXPIRY_DAYS", 30, 1)
DT_REPAIR_HINTED_RETURN_DAYS = _int("DT_REPAIR_HINTED_RETURN_DAYS", 3, 1)
DT_REPAIR_FAILED_RETURN_DAYS = _int_list("DT_REPAIR_FAILED_RETURN_DAYS", "2,4")
DT_REPAIR_RETIRE_AFTER_FAILED = _int("DT_REPAIR_RETIRE_AFTER_FAILED", 3, 1)
DT_REPAIR_MAX_SITTINGS = _int("DT_REPAIR_MAX_SITTINGS", 5, 1)
DT_REPAIR_TOKEN_ALLOWANCE = _int("DT_REPAIR_TOKEN_ALLOWANCE", 40000, 0)
DT_REPAIR_MAX_CHECKS_PER_DAY = _int("DT_REPAIR_MAX_CHECKS_PER_DAY", 60, 0)
DT_REPAIR_SESSION_STALE_HOURS = _int("DT_REPAIR_SESSION_STALE_HOURS", 24, 1)
DT_REPAIR_AUTO_ADVANCE_MS = _int("DT_REPAIR_AUTO_ADVANCE_MS", 1600, 0)

# Not in the tech table but fixed by the text of tech 4.4 / 4.6 / 7.5.
DT_REPAIR_SITTING_RESUME_HOURS = 2       # 4.4: a daily sitting opened < 2 h ago resumes
DT_REPAIR_CHECK_LOCK_S = 15              # 4.6 step 1: check_lock_until = now() + 15 s
DT_REPAIR_PASS_CREDIT_MAX_S = 300        # 7.5: repair-pass study time cap
DT_REPAIR_DAILY_CREDIT_MAX_S = 120       # 7.5: daily sitting study time cap
DT_REPAIR_STALE_PER_CALL = 5             # 7.4: stale sessions finished per /practice/due


def snapshot() -> dict:
    """The settings a session records at creation (``dt_repair_session.settings``)."""
    return {
        "max_targets": DT_REPAIR_MAX_TARGETS,
        "bypass": DT_REPAIR_BYPASS_FLAGGED,
        "unsure_max": DT_REPAIR_UNSURE_CONFIDENCE_MAX,
        "cap_pass": DT_REPAIR_CHECK_CAP_PASS,
        "loc_share": DT_REPAIR_LOCATION_MAX_SHARE,
    }
