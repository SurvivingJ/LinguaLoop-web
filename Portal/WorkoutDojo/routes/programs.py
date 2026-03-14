"""WorkoutOS — Program Routes (S11)"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from services.program_service import (
    activate_program,
    delete_program,
    get_program,
    get_program_status,
    list_programs,
    save_program,
    update_program,
)
from services.workout_service import list_plans

programs_bp = Blueprint("programs", __name__, url_prefix="/programs")


@programs_bp.get("/")
def index():
    return render_template("programs/index.html", programs=list_programs())


@programs_bp.get("/new")
def new_form():
    return render_template(
        "programs/builder.html",
        program=None,
        plans=list_plans(),
    )


@programs_bp.get("/<id>/edit")
def edit_form(id):
    program = get_program(id)
    if not program:
        flash("Program not found.", "error")
        return redirect(url_for("programs.index"))
    return render_template(
        "programs/builder.html",
        program=program,
        plans=list_plans(),
    )


@programs_bp.post("/")
def create():
    data = request.get_json(force=True)
    program = save_program(data)
    return jsonify({"id": program["id"], "success": True})


@programs_bp.post("/<id>")
def update(id):
    data = request.get_json(force=True)
    result = update_program(id, data)
    if not result:
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({"success": True})


@programs_bp.post("/<id>/activate")
def activate(id):
    success = activate_program(id)
    return jsonify({"success": success})


@programs_bp.delete("/<id>")
def delete(id):
    return jsonify({"success": delete_program(id)})


@programs_bp.get("/<id>")
def detail(id):
    program = get_program(id)
    if not program:
        flash("Program not found.", "error")
        return redirect(url_for("programs.index"))
    status = get_program_status(program)
    plans = {p["id"]: p for p in list_plans()}
    return render_template(
        "programs/detail.html",
        program=program,
        status=status,
        plans=plans,
    )
