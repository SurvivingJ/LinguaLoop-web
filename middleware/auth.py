# middleware/auth.py
"""
Consolidated authentication middleware.
Provides both class-based and standalone decorator functions.
"""

from functools import wraps
from flask import request, jsonify, g
import os
import logging

logger = logging.getLogger(__name__)


def _extract_token(req):
    """Extract JWT token from Authorization header"""
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None


def _get_supabase_client():
    """Get Supabase client from factory (lazy import to avoid circular deps)"""
    from ..services.supabase_factory import get_supabase, get_supabase_admin
    return get_supabase()


# ============================================================================
# STANDALONE DECORATORS - Use these for most routes
# ============================================================================

def jwt_required(f):
    """
    Decorator for endpoints requiring JWT authentication.
    Uses the centralized SupabaseFactory.

    Sets:
        g.current_user_id: The authenticated user's ID
        g.current_user: The full user object from Supabase
        g.supabase_claims: Dict with user claims (sub, email, role)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token(request)
        if not token:
            return jsonify({'error': 'Token missing'}), 401

        try:
            # Check for service role key (batch operations)
            service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            if service_role_key and token == service_role_key:
                g.supabase_claims = {
                    'sub': 'service-account',
                    'role': 'service_role',
                    'email': 'batch-service@internal'
                }
                g.current_user_id = 'service-account'
                g.user_id = 'service-account'
                return f(*args, **kwargs)

            # Verify with Supabase Auth
            supabase = _get_supabase_client()
            user_response = supabase.auth.get_user(token)

            if not user_response or not user_response.user:
                return jsonify({'error': 'Invalid or expired token'}), 401

            # Set all the context variables for compatibility
            g.current_user_id = user_response.user.id
            g.current_user = user_response.user
            g.user_id = user_response.user.id
            g.supabase_claims = {
                'sub': user_response.user.id,
                'email': user_response.user.email,
                'role': 'authenticated',
                'aud': 'authenticated'
            }

            logger.debug(f"User authenticated: {user_response.user.id}")

        except Exception as e:
            logger.error(f'JWT validation failed: {e}')
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """
    Decorator for admin-only endpoints.
    Checks subscription_tier for 'admin' or 'moderator'.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token(request)
        if not token:
            return jsonify({'error': 'Token missing'}), 401

        try:
            supabase = _get_supabase_client()
            user_response = supabase.auth.get_user(token)

            if not user_response or not user_response.user:
                return jsonify({'error': 'Invalid token'}), 401

            g.current_user_id = user_response.user.id
            g.current_user = user_response.user

            # Check admin status using admin client to bypass RLS
            logger.debug(f"[AUTH] Checking admin status for user_id={user_response.user.id}")
            supabase_admin = get_supabase_admin()
            result = supabase_admin.table('users')\
                .select('subscription_tier')\
                .eq('id', user_response.user.id)\
                .execute()

            if not result.data or result.data[0]['subscription_tier'] not in ['admin', 'moderator']:
                logger.warning(f"[AUTH] Admin access denied for user_id={user_response.user.id}")
                return jsonify({'error': 'Admin access required'}), 403

            logger.info(f"[AUTH] Admin access granted for user_id={user_response.user.id}")

        except Exception as e:
            logger.error(f'Admin auth failed: {e}')
            return jsonify({'error': 'Access denied'}), 403

        return f(*args, **kwargs)
    return decorated


