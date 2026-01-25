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
    TEST_GEN_DEBUG: Set to 'true' for verbose debugging
"""

import sys
import os
import logging
import traceback
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debug mode flag
DEBUG_MODE = os.getenv('TEST_GEN_DEBUG', 'true').lower() == 'true'


def setup_logging():
    """Configure logging for the script."""
    # Use DEBUG level if TEST_GEN_DEBUG is enabled
    if DEBUG_MODE:
        log_level = 'DEBUG'
    else:
        log_level = os.getenv('TEST_GEN_LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # In debug mode, also enable debug for test_generation modules
    if DEBUG_MODE:
        logging.getLogger('services.test_generation').setLevel(logging.DEBUG)
        logging.getLogger('services.test_generation.orchestrator').setLevel(logging.DEBUG)
        logging.getLogger('services.test_generation.agents').setLevel(logging.DEBUG)

    # Reduce noise from third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)


def wrap_agent_with_debug(agent, agent_name, logger):
    """Wrap an agent's main method with debug logging."""

    if agent_name == 'topic_translator':
        original_translate = agent.translate
        def debug_translate(*args, **kwargs):
            logger.info(f"[DEBUG] [{agent_name}] Starting translation...")
            logger.debug(f"[DEBUG] [{agent_name}]   Args: topic_concept={args[0][:50] if args else 'N/A'}...")
            logger.debug(f"[DEBUG] [{agent_name}]   Target language: {args[2] if len(args) > 2 else kwargs.get('target_language', 'N/A')}")
            logger.debug(f"[DEBUG] [{agent_name}]   Model override: {kwargs.get('model_override', 'default')}")
            try:
                result = original_translate(*args, **kwargs)
                logger.info(f"[DEBUG] [{agent_name}] Translation SUCCESS")
                return result
            except Exception as e:
                logger.error(f"[DEBUG] [{agent_name}] Translation FAILED: {type(e).__name__}: {e}")
                logger.error(f"[DEBUG] [{agent_name}] Traceback:\n{traceback.format_exc()}")
                raise
        agent.translate = debug_translate

    elif agent_name == 'prose_writer':
        original_generate = agent.generate_prose
        def debug_generate_prose(*args, **kwargs):
            logger.info(f"[DEBUG] [{agent_name}] Starting prose generation...")
            logger.debug(f"[DEBUG] [{agent_name}]   Language: {kwargs.get('language_name', args[1] if len(args) > 1 else 'N/A')}")
            logger.debug(f"[DEBUG] [{agent_name}]   Difficulty: {kwargs.get('difficulty', args[3] if len(args) > 3 else 'N/A')}")
            logger.debug(f"[DEBUG] [{agent_name}]   Word count: {kwargs.get('word_count_min', 'N/A')}-{kwargs.get('word_count_max', 'N/A')}")
            logger.debug(f"[DEBUG] [{agent_name}]   Model override: {kwargs.get('model_override', 'default')}")
            try:
                result = original_generate(*args, **kwargs)
                logger.info(f"[DEBUG] [{agent_name}] Prose generation SUCCESS ({len(result)} chars)")
                return result
            except Exception as e:
                logger.error(f"[DEBUG] [{agent_name}] Prose generation FAILED: {type(e).__name__}: {e}")
                logger.error(f"[DEBUG] [{agent_name}] Traceback:\n{traceback.format_exc()}")
                raise
        agent.generate_prose = debug_generate_prose

    elif agent_name == 'question_generator':
        original_generate = agent.generate_questions
        def debug_generate_questions(*args, **kwargs):
            logger.info(f"[DEBUG] [{agent_name}] Starting question generation...")
            logger.debug(f"[DEBUG] [{agent_name}]   Language: {kwargs.get('language_name', args[1] if len(args) > 1 else 'N/A')}")
            logger.debug(f"[DEBUG] [{agent_name}]   Question types: {kwargs.get('question_type_codes', 'N/A')}")
            logger.debug(f"[DEBUG] [{agent_name}]   Model override: {kwargs.get('model_override', 'default')}")
            try:
                result = original_generate(*args, **kwargs)
                logger.info(f"[DEBUG] [{agent_name}] Question generation SUCCESS ({len(result)} questions)")
                return result
            except Exception as e:
                logger.error(f"[DEBUG] [{agent_name}] Question generation FAILED: {type(e).__name__}: {e}")
                logger.error(f"[DEBUG] [{agent_name}] Traceback:\n{traceback.format_exc()}")
                raise
        agent.generate_questions = debug_generate_questions

    elif agent_name == 'audio_synthesizer':
        original_generate = agent.generate_and_upload
        def debug_generate_audio(*args, **kwargs):
            text = args[0] if args else kwargs.get('text', '')
            file_id = args[1] if len(args) > 1 else kwargs.get('file_id', 'N/A')
            voice = kwargs.get('voice', args[2] if len(args) > 2 else 'default')
            speed = kwargs.get('speed', args[3] if len(args) > 3 else 'default')

            logger.info(f"[DEBUG] [{agent_name}] Starting audio generation...")
            logger.debug(f"[DEBUG] [{agent_name}]   File ID: {file_id}")
            logger.debug(f"[DEBUG] [{agent_name}]   Voice: {voice}")
            logger.debug(f"[DEBUG] [{agent_name}]   Speed: {speed}")
            logger.debug(f"[DEBUG] [{agent_name}]   Text length: {len(text)} chars")
            logger.debug(f"[DEBUG] [{agent_name}]   Text preview: {text[:100]}...")
            try:
                result = original_generate(*args, **kwargs)
                logger.info(f"[DEBUG] [{agent_name}] Audio generation SUCCESS: {result}")
                return result
            except Exception as e:
                logger.error(f"[DEBUG] [{agent_name}] Audio generation FAILED: {type(e).__name__}: {e}")
                logger.error(f"[DEBUG] [{agent_name}] Traceback:\n{traceback.format_exc()}")
                raise
        agent.generate_and_upload = debug_generate_audio

        # Also wrap voice selection
        original_select_voice = agent.select_voice
        def debug_select_voice(*args, **kwargs):
            voice_ids = kwargs.get('voice_ids', args[0] if args else None)
            lang_code = kwargs.get('language_code', args[1] if len(args) > 1 else None)
            logger.debug(f"[DEBUG] [{agent_name}] Selecting voice...")
            logger.debug(f"[DEBUG] [{agent_name}]   Available voices: {voice_ids}")
            logger.debug(f"[DEBUG] [{agent_name}]   Language code: {lang_code}")
            result = original_select_voice(*args, **kwargs)
            logger.info(f"[DEBUG] [{agent_name}] Selected voice: {result}")
            return result
        agent.select_voice = debug_select_voice

    elif agent_name == 'title_generator':
        original_generate = agent.generate_title
        def debug_generate_title(*args, **kwargs):
            logger.info(f"[DEBUG] [{agent_name}] Starting title generation...")
            logger.debug(f"[DEBUG] [{agent_name}]   Language: {kwargs.get('language_name', 'N/A')}")
            try:
                result = original_generate(*args, **kwargs)
                logger.info(f"[DEBUG] [{agent_name}] Title generation SUCCESS: {result[:50] if result else 'None'}...")
                return result
            except Exception as e:
                logger.error(f"[DEBUG] [{agent_name}] Title generation FAILED: {type(e).__name__}: {e}")
                logger.error(f"[DEBUG] [{agent_name}] Traceback:\n{traceback.format_exc()}")
                raise
        agent.generate_title = debug_generate_title


