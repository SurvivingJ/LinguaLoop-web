# routes/dt_repair.py
"""Guided self-repair endpoints (wiki/features/dt-guided-self-repair.tech.md section 4).

Mounted at /api/dual-translation/repair. Thin: authenticate, check the feature
flag, parse, call ``services.dual_translation.repair.service`` (which checks
ownership and every rule), shape the response.

  GET  /submissions/<id>/session   read / resume the repair session
  GET  /submissions/<id>/result    the full grade contract, once the session is finished
  POST /items/<id>/open            start (or resume) a step / daily sitting
  POST /items/<id>/hint            next hint rung
  POST /items/<id>/check           re-check a revision (one model call at most)
  POST /items/<id>/reveal          show the answer
  POST /items/<id>/dispute         "Mine is fine"
  POST /items/<id>/skip            skip a daily-practice item
  POST /sessions/<id>/finish       end the repair pass
  GET  /practice/due               today's daily-practice items
"""

import logging

from flask import Blueprint, current_app, g, request

from middleware.auth import jwt_required as supabase_jwt_required
from services.dual_translation.repair import service, settings
from utils.responses import ApiResponse, api_error, api_success

logger = logging.getLogger(__name__)
dt_repair_bp = Blueprint("dt_repair", __name__)


def _run(fn, *args):
    if not settings.DT_GUIDED_REPAIR:
        return api_error("Guided repair is turned off", 503, error_code="REPAIR_DISABLED")
    db = current_app.supabase_service
    if not db:
        return api_error("Database service not configured", 500, error_code="SERVER_ERROR")
    try:
        return api_success(fn(db, g.current_user_id, *args))
    except service.RepairError as e:
        return api_error(e.message, e.status, error_code=e.code)
    except Exception as e:  # noqa: BLE001
        logger.error("dt_repair %s failed: %s", getattr(fn, "__name__", fn), e, exc_info=True)
        return api_error("Something went wrong", 500, error_code="SERVER_ERROR")


def _body() -> dict:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


@dt_repair_bp.route('/submissions/<int:submission_id>/session', methods=['GET'])
@supabase_jwt_required
def get_session(submission_id: int) -> ApiResponse:
    return _run(lambda db, uid: {"session": service.get_session(db, uid, submission_id)})


@dt_repair_bp.route('/submissions/<int:submission_id>/result', methods=['GET'])
@supabase_jwt_required
def get_result(submission_id: int) -> ApiResponse:
    return _run(service.full_result, submission_id)


@dt_repair_bp.route('/items/<int:item_id>/open', methods=['POST'])
@supabase_jwt_required
def open_item(item_id: int) -> ApiResponse:
    return _run(service.open_item, item_id, _body())


@dt_repair_bp.route('/items/<int:item_id>/hint', methods=['POST'])
@supabase_jwt_required
def hint(item_id: int) -> ApiResponse:
    return _run(service.next_hint, item_id, _body())


@dt_repair_bp.route('/items/<int:item_id>/check', methods=['POST'])
@supabase_jwt_required
def check(item_id: int) -> ApiResponse:
    return _run(service.check, item_id, _body())


@dt_repair_bp.route('/items/<int:item_id>/reveal', methods=['POST'])
@supabase_jwt_required
def reveal(item_id: int) -> ApiResponse:
    return _run(service.reveal, item_id, _body())


@dt_repair_bp.route('/items/<int:item_id>/dispute', methods=['POST'])
@supabase_jwt_required
def dispute(item_id: int) -> ApiResponse:
    return _run(service.dispute, item_id, _body())


@dt_repair_bp.route('/items/<int:item_id>/skip', methods=['POST'])
@supabase_jwt_required
def skip(item_id: int) -> ApiResponse:
    return _run(service.skip, item_id, _body())


@dt_repair_bp.route('/sessions/<int:session_id>/finish', methods=['POST'])
@supabase_jwt_required
def finish(session_id: int) -> ApiResponse:
    return _run(service.finish, session_id, _body())


@dt_repair_bp.route('/practice/due', methods=['GET'])
@supabase_jwt_required
def practice_due() -> ApiResponse:
    raw = request.args.get('language_id')
    try:
        language_id = int(raw)
    except (TypeError, ValueError):
        if not settings.DT_GUIDED_REPAIR:
            return api_error("Guided repair is turned off", 503, error_code="REPAIR_DISABLED")
        return api_error("language_id must be an integer", 400, error_code="BAD_REQUEST")
    return _run(service.practice_due, language_id)
