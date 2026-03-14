"""WorkoutOS — Exercise Service (S1)"""

import json
import os
import uuid
from datetime import datetime

from config import EXERCISES_FILE, MOBILITY_FILE


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_exercises() -> list[dict]:
    return _load(EXERCISES_FILE)


def get_exercise(id: str) -> dict | None:
    return next((e for e in list_exercises() if e["id"] == id), None)


def save_exercise(data: dict) -> dict:
    exercises = list_exercises()
    data = dict(data)
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now().isoformat()
    exercises.append(data)
    _save(EXERCISES_FILE, exercises)
    return data


def update_exercise(id: str, data: dict) -> dict | None:
    exercises = list_exercises()
    for i, e in enumerate(exercises):
        if e["id"] == id:
            data = dict(data)
            data["id"] = id
            data["created_at"] = e.get("created_at", datetime.now().isoformat())
            exercises[i] = data
            _save(EXERCISES_FILE, exercises)
            return data
    return None


def delete_exercise(id: str) -> bool:
    exercises = list_exercises()
    new = [e for e in exercises if e["id"] != id]
    if len(new) < len(exercises):
        _save(EXERCISES_FILE, new)
        return True
    return False


def list_mobility() -> list[dict]:
    return _load(MOBILITY_FILE)


def get_mobility(id: str) -> dict | None:
    return next((m for m in list_mobility() if m["id"] == id), None)


def save_mobility(data: dict) -> dict:
    items = list_mobility()
    data = dict(data)
    data["id"] = str(uuid.uuid4())
    items.append(data)
    _save(MOBILITY_FILE, items)
    return data
