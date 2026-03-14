"""Create classic calisthenics workout plans and mark timed exercises."""
import json
import uuid
import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXERCISES_FILE = os.path.join(BASE, "data", "exercises", "exercises.json")
PLANS_FILE = os.path.join(BASE, "data", "workouts", "plans.json")

# Load exercises
with open(EXERCISES_FILE, "r") as f:
    exercises = json.load(f)

by_name = {e["name"]: e for e in exercises}


# --- Step 1: Mark timed exercises ---
TIMED_EXERCISES = [
    # All stretching
    "Hamstring Stretch", "Quad Stretch", "Hip Flexor Stretch", "Chest Doorway Stretch",
    "Shoulder Cross-Body Stretch", "Tricep Stretch", "Lat Stretch", "Pigeon Pose",
    "Cat-Cow Stretch", "Seated Spinal Twist", "Calf Stretch", "Wrist Flexor Stretch",
    # All mobility
    "Hip Circles", "Shoulder Dislocates", "Thoracic Spine Rotation", "Ankle Circles",
    "Wrist Circles", "Leg Swings", "Arm Circles", "World's Greatest Stretch",
    "Inchworm", "Scorpion Stretch", "Deep Squat Hold", "Band Pull-Apart",
    # Isometric bodyweight
    "Plank", "L-Sit",
]

updated_count = 0
for name in TIMED_EXERCISES:
    ex = by_name.get(name)
    if ex and not ex.get("is_timed", False):
        ex["is_timed"] = True
        updated_count += 1

with open(EXERCISES_FILE, "w") as f:
    json.dump(exercises, f, indent=2)
print(f"Marked {updated_count} exercises as is_timed")


# --- Step 2: Helpers ---
def eid(name):
    return by_name[name]["id"]


def make_set(rep_min=0, rep_max=0, rest=90, warmup=False, rpe=None, duration=None):
    s = {
        "rep_min": rep_min,
        "rep_max": rep_max,
        "rest_seconds": rest,
        "is_warmup": warmup,
        "target_rpe": rpe,
    }
    if duration is not None:
        s["duration_seconds"] = duration
    return s


def make_entry(name, order, sets, superset=None, notes="", locked=False):
    return {
        "exercise_id": eid(name),
        "order": order,
        "sets": sets,
        "superset_group": superset,
        "filler_id": None,
        "filler_type": "none",
        "notes": notes,
        "starting_weight_kg": None,
        "optimizer_locked": locked,
    }


now = datetime.now().isoformat()


# --- Workout 1: Push-Pull Superset Pyramid ---
pyramid_plan = {
    "id": str(uuid.uuid4()),
    "name": "Push-Pull Superset Pyramid",
    "description": (
        "Classic calisthenics pyramid: alternate pull-ups and push-ups with "
        "increasing reps, stretches during rest. Finisher with dips + inverted rows superset."
    ),
    "entries": [
        # Superset A: Pull-Up + Lat Stretch (5 sets pyramid)
        make_entry("Pull-Up", 1,
            [make_set(i, i, rest=60) for i in [1, 2, 3, 4, 5]],
            superset="A", notes="Pyramid up: 1-2-3-4-5 reps"),
        make_entry("Lat Stretch", 2,
            [make_set(duration=30, rest=60) for _ in range(5)],
            superset="A", notes="30s hold each side between pull-up sets"),

        # Superset B: Push-Up + Chest Doorway Stretch (5 sets pyramid, double pull-up reps)
        make_entry("Push-Up", 3,
            [make_set(i, i, rest=60) for i in [2, 4, 6, 8, 10]],
            superset="B", notes="Pyramid up: 2-4-6-8-10 reps (double the pull-ups)"),
        make_entry("Chest Doorway Stretch", 4,
            [make_set(duration=30, rest=60) for _ in range(5)],
            superset="B", notes="30s hold between push-up sets"),

        # Superset C: Dip + Inverted Row + Shoulder Stretch
        make_entry("Dip", 5,
            [make_set(6, 10, rest=60) for _ in range(3)],
            superset="C", notes="Finisher superset"),
        make_entry("Inverted Row", 6,
            [make_set(8, 12, rest=60) for _ in range(3)],
            superset="C", notes="Match dip sets"),
        make_entry("Shoulder Cross-Body Stretch", 7,
            [make_set(duration=30, rest=60) for _ in range(3)],
            superset="C", notes="30s each side"),

        # Core finisher
        make_entry("Hanging Leg Raise", 8,
            [make_set(8, 15, rest=60) for _ in range(3)],
            notes="Core finisher"),

        # Cooldown superset
        make_entry("Pigeon Pose", 9,
            [make_set(duration=45, rest=0) for _ in range(2)],
            superset="D", notes="Cooldown: 45s each side"),
        make_entry("Cat-Cow Stretch", 10,
            [make_set(duration=30, rest=0) for _ in range(2)],
            superset="D", notes="Cooldown: slow and controlled"),
    ],
    "target_muscles": ["chest", "back", "lats", "triceps", "biceps", "shoulders", "abs"],
    "estimated_duration_minutes": 35,
    "created_at": now,
}


