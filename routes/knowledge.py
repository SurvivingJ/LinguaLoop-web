# routes/knowledge.py
"""Knowledge Report ("My vocabulary") API — wiki/features/knowledge-report.tech.md §6.2.

``GET /api/knowledge/summary``              the §6.3 summary (all tiers; TASK-1039)
``GET /api/knowledge/prestudy-suggestion``  next-step rule 2 (all tiers; TASK-1041)

The Pro routes (``/words``, ``/words/<vocab_id>/<sense_rank>``, ``/lists/<code>/words``,
``/export``) are added by TASK-1045 – TASK-1049 with ``knowledge_report.entitlement_gate`` and the
``knowledge_pro_intent`` log.

Every route: JWT → ``api_errors`` → ``require_language_id`` → learner guard (a non-UUID identity,
e.g. the batch service token, gets 403) → language ∈ {1, 2, 3} → ``KNOWLEDGE_REPORT_ENABLED`` (404
when off). The user id sent to an RPC is always ``g.current_user_id``. Every response is
``Cache-Control: private, no-store``.
"""

import logging
import uuid

from flask import Blueprint, current_app, g

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import get_db
from services.vocabulary import knowledge_report
from utils.responses import (
    ApiResponse, api_errors, api_success, bad_request, forbidden, not_found, service_unavailable,
)
from utils.validation import require_language_id

logger = logging.getLogger(__name__)

knowledge_bp = Blueprint('knowledge', __name__)


@knowledge_bp.after_request
def _private_no_store(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def report_enabled() -> bool:
    """The flag as the app was configured (tests set ``app.config``); templates read the same key."""
    return bool(current_app.config.get('KNOWLEDGE_REPORT_ENABLED', Config.KNOWLEDGE_REPORT_ENABLED))


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def _guard(language_id: int):
    """None when the request may proceed, else the error response (tech §6.2 order)."""
    if not _is_uuid(getattr(g, 'current_user_id', None)):
        return forbidden('Learner token required')
    if language_id not in Config.VALID_LANGUAGE_IDS:
        return bad_request('Unsupported language_id')
    if not report_enabled():
        return not_found('Not found')
    return None


@knowledge_bp.route('/summary', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load your vocabulary summary")
@require_language_id
def summary(language_id: int) -> ApiResponse:
    blocked = _guard(language_id)
    if blocked:
        return blocked
    payload = knowledge_report.summary(get_db(), g.current_user_id, language_id)
    if payload is None:
        return service_unavailable('The vocabulary report is not available yet')
    return api_success(payload)


@knowledge_bp.route('/prestudy-suggestion', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load a prestudy suggestion")
@require_language_id
def prestudy_suggestion(language_id: int) -> ApiResponse:
    blocked = _guard(language_id)
    if blocked:
        return blocked
    suggestion = knowledge_report.prestudy_suggestion(get_db(), g.current_user_id, language_id)
    return api_success({'suggestion': suggestion})
