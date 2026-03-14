"""WorkoutOS — Progression Group Routes"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from services.exercise_service import list_exercises
from services.progression_service import (
    delete_progression,
    get_progression,
    list_progressions,
    save_progression,
    update_progression,
)

progressions_bp = Blueprint("progressions", __name__, url_prefix="/progressions")


@progressions_bp.get("/")
def index():
    progressions = list_progressions()
    exercises = {e["id"]: e for e in list_exercises()}
    return render_template(
        "progressions/index.html",
        progressions=progressions,
        exercises=exercises,
    )


@progressions_bp.get("/new")
def new_form():
    return render_template(
        "progressions/builder.html",
        progression=None,
        exercises=list_exercises(),
    )


@progressions_bp.get("/<id>/edit")
def edit_form(id):
    progression = get_progression(id)
    if not progression:
        flash("Progression not found.", "error")
        return redirect(url_for("progressions.index"))
    return render_template(
        "progressions/builder.html",
        progression=progression,
        exercises=list_exercises(),
    )


@progressions_bp.post("/")
def create():
    data = request.get_json(force=True)
    progression = save_progression(data)
    return jsonify({"id": progression["id"], "success": True})


@progressions_bp.post("/<id>")
def update(id):
    data = request.get_json(force=True)
    result = update_progression(id, data)
    if not result:
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({"success": True})


@progressions_bp.delete("/<id>")
def delete(id):
    return jsonify({"success": delete_progression(id)})
