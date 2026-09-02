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
    python scripts/backfill_vocab.py --language zh [--dry-run] [--limit 10] [--delay 0.5]

    # Under a Claude subscription rather than per-token OpenRouter billing:
    python scripts/backfill_vocab.py --language zh --provider claude-cli

Options:
    --language CODE   Required. Language code: zh, en, ja
    --dry-run         Preview changes without writing to DB
    --limit N         Process at most N tests (default: all)
    --delay SECS      Delay between tests for LLM rate limiting (default: 0.5)
    --select-senses   Ask the LLM which existing sense fits each occurrence
                      (default: link the primary sense, no call)
    --provider NAME   openrouter (default, per-token) | claude-cli (subscription)

Note on scope: this script extracts and seeds vocabulary inline, one test at a
time, via a hosted model. To seed the dictionary in bulk with definitions written
in a Claude Code session instead, see
.claude/skills/batch-sense-generation/SKILL.md.
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
from scripts.sense_linking_common import build_token_map_with_fallback, lemma_sense_lookup
from scripts.provider_arg import add_provider_arg, apply_provider

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VocabBackfillRunner:
    def __init__(self, language_code: str, dry_run: bool = False,
                 limit: int = 0, delay: float = 0.5,
                 select_senses: bool = False):
        self.language_code = language_code
        self.dry_run = dry_run
        self.limit = limit
        self.delay = delay
        self.select_senses = select_senses

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
            # None -> SENSE_MODEL_DEFAULT (cheap hosted sense model).
            #
            # prefer_existing=True short-circuits generate_sense() to the word's
            # PRIMARY sense without an LLM call — fast and cheap, but it means no
            # sense is ever chosen for the context it appears in. On a dictionary
            # this well seeded that is the branch nearly every known word takes,
            # so the selection step was effectively off. --select-senses turns it
            # back on at the cost of one call per already-known lemma.
            model=None,
            prefer_existing=not self.select_senses,
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
        """Fetch tests that need vocab backfill, newest-linked-last.

        Pages through the whole language and applies --limit to the *filtered*
        result. The previous version fetched `limit * 2` rows and filtered those,
        so `--limit 1` against a corpus whose two oldest tests were already linked
        reported "Found 0 tests needing vocab backfill" while 27 were waiting —
        a limit that silently means "look at 2N rows and hope".

        PostgREST caps a page at 1000 rows, hence the explicit paging.
        """
        PAGE_SIZE = 1000
        tests: list[dict] = []
        offset = 0

        while True:
            rows = (self.db.table('tests')
                    .select('id, slug, transcript, difficulty, vocab_sense_ids')
                    .eq('language_id', self.language_id)
                    .eq('is_active', True)
                    .order('created_at')
                    .range(offset, offset + PAGE_SIZE - 1)
                    .execute()).data or []

            for row in rows:
                if not (row.get('vocab_sense_ids') or []):
                    tests.append(row)
                    if self.limit and len(tests) >= self.limit:
                        return tests

            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

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

    def _build_token_map(self, transcript: str, sense_ids: list[int] | None = None):
        """
        Build vocab token map: [[display_text, sense_id_or_0], ...].

        Two strategies, both now living in scripts/sense_linking_common.py:
        1. Reverse-lookup from the sense_ids this run just linked
        2. Fall back to each remaining content lemma's best existing sense

        Delegated rather than hand-rolled. The private copy this replaced had
        drifted from backfill_token_maps.py far enough to unpack tokenize_full's
        4-tuple into three names, which raised for every single test — inside
        _process_test's except, so the run reported "Failed to process" after
        the vocab rows and senses had already been created and paid for. It also
        filtered neither definition_level nor definition_language, so its
        fallback could link a `simple` row and render a child-register gloss
        where the standard definition belonged.

        Returns (token_map, unmatched_lemmas).
        """
        return build_token_map_with_fallback(
            self.db, self.language_code, self.language_id, transcript,
            lemma_sense_lookup(self.db, sense_ids or []),
            resolve_vocab_id=lambda lemma: self._vocab_cache.get((lemma, self.language_id)),
        )

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
            linked_vocab_ids = []
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
                    linked_vocab_ids.append(vid)

            if not sense_ids:
                logger.warning(f"Skipping {slug}: no word senses generated")
                self.stats['tests_skipped'] += 1
                return

            # Build stats. unique_vocab counts distinct dim_vocabulary ids — it
            # previously de-duplicated sense_ids and called the result vocab,
            # which made it a copy of unique_senses that could never disagree.
            vocab_stats = {
                'unique_senses': len(set(sense_ids)),
                'unique_vocab': len(set(linked_vocab_ids)),
                'phrases': sum(1 for v in vocab_items if v.get('is_phrase')),
                'single_words': sum(1 for v in vocab_items if not v.get('is_phrase')),
            }

            # Build token map (full transcript tokenization with sense IDs)
            token_map, unmatched = self._build_token_map(transcript, sense_ids)

            if self.dry_run:
                lemma_list = [v['lemma'] for v in vocab_items]
                logger.info(
                    f"[DRY RUN] {slug}: {len(sense_ids)} senses from "
                    f"{len(vocab_items)} vocab items, "
                    f"{len(token_map)} tokens in map, {len(unmatched)} lemmas unmatched — "
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

                linked = sum(1 for t in token_map if t[1])
                logger.info(
                    f"Updated {slug}: {len(sense_ids)} word senses, "
                    f"{linked}/{len(token_map)} tokens linked, "
                    f"{len(unmatched)} lemmas unmatched"
                )

            self.stats['tests_processed'] += 1

        except Exception as e:
            # exception(), not error(): this handler is broad enough to swallow a
            # programming error, and it did — for months it reported a TypeError
            # in the token-map builder as an ordinary per-test failure with no
            # traceback to identify it by.
            logger.exception(f"Failed to process {slug}: {e}")
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
    parser.add_argument('--language', required=True, choices=['zh', 'en', 'ja'],
                        help='Language code to process')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing to DB')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max number of tests to process (0=all)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay in seconds between tests (rate limiting)')
    parser.add_argument('--select-senses', action='store_true',
                        help=(
                            'Run the vocab_sense_selection call for words that '
                            'already have senses, choosing the one that fits the '
                            'sentence. Off by default: it costs one extra LLM '
                            'call per known lemma. Leaving it off links each '
                            "word's primary sense regardless of context."
                        ))
    add_provider_arg(parser)

    args = parser.parse_args()
    apply_provider(args.provider)

    if args.dry_run:
        logger.info("Running in DRY RUN mode — no changes will be made")

    # Initialize Supabase
    SupabaseFactory.initialize()

    runner = VocabBackfillRunner(
        language_code=args.language,
        dry_run=args.dry_run,
        limit=args.limit,
        delay=args.delay,
        select_senses=args.select_senses,
    )

    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