# --- Workout 2: Full Body Mobility Flow ---
mobility_plan = {
    "id": str(uuid.uuid4()),
    "name": "Full Body Mobility Flow",
    "description": (
        "Complete mobility session flowing head-to-toe. All timed holds and movements. "
        "Perfect for rest days or pre-workout warm-up."
    ),
    "entries": [
        make_entry("Arm Circles", 1,
            [make_set(duration=30, rest=10), make_set(duration=30, rest=10)],
            notes="Forward then backward", locked=True),
        make_entry("Shoulder Dislocates", 2,
            [make_set(duration=30, rest=10) for _ in range(3)],
            notes="Slow and controlled with band/stick", locked=True),
        make_entry("Thoracic Spine Rotation", 3,
            [make_set(duration=30, rest=10) for _ in range(3)],
            notes="Each side", locked=True),
        make_entry("Cat-Cow Stretch", 4,
            [make_set(duration=30, rest=10) for _ in range(3)],
            notes="Sync with breath", locked=True),
        make_entry("World's Greatest Stretch", 5,
            [make_set(duration=45, rest=10) for _ in range(3)],
            notes="Alternate sides each set", locked=True),
        make_entry("Hip Circles", 6,
            [make_set(duration=30, rest=10), make_set(duration=30, rest=10)],
            notes="Each direction", locked=True),
        make_entry("Leg Swings", 7,
            [make_set(duration=30, rest=10), make_set(duration=30, rest=10)],
            notes="Front-to-back then side-to-side", locked=True),
        make_entry("Deep Squat Hold", 8,
            [make_set(duration=45, rest=15) for _ in range(3)],
            notes="Heels down, chest up, push knees out", locked=True),
        make_entry("Scorpion Stretch", 9,
            [make_set(duration=30, rest=10) for _ in range(2)],
            notes="Alternate sides", locked=True),
        make_entry("Pigeon Pose", 10,
            [make_set(duration=45, rest=10) for _ in range(2)],
            notes="Each side, sink into the stretch", locked=True),
        make_entry("Inchworm", 11,
            [make_set(duration=30, rest=10) for _ in range(3)],
            notes="Walk hands out to plank, walk back", locked=True),
        make_entry("Ankle Circles", 12,
            [make_set(duration=20, rest=5), make_set(duration=20, rest=0)],
            notes="Each foot, both directions", locked=True),
    ],
    "target_muscles": ["shoulders", "back", "hip_flexors", "glutes", "hamstrings", "quads", "abs"],
    "estimated_duration_minutes": 20,
    "created_at": now,
}


# --- Workout 3: Calisthenics Upper Body ---
upper_plan = {
    "id": str(uuid.uuid4()),
    "name": "Calisthenics Upper Body",
    "description": (
        "Comprehensive bodyweight upper body session. Pull-up/push-up supersets with "
        "stretches in rest periods, plus pike push-ups and chin-ups for vertical work."
    ),
    "entries": [
        # Superset A: Pull-Up + Diamond Push-Up + Lat Stretch
        make_entry("Pull-Up", 1,
            [make_set(6, 10, rest=90) for _ in range(4)],
            superset="A", notes="Full range of motion, dead hang at bottom"),
        make_entry("Diamond Push-Up", 2,
            [make_set(10, 15, rest=90) for _ in range(4)],
            superset="A", notes="Hands together under chest"),
        make_entry("Lat Stretch", 3,
            [make_set(duration=30, rest=30) for _ in range(4)],
            superset="A", notes="30s each side during rest"),

        # Superset B: Pike Push-Up + Chin-Up + Shoulder Stretch
        make_entry("Pike Push-Up", 4,
            [make_set(6, 10, rest=90) for _ in range(3)],
            superset="B", notes="Vertical push — feet elevated for extra difficulty"),
        make_entry("Chin-Up", 5,
            [make_set(6, 10, rest=90) for _ in range(3)],
            superset="B", notes="Palms facing you, squeeze biceps at top"),
        make_entry("Shoulder Cross-Body Stretch", 6,
            [make_set(duration=30, rest=30) for _ in range(3)],
            superset="B", notes="30s each side"),

        # Superset C: Dip + Inverted Row + Chest Stretch
        make_entry("Dip", 7,
            [make_set(8, 12, rest=90) for _ in range(3)],
            superset="C", notes="Lean forward slightly for chest emphasis"),
        make_entry("Inverted Row", 8,
            [make_set(8, 12, rest=90) for _ in range(3)],
            superset="C", notes="Squeeze shoulder blades together"),
        make_entry("Chest Doorway Stretch", 9,
            [make_set(duration=30, rest=30) for _ in range(3)],
            superset="C", notes="30s hold during rest"),

        # Core
        make_entry("Hanging Leg Raise", 10,
            [make_set(8, 15, rest=60) for _ in range(3)],
            notes="Controlled, no swinging"),
        make_entry("L-Sit", 11,
            [make_set(duration=20, rest=60) for _ in range(3)],
            notes="On parallettes or dip bars"),

        # Cooldown
        make_entry("Tricep Stretch", 12,
            [make_set(duration=30, rest=0) for _ in range(2)],
            superset="D", notes="30s each arm"),
        make_entry("Pigeon Pose", 13,
            [make_set(duration=30, rest=0) for _ in range(2)],
            superset="D", notes="Wind down"),
    ],
    "target_muscles": ["chest", "back", "lats", "triceps", "biceps", "shoulders", "abs"],
    "estimated_duration_minutes": 45,
    "created_at": now,
}


