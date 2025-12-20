# routes/auth.py
"""Authentication routes for OTP-based login."""

from flask import Blueprint, request, jsonify, g
from ..utils.validation import validate_email
from ..middleware.auth import jwt_required

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Services are initialized via app context - see _register_blueprints in app.py
# auth_bp.auth_service is set there


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

    Returns user data and JWT token on success.
    """
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        token = data.get('otp_code', '').strip()

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

            # Format response with consistent field naming
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
                'jwt_token': result.get('jwt_token')
            }

            return jsonify(response_data), 200
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
        result = auth_bp.auth_service.logout(g.current_user_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500
