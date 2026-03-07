#!/usr/bin/env python3
"""
Backfill vocab_token_map for existing tests.

Builds the per-token sense mapping for tests that already have vocabulary
in dim_vocabulary/dim_word_senses.

Two-strategy matching:
1. Reverse-lookup from test's vocab_sense_ids (sense_id → vocab_id → lemma)
2. Global vocab/sense cache (lemma → vocab_id → best sense_id)

Optional --create-missing flag to create new dim_vocabulary + dim_word_senses
entries for content tokens that don't match either strategy (requires LLM).

Usage:
    python scripts/backfill_token_maps.py --language cn [--limit 10] [--force] [--create-missing]

Options:
    --language CODE      Required. Language code: cn, en, jp
    --limit N            Process at most N tests (default: all)
    --force              Rebuild token maps even for tests that already have one
    --create-missing     Create new vocab+sense entries for unmatched words (LLM)
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.pipeline import VocabularyExtractionPipeline
from services.vocabulary.frequency_service import compute_zipf_for_vocab_item

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TokenMapBackfillRunner:
    def __init__(self, language_code: str, limit: int = 0, force: bool = False,
                 create_missing: bool = False):
        self.language_code = language_code
        self.limit = limit
        self.force = force
        self.create_missing = create_missing

        self.db = get_supabase_admin()
        self.language_id = Config.LANGUAGE_CODE_TO_ID.get(language_code)
        if not self.language_id:
            raise ValueError(f"Unknown language code: {language_code}")

        # Initialize pipeline and optionally sense generator
        self.pipeline, self.sense_generator = self._init_pipeline()

        # Caches
        self._vocab_cache: dict[tuple[str, int], int] = {}  # (lemma, lang_id) → vocab_id
        self._sense_cache: dict[int, int] = {}  # vocab_id → best sense_id

        self.stats = {
            'processed': 0, 'skipped': 0, 'failed': 0,
            'matched_reverse': 0, 'matched_cache': 0,
            'unmatched': 0, 'created': 0,
        }

    def _init_pipeline(self):
        """Initialize the vocabulary pipeline and optionally sense generator."""
        from openai import OpenAI
        from services.test_generation.database_client import TestDatabaseClient

        db_client = TestDatabaseClient()

        if self.create_missing:
            # Need real OpenAI client for LLM calls
            if Config.USE_OPENROUTER and Config.OPENROUTER_API_KEY:
                openai_client = OpenAI(
                    api_key=Config.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
            elif Config.OPENAI_API_KEY:
                openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
            else:
                raise RuntimeError("--create-missing requires OpenAI or OpenRouter API key")

            from services.vocabulary.sense_generator import SenseGenerator
            lang_config = db_client.get_language_config_by_code(self.language_code)
            if not lang_config:
                raise ValueError(f"Language '{self.language_code}' not found in database")

            sense_gen = SenseGenerator(
                openai_client=openai_client,
                db=self.db,
                db_client=db_client,
                language_code=self.language_code,
                language_id=self.language_id,
                model=lang_config.prose_model,
            )
        else:
            openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', 'dummy'))
            sense_gen = None

        pipeline = VocabularyExtractionPipeline(
            openai_client=openai_client,
            db_client=db_client,
        )

        return pipeline, sense_gen

    def _preload_caches(self):
        """Load all vocab and sense data for this language into memory."""
        # Load vocab: (lemma, language_id) → vocab_id
        response = self.db.table('dim_vocabulary') \
            .select('id, lemma') \
            .eq('language_id', self.language_id) \
            .execute()

        for row in (response.data or []):
            self._vocab_cache[(row['lemma'], self.language_id)] = row['id']

        logger.info(f"Loaded {len(self._vocab_cache)} vocab entries")

        # Load best sense per vocab_id
        vocab_ids = list(self._vocab_cache.values())
        if vocab_ids:
            for i in range(0, len(vocab_ids), 500):
                chunk = vocab_ids[i:i + 500]
                result = self.db.table('dim_word_senses') \
                    .select('id, vocab_id, sense_rank') \
                    .in_('vocab_id', chunk) \
                    .order('sense_rank') \
                    .execute()
                for row in (result.data or []):
                    vid = row['vocab_id']
                    if vid not in self._sense_cache:
                        self._sense_cache[vid] = row['id']

        logger.info(f"Loaded {len(self._sense_cache)} sense mappings")

    def _get_tests(self) -> list[dict]:
        """Fetch tests needing token map backfill."""
        query = self.db.table('tests') \
            .select('id, slug, transcript, vocab_sense_ids') \
            .eq('language_id', self.language_id) \
            .eq('is_active', True) \
            .order('created_at')

        if not self.force:
            query = query.is_('vocab_token_map', 'null')

        if self.limit:
            query = query.limit(self.limit)

        response = query.execute()
        return response.data or []

    def _build_sense_lookup(self, sense_ids: list[int]) -> dict[str, int]:
        """
        Reverse-lookup: sense_ids → vocab_id → lemma → {lemma: sense_id}.

        Uses the test's known vocab_sense_ids to build a lemma → sense_id map.
        """
        if not sense_ids:
            return {}

        # Batch in chunks of 500
        sense_to_vocab: dict[int, int] = {}
        for i in range(0, len(sense_ids), 500):
            chunk = sense_ids[i:i + 500]
            result = self.db.table('dim_word_senses') \
                .select('id, vocab_id') \
                .in_('id', chunk) \
                .execute()
            for row in (result.data or []):
                sense_to_vocab[row['id']] = row['vocab_id']

        vocab_ids = list(set(sense_to_vocab.values()))

        # Fetch vocab_id → lemma
        vocab_to_lemma: dict[int, str] = {}
        for i in range(0, len(vocab_ids), 500):
            chunk = vocab_ids[i:i + 500]
            result = self.db.table('dim_vocabulary') \
                .select('id, lemma') \
                .in_('id', chunk) \
                .execute()
            for row in (result.data or []):
                vocab_to_lemma[row['id']] = row['lemma']

        # Build lemma → sense_id (first sense wins)
        lemma_to_sense: dict[str, int] = {}
        for sense_id, vocab_id in sense_to_vocab.items():
            lemma = vocab_to_lemma.get(vocab_id)
            if lemma and lemma not in lemma_to_sense:
                lemma_to_sense[lemma] = sense_id

        return lemma_to_sense

    def _create_vocab_and_sense(self, lemma: str, transcript: str) -> int | None:
        """Create dim_vocabulary entry + dim_word_senses definition for a word."""
        if not self.sense_generator:
            return None

        from services.vocabulary.sense_generator import find_sentence

        # Check if vocab already exists (might have been created by another test)
        cache_key = (lemma, self.language_id)
        vid = self._vocab_cache.get(cache_key)

        if not vid:
            # Create dim_vocabulary entry
            row = {
                'lemma': lemma,
                'language_id': self.language_id,
            }

            try:
                response = self.db.table('dim_vocabulary') \
                    .insert(row) \
                    .execute()
                if response.data and len(response.data) > 0:
                    vid = response.data[0]['id']
                else:
                    # Race condition — look it up
                    lookup = self.db.table('dim_vocabulary') \
                        .select('id') \
                        .eq('lemma', lemma) \
                        .eq('language_id', self.language_id) \
                        .single() \
                        .execute()
                    vid = lookup.data['id']
            except Exception as e:
                logger.error(f"Failed to create vocab for '{lemma}': {e}")
                return None

            self._vocab_cache[cache_key] = vid

        # Check if sense already exists
        existing_sense = self._sense_cache.get(vid)
        if existing_sense:
            return existing_sense

        # Generate sense via LLM
        sentence = find_sentence(transcript, lemma)
        try:
            sense_id = self.sense_generator.generate_sense(
                vocab_id=vid,
                lemma=lemma,
                phrase_type=None,
                sentence=sentence,
                transcript=transcript,
            )
            if sense_id:
                self._sense_cache[vid] = sense_id
                self.stats['created'] += 1
            return sense_id
        except Exception as e:
            logger.error(f"Failed to generate sense for '{lemma}': {e}")
            return None

    def _build_token_map(self, transcript: str, vocab_sense_ids: list[int] | None) -> tuple[list, list]:
        """Build token map using two-strategy matching."""
        tokens = self.pipeline.tokenize_full(transcript, self.language_code)

        # Strategy 1: Reverse-lookup from test's existing vocab_sense_ids
        sense_lookup = self._build_sense_lookup(vocab_sense_ids or [])

        token_map = []
        unmatched = []

        for i, (display_text, lemma, is_content) in enumerate(tokens):
            sense_id = 0
            if is_content and lemma:
                # Strategy 1: reverse lookup from test's vocab_sense_ids
                sense_id = sense_lookup.get(lemma, 0)
                if sense_id:
                    self.stats['matched_reverse'] += 1
                else:
                    # Strategy 2: global vocab + sense cache
                    vid = self._vocab_cache.get((lemma, self.language_id))
                    if vid:
                        sense_id = self._sense_cache.get(vid, 0)
                    if sense_id:
                        self.stats['matched_cache'] += 1
                    else:
                        self.stats['unmatched'] += 1
                        unmatched.append((i, lemma))

            token_map.append([display_text, sense_id])

        return token_map, unmatched

    def run(self):
        logger.info("=" * 60)
        logger.info(f"Token Map Backfill: language={self.language_code} (id={self.language_id})")
        logger.info(f"  limit={self.limit or 'all'}, force={self.force}, create_missing={self.create_missing}")
        logger.info("=" * 60)

        self._preload_caches()

        tests = self._get_tests()
        logger.info(f"Found {len(tests)} tests to process")

        if not tests:
            logger.info("Nothing to backfill!")
            return True

        for i, test in enumerate(tests):
            slug = test['slug']
            transcript = test.get('transcript', '')
            vocab_sense_ids = test.get('vocab_sense_ids') or []

            if not transcript or not transcript.strip():
                logger.warning(f"Skipping {slug}: empty transcript")
                self.stats['skipped'] += 1
                continue

            try:
                token_map, unmatched = self._build_token_map(transcript, vocab_sense_ids)

                # Strategy 3: Create missing entries if requested
                if self.create_missing and unmatched:
                    for idx, lemma in unmatched:
                        sense_id = self._create_vocab_and_sense(lemma, transcript)
                        if sense_id:
                            token_map[idx][1] = sense_id

                self.db.table('tests') \
                    .update({'vocab_token_map': token_map}) \
                    .eq('id', test['id']) \
                    .execute()

                defined = sum(1 for _, s in token_map if s)
                total = len(token_map)
                logger.info(
                    f"[{i+1}/{len(tests)}] {slug}: "
                    f"{total} tokens, {defined} with definitions, "
                    f"{len(unmatched)} unmatched"
                )
                self.stats['processed'] += 1

            except Exception as e:
                logger.error(f"Failed {slug}: {e}")
                self.stats['failed'] += 1

        logger.info("=" * 60)
        logger.info("Backfill Complete")
        logger.info(f"  Processed:         {self.stats['processed']}")
        logger.info(f"  Skipped:           {self.stats['skipped']}")
        logger.info(f"  Failed:            {self.stats['failed']}")
        logger.info(f"  Matched (reverse): {self.stats['matched_reverse']}")
        logger.info(f"  Matched (cache):   {self.stats['matched_cache']}")
        logger.info(f"  Unmatched:         {self.stats['unmatched']}")
        if self.create_missing:
            logger.info(f"  Created:           {self.stats['created']}")
            if self.sense_generator:
                logger.info(f"  Senses created:    {self.sense_generator.stats['senses_created']}")
                logger.info(f"  Senses reused:     {self.sense_generator.stats['senses_reused']}")
                logger.info(f"  Senses skipped:    {self.sense_generator.stats['senses_skipped']}")
                logger.info(f"  Senses failed:     {self.sense_generator.stats['senses_failed']}")
        logger.info("=" * 60)

        return self.stats['failed'] == 0


def main():
    parser = argparse.ArgumentParser(description='Backfill vocab_token_map for existing tests')
    parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],
                        help='Language code to process')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max number of tests to process (0=all)')
    parser.add_argument('--force', action='store_true',
                        help='Rebuild token maps even if they already exist')
    parser.add_argument('--create-missing', action='store_true',
                        help='Create new vocab+sense entries for unmatched words (requires LLM)')

    args = parser.parse_args()

    SupabaseFactory.initialize()

    runner = TokenMapBackfillRunner(
        language_code=args.language,
        limit=args.limit,
        force=args.force,
        create_missing=args.create_missing,
    )

    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
