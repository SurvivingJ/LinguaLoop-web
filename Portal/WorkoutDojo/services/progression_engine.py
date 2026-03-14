"""
WorkoutOS — Progression Engine (O3)

Analyses exercise history to suggest weight/rep changes for the next session.
Core responsibilities:
  1. Estimate current 1RM from recent sets
  2. Determine strength level (beginner/intermediate/advanced)
  3. Detect RPE drift (fatigue accumulation → suggest deload)
  4. Suggest next-session weight using the increment table
  5. Apply deload modifiers when the session falls in a deload week
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from typing import Optional

from config import (
    WEIGHT_INCREMENTS,
    STRENGTH_LEVELS,
    SETS_LOG_FILE,
    BODY_WEIGHT_FILE,
    RPE_DRIFT_WINDOW,
    RPE_DRIFT_THRESHOLD,
    MIN_SESSIONS_FOR_PROGRESSION,
    ESTIMATED_1RM_FORMULA,
)
from schemas import Exercise, ProgressionAggression


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SetRecord:
    """A single logged set from sets_log.csv."""
    session_id: str
    exercise_id: str
    set_number: int
    reps: int
    weight_kg: float
    rpe: Optional[float]
    is_warmup: bool
    timestamp: str


@dataclass
class ProgressionSuggestion:
    """Returned to the UI for the 'next session' recommendation."""
    exercise_id: str
    current_weight_kg: float
    suggested_weight_kg: float
    increment_kg: float
    reason: str                        # human-readable explanation
    alternatives: list[float]          # other increment options for UI buttons
    estimated_1rm: Optional[float]
    strength_level: str
    rpe_drift_warning: bool


# ---------------------------------------------------------------------------
# 1RM estimation
# ---------------------------------------------------------------------------

def estimate_1rm(weight_kg: float, reps: int, formula: str = ESTIMATED_1RM_FORMULA) -> float:
    """
    Estimate one-rep max from a set.

    Epley:   1RM = w × (1 + r/30)
    Brzycki: 1RM = w × 36 / (37 − r)

    Returns 0 for bodyweight (weight_kg == 0) or single-rep sets where
    the actual weight IS the 1RM.
    """
    if weight_kg <= 0 or reps <= 0:
        return 0.0
    if reps == 1:
        return weight_kg

    if formula == "brzycki":
        if reps >= 37:
            return weight_kg  # formula breaks down at high reps
        return weight_kg * 36.0 / (37.0 - reps)
    else:  # epley (default)
        return weight_kg * (1.0 + reps / 30.0)


# ---------------------------------------------------------------------------
# History loading
# ---------------------------------------------------------------------------

def load_exercise_history(exercise_id: str) -> list[SetRecord]:
    """Load all logged sets for an exercise, sorted by timestamp."""
    if not os.path.exists(SETS_LOG_FILE):
        return []

    records: list[SetRecord] = []
    with open(SETS_LOG_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("exercise_id") == exercise_id:
                records.append(SetRecord(
                    session_id=row["session_id"],
                    exercise_id=row["exercise_id"],
                    set_number=int(row.get("set_number", 0)),
                    reps=int(row.get("reps", 0)),
                    weight_kg=float(row.get("weight_kg", 0)),
                    rpe=float(row["rpe"]) if row.get("rpe") else None,
                    is_warmup=row.get("is_warmup", "false").lower() == "true",
                    timestamp=row.get("timestamp", ""),
                ))
    return sorted(records, key=lambda r: r.timestamp)


def load_latest_body_weight() -> Optional[float]:
    """Return the most recent body weight entry, or None."""
    if not os.path.exists(BODY_WEIGHT_FILE):
        return None

    last_weight = None
    with open(BODY_WEIGHT_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                last_weight = float(row["weight_kg"].strip())
            except (ValueError, KeyError):
                continue
    return last_weight


# ---------------------------------------------------------------------------
# Strength level determination
# ---------------------------------------------------------------------------

def determine_strength_level(
    exercise: Exercise,
    estimated_1rm: float,
    body_weight_kg: Optional[float],
) -> str:
    """
    Classify the user's strength level for this exercise.

    Uses body-weight ratios for barbell compounds (from STRENGTH_LEVELS).
    For other categories, returns "any" (increments don't vary by level).
    """
    # Non-barbell categories use "any" level
    if exercise.category.value not in ("barbell_compound", "barbell_isolation"):
        return "any"

    if not body_weight_kg or body_weight_kg <= 0 or estimated_1rm <= 0:
        return "beginner"

    ratio = estimated_1rm / body_weight_kg
    pattern = exercise.movement_pattern.value

    thresholds = STRENGTH_LEVELS.get(pattern)
    if not thresholds:
        return "beginner"

    # Walk from highest to lowest
    if ratio >= thresholds.get("advanced", 999):
        return "advanced"
    elif ratio >= thresholds.get("intermediate", 999):
        return "intermediate"
    else:
        return "beginner"


# ---------------------------------------------------------------------------
# RPE drift detection
# ---------------------------------------------------------------------------

def detect_rpe_drift(sets: list[SetRecord]) -> tuple[bool, float]:
    """
    Check if average RPE is trending upward over recent sessions,
    which indicates accumulated fatigue and a potential need to deload.

    Returns (is_drifting, avg_rpe_change).
    """
    # Group working sets by session
    sessions: dict[str, list[float]] = {}
    for s in sets:
        if s.is_warmup or s.rpe is None:
            continue
        sessions.setdefault(s.session_id, []).append(s.rpe)

    if len(sessions) < RPE_DRIFT_WINDOW:
        return False, 0.0

    # Get per-session average RPE, ordered by first timestamp in each session
    session_order = []
    for sid, rpes in sessions.items():
        first_ts = min(s.timestamp for s in sets if s.session_id == sid)
        session_order.append((first_ts, sum(rpes) / len(rpes)))

    session_order.sort(key=lambda x: x[0])

    # Compare the last N sessions to the ones before
    recent = session_order[-RPE_DRIFT_WINDOW:]
    recent_avg = sum(r[1] for r in recent) / len(recent)

    if len(session_order) > RPE_DRIFT_WINDOW:
        earlier = session_order[-RPE_DRIFT_WINDOW * 2:-RPE_DRIFT_WINDOW]
        if earlier:
            earlier_avg = sum(r[1] for r in earlier) / len(earlier)
            drift = recent_avg - earlier_avg
            return drift >= RPE_DRIFT_THRESHOLD, drift

    # Not enough earlier data — just check if recent RPE is very high
    return recent_avg >= 9.0, 0.0


# ---------------------------------------------------------------------------
# Increment lookup
# ---------------------------------------------------------------------------

def get_increment(
    category: str,
    strength_level: str,
    aggression: ProgressionAggression,
) -> Optional[float]:
    """
    Look up the weight increment for a given category, level, and aggression.

    Returns None for bodyweight exercises (rep-based progression only).
    """
    # Try exact match first, then fall back to "any" level
    key = (category, strength_level)
    increments = WEIGHT_INCREMENTS.get(key)
    if not increments:
        key = (category, "any")
        increments = WEIGHT_INCREMENTS.get(key)

    if not increments:
        return None

    idx = {"conservative": 0, "standard": 1, "aggressive": 2}.get(aggression.value, 1)
    return increments[idx]


# ---------------------------------------------------------------------------
# Core suggestion logic
# ---------------------------------------------------------------------------

def suggest_progression(exercise: Exercise, starting_weight_kg: float | None = None) -> ProgressionSuggestion:
    """
    Analyse an exercise's history and produce a weight suggestion for the
    next session.

    Algorithm:
    1. Load all working sets for this exercise.
    2. Find the best estimated 1RM from the most recent session.
    3. Determine strength level from 1RM and body weight.
    4. Check RPE drift over the last N sessions.
    5. If drifting → suggest same weight or slight decrease.
       If stable  → suggest current weight + increment.
       If too few sessions → suggest same weight (gather more data).
    6. Return suggestion with alternatives for UI buttons.
    """
    history = load_exercise_history(exercise.id)
    working_sets = [s for s in history if not s.is_warmup and s.weight_kg > 0]

    if not working_sets:
        if starting_weight_kg and starting_weight_kg > 0:
            return ProgressionSuggestion(
                exercise_id=exercise.id,
                current_weight_kg=0,
                suggested_weight_kg=starting_weight_kg,
                increment_kg=0,
                reason=f"No history yet — starting at {starting_weight_kg} kg",
                alternatives=[],
                estimated_1rm=None,
                strength_level="beginner",
                rpe_drift_warning=False,
            )
        return ProgressionSuggestion(
            exercise_id=exercise.id,
            current_weight_kg=0,
            suggested_weight_kg=0,
            increment_kg=0,
            reason="No history yet — start with a comfortable weight",
            alternatives=[],
            estimated_1rm=None,
            strength_level="beginner",
            rpe_drift_warning=False,
        )

    # --- Most recent session's best set ---
    latest_session_id = working_sets[-1].session_id
    latest_sets = [s for s in working_sets if s.session_id == latest_session_id]
    current_weight = max(s.weight_kg for s in latest_sets)

    # Best estimated 1RM from latest session
    best_1rm = max(estimate_1rm(s.weight_kg, s.reps) for s in latest_sets)

    # --- Strength level ---
    body_weight = load_latest_body_weight()
    strength_level = determine_strength_level(exercise, best_1rm, body_weight)

    # --- RPE drift ---
    is_drifting, drift_amount = detect_rpe_drift(history)

    # --- Session count for this exercise ---
    unique_sessions = len(set(s.session_id for s in working_sets))

    # --- Increment ---
    increment = get_increment(
        exercise.category.value,
        strength_level,
        exercise.progression_aggression,
    )

    # --- Decision logic ---
    if not getattr(exercise, 'uses_weights', True) or increment is None:
        # Bodyweight exercise — suggest rep increase
        best_reps = max(s.reps for s in latest_sets)
        return ProgressionSuggestion(
            exercise_id=exercise.id,
            current_weight_kg=0,
            suggested_weight_kg=0,
            increment_kg=0,
            reason=f"Bodyweight exercise — aim for {best_reps + 1}+ reps next session",
            alternatives=[],
            estimated_1rm=best_1rm if best_1rm > 0 else None,
            strength_level=strength_level,
            rpe_drift_warning=is_drifting,
        )

    if is_drifting:
        return ProgressionSuggestion(
            exercise_id=exercise.id,
            current_weight_kg=current_weight,
            suggested_weight_kg=current_weight,
            increment_kg=0,
            reason=f"RPE trending up — hold weight at {current_weight} kg or consider a deload",
            alternatives=[current_weight - increment, current_weight],
            estimated_1rm=best_1rm,
            strength_level=strength_level,
            rpe_drift_warning=True,
        )

    if unique_sessions < MIN_SESSIONS_FOR_PROGRESSION:
        return ProgressionSuggestion(
            exercise_id=exercise.id,
            current_weight_kg=current_weight,
            suggested_weight_kg=current_weight,
            increment_kg=0,
            reason=f"Only {unique_sessions} session(s) logged — repeat {current_weight} kg to establish baseline",
            alternatives=[],
            estimated_1rm=best_1rm,
            strength_level=strength_level,
            rpe_drift_warning=False,
        )

    # --- Check if last session hit target reps ---
    # If the user hit the top of their rep range on all working sets, progress
    avg_rpe = None
    rpe_sets = [s for s in latest_sets if s.rpe is not None]
    if rpe_sets:
        avg_rpe = sum(s.rpe for s in rpe_sets) / len(rpe_sets)

    # If average RPE < 8, confidently suggest increase
    # If RPE 8-9, suggest standard increase
    # If RPE >= 9.5, hold weight
    if avg_rpe is not None and avg_rpe >= 9.5:
        return ProgressionSuggestion(
            exercise_id=exercise.id,
            current_weight_kg=current_weight,
            suggested_weight_kg=current_weight,
            increment_kg=0,
            reason=f"Last session RPE was {avg_rpe:.1f} — repeat {current_weight} kg",
            alternatives=[current_weight + increment],
            estimated_1rm=best_1rm,
            strength_level=strength_level,
            rpe_drift_warning=False,
        )

    suggested = current_weight + increment

    # Build alternative options
    all_increments = _get_all_increments(exercise.category.value, strength_level)
    alternatives = sorted(set(
        current_weight + inc for inc in all_increments
        if inc is not None and current_weight + inc != suggested
    ))

    return ProgressionSuggestion(
        exercise_id=exercise.id,
        current_weight_kg=current_weight,
        suggested_weight_kg=suggested,
        increment_kg=increment,
        reason=f"Good progress — try {suggested} kg (+{increment} kg)",
        alternatives=alternatives,
        estimated_1rm=best_1rm,
        strength_level=strength_level,
        rpe_drift_warning=False,
    )


def _get_all_increments(category: str, strength_level: str) -> list[Optional[float]]:
    """Get all three aggression levels for the UI alternative buttons."""
    key = (category, strength_level)
    increments = WEIGHT_INCREMENTS.get(key)
    if not increments:
        key = (category, "any")
        increments = WEIGHT_INCREMENTS.get(key)
    return increments or []


# ---------------------------------------------------------------------------
# Deload modifier
# ---------------------------------------------------------------------------

def apply_deload(sets: list[dict], deload_volume_pct: int) -> list[dict]:
    """
    Reduce the number of working sets by the deload percentage.

    Applied at session load time — the underlying plan is NOT modified.
    Warm-up sets are preserved; working sets are reduced.

    Example: 4 working sets with 40% deload → ceil(4 × 0.6) = 3 sets kept.
    """
    warmup = [s for s in sets if s.get("is_warmup", False)]
    working = [s for s in sets if not s.get("is_warmup", False)]

    keep_count = math.ceil(len(working) * (1 - deload_volume_pct / 100))
    keep_count = max(1, keep_count)  # always keep at least 1 working set

    return warmup + working[:keep_count]


# ---------------------------------------------------------------------------
# Per-set weight computation
# ---------------------------------------------------------------------------

_ROUND_INCREMENTS = {
    "barbell_compound": 2.5,
    "barbell_isolation": 2.5,
    "dumbbell": 2.0,
    "cable": 2.5,
    "machine": 2.5,
}

DEFAULT_WARMUP_RAMP = [0.5, 0.75]


@dataclass
class SetWeightPlan:
    """Per-set weight recommendations for a single exercise entry."""
    exercise_id: str
    set_weights: list[float]   # one weight per set, in order
    labels: list[str]          # e.g. ["Warmup 50%", "Warmup 75%", "Working", ...]


def round_to_increment(weight_kg: float, category: str) -> float:
    """Round a weight to the nearest valid plate loading for the category."""
    inc = _ROUND_INCREMENTS.get(category, 2.5)
    if inc <= 0:
        return weight_kg
    return round(weight_kg / inc) * inc


def compute_set_weights(
    suggestion: ProgressionSuggestion,
    sets: list[dict],
    category: str = "barbell_compound",
    warmup_ramp: list[float] | None = None,
) -> SetWeightPlan:
    """
    Given a ProgressionSuggestion and the exercise's sets list,
    compute a weight for each set.

    Warmup sets get ramped percentages of the working weight.
    Working sets get the full suggested weight.
    """
    ramp = warmup_ramp or DEFAULT_WARMUP_RAMP
    working_weight = suggestion.suggested_weight_kg

    weights: list[float] = []
    labels: list[str] = []

    warmup_idx = 0
    for s in sets:
        is_warmup = s.get("is_warmup", False)
        if is_warmup and working_weight > 0:
            pct = ramp[min(warmup_idx, len(ramp) - 1)]
            w = round_to_increment(working_weight * pct, category)
            w = max(0, w)
            weights.append(w)
            labels.append(f"Warmup {int(pct * 100)}%")
            warmup_idx += 1
        else:
            weights.append(working_weight)
            labels.append("Working")

    return SetWeightPlan(
        exercise_id=suggestion.exercise_id,
        set_weights=weights,
        labels=labels,
    )
