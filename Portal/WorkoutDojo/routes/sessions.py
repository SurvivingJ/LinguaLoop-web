"""WorkoutOS — Session Routes (S14, S27)"""

import dataclasses

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from services.exercise_service import list_exercises, list_mobility
from services.filler_scheduler import schedule_fillers
from services.ordering_algorithm import order_entries
from services.workout_optimizer import optimize_workout
from services.program_service import get_active_program, get_program_status
from services.progression_engine import apply_deload, compute_set_weights, suggest_progression
from services.session_service import complete_session, log_set, start_session
from services.workout_service import get_plan
from schemas import Exercise, MobilityExercise, WorkoutPlan

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.get("/workouts/<id>/start")
def start(id):
    plan = get_plan(id)
    if not plan:
        return redirect(url_for("workouts.index"))

    exercises_list = list_exercises()
    exercises = {e["id"]: e for e in exercises_list}

    mobility_list = list_mobility()
    mobility = {m["id"]: m for m in mobility_list}

    # Convert to schema objects for optimizer and filler scheduling
    plan = dict(plan)
    entry_ex_ids = {e["exercise_id"] for e in plan.get("entries", [])}
    exercises_obj = {
        k: Exercise.from_dict(v)
        for k, v in exercises.items()
        if k in entry_ex_ids
    }

    # Apply smart optimizer (replaces basic ordering)
    auto_superset = request.args.get("auto_superset", "0") == "1"
    plan_obj = WorkoutPlan.from_dict(plan)
    plan_obj = optimize_workout(plan_obj, exercises_obj, auto_superset=auto_superset)

    # Apply filler scheduling
    mobility_obj_list = [MobilityExercise.from_dict(m) for m in mobility_list]
    plan_obj = schedule_fillers(plan_obj, exercises_obj, mobility_obj_list)

    # Sync back to plan dict
    plan = plan_obj.to_dict()

    # Progression suggestions (pass starting weight from plan entries)
    starting_weights = {
        e["exercise_id"]: e.get("starting_weight_kg")
        for e in plan["entries"]
    }
    suggestions = {}
    for ex_id, ex_obj in exercises_obj.items():
        sugg = suggest_progression(ex_obj, starting_weight_kg=starting_weights.get(ex_id))
        suggestions[ex_id] = dataclasses.asdict(sugg)

    # Per-set weight plans (warmup ramp + working weight)
    set_weight_plans = {}
    for entry in plan["entries"]:
        ex_id = entry["exercise_id"]
        ex_obj = exercises_obj.get(ex_id)
        sugg_dict = suggestions.get(ex_id)
        if ex_obj and sugg_dict and ex_obj.uses_weights and sugg_dict.get("suggested_weight_kg", 0) > 0:
            from services.progression_engine import ProgressionSuggestion, SetWeightPlan
            sugg_obj = ProgressionSuggestion(**sugg_dict)
            swp = compute_set_weights(
                sugg_obj,
                entry.get("sets", []),
                category=ex_obj.category.value,
            )
            set_weight_plans[ex_id] = dataclasses.asdict(swp)

    # Check deload
    is_deload = False
    deload_pct = 40
    active_program = get_active_program()
    if active_program:
        status = get_program_status(active_program)
        is_deload = status.get("is_deload", False)
        deload_pct = active_program.get("deload_volume_pct", 40)

    # Apply deload to sets if needed (S27)
    if is_deload:
        for entry in plan["entries"]:
            entry["sets"] = apply_deload(entry.get("sets", []), deload_pct)

    session_id = start_session(id)

    return render_template(
        "session/active.html",
        plan=plan,
        exercises=exercises,
        mobility=mobility,
        session_id=session_id,
        suggestions=suggestions,
        set_weight_plans=set_weight_plans,
        is_deload=is_deload,
        deload_pct=deload_pct,
    )


@sessions_bp.post("/session/complete")
def complete():
    """
    JSON body:
    {
        session_id: str,
        plan_id: str,
        duration_minutes: int,
        notes: str,
        sets: [{exercise_id, set_number, reps, weight_kg, rpe, is_warmup}]
    }
    """
    data = request.get_json(force=True)
    session_id = data["session_id"]
    plan_id = data["plan_id"]
    # Accept duration_minutes or duration_seconds from frontend
    duration_minutes = int(data.get("duration_minutes", 0))
    if not duration_minutes and data.get("duration_seconds"):
        duration_minutes = max(1, int(data["duration_seconds"]) // 60)
    notes = data.get("notes", "")

    for s in data.get("sets", data.get("logged_sets", [])):
        log_set(
            session_id=session_id,
            exercise_id=s["exercise_id"],
            set_number=s["set_number"],
            reps=s["reps"],
            weight_kg=s.get("weight_kg", 0),
            rpe=s.get("rpe"),
            is_warmup=s.get("is_warmup", False),
            duration_seconds=s.get("duration_seconds"),
        )

    complete_session(session_id, plan_id, duration_minutes, notes)
    return jsonify({"success": True})
