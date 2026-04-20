# services/vocabulary_ladder/exercise_renderer.py
"""
Ladder Exercise Renderer — Assets → Exercises Table

Transforms validated word_assets into concrete exercise rows in the exercises
table. No LLM calls — pure data transformation. Each level produces content
in the SAME JSON format as existing generators so the frontend renderers
work without modification.

This runs at admin upload time (offline), not in the request path.
"""

import logging
import random
from uuid import uuid4

from services.supabase_factory import get_supabase_admin
from services.vocabulary_ladder.config import (
    LADDER_LEVELS, compute_active_levels,
    SENTENCE_ASSIGNMENTS_A, SENTENCE_ASSIGNMENTS_B,
)

logger = logging.getLogger(__name__)


class LadderExerciseRenderer:
    """Renders word_assets into exercises table rows for each ladder level."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()

    def render_all(self, sense_id: int, language_id: int) -> list[dict]:
        """Render exercises for all active ladder levels for a word sense.

        Produces 2 exercises per level (variants A and B) when variant
        assets are available. Falls back to single-variant for legacy
        assets (prompt2_exercises / prompt3_transforms without suffix).

        Returns list of inserted exercise IDs.
        """
        assets = self._load_assets(sense_id)
        if not assets.get('prompt1_core'):
            logger.error("No valid prompt1_core for sense %s — cannot render", sense_id)
            return []

        core = assets['prompt1_core']

        semantic_class = core.get('semantic_class', '')
        active_levels = compute_active_levels(semantic_class)
        asset_ids = self._load_asset_ids(sense_id)
        tier = self._get_tier(core)

        # Build variant list based on available assets
        variant_configs = []
        if assets.get('prompt2_exercises_A') or assets.get('prompt3_transforms_A'):
            variant_configs.append({
                'key': 'A',
                'p2': assets.get('prompt2_exercises_A', {}),
                'p3': assets.get('prompt3_transforms_A', {}),
                'sentence_assignments': SENTENCE_ASSIGNMENTS_A,
            })
        if assets.get('prompt2_exercises_B') or assets.get('prompt3_transforms_B'):
            variant_configs.append({
                'key': 'B',
                'p2': assets.get('prompt2_exercises_B', {}),
                'p3': assets.get('prompt3_transforms_B', {}),
                'sentence_assignments': SENTENCE_ASSIGNMENTS_B,
            })

        # Fallback: legacy single-variant assets
        if not variant_configs:
            variant_configs.append({
                'key': 'A',
                'p2': assets.get('prompt2_exercises', {}),
                'p3': assets.get('prompt3_transforms', {}),
                'sentence_assignments': SENTENCE_ASSIGNMENTS_A,
            })

        rows = []
        for variant in variant_configs:
            p2 = variant['p2']
            p3 = variant['p3']
            sa = variant['sentence_assignments']

            for level in active_levels:
                try:
                    content = self._render_level(
                        level, core, p2, p3, sense_id, language_id, sa)
                    if content is None:
                        continue

                    exercise_type = LADDER_LEVELS[level]['exercise_type']
                    row = {
                        'id': str(uuid4()),
                        'language_id': language_id,
                        'exercise_type': exercise_type,
                        'source_type': 'vocabulary',
                        'content': content,
                        'tags': {
                            'ladder_level': level,
                            'semantic_class': semantic_class,
                            'variant': variant['key'],
                        },
                        'complexity_tier': tier,
                        'is_active': True,
                        'word_sense_id': sense_id,
                        'word_asset_id': asset_ids.get('prompt1_core'),
                        'ladder_level': level,
                    }
                    rows.append(row)

                except Exception as e:
                    logger.error("Error rendering L%d variant %s for sense %s: %s",
                                 level, variant['key'], sense_id, e)

        if rows:
            try:
                self.db.table('exercises').insert(rows).execute()
                logger.info("Rendered %d ladder exercises for sense %s", len(rows), sense_id)
            except Exception as e:
                logger.error("Failed to insert ladder exercises for sense %s: %s", sense_id, e)
                return []

        return [r['id'] for r in rows]

    # ------------------------------------------------------------------
    # Per-level renderers
    # ------------------------------------------------------------------

    def _render_level(
        self, level: int, core: dict, p2: dict, p3: dict,
        sense_id: int, language_id: int,
        sentence_assignments: dict[int, int] | None = None,
    ) -> dict | None:
        """Dispatch to the appropriate level renderer."""
        if sentence_assignments is None:
            sentence_assignments = SENTENCE_ASSIGNMENTS_A
        renderers = {
            1: self._render_phonetic,
            2: self._render_definition_match,
            3: self._render_cloze,
            4: self._render_morphology_slot,
            5: self._render_collocation_gap,
            6: self._render_semantic_discrimination,
            7: self._render_spot_incorrect,
            8: self._render_collocation_repair,
            9: self._render_jumbled,
        }
        renderer = renderers.get(level)
        if not renderer:
            return None
        return renderer(core, p2, p3, sense_id, language_id, sentence_assignments)

    def _render_phonetic(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L1: Phonetic/orthographic recognition.

        Content matches MCQ format: word, pronunciation, 4 options.
        """
        level_data = p2.get('level_1', {})
        if not level_data:
            return None

        options = level_data.get('options', [])
        if len(options) < 4:
            return None

        # Build option texts for MCQ
        option_texts = [o.get('text', '') for o in options]
        correct = [o.get('text', '') for o in options if o.get('is_correct')]
        correct_answer = correct[0] if correct else ''

        explanations = level_data.get('explanations', {})

        return {
            'word': correct_answer,
            'pronunciation': core.get('pronunciation', ''),
            'ipa': core.get('ipa', ''),
            'syllable_count': core.get('syllable_count'),
            'options': option_texts,
            'correct_answer': correct_answer,
            'explanation': explanations.get(correct_answer, ''),
            'distractor_explanations': {
                text: explanations.get(text, '')
                for text in option_texts if text != correct_answer
            },
        }

    def _render_definition_match(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L2: Definition match from database.

        Uses existing get_distractors() RPC for wrong definitions.
        """
        definition = core.get('definition', '')
        if not definition:
            return None

        # Get 3 distractor definitions from other words
        try:
            from services.vocabulary.knowledge_service import VocabularyKnowledgeService
            ks = VocabularyKnowledgeService(self.db)
            distractors = ks.get_distractors(sense_id, language_id, count=3)
        except Exception as e:
            logger.warning("Failed to get distractors for L2 sense %s: %s", sense_id, e)
            distractors = []

        if len(distractors) < 3:
            return None

        options = [definition] + distractors[:3]
        random.shuffle(options)

        # Get the lemma
        sentences = core.get('sentences', [])
        word = sentences[0].get('target_substring', '') if sentences else ''

        return {
            'word': word,
            'pronunciation': core.get('pronunciation', ''),
            'correct_definition': definition,
            'options': options,
        }

    def _render_cloze(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L3: Cloze completion.

        Output format matches existing ClozeGenerator:
        {sentence_with_blank, original_sentence, correct_answer, options, explanation}
        """
        level_data = p2.get('level_3', {})
        if not level_data:
            return None

        sent_idx = level_data.get('sentence_index', sa.get(3, 0))
        sentences = core.get('sentences', [])
        if sent_idx >= len(sentences):
            return None

        sentence = sentences[sent_idx]
        text = sentence.get('text', '')
        target = sentence.get('target_substring', '')
        if not text or not target:
            return None

        blanked = text.replace(target, '___', 1)

        options_data = level_data.get('options', [])
        correct = level_data.get('correct_answer', target)
        distractors = [
            o.get('text', '') for o in options_data
            if not o.get('is_correct') and o.get('text')
        ]

        option_list = [correct] + distractors[:3]
        random.shuffle(option_list)

        explanations = level_data.get('explanations', {})

        return {
            'sentence_with_blank': blanked,
            'original_sentence': text,
            'correct_answer': correct,
            'options': option_list,
            'explanation': explanations.get(correct, ''),
            'distractor_tags': {},
            'word_definition': core.get('definition', ''),
            'target_word': target,
        }

    def _render_morphology_slot(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L4: Morphology slot fill.

        Shows sentence with blank, 4 morphological form options.
        """
        level_data = p3.get('level_4', {})
        if not level_data:
            return None

        sent_idx = level_data.get('sentence_index', sa.get(4, 1))
        sentences = core.get('sentences', [])
        if sent_idx >= len(sentences):
            return None

        sentence = sentences[sent_idx]
        text = sentence.get('text', '')
        target = sentence.get('target_substring', '')
        if not text or not target:
            return None

        blanked = text.replace(target, '___', 1)

        correct_form = level_data.get('correct_form', target)
        base_form = level_data.get('base_form', '')
        form_label = level_data.get('form_label', '')

        options_data = level_data.get('options', [])
        distractors = [
            o.get('text', '') for o in options_data
            if not o.get('is_correct') and o.get('text')
        ]
        option_list = [correct_form] + distractors[:3]
        random.shuffle(option_list)

        explanations = level_data.get('explanations', {})

        return {
            'sentence_with_blank': blanked,
            'original_sentence': text,
            'correct_answer': correct_form,
            'base_form': base_form,
            'form_label': form_label,
            'options': option_list,
            'explanation': explanations.get(correct_form, ''),
            'word_definition': core.get('definition', ''),
            'target_word': target,
        }

    def _render_collocation_gap(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L5: Collocation gap fill.

        Output format matches existing CollocationGapFillGenerator:
        {sentence, correct, options, collocation}
        """
        level_data = p2.get('level_5')
        if not level_data:
            return None

        sent_idx = level_data.get('sentence_index', sa.get(5, 2))
        sentences = core.get('sentences', [])
        if sent_idx >= len(sentences):
            return None

        sentence = sentences[sent_idx]
        text = sentence.get('text', '')
        collocate = level_data.get('correct_collocate', '')
        if not text or not collocate:
            return None

        blanked = text.replace(collocate, '___', 1)
        if '___' not in blanked:
            # Collocate not found in sentence — skip
            return None

        options_data = level_data.get('options', [])
        distractors = [
            o.get('text', '') for o in options_data
            if not o.get('is_correct') and o.get('text')
        ]
        option_list = [collocate] + distractors[:3]
        random.shuffle(option_list)

        return {
            'sentence': blanked,
            'correct': collocate,
            'options': option_list,
            'collocation': f"{sentence.get('target_substring', '')} + {collocate}",
        }

    def _render_semantic_discrimination(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L6: Semantic discrimination.

        Output format matches existing SemanticDiscrimGenerator:
        {sentences: [{text, is_correct}], explanation, target_word}
        """
        level_data = p2.get('level_6', {})
        if not level_data:
            return None

        correct_idx = level_data.get('correct_sentence_index', sa.get(6, 3))
        sentences = core.get('sentences', [])
        if correct_idx >= len(sentences):
            return None

        correct_sent = sentences[correct_idx]
        wrong_sents = level_data.get('wrong_sentences', [])
        if len(wrong_sents) < 3:
            return None

        all_sentences = [
            {'text': correct_sent.get('text', ''), 'is_correct': True},
        ]
        for ws in wrong_sents[:3]:
            all_sentences.append({
                'text': ws.get('text', ''),
                'is_correct': False,
            })

        random.shuffle(all_sentences)

        # Collect explanations
        explanation_parts = [ws.get('explanation', '') for ws in wrong_sents if ws.get('explanation')]
        explanation = ' '.join(explanation_parts) if explanation_parts else ''

        return {
            'sentences': all_sentences,
            'explanation': explanation,
            'target_word': correct_sent.get('target_substring', ''),
        }

    def _render_spot_incorrect(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L7: Spot incorrect sentence.

        Output format matches existing SpotIncorrectGenerator:
        {sentences: [{text, is_correct, error_description?}]}
        """
        level_data = p3.get('level_7', {})
        if not level_data:
            return None

        incorrect = level_data.get('incorrect_sentence', '')
        error_desc = level_data.get('error_description', '')
        correct_indices = level_data.get('correct_sentence_indices', [0, 1, 2])

        sentences = core.get('sentences', [])
        all_sents = []

        for idx in correct_indices:
            if idx < len(sentences):
                all_sents.append({
                    'text': sentences[idx].get('text', ''),
                    'is_correct': True,
                })

        if not incorrect:
            return None

        all_sents.append({
            'text': incorrect,
            'is_correct': False,
            'error_description': error_desc,
        })

        random.shuffle(all_sents)
        return {'sentences': all_sents}

    def _render_collocation_repair(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L8: Collocation repair.

        Output format matches existing CollocationRepairGenerator:
        {sentence_with_error, error_word, correct_word, explanation}
        """
        level_data = p3.get('level_8')
        if not level_data:
            return None

        sent_idx = level_data.get('sentence_index', sa.get(8, 4))
        sentences = core.get('sentences', [])
        if sent_idx >= len(sentences):
            return None

        sentence = sentences[sent_idx]
        text = sentence.get('text', '')
        correct_collocate = level_data.get('correct_collocate', '')
        error_collocate = level_data.get('error_collocate', '')

        if not text or not correct_collocate or not error_collocate:
            return None

        # Replace correct collocate with the error collocate in the sentence
        sentence_with_error = text.replace(correct_collocate, error_collocate, 1)

        explanations = level_data.get('explanations', {})

        return {
            'sentence_with_error': sentence_with_error,
            'error_word': error_collocate,
            'correct_word': correct_collocate,
            'explanation': explanations.get(correct_collocate, ''),
        }

    def _render_jumbled(self, core, p2, p3, sense_id, language_id, sa) -> dict | None:
        """L9: Jumbled sentence via local chunking.

        Uses the sentence specified by sentence_assignments for this variant.
        """
        sentences = core.get('sentences', [])
        sent_idx = sa.get(9, 5)
        if sent_idx >= len(sentences):
            sent_idx = len(sentences) - 1
        if sent_idx < 0:
            return None

        sentence = sentences[sent_idx]
        text = sentence.get('text', '')
        if not text:
            return None

        # Store minimal content; chunking happens at serve time
        return {
            'original_sentence': text,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_assets(self, sense_id: int) -> dict:
        """Load all valid word_assets for a sense, keyed by asset_type."""
        try:
            resp = (
                self.db.table('word_assets')
                .select('asset_type, content')
                .eq('sense_id', sense_id)
                .eq('is_valid', True)
                .execute()
            )
            return {row['asset_type']: row['content'] for row in (resp.data or [])}
        except Exception as e:
            logger.error("Failed to load assets for sense %s: %s", sense_id, e)
            return {}

    def _load_asset_ids(self, sense_id: int) -> dict:
        """Load word_asset IDs for FK reference."""
        try:
            resp = (
                self.db.table('word_assets')
                .select('id, asset_type')
                .eq('sense_id', sense_id)
                .eq('is_valid', True)
                .execute()
            )
            return {row['asset_type']: row['id'] for row in (resp.data or [])}
        except Exception as e:
            logger.error("Failed to load asset IDs for sense %s: %s", sense_id, e)
            return {}

    def _get_tier(self, core: dict) -> str | None:
        """Extract complexity tier from the first sentence."""
        sentences = core.get('sentences', [])
        if sentences:
            return sentences[0].get('complexity_tier')
        return None
