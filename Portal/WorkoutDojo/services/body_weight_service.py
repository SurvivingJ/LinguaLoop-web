"""WorkoutOS — Body Weight Service (S4)"""

import csv
import os
from datetime import date, datetime, timedelta

from config import BODY_WEIGHT_FILE

_HEADER = ["date", "weight_kg", "time_of_day", "notes"]


def _ensure_file():
    if not os.path.exists(BODY_WEIGHT_FILE):
        os.makedirs(os.path.dirname(BODY_WEIGHT_FILE), exist_ok=True)
        with open(BODY_WEIGHT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_HEADER)


def log_weight(weight_kg: float, time_of_day: str = "morning", notes: str = "") -> dict:
    _ensure_file()
    entry = {
        "date": date.today().isoformat(),
        "weight_kg": round(float(weight_kg), 2),
        "time_of_day": time_of_day,
        "notes": notes,
    }
    with open(BODY_WEIGHT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_HEADER)
        writer.writerow(entry)
    return entry


def get_history() -> list[dict]:
    _ensure_file()
    entries = []
    with open(BODY_WEIGHT_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                entries.append({
                    "date": row["date"].strip(),
                    "weight_kg": float(row["weight_kg"].strip()),
                    "time_of_day": row.get("time_of_day", "").strip(),
                    "notes": row.get("notes", "").strip(),
                })
            except (ValueError, KeyError):
                continue
    return sorted(entries, key=lambda e: e["date"])


def get_rolling_average(days: int = 7) -> list[dict]:
    """
    Compute rolling N-day average weight for each date in the history.
    Returns list of {date, avg_weight} dicts, ordered by date.
    """
    history = get_history()
    if not history:
        return []

    # Build a date → weight map (use last entry per day)
    date_map: dict[str, float] = {}
    for entry in history:
        date_map[entry["date"]] = entry["weight_kg"]

    if not date_map:
        return []

    # Fill date range
    sorted_dates = sorted(date_map.keys())
    start = date.fromisoformat(sorted_dates[0])
    end = date.fromisoformat(sorted_dates[-1])

    result = []
    current = start
    while current <= end:
        ds = current.isoformat()
        # Collect values in the window
        window = []
        for i in range(days):
            d = (current - timedelta(days=i)).isoformat()
            if d in date_map:
                window.append(date_map[d])
        if window:
            result.append({"date": ds, "avg_weight": round(sum(window) / len(window), 2)})
        current += timedelta(days=1)

    return result