# --- Workout 4: Calisthenics Lower Body + Core ---
lower_plan = {
    "id": str(uuid.uuid4()),
    "name": "Calisthenics Lower + Core",
    "description": (
        "Bodyweight lower body and core session. Bulgarian split squats, deep squats, "
        "and core work with stretches between sets for active recovery."
    ),
    "entries": [
        # Superset A: Bulgarian Split Squat + Hip Flexor Stretch
        make_entry("Bulgarian Split Squat", 1,
            [make_set(8, 12, rest=90) for _ in range(4)],
            superset="A", notes="Each leg — rear foot on bench"),
        make_entry("Hip Flexor Stretch", 2,
            [make_set(duration=30, rest=30) for _ in range(4)],
            superset="A", notes="30s each side — stretch the non-working hip flexor"),

        # Superset B: Bodyweight Squat (high rep) + Hamstring Stretch
        make_entry("Bodyweight Squat", 3,
            [make_set(15, 25, rest=60) for _ in range(3)],
            superset="B", notes="Deep squat, pause at bottom"),
        make_entry("Hamstring Stretch", 4,
            [make_set(duration=30, rest=30) for _ in range(3)],
            superset="B", notes="30s each leg between sets"),

        # Core block superset
        make_entry("Plank", 5,
            [make_set(duration=45, rest=45) for _ in range(3)],
            superset="C", notes="Squeeze glutes, brace abs"),
        make_entry("Hanging Leg Raise", 6,
            [make_set(8, 15, rest=45) for _ in range(3)],
            superset="C", notes="Controlled, no swinging"),

        make_entry("Ab Wheel Rollout", 7,
            [make_set(8, 12, rest=60) for _ in range(3)],
            notes="From knees or standing"),

        # Cooldown
        make_entry("Quad Stretch", 8,
            [make_set(duration=30, rest=0) for _ in range(2)],
            superset="D", notes="30s each leg"),
        make_entry("Pigeon Pose", 9,
            [make_set(duration=45, rest=0) for _ in range(2)],
            superset="D", notes="Deep hip opener, 45s each side"),
        make_entry("Calf Stretch", 10,
            [make_set(duration=30, rest=0) for _ in range(2)],
            superset="D", notes="30s each leg"),
    ],
    "target_muscles": ["quads", "glutes", "hamstrings", "hip_flexors", "abs", "calves"],
    "estimated_duration_minutes": 35,
    "created_at": now,
}


# --- Step 3: Save plans ---
with open(PLANS_FILE, "r") as f:
    plans = json.load(f)

plans.extend([pyramid_plan, mobility_plan, upper_plan, lower_plan])

with open(PLANS_FILE, "w") as f:
    json.dump(plans, f, indent=2)

print(f"\nAdded 4 workout plans (total: {len(plans)})")
print(f"  1. {pyramid_plan['name']} ({pyramid_plan['estimated_duration_minutes']}min)")
print(f"  2. {mobility_plan['name']} ({mobility_plan['estimated_duration_minutes']}min)")
print(f"  3. {upper_plan['name']} ({upper_plan['estimated_duration_minutes']}min)")
print(f"  4. {lower_plan['name']} ({lower_plan['estimated_duration_minutes']}min)")
