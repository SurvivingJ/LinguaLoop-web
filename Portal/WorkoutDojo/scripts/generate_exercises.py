"""Generate 100 exercises and progression groups for WorkoutOS."""

import json
import os
import uuid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
EXERCISES_FILE = os.path.join(BASE_DIR, "data", "exercises", "exercises.json")
PROGRESSIONS_FILE = os.path.join(BASE_DIR, "data", "progressions", "progressions.json")


def uid():
    return str(uuid.uuid4())


def ex(name, category, movement, primary, secondary=None, equipment="", compound=False, uses_weights=True):
    eid = uid()
    return eid, {
        "name": name,
        "category": category,
        "movement_pattern": movement,
        "equipment": equipment,
        "primary_muscles": primary,
        "secondary_muscles": secondary or [],
        "progression_aggression": "standard",
        "voice_name": "",
        "notes": "",
        "is_compound": compound,
        "uses_weights": uses_weights,
        "id": eid,
        "created_at": "2026-03-09T22:00:00.000000",
    }


exercises = []
ids = {}  # name -> id


def add(name, **kwargs):
    eid, data = ex(name, **kwargs)
    exercises.append(data)
    ids[name] = eid
    return eid


# ============================================================
# BARBELL COMPOUND (~15)
# ============================================================
add("Back Squat", category="barbell_compound", movement="squat",
    primary=["quads", "glutes"], secondary=["hamstrings", "abs"], equipment="barbell", compound=True)
add("Front Squat", category="barbell_compound", movement="squat",
    primary=["quads", "glutes"], secondary=["abs", "back"], equipment="barbell", compound=True)
add("Bench Press", category="barbell_compound", movement="horizontal_push",
    primary=["chest", "triceps"], secondary=["shoulders"], equipment="barbell", compound=True)
add("Incline Bench Press", category="barbell_compound", movement="horizontal_push",
    primary=["chest", "shoulders"], secondary=["triceps"], equipment="barbell", compound=True)
add("Overhead Press", category="barbell_compound", movement="vertical_push",
    primary=["shoulders", "triceps"], secondary=["abs", "traps"], equipment="barbell", compound=True)
add("Deadlift", category="barbell_compound", movement="hip_hinge",
    primary=["hamstrings", "glutes", "back"], secondary=["forearms", "traps", "abs"], equipment="barbell", compound=True)
add("Romanian Deadlift", category="barbell_compound", movement="hip_hinge",
    primary=["hamstrings", "glutes"], secondary=["back", "forearms"], equipment="barbell", compound=True)
add("Barbell Row", category="barbell_compound", movement="horizontal_pull",
    primary=["back", "lats"], secondary=["biceps", "forearms"], equipment="barbell", compound=True)
add("Pendlay Row", category="barbell_compound", movement="horizontal_pull",
    primary=["back", "lats"], secondary=["biceps", "forearms"], equipment="barbell", compound=True)
add("Sumo Deadlift", category="barbell_compound", movement="hip_hinge",
    primary=["glutes", "quads", "hamstrings"], secondary=["back", "forearms"], equipment="barbell", compound=True)
add("Close-Grip Bench Press", category="barbell_compound", movement="horizontal_push",
    primary=["triceps", "chest"], secondary=["shoulders"], equipment="barbell", compound=True)
add("Push Press", category="barbell_compound", movement="vertical_push",
    primary=["shoulders", "triceps"], secondary=["quads", "abs"], equipment="barbell", compound=True)
add("Floor Press", category="barbell_compound", movement="horizontal_push",
    primary=["chest", "triceps"], secondary=["shoulders"], equipment="barbell", compound=True)
add("Zercher Squat", category="barbell_compound", movement="squat",
    primary=["quads", "glutes"], secondary=["abs", "biceps", "back"], equipment="barbell", compound=True)
add("Barbell Hip Thrust", category="barbell_compound", movement="hip_hinge",
    primary=["glutes", "hamstrings"], secondary=["abs"], equipment="barbell", compound=True)

