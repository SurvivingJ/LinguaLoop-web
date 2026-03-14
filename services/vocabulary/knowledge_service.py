"""
Vocabulary Knowledge Service — BKT wrapper

Thin Python wrapper around SQL BKT functions. All heavy logic
(Bayesian update, status derivation, frequency priors) lives in
PostgreSQL — this service just calls the RPCs and formats results.

SQL functions called:
- update_vocabulary_from_test       (comprehension signal)
- update_vocabulary_from_word_test  (strong word-test signal)
- get_word_quiz_candidates          (uncertain-zone words for quiz)
- get_distractors                   (MCQ wrong answers)
"""

import logging
from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


class VocabularyKnowledgeService:
    """Wraps BKT SQL functions for vocabulary tracking."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()

    def update_from_comprehension(
        self, user_id: str, language_id: int, question_results: list[dict]
    ) -> list[dict]:
        """
        Update BKT after a comprehension test submission.

        Args:
            user_id: UUID string
            language_id: e.g. 1 for Chinese
            question_results: [{"question_id": uuid_str, "is_correct": bool}, ...]

        Returns:
            List of {sense_id, p_known_before, p_known_after, status}
        """
        try:
            response = self.db.rpc('update_vocabulary_from_test', {
                'p_user_id': user_id,
                'p_language_id': language_id,
                'p_question_results': question_results,
            }).execute()

            results = response.data or []
            logger.info(
                f"BKT comprehension update: user={user_id}, "
                f"{len(question_results)} questions → {len(results)} senses updated"
            )

            # Auto-create flashcards for words entering the learning zone
            self._auto_create_flashcards(user_id, language_id, results)

            return results

        except Exception as e:
            logger.error(f"BKT comprehension update failed: {e}")
            return []

    def update_from_word_test(
        self, user_id: str, sense_id: int, is_correct: bool, language_id: int
    ) -> dict | None:
        """
        Update BKT after a single word quiz answer (strong signal).

        Returns:
            {sense_id, p_known_before, p_known_after, status} or None
        """
        try:
            response = self.db.rpc('update_vocabulary_from_word_test', {
                'p_user_id': user_id,
                'p_sense_id': sense_id,
                'p_is_correct': is_correct,
                'p_language_id': language_id,
            }).execute()

            results = response.data or []
            if results:
                row = results[0]
                logger.debug(
                    f"BKT word test: sense={sense_id}, "
                    f"correct={is_correct}, "
                    f"p_known {row.get('out_p_known_before')} → {row.get('out_p_known_after')}"
                )
                return row
            return None

        except Exception as e:
            logger.error(f"BKT word test update failed: {e}")
            return None

    def get_word_quiz_candidates(
        self, user_id: str, sense_ids: list[int], language_id: int, max_words: int = 5
    ) -> list[dict]:
        """
        Get uncertain-zone words for the post-test word quiz.

        Returns candidates ranked by information gain, each with
        sense_id, lemma, definition, pronunciation, p_known, score.
        """
        if not sense_ids:
            return []

        try:
            response = self.db.rpc('get_word_quiz_candidates', {
                'p_user_id': user_id,
                'p_sense_ids': sense_ids,
                'p_language_id': language_id,
                'p_max_words': max_words,
            }).execute()

            candidates = response.data or []
            logger.info(
                f"Word quiz candidates: {len(candidates)} from {len(sense_ids)} sense_ids"
            )
            return candidates

        except Exception as e:
            logger.error(f"Word quiz candidate selection failed: {e}")
            return []

    def get_distractors(
        self, sense_id: int, language_id: int, count: int = 3
    ) -> list[str]:
        """
        Get distractor definitions for a word quiz MCQ.

        Returns list of wrong-answer definition strings.
        """
        try:
            response = self.db.rpc('get_distractors', {
                'p_sense_id': sense_id,
                'p_language_id': language_id,
                'p_count': count,
            }).execute()

            return [row['out_definition'] for row in (response.data or [])]

        except Exception as e:
            logger.error(f"Distractor generation failed: {e}")
            return []

    def build_quiz_with_distractors(
        self, user_id: str, sense_ids: list[int], language_id: int, max_words: int = 5
    ) -> list[dict]:
        """
        Get quiz candidates with shuffled answer options (1 correct + 3 distractors).

        Returns ready-to-render quiz data for the frontend.
        """
        import random

        candidates = self.get_word_quiz_candidates(
            user_id, sense_ids, language_id, max_words
        )

        quiz_items = []
        for c in candidates:
            sid = c.get('out_sense_id') or c.get('sense_id')
            correct_def = c.get('out_definition') or c.get('definition', '')
            distractors = self.get_distractors(sid, language_id)

            if len(distractors) < 2:
                continue  # Not enough distractors — skip this word

            options = [correct_def] + distractors
            random.shuffle(options)

            quiz_items.append({
                'sense_id': sid,
                'lemma': c.get('out_lemma') or c.get('lemma', ''),
                'pronunciation': c.get('out_pronunciation') or c.get('pronunciation', ''),
                'correct_definition': correct_def,
                'options': options,
                'p_known': float(c.get('out_p_known') or c.get('p_known', 0)),
            })

        return quiz_items

    def record_word_quiz_results(
        self, user_id: str, attempt_id: str | None, results: list[dict], language_id: int
    ) -> list[dict]:
        """
        Record word quiz results and update BKT for each answer.

        Args:
            results: [{"sense_id": int, "selected_answer": str, "is_correct": bool,
                        "response_time_ms": int}, ...]

        Returns:
            List of BKT update results per word.
        """
        bkt_updates = []

        for r in results:
            # Insert quiz result row
            try:
                row = {
                    'user_id': user_id,
                    'sense_id': r['sense_id'],
                    'is_correct': r['is_correct'],
                    'selected_answer': r.get('selected_answer'),
                    'correct_answer': r.get('correct_answer'),
                    'response_time_ms': r.get('response_time_ms'),
                }
                if attempt_id:
                    row['attempt_id'] = attempt_id

                self.db.table('word_quiz_results').insert(row).execute()
            except Exception as e:
                logger.error(f"Failed to insert quiz result for sense {r['sense_id']}: {e}")

            # Update BKT (strong signal)
            bkt_result = self.update_from_word_test(
                user_id=user_id,
                sense_id=r['sense_id'],
                is_correct=r['is_correct'],
                language_id=language_id,
            )
            if bkt_result:
                bkt_updates.append(bkt_result)

        return bkt_updates

    def _auto_create_flashcards(
        self, user_id: str, language_id: int, bkt_results: list[dict]
    ):
        """
        Auto-create flashcards for words that moved into encountered/learning status.

        Only creates cards for senses that don't already have a flashcard.
        """
        from services.vocabulary.fsrs import difficulty_from_p_known

        # Filter to words in the learning zone
        eligible_statuses = {'encountered', 'learning'}
        eligible = [
            r for r in bkt_results
            if (r.get('out_status') or r.get('status', '')) in eligible_statuses
        ]

        if not eligible:
            return

        sense_ids = [r.get('out_sense_id') or r.get('sense_id') for r in eligible]

        # Check which already have flashcards
        try:
            existing = self.db.table('user_flashcards') \
                .select('sense_id') \
                .eq('user_id', user_id) \
                .in_('sense_id', sense_ids) \
                .execute()

            existing_ids = {r['sense_id'] for r in (existing.data or [])}
        except Exception as e:
            logger.error(f"Failed to check existing flashcards: {e}")
            return

        # Create new flashcards
        new_cards = []
        for r in eligible:
            sid = r.get('out_sense_id') or r.get('sense_id')
            if sid in existing_ids:
                continue

            p_known = float(r.get('out_p_known_after') or r.get('p_known', 0.1))
            difficulty = difficulty_from_p_known(p_known)

            new_cards.append({
                'user_id': user_id,
                'sense_id': sid,
                'language_id': language_id,
                'difficulty': difficulty,
                'state': 'new',
            })

        if not new_cards:
            return

        try:
            # Fetch example sentences for the new cards
            new_sense_ids = [c['sense_id'] for c in new_cards]
            senses_resp = self.db.table('dim_word_senses') \
                .select('id, example_sentence') \
                .in_('id', new_sense_ids) \
                .execute()

            sentence_map = {
                r['id']: r.get('example_sentence', '')
                for r in (senses_resp.data or [])
            }

            for card in new_cards:
                card['example_sentence'] = sentence_map.get(card['sense_id'], '')

            self.db.table('user_flashcards').insert(new_cards).execute()
            logger.info(f"Auto-created {len(new_cards)} flashcards for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to auto-create flashcards: {e}")
