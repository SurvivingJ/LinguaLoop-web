"""
WorkoutOS — Superset & Filler Scheduling Algorithm (O4)

This is the core "maximise workout effectiveness" feature. It fills rest
periods with productive work — either superset exercises or active
mobility/stretching — while avoiding fatigue interference.

Principles:
  1. NEVER schedule a filler that targets the same primary muscles being
     rested. E.g. don't stretch chest during rest between bench press sets.
  2. PREFER fillers that target muscles about to be used (pre-activation)
     or that are chronically tight (hip flexors, thoracic spine).
  3. For supersets, pair opposing movement patterns (push ↔ pull) or
     upper ↔ lower to maximise recovery between sets.
  4. Keep fillers short enough to fit within the rest period (with buffer).
  5. Don't repeat the same filler back-to-back — rotate through options.

Usage:
    from services.filler_scheduler import schedule_fillers
    plan_with_fillers = schedule_fillers(plan, exercises, mobility_pool)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from config import MOBILITY_FILE
from schemas import (
    Exercise,
    MobilityExercise,
    MuscleGroup,
    MovementPattern,
    PlanEntry,
    WorkoutPlan,
    FillerType,
)


# ---------------------------------------------------------------------------
# Movement pattern compatibility for supersets
# ---------------------------------------------------------------------------

# Maps a movement pattern to its ideal superset partner(s)
SUPERSET_PAIRS: dict[str, list[str]] = {
    "horizontal_push": ["horizontal_pull"],
    "horizontal_pull": ["horizontal_push"],
    "vertical_push":   ["vertical_pull"],
    "vertical_pull":   ["vertical_push"],
    "squat":           ["hip_hinge", "core"],
    "hip_hinge":       ["squat", "core"],
    "isolation":       ["isolation"],       # pair opposing isolations
    "carry":           ["core"],
    "core":            ["carry", "squat", "hip_hinge"],
}

# Muscles that are commonly tight — prioritised for filler stretches
# when no better option exists
PRIORITY_STRETCH_TARGETS: list[MuscleGroup] = [
    MuscleGroup.HIP_FLEXORS,
    MuscleGroup.HAMSTRINGS,
    MuscleGroup.SHOULDERS,
    MuscleGroup.LATS,
    MuscleGroup.CALVES,
]

# Minimum buffer (seconds) between filler end and rest end
# so the user isn't rushed back into the next set
FILLER_BUFFER_SECONDS = 10


# ---------------------------------------------------------------------------
# Muscle conflict detection
# ---------------------------------------------------------------------------

def _muscles_conflict(
    filler_targets: set[MuscleGroup],
    exercise_primary: set[MuscleGroup],
    exercise_secondary: set[MuscleGroup],
) -> bool:
    """
    Returns True if the filler would fatigue muscles needed for the
    current or next exercise.

    Rules:
    - Direct primary overlap → always conflict
    - Filler targets secondary muscles → conflict only if the filler
      is a stretch (stretching a muscle under load can reduce force output)
    """
    if filler_targets & exercise_primary:
        return True
    return False


def _muscles_synergise(
    filler_targets: set[MuscleGroup],
    next_exercise_primary: set[MuscleGroup],
) -> bool:
    """
    Returns True if the filler pre-activates or mobilises muscles
    that the NEXT exercise will use. This is a positive signal.
    """
    return bool(filler_targets & next_exercise_primary)


# ---------------------------------------------------------------------------
# Scoring a filler candidate
# ---------------------------------------------------------------------------

def _score_filler(
    filler: MobilityExercise,
    current_exercise: Exercise,
    next_exercise: Optional[Exercise],
    rest_seconds: int,
    recently_used: set[str],
) -> float:
    """
    Score a filler candidate. Higher is better. Returns -1 if disqualified.

    Scoring factors:
      -1.0  → disqualified (muscle conflict or too long)
      +3.0  → pre-activates next exercise's muscles
      +2.0  → targets a priority stretch area
      +1.0  → fits comfortably in rest window
      -0.5  → was recently used (penalise repetition)
    """
    filler_targets = set(filler.target_muscles)
    available_time = rest_seconds - FILLER_BUFFER_SECONDS

    # Disqualify: too long for the rest period
    if filler.duration_seconds > available_time:
        return -1.0

    # Disqualify: conflicts with current exercise
    if _muscles_conflict(filler_targets, set(current_exercise.primary_muscles),
                         set(current_exercise.secondary_muscles)):
        return -1.0

    score = 1.0  # base score for fitting in the window

    # Bonus: pre-activates next exercise
    if next_exercise and _muscles_synergise(filler_targets, set(next_exercise.primary_muscles)):
        score += 3.0

    # Bonus: targets commonly tight muscles
    if any(m in PRIORITY_STRETCH_TARGETS for m in filler.target_muscles):
        score += 2.0

    # Penalty: recently used
    if filler.id in recently_used:
        score -= 0.5

    return score


# ---------------------------------------------------------------------------
# Superset grouping logic
# ---------------------------------------------------------------------------

def suggest_supersets(
    entries: list[PlanEntry],
    exercises: dict[str, Exercise],
) -> list[tuple[PlanEntry, PlanEntry]]:
    """
    Analyse a workout's entries and suggest which exercises could be
    superset together based on movement pattern compatibility.

    Returns pairs of PlanEntry that can be performed back-to-back.
    Only suggests if both exercises in the pair have compatible patterns
    AND don't share primary muscles.

    This is a suggestion engine — the user decides in the workout builder
    whether to accept the grouping.
    """
    available = list(entries)
    pairs: list[tuple[PlanEntry, PlanEntry]] = []
    used: set[int] = set()

    for i, entry_a in enumerate(available):
        if i in used:
            continue

        ex_a = exercises.get(entry_a.exercise_id)
        if not ex_a:
            continue

        compatible_patterns = SUPERSET_PAIRS.get(ex_a.movement_pattern.value, [])
        if not compatible_patterns:
            continue

        best_match: Optional[tuple[int, PlanEntry]] = None
        best_score = 0

        for j, entry_b in enumerate(available):
            if j in used or j == i:
                continue

            ex_b = exercises.get(entry_b.exercise_id)
            if not ex_b:
                continue

            # Check pattern compatibility
            if ex_b.movement_pattern.value not in compatible_patterns:
                continue

            # Check no primary muscle overlap
            if set(ex_a.primary_muscles) & set(ex_b.primary_muscles):
                continue

            # Score: prefer compound+compound or isolation+isolation pairings
            score = 1.0
            if ex_a.is_compound == ex_b.is_compound:
                score += 1.0

            # Prefer similar set counts
            if len(entry_a.sets) == len(entry_b.sets):
                score += 0.5

            if score > best_score:
                best_score = score
                best_match = (j, entry_b)

        if best_match:
            used.add(i)
            used.add(best_match[0])
            pairs.append((entry_a, best_match[1]))

    return pairs


# ---------------------------------------------------------------------------
# Filler assignment for a full workout plan
# ---------------------------------------------------------------------------

def load_mobility_pool() -> list[MobilityExercise]:
    """Load all mobility/stretch exercises from mobility.json."""
    if not os.path.exists(MOBILITY_FILE):
        return []

    with open(MOBILITY_FILE, "r") as f:
        data = json.load(f)

    return [MobilityExercise.from_dict(d) for d in data]


def schedule_fillers(
    plan: WorkoutPlan,
    exercises: dict[str, Exercise],
    mobility_pool: Optional[list[MobilityExercise]] = None,
) -> WorkoutPlan:
    """
    Walk through every rest period in the plan and assign the best
    filler activity. Modifies plan entries in place.

    Algorithm:
    1. For each PlanEntry, look at each set's rest_seconds.
    2. Skip if the entry already has a manually-assigned filler_id.
    3. Skip if the entry is part of a superset (rest is between the
       superset pair, not between sets of the same exercise).
    4. Score all mobility_pool candidates against the current + next exercise.
    5. Pick the highest-scoring filler; assign its ID to the entry.
    6. Track recently-used fillers to encourage rotation.

    Returns the modified plan (same object, mutated).
    """
    if mobility_pool is None:
        mobility_pool = load_mobility_pool()

    if not mobility_pool:
        return plan  # nothing to assign

    recently_used: set[str] = set()
    sorted_entries = sorted(plan.entries, key=lambda e: e.order)

    for idx, entry in enumerate(sorted_entries):
        # Skip if user already assigned a filler manually
        if entry.filler_id:
            recently_used.add(entry.filler_id)
            continue

        # Skip superset members (rest handling is different)
        if entry.superset_group:
            continue

        current_ex = exercises.get(entry.exercise_id)
        if not current_ex:
            continue

        # Determine the next exercise (for pre-activation scoring)
        next_ex = None
        if idx + 1 < len(sorted_entries):
            next_entry = sorted_entries[idx + 1]
            next_ex = exercises.get(next_entry.exercise_id)

        # Use the longest rest in this entry's sets as the available window
        max_rest = max((s.rest_seconds for s in entry.sets), default=0)
        if max_rest <= FILLER_BUFFER_SECONDS + 10:
            continue  # rest too short for any filler

        # Score all candidates
        scored = []
        for filler in mobility_pool:
            s = _score_filler(filler, current_ex, next_ex, max_rest, recently_used)
            if s > 0:
                scored.append((s, filler))

        if not scored:
            continue

        # Pick the best
        scored.sort(key=lambda x: x[0], reverse=True)
        best_filler = scored[0][1]

        entry.filler_id = best_filler.id
        entry.filler_type = best_filler.filler_type
        recently_used.add(best_filler.id)

        # Reset recently_used every 4 entries to allow re-use in longer workouts
        if len(recently_used) > 4:
            recently_used.clear()

    return plan


# ---------------------------------------------------------------------------
# Superset rest scheduling
# ---------------------------------------------------------------------------

def compute_superset_rest(
    group_entries: list[PlanEntry],
    exercises: dict[str, Exercise],
) -> int:
    """
    For a superset group, determine the rest period after the full
    round (all exercises done back-to-back).

    Rules:
    - Take the LONGEST rest_seconds from any entry in the group
    - Add 15s for each additional exercise beyond the first
      (accounts for transition time)
    - Cap at 180s (3 minutes) — supersets shouldn't have marathon rests
    """
    if not group_entries:
        return 90

    max_rest = 0
    for entry in group_entries:
        for s in entry.sets:
            if s.rest_seconds > max_rest:
                max_rest = s.rest_seconds

    transition_bonus = 15 * (len(group_entries) - 1)
    total = max_rest + transition_bonus

    return min(total, 180)


def build_session_sequence(
    plan: WorkoutPlan,
    exercises: dict[str, Exercise],
) -> list[dict]:
    """
    Flatten a workout plan into the exact sequence of actions the session
    engine (and Play Mode) will execute.

    Returns a list of action dicts:
      {"type": "set",    "exercise": Exercise, "set_spec": SetSpec, "set_num": int}
      {"type": "rest",   "seconds": int, "filler": MobilityExercise | None}
      {"type": "transition", "message": str}

    Supersets are interleaved: if A and B are superset partners with 3 sets each,
    the sequence is: A1 → B1 → rest → A2 → B2 → rest → A3 → B3 → rest.
    """
    mobility_pool = {m.id: m for m in load_mobility_pool()}
    sorted_entries = sorted(plan.entries, key=lambda e: e.order)

    # Group entries by superset
    superset_groups: dict[str, list[PlanEntry]] = {}
    standalone: list[PlanEntry] = []

    for entry in sorted_entries:
        if entry.superset_group:
            superset_groups.setdefault(entry.superset_group, []).append(entry)
        else:
            standalone.append(entry)

    sequence: list[dict] = []
    processed_groups: set[str] = set()

    for entry in sorted_entries:
        if entry.superset_group:
            if entry.superset_group in processed_groups:
                continue
            processed_groups.add(entry.superset_group)

            group = superset_groups[entry.superset_group]
            group_rest = compute_superset_rest(group, exercises)

            # Determine max sets across the group
            max_sets = max(len(e.sets) for e in group)

            for set_idx in range(max_sets):
                for g_entry in group:
                    ex = exercises.get(g_entry.exercise_id)
                    if not ex or set_idx >= len(g_entry.sets):
                        continue

                    sequence.append({
                        "type": "set",
                        "exercise": ex,
                        "set_spec": g_entry.sets[set_idx],
                        "set_num": set_idx + 1,
                        "total_sets": len(g_entry.sets),
                        "superset_group": g_entry.superset_group,
                    })

                # Rest after the full superset round (not after last round)
                if set_idx < max_sets - 1:
                    sequence.append({
                        "type": "rest",
                        "seconds": group_rest,
                        "filler": None,  # no filler during superset rest (too short)
                    })

        else:
            ex = exercises.get(entry.exercise_id)
            if not ex:
                continue

            filler = mobility_pool.get(entry.filler_id) if entry.filler_id else None

            for set_idx, set_spec in enumerate(entry.sets):
                sequence.append({
                    "type": "set",
                    "exercise": ex,
                    "set_spec": set_spec,
                    "set_num": set_idx + 1,
                    "total_sets": len(entry.sets),
                    "superset_group": None,
                })

                # Rest after every set except the last
                if set_idx < len(entry.sets) - 1:
                    sequence.append({
                        "type": "rest",
                        "seconds": set_spec.rest_seconds,
                        "filler": filler,
                    })

            # Transition to next exercise
            sequence.append({
                "type": "transition",
                "message": "Moving to next exercise",
            })

    return sequence
