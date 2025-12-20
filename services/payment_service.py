"""
Payment Service for Language Learning Platform
Handles token-based pay-as-you-go payments via Stripe
"""

import stripe
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from enum import Enum
from supabase import Client

from ..config import Config


class TokenAction(Enum):
    """Actions that consume tokens"""
    TAKE_TEST = 'take_test'
    GENERATE_TEST = 'generate_test'


class PaymentService:
    """
    Handles all payment and token-related operations.
    Uses Config as single source of truth for costs and packages.
    """

    @property
    def TOKEN_COSTS(self):
        """Get token costs from Config"""
        return {
            TokenAction.TAKE_TEST: Config.TOKEN_COSTS['take_test'],
            TokenAction.GENERATE_TEST: Config.TOKEN_COSTS['generate_test']
        }

    @property
    def DAILY_FREE_TOKENS(self):
        """Get daily free tokens from Config"""
        return Config.DAILY_FREE_TOKENS

    @property
    def TOKEN_PACKAGES(self):
        """Get token packages from Config"""
        return Config.TOKEN_PACKAGES
    
    def __init__(self, supabase_client: Client, stripe_secret_key: str):
        """
        Initialize payment service
        
        Args:
            supabase_client: Supabase database client
            stripe_secret_key: Stripe API secret key
        """
        self.supabase = supabase_client
        stripe.api_key = stripe_secret_key
        
    def get_user_token_balance(self, user_id: str) -> Dict:
        """
        Get user's current token balance including free daily tokens
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with token balance information
        """
        try:
            # Get user's token record
            result = self.supabase.table('user_tokens').select('*').eq('user_id', user_id).execute()
            
            if not result.data:
                # Create initial token record for new user
                self._create_user_token_record(user_id)
                return {
                    'total_tokens': self.DAILY_FREE_TOKENS,
                    'purchased_tokens': 0,
                    'free_tokens_today': self.DAILY_FREE_TOKENS,
                    'last_free_token_date': datetime.utcnow().date().isoformat()
                }
            
            user_tokens = result.data[0]
            
            # Check if user gets new free tokens today
            last_free_date = datetime.fromisoformat(user_tokens['last_free_token_date']).date()
            today = datetime.utcnow().date()
            
            if last_free_date < today:
                # Award daily free tokens
                user_tokens = self._award_daily_free_tokens(user_id, user_tokens)
            
            free_tokens_today = self.DAILY_FREE_TOKENS if last_free_date == today else 0
            
            return {
                'total_tokens': user_tokens['purchased_tokens'] + free_tokens_today,
                'purchased_tokens': user_tokens['purchased_tokens'],
                'free_tokens_today': free_tokens_today,
                'last_free_token_date': user_tokens['last_free_token_date']
            }
            
        except Exception as e:
            print(f"Error getting token balance: {e}")
            return {'error': 'Failed to retrieve token balance'}
    
    def can_perform_action(self, user_id: str, action: TokenAction) -> Tuple[bool, str]:
        """
        Check if user has enough tokens for an action
        
        Args:
            user_id: User identifier
            action: Action to check
            
        Returns:
            Tuple of (can_perform, message)
        """
        required_tokens = self.TOKEN_COSTS[action]
        balance = self.get_user_token_balance(user_id)
        
        if 'error' in balance:
            return False, balance['error']
        
        if balance['total_tokens'] >= required_tokens:
            return True, f"Action requires {required_tokens} tokens. You have {balance['total_tokens']}."
        else:
            return False, f"Insufficient tokens. Need {required_tokens}, have {balance['total_tokens']}."
    
    def consume_tokens(self, user_id: str, action: TokenAction, description: str = None) -> Dict:
        """
        Consume tokens for an action
        
        Args:
            user_id: User identifier
            action: Action being performed
            description: Optional description of the action
            
        Returns:
            Dict with transaction result
        """
        required_tokens = self.TOKEN_COSTS[action]
        
        # Check if user can perform action
        can_perform, message = self.can_perform_action(user_id, action)
        if not can_perform:
            return {'success': False, 'error': message}
        
        try:
            # Get current balance
            balance = self.get_user_token_balance(user_id)
            
            # Determine which tokens to consume (free first, then purchased)
            free_tokens_available = min(balance['free_tokens_today'], required_tokens)
            purchased_tokens_needed = required_tokens - free_tokens_available
            
            # Update purchased tokens balance
            new_purchased_balance = balance['purchased_tokens'] - purchased_tokens_needed
            
            # Update database
            self.supabase.table('user_tokens').update({
                'purchased_tokens': new_purchased_balance,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).execute()
            
            # Log transaction
            self._log_token_transaction(
                user_id=user_id,
                tokens_consumed=required_tokens,
                action=action.value,
                description=description or f"Consumed {required_tokens} tokens for {action.value}"
            )
            
            return {
                'success': True,
                'tokens_consumed': required_tokens,
                'remaining_tokens': new_purchased_balance + (balance['free_tokens_today'] - free_tokens_available),
                'action': action.value
            }
            
        except Exception as e:
            print(f"Error consuming tokens: {e}")
            return {'success': False, 'error': 'Failed to consume tokens'}
    
    def create_payment_intent(self, user_id: str, package_id: str) -> Dict:
        """
        Create Stripe PaymentIntent for token purchase
        
        Args:
            user_id: User identifier
            package_id: Token package identifier
            
        Returns:
            Dict with PaymentIntent details
        """
        if package_id not in self.TOKEN_PACKAGES:
            return {'error': 'Invalid token package'}
        
        package = self.TOKEN_PACKAGES[package_id]
        
        try:
            # Create PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=package.price_cents,
                currency='usd',
                metadata={
                    'user_id': user_id,
                    'package_id': package_id,
                    'tokens': package.tokens,
                    'type': 'token_purchase'
                },
                description=f"Purchase {package.tokens} tokens - {package.description}"
            )
            
            return {
                'client_secret': intent.client_secret,
                'amount': package.price_cents,
                'tokens': package.tokens,
                'package_id': package_id
            }
            
        except Exception as e:
            print(f"Error creating payment intent: {e}")
            return {'error': 'Failed to create payment intent'}
    
    def handle_successful_payment(self, payment_intent_id: str) -> Dict:
        """
        Handle successful payment and award tokens
        
        Args:
            payment_intent_id: Stripe PaymentIntent ID
            
        Returns:
            Dict with processing result
        """
        try:
            # Retrieve PaymentIntent from Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status != 'succeeded':
                return {'error': 'Payment not successful'}
            
            user_id = intent.metadata['user_id']
            package_id = intent.metadata['package_id']
            tokens_purchased = int(intent.metadata['tokens'])
            
            # Add tokens to user's account
            result = self.supabase.table('user_tokens').select('*').eq('user_id', user_id).execute()
            
            if result.data:
                current_tokens = result.data[0]['purchased_tokens']
                new_balance = current_tokens + tokens_purchased
                
                self.supabase.table('user_tokens').update({
                    'purchased_tokens': new_balance,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('user_id', user_id).execute()
            else:
                # Create new token record
                self._create_user_token_record(user_id, initial_purchased_tokens=tokens_purchased)
            
            # Log purchase transaction
            self._log_token_transaction(
                user_id=user_id,
                tokens_added=tokens_purchased,
                action='purchase',
                description=f"Purchased {tokens_purchased} tokens ({package_id})",
                payment_intent_id=payment_intent_id
            )
            
            return {
                'success': True,
                'tokens_purchased': tokens_purchased,
                'package_id': package_id,
                'user_id': user_id
            }
            
        except Exception as e:
            print(f"Error handling successful payment: {e}")
            return {'error': 'Failed to process payment'}
    
    def get_token_packages(self) -> Dict:
        """
        Get available token packages for purchase
        
        Returns:
            Dict of available packages
        """
        return {
            package_id: {
                'tokens': package.tokens,
                'price': package.price_dollars,
                'price_cents': package.price_cents,
                'description': package.description,
                'price_per_token': round(package.price_dollars / package.tokens, 3)
            }
            for package_id, package in self.TOKEN_PACKAGES.items()
        }
    
    def get_user_transaction_history(self, user_id: str, limit: int = 50) -> Dict:
        """
        Get user's token transaction history
        
        Args:
            user_id: User identifier
            limit: Maximum transactions to return
            
        Returns:
            Dict with transaction history
        """
        try:
            result = self.supabase.table('token_transactions').select('*').eq(
                'user_id', user_id
            ).order('created_at', desc=True).limit(limit).execute()
            
            return {
                'transactions': result.data,
                'count': len(result.data)
            }
            
        except Exception as e:
            print(f"Error getting transaction history: {e}")
            return {'error': 'Failed to retrieve transaction history'}
    
    def _create_user_token_record(self, user_id: str, initial_purchased_tokens: int = 0):
        """Create initial token record for new user"""
        return self.supabase.table('user_tokens').insert({
            'user_id': user_id,
            'purchased_tokens': initial_purchased_tokens,
            'last_free_token_date': datetime.utcnow().date().isoformat(),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }).execute()
    
    def _award_daily_free_tokens(self, user_id: str, current_record: Dict) -> Dict:
        """Award daily free tokens to user"""
        today = datetime.utcnow().date().isoformat()
        
        updated_record = self.supabase.table('user_tokens').update({
            'last_free_token_date': today,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('user_id', user_id).execute()
        
        # Log free token award
        self._log_token_transaction(
            user_id=user_id,
            tokens_added=self.DAILY_FREE_TOKENS,
            action='daily_free',
            description=f"Daily free tokens awarded ({self.DAILY_FREE_TOKENS} tokens)"
        )
        
        current_record['last_free_token_date'] = today
        return current_record
    
    def _log_token_transaction(self, user_id: str, tokens_consumed: int = 0, 
                              tokens_added: int = 0, action: str = '', 
                              description: str = '', payment_intent_id: str = None):
        """Log token transaction to database"""
        try:
            self.supabase.table('token_transactions').insert({
                'user_id': user_id,
                'tokens_consumed': tokens_consumed,
                'tokens_added': tokens_added,
                'action': action,
                'description': description,
                'payment_intent_id': payment_intent_id,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            print(f"Error logging transaction: {e}")

# Usage example for your Flask routes
def get_payment_service(config) -> PaymentService:
    """Factory function to create PaymentService instance"""
    from supabase import create_client
    
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return PaymentService(supabase, config.STRIPE_SECRET_KEY)