from typing import Dict, List, Optional
from datetime import datetime, timezone

class DatabaseService:
    """Centralized database operations for ELO and test management"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    def get_user_elo(self, user_email: str, language: str, skill_type: str) -> float:
        """Get user's current ELO rating for specific language/skill"""
        try:
            result = self.supabase.table('user_skill_ratings').select('elo_rating').eq(
                'user_email', user_email
            ).eq('language', language.lower()).eq('skill_type', skill_type.lower()).single().execute()
            
            return float(result.data['elo_rating']) if result.data else 1400.0
        except:
            return 1400.0
    
    def update_user_elo(self, user_email: str, language: str, skill_type: str, new_elo: float):
        """Update or create user ELO rating"""
        try:
            self.supabase.table('user_skill_ratings').upsert({
                'user_email': user_email,
                'language': language.lower(),
                'skill_type': skill_type.lower(),
                'elo_rating': int(new_elo),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            print(f"Error updating user ELO: {e}")
    
    def get_test_with_questions(self, slug: str) -> Optional[Dict]:
        """Get test with questions by slug"""
        try:
            # Get test
            test_result = self.supabase.table('tests').select('*').eq('slug', slug).single().execute()
            if not test_result.data:
                return None
            
            test = test_result.data
            
            # Get questions
            questions_result = self.supabase.table('questions').select('*').eq('test_id', test['id']).order('question_order').execute()
            test['questions'] = questions_result.data or []
            
            return test
        except Exception as e:
            print(f"Error getting test: {e}")
            return None
    
    def record_test_attempt(self, attempt_data: Dict) -> str:
        """Record a test attempt in database"""
        try:
            result = self.supabase.table('test_attempts').insert(attempt_data).execute()
            return result.data[0]['id'] if result.data else None
        except Exception as e:
            print(f"Error recording test attempt: {e}")
            return None
    
    def update_question_elos(self, question_updates: List[Dict]):
        """Batch update question ELO ratings"""
        try:
            for update in question_updates:
                self.supabase.table('questions').update({
                    'elo_rating': int(update['new_elo']),
                    'attempts_count': 'attempts_count + 1',  # SQL increment
                    'last_attempt_date': datetime.now().date().isoformat()
                }).eq('id', update['question_id']).execute()
        except Exception as e:
            print(f"Error updating question ELOs: {e}")
