#!/usr/bin/env python3
"""
Test Generation Cron Job Entry Point

Processes items from production_queue and generates complete tests
with prose, questions, and audio.

Run with: python -m scripts.run_test_generation

Environment Variables:
    TEST_GEN_BATCH_SIZE: Max queue items per run (default: 50)
    TEST_GEN_TARGET_DIFFICULTIES: JSON array of difficulties (default: [4, 6, 9])
    TEST_GEN_DRY_RUN: Set to 'true' for dry run mode
    TEST_GEN_LOG_LEVEL: Logging level (default: INFO)
"""

import sys
import os
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def setup_logging():
    """Configure logging for the script."""
    log_level = os.getenv('TEST_GEN_LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Reduce noise from third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)


def main():
    """Run test generation workflow."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("  LinguaLoop Test Generation")
    logger.info(f"  Started: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    # Import after path setup (before try block for exception handling)
    from services.supabase_factory import SupabaseFactory
    from services.test_generation.orchestrator import (
        TestGenerationOrchestrator,
        NoQueueItemsError
    )
    from services.test_generation.config import test_gen_config

    try:
        # Initialize Supabase
        logger.info("Initializing Supabase connection...")
        SupabaseFactory.initialize()

        # Log configuration
        logger.info("Configuration:")
        logger.info(f"  Batch Size: {test_gen_config.batch_size}")
        logger.info(f"  Target Difficulties: {test_gen_config.target_difficulties}")
        logger.info(f"  Dry Run: {test_gen_config.dry_run}")
        logger.info(f"  Prose Model: {test_gen_config.default_prose_model}")
        logger.info(f"  Question Model: {test_gen_config.default_question_model}")

        # Create and run orchestrator
        logger.info("Creating orchestrator...")
        orchestrator = TestGenerationOrchestrator()

        logger.info("Starting test generation run...")
        metrics = orchestrator.run()

        # Report results
        logger.info("=" * 70)
        logger.info("  Run Complete")
        logger.info("=" * 70)
        logger.info(f"  Queue Items Processed: {metrics.queue_items_processed}")
        logger.info(f"  Tests Generated: {metrics.tests_generated}")
        logger.info(f"  Tests Failed: {metrics.tests_failed}")
        logger.info(f"  Duration: {metrics.execution_time_seconds}s")

        if metrics.error_message:
            logger.error(f"  Error: {metrics.error_message}")
            sys.exit(1)

        # Exit codes for monitoring
        if metrics.tests_generated == 0 and metrics.queue_items_processed > 0:
            logger.warning("No tests generated despite processing queue items")
            sys.exit(1)

        logger.info("Test generation completed successfully")
        sys.exit(0)

    except NoQueueItemsError:
        logger.info("No pending queue items - nothing to process")
        sys.exit(0)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
