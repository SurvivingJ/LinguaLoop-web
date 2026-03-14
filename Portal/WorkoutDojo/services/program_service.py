"""WorkoutOS — Program Service (S3)"""

import csv
import json
import os
import uuid
from datetime import date, datetime, timedelta

from config import PROGRAMS_FILE, SESSIONS_FILE


def _load():
    if not os.path.exists(PROGRAMS_FILE):
        return []
    with open(PROGRAMS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    os.makedirs(os.path.dirname(PROGRAMS_FILE), exist_ok=True)
    with open(PROGRAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_programs() -> list[dict]:
    return _load()


def get_program(id: str) -> dict | None:
    return next((p for p in list_programs() if p["id"] == id), None)


def get_active_program() -> dict | None:
    return next((p for p in list_programs() if p.get("active")), None)


def save_program(data: dict) -> dict:
    programs = list_programs()
    data = dict(data)
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now().isoformat()
    data.setdefault("active", False)
    programs.append(data)
    _save(programs)
    return data


def update_program(id: str, data: dict) -> dict | None:
    programs = list_programs()
    for i, p in enumerate(programs):
        if p["id"] == id:
            data = dict(data)
            data["id"] = id
            data["created_at"] = p.get("created_at", datetime.now().isoformat())
            data["active"] = p.get("active", False)
            programs[i] = data
            _save(programs)
            return data
    return None


def activate_program(id: str) -> bool:
    programs = list_programs()
    found = False
    for p in programs:
        p["active"] = p["id"] == id
        if p["id"] == id:
            found = True
    if found:
        _save(programs)
    return found


def delete_program(id: str) -> bool:
    programs = list_programs()
    new = [p for p in programs if p["id"] != id]
    if len(new) < len(programs):
        _save(new)
        return True
    return False


def _load_sessions_this_week(week_start: date) -> int:
    """Count sessions logged in the calendar week starting week_start."""
    if not os.path.exists(SESSIONS_FILE):
        return 0
    week_end = week_start + timedelta(days=7)
    count = 0
    with open(SESSIONS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                session_date = date.fromisoformat(row["date"].strip())
                if week_start <= session_date < week_end:
                    count += 1
            except (ValueError, KeyError):
                continue
    return count


def _load_total_sessions(started_at: date) -> int:
    """Count all sessions since the program started."""
    if not os.path.exists(SESSIONS_FILE):
        return 0
    count = 0
    with open(SESSIONS_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                session_date = date.fromisoformat(row["date"].strip())
                if session_date >= started_at:
                    count += 1
            except (ValueError, KeyError):
                continue
    return count


def get_program_status(program: dict) -> dict:
    """
    Compute runtime status for the active program widget.
    Returns dict with: current_week_number, week_index, today_day,
    today_entry, is_deload, sessions_this_week, total_sessions_expected,
    pct_complete, week_start.
    """
    today = date.today()
    today_day = today.strftime("%A").lower()  # "monday", "tuesday", ...

    # Parse start date
    try:
        started_at = date.fromisoformat(program.get("started_at", today.isoformat()))
    except ValueError:
        started_at = today

    duration_weeks = program.get("duration_weeks", 1)
    weeks = program.get("weeks", [])

    # Current week number (1-based), clamped to program duration
    days_elapsed = (today - started_at).days
    current_week_number = min(days_elapsed // 7 + 1, duration_weeks)
    week_index = current_week_number - 1

    # Week start date for this week
    week_start = started_at + timedelta(weeks=week_index)

    # Locate the week definition
    current_week = None
    if week_index < len(weeks):
        current_week = weeks[week_index]
    elif weeks:
        # Repeat last week if program runs long
        current_week = weeks[-1]

    is_deload = current_week.get("is_deload", False) if current_week else False
    today_entry = None
    if current_week:
        today_entry = current_week.get("days", {}).get(today_day)

    # Count non-rest days this week
    total_sessions_expected = 0
    if current_week:
        for day_entry in current_week.get("days", {}).values():
            if day_entry is not None:
                total_sessions_expected += 1

    sessions_this_week = _load_sessions_this_week(week_start)

    # Overall completion percentage
    total_training_days = sum(
        1 for w in weeks for d in w.get("days", {}).values() if d is not None
    )
    total_done = _load_total_sessions(started_at)
    pct_complete = round(100 * total_done / total_training_days, 1) if total_training_days else 0.0

    return {
        "current_week_number": current_week_number,
        "week_index": week_index,
        "today_day": today_day,
        "today_entry": today_entry,
        "is_deload": is_deload,
        "sessions_this_week": sessions_this_week,
        "total_sessions_expected": total_sessions_expected,
        "pct_complete": pct_complete,
        "week_start": week_start.isoformat(),
    }
