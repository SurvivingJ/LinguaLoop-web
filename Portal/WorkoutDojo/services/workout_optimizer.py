"""
WorkoutOS — Smart Workout Optimizer

Reorders exercises and optionally auto-generates superset pairings for
optimal muscle recovery, time efficiency, and training effectiveness.

Rules (priority order):
1. Respect user-defined superset groups (never break them)
2. Respect optimizer_locked entries (don't move them)
3. Compounds before isolations
4. Avoid consecutive same-muscle exercises
5. Auto-pair antagonist exercises as supersets (when enabled)
"""

from __future__ import annotations

from schemas import Exercise, PlanEntry, WorkoutPlan

# Antagonist muscle pairs for superset pairing
ANTAGONIST_PAIRS: dict[str, list[str]] = {
    "chest":      ["back", "lats"],
    "back":       ["chest"],
    "lats":       ["chest"],
    "biceps":     ["triceps"],
    "triceps":    ["biceps"],
    "quads":      ["hamstrings", "glutes"],
    "hamstrings": ["quads"],
    "glutes":     ["quads"],
    "shoulders":  ["lats"],
}

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


def optimize_workout(
    plan: WorkoutPlan,
    exercises: dict[str, Exercise],
    auto_superset: bool = False,
) -> WorkoutPlan:
    """
    Reorder exercises for optimal session execution and optionally
    auto-pair antagonist exercises as supersets.
    """
    if not plan.entries:
        return plan

    # Step 1: Partition entries
    user_supersets: dict[str, list[PlanEntry]] = {}
    locked: list[tuple[int, PlanEntry]] = []
    free: list[PlanEntry] = []

    for entry in plan.entries:
        if entry.superset_group:
            user_supersets.setdefault(entry.superset_group, []).append(entry)
        elif entry.optimizer_locked:
            locked.append((entry.order, entry))
        else:
            free.append(entry)

    # Step 2: Classify free entries
    compounds = [e for e in free if exercises.get(e.exercise_id) and exercises[e.exercise_id].is_compound]
    isolations = [e for e in free if exercises.get(e.exercise_id) and not exercises[e.exercise_id].is_compound]

    def _pattern_sort(entry: PlanEntry) -> int:
        ex = exercises.get(entry.exercise_id)
        if not ex:
            return 99
        return _PATTERN_PRIORITY.get(ex.movement_pattern.value, 10)

    compounds.sort(key=_pattern_sort)
    isolations.sort(key=_pattern_sort)

    # Step 3: Greedy muscle-separation ordering
    ordered_compounds = _greedy_muscle_separation(compounds, exercises)
    ordered_isolations = _greedy_muscle_separation(isolations, exercises)
    all_ordered = ordered_compounds + ordered_isolations

    # Step 4: Auto-superset pairing (if enabled)
    if auto_superset:
        all_ordered = _auto_pair_supersets(all_ordered, exercises)

    # Step 5: Reassemble
    final = _reassemble(all_ordered, user_supersets, locked)

    for i, entry in enumerate(final, start=1):
        entry.order = i

    plan.entries = final
    return plan


def _greedy_muscle_separation(
    entries: list[PlanEntry],
    exercises: dict[str, Exercise],
) -> list[PlanEntry]:
    """Pick next exercise with least primary muscle overlap with previous."""
    if len(entries) <= 1:
        return list(entries)

    remaining = list(entries)
    ordered = [remaining.pop(0)]

    while remaining:
        last_ex = exercises.get(ordered[-1].exercise_id)
        last_muscles = set(m.value for m in last_ex.primary_muscles) if last_ex else set()

        best_idx = 0
        best_score = float('inf')

        for i, candidate in enumerate(remaining):
            cand_ex = exercises.get(candidate.exercise_id)
            if not cand_ex:
                continue

            cand_muscles = set(m.value for m in cand_ex.primary_muscles)
            overlap = len(last_muscles & cand_muscles)
            secondary_overlap = len(last_muscles & set(m.value for m in cand_ex.secondary_muscles)) * 0.5
            score = overlap + secondary_overlap

            if score < best_score:
                best_score = score
                best_idx = i

        ordered.append(remaining.pop(best_idx))

    return ordered


def _auto_pair_supersets(
    entries: list[PlanEntry],
    exercises: dict[str, Exercise],
) -> list[PlanEntry]:
    """Find antagonist pairs and assign superset groups."""
    paired: set[int] = set()
    group_counter = ord('A')

    for i in range(len(entries)):
        if i in paired or entries[i].superset_group:
            continue

        ex_a = exercises.get(entries[i].exercise_id)
        if not ex_a:
            continue

        a_primary = set(m.value for m in ex_a.primary_muscles)

        for j in range(i + 1, len(entries)):
            if j in paired or entries[j].superset_group:
                continue

            ex_b = exercises.get(entries[j].exercise_id)
            if not ex_b:
                continue

            b_primary = set(m.value for m in ex_b.primary_muscles)

            # No primary muscle overlap
            if a_primary & b_primary:
                continue

            # Check antagonist relationship
            is_antagonist = any(
                target in b_primary
                for muscle in a_primary
                for target in ANTAGONIST_PAIRS.get(muscle, [])
            )
            if not is_antagonist:
                continue

            # Similar set count (within 1)
            if abs(len(entries[i].sets) - len(entries[j].sets)) > 1:
                continue

            # Pair them
            group_label = chr(group_counter)
            group_counter += 1
            if group_counter > ord('Z'):
                group_counter = ord('A')

            entries[i].superset_group = group_label
            entries[j].superset_group = group_label
            entries[i].notes = _append_note(entries[i].notes, "[Auto-superset]")
            entries[j].notes = _append_note(entries[j].notes, "[Auto-superset]")
            paired.add(i)
            paired.add(j)
            break

    # Reorder so paired entries are adjacent
    result: list[PlanEntry] = []
    added: set[int] = set()

    for i, entry in enumerate(entries):
        if i in added:
            continue
        result.append(entry)
        added.add(i)

        if entry.superset_group and i in paired:
            for j in range(i + 1, len(entries)):
                if j not in added and entries[j].superset_group == entry.superset_group:
                    result.append(entries[j])
                    added.add(j)
                    break

    return result


def _reassemble(
    ordered_free: list[PlanEntry],
    user_supersets: dict[str, list[PlanEntry]],
    locked: list[tuple[int, PlanEntry]],
) -> list[PlanEntry]:
    """
    Assemble final order:
    1. Ordered free entries (compounds + isolations, with auto-supersets)
    2. User-defined superset groups appended
    3. Locked entries inserted at their original positions
    """
    result = list(ordered_free)

    for group_key in sorted(user_supersets.keys()):
        group_entries = user_supersets[group_key]
        group_entries.sort(key=lambda e: e.order)
        result.extend(group_entries)

    locked.sort(key=lambda x: x[0])
    for orig_order, entry in locked:
        insert_idx = min(orig_order - 1, len(result))
        insert_idx = max(0, insert_idx)
        result.insert(insert_idx, entry)

    return result


def _append_note(existing: str, tag: str) -> str:
    if tag in existing:
        return existing
    return (existing + " " + tag).strip() if existing else tag
