from supabase import Client, create_client
from datetime import datetime, timezone
from typing import Dict, Optional
import logging
import uuid
import os
# DEBUG
class AuthService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client  # Keep existing client for regular ops
        
        # Add admin client with service role for privileged operations
        self.supabase_admin = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # This bypasses RLS
        )
        self.logger = logging.getLogger(__name__)
    
    def send_otp(self, email: str, is_registration: bool = False) -> Dict:
        """Send OTP using admin client to bypass RLS restrictions"""
        try:
            # Use ADMIN client for sending OTP emails
            response = self.supabase_admin.auth.sign_in_with_otp({
                "email": email,
                "options": {
                    "should_create_user": is_registration
                }
            })
            
            return {
                'success': True, 
                'message': f'OTP sent to {email}. Please check your inbox.',
                'email': email
            }
            
        except Exception as e:
            self.logger.error(f'OTP send error: {e}')
            error_msg = str(e).lower()
            
            if 'user not found' in error_msg:
                return {
                    'success': False, 
                    'error': 'No account found. Please register first.',
                    'code': 'USER_NOT_FOUND'
                }
            elif 'rate limit' in error_msg:
                return {
                    'success': False, 
                    'error': 'Too many requests. Please wait before trying again.',
                    'code': 'RATE_LIMITED'
                }
            else:
                return {
                    'success': False, 
                    'error': f'Failed to send OTP: {str(e)}'
                }
    
    def verify_otp(self, email: str, token: str) -> Dict:
        """Verify OTP and return complete user data"""
        try:
            print(f"🔧 Service: Verifying OTP for {email}")
            
            # Use admin client for OTP verification
            response = self.supabase_admin.auth.verify_otp({
                "email": email,
                "token": token,
                "type": "email"
            })
            
            print(f"🔧 Service: Supabase response user: {response.user}")
            print(f"🔧 Service: Supabase response session: {response.session}")
            
            if response.user and response.session:
                # Get complete user data from your users table
                user_data = self._get_user_data(response.user.id, email)
                
                print(f"🔧 Service: Complete user data: {user_data}")
                
                return {
                    'success': True,
                    'message': 'Verification successful',
                    'user': user_data,
                    'jwt_token': response.session.access_token,
                    'session': response.session
                }
            else:
                print(f"🔧 Service: No user or session in response")
                return {
                    'success': False,
                    'error': 'Invalid or expired OTP',
                    'message': 'Invalid or expired OTP'
                }
                
        except Exception as e:
            print(f"🔧 Service: OTP verification error: {e}")
            return {
                'success': False,
                'error': f'Verification failed: {str(e)}',
                'message': f'Verification failed: {str(e)}'
            }

    def _get_user_data(self, user_id: str, email: str) -> Dict:
        """Get complete user data after verification"""
        try:
            # Your trigger should have created the user, so get the data
            result = self.supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .execute()
            
            print(f"🔧 Service: Users table query result: {result.data}")
            
            if result.data:
                user_data = result.data[0]
                
                # Get token balance
                token_balance = self.supabase_admin.rpc('get_token_balance', {
                    'p_user_id': user_id
                }).execute()
                
                user_data['token_balance'] = token_balance.data if token_balance.data else 0
                
                # Ensure all fields have safe values
                return {
                    'id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'subscription_tier': user_data.get('subscription_tier', 'free'),
                    'email_verified': bool(user_data.get('email_verified', True)),
                    'token_balance': int(user_data.get('token_balance', 0)),
                    'total_tests_taken': int(user_data.get('total_tests_taken', 0)),
                    'total_tests_generated': int(user_data.get('total_tests_generated', 0)),
                    'created_at': user_data.get('created_at'),
                    'last_login': user_data.get('last_login')
                }
            else:
                # If trigger didn't create user, create manually using admin client
                print(f"🔧 Service: No user found, creating manually")
                
                user_record = {
                    'id': user_id,
                    'email': email,
                    'subscription_tier': 'free',
                    'email_verified': True,
                    'total_tests_taken': 0,
                    'total_tests_generated': 0,
                    'last_login': datetime.now(timezone.utc).isoformat()
                }
                
                self.supabase_admin.table('users').insert(user_record).execute()
                
                # Grant welcome tokens
                self.supabase_admin.rpc('grant_daily_free_tokens', {
                    'p_user_id': user_id
                }).execute()
                
                user_record['token_balance'] = 2  # Default welcome tokens
                return user_record
                
        except Exception as e:
            print(f"🔧 Service: Get user data error: {e}")
            # Return safe minimal data
            return {
                'id': user_id,
                'email': email,
                'subscription_tier': 'free',
                'email_verified': True,
                'token_balance': 0,
                'total_tests_taken': 0,
                'total_tests_generated': 0,
                'last_login': datetime.now(timezone.utc).isoformat()
            }


    def _get_user_data(self, user_id: str, email: str) -> Dict:
        """Get user data after trigger has created the record"""
        try:
            # Use regular client - RLS will ensure user can only see their own data
            result = self.supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .execute()
            
            if result.data:
                user_data = result.data[0]
                
                # Get token balance using admin client
                token_balance = self.supabase_admin.rpc('get_token_balance', {
                    'p_user_id': user_id
                }).execute()
                
                user_data['token_balance'] = token_balance.data if token_balance.data else 0
                return self._sanitize_user_data(user_data)
            else:
                # Return safe defaults if user not found
                return {
                    'id': user_id,
                    'email': email,
                    'subscription_tier': 'free',
                    'email_verified': True,
                    'token_balance': 0,
                    'total_tests_taken': 0,
                    'total_tests_generated': 0,
                    'last_login': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            self.logger.error(f'Get user data error: {e}')
            return {
                'id': user_id,
                'email': email,
                'subscription_tier': 'free',
                'email_verified': True,
                'token_balance': 0,
                'total_tests_taken': 0,
                'total_tests_generated': 0,
                'last_login': datetime.now(timezone.utc).isoformat()
            }
        
    def _ensure_user_setup(self, user_id: str, email: str) -> Dict:
        """Verify user setup and get user data (trigger handles creation)"""
        try:
            # Just get the user data - trigger should have created it
            result = self.supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .execute()
            
            if result.data:
                user_data = result.data[0]
                
                # Get token balance
                token_balance = self.supabase.rpc('get_token_balance', {
                    'p_user_id': user_id
                }).execute()
                
                user_data['token_balance'] = token_balance.data if token_balance.data else 0
                return self._sanitize_user_data(user_data)
            else:
                # If trigger didn't work, return safe defaults
                return {
                    'id': user_id,
                    'email': email,
                    'subscription_tier': 'free',
                    'email_verified': True,
                    'token_balance': 0,
                    'total_tests_taken': 0,
                    'total_tests_generated': 0,
                    'last_login': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            self.logger.error(f'User setup verification error: {e}')
            return {
                'id': user_id,
                'email': email,
                'subscription_tier': 'free',
                'email_verified': True,
                'token_balance': 0,
                'total_tests_taken': 0,
                'total_tests_generated': 0,
                'last_login': datetime.now(timezone.utc).isoformat()
            }

    
    def _safe_bool(self, value, default=False):
        """Safely convert value to boolean, handling null cases"""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def _sanitize_user_data(self, user_data: Dict) -> Dict:
        """Ensure all user data fields have proper types"""
        return {
            'id': user_data.get('id'),
            'email': user_data.get('email'),
            'email_verified': bool(user_data.get('email_verified', True)),
            'subscription_tier': user_data.get('subscription_tier', 'free'),
            'token_balance': int(user_data.get('token_balance') or 0),
            'total_tests_taken': int(user_data.get('total_tests_taken') or 0),
            'total_tests_generated': int(user_data.get('total_tests_generated') or 0),
            'created_at': user_data.get('created_at'),
            'last_login': user_data.get('last_login')
        }

    
    def logout(self, user_id: str) -> Dict:
        """Handle user logout"""
        try:
            # Sign out from Supabase
            self.supabase.auth.sign_out()
            
            # Update last activity
            self.supabase.table('users').update({
                'last_activity_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', user_id).execute()
            
            return {'success': True, 'message': 'Logged out successfully'}
            
        except Exception as e:
            self.logger.error(f'Logout error: {e}')
            return {'success': False, 'error': 'Logout failed'}
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile with token balance"""
        try:
            # Get user data (RLS will filter automatically)
            user_result = self.supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .execute()
            
            if not user_result.data:
                return {'success': False, 'error': 'User not found'}
            
            # Get token balance
            token_balance = self.supabase.rpc('get_token_balance', {
                'p_user_id': user_id
            })
            
            user_data = user_result.data[0]
            user_data['token_balance'] = token_balance
            
            return {'success': True, 'user': user_data}
            
        except Exception as e:
            self.logger.error(f'Profile fetch error: {e}')
            return {'success': False, 'error': 'Failed to fetch profile'}