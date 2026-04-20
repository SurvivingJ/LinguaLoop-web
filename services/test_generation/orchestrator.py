"""
Test Generation Orchestrator

Coordinates the test generation workflow:
1. Fetch pending items from production_queue
2. For each queue item, generate tests at multiple difficulty levels
3. Generate prose, questions, and audio for each test
4. Save to database and update queue status
5. Extract vocabulary and generate word sense definitions
"""

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional
from uuid import UUID, uuid4

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
    TopicTranslator,
    ProseWriter,
    TitleGenerator,
    QuestionGenerator,
    QuestionValidator,
    AudioSynthesizer
)
from services.vocabulary.pipeline import VocabularyExtractionPipeline
from services.vocabulary.sense_generator import SenseGenerator, find_sentence
from services.vocabulary.frequency_service import compute_zipf_for_vocab_item
from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)

DIFFICULTY_LABELS = {
    1: 'beginner', 2: 'beginner', 3: 'elementary',
    4: 'intermediate', 5: 'intermediate', 6: 'upper-int',
    7: 'advanced', 8: 'advanced', 9: 'advanced',
}


@dataclass
class BatchConfig:
    """Configuration for a batch test generation run."""
    language_code: str                                # 'cn', 'en', 'jp'
    count: int = 20                                   # tests to generate
    test_type: str = 'listening'                      # 'listening' | 'reading'
    difficulty: Optional[int] = None                  # 1-9 or None (balanced)
    topic_source: str = 'queue'                       # 'queue'
    dry_run: bool = False
    start_index: int = 0                              # resume from index
    delay_ms: int = 0                                 # ms between LLM calls
    stop_check: Optional[Callable[[], bool]] = field(default=None, repr=False)


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
        self.topic_translator = TopicTranslator()
        self.prose_writer = ProseWriter()
        self.title_generator = TitleGenerator()
        self.question_generator = QuestionGenerator()
        self.question_validator = QuestionValidator()
        self.audio_synthesizer = AudioSynthesizer()

        # Initialize vocabulary pipeline (reuses existing OpenAI client)
        self.vocab_pipeline = VocabularyExtractionPipeline(
            openai_client=self.prose_writer.client,
            db_client=self.db,
        )

        # Vocab cache: (lemma, language_id) → vocab_id
        self._vocab_cache: dict[tuple[str, int], int] = {}

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
                    i. Get tier config (word counts, ELO)
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
        difficulty: int,
        test_type: str = 'listening',
    ) -> bool:
        """
        Generate a single test at specified difficulty.

        Args:
            topic: Topic details
            lang_config: Language configuration
            category_name: Category name
            difficulty: Difficulty level 1-9
            test_type: 'listening' or 'reading'

        Returns:
            bool: True if successful
        """
        logger.info(f"Generating test: difficulty={difficulty}, type={test_type}")

        # Get tier config
        cefr_config = self.db.get_cefr_config(difficulty)
        word_min, word_max = self.db.get_word_count_range(difficulty)
        initial_elo = self.db.get_initial_elo(difficulty)
        complexity_tier = cefr_config.tier_code if cefr_config else 'T3'

        # Get question distribution
        question_types = self.db.get_question_distribution(difficulty)

        # Generate slug
        slug = self.db.generate_test_slug(
            lang_config.language_code,
            difficulty,
            topic.concept_english
        )

        logger.debug(f"Test slug: {slug}")

        # Step 0: Translate topic to target language (skip for English)
        if self.topic_translator.should_translate(lang_config.language_code):
            translated_topic, translated_keywords = self.topic_translator.translate(
                topic_concept=topic.concept_english,
                keywords=topic.keywords,
                target_language=lang_config.language_name,
                model_override=lang_config.prose_model
            )
            logger.info(f"Translated topic to {lang_config.language_name}")
        else:
            translated_topic = topic.concept_english
            translated_keywords = topic.keywords

        # Step 1: Generate prose
        prose_template = self.db.get_prompt_template(
            'prose_generation',
            lang_config.id  # Use language_id, not language_code
        )

        prose = self.prose_writer.generate_prose(
            topic_concept=translated_topic,  # Use translated topic
            language_name=lang_config.language_name,
            language_code=lang_config.language_code,
            difficulty=difficulty,
            word_count_min=word_min,
            word_count_max=word_max,
            keywords=translated_keywords,  # Use translated keywords
            complexity_tier=complexity_tier,
            prompt_template=prose_template,
            model_override=lang_config.prose_model
        )

        logger.debug(f"Generated prose: {len(prose.split())} words")

        # Validation gate: prose length
        if not prose or len(prose.strip()) < 50:
            raise ValueError(f"Prose too short: {len(prose.strip()) if prose else 0} chars (min 50)")

        # Step 1.5: Generate title
        title_template = self.db.get_prompt_template(
            'title_generation',
            lang_config.id
        )

        title = None
        try:
            title = self.title_generator.generate_title(
                prose=prose,
                topic_concept=translated_topic,
                difficulty=difficulty,
                complexity_tier=complexity_tier,
                language_name=lang_config.language_name,
                language_code=lang_config.language_code,
                prompt_template=title_template,
                model_override=lang_config.question_model
            )
            logger.info(f"Generated title: {title[:50]}...")
        except Exception as e:
            logger.warning(f"Title generation failed, continuing with NULL title: {e}")
            title = None

        # Step 2: Generate questions
        question_templates = {}
        for type_code in set(question_types):
            template = self.db.get_prompt_template(
                f'question_{type_code}',
                lang_config.id  # Use language_id, not language_code
            )
            if template:
                question_templates[type_code] = template

        questions = self.question_generator.generate_questions(
            prose=prose,
            language_name=lang_config.language_name,
            question_type_codes=question_types,
            difficulty=difficulty,  # Pass difficulty for templates
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

        min_questions = max(3, test_gen_config.questions_per_test - 1)
        if len(valid_questions) < min_questions:
            raise ValueError(
                f"Too few valid questions: {len(valid_questions)}/{test_gen_config.questions_per_test}"
            )

        # Step 3.5: Generate test UUID early (will use for both audio filename and test.id)
        test_id = uuid4()

        # Step 4: Generate audio (listening tests only)
        audio_url = ""
        if test_type == 'listening':
            voice = self.audio_synthesizer.select_voice(
                voice_ids=lang_config.tts_voice_ids,
                language_code=lang_config.language_code
            )

            if not test_gen_config.dry_run:
                audio_url = self.audio_synthesizer.generate_and_upload(
                    text=prose,
                    file_id=str(test_id),
                    voice=voice,
                    speed=lang_config.tts_speed
                )
            else:
                logger.info(f"[DRY RUN] Would generate audio: {test_id}.mp3")
        else:
            logger.info(f"Skipping audio generation for {test_type} test")

        # Step 5: Save to database
        if not test_gen_config.dry_run:
            # Insert test
            test = GeneratedTest(
                id=test_id,
                slug=slug,
                language_id=lang_config.id,
                language_name=lang_config.language_name,
                topic_id=topic.id,
                topic_name=topic.concept_english,
                difficulty=difficulty,
                transcript=prose,
                gen_user=test_gen_config.system_user_id,
                initial_elo=initial_elo,
                audio_url=audio_url,
                title=title
            )
            self.db.insert_test(test)

            # Insert questions
            db_questions = []
            for i, q in enumerate(valid_questions):
                type_id = self.db.get_question_type_id(q.get('type_code', ''))
                db_questions.append(GeneratedQuestion(
                    test_id=test_id,
                    question_id=f"{slug}-q{i+1}",
                    question_text=q['question'],
                    choices=q['choices'],
                    answer=q['answer'],
                    question_type_id=type_id,
                    distractor_types=q.get('distractor_types')
                ))
            self.db.insert_questions(db_questions)

            # Insert skill ratings
            self.db.insert_test_skill_ratings(
                test_id=test_id,
                initial_elo=initial_elo,
                has_audio=bool(audio_url),
                language_id=lang_config.id
            )

            # Generate pinyin payload for Chinese tests
            if lang_config.id == 1 and prose:
                try:
                    from services.pinyin_service import process_passage
                    pinyin_payload = process_passage(prose)
                    self.db.client.table('tests').update({
                        'pinyin_payload': pinyin_payload
                    }).eq('id', str(test_id)).execute()
                    logger.info(f"Pinyin payload generated for {slug}")
                except Exception as e:
                    logger.warning(f"Pinyin payload generation failed (non-fatal): {e}")

            logger.info(f"Test saved: {slug}")

            # Step 6: Extract vocabulary and generate word senses
            self._generate_vocabulary(
                test_id=test_id,
                transcript=prose,
                lang_config=lang_config,
            )
        else:
            logger.info(f"[DRY RUN] Would save test: {slug}")

        return True

    def _generate_vocabulary(
        self,
        test_id: UUID,
        transcript: str,
        lang_config: LanguageConfig,
    ):
        """
        Step 6: Extract vocabulary, create dim_vocabulary entries,
        generate word sense definitions, and update the test row.

        Non-fatal — vocabulary failure does not fail the test.
        """
        try:
            # Extract vocabulary with metadata
            vocab_items = self.vocab_pipeline.extract_detailed(
                transcript, lang_config.language_code
            )
            if not vocab_items:
                logger.warning(f"No vocabulary extracted for test {test_id}")
                return

            db = get_supabase_admin()
            sense_gen = SenseGenerator(
                openai_client=self.prose_writer.client,
                db=db,
                db_client=self.db,
                language_code=lang_config.language_code,
                language_id=lang_config.id,
                model=lang_config.prose_model,
            )

            sense_ids = []
            for item in vocab_items:
                vocab_id = self._get_or_create_vocab_id(
                    db, item, lang_config.id, lang_config.language_code
                )
                sentence = find_sentence(transcript, item['lemma'])
                sense_id = sense_gen.generate_sense(
                    vocab_id=vocab_id,
                    lemma=item['lemma'],
                    phrase_type=item.get('phrase_type'),
                    sentence=sentence,
                    transcript=transcript,
                )
                if sense_id is not None:
                    sense_ids.append(sense_id)

            if sense_ids:
                vocab_stats = {
                    'unique_senses': len(sense_ids),
                    'phrases': sum(
                        1 for v in vocab_items if v.get('is_phrase')
                    ),
                    'single_words': sum(
                        1 for v in vocab_items if not v.get('is_phrase')
                    ),
                }

                # Build token map for frontend rendering
                token_map = self._build_token_map(
                    db, transcript, lang_config.language_code, lang_config.id,
                    sense_ids=sense_ids
                )

                db.table('tests').update({
                    'vocab_sense_ids': sense_ids,
                    'vocab_sense_stats': vocab_stats,
                    'vocab_token_map': token_map,
                }).eq('id', str(test_id)).execute()

                # Assign per-question sense_ids: match vocab lemmas against
                # each question's text + choices (not all transcript senses)
                questions = db.table('questions') \
                    .select('id, question_text, choices, answer') \
                    .eq('test_id', str(test_id)) \
                    .execute()

                lemma_to_sense = self._build_sense_lookup(db, sense_ids)
                for q in (questions.data or []):
                    q_senses = self._match_question_senses(
                        q, lemma_to_sense, sense_ids
                    )
                    db.table('questions') \
                        .update({'sense_ids': q_senses}) \
                        .eq('id', q['id']) \
                        .execute()

                logger.info(
                    f"Vocabulary: {len(sense_ids)} word senses generated "
                    f"({sense_gen.stats['senses_created']} new, "
                    f"{sense_gen.stats['senses_reused']} reused), "
                    f"{len(token_map)} tokens in map, "
                    f"{len(questions.data or [])} questions updated with sense_ids"
                )
            else:
                logger.warning(f"No word senses generated for test {test_id}")

        except Exception as e:
            # Vocab failure is non-fatal — test is still usable without vocab
            logger.error(f"Vocabulary generation failed for test {test_id}: {e}")

    def _build_sense_lookup(
        self, db, sense_ids: list[int]
    ) -> dict[str, int]:
        """Reverse-lookup: sense_ids → vocab_id → lemma → {lemma: sense_id}."""
        if not sense_ids:
            return {}

        sense_to_vocab: dict[int, int] = {}
        for i in range(0, len(sense_ids), 500):
            chunk = sense_ids[i:i + 500]
            result = db.table('dim_word_senses') \
                .select('id, vocab_id') \
                .in_('id', chunk) \
                .execute()
            for row in (result.data or []):
                sense_to_vocab[row['id']] = row['vocab_id']

        vocab_ids = list(set(sense_to_vocab.values()))
        vocab_to_lemma: dict[int, str] = {}
        for i in range(0, len(vocab_ids), 500):
            chunk = vocab_ids[i:i + 500]
            result = db.table('dim_vocabulary') \
                .select('id, lemma') \
                .in_('id', chunk) \
                .execute()
            for row in (result.data or []):
                vocab_to_lemma[row['id']] = row['lemma']

        lemma_to_sense: dict[str, int] = {}
        for sense_id, vocab_id in sense_to_vocab.items():
            lemma = vocab_to_lemma.get(vocab_id)
            if lemma and lemma not in lemma_to_sense:
                lemma_to_sense[lemma] = sense_id

        return lemma_to_sense

    @staticmethod
    def _match_question_senses(
        question: dict,
        lemma_to_sense: dict[str, int],
        all_sense_ids: list[int],
    ) -> list[int]:
        """Determine which sense_ids are relevant to a specific question.

        Matches vocabulary lemmas against the question text + answer choices.
        Falls back to all_sense_ids if no matches found (shouldn't happen
        for well-formed questions about the passage).
        """
        # Build the searchable text from question text + choices + answer
        text_parts = [question.get('question_text', '')]
        choices = question.get('choices') or []
        if isinstance(choices, list):
            text_parts.extend(choices)
        answer = question.get('answer', '')
        if answer:
            text_parts.append(answer)
        searchable = ' '.join(text_parts).lower()

        matched_senses = []
        for lemma, sense_id in lemma_to_sense.items():
            if lemma.lower() in searchable:
                matched_senses.append(sense_id)

        # Fallback: if no vocab matched (e.g. inference questions),
        # assign all senses so BKT still gets signal from this question
        if not matched_senses:
            return all_sense_ids

        return matched_senses

    def _build_token_map(
        self, db, transcript: str, language_code: str, language_id: int,
        sense_ids: list[int] | None = None
    ) -> list:
        """Build vocab token map: [[display_text, sense_id_or_0], ...]."""
        tokens = self.vocab_pipeline.tokenize_full(transcript, language_code)

        # Strategy 1: Reverse-lookup from just-generated sense_ids
        sense_lookup = self._build_sense_lookup(db, sense_ids or [])

        # Strategy 2: Collect vocab_ids for cache-based lookup
        vocab_ids_needed = set()
        token_vocab_ids = []
        for display_text, lemma, is_content in tokens:
            vid = self._vocab_cache.get((lemma, language_id)) if is_content else None
            token_vocab_ids.append(vid)
            if vid:
                vocab_ids_needed.add(vid)

        # Batch-fetch best sense for each vocab_id
        sense_map = {}
        if vocab_ids_needed:
            result = db.table('dim_word_senses') \
                .select('id, vocab_id, sense_rank') \
                .in_('vocab_id', list(vocab_ids_needed)) \
                .order('sense_rank') \
                .execute()
            for row in (result.data or []):
                vid = row['vocab_id']
                if vid not in sense_map:
                    sense_map[vid] = row['id']

        token_map = []
        for i, (display_text, lemma, is_content) in enumerate(tokens):
            sid = 0
            if is_content and lemma:
                # Try reverse lookup first
                sid = sense_lookup.get(lemma, 0)
                if not sid:
                    # Fall back to cache-based lookup
                    vid = token_vocab_ids[i]
                    sid = sense_map.get(vid, 0) if vid else 0
            token_map.append([display_text, sid])

        return token_map

    def _get_or_create_vocab_id(
        self, db, item: dict, language_id: int, language_code: str
    ) -> int:
        """
        Get existing vocab ID or create new entry in dim_vocabulary.

        Args:
            db: Supabase admin client
            item: Dict from extract_detailed() with lemma, pos, is_phrase, etc.
            language_id: Integer language ID

        Returns:
            Integer vocab ID
        """
        lemma = item['lemma']
        cache_key = (lemma, language_id)

        if cache_key in self._vocab_cache:
            return self._vocab_cache[cache_key]

        # Insert new vocab entry
        row = {
            'lemma': lemma,
            'language_id': language_id,
            'part_of_speech': item.get('pos'),
        }

        if item.get('phrase_type'):
            row['phrase_type'] = item['phrase_type']
        if item.get('components'):
            row['component_lemmas'] = item['components']

        zipf = compute_zipf_for_vocab_item(item, language_code)
        if zipf is not None:
            row['frequency_rank'] = zipf

        response = db.table('dim_vocabulary') \
            .insert(row) \
            .execute()

        if response.data and len(response.data) > 0:
            vocab_id = response.data[0]['id']
        else:
            # Race condition: another process inserted it
            lookup = db.table('dim_vocabulary') \
                .select('id') \
                .eq('lemma', lemma) \
                .eq('language_id', language_id) \
                .single() \
                .execute()
            vocab_id = lookup.data['id']

        self._vocab_cache[cache_key] = vocab_id
        return vocab_id

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

    # ============================================================
    # BATCH GENERATION (count-based, balanced difficulty)
    # ============================================================

    def run_batch(self, config: BatchConfig) -> TestGenMetrics:
        """
        Generate a fixed number of tests with balanced difficulty distribution.

        When config.difficulty is None, tests are spread evenly across
        target_difficulties (default [1,3,6,9]).  When set, all tests
        use that single difficulty level.

        Args:
            config: BatchConfig with language, count, difficulty, etc.

        Returns:
            TestGenMetrics with per-run statistics.
        """
        start_time = time.time()

        # Apply dry_run override
        original_dry_run = test_gen_config.dry_run
        if config.dry_run:
            test_gen_config.dry_run = True

        self.metrics = TestGenMetrics(run_date=datetime.utcnow())

        try:
            # Resolve language
            lang_config = self.db.get_language_config_by_code(config.language_code)
            if not lang_config:
                raise ValueError(f"Unknown language code: {config.language_code}")

            # Build difficulty schedule
            difficulty_schedule = self._build_difficulty_schedule(
                config.count, config.difficulty
            )

            logger.info("=" * 60)
            logger.info("Batch Test Generation")
            logger.info("=" * 60)
            logger.info(
                f"Language: {lang_config.language_name} | "
                f"Type: {config.test_type} | Count: {config.count}"
            )
            if config.difficulty:
                logger.info(f"Fixed difficulty: {config.difficulty}")
            else:
                diff_counts = {}
                for d in difficulty_schedule:
                    diff_counts[d] = diff_counts.get(d, 0) + 1
                logger.info(f"Balanced distribution: {diff_counts}")
            logger.info(f"Dry run: {config.dry_run}")
            logger.info("=" * 60)

            # Fetch queue items
            pending_status_id = self.db._get_status_id('pending')
            queue_resp = self.db.client.table('production_queue') \
                .select('*') \
                .eq('status_id', pending_status_id) \
                .eq('language_id', lang_config.id) \
                .limit(config.count) \
                .execute()

            queue_items = queue_resp.data or []
            if not queue_items:
                logger.warning("No pending queue items for %s", config.language_code)
                return self._finalize(start_time)

            # Track per-difficulty results for summary
            diff_stats: dict[int, dict[str, int]] = {}
            for d in set(difficulty_schedule):
                diff_stats[d] = {'generated': 0, 'skipped': 0, 'errors': 0}

            # Main generation loop
            for i, diff in enumerate(difficulty_schedule):
                if i < config.start_index:
                    continue

                # Stop check
                if config.stop_check and config.stop_check():
                    logger.info("Stop requested — aborting at [%d/%d]", i + 1, config.count)
                    break

                # Pick queue item (cycle if fewer items than count)
                qi_idx = i % len(queue_items)
                qi_row = queue_items[qi_idx]

                topic = self.db.get_topic(UUID(qi_row['topic_id']))
                if not topic:
                    logger.warning("[%d/%d] Topic not found: %s — skipping",
                                   i + 1, config.count, qi_row['topic_id'])
                    diff_stats[diff]['skipped'] += 1
                    continue

                category_name = self.db.get_category_name(topic.category_id)

                try:
                    success = self._generate_test(
                        topic=topic,
                        lang_config=lang_config,
                        category_name=category_name,
                        difficulty=diff,
                        test_type=config.test_type,
                    )
                    if success:
                        self.metrics.tests_generated += 1
                        diff_stats[diff]['generated'] += 1
                        logger.info(
                            "[%d/%d] %s | %s | diff=%d (%s) | pass",
                            i + 1, config.count, config.language_code,
                            config.test_type, diff,
                            DIFFICULTY_LABELS.get(diff, '?'),
                        )
                    else:
                        diff_stats[diff]['skipped'] += 1
                        logger.info(
                            "[%d/%d] %s | %s | diff=%d | skip",
                            i + 1, config.count, config.language_code,
                            config.test_type, diff,
                        )

                except Exception as e:
                    self.metrics.tests_failed += 1
                    diff_stats[diff]['errors'] += 1
                    logger.error(
                        "[%d/%d] %s | %s | diff=%d | ERROR: %s",
                        i + 1, config.count, config.language_code,
                        config.test_type, diff, str(e),
                    )

                # Rate limiting
                if config.delay_ms > 0:
                    time.sleep(config.delay_ms / 1000.0)

            # Mark processed queue items complete (first batch only)
            if not config.dry_run and self.metrics.tests_generated > 0:
                for qi_row in queue_items:
                    try:
                        self.db.mark_queue_completed(
                            UUID(qi_row['id']),
                            self.metrics.tests_generated,
                        )
                    except Exception:
                        pass

            # Log summary table
            self._log_batch_summary(
                lang_config.language_name, config.test_type, diff_stats
            )

            return self._finalize(start_time)

        except Exception as e:
            logger.exception(f"Batch generation failed: {e}")
            if self.metrics:
                self.metrics.error_message = str(e)
            return self._finalize(start_time)

        finally:
            test_gen_config.dry_run = original_dry_run

    @staticmethod
    def _build_difficulty_schedule(
        count: int, fixed_difficulty: Optional[int] = None,
    ) -> list[int]:
        """Build an ordered list of difficulty levels for the batch.

        When *fixed_difficulty* is set every slot uses that value.
        Otherwise slots are distributed evenly across target_difficulties,
        with remainder going to the middle levels.
        """
        if fixed_difficulty is not None:
            return [fixed_difficulty] * count

        difficulties = list(test_gen_config.target_difficulties)
        if not difficulties:
            difficulties = [1, 3, 6, 9]

        per_level = count // len(difficulties)
        remainder = count % len(difficulties)

        # Distribute remainder to middle difficulties first
        mid = len(difficulties) // 2
        schedule: list[int] = []
        for idx, d in enumerate(difficulties):
            n = per_level
            # Give remainder to indices nearest the middle
            dist_from_mid = abs(idx - mid)
            if remainder > 0 and dist_from_mid <= remainder:
                # Simpler: just hand out remainder round-robin from the middle out
                pass
            schedule.extend([d] * n)

        # Distribute remainder round-robin starting from middle
        remainder_indices = sorted(
            range(len(difficulties)),
            key=lambda i: abs(i - mid),
        )
        for r in range(remainder):
            d = difficulties[remainder_indices[r % len(remainder_indices)]]
            schedule.append(d)

        return schedule

    @staticmethod
    def _log_batch_summary(
        language_name: str,
        test_type: str,
        diff_stats: dict[int, dict[str, int]],
    ) -> None:
        """Log a formatted summary table of batch results."""
        logger.info("")
        logger.info("=" * 50)
        logger.info("  Batch Complete")
        logger.info("=" * 50)
        logger.info(f"  Language: {language_name} | Type: {test_type}")
        logger.info("  %-12s %-10s %-8s %-6s", "Difficulty", "Generated", "Skipped", "Errors")
        logger.info("  " + "-" * 40)

        total_gen = total_skip = total_err = 0
        for diff in sorted(diff_stats.keys()):
            s = diff_stats[diff]
            label = DIFFICULTY_LABELS.get(diff, '?')
            logger.info(
                "  %-12s %-10d %-8d %-6d",
                f"{diff} ({label})", s['generated'], s['skipped'], s['errors'],
            )
            total_gen += s['generated']
            total_skip += s['skipped']
            total_err += s['errors']

        logger.info("  " + "-" * 40)
        logger.info("  %-12s %-10d %-8d %-6d", "TOTAL", total_gen, total_skip, total_err)
        logger.info("=" * 50)
