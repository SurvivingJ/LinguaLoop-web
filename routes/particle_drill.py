"""Particle drill API (Japanese).

  GET /api/particle-drill/catalog?language_id=3        stages, groups, skills with counts
  GET /api/particle-drill/skill/<id>?language_id=3     guide + exercise bank + pattern packs
  GET /api/particle-drill/conjugation?language_id=3    conjugation guides + word lists
  GET /api/particle-drill/conjugation/words?language_id=3   the learner's own verbs and adjectives
  GET /api/particle-drill/progress?language_id=3       the learner's stored ladder state
  PUT /api/particle-drill/progress                     body: {language_id, state}

The content is static (services/particle_drill/content.py); exercises are
built and judged in the browser, so a drill round makes no request at all.
"""
import logging

from flask import Blueprint, g, make_response, request

from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import get_db
from services.particle_drill import conjugation, progress
from services.particle_drill.content import get_content
from utils.responses import ApiResponse, api_errors, api_success, bad_request, not_found
from utils.validation import json_body, require_language_id

logger = logging.getLogger(__name__)

particle_drill_bp = Blueprint('particle_drill', __name__)

WRONG_LANGUAGE = "The particle drill is Japanese-only"


def _cached(payload: dict, version: str) -> ApiResponse:
    """Static content: the browser may reuse it for an hour and revalidate by version."""
    etag = f'"pd-{version}"'
    if request.headers.get('If-None-Match') == etag:
        resp = make_response('', 304)
    else:
        resp, _status = api_success(payload)
    resp.headers['ETag'] = etag
    resp.headers['Cache-Control'] = 'private, max-age=3600'
    return resp, resp.status_code


def _course_content(language_id: int):
    """The content of the course named by ?course= (particles by default)."""
    return get_content(language_id, request.args.get('course') or None)


@particle_drill_bp.route('/reading', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load the reading drill")
@require_language_id
def get_reading(language_id: int) -> ApiResponse:
    content = get_content(language_id, 'grammar')
    if content is None:
        return bad_request(WRONG_LANGUAGE)
    return _cached(content.reading_payload(), f'{content.version()}-reading')


@particle_drill_bp.route('/catalog', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load the particle drill")
@require_language_id
def get_catalog(language_id: int) -> ApiResponse:
    content = _course_content(language_id)
    if content is None:
        return bad_request(WRONG_LANGUAGE)
    return _cached(content.catalog_payload(), content.version())


@particle_drill_bp.route('/skill/<skill_id>', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load the particle skill")
@require_language_id
def get_skill(skill_id: str, language_id: int) -> ApiResponse:
    content = _course_content(language_id)
    if content is None:
        return bad_request(WRONG_LANGUAGE)
    payload = content.skill_payload(skill_id)
    if payload is None:
        return not_found("Unknown particle skill")
    return _cached(payload, f'{content.version()}-{skill_id}')


@particle_drill_bp.route('/conjugation', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load the conjugation drill")
@require_language_id
def get_conjugation(language_id: int) -> ApiResponse:
    content = get_content(language_id)
    if content is None:
        return bad_request(WRONG_LANGUAGE)
    return _cached(content.conjugation_payload(), f'{content.version()}-conj')


def _gloss_language_id(db, user_id: str) -> int:
    """The language the learner reads glosses in (users.native_language_id), else English."""
    try:
        rows = db.table('users').select('native_language_id').eq('id', user_id).limit(1).execute().data
        value = rows[0].get('native_language_id') if rows else None
        return value if isinstance(value, int) and value != 3 else conjugation.ENGLISH_ID
    except Exception:  # noqa: BLE001 - a gloss in English is better than no drill
        logger.exception("could not read native_language_id")
        return conjugation.ENGLISH_ID


@particle_drill_bp.route('/conjugation/words', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load your words for the conjugation drill")
@require_language_id
def get_conjugation_words(language_id: int) -> ApiResponse:
    """The verbs and adjectives this learner knows, classified for the conjugation engine."""
    content = get_content(language_id)
    if content is None:
        return bad_request(WRONG_LANGUAGE)
    db = get_db()
    return api_success(conjugation.known_words(
        db, g.current_user_id, language_id, content.conjugation_payload(),
        gloss_language_id=_gloss_language_id(db, g.current_user_id)))


@particle_drill_bp.route('/progress', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to load particle drill progress")
@require_language_id
def get_progress(language_id: int) -> ApiResponse:
    if get_content(language_id) is None:
        return bad_request(WRONG_LANGUAGE)
    return api_success(progress.load(get_db(), g.current_user_id))


@particle_drill_bp.route('/progress', methods=['PUT'])
@supabase_jwt_required
@api_errors("Failed to save particle drill progress")
def put_progress() -> ApiResponse:
    data = json_body()
    language_id = data.get('language_id')
    if not isinstance(language_id, int) or get_content(language_id) is None:
        return bad_request(WRONG_LANGUAGE)
    state = data.get('state')
    error = progress.validate_state(state)
    if error:
        return bad_request(error)
    return api_success(progress.save(get_db(), g.current_user_id, state))
