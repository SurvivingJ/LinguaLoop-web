"""WorkoutOS — JSON API Routes (S26)"""

from flask import Blueprint, jsonify

from services.body_weight_service import get_history, get_rolling_average
from services.exercise_service import list_exercises
from services.progression_service import list_progressions
from services.session_service import get_session_history

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/exercises")
def exercises():
    return jsonify(list_exercises())


@api_bp.get("/exercises/<id>/history")
def exercise_history(id):
    sets = get_session_history(exercise_id=id)
    return jsonify(sets)


@api_bp.get("/progressions")
def progressions():
    return jsonify(list_progressions())


@api_bp.get("/body-weight")
def body_weight():
    return jsonify({
        "history": get_history(),
        "rolling_avg": get_rolling_average(),
    })
