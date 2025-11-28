from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
import logging

@dataclass
class EloCalculationResult:
    """Clean data structure for ELO calculation results"""
    new_user_elo: float
    new_question_elo: float
    user_change: int
    question_change: int

class EloService:
    """Centralized ELO calculation and management service - Schema Optimized"""
    
    DEFAULT_USER_ELO = 1200  # Matches your schema default
    DEFAULT_TEST_ELO = 1400
    DEFAULT_VOLATILITY = 2.0  # Matches your schema default
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def calculate_question_elo(user_elo: float, question_elo: float, correct: bool, 
                             question_attempts: int = 10, last_attempt_date: Optional[datetime] = None, 
                             k: int = 32) -> EloCalculationResult:
        """Calculate new ELO ratings for user-question interaction"""
        # Volatility adjustment
        volatility_multiplier = 1.0
        if question_attempts < 10:
            volatility_multiplier += 0.5
        if last_attempt_date and (datetime.now() - last_attempt_date).days > 90:
            volatility_multiplier += 0.5

        adjusted_k = k * volatility_multiplier
        result = 1 if correct else 0
        expected_user = 1 / (1 + 10 ** ((question_elo - user_elo) / 400))

        new_user_elo = user_elo + adjusted_k * (result - expected_user)
        new_question_elo = question_elo + adjusted_k * (expected_user - result)

        return EloCalculationResult(
            new_user_elo=new_user_elo,
            new_question_elo=new_question_elo,
            user_change=int(new_user_elo - user_elo),
            question_change=int(new_question_elo - question_elo)
        )
    
    @staticmethod
    def calculate_test_elo(test_elo: float, user_avg_elo: float, test_score: float,
                          test_attempts: int = 10, last_attempt_date: Optional[datetime] = None,
                          k: int = 16) -> float:
        """Calculate new test ELO rating"""
        volatility_multiplier = 1.0
        if test_attempts < 10:
            volatility_multiplier += 0.5
        if last_attempt_date and (datetime.now() - last_attempt_date).days > 90:
            volatility_multiplier += 0.5

        adjusted_k = k * volatility_multiplier
        expected_score = 1 / (1 + 10 ** ((test_elo - user_avg_elo) / 400))
        return test_elo + adjusted_k * (test_score - expected_score)
    
    def get_user_elo(self, user_id: str, language: str, skill_type: str) -> float:
        """Get user's current ELO rating - uses your schema"""
        try:
            result = self.supabase.table('user_skill_ratings').select('elo_rating').eq(
                'user_id', user_id
            ).eq('language', language.lower()).eq('skill_type', skill_type.lower()).execute()
            
            if result.data:
                return float(result.data[0]['elo_rating'])
            else:
                # Create new rating entry with schema defaults
                self._create_user_skill_rating(user_id, language, skill_type)
                return self.DEFAULT_USER_ELO
                
        except Exception as e:
            self.logger.error(f"Error getting user ELO: {e}")
            return self.DEFAULT_USER_ELO
    
    def get_test_elo(self, test_id: str, skill_type: str) -> float:
        """Get test's current ELO rating - uses your schema"""
        try:
            result = self.supabase.table('test_skill_ratings').select('elo_rating').eq(
                'test_id', test_id
            ).eq('skill_type', skill_type.lower()).execute()
            
            if result.data:
                return float(result.data[0]['elo_rating'])
            else:
                # Create new test rating entry
                self._create_test_skill_rating(test_id, skill_type)
                return self.DEFAULT_TEST_ELO
                
        except Exception as e:
            self.logger.error(f"Error getting test ELO: {e}")
            return self.DEFAULT_TEST_ELO
    
    def update_user_elo(self, user_id: str, language: str, skill_type: str, 
                       new_elo: float, tests_taken_increment: int = 1):
        """Update user ELO rating - uses your schema structure"""
        try:
            self.supabase.table('user_skill_ratings').upsert({
                'user_id': user_id,
                'language': language.lower(),
                'skill_type': skill_type.lower(),
                'elo_rating': max(400, min(3000, int(new_elo))),  # Respect constraints
                'tests_taken': f'tests_taken + {tests_taken_increment}',
                'last_test_date': datetime.now().date().isoformat(),
                'updated_at': datetime.now().isoformat()
            }, on_conflict=['user_id', 'language', 'skill_type']).execute()
            
        except Exception as e:
            self.logger.error(f"Error updating user ELO: {e}")
    
    def update_test_elo(self, test_id: str, skill_type: str, new_elo: float):
        """Update test ELO rating - uses your schema structure"""
        try:
            self.supabase.table('test_skill_ratings').upsert({
                'test_id': test_id,
                'skill_type': skill_type.lower(),
                'elo_rating': max(400, min(3000, int(new_elo))),  # Respect constraints
                'total_attempts': 'total_attempts + 1',
                'updated_at': datetime.now().isoformat()
            }, on_conflict=['test_id', 'skill_type']).execute()
            
        except Exception as e:
            self.logger.error(f"Error updating test ELO: {e}")
    
    def _create_user_skill_rating(self, user_id: str, language: str, skill_type: str):
        """Create new user skill rating entry"""
        try:
            self.supabase.table('user_skill_ratings').insert({
                'user_id': user_id,
                'language': language.lower(),
                'skill_type': skill_type.lower(),
                'elo_rating': self.DEFAULT_USER_ELO,
                'volatility': self.DEFAULT_VOLATILITY,
                'tests_taken': 0
            }).execute()
        except Exception as e:
            self.logger.error(f"Error creating user skill rating: {e}")
    
    def _create_test_skill_rating(self, test_id: str, skill_type: str):
        """Create new test skill rating entry"""
        try:
            self.supabase.table('test_skill_ratings').insert({
                'test_id': test_id,
                'skill_type': skill_type.lower(),
                'elo_rating': self.DEFAULT_TEST_ELO,
                'volatility': 1.0,
                'total_attempts': 0
            }).execute()
        except Exception as e:
            self.logger.error(f"Error creating test skill rating: {e}")
    
    def process_test_submission(self, user_id: str, test_id: str, language: str, 
                              skill_type: str, questions_data: list, responses: list, 
                              percentage: float) -> Dict:
        """Process entire test submission and calculate all ELO changes"""
        # Get current ELOs
        current_user_elo = self.get_user_elo(user_id, language, skill_type)
        current_test_elo = self.get_test_elo(test_id, skill_type)
        
        # Calculate average question interaction ELO change
        total_user_elo_change = 0
        processed_questions = 0
        
        for i, question_data in enumerate(questions_data):
            if i < len(responses):
                response = responses[i]
                is_correct = response.get('is_correct', False)
                
                # Use existing question ELO or default
                question_elo = question_data.get('elo_rating', self.DEFAULT_TEST_ELO)
                
                result = self.calculate_question_elo(
                    user_elo=current_user_elo,
                    question_elo=question_elo,
                    correct=is_correct,
                    question_attempts=10,  # Default for now
                    last_attempt_date=None
                )
                
                total_user_elo_change += result.user_change
                processed_questions += 1
        
        # Calculate final ELOs
        avg_user_elo_change = total_user_elo_change / processed_questions if processed_questions > 0 else 0
        final_user_elo = current_user_elo + avg_user_elo_change
        
        # Calculate test ELO change
        final_test_elo = self.calculate_test_elo(
            test_elo=current_test_elo,
            user_avg_elo=final_user_elo,
            test_score=percentage,
            test_attempts=10,  # Get from test_skill_ratings if needed
            last_attempt_date=None
        )
        
        # Update database
        self.update_user_elo(user_id, language, skill_type, final_user_elo)
        self.update_test_elo(test_id, skill_type, final_test_elo)
        
        return {
            'user_elo_before': int(current_user_elo),
            'user_elo_after': int(final_user_elo),
            'user_elo_change': int(avg_user_elo_change),
            'test_elo_before': int(current_test_elo),
            'test_elo_after': int(final_test_elo),
            'test_elo_change': int(final_test_elo - current_test_elo)
        }