# ============================================================
# BARBELL ISOLATION (~8)
# ============================================================
add("Barbell Curl", category="barbell_isolation", movement="isolation",
    primary=["biceps"], secondary=["forearms"], equipment="barbell")
add("Skull Crusher", category="barbell_isolation", movement="isolation",
    primary=["triceps"], secondary=["shoulders"], equipment="EZ bar")
add("Preacher Curl", category="barbell_isolation", movement="isolation",
    primary=["biceps"], secondary=["forearms"], equipment="EZ bar")
add("Barbell Wrist Curl", category="barbell_isolation", movement="isolation",
    primary=["forearms"], equipment="barbell")
add("Upright Row", category="barbell_isolation", movement="vertical_pull",
    primary=["shoulders", "traps"], secondary=["biceps"], equipment="barbell")
add("Barbell Shrug", category="barbell_isolation", movement="isolation",
    primary=["traps"], secondary=["forearms"], equipment="barbell")
add("Good Morning", category="barbell_isolation", movement="hip_hinge",
    primary=["hamstrings", "back"], secondary=["glutes"], equipment="barbell")
add("Landmine Press", category="barbell_isolation", movement="vertical_push",
    primary=["shoulders", "chest"], secondary=["triceps"], equipment="landmine")

# ============================================================
# DUMBBELL (~15)
# ============================================================
add("DB Bench Press", category="dumbbell", movement="horizontal_push",
    primary=["chest", "triceps"], secondary=["shoulders"], equipment="dumbbells")
add("DB Incline Press", category="dumbbell", movement="horizontal_push",
    primary=["chest", "shoulders"], secondary=["triceps"], equipment="dumbbells")
add("DB Shoulder Press", category="dumbbell", movement="vertical_push",
    primary=["shoulders", "triceps"], secondary=["traps"], equipment="dumbbells")
add("DB Row", category="dumbbell", movement="horizontal_pull",
    primary=["back", "lats"], secondary=["biceps", "forearms"], equipment="dumbbell")
add("DB Lateral Raise", category="dumbbell", movement="isolation",
    primary=["shoulders"], secondary=["traps"], equipment="dumbbells")
add("DB Front Raise", category="dumbbell", movement="isolation",
    primary=["shoulders"], equipment="dumbbells")
add("DB Curl", category="dumbbell", movement="isolation",
    primary=["biceps"], secondary=["forearms"], equipment="dumbbells")
add("DB Hammer Curl", category="dumbbell", movement="isolation",
    primary=["biceps", "forearms"], equipment="dumbbells")
add("DB Fly", category="dumbbell", movement="isolation",
    primary=["chest"], secondary=["shoulders"], equipment="dumbbells")
add("DB Reverse Fly", category="dumbbell", movement="isolation",
    primary=["shoulders", "back"], secondary=["traps"], equipment="dumbbells")
add("DB Lunges", category="dumbbell", movement="squat",
    primary=["quads", "glutes"], secondary=["hamstrings"], equipment="dumbbells")
add("DB Goblet Squat", category="dumbbell", movement="squat",
    primary=["quads", "glutes"], secondary=["abs"], equipment="dumbbell")
add("DB Tricep Extension", category="dumbbell", movement="isolation",
    primary=["triceps"], equipment="dumbbell")
add("DB Pullover", category="dumbbell", movement="isolation",
    primary=["lats", "chest"], secondary=["triceps"], equipment="dumbbell")
add("DB Shrug", category="dumbbell", movement="isolation",
    primary=["traps"], secondary=["forearms"], equipment="dumbbells")

# ============================================================
# CABLE (~10)
# ============================================================
add("Cable Fly", category="cable", movement="isolation",
    primary=["chest"], secondary=["shoulders"], equipment="cable machine")
add("Cable Crossover", category="cable", movement="isolation",
    primary=["chest"], secondary=["shoulders"], equipment="cable machine")
add("Tricep Pushdown", category="cable", movement="isolation",
    primary=["triceps"], equipment="cable machine")
add("Cable Curl", category="cable", movement="isolation",
    primary=["biceps"], secondary=["forearms"], equipment="cable machine")
