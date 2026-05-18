# routes/auth.py
"""Authentication routes for OTP-based login."""

from flask import Blueprint, request, jsonify, g, make_response
from utils.validation import validate_email
from middleware.auth import jwt_required
from config import Config

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Services are initialized via app context - see _register_blueprints in app.py
# auth_bp.auth_service and auth_bp.device_service are set there


def _client_ip():
    """Best-effort client IP, respecting a single forwarded-for hop."""
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.remote_addr


def _set_device_cookie(response, raw_token: str):
    """Attach the trusted-device cookie to a Flask response."""
    response.set_cookie(
        Config.DEVICE_COOKIE_NAME,
        raw_token,
        max_age=int(Config.REMEMBER_DEVICE_DURATION.total_seconds()),
        secure=not Config.DEBUG,        # HTTPS-only in prod; relaxed in local dev
        httponly=True,
        samesite='Lax',
        path=Config.DEVICE_COOKIE_PATH,
    )


def _clear_device_cookie(response):
    response.set_cookie(
        Config.DEVICE_COOKIE_NAME,
        '',
        max_age=0,
        secure=not Config.DEBUG,
        httponly=True,
        samesite='Lax',
        path=Config.DEVICE_COOKIE_PATH,
    )


def _origin_is_allowed() -> bool:
    """Defense-in-depth against CSRF on cookie-bearing endpoints."""
    origin = request.headers.get('Origin')
    if not origin:
        # Same-origin browser POSTs without a CORS-relevant cross-site context
        # typically omit Origin; Referer can be checked but isn't required.
        return True
    return origin in Config.CORS_ORIGINS


@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    """Send OTP to user's email for authentication."""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        is_registration = data.get('is_registration', False)

        if not email or not validate_email(email):
            return jsonify({'error': 'Valid email is required'}), 400

        result = auth_bp.auth_service.send_otp(email, is_registration)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500


