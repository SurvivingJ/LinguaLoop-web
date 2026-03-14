"""WorkoutOS — Workout Plan Service (S2)"""

import json
import os
import uuid
from datetime import datetime

from config import PLANS_FILE, WORK_TIME_ESTIMATE_SECONDS


def _load():
    if not os.path.exists(PLANS_FILE):
        return []
    with open(PLANS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    os.makedirs(os.path.dirname(PLANS_FILE), exist_ok=True)
    with open(PLANS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _compute_duration(entries: list[dict]) -> int:
    total = 0
    for entry in entries:
        for s in entry.get("sets", []):
            total += WORK_TIME_ESTIMATE_SECONDS + s.get("rest_seconds", 90)
    return max(1, total // 60)


def list_plans() -> list[dict]:
    return _load()


def get_plan(id: str) -> dict | None:
    return next((p for p in list_plans() if p["id"] == id), None)


def save_plan(data: dict) -> dict:
    plans = list_plans()
    data = dict(data)
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now().isoformat()
    data["estimated_duration_minutes"] = _compute_duration(data.get("entries", []))
    plans.append(data)
    _save(plans)
    return data


def update_plan(id: str, data: dict) -> dict | None:
    plans = list_plans()
    for i, p in enumerate(plans):
        if p["id"] == id:
            data = dict(data)
            data["id"] = id
            data["created_at"] = p.get("created_at", datetime.now().isoformat())
            data["estimated_duration_minutes"] = _compute_duration(data.get("entries", []))
            plans[i] = data
            _save(plans)
            return data
    return None


def delete_plan(id: str) -> bool:
    plans = list_plans()
    new = [p for p in plans if p["id"] != id]
    if len(new) < len(plans):
        _save(new)
        return True
    return False