add("Face Pull", category="cable", movement="horizontal_pull",
    primary=["shoulders", "back"], secondary=["biceps"], equipment="cable machine")
add("Cable Lateral Raise", category="cable", movement="isolation",
    primary=["shoulders"], equipment="cable machine")
add("Cable Row", category="cable", movement="horizontal_pull",
    primary=["back", "lats"], secondary=["biceps"], equipment="cable machine")
add("Lat Pushdown", category="cable", movement="isolation",
    primary=["lats", "triceps"], equipment="cable machine")
add("Cable Woodchop", category="cable", movement="core",
    primary=["abs"], secondary=["shoulders"], equipment="cable machine")
add("Cable Pull-Through", category="cable", movement="hip_hinge",
    primary=["glutes", "hamstrings"], equipment="cable machine")

# ============================================================
# MACHINE (~10)
# ============================================================
add("Leg Press", category="machine", movement="squat",
    primary=["quads", "glutes"], secondary=["hamstrings"], equipment="leg press")
add("Leg Extension", category="machine", movement="isolation",
    primary=["quads"], equipment="leg extension machine")
add("Leg Curl", category="machine", movement="isolation",
    primary=["hamstrings"], equipment="leg curl machine")
add("Chest Press Machine", category="machine", movement="horizontal_push",
    primary=["chest", "triceps"], secondary=["shoulders"], equipment="chest press")
add("Lat Pulldown", category="machine", movement="vertical_pull",
    primary=["lats", "back"], secondary=["biceps"], equipment="lat pulldown")
add("Seated Row Machine", category="machine", movement="horizontal_pull",
    primary=["back", "lats"], secondary=["biceps"], equipment="seated row")
add("Pec Deck", category="machine", movement="isolation",
    primary=["chest"], equipment="pec deck")
add("Calf Raise Machine", category="machine", movement="isolation",
    primary=["calves"], equipment="calf raise machine")
add("Hack Squat", category="machine", movement="squat",
    primary=["quads", "glutes"], secondary=["hamstrings"], equipment="hack squat")
add("Smith Machine Squat", category="machine", movement="squat",
    primary=["quads", "glutes"], secondary=["hamstrings"], equipment="Smith machine")

# ============================================================
# BODYWEIGHT (~18)
# ============================================================
add("Push-Up", category="bodyweight", movement="horizontal_push",
    primary=["chest", "triceps"], secondary=["shoulders", "abs"], uses_weights=False)
add("Diamond Push-Up", category="bodyweight", movement="horizontal_push",
    primary=["triceps", "chest"], secondary=["shoulders"], uses_weights=False)
add("Archer Push-Up", category="bodyweight", movement="horizontal_push",
    primary=["chest", "triceps"], secondary=["shoulders", "abs"], uses_weights=False)
add("Pike Push-Up", category="bodyweight", movement="vertical_push",
    primary=["shoulders", "triceps"], secondary=["chest"], uses_weights=False)
add("Handstand Push-Up", category="bodyweight", movement="vertical_push",
    primary=["shoulders", "triceps"], secondary=["traps", "abs"], uses_weights=False)
add("Pull-Up", category="bodyweight", movement="vertical_pull",
    primary=["lats", "back"], secondary=["biceps", "forearms"], uses_weights=False)
add("Chin-Up", category="bodyweight", movement="vertical_pull",
    primary=["biceps", "lats"], secondary=["back", "forearms"], uses_weights=False)
add("Muscle-Up", category="bodyweight", movement="vertical_pull",
    primary=["lats", "chest", "triceps"], secondary=["shoulders", "abs"], uses_weights=False)
add("Dip", category="bodyweight", movement="horizontal_push",
    primary=["triceps", "chest"], secondary=["shoulders"], uses_weights=False)
add("Ring Dip", category="bodyweight", movement="horizontal_push",
    primary=["triceps", "chest"], secondary=["shoulders", "abs"], uses_weights=False)
add("Inverted Row", category="bodyweight", movement="horizontal_pull",
    primary=["back", "lats"], secondary=["biceps", "forearms"], uses_weights=False)
