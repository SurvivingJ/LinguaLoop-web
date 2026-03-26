"""
Mystery Generation Database Client

Handles all database operations for the mystery generation pipeline.
"""

import logging
from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone

from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


class MysteryDatabaseClient:
    """Database operations for mystery generation pipeline."""

    def __init__(self):
        self._admin = None

    @property
    def admin(self):
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    def get_language_config(self, language_id: int) -> Optional[Dict]:
        """Get language configuration from dim_languages."""
        result = self.admin.table('dim_languages').select('*')\
            .eq('id', language_id).single().execute()
        return result.data if result.data else None

    def get_prompt_template(self, task_name: str, language_id: int) -> Optional[str]:
        """
        Fetch prompt template by task name and language ID.
        Falls back to English (language_id=2) if not found.
        """
        response = self.admin.table('prompt_templates') \
            .select('template_text') \
            .eq('task_name', task_name) \
            .eq('language_id', language_id) \
            .eq('is_active', True) \
            .order('version', desc=True) \
            .limit(1) \
            .execute()

        if response.data:
            return response.data[0]['template_text']

        # Fallback to English
        if language_id != 2:
            response = self.admin.table('prompt_templates') \
                .select('template_text') \
                .eq('task_name', task_name) \
                .eq('language_id', 2) \
                .eq('is_active', True) \
                .order('version', desc=True) \
                .limit(1) \
                .execute()

            if response.data:
                logger.debug(f"Using fallback English template for {task_name}")
                return response.data[0]['template_text']

        return None

    def get_cefr_config(self, difficulty: int) -> Optional[Dict]:
        """Get CEFR configuration for a difficulty level."""
        # Map difficulty to CEFR code
        cefr_map = {1: 'A1', 2: 'A1', 3: 'A2', 4: 'B1', 5: 'B1', 6: 'B2', 7: 'C1', 8: 'C2', 9: 'C2'}
        cefr_code = cefr_map.get(difficulty, 'B1')

        result = self.admin.table('dim_cefr_levels').select('*')\
            .eq('code', cefr_code).single().execute()
        return result.data if result.data else None

    def save_mystery(
        self,
        mystery_data: Dict,
        scenes: List[Dict],
        questions_by_scene: Dict[int, List[Dict]],
        gen_user_id: str,
    ) -> str:
        """
        Save a complete mystery with all scenes and questions.

        Returns:
            Mystery ID (UUID string)
        """
        now = datetime.now(timezone.utc).isoformat()

        # Generate slug
        slug = mystery_data.get('slug') or f"mystery-{uuid4().hex[:12]}"
        mystery_data['slug'] = slug

        # Insert mystery
        mystery_row = {
            'slug': slug,
            'language_id': mystery_data['language_id'],
            'difficulty': mystery_data['difficulty'],
            'title': mystery_data['title'],
            'premise': mystery_data['premise'],
            'suspects': mystery_data['suspects'],
            'solution_suspect': mystery_data['solution_suspect'],
            'solution_reasoning': mystery_data['solution_reasoning'],
            'archetype': mystery_data.get('archetype'),
            'target_vocab_ids': mystery_data.get('target_vocab_ids', []),
            'vocab_sense_ids': mystery_data.get('vocab_sense_ids', []),
            'generation_model': mystery_data.get('generation_model', 'gpt-4'),
            'gen_user': gen_user_id,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }

        mystery_result = self.admin.table('mysteries').insert(mystery_row).execute()
        if not mystery_result.data:
            raise Exception("Failed to insert mystery")

        mystery_id = mystery_result.data[0]['id']
        logger.info(f"Inserted mystery: {slug} (id={mystery_id})")

        # Insert scenes
        for scene_data in scenes:
            scene_row = {
                'mystery_id': mystery_id,
                'scene_number': scene_data['scene_number'],
                'title': scene_data['title'],
                'transcript': scene_data['transcript'],
                'audio_url': scene_data.get('audio_url'),
                'clue_text': scene_data['clue_text'],
                'clue_type': scene_data.get('clue_type', 'evidence'),
                'is_finale': scene_data['scene_number'] == 5,
                'target_words': scene_data.get('target_words'),
                'created_at': now,
            }

            scene_result = self.admin.table('mystery_scenes').insert(scene_row).execute()
            if not scene_result.data:
                raise Exception(f"Failed to insert scene {scene_data['scene_number']}")

            scene_id = scene_result.data[0]['id']

            # Insert questions for this scene
            scene_num = scene_data['scene_number']
            scene_questions = questions_by_scene.get(scene_num, [])

            question_rows = []
            for q in scene_questions:
                question_rows.append({
                    'scene_id': scene_id,
                    'question_text': q['question_text'],
                    'choices': q['choices'],
                    'answer': q['correct_answer'],
                    'answer_explanation': q.get('explanation', ''),
                    'is_deduction': q.get('is_deduction', False),
                    'sense_ids': q.get('sense_ids', []),
                    'created_at': now,
                })

            if question_rows:
                self.admin.table('mystery_questions').insert(question_rows).execute()

            logger.info(f"Inserted scene {scene_num} with {len(question_rows)} questions")

        # Create initial skill rating
        self.admin.table('mystery_skill_ratings').insert({
            'mystery_id': mystery_id,
            'elo_rating': 1400,
            'total_attempts': 0,
            'created_at': now,
            'updated_at': now,
        }).execute()

        logger.info(f"Mystery generation complete: {slug}")
        return mystery_id
