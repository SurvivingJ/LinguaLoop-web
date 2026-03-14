"""
WorkoutOS — Configuration

Central config for file paths, weight increment tables, and defaults.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Data file paths
# ---------------------------------------------------------------------------
DATA_DIR         = os.path.join(BASE_DIR, "data")
EXERCISES_FILE   = os.path.join(DATA_DIR, "exercises", "exercises.json")
MOBILITY_FILE    = os.path.join(DATA_DIR, "exercises", "mobility.json")
PLANS_FILE       = os.path.join(DATA_DIR, "workouts", "plans.json")
PROGRAMS_FILE    = os.path.join(DATA_DIR, "programs", "programs.json")
PROGRESSIONS_FILE = os.path.join(DATA_DIR, "progressions", "progressions.json")
SESSIONS_FILE    = os.path.join(DATA_DIR, "history", "sessions.csv")
SETS_LOG_FILE    = os.path.join(DATA_DIR, "history", "sets_log.csv")
BODY_WEIGHT_FILE = os.path.join(DATA_DIR, "history", "body_weight.csv")

# ---------------------------------------------------------------------------
# Weight increment table  (A1.3)
#
# Key:   (ExerciseCategory.value, strength_level)
#        strength_level is "beginner" | "intermediate" | "advanced" | "any"
# Value: [conservative_kg, standard_kg, aggressive_kg]
#
# "any" matches all strength levels (used for categories where level
# doesn't meaningfully change the jump size).
# ---------------------------------------------------------------------------
WEIGHT_INCREMENTS: dict[tuple[str, str], list[float | None]] = {
    ("barbell_compound",  "beginner"):     [2.5,  5.0, 10.0],
    ("barbell_compound",  "intermediate"): [2.5,  2.5,  5.0],
    ("barbell_compound",  "advanced"):     [1.25, 2.5,  2.5],
    ("barbell_isolation", "beginner"):     [1.25, 2.5,  5.0],
    ("barbell_isolation", "intermediate"): [1.25, 1.25, 2.5],
    ("dumbbell",          "any"):          [2.0,  2.0,  4.0],
    ("cable",             "any"):          [2.5,  2.5,  5.0],
    ("machine",           "any"):          [2.5,  5.0,  5.0],
    ("bodyweight",        "any"):          [None, None, None],  # rep-based only
    ("stretching",        "any"):          [None, None, None],  # duration/rep-based
    ("mobility",          "any"):          [None, None, None],  # duration/rep-based
}

# ---------------------------------------------------------------------------
# Progression engine defaults
# ---------------------------------------------------------------------------
RPE_DRIFT_WINDOW = 4            # number of recent sessions to check
RPE_DRIFT_THRESHOLD = 1.5       # avg RPE increase over window that triggers warning
MIN_SESSIONS_FOR_PROGRESSION = 2  # must have at least N sessions before suggesting increase
ESTIMATED_1RM_FORMULA = "epley"   # "epley" or "brzycki"

# ---------------------------------------------------------------------------
# Strength level thresholds (relative to body weight, for barbell compounds)
# Used by progression engine to determine which increment row to use.
# Values are multipliers of body weight for estimated 1RM.
# ---------------------------------------------------------------------------
STRENGTH_LEVELS = {
    # (movement_pattern): {level: min_1rm_bw_ratio}
    "squat":           {"beginner": 0.0, "intermediate": 1.25, "advanced": 1.75},
    "hip_hinge":       {"beginner": 0.0, "intermediate": 1.5,  "advanced": 2.0},
    "horizontal_push": {"beginner": 0.0, "intermediate": 1.0,  "advanced": 1.5},
    "horizontal_pull": {"beginner": 0.0, "intermediate": 0.9,  "advanced": 1.3},
    "vertical_push":   {"beginner": 0.0, "intermediate": 0.6,  "advanced": 0.9},
    "vertical_pull":   {"beginner": 0.0, "intermediate": 0.9,  "advanced": 1.3},
}

# ---------------------------------------------------------------------------
# Session defaults
# ---------------------------------------------------------------------------
DEFAULT_REST_SECONDS = 90
WORK_TIME_ESTIMATE_SECONDS = 30   # used for duration estimation
DELOAD_VOLUME_PCT_DEFAULT = 40
