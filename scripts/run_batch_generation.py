#!/usr/bin/env python3
"""
Batch Conversation Generation

Generates conversations for all validated scenarios in specified domains.
Does not require queue items — iterates domains directly.

Usage:
    python -m scripts.run_batch_generation --language 2
    python -m scripts.run_batch_generation --language 2 --domain 5
    python -m scripts.run_batch_generation --language 2 --workers 2
    python -m scripts.run_batch_generation --language 1 --dry-run
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
    log_level = os.getenv('CONV_GEN_LOG_LEVEL', 'INFO').upper()

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
    """Run batch conversation generation."""
    parser = argparse.ArgumentParser(
        description='Batch conversation generation by domain',
    )
    parser.add_argument(
        '--language', required=True, type=int, choices=[1, 2, 3],
        help='Language ID: 1=Chinese, 2=English, 3=Japanese',
    )
    parser.add_argument(
        '--domain', type=int, default=None,
        help='Specific domain ID to process (default: all active domains)',
    )
    parser.add_argument(
        '--max-per-domain', type=int, default=None,
        help='Max conversations per domain (default: from config)',
    )
    parser.add_argument(
        '--workers', type=int, default=None,
        help='Number of parallel workers (default: from config, max 4)',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Log what would be generated without LLM calls',
    )
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    # Apply dry-run override
    if args.dry_run:
        os.environ['CONV_GEN_DRY_RUN'] = 'true'

    logger.info('=' * 60)
    logger.info('Batch Conversation Generation')
    logger.info('Started at: %s', datetime.now().isoformat())
    logger.info('=' * 60)

    # Initialize Supabase
    from services.supabase_factory import SupabaseFactory
    SupabaseFactory.initialize()

    from services.conversation_generation.config import conv_gen_config
    from services.conversation_generation.batch_processor import (
        ConversationBatchProcessor,
    )

    language_names = {1: 'Chinese', 2: 'English', 3: 'Japanese'}

    logger.info('Configuration:')
    logger.info('  Language: %s (ID %d)', language_names[args.language], args.language)
    logger.info('  LLM Provider: %s', conv_gen_config.llm_provider)
    logger.info('  Generation Mode: %s', conv_gen_config.generation_mode)
    logger.info('  Temperature: %.2f', conv_gen_config.temperature)
    logger.info('  Domain: %s', args.domain or 'all active')
    logger.info('  Max per domain: %s', args.max_per_domain or conv_gen_config.max_conversations_per_domain)
    logger.info('  Workers: %s', args.workers or conv_gen_config.max_parallel_workers)
    logger.info('  Dry Run: %s', args.dry_run)
    logger.info('  Skip Existing: %s', conv_gen_config.skip_existing_pairs)
    logger.info('')

    try:
        processor = ConversationBatchProcessor()

        if args.domain:
            metrics = processor.run_domain(
                domain_id=args.domain,
                language_id=args.language,
                max_conversations=args.max_per_domain,
                max_workers=args.workers,
            )
        else:
            metrics = processor.run_all_domains(
                language_id=args.language,
                max_per_domain=args.max_per_domain,
                max_workers=args.workers,
            )

        logger.info('')
        logger.info('=' * 60)
        logger.info('Run Complete')
        logger.info('  Domains processed: %d', metrics.domains_processed)
        logger.info('  Scenarios processed: %d', metrics.scenarios_processed)
        logger.info('  Conversations generated: %d', metrics.conversations_generated)
        logger.info('  Failed QC: %d', metrics.conversations_failed_qc)
        logger.info('  Failed (error): %d', metrics.conversations_failed_error)
        logger.info('  Exercises generated: %d', metrics.exercises_generated)
        logger.info('  Execution time: %ds', metrics.execution_time_seconds)
        logger.info('=' * 60)

    except Exception as exc:
        logger.error('Batch generation failed: %s', exc, exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
