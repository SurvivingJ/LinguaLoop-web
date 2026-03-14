"""WorkoutOS — Body Weight Routes (S24)"""

from flask import Blueprint, flash, redirect, request, url_for

from services.body_weight_service import log_weight

body_weight_bp = Blueprint("body_weight", __name__)


@body_weight_bp.post("/body-weight")
def log():
    weight_kg = request.form.get("weight_kg", type=float)
    if not weight_kg or weight_kg <= 0:
        flash("Please enter a valid weight.", "error")
        return redirect(url_for("dashboard"))

    time_of_day = request.form.get("time_of_day", "morning")
    notes = request.form.get("notes", "")
    log_weight(weight_kg, time_of_day, notes)
    flash(f"Weight {weight_kg} kg logged.", "success")
    return redirect(url_for("dashboard"))
