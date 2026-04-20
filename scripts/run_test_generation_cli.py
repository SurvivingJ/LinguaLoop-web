#!/usr/bin/env python3
"""
Batch Test Generation CLI

Generates comprehension tests with balanced difficulty distribution.
Produces prose, questions, audio, and saves to database.

Usage:
    # Default: 20 tests, balanced across difficulties [1,3,6,9]
    python -m scripts.run_test_generation_cli --language cn

    # All 10 at difficulty 5
    python -m scripts.run_test_generation_cli --language en --count 10 --difficulty 5

    # Reading-only (no audio), dry run
    python -m scripts.run_test_generation_cli --language jp --type reading --dry-run

    # Resume from index 12 after a failure
    python -m scripts.run_test_generation_cli --language cn --count 50 --start-index 12
"""

import sys
import os
import argparse
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def setup_logging():
    """Configure logging for the script."""
    log_level = os.getenv('TEST_GEN_LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def main():
    """Run batch test generation."""
    parser = argparse.ArgumentParser(
        description='Batch test generation with balanced difficulty distribution',
    )
    parser.add_argument(
        '--language', required=True, choices=['cn', 'en', 'jp'],
        help='Language code: cn=Chinese, en=English, jp=Japanese',
    )
    parser.add_argument(
        '--count', type=int, default=20,
        help='Tests to generate (default: 20, evenly spread across difficulties)',
    )
    parser.add_argument(
        '--type', default='listening', choices=['listening', 'reading'],
        help='Test type (default: listening)',
    )
    parser.add_argument(
        '--difficulty', type=int, choices=range(1, 10), default=None,
        metavar='1-9',
        help='Fix ALL tests at this difficulty. Default: balanced across [1,3,6,9]',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Log what would be generated without DB writes or audio generation',
    )
    parser.add_argument(
        '--start-index', type=int, default=0,
        help='Resume from this index (default: 0)',
    )
    parser.add_argument(
        '--delay', type=int, default=0,
        help='Delay in milliseconds between tests (default: 0)',
    )
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    language_names = {'cn': 'Chinese', 'en': 'English', 'jp': 'Japanese'}

    logger.info('=' * 60)
    logger.info('Batch Test Generation')
    logger.info('Started at: %s', datetime.now().isoformat())
    logger.info('=' * 60)
    logger.info('Configuration:')
    logger.info('  Language: %s (%s)', language_names[args.language], args.language)
    logger.info('  Count: %d', args.count)
    logger.info('  Type: %s', args.type)
    logger.info('  Difficulty: %s', args.difficulty or 'balanced [1,3,6,9]')
    logger.info('  Dry Run: %s', args.dry_run)
    if args.start_index > 0:
        logger.info('  Start Index: %d', args.start_index)
    if args.delay > 0:
        logger.info('  Delay: %dms', args.delay)
    logger.info('')

    # Initialize Supabase
    from services.supabase_factory import SupabaseFactory
    SupabaseFactory.initialize()

    from services.test_generation.orchestrator import (
        TestGenerationOrchestrator,
        BatchConfig,
    )

    try:
        orchestrator = TestGenerationOrchestrator()

        config = BatchConfig(
            language_code=args.language,
            count=args.count,
            test_type=args.type,
            difficulty=args.difficulty,
            dry_run=args.dry_run,
            start_index=args.start_index,
            delay_ms=args.delay,
        )

        metrics = orchestrator.run_batch(config)

        logger.info('')
        logger.info('=' * 60)
        logger.info('Run Complete')
        logger.info('  Tests Generated: %d', metrics.tests_generated)
        logger.info('  Tests Failed: %d', metrics.tests_failed)
        logger.info('  Execution Time: %ds', metrics.execution_time_seconds or 0)
        if metrics.error_message:
            logger.error('  Error: %s', metrics.error_message)
        logger.info('=' * 60)

        if metrics.tests_failed > 0:
            sys.exit(1)

    except Exception as exc:
        logger.error('Batch generation failed: %s', exc, exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
