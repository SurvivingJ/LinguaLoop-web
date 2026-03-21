#!/usr/bin/env python3
"""
Conversation Generation Entry Point

Processes items from conversation_generation_queue and generates
multi-turn conversations with analysis and exercise generation.

Run with: python -m scripts.run_conversation_generation

Environment Variables:
    CONV_GEN_BATCH_SIZE: Max queue items per run (default: 20)
    CONV_GEN_DRY_RUN: Set to 'true' for dry run mode
    CONV_GEN_LOG_LEVEL: Logging level (default: INFO)
    CONV_GEN_LLM_PROVIDER: 'openrouter' (default) or 'ollama'
    CONV_GEN_OLLAMA_URL: Ollama API base URL (default: http://localhost:11434/v1)
    CONV_GEN_OLLAMA_MODEL: Ollama model name (default: qwen2.5:7b-instruct-q4_K_M)
"""

import sys
import os
import logging
from datetime import datetime

# Add parent directory to path for imports
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
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Reduce noise from third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def main():
    """Run the conversation generation pipeline."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Conversation Generation Pipeline")
    logger.info("Started at: %s", datetime.now().isoformat())
    logger.info("=" * 60)

    # Initialize Supabase
    from services.supabase_factory import SupabaseFactory
    SupabaseFactory.initialize()

    # Import after env is loaded
    from services.conversation_generation.config import conv_gen_config
    from services.conversation_generation.orchestrator import (
        ConversationGenerationOrchestrator,
        NoQueueItemsError,
    )

    # Log configuration
    logger.info("Configuration:")
    logger.info("  LLM Provider: %s", conv_gen_config.llm_provider)
    if conv_gen_config.llm_provider == 'ollama':
        logger.info("  Ollama URL: %s", conv_gen_config.ollama_base_url)
        logger.info("  Ollama Model: %s", conv_gen_config.ollama_model)
    else:
        logger.info("  Conversation Model: %s", conv_gen_config.conversation_model)
        logger.info("  Analysis Model: %s", conv_gen_config.analysis_model)
    logger.info("  Batch Size: %d", conv_gen_config.batch_size)
    logger.info("  Turns: %d-%d", conv_gen_config.turns_min, conv_gen_config.turns_max)
    logger.info("  Temperature: %.2f", conv_gen_config.temperature)
    logger.info("  CEFR Levels: %s", conv_gen_config.target_cefr_levels)
    logger.info("  Dry Run: %s", conv_gen_config.dry_run)
    logger.info("")

    try:
        orchestrator = ConversationGenerationOrchestrator()
        metrics = orchestrator.run()

        logger.info("")
        logger.info("=" * 60)
        logger.info("Run Complete")
        logger.info("  Queue items processed: %d", metrics.queue_items_processed)
        logger.info("  Conversations generated: %d", metrics.conversations_generated)
        logger.info("  Conversations failed: %d", metrics.conversations_failed)
        logger.info("  Exercises generated: %d", metrics.exercises_generated)
        logger.info("  Execution time: %ds", metrics.execution_time_seconds or 0)
        logger.info("=" * 60)

    except NoQueueItemsError:
        logger.info("No pending queue items - nothing to process")

    except Exception as exc:
        logger.error("Conversation generation failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
