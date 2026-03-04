"""User report submission routes."""
from flask import Blueprint, request, jsonify, current_app, g
import logging
import traceback

from middleware.auth import jwt_required as supabase_jwt_required

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__)

VALID_CATEGORIES = [
    'test_answer_incorrect',
    'test_load_error',
    'website_crash',
    'improvement_idea',
    'audio_quality',
    'other'
]


@reports_bp.route('/submit', methods=['POST'])
@supabase_jwt_required
def submit_report():
    """Submit a user report with metadata."""
    try:
        user_id = g.supabase_claims.get('sub')
        if not user_id:
            return jsonify({"error": "User ID not found", "status": "error"}), 401

        data = request.get_json() or {}
        category = data.get('report_category')
        description = data.get('description', '').strip()

        if category not in VALID_CATEGORIES:
            return jsonify({"error": "Invalid category", "status": "error"}), 400
        if len(description) < 10:
            return jsonify({"error": "Description too short", "status": "error"}), 400

        result = current_app.supabase_service.table('user_reports').insert({
            'user_id': user_id,
            'report_category': category,
            'description': description,
            'current_page': data.get('current_page', ''),
            'test_id': data.get('test_id'),
            'test_type': data.get('test_type'),
            'user_agent': data.get('user_agent', ''),
            'screen_resolution': data.get('screen_resolution', ''),
            'status': 'pending'
        }).execute()

        if not result.data:
            raise Exception("Insert failed")

        logger.info(f"Report submitted: user={user_id}, category={category}")
        return jsonify({"status": "success", "report_id": result.data[0]['id']}), 201

    except Exception as e:
        logger.error(f"Report error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "status": "error"}), 500
