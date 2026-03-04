#!/usr/bin/env python3
"""
Topic Generation Cron Job Entry Point

Run with: python -m scripts.run_topic_generation

Environment variables:
    TOPIC_DAILY_QUOTA: Number of topics to generate per run (default: 5)
    TOPIC_SIMILARITY_THRESHOLD: Cosine similarity threshold (default: 0.85)
    TOPIC_DRY_RUN: Set to 'true' to test without saving (default: false)
    TOPIC_LOG_LEVEL: Logging level (default: INFO)

Exit codes:
    0: Success - all topics generated
    1: Partial success - some topics generated but below quota
    2: Failure - error during execution
"""

import sys
import os
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_logging():
    """Configure logging for the script."""
    log_level = os.getenv('TOPIC_LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific loggers
    logging.getLogger('services.topic_generation').setLevel(
        getattr(logging, log_level, logging.INFO)
    )

    # Reduce noise from HTTP libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)


def main():
    """Run daily topic generation."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("  LinguaDojo Topic Generation")
    logger.info(f"  Started: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    # Import after path setup (before try block for exception handling)
    from services.supabase_factory import SupabaseFactory
    from services.topic_generation.orchestrator import (
        TopicGenerationOrchestrator,
        NoEligibleCategoryError
    )
    from services.topic_generation.config import topic_gen_config

    try:
        # Initialize Supabase
        logger.info("Initializing Supabase connection...")
        SupabaseFactory.initialize()

        # Log configuration
        logger.info(f"Configuration:")
        logger.info(f"  Daily Quota: {topic_gen_config.daily_topic_quota}")
        logger.info(f"  Similarity Threshold: {topic_gen_config.similarity_threshold}")
        logger.info(f"  LLM Model: {topic_gen_config.llm_model}")
        logger.info(f"  Embedding Model: {topic_gen_config.embedding_model}")
        logger.info(f"  Dry Run: {topic_gen_config.dry_run}")

        # Run orchestrator
        orchestrator = TopicGenerationOrchestrator()
        metrics = orchestrator.run()

        # Determine exit code
        if metrics.error_message:
            logger.error(f"Run completed with error: {metrics.error_message}")
            sys.exit(2)

        if metrics.topics_generated < topic_gen_config.daily_topic_quota:
            logger.warning(
                f"Quota not met: generated {metrics.topics_generated} "
                f"of {topic_gen_config.daily_topic_quota} topics"
            )
            sys.exit(1)

        logger.info(f"Success: generated {metrics.topics_generated} topics")
        sys.exit(0)

    except NoEligibleCategoryError as e:
        logger.warning(f"No categories available: {e}")
        # This is not a failure - just nothing to do
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(2)


if __name__ == '__main__':
    main()
