"""WorkoutOS — Session Service (S5)"""

import csv
import os
import uuid
from datetime import date, datetime

from config import SESSIONS_FILE, SETS_LOG_FILE

_SESSIONS_HEADER = ["session_id", "plan_id", "date", "duration_minutes", "notes", "completed_at"]
_SETS_HEADER = ["session_id", "exercise_id", "set_number", "reps", "weight_kg", "rpe", "is_warmup", "duration_seconds", "timestamp"]


def _ensure_csv(path, header):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)


_sets_csv_migrated = False


def _migrate_sets_csv_if_needed():
    """Add duration_seconds column to existing sets_log.csv if missing."""
    global _sets_csv_migrated
    if _sets_csv_migrated or not os.path.exists(SETS_LOG_FILE):
        _sets_csv_migrated = True
        return

    with open(SETS_LOG_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header and "duration_seconds" not in header:
            rows = list(reader)
            # Insert duration_seconds before timestamp (last column)
            ts_idx = header.index("timestamp") if "timestamp" in header else len(header)
            header.insert(ts_idx, "duration_seconds")
            for row in rows:
                row.insert(ts_idx, "")
            with open(SETS_LOG_FILE, "w", newline="", encoding="utf-8") as wf:
                writer = csv.writer(wf)
                writer.writerow(header)
                writer.writerows(rows)

    _sets_csv_migrated = True


def start_session(plan_id: str) -> str:
    session_id = str(uuid.uuid4())
    return session_id


def log_set(
    session_id: str,
    exercise_id: str,
    set_number: int,
    reps: int,
    weight_kg: float,
    rpe: float | None,
    is_warmup: bool,
    duration_seconds: int | None = None,
) -> dict:
    _ensure_csv(SETS_LOG_FILE, _SETS_HEADER)
    _migrate_sets_csv_if_needed()
    row = {
        "session_id": session_id,
        "exercise_id": exercise_id,
        "set_number": set_number,
        "reps": reps,
        "weight_kg": round(float(weight_kg), 2),
        "rpe": round(float(rpe), 1) if rpe is not None else "",
        "is_warmup": str(is_warmup).lower(),
        "duration_seconds": int(duration_seconds) if duration_seconds is not None else "",
        "timestamp": datetime.now().isoformat(),
    }
    with open(SETS_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_SETS_HEADER)
        writer.writerow(row)
    return row


def complete_session(
    session_id: str,
    plan_id: str,
    duration_minutes: int,
    notes: str = "",
) -> dict:
    _ensure_csv(SESSIONS_FILE, _SESSIONS_HEADER)
    row = {
        "session_id": session_id,
        "plan_id": plan_id,
        "date": date.today().isoformat(),
        "duration_minutes": duration_minutes,
        "notes": notes,
        "completed_at": datetime.now().isoformat(),
    }
    with open(SESSIONS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_SESSIONS_HEADER)
        writer.writerow(row)
    return row


def get_session_history(exercise_id: str | None = None, limit: int = 200) -> list[dict]:
    _ensure_csv(SETS_LOG_FILE, _SETS_HEADER)
    rows = []
    with open(SETS_LOG_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if exercise_id and row.get("exercise_id") != exercise_id:
                continue
            rows.append({
                "session_id": row["session_id"],
                "exercise_id": row["exercise_id"],
                "set_number": int(row.get("set_number", 0)),
                "reps": int(row.get("reps", 0)),
                "weight_kg": float(row.get("weight_kg", 0)),
                "rpe": float(row["rpe"]) if row.get("rpe") else None,
                "is_warmup": row.get("is_warmup", "false").lower() == "true",
                "duration_seconds": int(row["duration_seconds"]) if row.get("duration_seconds") else None,
                "timestamp": row.get("timestamp", ""),
            })
    rows.sort(key=lambda r: r["timestamp"])
    return rows[-limit:] if limit else rows


def get_recent_sessions(limit: int = 10) -> list[dict]:
    _ensure_csv(SESSIONS_FILE, _SESSIONS_HEADER)
    rows = []
    with open(SESSIONS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "session_id": row["session_id"],
                "plan_id": row["plan_id"],
                "date": row["date"],
                "duration_minutes": int(row.get("duration_minutes", 0)),
                "notes": row.get("notes", ""),
                "completed_at": row.get("completed_at", ""),
            })
    rows.sort(key=lambda r: r["completed_at"], reverse=True)
    return rows[:limit]