def tier_required(required_tiers: list):
    """
    Decorator for subscription tier-based access.

    Args:
        required_tiers: List of allowed tiers (e.g., ['premium', 'admin'])
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = _extract_token(request)
            if not token:
                return jsonify({'error': 'Token missing'}), 401

            try:
                supabase = _get_supabase_client()
                user_response = supabase.auth.get_user(token)

                if not user_response or not user_response.user:
                    return jsonify({'error': 'Invalid token'}), 401

                g.current_user_id = user_response.user.id

                # Check tier using admin client to bypass RLS
                logger.debug(f"[AUTH] Checking tier for user_id={user_response.user.id}, required_tiers={required_tiers}")
                supabase_admin = get_supabase_admin()
                result = supabase_admin.table('users')\
                    .select('subscription_tier')\
                    .eq('id', user_response.user.id)\
                    .execute()

                if not result.data or result.data[0]['subscription_tier'] not in required_tiers:
                    logger.warning(f"[AUTH] Tier access denied for user_id={user_response.user.id}, has tier={result.data[0]['subscription_tier'] if result.data else 'unknown'}")
                    return jsonify({'error': f'Requires {" or ".join(required_tiers)} access'}), 403

                logger.info(f"[AUTH] Tier access granted for user_id={user_response.user.id}")

            except Exception as e:
                logger.error(f'Tier auth failed: {e}')
                return jsonify({'error': 'Access denied'}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


# ============================================================================
# CLASS-BASED MIDDLEWARE - For backwards compatibility with existing code
# ============================================================================

class AuthMiddleware:
    """
    Class-based auth middleware for backwards compatibility.
    New code should use the standalone decorators above.
    """

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        # Get admin client from factory for privileged operations
        self.supabase_admin = get_supabase_admin()

    def jwt_required(self, f):
        """Decorator for endpoints requiring authentication"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = _extract_token(request)
            if not token:
                return jsonify({'error': 'Token missing'}), 401

            try:
                user = self.supabase.auth.get_user(token)
                g.current_user_id = user.user.id
                g.current_user = user.user
            except Exception as e:
                return jsonify({'error': 'Invalid token'}), 401

            return f(*args, **kwargs)
        return decorated

    def admin_required(self, f):
        """Decorator for admin-only endpoints"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = _extract_token(request)
            if not token:
                return jsonify({'error': 'Token missing'}), 401

            try:
                user = self.supabase.auth.get_user(token)
                g.current_user_id = user.user.id

                # Check admin status using admin client to bypass RLS
                logger.debug(f"[AUTH] Class-based admin check for user_id={user.user.id}")
                result = self.supabase_admin.table('users')\
                    .select('subscription_tier')\
                    .eq('id', user.user.id)\
                    .execute()

                if not result.data or result.data[0]['subscription_tier'] not in ['admin', 'moderator']:
                    logger.warning(f"[AUTH] Admin access denied for user_id={user.user.id}")
                    return jsonify({'error': 'Admin access required'}), 403

                logger.info(f"[AUTH] Admin access granted (class-based) for user_id={user.user.id}")

            except Exception as e:
                return jsonify({'error': 'Access denied'}), 403

            return f(*args, **kwargs)
        return decorated

    def tier_required(self, required_tiers: list):
        """Decorator for subscription tier-based access"""
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                token = _extract_token(request)
                if not token:
                    return jsonify({'error': 'Token missing'}), 401

                try:
                    user = self.supabase.auth.get_user(token)
                    g.current_user_id = user.user.id

                    # Check tier using admin client to bypass RLS
                    logger.debug(f"[AUTH] Class-based tier check for user_id={user.user.id}, required_tiers={required_tiers}")
                    result = self.supabase_admin.table('users')\
                        .select('subscription_tier')\
                        .eq('id', user.user.id)\
                        .execute()

                    if not result.data or result.data[0]['subscription_tier'] not in required_tiers:
                        logger.warning(f"[AUTH] Tier access denied for user_id={user.user.id}, has tier={result.data[0]['subscription_tier'] if result.data else 'unknown'}")
                        return jsonify({'error': f'Requires {" or ".join(required_tiers)} access'}), 403

                    logger.info(f"[AUTH] Tier access granted (class-based) for user_id={user.user.id}")

                except Exception as e:
                    return jsonify({'error': 'Access denied'}), 403

                return f(*args, **kwargs)
            return decorated
        return decorator
