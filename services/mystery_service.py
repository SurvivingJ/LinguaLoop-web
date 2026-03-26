# services/mystery_service.py
"""
Mystery Service - Business logic for murder mystery comprehension mode.
Handles mystery retrieval, progress management, scene submission, and finale scoring.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from uuid import uuid4

from services.supabase_factory import get_supabase, get_supabase_admin
from services.dimension_service import DimensionService

logger = logging.getLogger(__name__)


class MysteryService:
    """
    Centralized service for murder mystery operations.
    Follows the same singleton + lazy-init pattern as TestService.
    """

    def __init__(self, supabase_client=None, supabase_admin=None):
        self._client = supabase_client
        self._admin = supabase_admin

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase()
        return self._client

    @property
    def admin(self):
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    # -------------------------------------------------------------------------
    # MYSTERY RETRIEVAL
    # -------------------------------------------------------------------------

    def get_mysteries(self, language_id: int, difficulty: int = None,
                      limit: int = 50) -> List[Dict]:
        """Fetch mysteries list with optional filters."""
        try:
            query = self.client.table('mysteries').select(
                'id, slug, language_id, difficulty, title, premise, '
                'suspects, total_attempts, created_at'
            ).eq('is_active', True)

            if language_id:
                query = query.eq('language_id', language_id)
            if difficulty is not None:
                query = query.eq('difficulty', int(difficulty))

            query = query.order('created_at', desc=True).limit(limit)
            result = query.execute()
            mysteries = result.data or []

            # Enrich with ELO ratings
            if mysteries:
                mystery_ids = [m['id'] for m in mysteries]
                ratings = self._get_mystery_ratings(mystery_ids)
                for m in mysteries:
                    m['elo_rating'] = ratings.get(m['id'], 1400)

            return mysteries

        except Exception as e:
            logger.error(f"Error fetching mysteries: {e}")
            return []

    def get_mystery_by_slug(self, slug: str) -> Optional[Dict]:
        """Get a mystery by slug with its scenes (no questions)."""
        if not slug:
            return None

        try:
            m_res = self.client.table('mysteries').select('*')\
                .eq('slug', slug).eq('is_active', True).limit(1).execute()
            if not m_res.data:
                return None

            mystery = m_res.data[0]

            # Fetch scenes (without questions for overview)
            scenes_res = self.client.table('mystery_scenes').select(
                'id, scene_number, title, is_finale'
            ).eq('mystery_id', mystery['id'])\
                .order('scene_number').execute()

            mystery['scenes'] = scenes_res.data or []

            # Get ELO
            ratings = self._get_mystery_ratings([mystery['id']])
            mystery['elo_rating'] = ratings.get(mystery['id'], 1400)

            return mystery

        except Exception as e:
            logger.error(f"Error fetching mystery by slug '{slug}': {e}")
            return None

    def get_scene(self, mystery_id: str, scene_number: int) -> Optional[Dict]:
        """Get a specific scene with its questions."""
        try:
            scene_res = self.client.table('mystery_scenes').select('*')\
                .eq('mystery_id', mystery_id)\
                .eq('scene_number', scene_number)\
                .single().execute()

            if not scene_res.data:
                return None

            scene = scene_res.data

            # Fetch questions for this scene
            q_res = self.client.table('mystery_questions').select(
                'id, question_text, choices, is_deduction'
            ).eq('scene_id', scene['id'])\
                .order('created_at').execute()

            scene['questions'] = q_res.data or []
            return scene

        except Exception as e:
            logger.error(f"Error fetching scene {scene_number} for mystery {mystery_id}: {e}")
            return None

    def get_recommended_mysteries(self, user_id: str, language_id: int) -> List[Dict]:
        """Get ELO-matched mysteries for a user."""
        try:
            result = self.admin.rpc('get_recommended_mysteries', {
                'p_user_id': user_id,
                'p_language_id': language_id
            }).execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Error fetching recommended mysteries: {e}")
            return []

    # -------------------------------------------------------------------------
    # PROGRESS MANAGEMENT
    # -------------------------------------------------------------------------

    def get_or_create_progress(self, user_id: str, mystery_id: str,
                               mode: str = 'reading') -> Dict:
        """Get existing progress or create a new one."""
        try:
            # Check for existing progress
            existing = self.admin.table('mystery_progress').select('*')\
                .eq('user_id', user_id)\
                .eq('mystery_id', mystery_id)\
                .execute()

            if existing.data:
                return existing.data[0]

            # Fetch mystery suspects for initial notebook
            mystery = self.admin.table('mysteries').select('suspects')\
                .eq('id', mystery_id).single().execute()

            suspects_data = []
            if mystery.data and mystery.data.get('suspects'):
                raw_suspects = mystery.data['suspects']
                if isinstance(raw_suspects, str):
                    raw_suspects = json.loads(raw_suspects)
                suspects_data = [
                    {'name': s.get('name', ''), 'description': s.get('description', '')}
                    for s in raw_suspects
                ]

            initial_notebook = {
                'suspects': suspects_data,
                'clues': []
            }

            # Create new progress
            now = datetime.now(timezone.utc).isoformat()
            new_progress = {
                'user_id': user_id,
                'mystery_id': mystery_id,
                'current_scene': 1,
                'scene_responses': {},
                'notebook_state': initial_notebook,
                'mode': mode,
                'started_at': now,
                'updated_at': now,
            }

            result = self.admin.table('mystery_progress').insert(new_progress).execute()
            return result.data[0] if result.data else new_progress

        except Exception as e:
            logger.error(f"Error getting/creating progress: {e}")
            raise

    def submit_scene(self, user_id: str, mystery_id: str, scene_number: int,
                     responses: List[Dict]) -> Dict:
        """
        Submit answers for a scene. Returns clue if all correct.

        Args:
            responses: [{question_id, selected_answer}]

        Returns:
            {correct, question_results, clue_text?, notebook_state?}
        """
        try:
            # Get progress and validate ordering
            progress = self.admin.table('mystery_progress').select('*')\
                .eq('user_id', user_id)\
                .eq('mystery_id', mystery_id)\
                .single().execute()

            if not progress.data:
                return {'correct': False, 'error': 'No progress found. Start the mystery first.'}

            prog = progress.data

            if prog.get('completed_at'):
                return {'correct': False, 'error': 'Mystery already completed.'}

            if scene_number != prog['current_scene']:
                return {
                    'correct': False,
                    'error': f'Expected scene {prog["current_scene"]}, got {scene_number}.'
                }

            # Get scene and questions
            scene = self.admin.table('mystery_scenes').select('*')\
                .eq('mystery_id', mystery_id)\
                .eq('scene_number', scene_number)\
                .single().execute()

            if not scene.data:
                return {'correct': False, 'error': 'Scene not found.'}

            questions = self.admin.table('mystery_questions').select('*')\
                .eq('scene_id', scene.data['id'])\
                .order('created_at').execute()

            if not questions.data:
                return {'correct': False, 'error': 'No questions found for this scene.'}

            # Build response lookup
            response_map = {str(r['question_id']): r['selected_answer'] for r in responses}

            # Validate answers
            question_results = []
            all_correct = True

            for q in questions.data:
                q_id = str(q['id'])
                user_answer = response_map.get(q_id, '')
                correct_answer = q['answer']

                # Extract string from JSONB if needed
                if isinstance(correct_answer, dict):
                    correct_answer = correct_answer.get('text', str(correct_answer))
                elif isinstance(correct_answer, str):
                    try:
                        parsed = json.loads(correct_answer)
                        if isinstance(parsed, str):
                            correct_answer = parsed
                    except (json.JSONDecodeError, TypeError):
                        pass

                is_correct = (user_answer == correct_answer)
                if not is_correct:
                    all_correct = False

                question_results.append({
                    'question_id': q_id,
                    'is_correct': is_correct,
                })

            # Track attempt count for this scene
            scene_responses = prog.get('scene_responses', {}) or {}
            scene_key = str(scene_number)
            scene_entry = scene_responses.get(scene_key, {'attempts': 0})
            scene_entry['attempts'] = scene_entry.get('attempts', 0) + 1

            if all_correct:
                # Record success
                scene_entry['correct'] = True
                scene_entry['answers'] = [r['selected_answer'] for r in responses]
                scene_responses[scene_key] = scene_entry

                # Add clue to notebook
                notebook = prog.get('notebook_state', {'suspects': [], 'clues': []})
                if not isinstance(notebook, dict):
                    notebook = json.loads(notebook) if isinstance(notebook, str) else {'suspects': [], 'clues': []}

                clues = notebook.get('clues', [])
                clues.append({
                    'scene_number': scene_number,
                    'text': scene.data['clue_text'],
                    'clue_type': scene.data.get('clue_type', 'evidence'),
                })
                notebook['clues'] = clues

                # Advance to next scene
                next_scene = scene_number + 1
                now = datetime.now(timezone.utc).isoformat()

                update_data = {
                    'current_scene': next_scene,
                    'scene_responses': scene_responses,
                    'notebook_state': notebook,
                    'updated_at': now,
                }

                self.admin.table('mystery_progress').update(update_data)\
                    .eq('user_id', user_id)\
                    .eq('mystery_id', mystery_id)\
                    .execute()

                return {
                    'correct': True,
                    'question_results': question_results,
                    'clue_text': scene.data['clue_text'],
                    'clue_type': scene.data.get('clue_type', 'evidence'),
                    'notebook_state': notebook,
                    'next_scene': next_scene,
                    'transcript': scene.data['transcript'],
                }

            else:
                # Record failed attempt (don't advance)
                scene_responses[scene_key] = scene_entry
                self.admin.table('mystery_progress').update({
                    'scene_responses': scene_responses,
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                }).eq('user_id', user_id)\
                    .eq('mystery_id', mystery_id)\
                    .execute()

                return {
                    'correct': False,
                    'question_results': question_results,
                }

        except Exception as e:
            logger.error(f"Error submitting scene {scene_number}: {e}")
            raise

    def submit_finale(self, user_id: str, mystery_id: str,
                      responses: List[Dict]) -> Dict:
        """
        Submit the finale (scene 5) and trigger ELO + BKT processing.

        Args:
            responses: All responses across all 5 scenes
                       [{question_id, selected_answer}]

        Returns:
            ELO result + solution reveal
        """
        try:
            # Verify progress: scenes 1-4 must be complete
            progress = self.admin.table('mystery_progress').select('*')\
                .eq('user_id', user_id)\
                .eq('mystery_id', mystery_id)\
                .single().execute()

            if not progress.data:
                return {'success': False, 'error': 'No progress found.'}

            prog = progress.data

            if prog.get('completed_at'):
                return {'success': False, 'error': 'Mystery already completed.'}

            # Current scene should be 5 (scenes 1-4 are done) or 6 (scene 5 just completed)
            if prog['current_scene'] < 5:
                return {
                    'success': False,
                    'error': f'Not all scenes completed. Current: {prog["current_scene"]}'
                }

            # Get mystery for language_id and solution
            mystery = self.admin.table('mysteries').select(
                'language_id, solution_suspect, solution_reasoning'
            ).eq('id', mystery_id).single().execute()

            if not mystery.data:
                return {'success': False, 'error': 'Mystery not found.'}

            language_id = mystery.data['language_id']

            # Get mystery test_type_id
            mystery_type_id = DimensionService.get_test_type_id('mystery', self.admin)
            if not mystery_type_id:
                return {'success': False, 'error': 'Mystery test type not configured.'}

            # Build JSONB responses for RPC
            rpc_responses = json.dumps([
                {'question_id': str(r['question_id']), 'selected_answer': r['selected_answer']}
                for r in responses
            ])

            # Call the mystery submission RPC
            rpc_result = self.admin.rpc('process_mystery_submission', {
                'p_user_id': user_id,
                'p_mystery_id': mystery_id,
                'p_language_id': language_id,
                'p_test_type_id': mystery_type_id,
                'p_responses': rpc_responses,
                'p_idempotency_key': str(uuid4()),
            }).execute()

            result = rpc_result.data
            if isinstance(result, list) and result:
                result = result[0]

            if not result or not result.get('success'):
                error_msg = result.get('error', 'Unknown error') if result else 'RPC failed'
                logger.error(f"Mystery submission RPC failed: {error_msg}")
                return {'success': False, 'error': error_msg}

            # Mark progress as completed
            now = datetime.now(timezone.utc).isoformat()
            self.admin.table('mystery_progress').update({
                'completed_at': now,
                'updated_at': now,
            }).eq('user_id', user_id)\
                .eq('mystery_id', mystery_id)\
                .execute()

            # Return result with solution
            result['solution_suspect'] = mystery.data['solution_suspect']
            result['solution_reasoning'] = mystery.data['solution_reasoning']

            return result

        except Exception as e:
            logger.error(f"Error submitting mystery finale: {e}")
            raise

    # -------------------------------------------------------------------------
    # CREATION (for generation pipeline)
    # -------------------------------------------------------------------------

    def save_mystery(self, mystery_data: Dict, scenes: List[Dict],
                     questions_by_scene: Dict[int, List[Dict]]) -> str:
        """
        Save a complete mystery with scenes and questions.

        Args:
            mystery_data: Mystery metadata
            scenes: List of scene dicts
            questions_by_scene: {scene_number: [question_dicts]}

        Returns:
            Mystery slug
        """
        try:
            # Insert mystery
            mystery_result = self.admin.table('mysteries')\
                .insert(mystery_data).execute()

            if not mystery_result.data:
                raise Exception("Failed to insert mystery")

            mystery_id = mystery_result.data[0]['id']

            # Insert scenes and their questions
            for scene_data in scenes:
                scene_data['mystery_id'] = mystery_id
                scene_result = self.admin.table('mystery_scenes')\
                    .insert(scene_data).execute()

                if not scene_result.data:
                    raise Exception(f"Failed to insert scene {scene_data.get('scene_number')}")

                scene_id = scene_result.data[0]['id']
                scene_num = scene_data['scene_number']

                # Insert questions for this scene
                scene_questions = questions_by_scene.get(scene_num, [])
                for q_data in scene_questions:
                    q_data['scene_id'] = scene_id

                if scene_questions:
                    self.admin.table('mystery_questions')\
                        .insert(scene_questions).execute()

            # Create initial skill rating
            self.admin.table('mystery_skill_ratings').insert({
                'mystery_id': mystery_id,
                'elo_rating': 1400,
                'total_attempts': 0,
            }).execute()

            return mystery_data['slug']

        except Exception as e:
            logger.error(f"Error saving mystery: {e}")
            raise

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_mystery_ratings(self, mystery_ids: List[str]) -> Dict[str, int]:
        """Get ELO ratings for a list of mysteries."""
        if not mystery_ids:
            return {}

        try:
            result = self.admin.table('mystery_skill_ratings')\
                .select('mystery_id, elo_rating')\
                .in_('mystery_id', mystery_ids)\
                .execute()

            return {r['mystery_id']: r['elo_rating'] for r in (result.data or [])}

        except Exception as e:
            logger.error(f"Error fetching mystery ratings: {e}")
            return {}


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_mystery_service_instance: MysteryService = None


def get_mystery_service() -> MysteryService:
    """Get the singleton MysteryService instance."""
    global _mystery_service_instance
    if _mystery_service_instance is None:
        _mystery_service_instance = MysteryService()
    return _mystery_service_instance
