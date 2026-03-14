"""
WorkoutOS — Canonical Schemas (O1 + O2)

This module defines the authoritative data shapes for exercises, workout plans,
and all related sub-structures.  Every service that reads or writes JSON/CSV
data MUST go through these schemas for validation.

Usage:
    from schemas import ExerciseSchema, WorkoutPlanSchema
    exercise = ExerciseSchema.validate(raw_dict)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# O1 — Exercise Schema & Category Taxonomy
# ---------------------------------------------------------------------------

class ExerciseCategory(str, Enum):
    """
    Categories are aligned 1-to-1 with the WEIGHT_INCREMENTS keys in config.py.
    The progression engine uses the category to look up the correct increment.
    """
    BARBELL_COMPOUND  = "barbell_compound"   # squat, bench, deadlift, OHP, row
    BARBELL_ISOLATION = "barbell_isolation"   # curl, skullcrusher, upright row
    DUMBBELL          = "dumbbell"            # any dumbbell movement
    CABLE             = "cable"               # cable fly, tricep pushdown
    MACHINE           = "machine"             # leg press, chest press machine
    BODYWEIGHT        = "bodyweight"          # pull-up, dip, push-up
    STRETCHING        = "stretching"         # static/dynamic stretches
    MOBILITY          = "mobility"           # mobility drills, joint circles


class MuscleGroup(str, Enum):
    """Primary and secondary muscle tagging for ordering & filler selection."""
    CHEST       = "chest"
    BACK        = "back"
    SHOULDERS   = "shoulders"
    BICEPS      = "biceps"
    TRICEPS     = "triceps"
    FOREARMS    = "forearms"
    QUADS       = "quads"
    HAMSTRINGS  = "hamstrings"
    GLUTES      = "glutes"
    CALVES      = "calves"
    ABS         = "abs"
    TRAPS       = "traps"
    LATS        = "lats"
    HIP_FLEXORS = "hip_flexors"
    ADDUCTORS   = "adductors"


class MovementPattern(str, Enum):
    """Used by the ordering algorithm to separate push/pull/hinge/squat."""
    HORIZONTAL_PUSH = "horizontal_push"
    HORIZONTAL_PULL = "horizontal_pull"
    VERTICAL_PUSH   = "vertical_push"
    VERTICAL_PULL   = "vertical_pull"
    HIP_HINGE       = "hip_hinge"
    SQUAT           = "squat"
    ISOLATION       = "isolation"
    CARRY           = "carry"
    CORE            = "core"


class ProgressionAggression(str, Enum):
    CONSERVATIVE = "conservative"
    STANDARD     = "standard"
    AGGRESSIVE   = "aggressive"


class FillerType(str, Enum):
    """What kind of activity can fill rest periods."""
    MOBILITY  = "mobility"
    STRETCH   = "stretch"
    NONE      = "none"


@dataclass
class Exercise:
    """
    Full exercise definition stored in exercises.json.

    Design decisions:
    - `primary_muscles` and `secondary_muscles` are lists so the ordering
      algorithm and filler scheduler can reason about muscle overlap.
    - `movement_pattern` lets the ordering algorithm alternate push/pull.
    - `progression_aggression` defaults to STANDARD; overrideable per-exercise.
    - `voice_name` is an optional pronunciation hint for Web Speech API
      (e.g. "D B Row" instead of "Dumbbell Row" for brevity).
    - `is_compound` is derived from category but stored explicitly so the
      ordering algorithm can sort compounds-first without re-deriving.
    """
    name: str
    category: ExerciseCategory
    primary_muscles: list[MuscleGroup]
    movement_pattern: MovementPattern
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    secondary_muscles: list[MuscleGroup] = field(default_factory=list)
    equipment: str = ""                          # free-text: "barbell", "EZ bar", "lat pulldown"
    progression_aggression: ProgressionAggression = ProgressionAggression.STANDARD
    is_compound: bool = True
    voice_name: Optional[str] = None             # speech override
    notes: str = ""
    uses_weights: bool = True                    # False for bodyweight, stretching, mobility
    is_timed: bool = False                       # True for planks, wall sits, farmer's walks
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        # Derive is_compound from category if not explicitly set
        self.is_compound = self.category in (
            ExerciseCategory.BARBELL_COMPOUND,
        )

    def display_name(self) -> str:
        return self.voice_name or self.name

    def all_muscles(self) -> set[MuscleGroup]:
        return set(self.primary_muscles) | set(self.secondary_muscles)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["primary_muscles"] = [m.value for m in self.primary_muscles]
        d["secondary_muscles"] = [m.value for m in self.secondary_muscles]
        d["movement_pattern"] = self.movement_pattern.value
        d["progression_aggression"] = self.progression_aggression.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Exercise":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d["name"],
            category=ExerciseCategory(d["category"]),
            primary_muscles=[MuscleGroup(m) for m in d["primary_muscles"]],
            secondary_muscles=[MuscleGroup(m) for m in d.get("secondary_muscles", [])],
            movement_pattern=MovementPattern(d["movement_pattern"]),
            equipment=d.get("equipment", ""),
            progression_aggression=ProgressionAggression(d.get("progression_aggression", "standard")),
            is_compound=d.get("is_compound", True),
            voice_name=d.get("voice_name"),
            notes=d.get("notes", ""),
            uses_weights=d.get("uses_weights", True),
            is_timed=d.get("is_timed", False),
            created_at=d.get("created_at", datetime.now().isoformat()),
        )


# ---------------------------------------------------------------------------
# Mobility / Filler Exercise (lightweight, used during rest)
# ---------------------------------------------------------------------------

@dataclass
class MobilityExercise:
    """
    Stored in mobility.json.  Lighter schema — no progression needed.
    Tagged with target muscles so the filler scheduler knows which ones
    are appropriate during a given rest period.
    """
    name: str
    target_muscles: list[MuscleGroup]
    filler_type: FillerType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    duration_seconds: int = 30          # how long the filler takes
    instructions: str = ""              # short cue shown during rest
    voice_name: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["target_muscles"] = [m.value for m in self.target_muscles]
        d["filler_type"] = self.filler_type.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MobilityExercise":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d["name"],
            target_muscles=[MuscleGroup(m) for m in d["target_muscles"]],
            filler_type=FillerType(d.get("filler_type", "mobility")),
            duration_seconds=d.get("duration_seconds", 30),
            instructions=d.get("instructions", ""),
            voice_name=d.get("voice_name"),
        )


# ---------------------------------------------------------------------------
# O2 — Workout Plan Schema
# ---------------------------------------------------------------------------

@dataclass
class SetSpec:
    """
    A single set prescription within a plan entry.

    Design decisions:
    - `rest_seconds` is per-SET, not per-exercise, because rest may differ
      between warm-up sets and working sets.
    - `is_warmup` lets the progression engine skip warm-up sets when
      computing volume and suggesting weight changes.
    """
    rep_min: int = 0                      # e.g. 8  (0 when timed)
    rep_max: int = 0                      # e.g. 10  (same as min for fixed-rep, 0 when timed)
    rest_seconds: int = 90               # rest AFTER this set
    is_warmup: bool = False
    target_rpe: Optional[float] = None   # e.g. 8.0  (None = no RPE target)
    duration_seconds: Optional[int] = None  # for timed exercises (planks, wall sits)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SetSpec":
        return cls(
            rep_min=d.get("rep_min", 0),
            rep_max=d.get("rep_max", 0),
            rest_seconds=d.get("rest_seconds", 90),
            is_warmup=d.get("is_warmup", False),
            target_rpe=d.get("target_rpe"),
            duration_seconds=d.get("duration_seconds"),
        )


@dataclass
class PlanEntry:
    """
    One exercise slot in a workout plan.

    Design decisions:
    - `exercise_id` references an Exercise in exercises.json.
    - `order` is the display/execution position (1-based).
    - `superset_group` — entries sharing the same non-null group string
      are performed back-to-back with no rest between them; rest is taken
      only after the last exercise in the superset.
    - `filler_id` optionally references a MobilityExercise to perform
      during rest periods. If null, the filler scheduler assigns one
      automatically based on muscle compatibility.
    - `sets` is a list of SetSpec allowing per-set customisation
      (e.g. 2 warm-up sets + 3 working sets with different rest times).
    """
    exercise_id: str
    order: int
    sets: list[SetSpec]
    superset_group: Optional[str] = None    # e.g. "A", "B" or null
    filler_id: Optional[str] = None         # mobility exercise to show during rest
    filler_type: FillerType = FillerType.NONE
    notes: str = ""
    starting_weight_kg: Optional[float] = None  # optional initial weight for progression
    optimizer_locked: bool = False               # if True, optimizer won't reorder this entry

    def working_sets(self) -> list[SetSpec]:
        return [s for s in self.sets if not s.is_warmup]

    def total_sets(self) -> int:
        return len(self.sets)

    def to_dict(self) -> dict:
        return {
            "exercise_id": self.exercise_id,
            "order": self.order,
            "sets": [s.to_dict() for s in self.sets],
            "superset_group": self.superset_group,
            "filler_id": self.filler_id,
            "filler_type": self.filler_type.value,
            "notes": self.notes,
            "starting_weight_kg": self.starting_weight_kg,
            "optimizer_locked": self.optimizer_locked,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlanEntry":
        return cls(
            exercise_id=d["exercise_id"],
            order=d["order"],
            sets=[SetSpec.from_dict(s) for s in d["sets"]],
            superset_group=d.get("superset_group"),
            filler_id=d.get("filler_id"),
            filler_type=FillerType(d.get("filler_type", "none")),
            notes=d.get("notes", ""),
            starting_weight_kg=d.get("starting_weight_kg"),
            optimizer_locked=d.get("optimizer_locked", False),
        )


@dataclass
class WorkoutPlan:
    """
    A complete workout plan stored in plans.json.

    Design decisions:
    - `entries` is ordered by `PlanEntry.order`.
    - `estimated_duration_minutes` is computed from sets × rest times +
      estimated work time (≈30s per set).  Shown on list pages.
    - Supersets are expressed via `superset_group` on entries — the session
      engine groups them at runtime and adjusts rest accordingly.
    """
    name: str
    entries: list[PlanEntry]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    target_muscles: list[MuscleGroup] = field(default_factory=list)
    estimated_duration_minutes: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def compute_duration(self) -> int:
        """Estimate workout duration in minutes."""
        total_seconds = 0
        for entry in self.entries:
            for s in entry.sets:
                total_seconds += 30 + s.rest_seconds  # ~30s work + rest
        return max(1, total_seconds // 60)

    def superset_groups(self) -> dict[str, list[PlanEntry]]:
        """Return entries grouped by superset_group (excluding None)."""
        groups: dict[str, list[PlanEntry]] = {}
        for e in self.entries:
            if e.superset_group:
                groups.setdefault(e.superset_group, []).append(e)
        return groups

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "entries": [e.to_dict() for e in self.entries],
            "target_muscles": [m.value for m in self.target_muscles],
            "estimated_duration_minutes": self.estimated_duration_minutes or self.compute_duration(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkoutPlan":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d["name"],
            description=d.get("description", ""),
            entries=[PlanEntry.from_dict(e) for e in d["entries"]],
            target_muscles=[MuscleGroup(m) for m in d.get("target_muscles", [])],
            estimated_duration_minutes=d.get("estimated_duration_minutes"),
            created_at=d.get("created_at", datetime.now().isoformat()),
        )


# ---------------------------------------------------------------------------
# O3 — Progression Groups (exercise chains with programmable rules)
# ---------------------------------------------------------------------------

@dataclass
class ProgressionRule:
    """
    A transition rule between two exercises in a progression chain.

    When the user hits `trigger_reps` for `trigger_sets` on `from_exercise_id`,
    the system suggests transitioning to `to_exercise_id`.

    Transition modes:
    - "replace": fully swap to the new exercise
    - "blend": mix old and new exercises (e.g. 2 sets old + 1 set new)
    """
    from_exercise_id: str
    to_exercise_id: str
    trigger_reps: int               # hit this many reps...
    trigger_sets: int               # ...for this many sets to trigger
    transition: str = "replace"     # "replace" | "blend"
    blend_new_sets: int = 0         # during blend: sets of new exercise
    blend_old_sets: int = 0         # during blend: sets of old exercise kept

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProgressionRule":
        return cls(
            from_exercise_id=d["from_exercise_id"],
            to_exercise_id=d["to_exercise_id"],
            trigger_reps=d.get("trigger_reps", 10),
            trigger_sets=d.get("trigger_sets", 3),
            transition=d.get("transition", "replace"),
            blend_new_sets=d.get("blend_new_sets", 0),
            blend_old_sets=d.get("blend_old_sets", 0),
        )


@dataclass
class ProgressionGroup:
    """
    A chain of exercises ordered from easiest to hardest,
    with rules governing when to transition between them.

    Stored in progressions.json.
    """
    name: str
    exercises: list[str]                # ordered exercise IDs (easy -> hard)
    rules: list[ProgressionRule] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "exercises": self.exercises,
            "rules": [r.to_dict() for r in self.rules],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProgressionGroup":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d["name"],
            exercises=d.get("exercises", []),
            rules=[ProgressionRule.from_dict(r) for r in d.get("rules", [])],
            created_at=d.get("created_at", datetime.now().isoformat()),
        )
