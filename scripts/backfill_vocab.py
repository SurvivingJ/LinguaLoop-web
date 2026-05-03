#!/usr/bin/env python3
"""
Backfill vocabulary for existing tests.

For each test in a given language:
1. Extract vocabulary (lemmas + phrases) using the NLP + LLM pipeline
2. Upsert extracted items into dim_vocabulary
3. Generate word sense definitions via LLM (select, generate, validate)
4. Write the integer ID array to tests.vocab_sense_ids
5. Write stats to tests.vocab_sense_stats

Usage:
    python scripts/backfill_vocab.py --language cn [--dry-run] [--limit 10] [--delay 0.5]

Options:
    --language CODE   Required. Language code: cn, en, jp
    --dry-run         Preview changes without writing to DB
    --limit N         Process at most N tests (default: all)
    --delay SECS      Delay between tests for LLM rate limiting (default: 0.5)
"""

import sys
import os
import time
import argparse
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import Config
from services.supabase_factory import SupabaseFactory, get_supabase_admin
from services.vocabulary.sense_generator import SenseGenerator, find_sentence
from services.vocabulary.frequency_service import compute_zipf_for_vocab_item

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VocabBackfillRunner:
    def __init__(self, language_code: str, dry_run: bool = False,
                 limit: int = 0, delay: float = 0.5):
        self.language_code = language_code
        self.dry_run = dry_run
        self.limit = limit
        self.delay = delay

        self.db = get_supabase_admin()
        self.language_id = Config.LANGUAGE_CODE_TO_ID.get(language_code)
        if not self.language_id:
            raise ValueError(f"Unknown language code: {language_code}")

        # Initialize vocabulary pipeline and sense generator
        self.pipeline, self.sense_generator = self._init_pipeline()

        # Local cache: (lemma, language_id) → vocab_id
        self._vocab_cache: dict[tuple[str, int], int] = {}

        # Stats
        self.stats = {
            'tests_processed': 0,
            'tests_skipped': 0,
            'tests_failed': 0,
            'vocab_created': 0,
            'vocab_reused': 0,
        }

    def _init_pipeline(self):
        """Initialize the vocabulary extraction pipeline and sense generator."""
        from openai import OpenAI
        from services.test_generation.database_client import TestDatabaseClient
        from services.vocabulary.pipeline import VocabularyExtractionPipeline

        # Create OpenAI client (same pattern as ServiceFactory)
        if Config.USE_OPENROUTER and Config.OPENROUTER_API_KEY:
            openai_client = OpenAI(
                api_key=Config.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
        elif Config.OPENAI_API_KEY:
            openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        else:
            raise RuntimeError("No OpenAI or OpenRouter API key configured")

        db_client = TestDatabaseClient()

        pipeline = VocabularyExtractionPipeline(
            openai_client=openai_client,
            db_client=db_client,
        )

        # Get language config for LLM model selection
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
            dry_run=self.dry_run,
        )

        return pipeline, sense_gen

    def _preload_vocab_cache(self):
        """Load existing dim_vocabulary rows for this language into local cache."""
        # PostgREST caps a single response at 1000 rows by default, so paginate.
        PAGE_SIZE = 1000
        offset = 0
        while True:
            response = self.db.table('dim_vocabulary') \
                .select('id, lemma') \
                .eq('language_id', self.language_id) \
                .range(offset, offset + PAGE_SIZE - 1) \
                .execute()
            rows = response.data or []
            for row in rows:
                self._vocab_cache[(row['lemma'], self.language_id)] = row['id']
            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        logger.info(f"Pre-loaded {len(self._vocab_cache)} existing vocab entries for {self.language_code}")

    def _get_tests_to_process(self) -> list[dict]:
        """Fetch tests that need vocab backfill."""
        query_with_vocab = self.db.table('tests') \
            .select('id, slug, transcript, difficulty, vocab_sense_ids') \
            .eq('language_id', self.language_id) \
            .eq('is_active', True) \
            .order('created_at')

        if self.limit:
            query_with_vocab = query_with_vocab.limit(self.limit * 2)

        response = query_with_vocab.execute()

        tests = []
        for row in (response.data or []):
            vocab_ids = row.get('vocab_sense_ids')
            if not vocab_ids or len(vocab_ids) == 0:
                tests.append(row)
                if self.limit and len(tests) >= self.limit:
                    break

        return tests

    def _get_or_create_vocab_id(self, item: dict) -> int:
        """
        Get existing vocab ID or create new entry in dim_vocabulary.

        Args:
            item: Dict from extract_detailed() with lemma, pos, is_phrase, etc.

        Returns:
            Integer vocab ID
        """
        lemma = item['lemma']
        cache_key = (lemma, self.language_id)

        if cache_key in self._vocab_cache:
            self.stats['vocab_reused'] += 1
            return self._vocab_cache[cache_key]

        # Insert new vocab entry
        row = {
            'lemma': lemma,
            'language_id': self.language_id,
            'part_of_speech': item.get('pos'),
        }

        # Only include phrase fields when they have values
        if item.get('phrase_type'):
            row['phrase_type'] = item['phrase_type']
        if item.get('components'):
            row['component_lemmas'] = item['components']

        zipf = compute_zipf_for_vocab_item(item, self.language_code)
        if zipf is not None:
            row['frequency_rank'] = zipf

        if self.dry_run:
            # In dry-run mode, use a fake ID
            fake_id = -(len(self._vocab_cache) + 1)
            self._vocab_cache[cache_key] = fake_id
            self.stats['vocab_created'] += 1
            return fake_id

        try:
            response = self.db.table('dim_vocabulary') \
                .insert(row) \
                .execute()
            vocab_id = response.data[0]['id']
        except Exception:
            # Duplicate: look up the existing row
            lookup = self.db.table('dim_vocabulary') \
                .select('id') \
                .eq('lemma', lemma) \
                .eq('language_id', self.language_id) \
                .single() \
                .execute()
            vocab_id = lookup.data['id']
            self.stats['vocab_reused'] += 1
            self._vocab_cache[cache_key] = vocab_id
            return vocab_id

        self._vocab_cache[cache_key] = vocab_id
        self.stats['vocab_created'] += 1
        return vocab_id

    def _build_sense_lookup(self, sense_ids: list[int]) -> dict[str, int]:
        """Reverse-lookup: sense_ids → vocab_id → lemma → {lemma: sense_id}."""
        if not sense_ids:
            return {}

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
        vocab_to_lemma: dict[int, str] = {}
        for i in range(0, len(vocab_ids), 500):
            chunk = vocab_ids[i:i + 500]
            result = self.db.table('dim_vocabulary') \
                .select('id, lemma') \
                .in_('id', chunk) \
                .execute()
            for row in (result.data or []):
                vocab_to_lemma[row['id']] = row['lemma']

        lemma_to_sense: dict[str, int] = {}
        for sense_id, vocab_id in sense_to_vocab.items():
            lemma = vocab_to_lemma.get(vocab_id)
            if lemma and lemma not in lemma_to_sense:
                lemma_to_sense[lemma] = sense_id

        return lemma_to_sense

    def _build_token_map(self, transcript: str, sense_ids: list[int] | None = None) -> list:
        """
        Build vocab token map: [[display_text, sense_id_or_0], ...].

        Uses two strategies:
        1. Reverse-lookup from sense_ids (if provided)
        2. Global vocab cache → DB sense lookup
        """
        tokens = self.pipeline.tokenize_full(transcript, self.language_code)

        # Strategy 1: Reverse-lookup from just-generated sense_ids
        sense_lookup = self._build_sense_lookup(sense_ids or [])

        # Strategy 2: Collect vocab_ids for cache-based lookup
        vocab_ids_needed = set()
        token_vocab_ids = []
        for display_text, lemma, is_content in tokens:
            vid = self._vocab_cache.get((lemma, self.language_id)) if is_content else None
            token_vocab_ids.append(vid)
            if vid:
                vocab_ids_needed.add(vid)

        # Batch-fetch best sense for each vocab_id (lowest sense_rank)
        sense_map = {}
        if vocab_ids_needed:
            result = self.db.table('dim_word_senses') \
                .select('id, vocab_id, sense_rank') \
                .in_('vocab_id', list(vocab_ids_needed)) \
                .order('sense_rank') \
                .execute()
            for row in (result.data or []):
                vid = row['vocab_id']
                if vid not in sense_map:  # First = lowest rank = best
                    sense_map[vid] = row['id']

        # Build the map
        token_map = []
        for i, (display_text, lemma, is_content) in enumerate(tokens):
            sid = 0
            if is_content and lemma:
                # Try reverse lookup first
                sid = sense_lookup.get(lemma, 0)
                if not sid:
                    # Fall back to cache-based lookup
                    vid = token_vocab_ids[i]
                    sid = sense_map.get(vid, 0) if vid else 0
            token_map.append([display_text, sid])

        return token_map

    def _process_test(self, test: dict):
        """Process a single test: extract vocab, upsert, generate senses, update test row."""
        test_id = test['id']
        slug = test['slug']
        transcript = test.get('transcript', '')

        if not transcript or not transcript.strip():
            logger.warning(f"Skipping {slug}: empty transcript")
            self.stats['tests_skipped'] += 1
            return

        try:
            # Extract vocabulary with full metadata
            vocab_items = self.pipeline.extract_detailed(transcript, self.language_code)

            if not vocab_items:
                logger.warning(f"Skipping {slug}: no vocabulary extracted")
                self.stats['tests_skipped'] += 1
                return

            # Get or create vocab IDs and generate word senses
            # vocab_sense_ids stores dim_word_senses.id (NOT dim_vocabulary.id)
            sense_ids = []
            for item in vocab_items:
                vid = self._get_or_create_vocab_id(item)

                # Find the sentence containing this word
                sentence = find_sentence(transcript, item['lemma'])

                # Generate/select word sense definition → returns sense_id
                sense_id = self.sense_generator.generate_sense(
                    vocab_id=vid,
                    lemma=item['lemma'],
                    phrase_type=item.get('phrase_type'),
                    sentence=sentence,
                    transcript=transcript,
                )

                if sense_id is not None:
                    sense_ids.append(sense_id)

            if not sense_ids:
                logger.warning(f"Skipping {slug}: no word senses generated")
                self.stats['tests_skipped'] += 1
                return

            # Build stats
            vocab_stats = {
                'unique_senses': len(sense_ids),
                'unique_vocab': len(set(vid for vid in sense_ids)),
                'phrases': sum(1 for v in vocab_items if v.get('is_phrase')),
                'single_words': sum(1 for v in vocab_items if not v.get('is_phrase')),
            }

            # Build token map (full transcript tokenization with sense IDs)
            token_map = self._build_token_map(transcript, sense_ids)

            if self.dry_run:
                lemma_list = [v['lemma'] for v in vocab_items]
                logger.info(
                    f"[DRY RUN] {slug}: {len(sense_ids)} senses from "
                    f"{len(vocab_items)} vocab items, "
                    f"{len(token_map)} tokens in map — "
                    f"{lemma_list[:10]}{'...' if len(lemma_list) > 10 else ''}"
                )
            else:
                # Update the test row with word sense IDs and token map
                self.db.table('tests') \
                    .update({
                        'vocab_sense_ids': sense_ids,
                        'vocab_sense_stats': vocab_stats,
                        'vocab_token_map': token_map,
                    }) \
                    .eq('id', test_id) \
                    .execute()

                logger.info(f"Updated {slug}: {len(sense_ids)} word senses, {len(token_map)} tokens")

            self.stats['tests_processed'] += 1

        except Exception as e:
            logger.error(f"Failed to process {slug}: {e}")
            self.stats['tests_failed'] += 1

    def run(self):
        """Execute the backfill."""
        logger.info("=" * 60)
        logger.info(f"Vocabulary Backfill: language={self.language_code} (id={self.language_id})")
        logger.info(f"  dry_run={self.dry_run}, limit={self.limit or 'all'}, delay={self.delay}s")
        logger.info("=" * 60)

        # Pre-load existing vocabulary
        self._preload_vocab_cache()

        # Fetch tests to process
        tests = self._get_tests_to_process()
        logger.info(f"Found {len(tests)} tests needing vocab backfill")

        if not tests:
            logger.info("Nothing to backfill!")
            return True

        for i, test in enumerate(tests):
            self._process_test(test)

            # Rate limit between tests (for LLM calls)
            if i < len(tests) - 1 and self.delay > 0:
                time.sleep(self.delay)

        # Summary
        logger.info("=" * 60)
        logger.info("Backfill Complete")
        logger.info("=" * 60)
        logger.info(f"  Tests processed:  {self.stats['tests_processed']}")
        logger.info(f"  Tests skipped:    {self.stats['tests_skipped']}")
        logger.info(f"  Tests failed:     {self.stats['tests_failed']}")
        logger.info(f"  Vocab created:    {self.stats['vocab_created']}")
        logger.info(f"  Vocab reused:     {self.stats['vocab_reused']}")
        logger.info(f"  Senses created:   {self.sense_generator.stats['senses_created']}")
        logger.info(f"  Senses reused:    {self.sense_generator.stats['senses_reused']}")
        logger.info(f"  Senses skipped:   {self.sense_generator.stats['senses_skipped']}")
        logger.info(f"  Senses failed:    {self.sense_generator.stats['senses_failed']}")
        logger.info("=" * 60)

        return self.stats['tests_failed'] == 0


def main():
    parser = argparse.ArgumentParser(description='Backfill vocabulary for existing tests')
    parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],
                        help='Language code to process')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing to DB')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max number of tests to process (0=all)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay in seconds between tests (rate limiting)')

    args = parser.parse_args()

    if args.dry_run:
        logger.info("Running in DRY RUN mode — no changes will be made")

    # Initialize Supabase
    SupabaseFactory.initialize()

    runner = VocabBackfillRunner(
        language_code=args.language,
        dry_run=args.dry_run,
        limit=args.limit,
        delay=args.delay,
    )

    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
