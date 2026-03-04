#!/usr/bin/env python3
"""
Topic Import CLI Entry Point

Import topics from a JSON file into the topic generation system.

Run with: python -m scripts.run_topic_import --file <path.json>

Arguments:
    --file, -f        Path to JSON file containing topics (required)
    --category, -t    Category name (default: "Import: {filename}")
    --lens, -e        Default lens code if not in JSON (default: "cultural")
    --dry-run, -d     Validate without database changes
    --skip-gatekeeper Skip cultural validation for faster imports
    --skip-novelty    Skip duplicate checking
    --validate-only   Only validate JSON format, don't import

Exit codes:
    0: Success
    1: Validation errors
    2: Import errors
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_logging(verbose: bool = False):
    """Configure logging for the script."""
    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific loggers
    logging.getLogger('services.topic_generation').setLevel(log_level)

    # Reduce noise from HTTP libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Import topics from JSON file into the topic generation system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import topics
  python -m scripts.run_topic_import --file data/topics.json

  # Import with custom category
  python -m scripts.run_topic_import --file slang.json --category "Gen-Z Slang 2024"

  # Validate JSON format only
  python -m scripts.run_topic_import --file topics.json --validate-only

  # Fast import (skip checks)
  python -m scripts.run_topic_import --file verified.json --skip-novelty --skip-gatekeeper

JSON Format:
  {
    "topics": [
      {
        "topic": "Topic concept in English",
        "languages": ["zh", "ja", "en"],
        "keywords": ["optional", "tags"],
        "lens_code": "cultural"
      }
    ]
  }
        """
    )

    parser.add_argument(
        '--file', '-f',
        required=True,
        help='Path to JSON file containing topics'
    )
    parser.add_argument(
        '--category', '-t',
        help='Category name (default: "Import: {filename}")'
    )
    parser.add_argument(
        '--lens', '-e',
        default='cultural',
        help='Default lens code if not in JSON (default: cultural)'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Validate and log without database changes'
    )
    parser.add_argument(
        '--skip-gatekeeper',
        action='store_true',
        help='Skip cultural validation for faster imports'
    )
    parser.add_argument(
        '--skip-novelty',
        action='store_true',
        help='Skip duplicate checking (for known-unique lists)'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate JSON format, do not import'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def validate_only(file_path: str) -> int:
    """Validate JSON file without importing."""
    from services.topic_generation.json_importer import JSONTopicImporter

    logger = logging.getLogger(__name__)
    importer = JSONTopicImporter()

    logger.info(f"Validating: {file_path}")
    errors = importer.validate_json(file_path)

    if errors:
        logger.error("Validation FAILED:")
        for error in errors:
            logger.error(f"  - {error}")
        return 1
    else:
        logger.info("Validation PASSED")
        # Also report stats
        entries = importer.parse_json(file_path)
        all_languages = set()
        for entry in entries:
            all_languages.update(entry.languages)

        logger.info(f"  Topics: {len(entries)}")
        logger.info(f"  Languages referenced: {sorted(all_languages)}")
        return 0


def main():
    """Run topic import."""
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("  LinguaDojo Topic Import")
    logger.info(f"  Started: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    # Check file exists
    if not os.path.exists(args.file):
        logger.error(f"File not found: {args.file}")
        sys.exit(1)

    # Validate-only mode
    if args.validate_only:
        exit_code = validate_only(args.file)
        sys.exit(exit_code)

    # Full import mode - need Supabase
    from services.supabase_factory import SupabaseFactory
    from services.topic_generation.import_orchestrator import TopicImportOrchestrator

    try:
        # Initialize Supabase
        logger.info("Initializing Supabase connection...")
        SupabaseFactory.initialize()

        # Log configuration
        logger.info(f"Configuration:")
        logger.info(f"  File: {args.file}")
        logger.info(f"  Category: {args.category or '(auto)'}")
        logger.info(f"  Default Lens: {args.lens}")
        logger.info(f"  Dry Run: {args.dry_run}")
        logger.info(f"  Skip Novelty: {args.skip_novelty}")
        logger.info(f"  Skip Gatekeeper: {args.skip_gatekeeper}")

        # Run orchestrator
        orchestrator = TopicImportOrchestrator(
            json_file_path=args.file,
            category_name=args.category,
            default_lens_code=args.lens,
            skip_gatekeeper=args.skip_gatekeeper,
            skip_novelty=args.skip_novelty,
            dry_run=args.dry_run
        )

        metrics = orchestrator.run()

        # Determine exit code
        if metrics.error_message:
            logger.error(f"Import failed: {metrics.error_message}")
            sys.exit(2)

        if metrics.topics_imported == 0 and metrics.total_entries > 0:
            logger.warning("No topics imported (all rejected or invalid)")
            sys.exit(1)

        logger.info(f"Success: imported {metrics.topics_imported} topics, "
                    f"queued {metrics.queue_entries_created} entries")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(2)


if __name__ == '__main__':
    main()
