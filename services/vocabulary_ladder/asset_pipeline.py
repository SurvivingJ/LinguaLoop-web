# services/vocabulary_ladder/asset_pipeline.py
"""
Vocabulary Asset Pipeline Orchestrator

Runs Prompts 1-3 sequentially for a word sense, validates outputs,
and stores immutable assets in the word_assets table. This is the
offline pipeline — runs at admin upload time, not in the request path.

Usage:
    pipeline = VocabAssetPipeline()
    result = pipeline.generate_for_sense(sense_id=42, language_id=2)
    # result = {'sense_id': 42, 'assets': {...}, 'errors': [...]}
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from uuid import uuid4

from services.supabase_factory import get_supabase_admin
from services.vocabulary_ladder.config import (
    compute_active_levels,
    SENTENCE_ASSIGNMENTS_A, SENTENCE_ASSIGNMENTS_B,
    L7_CORRECT_INDICES_A, L7_CORRECT_INDICES_B,
)
from services.vocabulary_ladder.asset_generators.prompt1_core import CoreAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt2_exercises import ExerciseAssetGenerator
from services.vocabulary_ladder.asset_generators.prompt3_transforms import TransformAssetGenerator
from services.vocabulary_ladder.validators import VocabAssetValidator

logger = logging.getLogger(__name__)


class VocabAssetPipeline:
    """Orchestrates the three-prompt asset generation for vocabulary words."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()
        self.validator = VocabAssetValidator()

    def generate_for_sense(
        self,
        sense_id: int,
        language_id: int,
        force: bool = False,
        batch_id: str | None = None,
    ) -> dict:
        """Generate all assets for a single word sense.

        Runs Prompt 1 once (10 sentences), then Prompts 2 and 3 twice each
        (variants A and B) using different sentence assignments. Variants
        run in parallel for latency parity with the old single-variant path.

        Args:
            sense_id: The dim_word_senses ID.
            language_id: Language ID (2 = English).
            force: If True, regenerate even if assets exist.
            batch_id: Optional batch UUID for tracking.

        Returns:
            {'sense_id': int, 'status': 'success'|'partial'|'failed', 'errors': [...]}
        """
        result = {'sense_id': sense_id, 'status': 'failed', 'errors': []}
        batch_id = batch_id or str(uuid4())

        # Check existing assets
        if not force and self._assets_exist(sense_id):
            result['status'] = 'skipped'
            return result

        # Step 1: Fetch corpus sentences (reuse existing content)
        corpus_sentences = self._fetch_corpus_sentences(sense_id, language_id)

        # Step 2: Run Prompt 1 — Core classification + 10 sentences
        p1_gen = CoreAssetGenerator(self.db, language_id)
        core_asset = p1_gen.generate(sense_id, corpus_sentences)

        if core_asset is None:
            result['errors'].append('Prompt 1 generation failed')
            return result

        p1_valid, p1_errors = self.validator.validate_prompt1(core_asset)
        if not p1_valid:
            result['errors'].extend(p1_errors)
            self._store_asset(sense_id, language_id, 'prompt1_core', core_asset,
                              p1_gen.model, batch_id, is_valid=False,
                              validation_errors=p1_errors)
            return result

        self._store_asset(sense_id, language_id, 'prompt1_core', core_asset,
                          p1_gen.model, batch_id)
        self._update_vocabulary_metadata(sense_id, core_asset)

        semantic_class = core_asset.get('semantic_class', '')
        active_levels = compute_active_levels(semantic_class)

        # Step 3: Run Prompts 2A, 2B, 3A, 3B in parallel
        p2_gen = ExerciseAssetGenerator(self.db, language_id)
        p3_gen = TransformAssetGenerator(self.db, language_id)

        variants = {
            'A': {
                'sentence_assignments': SENTENCE_ASSIGNMENTS_A,
                'l7_correct_indices': L7_CORRECT_INDICES_A,
            },
            'B': {
                'sentence_assignments': SENTENCE_ASSIGNMENTS_B,
                'l7_correct_indices': L7_CORRECT_INDICES_B,
            },
        }

        variant_results = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {}
            for variant_key, cfg in variants.items():
                # Submit P2 variant
                futures[pool.submit(
                    p2_gen.generate, sense_id, core_asset, active_levels,
                    cfg['sentence_assignments'],
                )] = ('p2', variant_key)
                # Submit P3 variant
                futures[pool.submit(
                    p3_gen.generate, sense_id, core_asset, active_levels,
                    cfg['sentence_assignments'], cfg['l7_correct_indices'],
                )] = ('p3', variant_key)

            for future in as_completed(futures):
                prompt_type, variant_key = futures[future]
                try:
                    asset = future.result()
                    variant_results[(prompt_type, variant_key)] = asset
                except Exception as e:
                    logger.error("Variant %s_%s failed for sense %s: %s",
                                 prompt_type, variant_key, sense_id, e)
                    variant_results[(prompt_type, variant_key)] = None

        # Step 4: Validate and store each variant
        for variant_key in ('A', 'B'):
            # P2 variant
            p2_asset = variant_results.get(('p2', variant_key))
            asset_type = f'prompt2_exercises_{variant_key}'
            if p2_asset is None:
                result['errors'].append(f'Prompt 2 variant {variant_key} generation failed')
            else:
                p2_valid, p2_errors = self.validator.validate_prompt2(p2_asset, active_levels)
                self._store_asset(sense_id, language_id, asset_type, p2_asset,
                                  p2_gen.model, batch_id, is_valid=p2_valid,
                                  validation_errors=p2_errors if not p2_valid else None)
                if not p2_valid:
                    result['errors'].extend(
                        [f'[{variant_key}] {e}' for e in p2_errors])

            # P3 variant
            p3_asset = variant_results.get(('p3', variant_key))
            asset_type = f'prompt3_transforms_{variant_key}'
            if p3_asset is None:
                result['errors'].append(f'Prompt 3 variant {variant_key} generation failed')
            else:
                p3_valid, p3_errors = self.validator.validate_prompt3(p3_asset, active_levels)
                self._store_asset(sense_id, language_id, asset_type, p3_asset,
                                  p3_gen.model, batch_id, is_valid=p3_valid,
                                  validation_errors=p3_errors if not p3_valid else None)
                if not p3_valid:
                    result['errors'].extend(
                        [f'[{variant_key}] {e}' for e in p3_errors])

        # Determine final status
        if not result['errors']:
            result['status'] = 'success'
        else:
            # Partial if P1 succeeded but some variants failed
            result['status'] = 'partial'

        return result

    def generate_batch(
        self,
        sense_ids: list[int],
        language_id: int,
        force: bool = False,
    ) -> dict:
        """Generate assets for multiple word senses.

        Returns:
            {'batch_id': str, 'total': int, 'success': int, 'partial': int,
             'failed': int, 'skipped': int, 'results': [...]}
        """
        batch_id = str(uuid4())
        results = []
        counts = {'success': 0, 'partial': 0, 'failed': 0, 'skipped': 0}

        for sense_id in sense_ids:
            try:
                result = self.generate_for_sense(
                    sense_id, language_id, force=force, batch_id=batch_id,
                )
                results.append(result)
                counts[result['status']] = counts.get(result['status'], 0) + 1
            except Exception as e:
                logger.error("Pipeline failed for sense %s: %s", sense_id, e)
                results.append({
                    'sense_id': sense_id, 'status': 'failed',
                    'errors': [str(e)],
                })
                counts['failed'] += 1

        logger.info(
            "Batch %s complete: %d total, %d success, %d partial, %d failed, %d skipped",
            batch_id, len(sense_ids), counts['success'], counts['partial'],
            counts['failed'], counts['skipped'],
        )

        return {
            'batch_id': batch_id,
            'total': len(sense_ids),
            **counts,
            'results': results,
        }

    # ------------------------------------------------------------------
    # Corpus sentence sourcing
    # ------------------------------------------------------------------

    def _fetch_corpus_sentences(
        self, sense_id: int, language_id: int
    ) -> list[dict]:
        """Pull existing sentences from tests/conversations that contain this word.

        Returns list of dicts with: text, target_substring, source, complexity_tier.
        """
        # Get the lemma for this sense
        try:
            resp = (
                self.db.table('dim_word_senses')
                .select('dim_vocabulary(lemma)')
                .eq('id', sense_id)
                .single()
                .execute()
            )
            vocab = (resp.data or {}).get('dim_vocabulary') or {}
            lemma = vocab.get('lemma', '')
        except Exception:
            return []

        if not lemma or len(lemma) < 2:
            return []

        sentences = []

        # Search test transcripts
        try:
            test_resp = (
                self.db.table('tests')
                .select('transcript, complexity_tier')
                .eq('language_id', language_id)
                .not_.is_('transcript', 'null')
                .limit(50)
                .execute()
            )
            for test in (test_resp.data or []):
                transcript = test.get('transcript', '')
                if not transcript:
                    continue
                tier = test.get('complexity_tier', 'T3')
                found = self._extract_sentences_with_word(
                    transcript, lemma, 'corpus', tier
                )
                sentences.extend(found)
                if len(sentences) >= Config.VOCAB_SENTENCES_PER_WORD:
                    break
        except Exception as e:
            logger.debug("Corpus sentence search in tests failed: %s", e)

        # Search conversation transcripts if needed
        if len(sentences) < Config.VOCAB_SENTENCES_PER_WORD:
            try:
                conv_resp = (
                    self.db.table('conversations')
                    .select('content, complexity_tier')
                    .eq('language_id', language_id)
                    .not_.is_('content', 'null')
                    .limit(30)
                    .execute()
                )
                for conv in (conv_resp.data or []):
                    content = conv.get('content', '')
                    if not content:
                        continue
                    tier = conv.get('complexity_tier', 'T3')
                    # Content may be JSON (dialogue turns) or plain text
                    if isinstance(content, list):
                        text = ' '.join(
                            turn.get('text', '') for turn in content
                            if isinstance(turn, dict)
                        )
                    elif isinstance(content, str):
                        text = content
                    else:
                        continue
                    found = self._extract_sentences_with_word(
                        text, lemma, 'corpus', tier
                    )
                    sentences.extend(found)
                    if len(sentences) >= Config.VOCAB_SENTENCES_PER_WORD:
                        break
            except Exception as e:
                logger.debug("Corpus sentence search in conversations failed: %s", e)

        # Deduplicate and limit
        seen = set()
        unique = []
        for s in sentences:
            key = s['text'].strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique[:Config.VOCAB_SENTENCES_PER_WORD]

    def _extract_sentences_with_word(
        self, text: str, lemma: str, source: str, tier: str
    ) -> list[dict]:
        """Split text into sentences and return those containing the lemma."""
        from services.exercise_generation.language_processor import LanguageProcessor
        processor = LanguageProcessor.for_language(self.db_language_id if hasattr(self, 'db_language_id') else 2)

        results = []
        try:
            sents = processor.split_sentences(text)
        except Exception:
            # Fallback: simple period splitting
            sents = [s.strip() for s in text.split('.') if s.strip()]

        lemma_lower = lemma.lower()
        for sent in sents:
            sent = sent.strip()
            if len(sent) < 10 or lemma_lower not in sent.lower():
                continue

            # Find the exact substring match (case-preserving)
            idx = sent.lower().index(lemma_lower)
            target_substring = sent[idx:idx + len(lemma)]

            results.append({
                'text': sent,
                'target_substring': target_substring,
                'source': source,
                'complexity_tier': tier,
            })

        return results

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def _assets_exist(self, sense_id: int) -> bool:
        """Check if all asset types exist and are valid for this sense.

        Accepts both old-format (prompt2_exercises, prompt3_transforms) and
        new variant format (prompt2_exercises_A/B, prompt3_transforms_A/B).
        """
        try:
            resp = (
                self.db.table('word_assets')
                .select('asset_type')
                .eq('sense_id', sense_id)
                .eq('is_valid', True)
                .execute()
            )
            types = {row['asset_type'] for row in (resp.data or [])}
            has_p1 = 'prompt1_core' in types
            has_p2 = (
                types >= {'prompt2_exercises_A', 'prompt2_exercises_B'}
                or 'prompt2_exercises' in types
            )
            has_p3 = (
                types >= {'prompt3_transforms_A', 'prompt3_transforms_B'}
                or 'prompt3_transforms' in types
            )
            return has_p1 and has_p2 and has_p3
        except Exception:
            return False

    def _store_asset(
        self,
        sense_id: int,
        language_id: int,
        asset_type: str,
        content: dict,
        model_used: str,
        batch_id: str,
        is_valid: bool = True,
        validation_errors: list[str] | None = None,
    ):
        """Upsert a word asset row."""
        try:
            row = {
                'sense_id': sense_id,
                'language_id': language_id,
                'asset_type': asset_type,
                'content': content,
                'model_used': model_used,
                'prompt_version': 'v1',
                'is_valid': is_valid,
                'validation_errors': validation_errors,
                'generation_batch_id': batch_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            self.db.table('word_assets').upsert(
                row, on_conflict='sense_id,asset_type'
            ).execute()

            logger.info(
                "Stored %s asset for sense %s (valid=%s)",
                asset_type, sense_id, is_valid,
            )
        except Exception as e:
            logger.error("Failed to store %s asset for sense %s: %s",
                         asset_type, sense_id, e)

    def _update_vocabulary_metadata(self, sense_id: int, core_asset: dict):
        """Update dim_vocabulary.semantic_class and dim_word_senses phonetics."""
        try:
            # Get vocab_id from sense
            resp = (
                self.db.table('dim_word_senses')
                .select('vocab_id')
                .eq('id', sense_id)
                .single()
                .execute()
            )
            vocab_id = resp.data.get('vocab_id') if resp.data else None

            if vocab_id:
                self.db.table('dim_vocabulary').update({
                    'semantic_class': core_asset.get('semantic_class'),
                    'part_of_speech': core_asset.get('pos'),
                }).eq('id', vocab_id).execute()

            # Update dim_word_senses with phonetic data
            updates = {}
            if core_asset.get('ipa'):
                updates['ipa_pronunciation'] = core_asset['ipa']
            if core_asset.get('morphological_forms'):
                updates['morphological_forms'] = core_asset['morphological_forms']
            if core_asset.get('pronunciation'):
                updates['pronunciation'] = core_asset['pronunciation']

            if updates:
                self.db.table('dim_word_senses').update(updates).eq('id', sense_id).execute()

        except Exception as e:
            logger.error("Failed to update vocabulary metadata for sense %s: %s",
                         sense_id, e)


# Import Config at module level for VOCAB_SENTENCES_PER_WORD
from config import Config
