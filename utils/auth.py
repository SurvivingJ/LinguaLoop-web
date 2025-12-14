from functools import wraps
from flask import request, jsonify, g
import jwt
import logging
import os
from supabase import create_client

logger = logging.getLogger(__name__)


def supabase_jwt_required(f):
    """
    Decorator to require valid Supabase JWT.
    Uses Supabase client to verify tokens.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("No authorization header provided")
            return jsonify({'error': 'No authorization token provided'}), 401
        
        token = auth_header.split(' ')[1]
        
        try:
            # Check service role key
            service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            if service_role_key and token == service_role_key:
                g.supabase_claims = {
                    'sub': 'service-account',
                    'role': 'service_role',
                    'email': 'batch-service@internal'
                }
                g.user_id = 'service-account'
                return f(*args, **kwargs)
            
            # ✅ Use Supabase to verify the JWT
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                logger.error("Supabase configuration missing")
                return jsonify({'error': 'Server configuration error'}), 500
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Verify token by fetching user
            user_response = supabase.auth.get_user(token)
            
            if not user_response or not user_response.user:
                logger.warning("Invalid JWT token")
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Store claims in Flask g
            g.supabase_claims = {
                'sub': user_response.user.id,
                'email': user_response.user.email,
                'role': 'authenticated',
                'aud': 'authenticated'
            }
            g.user_id = user_response.user.id
            
            logger.info(f"✅ User authenticated: {user_response.user.id}")
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f'JWT validation failed: {e}', exc_info=True)
            return jsonify({'error': 'Authentication failed'}), 401
    
    return wrapper
