from functools import wraps
from flask import request, jsonify, g
import jwt, requests, json
import logging
import os

logger = logging.getLogger(__name__)

SUPABASE_JWKS_URL = "https://kpfqrjtfxmujzolwsvdq.supabase.co/auth/v1/.well-known/jwks.json"

def supabase_jwt_required(f):
    """
    Decorator to require valid Supabase JWT or service role key.
    Supports both user JWTs and service role key for batch operations.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Get Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No authorization token provided'}), 401
        
        # Extract token
        token = auth_header.split(' ')[1]
        
        try:
            # Check if it's service role key (for batch scripts)
            service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            if service_role_key and token == service_role_key:
                # Service role - bypass JWT validation
                g.supabase_claims = {
                    'sub': 'service-account',
                    'role': 'service_role',
                    'email': 'batch-service@internal'
                }
                g.user_id = 'service-account'
                
                # THIS CALLS YOUR ORIGINAL FUNCTION (e.g., generate_test)
                return f(*args, **kwargs)
            
            # Otherwise validate as normal user JWT
            # Decode header to check algorithm
            header = jwt.get_unverified_header(token)
            
            # Get JWKS from Supabase
            jwks_url = f"{os.getenv('SUPABASE_URL')}/auth/v1/jwks"
            jwks_response = requests.get(jwks_url)
            jwks = jwks_response.json()['keys']
            
            # Find matching key (handle missing kid)
            kid = header.get('kid')
            if kid:
                key = next((k for k in jwks if k['kid'] == kid), None)
            else:
                # Fallback for tokens without kid
                key = jwks[0] if jwks else None
            
            if not key:
                return jsonify({'error': 'Unable to verify token'}), 401
            
            # Construct public key
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            
            # Validate JWT
            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience='authenticated'
            )
            
            # Store user info
            g.supabase_claims = payload
            g.user_id = payload.get('sub')
            
            # THIS CALLS YOUR ORIGINAL FUNCTION
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401
        except Exception as e:
            import logging
            logging.error(f'JWT validation failed: {e}')
            return jsonify({'error': 'Authentication failed'}), 401
    
    return wrapper
