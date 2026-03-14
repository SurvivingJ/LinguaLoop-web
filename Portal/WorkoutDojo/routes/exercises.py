"""WorkoutOS — Exercise Routes (S6)"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from services.exercise_service import (
    delete_exercise,
    get_exercise,
    list_exercises,
    list_mobility,
    save_exercise,
    update_exercise,
)
from services.progression_service import (
    get_progression_for_exercise,
    list_progression_names,
)

exercises_bp = Blueprint("exercises", __name__, url_prefix="/exercises")


def _form_to_exercise(form: dict) -> dict:
    """Normalize multiselect fields from HTML form."""
    data = dict(form)
    # Convert comma-separated or multi-value fields
    for field in ("primary_muscles", "secondary_muscles"):
        if field in data and isinstance(data[field], str):
            data[field] = [v.strip() for v in data[field].split(",") if v.strip()]
    data["is_compound"] = data.get("category") == "barbell_compound"
    return data


@exercises_bp.get("/")
def index():
    exercises = list_exercises()
    # Attach progression group info to each exercise for badge display
    for e in exercises:
        pg = get_progression_for_exercise(e["id"])
        e["_progression_name"] = pg["name"] if pg else None
    return render_template("exercises/index.html", exercises=exercises)


@exercises_bp.get("/new")
def new_form():
    return render_template(
        "exercises/form.html",
        exercise=None,
        progression_names=list_progression_names(),
    )


@exercises_bp.get("/<id>/edit")
def edit_form(id):
    exercise = get_exercise(id)
    if not exercise:
        flash("Exercise not found.", "error")
        return redirect(url_for("exercises.index"))
    pg = get_progression_for_exercise(id)
    return render_template(
        "exercises/form.html",
        exercise=exercise,
        progression_names=list_progression_names(),
        current_progression=pg,
    )


@exercises_bp.post("/")
def create():
    data = _form_to_exercise(request.form.to_dict(flat=True))
    # Handle multi-value selects (browsers send multiple values)
    data["primary_muscles"] = request.form.getlist("primary_muscles")
    data["secondary_muscles"] = request.form.getlist("secondary_muscles")
    data["is_compound"] = data.get("category") == "barbell_compound"
    data["uses_weights"] = "uses_weights" in request.form
    save_exercise(data)
    flash("Exercise saved.", "success")
    return redirect(url_for("exercises.index"))


@exercises_bp.post("/<id>")
def update(id):
    data = request.form.to_dict(flat=True)
    data["primary_muscles"] = request.form.getlist("primary_muscles")
    data["secondary_muscles"] = request.form.getlist("secondary_muscles")
    data["is_compound"] = data.get("category") == "barbell_compound"
    data["uses_weights"] = "uses_weights" in request.form
    result = update_exercise(id, data)
    if not result:
        flash("Exercise not found.", "error")
    else:
        flash("Exercise updated.", "success")
    return redirect(url_for("exercises.index"))


@exercises_bp.delete("/<id>")
def delete(id):
    success = delete_exercise(id)
    return jsonify({"success": success})