add("Bodyweight Squat", category="bodyweight", movement="squat",
    primary=["quads", "glutes"], secondary=["hamstrings"], uses_weights=False)
add("Pistol Squat", category="bodyweight", movement="squat",
    primary=["quads", "glutes"], secondary=["hamstrings", "abs"], uses_weights=False)
add("Bulgarian Split Squat", category="bodyweight", movement="squat",
    primary=["quads", "glutes"], secondary=["hamstrings"], uses_weights=False)
add("Hanging Leg Raise", category="bodyweight", movement="core",
    primary=["abs", "hip_flexors"], uses_weights=False)
add("L-Sit", category="bodyweight", movement="core",
    primary=["abs", "hip_flexors"], secondary=["quads"], uses_weights=False)
add("Plank", category="bodyweight", movement="core",
    primary=["abs"], secondary=["shoulders", "glutes"], uses_weights=False)
add("Ab Wheel Rollout", category="bodyweight", movement="core",
    primary=["abs"], secondary=["shoulders", "lats"], uses_weights=False, equipment="ab wheel")

# ============================================================
# STRETCHING (~12)
# ============================================================
add("Hamstring Stretch", category="stretching", movement="isolation",
    primary=["hamstrings"], uses_weights=False)
add("Quad Stretch", category="stretching", movement="isolation",
    primary=["quads"], uses_weights=False)
add("Hip Flexor Stretch", category="stretching", movement="isolation",
    primary=["hip_flexors"], secondary=["quads"], uses_weights=False)
add("Chest Doorway Stretch", category="stretching", movement="isolation",
    primary=["chest"], secondary=["shoulders"], uses_weights=False)
add("Shoulder Cross-Body Stretch", category="stretching", movement="isolation",
    primary=["shoulders"], uses_weights=False)
add("Tricep Stretch", category="stretching", movement="isolation",
    primary=["triceps"], uses_weights=False)
add("Lat Stretch", category="stretching", movement="isolation",
    primary=["lats"], secondary=["shoulders"], uses_weights=False)
add("Pigeon Pose", category="stretching", movement="isolation",
    primary=["glutes", "hip_flexors"], uses_weights=False)
add("Cat-Cow Stretch", category="stretching", movement="core",
    primary=["back", "abs"], uses_weights=False)
add("Seated Spinal Twist", category="stretching", movement="core",
    primary=["back", "abs"], uses_weights=False)
add("Calf Stretch", category="stretching", movement="isolation",
    primary=["calves"], uses_weights=False)
add("Wrist Flexor Stretch", category="stretching", movement="isolation",
    primary=["forearms"], uses_weights=False)

# ============================================================
# MOBILITY (~12)
# ============================================================
add("Hip Circles", category="mobility", movement="isolation",
    primary=["hip_flexors", "glutes"], uses_weights=False)
add("Shoulder Dislocates", category="mobility", movement="isolation",
    primary=["shoulders"], secondary=["chest"], uses_weights=False, equipment="PVC pipe/band")
add("Thoracic Spine Rotation", category="mobility", movement="core",
    primary=["back"], secondary=["abs"], uses_weights=False)
add("Ankle Circles", category="mobility", movement="isolation",
    primary=["calves"], uses_weights=False)
add("Wrist Circles", category="mobility", movement="isolation",
    primary=["forearms"], uses_weights=False)
add("Leg Swings", category="mobility", movement="isolation",
    primary=["hip_flexors", "hamstrings"], uses_weights=False)
add("Arm Circles", category="mobility", movement="isolation",
    primary=["shoulders"], uses_weights=False)
add("World's Greatest Stretch", category="mobility", movement="core",
    primary=["hip_flexors", "back", "shoulders"], secondary=["hamstrings", "glutes"], uses_weights=False)
add("Inchworm", category="mobility", movement="core",
    primary=["hamstrings", "abs"], secondary=["shoulders"], uses_weights=False)
add("Scorpion Stretch", category="mobility", movement="core",
    primary=["hip_flexors", "back"], secondary=["glutes"], uses_weights=False)
