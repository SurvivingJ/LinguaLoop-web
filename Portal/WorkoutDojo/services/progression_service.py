"""WorkoutOS — Progression Group Service"""

import json
import os
import uuid
from datetime import datetime

from config import PROGRESSIONS_FILE


def _load():
    if not os.path.exists(PROGRESSIONS_FILE):
        return []
    with open(PROGRESSIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    os.makedirs(os.path.dirname(PROGRESSIONS_FILE), exist_ok=True)
    with open(PROGRESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_progressions() -> list[dict]:
    return _load()


def get_progression(id: str) -> dict | None:
    return next((p for p in list_progressions() if p["id"] == id), None)


def save_progression(data: dict) -> dict:
    progressions = list_progressions()
    data = dict(data)
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now().isoformat()
    progressions.append(data)
    _save(progressions)
    return data


def update_progression(id: str, data: dict) -> dict | None:
    progressions = list_progressions()
    for i, p in enumerate(progressions):
        if p["id"] == id:
            data = dict(data)
            data["id"] = id
            data["created_at"] = p.get("created_at", datetime.now().isoformat())
            progressions[i] = data
            _save(progressions)
            return data
    return None


def delete_progression(id: str) -> bool:
    progressions = list_progressions()
    new = [p for p in progressions if p["id"] != id]
    if len(new) < len(progressions):
        _save(new)
        return True
    return False


def list_progression_names() -> list[dict]:
    """Return [{id, name}] for dropdowns."""
    return [{"id": p["id"], "name": p["name"]} for p in list_progressions()]


def get_progression_for_exercise(exercise_id: str) -> dict | None:
    """Find which progression group contains this exercise."""
    for p in list_progressions():
        if exercise_id in p.get("exercises", []):
            return p
    return None