def run_with_debug_wrapper(orchestrator, logger):
    """
    Run orchestrator with detailed debugging for each stage.
    Wraps the orchestrator to capture per-language and per-stage failures.
    """
    # Wrap all agents with debug logging
    logger.info("[DEBUG] Wrapping agents with debug logging...")
    wrap_agent_with_debug(orchestrator.topic_translator, 'topic_translator', logger)
    wrap_agent_with_debug(orchestrator.prose_writer, 'prose_writer', logger)
    wrap_agent_with_debug(orchestrator.question_generator, 'question_generator', logger)
    wrap_agent_with_debug(orchestrator.audio_synthesizer, 'audio_synthesizer', logger)
    wrap_agent_with_debug(orchestrator.title_generator, 'title_generator', logger)
    logger.info("[DEBUG] All agents wrapped")

    # Monkey-patch the _generate_test method to add debugging
    original_generate_test = orchestrator._generate_test

    def debug_generate_test(topic, lang_config, category_name, difficulty):
        """Wrapped _generate_test with detailed debugging."""
        logger.info("=" * 50)
        logger.info(f"[DEBUG] Starting test generation")
        logger.info(f"[DEBUG]   Language: {lang_config.language_name} ({lang_config.language_code})")
        logger.info(f"[DEBUG]   Topic: {topic.concept_english[:80]}...")
        logger.info(f"[DEBUG]   Difficulty: {difficulty}")
        logger.info(f"[DEBUG]   Category: {category_name}")
        logger.info("=" * 50)

        # Log language config details
        logger.info(f"[DEBUG] Language Config Details:")
        logger.info(f"[DEBUG]   ID: {lang_config.id}")
        logger.info(f"[DEBUG]   Prose Model: {lang_config.prose_model}")
        logger.info(f"[DEBUG]   Question Model: {lang_config.question_model}")
        logger.info(f"[DEBUG]   TTS Voice IDs: {lang_config.tts_voice_ids}")
        logger.info(f"[DEBUG]   TTS Speed: {lang_config.tts_speed}")

        try:
            result = original_generate_test(topic, lang_config, category_name, difficulty)
            logger.info(f"[DEBUG] Test generation SUCCEEDED for {lang_config.language_name} difficulty {difficulty}")
            return result

        except Exception as e:
            logger.error(f"[DEBUG] Test generation FAILED for {lang_config.language_name} difficulty {difficulty}")
            logger.error(f"[DEBUG] Error type: {type(e).__name__}")
            logger.error(f"[DEBUG] Error message: {str(e)}")
            logger.error(f"[DEBUG] Full traceback:\n{traceback.format_exc()}")
            raise

    # Apply the wrapper
    orchestrator._generate_test = debug_generate_test

    # Also wrap _process_queue_item for more context
    original_process_queue_item = orchestrator._process_queue_item

    def debug_process_queue_item(item):
        """Wrapped _process_queue_item with debugging."""
        logger.info("=" * 70)
        logger.info(f"[DEBUG] Processing Queue Item: {item.id}")
        logger.info(f"[DEBUG]   Topic ID: {item.topic_id}")
        logger.info(f"[DEBUG]   Language ID: {item.language_id}")
        logger.info(f"[DEBUG]   Status ID: {item.status_id}")
        logger.info("=" * 70)

        # Get language info for debugging
        try:
            lang_config = orchestrator.db.get_language_config(item.language_id)
            if lang_config:
                logger.info(f"[DEBUG] Language: {lang_config.language_name} ({lang_config.language_code})")
                # Dump full language config as JSON for inspection
                lang_config_dict = {
                    'id': lang_config.id,
                    'language_name': lang_config.language_name,
                    'language_code': lang_config.language_code,
                    'prose_model': lang_config.prose_model,
                    'question_model': lang_config.question_model,
                    'tts_voice_ids': lang_config.tts_voice_ids,
                    'tts_speed': lang_config.tts_speed,
                }
                logger.info(f"[DEBUG] Full language config:\n{json.dumps(lang_config_dict, indent=2, default=str)}")
            else:
                logger.error(f"[DEBUG] WARNING: Could not fetch language config for ID {item.language_id}")
        except Exception as e:
            logger.error(f"[DEBUG] Error fetching language config: {e}")

        try:
            result = original_process_queue_item(item)
            logger.info(f"[DEBUG] Queue item {item.id} completed with {result} tests generated")
            return result
        except Exception as e:
            logger.error(f"[DEBUG] Queue item {item.id} FAILED")
            logger.error(f"[DEBUG] Error: {e}")
            logger.error(f"[DEBUG] Full traceback:\n{traceback.format_exc()}")
            raise

    orchestrator._process_queue_item = debug_process_queue_item

    # Run the orchestrator
    return orchestrator.run()


def main():
    """Run test generation workflow."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("  Linguadojo Test Generation")
    logger.info(f"  Started: {datetime.now().isoformat()}")
    logger.info(f"  Debug Mode: {DEBUG_MODE}")
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

        # Use debug wrapper if DEBUG_MODE is enabled
        if DEBUG_MODE:
            logger.info("[DEBUG] Running with debug wrapper enabled")
            metrics = run_with_debug_wrapper(orchestrator, logger)
        else:
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
        if DEBUG_MODE:
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
        sys.exit(1)

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        if DEBUG_MODE:
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == '__main__':
    main()
