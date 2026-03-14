"""WorkoutOS — Flask Application Entry Point"""

import os

from flask import Flask, render_template

from routes.exercises import exercises_bp
from routes.workouts import workouts_bp
from routes.programs import programs_bp
from routes.sessions import sessions_bp
from routes.body_weight import body_weight_bp
from routes.analytics import analytics_bp
from routes.progressions import progressions_bp
from routes.api import api_bp

from services.body_weight_service import get_history
from services.program_service import get_active_program, get_program_status
from services.session_service import get_recent_sessions
from services.workout_service import get_plan


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "workoutos-dev-secret")
    app.config["DEBUG"] = os.environ.get("DEBUG", "true").lower() == "true"

    # Register blueprints
    app.register_blueprint(exercises_bp)
    app.register_blueprint(workouts_bp)
    app.register_blueprint(programs_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(body_weight_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(progressions_bp)
    app.register_blueprint(api_bp)

    # Dashboard
    @app.get("/")
    def dashboard():
        active_program = get_active_program()
        program_status = None
        today_plan = None

        if active_program:
            program_status = get_program_status(active_program)
            today_entry = program_status.get("today_entry")
            if today_entry and isinstance(today_entry, dict):
                plan_id = today_entry.get("plan_id")
                if plan_id:
                    today_plan = get_plan(plan_id)

        recent_sessions = get_recent_sessions(limit=5)
        bw_history = get_history()
        latest_bw = bw_history[-1] if bw_history else None

        return render_template(
            "dashboard.html",
            active_program=active_program,
            program_status=program_status,
            today_plan=today_plan,
            recent_sessions=recent_sessions,
            latest_bw=latest_bw,
        )

    @app.get("/settings")
    def settings():
        return render_template("settings.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