add("Deep Squat Hold", category="mobility", movement="squat",
    primary=["hip_flexors", "quads", "glutes"], secondary=["calves"], uses_weights=False)
add("Band Pull-Apart", category="mobility", movement="horizontal_pull",
    primary=["shoulders", "back"], secondary=["traps"], uses_weights=False, equipment="resistance band")

print(f"Total exercises: {len(exercises)}")

# ============================================================
# PROGRESSION GROUPS
# ============================================================

def make_rule(from_name, to_name, reps=12, sets=3, transition="replace"):
    return {
        "from_exercise_id": ids[from_name],
        "to_exercise_id": ids[to_name],
        "trigger_reps": reps,
        "trigger_sets": sets,
        "transition": transition,
        "blend_new_sets": 1 if transition == "blend" else 0,
        "blend_old_sets": 2 if transition == "blend" else 0,
    }


progressions = []


def prog(name, exercise_names, reps=12, sets=3, transition="replace"):
    rules = []
    for i in range(len(exercise_names) - 1):
        rules.append(make_rule(exercise_names[i], exercise_names[i + 1], reps, sets, transition))
    progressions.append({
        "id": uid(),
        "name": name,
        "exercises": [ids[n] for n in exercise_names],
        "rules": rules,
        "created_at": "2026-03-09T22:00:00.000000",
    })


# Bodyweight progressions use 15 reps
prog("Push-Up Progression",
     ["Push-Up", "Diamond Push-Up", "Archer Push-Up"], reps=15, sets=3)

prog("Overhead Push Progression",
     ["Pike Push-Up", "Handstand Push-Up"], reps=15, sets=3)

prog("Pull-Up Progression",
     ["Inverted Row", "Chin-Up", "Pull-Up", "Muscle-Up"], reps=15, sets=3)

prog("Dip Progression",
     ["Dip", "Ring Dip"], reps=15, sets=3)

prog("Squat Progression",
     ["Bodyweight Squat", "DB Goblet Squat", "Front Squat", "Back Squat"], reps=12, sets=3)

prog("Pistol Squat Progression",
     ["Bodyweight Squat", "Bulgarian Split Squat", "Pistol Squat"], reps=15, sets=3)

prog("Bench Press Progression",
     ["DB Bench Press", "Bench Press", "Close-Grip Bench Press", "Incline Bench Press"], reps=12, sets=3)

prog("Deadlift Progression",
     ["Romanian Deadlift", "Deadlift", "Sumo Deadlift"], reps=12, sets=3)

prog("Row Progression",
     ["Inverted Row", "DB Row", "Barbell Row", "Pendlay Row"], reps=12, sets=3)

prog("Overhead Press Progression",
     ["DB Shoulder Press", "Overhead Press", "Push Press"], reps=12, sets=3)

prog("Curl Progression",
     ["DB Curl", "DB Hammer Curl", "Barbell Curl", "Preacher Curl"], reps=12, sets=3)

prog("Core Progression",
     ["Plank", "Hanging Leg Raise", "L-Sit", "Ab Wheel Rollout"], reps=15, sets=3)

prog("Hip Hinge Progression",
     ["Good Morning", "Romanian Deadlift", "Deadlift"], reps=12, sets=3)

prog("Leg Machine Progression",
     ["Leg Press", "Hack Squat", "Smith Machine Squat"], reps=12, sets=3)

print(f"Total progressions: {len(progressions)}")

# ============================================================
# WRITE FILES
# ============================================================

os.makedirs(os.path.dirname(EXERCISES_FILE), exist_ok=True)
with open(EXERCISES_FILE, "w", encoding="utf-8") as f:
    json.dump(exercises, f, indent=2)
print(f"Wrote {EXERCISES_FILE}")

os.makedirs(os.path.dirname(PROGRESSIONS_FILE), exist_ok=True)
with open(PROGRESSIONS_FILE, "w", encoding="utf-8") as f:
    json.dump(progressions, f, indent=2)
print(f"Wrote {PROGRESSIONS_FILE}")
