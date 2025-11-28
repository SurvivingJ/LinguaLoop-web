from functools import wraps
from flask import request, jsonify, g
from supabase import create_client
import jwt

class AuthMiddleware:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    def jwt_required(self, f):
        """Decorator for endpoints requiring authentication"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = self._extract_token(request)
            if not token:
                return jsonify({'error': 'Token missing'}), 401
                
            try:
                # Verify with Supabase Auth
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
            # First check if user is authenticated
            token = self._extract_token(request)
            if not token:
                return jsonify({'error': 'Token missing'}), 401
                
            try:
                user = self.supabase.auth.get_user(token)
                g.current_user_id = user.user.id
                
                # Check admin status via RLS (will fail if not admin)
                result = self.supabase.table('users')\
                    .select('subscription_tier')\
                    .eq('id', user.user.id)\
                    .execute()
                    
                if not result.data or result.data[0]['subscription_tier'] not in ['admin', 'moderator']:
                    return jsonify({'error': 'Admin access required'}), 403
                    
            except Exception as e:
                return jsonify({'error': 'Access denied'}), 403
                
            return f(*args, **kwargs)
        return decorated
    
    def tier_required(self, required_tiers: list):
        """Decorator for subscription tier-based access"""
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                token = self._extract_token(request)
                if not token:
                    return jsonify({'error': 'Token missing'}), 401
                    
                try:
                    user = self.supabase.auth.get_user(token)
                    g.current_user_id = user.user.id
                    
                    # Leverage RLS for tier checking
                    result = self.supabase.table('users')\
                        .select('subscription_tier')\
                        .eq('id', user.user.id)\
                        .execute()
                        
                    if not result.data or result.data[0]['subscription_tier'] not in required_tiers:
                        return jsonify({'error': f'Requires {" or ".join(required_tiers)} access'}), 403
                        
                except Exception as e:
                    return jsonify({'error': 'Access denied'}), 403
                    
                return f(*args, **kwargs)
            return decorated
        return decorator
    
    def _extract_token(self, request):
        """Extract JWT token from Authorization header"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.replace('Bearer ', '')
        return None