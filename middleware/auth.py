# middleware/auth.py
"""
Consolidated authentication middleware.

Three decorators (`jwt_required`, `admin_required`, `tier_required`) share a
single `_authenticate` helper. This keeps the service-role JWT bypass
symmetric across all three (HI-02) — previously only `jwt_required` had it,
so batch jobs hitting an admin/tier endpoint silently 401'd.
"""

from functools import wraps
from flask import request, jsonify, g
from gotrue.errors import AuthApiError, AuthRetryableError
import hmac
import os
import logging

logger = logging.getLogger(__name__)


def _extract_token(req):
    """Extract JWT token from Authorization header."""
    auth_header = req.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None


def _get_supabase_client():
    """Get Supabase client from factory (lazy import to avoid circular deps)."""
    from services.supabase_factory import get_supabase
    return get_supabase()


def _get_supabase_admin():
    """Get admin Supabase client from factory (lazy import to avoid circular deps)."""
    from services.supabase_factory import get_supabase_admin
    return get_supabase_admin()


# ============================================================================
# Shared authentication helper — single source of truth for HI-01 / HI-02
# ============================================================================

def _authenticate(token):
    """Resolve a bearer token to Supabase claims.

    Returns ``(claims, error_response)``:
      - on success: ``(claims_dict, None)``
      - on failure: ``(None, (flask_response, status_code))``
    """
    if not token:
        return None, (jsonify({'error': 'Token missing'}), 401)

    # Service-role bypass — shared across jwt/admin/tier decorators (HI-02).
    # TODO: replace with a dedicated batch-service credential. With the bypass
    # now symmetric, a leak of SUPABASE_SERVICE_ROLE_KEY exposes admin/tier
    # endpoints too, not just jwt_required.
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if service_role_key and hmac.compare_digest(token, service_role_key):
        logger.info('Service-role bypass used on %s', request.path)
        return {
            'sub': 'service-account',
            'email': 'batch-service@internal',
            'role': 'service_role',
            'user': None,
        }, None

    try:
        user_response = _get_supabase_client().auth.get_user(token)
        if not user_response or not user_response.user:
            return None, (jsonify({'error': 'Invalid or expired token'}), 401)
        user = user_response.user
        return {
            'sub': user.id,
            'email': user.email,
            'role': 'authenticated',
            'aud': 'authenticated',
            'user': user,
        }, None
    except AuthApiError as e:
        logger.warning('Auth API error: %s', e.message)
        return None, (jsonify({'error': 'Invalid or expired token'}), 401)
    except AuthRetryableError as e:
        logger.error('Auth service temporarily unavailable: %s', e)
        return None, (jsonify({'error': 'Authentication service unavailable'}), 503)
    except Exception as e:
        logger.error('JWT validation failed: %s', e, exc_info=True)
        return None, (jsonify({'error': 'Invalid token'}), 401)


def _set_user_context(claims):
    """Populate Flask ``g`` with the same fields the legacy decorators set."""
    g.supabase_claims = claims
    g.current_user_id = claims['sub']
    g.user_id = claims['sub']
    if claims.get('user') is not None:
        g.current_user = claims['user']


def _user_has_tier(user_id, allowed):
    """True iff the user's subscription_tier is in ``allowed``."""
    result = _get_supabase_admin().table('users')\
        .select('subscription_tier').eq('id', user_id).execute()
    if not result.data:
        return False
    return result.data[0]['subscription_tier'] in allowed


# ============================================================================
# Decorators
# ============================================================================

def jwt_required(f):
    """Endpoint requires a valid JWT (or the service-role key)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        claims, err = _authenticate(_extract_token(request))
        if err:
            return err
        _set_user_context(claims)
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Endpoint requires admin/moderator tier — service-role bypass honoured."""
    @wraps(f)
    def decorated(*args, **kwargs):
        claims, err = _authenticate(_extract_token(request))
        if err:
            return err
        _set_user_context(claims)

        if claims['role'] == 'service_role':
            return f(*args, **kwargs)

        if not _user_has_tier(claims['sub'], ('admin', 'moderator')):
            logger.warning('[AUTH] Admin access denied for user_id=%s', claims['sub'])
            return jsonify({'error': 'Admin access required'}), 403

        logger.info('[AUTH] Admin access granted for user_id=%s', claims['sub'])
        return f(*args, **kwargs)
    return decorated


def tier_required(required_tiers):
    """Endpoint requires subscription_tier ∈ ``required_tiers`` — service-role bypass honoured."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            claims, err = _authenticate(_extract_token(request))
            if err:
                return err
            _set_user_context(claims)

            if claims['role'] == 'service_role':
                return f(*args, **kwargs)

            if not _user_has_tier(claims['sub'], tuple(required_tiers)):
                logger.warning(
                    '[AUTH] Tier access denied for user_id=%s required=%s',
                    claims['sub'], required_tiers,
                )
                return jsonify({
                    'error': f'Requires {" or ".join(required_tiers)} access'
                }), 403

            logger.info('[AUTH] Tier access granted for user_id=%s', claims['sub'])
            return f(*args, **kwargs)
        return decorated
    return decorator
