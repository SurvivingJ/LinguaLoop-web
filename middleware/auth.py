# middleware/auth.py
"""
Consolidated authentication middleware.

Three decorators (`jwt_required`, `admin_required`, `tier_required`) share a
single `_authenticate` helper.

The HTTP bearer-token bypass uses a dedicated `BATCH_SERVICE_TOKEN` (ADR-014,
2026-05-26), not the Supabase service-role key. It is honoured only by
`jwt_required` — `admin_required` and `tier_required` no longer short-circuit
on `service_role` claims, so a leak of the batch token does not unlock admin
endpoints. If `BATCH_SERVICE_TOKEN` is unset the bypass branch is inert.
"""

from functools import wraps
from flask import request, jsonify, g
from gotrue.errors import AuthApiError, AuthRetryableError
import base64
import hashlib
import hmac
import json
import os
import logging
import threading
import time

logger = logging.getLogger(__name__)


# ============================================================================
# Token validation cache (TASK-774)
# ============================================================================
# `auth.get_user(token)` is a NETWORK CALL to GoTrue, and it ran on every single
# authenticated request. Measured 2026-09-13: the round trip to this project's
# region is 53-108 ms even with keep-alive, so every endpoint in the app paid a
# fixed ~65-150 ms toll before its handler started. On the calibration hot path
# that was a fifth of the time between clicking an answer and seeing whether it
# was right.
#
# Two properties keep this honest:
#
#   * ONLY SUCCESSES ARE CACHED. A rejected token is re-checked every time, so a
#     bad or revoked-then-retried token never gets a free pass from here.
#
#   * AN ENTRY NEVER OUTLIVES ITS TOKEN. The expiry is
#     min(now + TTL, the JWT's own `exp`), read from the payload without
#     verifying it — safe because the value is only ever used to SHORTEN a
#     lifetime, so a forged `exp` can make a cache entry die early and nothing
#     else. A token that has actually expired is therefore never served from
#     cache; GoTrue is asked again and rejects it.
#
# The residual risk is the intended one: a session revoked server-side keeps
# working for at most AUTH_CACHE_TTL_SECONDS. Set it to 0 to disable the cache
# entirely and restore the previous behaviour.
_AUTH_CACHE_TTL = float(os.getenv('AUTH_CACHE_TTL_SECONDS', '60'))
_AUTH_CACHE_MAX = 512
_auth_cache: dict = {}
_auth_cache_lock = threading.Lock()


def _token_exp(token):
    """The JWT's own `exp`, or None. Unverified — see the note above."""
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        exp = json.loads(base64.urlsafe_b64decode(payload)).get('exp')
        return float(exp) if exp is not None else None
    except Exception:
        return None


def _auth_cache_get(key):
    with _auth_cache_lock:
        entry = _auth_cache.get(key)
        if not entry:
            return None
        expires_at, claims = entry
        if expires_at <= time.time():
            _auth_cache.pop(key, None)
            return None
        return claims


def _auth_cache_put(key, claims, token):
    if _AUTH_CACHE_TTL <= 0:
        return
    expires_at = time.time() + _AUTH_CACHE_TTL
    token_exp = _token_exp(token)
    if token_exp is not None:
        expires_at = min(expires_at, token_exp)
    if expires_at <= time.time():
        return
    with _auth_cache_lock:
        if len(_auth_cache) >= _AUTH_CACHE_MAX:
            # Crude but adequate: drop everything already dead, and if that
            # frees nothing, drop the whole map. This is a latency cache, not a
            # store — losing it costs one round trip per active user.
            now = time.time()
            for k in [k for k, (exp, _) in _auth_cache.items() if exp <= now]:
                _auth_cache.pop(k, None)
            if len(_auth_cache) >= _AUTH_CACHE_MAX:
                _auth_cache.clear()
        _auth_cache[key] = (expires_at, claims)


def _auth_cache_key(token):
    """Hash, so a raw bearer token is never a key in a long-lived dict."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def clear_auth_cache():
    """Drop every cached validation. For tests, and for an operator who has just
    revoked a session and does not want to wait out the TTL."""
    with _auth_cache_lock:
        _auth_cache.clear()


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

    # Batch-service bypass (ADR-014). Decoupled from SUPABASE_SERVICE_ROLE_KEY
    # so a leak of either credential no longer compromises both planes.
    # Honoured only by jwt_required — admin_required / tier_required treat
    # the synthetic service-account identity like any other user (no tier row
    # → 403). Unset = feature off.
    batch_token = os.getenv('BATCH_SERVICE_TOKEN')
    if batch_token and hmac.compare_digest(token, batch_token):
        logger.info('Batch-service bypass used on %s', request.path)
        return {
            'sub': 'service-account',
            'email': 'batch-service@internal',
            'role': 'service_role',
            'user': None,
        }, None

    cache_key = _auth_cache_key(token)
    cached = _auth_cache_get(cache_key)
    if cached is not None:
        return cached, None

    try:
        user_response = _get_supabase_client().auth.get_user(token)
        if not user_response or not user_response.user:
            return None, (jsonify({'error': 'Invalid or expired token'}), 401)
        user = user_response.user
        claims = {
            'sub': user.id,
            'email': user.email,
            'role': 'authenticated',
            'aud': 'authenticated',
            'user': user,
        }
        # Successes only. A rejection falls through to the handlers below and is
        # never remembered.
        _auth_cache_put(cache_key, claims, token)
        return claims, None
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


def get_optional_user_id(req) -> str | None:
    """Best-effort caller identity for endpoints that must stay reachable
    anonymously (e.g. public test preview/taking) but can personalize when a
    valid token happens to be present. Never raises, never blocks the
    request -- any missing/invalid/expired token just yields None, same as
    no Authorization header at all.
    """
    token = _extract_token(req)
    if not token:
        return None
    claims, err = _authenticate(token)
    if err or not claims:
        return None
    return claims.get('sub')


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
    """Endpoint requires admin/moderator tier.

    ADR-014: batch-service identity is **not** honoured here. A service-account
    request falls through to the tier check, finds no users row for
    ``sub='service-account'``, and 403s — the desired outcome.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        claims, err = _authenticate(_extract_token(request))
        if err:
            return err
        _set_user_context(claims)

        if not _user_has_tier(claims['sub'], ('admin', 'moderator')):
            logger.warning('[AUTH] Admin access denied for user_id=%s', claims['sub'])
            return jsonify({'error': 'Admin access required'}), 403

        logger.info('[AUTH] Admin access granted for user_id=%s', claims['sub'])
        return f(*args, **kwargs)
    return decorated


def tier_required(required_tiers):
    """Endpoint requires subscription_tier ∈ ``required_tiers``.

    ADR-014: batch-service identity is **not** honoured here (see admin_required).
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            claims, err = _authenticate(_extract_token(request))
            if err:
                return err
            _set_user_context(claims)

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
