"""WorkoutOS — Analytics Routes (S25)"""

from flask import Blueprint, render_template

from services.body_weight_service import get_history, get_rolling_average
from services.session_service import get_recent_sessions

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.get("/")
def index():
    return render_template(
        "analytics/index.html",
        body_weight_history=get_history(),
        rolling_avg=get_rolling_average(),
        recent_sessions=get_recent_sessions(limit=30),
    )
