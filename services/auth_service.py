from supabase import Client, create_client
from datetime import datetime, timezone
from typing import Dict, Optional
import logging
import uuid
import os


class AuthService:
    """
    Authentication service for handling OTP-based login and user management.

    Uses two Supabase clients:
    - supabase_admin: Service role client that bypasses RLS, used for:
      * Sending OTP emails (requires admin auth.admin.* permissions)
      * Verifying OTPs and creating sessions
      * Calling RPC functions that need elevated permissions
    - supabase: Regular anon client for standard queries (respects RLS)
    """
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client  # Regular client for RLS-protected queries

        # Admin client for privileged operations (bypasses RLS)
        self.supabase_admin = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        self.logger = logging.getLogger(__name__)
    
    def send_otp(self, email: str, is_registration: bool = False) -> Dict:
        """
        Send OTP code to user's email.

        Uses admin client because sending OTPs requires admin-level auth permissions
        that bypass RLS (Row Level Security) restrictions.

        Args:
            email: User's email address
            is_registration: If True, creates new user; if False, requires existing user

        Returns:
            Dict with 'success' boolean and either 'message' or 'error'
        """
        try:
            # Use ADMIN client for sending OTP emails (requires auth.admin permissions)
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
        """
        Verify OTP code and create user session.

        Uses admin client for OTP verification which requires elevated permissions.

        Args:
            email: User's email address
            token: 6-digit OTP code from email

        Returns:
            Dict containing:
                - success: Boolean indicating verification status
                - user: Complete user profile data (if successful)
                - jwt_token: Session access token (if successful)
                - session: Full Supabase session object (if successful)
                - error/message: Error details (if failed)
        """
        try:
            self.logger.info(f"Verifying OTP for {email}")

            # Use admin client for OTP verification (requires elevated permissions)
            response = self.supabase_admin.auth.verify_otp({
                "email": email,
                "token": token,
                "type": "email"
            })

            self.logger.debug(f"OTP verification response - User: {bool(response.user)}, Session: {bool(response.session)}")
            
            if response.user and response.session:
                # Get complete user data from users table
                user_data = self._get_user_data(response.user.id, email)

                self.logger.info(f"OTP verification successful for {email}")

                return {
                    'success': True,
                    'message': 'Verification successful',
                    'user': user_data,
                    'jwt_token': response.session.access_token,
                    'session': response.session
                }
            else:
                self.logger.warning(f"OTP verification failed - no user or session for {email}")
                return {
                    'success': False,
                    'error': 'Invalid or expired OTP',
                    'message': 'Invalid or expired OTP'
                }

        except Exception as e:
            self.logger.error(f"OTP verification error for {email}: {e}")
            return {
                'success': False,
                'error': f'Verification failed: {str(e)}',
                'message': f'Verification failed: {str(e)}'
            }

    def _get_user_data(self, user_id: str, email: str) -> Dict:
        """
        Get complete user data after OTP verification.

        The Supabase trigger should have already created the user record in the users table.
        This method retrieves that data and adds the token balance.
        """
        try:
            # Query user data from users table
            result = self.supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .execute()

            self.logger.info(f"Retrieved user data for {user_id}: {bool(result.data)}")

            if result.data:
                user_data = result.data[0]

                # Get token balance using admin client (RPC requires elevated permissions)
                token_balance = self.supabase_admin.rpc('get_token_balance', {
                    'p_user_id': user_id
                }).execute()

                user_data['token_balance'] = token_balance.data if token_balance.data else 0
                return self._sanitize_user_data(user_data)
            else:
                # If trigger didn't create user, create manually as fallback
                self.logger.warning(f"User {user_id} not found, creating manually")

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
            self.logger.error(f'Get user data error: {e}')
            # Return safe defaults on error
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