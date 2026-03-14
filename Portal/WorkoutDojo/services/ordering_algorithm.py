"""
WorkoutOS — Exercise Ordering Algorithm (S16)

Determines optimal exercise execution order within a session.
The user's drag-and-drop order is the baseline; this algorithm
refines it by applying gym science principles.

Rules (in priority order):
1. Keep superset groups intact and adjacent.
2. Compound exercises before isolations (within same session).
3. For push+pull mix sessions, alternate horizontal push/pull.
4. Respect the user's original relative order as tiebreaker.
"""

from __future__ import annotations

# Movement pattern execution priority (lower = earlier in session)
_PATTERN_PRIORITY: dict[str, int] = {
    "squat":           1,
    "hip_hinge":       2,
    "horizontal_push": 3,
    "horizontal_pull": 4,
    "vertical_push":   5,
    "vertical_pull":   6,
    "carry":           7,
    "isolation":       8,
    "core":            9,
}

_PUSH_PATTERNS = {"horizontal_push", "vertical_push"}
_PULL_PATTERNS = {"horizontal_pull", "vertical_pull"}


def order_entries(entries: list[dict], exercises: dict[str, dict]) -> list[dict]:
    """
    Reorder plan entries for optimal session execution.

    Args:
        entries:   list of PlanEntry dicts (exercise_id, order, sets, superset_group, ...)
        exercises: dict mapping exercise_id → Exercise dict

    Returns:
        New list with `order` fields updated. Original dicts mutated in place.
    """
    if not entries:
        return entries

    # --- Separate superset groups from standalone entries ---
    superset_groups: dict[str, list[dict]] = {}
    standalone: list[dict] = []

    for entry in entries:
        group = entry.get("superset_group")
        if group:
            superset_groups.setdefault(group, []).append(entry)
        else:
            standalone.append(entry)

    # --- Sort standalone entries ---
    def _sort_key(entry: dict) -> tuple:
        ex = exercises.get(entry.get("exercise_id", ""), {})
        is_compound = ex.get("is_compound", False)
        pattern = ex.get("movement_pattern", "isolation")
        pattern_priority = _PATTERN_PRIORITY.get(pattern, 10)
        original_order = entry.get("order", 999)
        # Compounds first (0), then by pattern priority, then original order
        return (0 if is_compound else 1, pattern_priority, original_order)

    sorted_standalone = sorted(standalone, key=_sort_key)

    # --- Interleave push and pull compounds for better recovery ---
    push_compounds = [
        e for e in sorted_standalone
        if exercises.get(e.get("exercise_id", ""), {}).get("is_compound")
        and exercises.get(e.get("exercise_id", ""), {}).get("movement_pattern") in _PUSH_PATTERNS
    ]
    pull_compounds = [
        e for e in sorted_standalone
        if exercises.get(e.get("exercise_id", ""), {}).get("is_compound")
        and exercises.get(e.get("exercise_id", ""), {}).get("movement_pattern") in _PULL_PATTERNS
    ]
    other_compounds = [
        e for e in sorted_standalone
        if exercises.get(e.get("exercise_id", ""), {}).get("is_compound")
        and e not in push_compounds and e not in pull_compounds
    ]
    isolations = [
        e for e in sorted_standalone
        if not exercises.get(e.get("exercise_id", ""), {}).get("is_compound")
    ]

    # Interleave push and pull
    interleaved: list[dict] = []
    push_q, pull_q = list(push_compounds), list(pull_compounds)
    while push_q or pull_q:
        if push_q:
            interleaved.append(push_q.pop(0))
        if pull_q:
            interleaved.append(pull_q.pop(0))

    ordered_standalone = interleaved + other_compounds + isolations

    # --- Append superset groups after standalone ---
    superset_flat: list[dict] = []
    for group_key in sorted(superset_groups.keys()):
        group = superset_groups[group_key]
        # Sort within group by original order
        group.sort(key=lambda e: e.get("order", 999))
        superset_flat.extend(group)

    final: list[dict] = ordered_standalone + superset_flat

    # --- Update order field ---
    for i, entry in enumerate(final, start=1):
        entry["order"] = i

    return final