@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """
    Verify OTP code and authenticate user.

    Expects JSON with:
        - email: User's email address
        - otp_code: 6-digit OTP code
        - remember_device: bool — if true, issue a long-lived device cookie

    Returns user data and JWT token on success.
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        token = data.get('otp_code', '').strip()
        remember_device = bool(data.get('remember_device', False))

        if not email or not token:
            return jsonify({
                'success': False,
                'error': 'Email and token are required',
                'message': 'Email and token are required',
                'user': None,
                'jwt_token': None
            }), 400

        # Verify OTP via auth service
        result = auth_bp.auth_service.verify_otp(email, token)

        if result.get('success'):
            user_data = result.get('user', {})

            # Extract refresh token from session if available
            session = result.get('session')
            refresh_token = session.refresh_token if session else None

            response_data = {
                'success': True,
                'message': result.get('message', 'Authentication successful'),
                'user': {
                    'id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'emailVerified': bool(user_data.get('email_verified', True)),
                    'subscriptionTier': user_data.get('subscription_tier', 'free'),
                    'tokenBalance': int(user_data.get('token_balance', 0)),
                    'totalTestsTaken': int(user_data.get('total_tests_taken', 0)),
                    'totalTestsGenerated': int(user_data.get('total_tests_generated', 0))
                },
                'jwt_token': result.get('jwt_token'),
                'refresh_token': refresh_token,
                'remembered': False,
            }

            raw_device_token = None
            if remember_device and getattr(auth_bp, 'device_service', None):
                try:
                    raw_device_token, _expires = auth_bp.device_service.issue_device_token(
                        user_id=user_data.get('id'),
                        user_agent=request.headers.get('User-Agent'),
                        ip=_client_ip(),
                    )
                    response_data['remembered'] = True
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        f'Failed to issue device token: {e}', exc_info=True
                    )
                    # Fall through with remembered=False — login still succeeds.

            response = make_response(jsonify(response_data), 200)
            if raw_device_token:
                _set_device_cookie(response, raw_device_token)
            return response
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', 'Authentication failed'),
                'user': None,
                'jwt_token': None
            }), 400

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Exception in verify_otp: {e}", exc_info=True)

        return jsonify({
            'success': False,
            'error': 'Server error occurred',
            'message': 'Server error occurred',
            'user': None,
            'jwt_token': None
        }), 500


@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    """Refresh JWT token using a refresh token."""
    try:
        data = request.get_json() or {}
        refresh_token = data.get('refresh_token')

        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 400

        result = auth_bp.auth_service.refresh_session(refresh_token)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Exception in refresh_token: {e}", exc_info=True)
        return jsonify({'error': 'Server error occurred'}), 500


@auth_bp.route('/device-restore', methods=['POST'])
def device_restore():
    """Silently re-authenticate a remembered device.

    Validates the HttpOnly trusted-device cookie, rotates it, and mints a
    fresh Supabase-shaped JWT. Used by base.html when the short-lived access
    token is missing or expired and there is no usable Supabase refresh
    token in storage.
    """
    if not _origin_is_allowed():
        return jsonify({'error': 'Origin not allowed'}), 403

    device_service = getattr(auth_bp, 'device_service', None)
    if device_service is None:
        return jsonify({'error': 'Device service unavailable'}), 503

    raw_token = request.cookies.get(Config.DEVICE_COOKIE_NAME)
    if not raw_token:
        return jsonify({'error': 'No device token'}), 401

    try:
        restored = device_service.restore_from_token(
            raw_token=raw_token,
            user_agent=request.headers.get('User-Agent'),
            ip=_client_ip(),
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(
            f'device-restore: restore_from_token crashed: {e}', exc_info=True
        )
        return jsonify({'error': 'Server error'}), 500

    if not restored:
        # Bad / expired / revoked / reuse — clear the cookie so the browser
        # stops sending it and the user is bounced to /login cleanly.
        response = make_response(jsonify({'error': 'Invalid device token'}), 401)
        _clear_device_cookie(response)
        return response

    # Mint a fresh Supabase-shaped access token for this user.
    minted = auth_bp.auth_service.mint_session_for_user(
        user_id=restored['user_id'],
        email=restored['user_email'],
    )
    if not minted.get('success'):
        return jsonify({'error': minted.get('error', 'Failed to mint session')}), 500

    # Fetch the user profile so the frontend can repopulate user_data.
    profile = auth_bp.auth_service.get_user_profile(restored['user_id'])
    user = profile.get('user', {}) if profile.get('success') else {}

    body = {
        'success': True,
        'jwt_token': minted['jwt_token'],
        'refresh_token': minted.get('refresh_token'),
        'user': {
            'id': user.get('id') or restored['user_id'],
            'email': user.get('email') or restored['user_email'],
            'emailVerified': bool(user.get('email_verified', True)),
            'subscriptionTier': user.get('subscription_tier', 'free'),
            'tokenBalance': int(user.get('token_balance', 0)),
            'totalTestsTaken': int(user.get('total_tests_taken', 0)),
            'totalTestsGenerated': int(user.get('total_tests_generated', 0)),
        },
    }

    response = make_response(jsonify(body), 200)
    _set_device_cookie(response, restored['new_raw_token'])
    return response


@auth_bp.route('/profile', methods=['GET'])
@jwt_required
def get_profile():
    """Get user profile - requires JWT authentication."""
    try:
        result = auth_bp.auth_service.get_user_profile(g.current_user_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404

    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required
def logout():
    """Logout user - requires JWT authentication."""
    try:
        # Revoke the trusted-device row for this browser (if any) before
        # clearing the cookie. Best-effort: a failure here shouldn't block
        # the user from logging out.
        device_service = getattr(auth_bp, 'device_service', None)
        raw_device_token = request.cookies.get(Config.DEVICE_COOKIE_NAME)
        if device_service and raw_device_token:
            try:
                device_service.revoke_by_raw_token(raw_device_token, reason='logout')
            except Exception:
                import logging
                logging.getLogger(__name__).exception('Failed to revoke device on logout')

        result = auth_bp.auth_service.logout(g.current_user_id)
        status = 200 if result['success'] else 400
        response = make_response(jsonify(result), status)
        _clear_device_cookie(response)
        return response

    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500
