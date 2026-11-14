"""User report submission routes."""
from flask import Blueprint, g
import logging

from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import get_db
from utils.responses import api_errors, ApiResponse, api_success, bad_request
from utils.validation import json_body

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
@api_errors("Failed to submit report")
def submit_report() -> ApiResponse:
    """Submit a user report with metadata."""
    user_id = g.current_user_id

    data = json_body()
    category = data.get('report_category')
    description = data.get('description', '').strip()

    if category not in VALID_CATEGORIES:
        return bad_request("Invalid category")
    if len(description) < 10:
        return bad_request("Description too short")

    result = get_db().table('user_reports').insert({
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
    return api_success({"report_id": result.data[0]['id']}, status_code=201)
