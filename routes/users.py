# routes/users.py
"""User routes — ELO ratings, token balance, profile."""

from flask import Blueprint, current_app, g, request
import logging
import traceback

from config import Config
from middleware.auth import jwt_required as supabase_jwt_required
from services.test_service import get_test_service
from utils.responses import api_success, bad_request, not_found, server_error, ApiResponse

logger = logging.getLogger(__name__)
users_bp = Blueprint("users", __name__)


@users_bp.route('/elo', methods=['GET'])
@supabase_jwt_required
def get_user_elo_ratings() -> ApiResponse:
    """Get user's ELO ratings across all languages and skills."""
    try:
        ratings = get_test_service().get_user_elo_summary(g.current_user_id)
        return api_success({'ratings': ratings})
    except Exception as e:
        logger.error(f"Error getting user ELO: {e}")
        logger.error(traceback.format_exc())
        return server_error("Failed to get ELO ratings")


@users_bp.route('/tokens', methods=['GET'])
@supabase_jwt_required
def get_token_balance() -> ApiResponse:
    """Get user's current token balance, atomically granting daily free tokens."""
    try:
        user_id = g.current_user_id

        # Atomic RPC: grants daily free tokens if not yet granted today
        client = current_app.supabase_service or current_app.supabase
        client.rpc('grant_daily_free_tokens', {'p_user_id': user_id}).execute()

        # Read updated balance
        user_result = current_app.supabase.table('users')\
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
    except Exception as e:
        logger.error(f"Token balance error: {e}")
        return server_error("Failed to get token balance")


@users_bp.route('/profile', methods=['GET'])
@supabase_jwt_required
def get_user_profile() -> ApiResponse:
    """Get user profile information."""
    try:
        user_id = g.current_user_id

        user_result = current_app.supabase.table('users')\
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
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return server_error("Failed to get profile")


@users_bp.route('/preferences', methods=['PATCH'])
@supabase_jwt_required
def update_preferences() -> ApiResponse:
    """Update user exercise preferences.

    Body: {"session_size": 15}
    """
    try:
        user_id = g.current_user_id
        data = request.get_json()
        if not data:
            return bad_request("Request body required")

        # Read current preferences
        user_resp = current_app.supabase_service.table('users') \
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

        current_app.supabase_service.table('users') \
            .update({'exercise_preferences': prefs}) \
            .eq('id', user_id) \
            .execute()

        return api_success({"exercise_preferences": prefs})

    except Exception as e:
        logger.error(f"Preferences update error: {e}")
        return server_error("Failed to update preferences")
