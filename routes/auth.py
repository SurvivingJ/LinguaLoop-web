from flask import Blueprint, request, jsonify, g
from ..services.auth_service import AuthService
from ..utils.validation import validate_email
from supabase import create_client
from ..config import Config

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Initialize services directly (avoid dependency injection complexity)
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
auth_service = AuthService(supabase)

# Import middleware class and create instance
from ..middleware.auth import AuthMiddleware
auth_middleware = AuthMiddleware(supabase)

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        is_registration = data.get('is_registration', False)
        
        if not email or not validate_email(email):
            return jsonify({'error': 'Valid email is required'}), 400
        
        result = auth_service.send_otp(email, is_registration)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json() or {}
        email = data.get('email', '').strip().lower()
        token = data.get('otp_code', '').strip()
        
        # Debug logging
        print(f"🔧 DEBUG: Verifying OTP for {email} with token {token}")
        
        if not email or not token:
            return jsonify({
                'success': False,
                'error': 'Email and token are required',
                'message': 'Email and token are required',
                'user': None,
                'accessToken': None
            }), 400
        
        # Call your auth service
        result = auth_service.verify_otp(email, token)
        print(f"🔧 DEBUG: Auth service result: {result}")
        
        if result.get('success'):
            user_data = result.get('user', {})
            print(f"RESULT: {result}", flush=True)
            # Map to Flutter's expected camelCase format
            response_data = {
                'success': True,
                'message': result.get('message', 'Authentication successful'),
                'user': {
                    'id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'emailVerified': bool(user_data.get('email_verified', True)),  # camelCase
                    'subscriptionTier': user_data.get('subscription_tier', 'free'),  # camelCase
                    'tokenBalance': int(user_data.get('token_balance', 0)),  # camelCase
                    'totalTestsTaken': int(user_data.get('total_tests_taken', 0)),  # camelCase
                    'totalTestsGenerated': int(user_data.get('total_tests_generated', 0))  # camelCase
                },
                'jwt_token': result.get('jwt_token')
            }
            
            print(f"🔧 DEBUG: Sending response: {response_data}")  # Add this debug line
            return jsonify(response_data), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', 'Authentication failed'),
                'user': None,
                'accessToken': None
            }), 400
            
    except Exception as e:
        print(f"🔧 DEBUG: Exception in verify_otp: {e}")
        import traceback
        print(f"🔧 DEBUG: Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': 'Server error occurred',
            'message': 'Server error occurred',
            'user': None,
            'accessToken': None
        }), 500



@auth_bp.route('/profile', methods=['GET'])
@auth_middleware.jwt_required  # Now this works!
def get_profile():
    try:
        result = auth_service.get_user_profile(g.current_user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500

@auth_bp.route('/logout', methods=['POST'])
@auth_middleware.jwt_required
def logout():
    try:
        result = auth_service.logout(g.current_user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500
