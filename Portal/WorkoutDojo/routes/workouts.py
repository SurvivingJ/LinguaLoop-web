"""WorkoutOS — Workout Plan Routes (S8)"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from services.exercise_service import list_exercises, list_mobility
from services.workout_service import (
    delete_plan,
    get_plan,
    list_plans,
    save_plan,
    update_plan,
)

workouts_bp = Blueprint("workouts", __name__, url_prefix="/workouts")


@workouts_bp.get("/")
def index():
    return render_template("workouts/index.html", plans=list_plans())


@workouts_bp.get("/new")
def new_form():
    return render_template(
        "workouts/builder.html",
        plan=None,
        exercises=list_exercises(),
        mobility=list_mobility(),
    )


@workouts_bp.get("/<id>/edit")
def edit_form(id):
    plan = get_plan(id)
    if not plan:
        flash("Workout not found.", "error")
        return redirect(url_for("workouts.index"))
    return render_template(
        "workouts/builder.html",
        plan=plan,
        exercises=list_exercises(),
        mobility=list_mobility(),
    )


@workouts_bp.post("/")
def create():
    data = request.get_json(force=True)
    plan = save_plan(data)
    return jsonify({"id": plan["id"], "success": True})


@workouts_bp.post("/<id>")
def update(id):
    data = request.get_json(force=True)
    result = update_plan(id, data)
    if not result:
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({"success": True})


@workouts_bp.delete("/<id>")
def delete(id):
    return jsonify({"success": delete_plan(id)})
