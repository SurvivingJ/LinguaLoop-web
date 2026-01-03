"""
Test Generation Orchestrator

Coordinates the test generation workflow:
1. Fetch pending items from production_queue
2. For each queue item, generate tests at multiple difficulty levels
3. Generate prose, questions, and audio for each test
4. Save to database and update queue status
"""

import time
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from .config import test_gen_config
from .database_client import (
    TestDatabaseClient,
    QueueItem,
    Topic,
    LanguageConfig,
    GeneratedTest,
    GeneratedQuestion,
    TestGenMetrics
)
from .agents import (
    ProseWriter,
    QuestionGenerator,
    QuestionValidator,
    AudioSynthesizer
)

logger = logging.getLogger(__name__)


class NoQueueItemsError(Exception):
    """Raised when no pending queue items are available."""
    pass


class TestGenerationOrchestrator:
    """Coordinates test generation workflow."""

    def __init__(self):
        """Initialize the orchestrator and all agents."""
        # Validate configuration
        if not test_gen_config.validate():
            raise ValueError("Invalid test generation configuration")

        # Initialize database client
        self.db = TestDatabaseClient()

        # Initialize agents
        self.prose_writer = ProseWriter()
        self.question_generator = QuestionGenerator()
        self.question_validator = QuestionValidator()
        self.audio_synthesizer = AudioSynthesizer()

        # Metrics tracking
        self.metrics: Optional[TestGenMetrics] = None

        logger.info("TestGenerationOrchestrator initialized")

    def run(self) -> TestGenMetrics:
        """
        Execute test generation workflow.

        Returns:
            TestGenMetrics: Execution statistics

        Workflow:
            1. Fetch pending queue items (up to batch_size)
            2. For each queue item:
                a. Get topic and language config
                b. For each target difficulty:
                    i. Get CEFR config (word counts, ELO)
                    ii. Generate prose
                    iii. Generate questions
                    iv. Validate questions
                    v. Generate audio
                    vi. Save test + questions + ratings
                c. Mark queue item complete
            3. Log metrics
        """
        start_time = time.time()

        # Initialize metrics
        self.metrics = TestGenMetrics(run_date=datetime.utcnow())

        try:
            logger.info("=" * 60)
            logger.info("Starting Test Generation Run")
            logger.info("=" * 60)
            logger.info(f"Batch size: {test_gen_config.batch_size}")
            logger.info(f"Target difficulties: {test_gen_config.target_difficulties}")
            logger.info(f"Dry run: {test_gen_config.dry_run}")

            # Step 1: Fetch pending queue items
            queue_items = self.db.get_pending_queue_items(
                limit=test_gen_config.batch_size
            )

            if not queue_items:
                logger.info("No pending queue items found")
                return self._finalize(start_time)

            logger.info(f"Found {len(queue_items)} pending queue items")

            # Step 2: Process each queue item
            for item in queue_items:
                try:
                    tests_generated = self._process_queue_item(item)
                    self.metrics.queue_items_processed += 1
                    self.metrics.tests_generated += tests_generated

                except Exception as e:
                    logger.error(f"Failed to process queue item {item.id}: {e}")
                    self.metrics.tests_failed += 1

                    if not test_gen_config.dry_run:
                        self.db.mark_queue_failed(item.id, str(e))

            return self._finalize(start_time)

        except Exception as e:
            logger.exception(f"Test generation run failed: {e}")
            if self.metrics:
                self.metrics.error_message = str(e)
            return self._finalize(start_time)

    def _process_queue_item(self, item: QueueItem) -> int:
        """
        Process a single queue item.

        Args:
            item: QueueItem from production_queue

        Returns:
            int: Number of tests generated
        """
        logger.info(f"Processing queue item: {item.id}")

        # Mark as processing
        if not test_gen_config.dry_run:
            self.db.mark_queue_processing(item.id)

        # Get topic details
        topic = self.db.get_topic(item.topic_id)
        if not topic:
            raise ValueError(f"Topic not found: {item.topic_id}")

        # Get language config
        lang_config = self.db.get_language_config(item.language_id)
        if not lang_config:
            raise ValueError(f"Language not found: {item.language_id}")

        # Get category name for prompts
        category_name = self.db.get_category_name(topic.category_id)

        logger.info(
            f"Topic: {topic.concept_english[:50]}... "
            f"Language: {lang_config.language_name}"
        )

        tests_generated = 0

        # Generate tests for each target difficulty
        for difficulty in test_gen_config.target_difficulties:
            try:
                success = self._generate_test(
                    topic=topic,
                    lang_config=lang_config,
                    category_name=category_name,
                    difficulty=difficulty
                )

                if success:
                    tests_generated += 1

            except Exception as e:
                logger.error(
                    f"Failed to generate test at difficulty {difficulty}: {e}"
                )
                # Continue with other difficulties

        # Mark queue item complete
        if not test_gen_config.dry_run:
            self.db.mark_queue_completed(item.id, tests_generated)

        logger.info(
            f"Queue item {item.id} complete: "
            f"{tests_generated}/{len(test_gen_config.target_difficulties)} tests"
        )

        return tests_generated

    def _generate_test(
        self,
        topic: Topic,
        lang_config: LanguageConfig,
        category_name: str,
        difficulty: int
    ) -> bool:
        """
        Generate a single test at specified difficulty.

        Args:
            topic: Topic details
            lang_config: Language configuration
            category_name: Category name
            difficulty: Difficulty level 1-9

        Returns:
            bool: True if successful
        """
        logger.info(f"Generating test: difficulty={difficulty}")

        # Get CEFR config
        word_min, word_max = self.db.get_word_count_range(difficulty)
        initial_elo = self.db.get_initial_elo(difficulty)

        # Get question distribution
        question_types = self.db.get_question_distribution(difficulty)

        # Generate slug
        slug = self.db.generate_test_slug(
            lang_config.language_code,
            difficulty,
            topic.concept_english
        )

        logger.debug(f"Test slug: {slug}")

        # Step 1: Generate prose
        prose_template = self.db.get_prompt_template(
            'prose_generation',
            lang_config.language_code
        )

        prose = self.prose_writer.generate_prose(
            topic_concept=topic.concept_english,
            language_name=lang_config.language_name,
            language_code=lang_config.language_code,
            difficulty=difficulty,
            word_count_min=word_min,
            word_count_max=word_max,
            prompt_template=prose_template,
            model_override=lang_config.prose_model
        )

        logger.debug(f"Generated prose: {len(prose.split())} words")

        # Step 2: Generate questions
        question_templates = {}
        for type_code in set(question_types):
            template = self.db.get_prompt_template(
                f'question_{type_code}',
                lang_config.language_code
            )
            if template:
                question_templates[type_code] = template

        questions = self.question_generator.generate_questions(
            prose=prose,
            language_name=lang_config.language_name,
            question_type_codes=question_types,
            prompt_templates=question_templates,
            model_override=lang_config.question_model
        )

        # Step 3: Validate questions
        valid_questions, errors = self.question_validator.validate_all_questions(
            questions, prose
        )

        if errors:
            for error in errors:
                logger.warning(f"Question validation: {error}")

        if len(valid_questions) < 3:
            raise ValueError(
                f"Too few valid questions: {len(valid_questions)}/5"
            )

        # Step 4: Generate audio
        voice = self.audio_synthesizer.select_voice(
            voice_ids=lang_config.tts_voice_ids,
            language_code=lang_config.language_code
        )

        if not test_gen_config.dry_run:
            self.audio_synthesizer.generate_and_upload(
                text=prose,
                slug=slug,
                voice=voice,
                speed=lang_config.tts_speed
            )
        else:
            logger.info(f"[DRY RUN] Would generate audio: {slug}")

        # Step 5: Save to database
        if not test_gen_config.dry_run:
            # Insert test
            test = GeneratedTest(
                slug=slug,
                language_id=lang_config.id,
                topic_id=topic.id,
                difficulty=difficulty,
                transcript=prose,
                gen_user=test_gen_config.system_user_id,
                initial_elo=initial_elo
            )
            self.db.insert_test(test)

            # Insert questions
            db_questions = []
            for q in valid_questions:
                type_id = self.db.get_question_type_id(q.get('type_code', ''))
                db_questions.append(GeneratedQuestion(
                    test_slug=slug,
                    question_text=q['question'],
                    choices=q['choices'],
                    answer=q['answer'],
                    question_type_id=type_id,
                    display_order=q.get('display_order', 1)
                ))
            self.db.insert_questions(db_questions)

            # Insert skill ratings
            self.db.insert_test_skill_ratings(slug, initial_elo)

            logger.info(f"Test saved: {slug}")
        else:
            logger.info(f"[DRY RUN] Would save test: {slug}")

        return True

    def _finalize(self, start_time: float) -> TestGenMetrics:
        """
        Calculate final metrics and persist to database.

        Args:
            start_time: Workflow start timestamp

        Returns:
            TestGenMetrics: Complete execution statistics
        """
        if self.metrics is None:
            self.metrics = TestGenMetrics(run_date=datetime.utcnow())

        self.metrics.execution_time_seconds = int(time.time() - start_time)

        # Persist metrics (unless dry run)
        if not test_gen_config.dry_run:
            try:
                self.db.insert_generation_run(self.metrics)
            except Exception as e:
                logger.error(f"Failed to save metrics: {e}")
        else:
            logger.info("[DRY RUN] Metrics not saved to database")

        # Log summary
        logger.info("=" * 60)
        logger.info("Test Generation Run Complete")
        logger.info("=" * 60)
        logger.info(f"  Queue Items Processed: {self.metrics.queue_items_processed}")
        logger.info(f"  Tests Generated: {self.metrics.tests_generated}")
        logger.info(f"  Tests Failed: {self.metrics.tests_failed}")
        logger.info(f"  Duration: {self.metrics.execution_time_seconds}s")
        if self.metrics.error_message:
            logger.error(f"  Error: {self.metrics.error_message}")
        logger.info("=" * 60)

        return self.metrics

    def run_single(self, queue_id: UUID) -> int:
        """
        Process a single queue item by ID.

        Args:
            queue_id: Queue item UUID

        Returns:
            int: Number of tests generated
        """
        # Fetch the specific queue item
        response = self.db.client.table('production_queue') \
            .select('*') \
            .eq('id', str(queue_id)) \
            .single() \
            .execute()

        if not response.data:
            raise ValueError(f"Queue item not found: {queue_id}")

        row = response.data
        item = QueueItem(
            id=UUID(row['id']),
            topic_id=UUID(row['topic_id']),
            language_id=row['language_id'],
            status_id=row['status_id'],
            created_at=datetime.fromisoformat(
                row['created_at'].replace('Z', '+00:00')
            ),
            tests_generated=row.get('tests_generated', 0) or 0,
            error_log=row.get('error_log')
        )

        return self._process_queue_item(item)
