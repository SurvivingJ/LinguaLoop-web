#!/usr/bin/env python3
"""
Backfill exercises for existing vocabulary senses and grammar patterns.

For each word sense (or grammar pattern):
1. Build a sentence pool from test transcripts + LLM fallback
2. Generate exercises via the ExerciseGenerationOrchestrator
3. Insert into the exercises table

Usage:
    python scripts/backfill_exercises.py --language en [options]

Options:
    --language CODE    Required. Language code: cn, en, jp
    --source TYPE      vocabulary, grammar, all (default: all)
    --dry-run          Preview without writing to DB
    --limit N          Max sources to process (default: 0 = all)
    --delay SECS       Delay between sources for rate limiting (default: 1.0)
    --phases A B C D   Restrict to specific exercise phases
    --skip-audio       Skip AudioSynthesizer (no listening_flashcard exercises)
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
from services.exercise_generation.orchestrator import ExerciseGenerationOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExerciseBackfillRunner:
    def __init__(
        self,
        language_code: str,
        source: str = 'all',
        dry_run: bool = False,
        limit: int = 0,
        delay: float = 1.0,
        phases: list[str] | None = None,
        skip_audio: bool = False,
    ):
        self.language_code = language_code
        self.source = source
        self.dry_run = dry_run
        self.limit = limit
        self.delay = delay
        self.phases = phases
        self.skip_audio = skip_audio

        self.db = get_supabase_admin()
        self.language_id = Config.LANGUAGE_CODE_TO_ID.get(language_code)
        if not self.language_id:
            raise ValueError(f"Unknown language code: {language_code}")

        # Initialize audio synthesizer (optional)
        audio_synthesizer = None
        if not skip_audio:
            try:
                from services.test_generation.agents.audio_synthesizer import AudioSynthesizer
                audio_synthesizer = AudioSynthesizer()
                logger.info("AudioSynthesizer initialized — listening_flashcard enabled")
            except Exception as exc:
                logger.warning("AudioSynthesizer unavailable (%s) — skipping listening_flashcard", exc)

        self.orchestrator = ExerciseGenerationOrchestrator(
            self.db, audio_synthesizer=audio_synthesizer,
        )

        # Stats
        self.stats = {
            'senses_processed': 0,
            'senses_skipped': 0,
            'senses_failed': 0,
            'patterns_processed': 0,
            'patterns_skipped': 0,
            'patterns_failed': 0,
            'exercises_created': 0,
        }

    def run(self) -> bool:
        """Execute the backfill."""
        logger.info("=" * 60)
        logger.info("Exercise Backfill: language=%s (id=%s)", self.language_code, self.language_id)
        logger.info("  source=%s, dry_run=%s, limit=%s, delay=%ss",
                     self.source, self.dry_run, self.limit or 'all', self.delay)
        if self.phases:
            logger.info("  phases=%s", self.phases)
        logger.info("=" * 60)

        # Pre-load existing exercise sources for idempotency
        existing_vocab, existing_grammar = self._get_existing_exercise_sources()

        if self.source in ('vocabulary', 'all'):
            self._run_vocabulary(existing_vocab)

        if self.source in ('grammar', 'all'):
            self._run_grammar(existing_grammar)

        self._print_summary()
        return (self.stats['senses_failed'] + self.stats['patterns_failed']) == 0

    def _run_vocabulary(self, existing: set[int]) -> None:
        sense_ids = self._get_senses_for_language()
        logger.info("Found %d total word senses for language=%s", len(sense_ids), self.language_code)

        # Filter out already-processed senses
        to_process = [sid for sid in sense_ids if sid not in existing]
        logger.info("%d senses already have exercises, %d to process",
                     len(sense_ids) - len(to_process), len(to_process))

        if self.limit:
            to_process = to_process[:self.limit]

        if not to_process:
            logger.info("No vocabulary senses to process")
            return

        for i, sid in enumerate(to_process):
            logger.info("[vocab %d/%d] Processing sense_id=%d", i + 1, len(to_process), sid)
            self._process_sense(sid)
            if i < len(to_process) - 1 and self.delay > 0:
                time.sleep(self.delay)

    def _run_grammar(self, existing: set[int]) -> None:
        pattern_ids = self._get_patterns_for_language()
        if not pattern_ids:
            logger.warning("No active grammar patterns found for language=%s. "
                           "Have you run the grammar pattern seed migration?", self.language_code)
            return

        logger.info("Found %d active grammar patterns for language=%s",
                     len(pattern_ids), self.language_code)

        to_process = [pid for pid in pattern_ids if pid not in existing]
        logger.info("%d patterns already have exercises, %d to process",
                     len(pattern_ids) - len(to_process), len(to_process))

        if self.limit:
            to_process = to_process[:self.limit]

        if not to_process:
            logger.info("No grammar patterns to process")
            return

        for i, pid in enumerate(to_process):
            logger.info("[grammar %d/%d] Processing pattern_id=%d", i + 1, len(to_process), pid)
            self._process_pattern(pid)
            if i < len(to_process) - 1 and self.delay > 0:
                time.sleep(self.delay)

    def _get_senses_for_language(self) -> list[int]:
        """
        Fetch all dim_word_senses IDs for this language.
        Two-step query: dim_vocabulary (has language_id) → dim_word_senses (has vocab_id).
        Chunked in batches of 500 to avoid URL length limits.
        """
        vocab_rows = self.db.table('dim_vocabulary') \
            .select('id') \
            .eq('language_id', self.language_id) \
            .execute()
        vocab_ids = [r['id'] for r in (vocab_rows.data or [])]

        all_sense_ids: list[int] = []
        for i in range(0, len(vocab_ids), 500):
            chunk = vocab_ids[i:i + 500]
            sense_rows = self.db.table('dim_word_senses') \
                .select('id') \
                .in_('vocab_id', chunk) \
                .execute()
            all_sense_ids.extend(r['id'] for r in (sense_rows.data or []))

        return all_sense_ids

    def _get_patterns_for_language(self) -> list[int]:
        """Fetch all active grammar pattern IDs for this language."""
        rows = self.db.table('dim_grammar_patterns') \
            .select('id') \
            .eq('language_id', self.language_id) \
            .eq('is_active', True) \
            .execute()
        return [r['id'] for r in (rows.data or [])]

    def _get_existing_exercise_sources(self) -> tuple[set[int], set[int]]:
        """
        Query exercises table to find which sources already have exercises.
        Returns (set of word_sense_ids, set of grammar_pattern_ids).
        """
        existing_vocab: set[int] = set()
        existing_grammar: set[int] = set()

        try:
            vocab_rows = self.db.table('exercises') \
                .select('word_sense_id') \
                .eq('source_type', 'vocabulary') \
                .not_.is_('word_sense_id', 'null') \
                .execute()
            existing_vocab = {r['word_sense_id'] for r in (vocab_rows.data or [])}
        except Exception as exc:
            logger.warning("Could not load existing vocab exercises: %s", exc)

        try:
            grammar_rows = self.db.table('exercises') \
                .select('grammar_pattern_id') \
                .eq('source_type', 'grammar') \
                .not_.is_('grammar_pattern_id', 'null') \
                .execute()
            existing_grammar = {r['grammar_pattern_id'] for r in (grammar_rows.data or [])}
        except Exception as exc:
            logger.warning("Could not load existing grammar exercises: %s", exc)

        logger.info("Existing exercises: %d vocab sources, %d grammar sources",
                     len(existing_vocab), len(existing_grammar))
        return existing_vocab, existing_grammar

    def _process_sense(self, sense_id: int) -> None:
        if self.dry_run:
            logger.info("  [DRY RUN] Would generate exercises for sense_id=%d", sense_id)
            self.stats['senses_skipped'] += 1
            return

        try:
            result = self.orchestrator.run(
                'vocabulary', sense_id, self.language_id, phases=self.phases,
            )
            total = result.get('total', 0)
            self.stats['senses_processed'] += 1
            self.stats['exercises_created'] += total
            logger.info("  sense_id=%d: %d exercises (batch=%s)",
                         sense_id, total, result.get('batch_id', '?'))
        except Exception as exc:
            logger.error("  sense_id=%d FAILED: %s", sense_id, exc)
            self.stats['senses_failed'] += 1

    def _process_pattern(self, pattern_id: int) -> None:
        if self.dry_run:
            logger.info("  [DRY RUN] Would generate exercises for pattern_id=%d", pattern_id)
            self.stats['patterns_skipped'] += 1
            return

        try:
            result = self.orchestrator.run(
                'grammar', pattern_id, self.language_id, phases=self.phases,
            )
            total = result.get('total', 0)
            self.stats['patterns_processed'] += 1
            self.stats['exercises_created'] += total
            logger.info("  pattern_id=%d: %d exercises (batch=%s)",
                         pattern_id, total, result.get('batch_id', '?'))
        except Exception as exc:
            logger.error("  pattern_id=%d FAILED: %s", pattern_id, exc)
            self.stats['patterns_failed'] += 1

    def _print_summary(self) -> None:
        logger.info("=" * 60)
        logger.info("Exercise Backfill Complete")
        logger.info("=" * 60)
        logger.info("  Senses processed:   %d", self.stats['senses_processed'])
        logger.info("  Senses skipped:     %d", self.stats['senses_skipped'])
        logger.info("  Senses failed:      %d", self.stats['senses_failed'])
        logger.info("  Patterns processed: %d", self.stats['patterns_processed'])
        logger.info("  Patterns skipped:   %d", self.stats['patterns_skipped'])
        logger.info("  Patterns failed:    %d", self.stats['patterns_failed'])
        logger.info("  Exercises created:  %d", self.stats['exercises_created'])
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Backfill exercises for existing vocabulary and grammar')
    parser.add_argument('--language', required=True, choices=['cn', 'en', 'jp'],
                        help='Language code to process')
    parser.add_argument('--source', choices=['vocabulary', 'grammar', 'all'], default='all',
                        help='Source type to process (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing to DB')
    parser.add_argument('--limit', type=int, default=0,
                        help='Max number of sources to process (0=all)')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay in seconds between sources (rate limiting)')
    parser.add_argument('--phases', nargs='*', choices=['A', 'B', 'C', 'D'],
                        help='Restrict to specific exercise phases')
    parser.add_argument('--skip-audio', action='store_true',
                        help='Skip AudioSynthesizer (no listening_flashcard)')

    args = parser.parse_args()

    if args.dry_run:
        logger.info("Running in DRY RUN mode — no changes will be made")

    # Initialize Supabase
    SupabaseFactory.initialize()

    runner = ExerciseBackfillRunner(
        language_code=args.language,
        source=args.source,
        dry_run=args.dry_run,
        limit=args.limit,
        delay=args.delay,
        phases=args.phases,
        skip_audio=args.skip_audio,
    )

    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
