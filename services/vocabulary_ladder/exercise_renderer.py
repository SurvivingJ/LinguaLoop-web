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
    get_sentence_target,
)

logger = logging.getLogger(__name__)


class LadderExerciseRenderer:
    """Renders word_assets into exercises table rows for each ladder level."""

    def __init__(self, db=None, audio_synthesizer=None):
        self.db = db or get_supabase_admin()
        self.audio_synthesizer = audio_synthesizer

    def render_all(self, sense_id: int, language_id: int) -> list[dict]:
        """Render exercises for all active ladder levels and insert them.

        Builds the rows in memory (see :meth:`build_rows`) then inserts them.
        Returns the list of inserted exercise IDs. Note: this is a plain
        insert with no de-duplication — callers that re-render an existing
        sense must clear the old rows themselves (or use ``build_rows`` and
        own the delete/insert ordering, as ``_do_vocab_generate`` does for
        non-destructive regeneration).
        """
        rows = self.build_rows(sense_id, language_id)
        if not rows:
            return []
        try:
            self.db.table('exercises').insert(rows).execute()
            logger.info("Rendered %d ladder exercises for sense %s", len(rows), sense_id)
        except Exception as e:
            logger.error("Failed to insert ladder exercises for sense %s: %s", sense_id, e)
            return []
        return [r['id'] for r in rows]

    def build_rows(self, sense_id: int, language_id: int) -> list[dict]:
        """Build exercise rows for all active ladder levels — no DB writes.

        Produces 2 exercises per level (variants A and B) when variant
        assets are available. Falls back to single-variant for legacy
        assets (prompt2_exercises / prompt3_transforms without suffix).

        Returns the fully-formed exercise row dicts (each with a generated
        ``id``) ready to be inserted. Returns ``[]`` when there is no valid
        prompt1_core asset to render from, which lets callers detect a failed
        render and avoid destroying a previously-good exercise set.
        """
        assets = self._load_assets(sense_id)
        if not assets.get('prompt1_core'):
            logger.error("No valid prompt1_core for sense %s — cannot render", sense_id)
            return []

        core = assets['prompt1_core']

        semantic_class = core.get('semantic_class', '')
        active_levels = compute_active_levels(semantic_class, language_id)
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

                    # Lift any per-render judge sidecars into tags. Renderers may
                    # attach __judge_metas={judge_key: meta} for one or more
                    # judges; each lands under a '<judge_key>_judge' tag key. The
                    # legacy single __judge_meta (L3 cloze) is still read and
                    # mapped to the cloze_judge key so its output is unchanged.
                    judge_metas = content.pop('__judge_metas', None) or {}
                    legacy_meta = content.pop('__judge_meta', None)
                    if legacy_meta is not None:
                        judge_metas.setdefault('cloze', legacy_meta)

                    exercise_type = LADDER_LEVELS[level]['exercise_type']
                    tags = {
                        'ladder_level': level,
                        'semantic_class': semantic_class,
                        'variant': variant['key'],
                    }
                    for judge_key, meta in judge_metas.items():
                        if meta is not None:
                            tags[f'{judge_key}_judge'] = meta

                    row = {
                        'id': str(uuid4()),
                        'language_id': language_id,
                        'exercise_type': exercise_type,
                        'source_type': 'vocabulary',
                        'content': content,
                        'tags': tags,
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

        return rows

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

        Content matches MCQ format: word, pronunciation, 4 options, plus an
        audio_url of the spoken target so the frontend can play it.
        """
        from services.exercise_generation.judges.l1_distractor import filter_l1_distractors

        level_data = p2.get('level_1', {})
        if not level_data:
            return None

        options = level_data.get('options', [])
        if len(options) < 4:
            return None

        correct = [o.get('text', '') for o in options if o.get('is_correct')]
        correct_answer = correct[0] if correct else ''
        if not correct_answer:
            return None

        explanations = level_data.get('explanations', {})

        # L1 is a listening exercise — route distractors through the L1 judge to
        # drop real-word synonyms and spelling-only look-alikes that aren't
        # audio-confusable. Skip the variant if fewer than 3 clean distractors
        # survive (same contract as the L3 cloze path).
        raw_distractors = [
            o.get('text', '') for o in options
            if not o.get('is_correct') and o.get('text')
        ]
        kept, judge_meta = filter_l1_distractors(
            self.db, correct_answer, raw_distractors, language_id,
        )
        if len(kept) < 3:
            logger.info(
                "L1 l1_distractor_judge kept %d/%d distractors for sense %s; skipping variant",
                len(kept), len(raw_distractors), sense_id,
            )
            return None

        kept = kept[:3]
        option_texts = [correct_answer] + kept
        random.shuffle(option_texts)

        audio_url = self._generate_l1_audio(correct_answer, sense_id, language_id)

        return {
            'word': correct_answer,
            'pronunciation': core.get('pronunciation', ''),
            'ipa': core.get('ipa', ''),
            'syllable_count': core.get('syllable_count'),
            'audio_url': audio_url,
            'options': option_texts,
            'correct_answer': correct_answer,
            'explanation': explanations.get(correct_answer, ''),
            'distractor_explanations': {
                text: explanations.get(text, '') for text in kept
            },
            '__judge_metas': {'l1_distractor': judge_meta},
        }

    def _generate_l1_audio(self, target: str, sense_id: int, language_id: int) -> str | None:
        """TTS the L1 target word and upload to R2.

        Returns the public URL, or None if no synthesizer is configured /
        generation fails. The slug is deterministic per (sense, language)
        so re-rendering reuses the existing R2 object.
        """
        if not self.audio_synthesizer or not target:
            return None
        try:
            from services.exercise_generation.audio_voice import pick_voice
            voice, speed = pick_voice(self.db, language_id)
            slug = f'l1_{sense_id}_{language_id}'
            return self.audio_synthesizer.generate_and_upload(
                text=target,
                file_id=slug,
                voice=voice,
                speed=speed,
            )
        except Exception as exc:
            logger.warning("L1 audio generation failed for sense %s lang %s: %s",
                           sense_id, language_id, exc)
            return None

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
        word = get_sentence_target(sentences[0]) if sentences else ''

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

        Distractors are routed through cloze_judge to drop any that could
        themselves pass as the correct answer. If fewer than 3 survive the
        judge, the L3 variant is skipped (returns None) and the caller
        either falls back to the alternate variant pool or omits L3.
        """
        from services.exercise_generation.cloze_judge import filter_distractors

        level_data = p2.get('level_3', {})
        if not level_data:
            return None

        sent_idx = level_data.get('sentence_index', sa.get(3, 0))
        sentences = core.get('sentences', [])
        if sent_idx >= len(sentences):
            return None

        sentence = sentences[sent_idx]
        text = sentence.get('text', '')
        target = get_sentence_target(sentence)
        if not text or not target:
            return None

        blanked = text.replace(target, '___', 1)

        options_data = level_data.get('options', [])
        correct = level_data.get('correct_answer', target)
        distractors = [
            o.get('text', '') for o in options_data
            if not o.get('is_correct') and o.get('text')
        ][:3]

        kept, judge_meta = filter_distractors(
            self.db,
            sentence_with_blank=blanked,
            correct_answer=correct,
            distractors=distractors,
            language_id=language_id,
        )
        if len(kept) < 3:
            logger.info(
                "L3 cloze_judge rejected %d/%d distractors for sense %s; skipping variant",
                judge_meta['rejected'], len(distractors), sense_id,
            )
            return None

        option_list = [correct] + kept[:3]
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
            '__judge_meta': judge_meta,
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
        target = get_sentence_target(sentence)
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

        target_word = get_sentence_target(sentence)
        options_data = level_data.get('options', [])
        raw_distractors = [
            o.get('text', '') for o in options_data
            if not o.get('is_correct') and o.get('text')
        ]

        # Route distractors through the collocation judge: drop any distractor
        # that is itself a valid collocate of the target (an also-correct
        # answer). Skip the variant if fewer than 3 clean distractors survive
        # (same contract as the L3 cloze path).
        from services.exercise_generation.judges.collocation import filter_collocation_distractors
        kept, judge_meta = filter_collocation_distractors(
            self.db, blanked, target_word, collocate, raw_distractors, language_id,
        )
        if len(kept) < 3:
            logger.info(
                "L5 collocation_judge kept %d/%d distractors for sense %s; skipping variant",
                len(kept), len(raw_distractors), sense_id,
            )
            return None

        option_list = [collocate] + kept[:3]
        random.shuffle(option_list)

        return {
            'sentence': blanked,
            'correct': collocate,
            'options': option_list,
            'collocation': f"{target_word} + {collocate}",
            '__judge_metas': {'collocation': judge_meta},
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

        target_word = get_sentence_target(correct_sent)

        # Judge each crafted-wrong sentence against its labeled reason (its
        # explanation): drop any that is actually acceptable, or wrong for a
        # different reason than labeled. L6 needs exactly 3 wrong + 1 correct,
        # so skip the variant if fewer than 3 clean wrong sentences survive.
        from services.exercise_generation.judges.sentence_validity import judge_wrong_sentences
        pairs = [(ws.get('text', ''), ws.get('explanation', '')) for ws in wrong_sents]
        outcomes = judge_wrong_sentences(self.db, target_word, pairs, language_id)
        kept_wrong = [
            ws for ws, o in zip(wrong_sents, outcomes) if o.verdict != 'reject'
        ]
        rejected_items = [
            ws.get('text', '') for ws, o in zip(wrong_sents, outcomes)
            if o.verdict == 'reject'
        ]
        if len(kept_wrong) < 3:
            logger.info(
                "L6 sentence_validity_judge kept %d/%d wrong sentences for sense %s; skipping variant",
                len(kept_wrong), len(wrong_sents), sense_id,
            )
            return None

        judge_meta = {
            'rejected':       len(rejected_items),
            'kept':           len(kept_wrong),
            'rejected_items': rejected_items,
        }
        kept_wrong = kept_wrong[:3]

        all_sentences = [
            {'text': correct_sent.get('text', ''), 'is_correct': True},
        ]
        for ws in kept_wrong:
            all_sentences.append({
                'text': ws.get('text', ''),
                'is_correct': False,
            })

        random.shuffle(all_sentences)

        # Collect explanations for the kept wrong sentences only.
        explanation_parts = [ws.get('explanation', '') for ws in kept_wrong if ws.get('explanation')]
        explanation = ' '.join(explanation_parts) if explanation_parts else ''

        return {
            'sentences': all_sentences,
            'explanation': explanation,
            'target_word': target_word,
            '__judge_metas': {'sentence_validity': judge_meta},
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

        # Judge the single crafted-wrong sentence against its labeled error
        # description: if it is actually acceptable, or wrong for a different
        # reason than labeled, drop the variant — there would be nothing valid
        # to spot.
        from services.exercise_generation.judges.sentence_validity import judge_wrong_sentences
        target_word = (
            get_sentence_target(sentences[correct_indices[0]])
            if correct_indices and correct_indices[0] < len(sentences) else ''
        )
        outcomes = judge_wrong_sentences(
            self.db, target_word, [(incorrect, error_desc)], language_id,
        )
        if outcomes and outcomes[0].verdict == 'reject':
            logger.info(
                "L7 sentence_validity_judge rejected the incorrect sentence for sense %s; skipping variant",
                sense_id,
            )
            return None

        outcome = outcomes[0] if outcomes else None
        judge_meta = {
            'rejected':   0,
            'kept':       1,
            'verdict':    outcome.verdict if outcome else 'accept',
            'confidence': outcome.confidence if outcome else 5.0,
        }

        all_sents.append({
            'text': incorrect,
            'is_correct': False,
            'error_description': error_desc,
        })

        random.shuffle(all_sents)
        return {'sentences': all_sents, '__judge_metas': {'sentence_validity': judge_meta}}

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

        # Semantic correctness check (replaces the old _l8_correctness_ok
        # string-match retry in prompt3_transforms): the planted error word must
        # be a genuine NON-collocate of the target. If the judge finds it could
        # pass as a valid collocate, the repair exercise is broken — drop it.
        from services.exercise_generation.judges.collocation import judge_collocation_repair
        target_word = get_sentence_target(sentence)
        outcome = judge_collocation_repair(
            self.db, text, target_word, correct_collocate, error_collocate, language_id,
        )
        if outcome.verdict == 'reject':
            logger.info(
                "L8 collocation_judge rejected error_collocate '%s' for sense %s; skipping variant",
                error_collocate, sense_id,
            )
            return None

        judge_meta = {
            'rejected':   0,
            'kept':       1,
            'verdict':    outcome.verdict,
            'confidence': outcome.confidence,
            'reason':     outcome.reason,
        }

        # Replace correct collocate with the error collocate in the sentence
        sentence_with_error = text.replace(correct_collocate, error_collocate, 1)

        explanations = level_data.get('explanations', {})

        return {
            'sentence_with_error': sentence_with_error,
            'error_word': error_collocate,
            'correct_word': correct_collocate,
            'explanation': explanations.get(correct_collocate, ''),
            '__judge_metas': {'collocation': judge_meta},
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
