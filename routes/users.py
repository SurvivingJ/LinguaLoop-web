# routes/users.py
"""User routes — ELO ratings, token balance, profile."""

from flask import Blueprint, g
import logging

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from routes.common import get_db
from services.dimension_service import parse_language_id
from services.test_service import get_test_service
from utils.responses import api_errors, api_success, bad_request, not_found, ApiResponse
from utils.validation import json_body

logger = logging.getLogger(__name__)
users_bp = Blueprint("users", __name__)


@users_bp.route('/elo', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to get ELO ratings")
def get_user_elo_ratings() -> ApiResponse:
    """Get user's ELO ratings across all languages and skills."""
    ratings = get_test_service().get_user_elo_summary(g.current_user_id)
    return api_success({'ratings': ratings})


@users_bp.route('/tokens', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to get token balance")
def get_token_balance() -> ApiResponse:
    """Get user's current token balance, atomically granting daily free tokens."""
    user_id = g.current_user_id

    # Atomic RPC: grants daily free tokens if not yet granted today
    client = get_db()
    client.rpc('grant_daily_free_tokens', {'p_user_id': user_id}).execute()

    # Read updated balance
    user_result = client.table('users')\
        .select('tokens, last_free_token_date')\
        .eq('id', user_id)\
        .single()\
        .execute()

    if not user_result.data:
        return not_found("User not found")

    return api_success({
        "total_tokens": user_result.data.get('tokens', 0),
        "free_tokens_today": Config.DAILY_FREE_TOKENS,
        "last_free_token_date": user_result.data.get('last_free_token_date', ''),
    })


@users_bp.route('/profile', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to get profile")
def get_user_profile() -> ApiResponse:
    """Get user profile information."""
    user_id = g.current_user_id

    user_result = get_db().table('users')\
        .select(
            'id, email, display_name, email_verified, '
            'total_tests_taken, total_tests_generated, '
            'last_activity_at, subscription_tier_id, '
            'created_at, last_login'
        )\
        .eq('id', user_id)\
        .single()\
        .execute()

    if not user_result.data:
        return not_found("User not found")

    return api_success({"profile": user_result.data})


@users_bp.route('/preferences', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to fetch preferences")
def get_preferences() -> ApiResponse:
    """Return the user's exercise_preferences JSONB (or empty dict if unset)."""
    user_id = g.current_user_id
    resp = get_db().table('users') \
        .select('exercise_preferences') \
        .eq('id', user_id) \
        .single() \
        .execute()
    prefs = (resp.data or {}).get('exercise_preferences') or {}
    return api_success({"exercise_preferences": prefs})


@users_bp.route('/preferences', methods=['PATCH'])
@supabase_jwt_required
@api_errors("Failed to update preferences")
def update_preferences() -> ApiResponse:
    """Update user exercise preferences.

    Body: any of {"session_size": 15}, {"furigana_enabled": true},
    {"script_variant": "traditional"}.
    """
    user_id = g.current_user_id
    data = json_body(silent=True)
    if not data:
        return bad_request("Request body required")

    # Read current preferences
    user_resp = get_db().table('users') \
        .select('exercise_preferences') \
        .eq('id', user_id) \
        .single() \
        .execute()

    prefs = (user_resp.data or {}).get('exercise_preferences') or {}

    # Validate and merge session_size
    if 'session_size' in data:
        size = data['session_size']
        if not isinstance(size, int) or not (
            Config.MIN_EXERCISE_SESSION_SIZE <= size <= Config.MAX_EXERCISE_SESSION_SIZE
        ):
            return bad_request(
                f"session_size must be {Config.MIN_EXERCISE_SESSION_SIZE}-"
                f"{Config.MAX_EXERCISE_SESSION_SIZE}"
            )
        prefs['session_size'] = size

    if 'furigana_enabled' in data:
        if not isinstance(data['furigana_enabled'], bool):
            return bad_request("furigana_enabled must be boolean")
        prefs['furigana_enabled'] = data['furigana_enabled']

    # TASK-526. Chinese only in effect — the practice surface ignores it
    # for other languages — but stored unconditionally so a learner who
    # sets it while studying Japanese does not have it silently dropped.
    if 'script_variant' in data:
        from services.vocabulary_ladder.script_serving import VALID_VARIANTS
        if data['script_variant'] not in VALID_VARIANTS:
            return bad_request(
                f"script_variant must be one of {list(VALID_VARIANTS)}"
            )
        prefs['script_variant'] = data['script_variant']

    get_db().table('users') \
        .update({'exercise_preferences': prefs}) \
        .eq('id', user_id) \
        .execute()

    return api_success({"exercise_preferences": prefs})


@users_bp.route('/native-language', methods=['GET'])
@supabase_jwt_required
@api_errors("Failed to fetch native language")
def get_native_language() -> ApiResponse:
    """Return the user's native (L1) language id, or null if never set.

    NULL is a legitimate state for every existing user (no onboarding UI
    captured this before TASK-619) — callers must treat null as "not set",
    never as an error. Dual Translation falls back to English on null; see
    routes/dual_translation.py::_resolve_l1_language_id.
    """
    user_id = g.current_user_id
    resp = get_db().table('users') \
        .select('native_language_id') \
        .eq('id', user_id) \
        .single() \
        .execute()
    native_id = (resp.data or {}).get('native_language_id')
    return api_success({"native_language_id": native_id})


@users_bp.route('/native-language', methods=['PATCH'])
@supabase_jwt_required
@api_errors("Failed to update native language")
def update_native_language() -> ApiResponse:
    """Set the user's native (L1) language.

    Body: {"language_id": 1|2|3}. Validated against the supported set
    (Config.VALID_LANGUAGE_IDS, via parse_language_id) — anything outside it,
    or a non-integer, is rejected with 400. Writes the plain
    users.native_language_id column directly (not JSONB like preferences).
    """
    user_id = g.current_user_id
    data = json_body(silent=True)
    if 'language_id' not in data:
        return bad_request("language_id required")

    language_id = parse_language_id(data['language_id'])
    if language_id is None:
        return bad_request("language_id must be a supported language id")

    get_db().table('users') \
        .update({'native_language_id': language_id}) \
        .eq('id', user_id) \
        .execute()

    return api_success({"native_language_id": language_id})
