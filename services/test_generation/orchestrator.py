"""
Test Generation Orchestrator

Coordinates the test generation workflow:
1. Fetch pending items from production_queue
2. For each queue item, generate tests at multiple difficulty levels
3. Generate prose, questions, and audio for each test
4. Save to database and update queue status
5. Extract vocabulary and generate word sense definitions
"""

import os
import time
import logging
import threading
from concurrent.futures import as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional
from uuid import UUID, uuid4

from postgrest.exceptions import APIError

from .config import get_test_gen_config
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
from services.vocabulary.sense_generator import (
    SenseGenerator, find_sentence, retry_transient_db_call,
)
from services.vocabulary.frequency_service import compute_zipf_for_vocab_item
# Fail-closed judging (TASK-510/727). Imported at module top rather than lazily
# because `run`/`run_batch` open the guard before any generation begins — an
# ImportError here must surface at import, not halfway through a batch.
from services.exercise_generation.judges.base import (
    JudgeUnavailable, batch_mode, BatchModeThreadPoolExecutor,
)
from services.timing import stage

logger = logging.getLogger(__name__)

DIFFICULTY_LABELS = {
    1: 'beginner', 2: 'beginner', 3: 'elementary',
    4: 'intermediate', 5: 'intermediate', 6: 'upper-int',
    7: 'advanced', 8: 'advanced', 9: 'advanced',
}


def _flag_reasons(flags: dict) -> list:
    """Judge names for `generation_review_queue.flag_reasons`, axis-qualified.

    TASK-720 redefined the distractor judge's review band as *judge
    uncertainty* rather than one named defect, which makes the bare judge name
    useless on its own: "distractor_plausibility" no longer tells a reviewer
    anything except that a judge was unsure. Each distractor outcome carries
    `flag_axes` (see `schemas.axes_to_verdict`), so the reason becomes
    `distractor_plausibility:confusability` — the judge, and which of its two
    questions it could not answer confidently.

    Single-axis judges keep their bare name; so does a distractor flag from a
    pre-v7 prompt row, whose outcomes have no axis attribution at all. Both
    read back as today's values, so existing queue rows stay comparable.
    """
    reasons = []
    for judge, payload in flags.items():
        axes = sorted({
            axis
            for item in (payload if isinstance(payload, list) else [])
            if isinstance(item, dict)
            for axis in (item.get('flag_axes') or [])
        })
        if axes:
            reasons.extend(f'{judge}:{axis}' for axis in axes)
        else:
            reasons.append(judge)
    return reasons


def _write_review_queue_rows(
    db,
    valid_questions: list,
    db_questions: list,
) -> None:
    """Best-effort: insert generation_review_queue rows for flagged questions.

    Called after insert_questions so every db_questions[i].id is already
    persisted to the questions table.  Never raises — review-queue failure
    must not abort a test.
    """
    try:
        rows = []
        for q_entry, gq in zip(valid_questions, db_questions):
            flags = q_entry.get('_judge_flags')
            if not flags:
                continue
            rows.append({
                'artifact_kind': 'test_question',
                'artifact_id':   str(gq.id),
                'flag_reasons':  _flag_reasons(flags),
                'judge_scores':  flags,
                'status':        'pending',
            })
        if rows:
            db.table('generation_review_queue').insert(rows).execute()
            logger.info("Queued %d flagged question(s) for review", len(rows))
    except Exception as exc:
        logger.warning("Failed to write review_queue rows (non-fatal): %s", exc)


@dataclass
class BatchConfig:
    """Configuration for a batch test generation run."""
    language_code: str                                # ISO 639-1: 'zh', 'en', 'ja'
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


def _subject_kwargs(topic_concept: str, keywords) -> dict:
    """Topic data for the distractor judge's subject/domain slot — OFF by default.

    Returns ``{}`` unless ``JUDGE_SUBJECT_KEYWORDS`` is truthy, so the judge
    keeps inferring the subject from the passage as it always has.

    The off-state is a MEASURED decision, not the TASK-717 bug reappearing.
    That bug was the argument going missing silently; this is a documented
    default with a test pinning both branches.

    Supplying an authoritative domain line was expected to LOOSEN the judge's
    off-topic band (it is a domain-membership test, and the judge had been
    inventing the boundary). On the frozen 150-question sample it TIGHTENED it:
    "concept + five keywords" is a narrower membership test than one inferred
    from a whole passage. ja rejects rose in both arms that included the line —
    on the v4 rubric 6→8 questions and 7→11 band-2 distractors, on v5 4→11 and
    4→13 — while zh and en did not move. Re-enable once TASK-718 has settled the
    judge model and TASK-719 has a rubric that consumes the line correctly.

    See wiki/evaluations/distractor-judge-language-divergence-2026-08-16 §10.
    """
    enabled = os.environ.get('JUDGE_SUBJECT_KEYWORDS', '').strip().lower()
    if enabled not in ('1', 'true', 'yes', 'on'):
        return {}
    return {'topic_concept': topic_concept, 'keywords': keywords}


class TestGenerationOrchestrator:
    """Coordinates test generation workflow."""

    def __init__(self):
        """Initialize the orchestrator and all agents."""
        # Validate configuration
        if not get_test_gen_config().validate():
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

        # Vocab cache: (lemma, language_id) → vocab_id. Guarded by
        # _vocab_cache_lock — TASK-737: _generate_vocabulary now fans its
        # per-word loop out across a thread pool, and this cache (plus the
        # select-then-insert it guards) is shared across those threads.
        self._vocab_cache: dict[tuple[str, int], int] = {}
        self._vocab_cache_lock = threading.Lock()

        # Metrics tracking
        self.metrics: Optional[TestGenMetrics] = None

        # Tests saved with incomplete vocabulary this run. Vocab failure is
        # non-fatal by design (see _generate_vocabulary), which means without a
        # counter a run that enriched nothing reports exactly like a clean one.
        self.vocab_shortfalls: int = 0

        logger.info("TestGenerationOrchestrator initialized")

    def run(self) -> TestGenMetrics:
        """Execute the queue-driven test generation workflow, fail-closed.

        The body lives in ``_run_impl``; this wrapper exists only to open
        ``batch_mode()`` around it, and must stay outside ``_run_impl``'s own
        ``try`` — inside it, the outer ``except Exception`` would catch
        ``JudgeUnavailable`` before the guard could mean anything.

        Inside the block a judge that cannot resolve its template or model
        raises ``JudgeUnavailable`` and aborts the run instead of returning
        ``safe_accept()`` for every question. Two total outages came from a
        delisted model slug doing exactly that silently — see
        ``services/exercise_generation/judges/base.py`` (TASK-510). Serve-path
        callers never enter this method, so a learner waiting on a session
        still gets the fail-open contract.

        Returns:
            TestGenMetrics: Execution statistics
        """
        with batch_mode():
            return self._run_impl()

    def _run_impl(self) -> TestGenMetrics:
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
        cfg = get_test_gen_config()
        dry_run = cfg.dry_run

        # Initialize metrics
        self.metrics = TestGenMetrics(run_date=datetime.now(timezone.utc))

        try:
            logger.info("=" * 60)
            logger.info("Starting Test Generation Run")
            logger.info("=" * 60)
            logger.info(f"Batch size: {cfg.batch_size}")
            logger.info(f"Target difficulties: {cfg.target_difficulties}")
            logger.info(f"Dry run: {dry_run}")

            # Step 1: Fetch pending queue items
            queue_items = self.db.get_pending_queue_items(
                limit=cfg.batch_size
            )

            if not queue_items:
                logger.info("No pending queue items found")
                return self._finalize(start_time, dry_run)

            logger.info(f"Found {len(queue_items)} pending queue items")

            # Step 2: Process each queue item
            for item in queue_items:
                try:
                    tests_generated = self._process_queue_item(item, dry_run)
                    self.metrics.queue_items_processed += 1
                    self.metrics.tests_generated += tests_generated

                except JudgeUnavailable:
                    # A judge outage, not a bad queue item. Marking the item
                    # failed and moving to the next one would work through the
                    # whole queue writing unjudged questions — the outage this
                    # run is wrapped in batch_mode() to prevent. Abort.
                    raise

                except Exception as e:
                    logger.error(f"Failed to process queue item {item.id}: {e}")
                    self.metrics.tests_failed += 1

                    if not dry_run:
                        self.db.mark_queue_failed(item.id, str(e))

            return self._finalize(start_time, dry_run)

        except JudgeUnavailable:
            # Recorded as an abort, not a completed run: _finalize() would
            # persist a generation_run row and log "Run Complete", which is how
            # an unjudged batch previously read as a normal finish.
            logger.exception("Test generation run ABORTED — judge unavailable")
            raise

        except Exception as e:
            logger.exception(f"Test generation run failed: {e}")
            if self.metrics:
                self.metrics.error_message = str(e)
            return self._finalize(start_time, dry_run)

    def _process_queue_item(self, item: QueueItem, dry_run: bool) -> int:
        """
        Process a single queue item.

        Args:
            item: QueueItem from production_queue
            dry_run: If True, skip all database writes

        Returns:
            int: Number of tests generated
        """
        logger.info(f"Processing queue item: {item.id}")

        # Mark as processing
        if not dry_run:
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

        # Constrain the difficulty range to the topic's age tier (ADR-003) when
        # set: a T2 topic only yields tests within its difficulty_min..max, not
        # the full 1-9 span. Legacy/untiered topics (target_age_tier is None)
        # fall back to the configured schedule -> no regression.
        target_difficulties = get_test_gen_config().target_difficulties
        if topic.target_age_tier is not None:
            tier_difficulties = self.db.get_tier_difficulties(topic.target_age_tier)
            if tier_difficulties:
                target_difficulties = tier_difficulties
                logger.info(
                    "Topic tier T%s -> difficulties %s",
                    topic.target_age_tier, tier_difficulties,
                )

        # Generate tests for each target difficulty
        for difficulty in target_difficulties:
            try:
                success = self._generate_test(
                    topic=topic,
                    lang_config=lang_config,
                    category_name=category_name,
                    difficulty=difficulty,
                    dry_run=dry_run,
                )

                if success:
                    tests_generated += 1

            except JudgeUnavailable:
                # Innermost judge-path handler. "Continue with other
                # difficulties" past a dead judge is precisely how a whole
                # topic ships unjudged.
                raise

            except Exception as e:
                logger.error(
                    f"Failed to generate test at difficulty {difficulty}: {e}"
                )
                # Continue with other difficulties

        # Mark queue item complete
        if not dry_run:
            self.db.mark_queue_completed(item.id, tests_generated)

        logger.info(
            f"Queue item {item.id} complete: "
            f"{tests_generated}/{len(target_difficulties)} tests"
        )

        return tests_generated

    def _generate_test(
        self,
        topic: Topic,
        lang_config: LanguageConfig,
        category_name: str,
        difficulty: int,
        test_type: str = 'listening',
        dry_run: bool = False,
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

        # TASK-737: per-stage wall clock for this test, logged at the end and
        # threaded into _generate_vocabulary — the only way to see where the
        # ~2.9 min/test baseline (services/test_generation economics) was
        # actually going before picking what to parallelize.
        stage_seconds: dict[str, float] = {}

        # Get tier config
        cefr_config = self.db.get_cefr_config(difficulty)
        word_min, word_max = self.db.get_word_count_range(difficulty)
        tier_initial_elo = self.db.get_initial_elo(difficulty)
        complexity_tier = cefr_config.tier_code if cefr_config else 'T3'

        # Tier midpoint is the prior; difficulty_scorer refines this with
        # passage-derived lexical complexity once prose is generated below.
        initial_elo = tier_initial_elo
        seeded_elo: Optional[int] = None

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
            with stage('translate', stage_seconds):
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

        with stage('prose', stage_seconds):
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

        # Difficulty scorer: refine tier midpoint with passage-derived lexical
        # complexity. Failure here must not block the test — fall back to the
        # tier midpoint and warn.
        try:
            from services.test_generation.difficulty_scorer import seed_test_elo
            with stage('difficulty_scorer', stage_seconds):
                seeded_elo, _sig = seed_test_elo(
                    prose=prose,
                    language_code=lang_config.language_code,
                    target_difficulty=difficulty,
                    tier_initial_elo=tier_initial_elo,
                )
            initial_elo = seeded_elo
            logger.info(
                f"Seeded ELO {seeded_elo} (tier midpoint {tier_initial_elo}, "
                f"delta {seeded_elo - tier_initial_elo:+d})"
            )
        except Exception as exc:
            logger.warning(
                f"difficulty_scorer failed ({exc}); falling back to tier midpoint {tier_initial_elo}"
            )
            seeded_elo = None
            initial_elo = tier_initial_elo

        # Step 1.5: Generate title
        title_template = self.db.get_prompt_template(
            'title_generation',
            lang_config.id
        )

        title = None
        try:
            with stage('title', stage_seconds):
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

        # Step 2: Generate questions. get_prompt_template raises if a question
        # template is missing — no silent fallback to legacy inline prompts.
        question_templates = {}
        for type_code in set(question_types):
            question_templates[type_code] = self.db.get_prompt_template(
                f'question_{type_code}',
                lang_config.id  # Use language_id, not language_code
            )

        # Skip the LLM judges (answer-entailment + distractor-plausibility) at
        # low difficulty. T1/T2 toddler passages are deliberately simple and
        # explicit ("The car is red"), so their answers are legitimately obvious
        # and the distractor-plausibility judge rejects nearly every question —
        # a category error that was zeroing out d1/d2 tests. Judges still run at
        # d>=3, where distractor richness is a meaningful quality signal. The
        # judges run only when both db and language_id are passed.
        run_judges = difficulty > 2
        with stage('questions', stage_seconds):
            questions = self.question_generator.generate_questions(
                prose=prose,
                language_name=lang_config.language_name,
                question_type_codes=question_types,
                difficulty=difficulty,  # Pass difficulty for templates
                prompt_templates=question_templates,
                model_override=lang_config.question_model,
                language_id=lang_config.id if run_judges else None,
                db=self.db.client if run_judges else None,
                # Feeds the distractor judge's subject/domain slot (prompt {5}).
                # The TRANSLATED pair, so a zh/ja judge prompt never gets an
                # English subject line. See _subject_kwargs for why it is off.
                **_subject_kwargs(translated_topic, translated_keywords),
            )

        # Step 3: Validate questions. generate_questions now runs the validator
        # in-loop per type (regenerating on rejection), so every returned
        # question should already pass here — this call is a cheap idempotent
        # safety net and still feeds the funnel diagnostic below.
        valid_questions, errors = self.question_validator.validate_all_questions(
            questions, prose
        )

        if errors:
            for error in errors:
                logger.warning(f"Question validation: {error}")

        cfg = get_test_gen_config()
        # Survival floor. At low difficulty (T1/T2 toddler passages, ~74 words)
        # a 5-question set cannot reliably survive validation: vocabulary_context
        # rejects ~30% of the time at this level and 3 literal_detail questions
        # collide on the Jaccard-overlap check, so the old 4-of-5 floor produced
        # intermittent "Too few valid questions: 0/5" aborts. Accept 3-of-5 at
        # d1/d2 (margin of 2); keep the standard "tolerate losing one" elsewhere.
        requested = len(question_types)
        min_questions = 3 if difficulty <= 2 else max(3, requested - 1)
        if len(valid_questions) < min_questions:
            # Funnel diagnostics: decompose where questions were lost so the
            # survival floor / judge strictness can be tuned per difficulty.
            # requested -> generated (post-judge) -> valid (post-validator).
            generated = len(questions)
            judge_rejections = getattr(
                self.question_generator, 'last_rejections', []
            )
            logger.warning(
                "Question funnel starved (diff=%s, lang=%s): "
                "requested=%d generated=%d valid=%d (floor=%d) | "
                "lost_to_generation_or_judges=%d lost_to_validation=%d | "
                "judge_rejections=%s | validation_errors=%s",
                difficulty, lang_config.language_code,
                requested, generated, len(valid_questions), min_questions,
                requested - generated, generated - len(valid_questions),
                judge_rejections, errors,
            )
            raise ValueError(
                f"Too few valid questions: {len(valid_questions)}/{requested} "
                f"(floor {min_questions}; generated {generated}, "
                f"{len(judge_rejections)} judge-rejected, "
                f"{generated - len(valid_questions)} validator-rejected)"
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

            if not dry_run:
                with stage('audio', stage_seconds):
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
        if not dry_run:
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
                gen_user=cfg.system_user_id,
                initial_elo=initial_elo,
                audio_url=audio_url,
                title=title,
                seeded_elo=seeded_elo,
            )
            self.db.insert_test(test)

            # Insert questions — pre-generate UUIDs so flagged questions can be
            # referenced in generation_review_queue before the rows exist there.
            db_questions = []
            for i, q in enumerate(valid_questions):
                type_id = self.db.get_question_type_id(q.get('type_code', ''))
                db_questions.append(GeneratedQuestion(
                    id=uuid4(),
                    test_id=test_id,
                    question_id=f"{slug}-q{i+1}",
                    question_text=q['question'],
                    choices=q['choices'],
                    answer=q['answer'],
                    question_type_id=type_id,
                    distractor_types=q.get('distractor_types')
                ))
            self.db.insert_questions(db_questions)

            # Enqueue judge-flagged questions for human review.
            _write_review_queue_rows(
                db=self.db.client,
                valid_questions=valid_questions,
                db_questions=db_questions,
            )

            # Insert skill ratings
            self.db.insert_test_skill_ratings(
                test_id=test_id,
                initial_elo=initial_elo,
                has_audio=bool(audio_url),
                language_id=lang_config.id
            )

            # Generate pinyin payload for Chinese tests
            if lang_config.language_code == 'zh' and prose:
                try:
                    from services.pinyin_service import process_passage
                    pinyin_payload = process_passage(prose)
                    self.db.client.table('tests').update({
                        'pinyin_payload': pinyin_payload
                    }).eq('id', str(test_id)).execute()
                    logger.info(f"Pinyin payload generated for {slug}")
                except Exception as e:
                    logger.warning(f"Pinyin payload generation failed (non-fatal): {e}")

            # Japanese script payloads — the counterpart to the zh branch above.
            # This path had no ja equivalent, so every test generated by the
            # batch runner shipped with furigana_payload NULL (all 83 live ja
            # tests, as of 2026-08-22) and relied on
            # scripts/batch_generate_pitch_accent.py to fill pitch after the
            # fact. services/test_service.py (the single-test UI path) has
            # always written both here; this brings the batch path in line.
            #
            # Both are non-fatal for the same reason the rest of this step is:
            # the prose, questions and audio are already written and paid for,
            # and both payloads have standalone backfill scripts
            # (batch_generate_furigana.py, batch_generate_pitch_accent.py).
            if lang_config.language_code == 'ja' and prose:
                try:
                    from services.pitch_accent_service import (
                        process_passage as process_pitch_passage,
                    )
                    self.db.client.table('tests').update({
                        'pitch_payload': process_pitch_passage(prose)
                    }).eq('id', str(test_id)).execute()
                    logger.info(f"Pitch accent payload generated for {slug}")
                except Exception as e:
                    logger.warning(
                        f"Pitch accent payload generation failed (non-fatal): {e}"
                    )

                try:
                    from services.furigana_service import process_test_payload
                    # valid_questions is the SAME list, in the SAME order, that
                    # built db_questions above with question_id "<slug>-qN" —
                    # so payload index i corresponds to question N=i+1. The
                    # frontend looks questions up positionally
                    # (furiganaPayload.questions[index]), which is only sound
                    # because the read paths sort by question_id.
                    self.db.client.table('tests').update({
                        'furigana_payload': process_test_payload(
                            prose, valid_questions
                        )
                    }).eq('id', str(test_id)).execute()
                    logger.info(f"Furigana payload generated for {slug}")
                except Exception as e:
                    logger.warning(
                        f"Furigana payload generation failed (non-fatal): {e}"
                    )

            logger.info(f"Test saved: {slug}")

            # Step 6: Extract vocabulary and generate word senses
            self._generate_vocabulary(
                test_id=test_id,
                transcript=prose,
                lang_config=lang_config,
                stage_seconds=stage_seconds,
            )
        else:
            logger.info(f"[DRY RUN] Would save test: {slug}")

        logger.info(
            "Stage timing for %s: %s (total %.1fs)",
            slug, {k: round(v, 1) for k, v in stage_seconds.items()},
            sum(stage_seconds.values()),
        )
        return True

    def _generate_vocabulary(
        self,
        test_id: UUID,
        transcript: str,
        lang_config: LanguageConfig,
        stage_seconds: dict[str, float] | None = None,
    ):
        """
        Step 6: Extract vocabulary, create dim_vocabulary entries,
        generate word sense definitions, and update the test row.

        ``stage_seconds`` is the same per-test timing bucket _generate_test
        builds up (TASK-737); a fresh dict is used when called standalone
        (e.g. from a backfill script) so this method never requires it.

        Non-fatal — vocabulary failure does not fail the test. Prose,
        questions and audio are already written and paid for by the time this
        runs, and a test is playable without its vocabulary layer; senses are
        an enrichment with a dedicated repair path (scripts/backfill_senses.py).
        Discarding a finished test over a missing enrichment costs more than it
        saves.

        What is NOT acceptable is a silent shortfall. Every exit path below
        records the outcome in tests.vocab_sense_stats — including the paths
        that produce nothing — so an incomplete test is queryable after the
        fact instead of being indistinguishable from one that never ran, and
        the run summary counts it.
        """
        stage_seconds = {} if stage_seconds is None else stage_seconds
        outcome = {
            'words_attempted': 0,
            'unique_senses': 0,
            'senses_failed': 0,
            'senses_skipped': 0,
            'both_models_failed': 0,
            'phrases': 0,
            'single_words': 0,
        }
        try:
            # Extract vocabulary with metadata
            with stage('vocab_extract', stage_seconds):
                vocab_items = self.vocab_pipeline.extract_detailed(
                    transcript, lang_config.language_code
                )
            if not vocab_items:
                logger.warning(f"No vocabulary extracted for test {test_id}")
                self._record_vocab_outcome(
                    test_id, outcome, reason='no_vocabulary_extracted'
                )
                return

            db = self.db.client
            sense_gen = SenseGenerator(
                openai_client=self.prose_writer.client,
                db=db,
                db_client=self.db,
                language_code=lang_config.language_code,
                language_id=lang_config.id,
                # Sense model now defaults to the cheap hosted sense model
                # (SENSE_MODEL_DEFAULT); pass None to use it rather than the
                # prose model. prefer_existing skips words already seeded by the
                # backfill so inline test-gen stays fast.
                model=None,
                prefer_existing=True,
            )

            # TASK-737: this loop was the dominant cost of test generation
            # (~82% of per-test wall clock per the batch economics) precisely
            # because it called out to the LLM once per extracted word, one
            # at a time. Each word is independent — no cross-word dependency
            # — so it fans out across a thread pool instead.
            # BatchModeThreadPoolExecutor (not a bare ThreadPoolExecutor) so
            # the fail-closed judge contract from run()/run_batch()'s
            # batch_mode() carries into the workers if a judge is ever added
            # to this path (see judges/base.py).
            #
            # A per-item exception is now caught and skipped rather than
            # aborting every remaining word in the transcript — the loop-level
            # try/except this call sits inside already treats the whole
            # vocabulary step as non-fatal to the test, so narrowing that to
            # per-word is a strict improvement, not a behaviour change in
            # what "non-fatal" means here.
            def _sense_for_item(item: dict) -> int | None:
                vocab_id = self._get_or_create_vocab_id(
                    db, item, lang_config.id, lang_config.language_code
                )
                sentence = find_sentence(transcript, item['lemma'])
                return sense_gen.generate_sense(
                    vocab_id=vocab_id,
                    lemma=item['lemma'],
                    phrase_type=item.get('phrase_type'),
                    sentence=sentence,
                    transcript=transcript,
                )

            sense_ids = []
            workers = max(1, min(
                get_test_gen_config().vocab_sense_workers, len(vocab_items),
            ))
            with stage('vocab_senses_llm', stage_seconds):
                with BatchModeThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {
                        pool.submit(_sense_for_item, item): item
                        for item in vocab_items
                    }
                    for future in as_completed(futures):
                        item = futures[future]
                        try:
                            sense_id = future.result()
                        except JudgeUnavailable:
                            # A judge outage during a batch aborts the batch —
                            # see the module-level contract in judges/base.py.
                            raise
                        except Exception as exc:
                            logger.error(
                                "Sense generation raised for lemma %r "
                                "(test %s): %s", item.get('lemma'), test_id, exc,
                            )
                            continue
                        if sense_id is not None:
                            sense_ids.append(sense_id)

            outcome.update({
                'words_attempted': len(vocab_items),
                'unique_senses': len(sense_ids),
                'senses_failed': sense_gen.stats['senses_failed'],
                'senses_skipped': sense_gen.stats['senses_skipped'],
                'both_models_failed': sense_gen.stats['both_models_failed'],
                'phrases': sum(
                    1 for v in vocab_items if v.get('is_phrase')
                ),
                'single_words': sum(
                    1 for v in vocab_items if not v.get('is_phrase')
                ),
            })

            if sense_ids:
                # Build token map for frontend rendering
                token_map = self._build_token_map(
                    db, transcript, lang_config.language_code, lang_config.id,
                    sense_ids=sense_ids
                )

                db.table('tests').update({
                    'vocab_sense_ids': sense_ids,
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
                    f"Vocabulary: {len(sense_ids)}/{len(vocab_items)} word senses linked "
                    f"({sense_gen.stats['senses_created']} new, "
                    f"{sense_gen.stats['senses_reused']} reused, "
                    f"{outcome['senses_failed']} failed, "
                    f"{outcome['senses_skipped']} skipped), "
                    f"{len(token_map)} tokens in map, "
                    f"{len(questions.data or [])} questions updated with sense_ids"
                )
                self._record_vocab_outcome(test_id, outcome)
            else:
                self._record_vocab_outcome(
                    test_id, outcome, reason='no_senses_generated'
                )

        except Exception as e:
            # Vocab failure is non-fatal — the test is still usable without its
            # vocabulary layer. Recorded rather than merely logged: a swallowed
            # exception here is exactly how a whole run of NULL-vocab tests
            # previously passed unnoticed.
            logger.error(f"Vocabulary generation failed for test {test_id}: {e}")
            self._record_vocab_outcome(
                test_id, outcome, reason=f"exception: {type(e).__name__}: {e}"[:300]
            )

    def _record_vocab_outcome(
        self, test_id: UUID, outcome: dict, reason: str | None = None
    ) -> None:
        """Persist the vocabulary outcome to tests.vocab_sense_stats and count
        any shortfall against the run.

        A test is `complete` only when every extracted word ended up either
        linked to a sense or deliberately skipped by the model (proper nouns,
        numerals, symbols). Anything else — a failed generation, an empty
        extraction, a swallowed exception — is a shortfall, gets a
        `shortfall_reason`, and is logged at WARNING so it cannot be read as a
        pass in the run output.
        """
        accounted = outcome['unique_senses'] + outcome['senses_skipped']
        complete = reason is None and accounted >= outcome['words_attempted']

        stats = dict(outcome)
        stats['complete'] = complete
        if not complete:
            stats['shortfall_reason'] = reason or 'senses_missing'

        try:
            self.db.client.table('tests').update({
                'vocab_sense_stats': stats,
            }).eq('id', str(test_id)).execute()
        except Exception as e:
            # Last line of defence: if even the shortfall record cannot be
            # written, say so loudly rather than returning quietly.
            logger.error(
                f"Could not record vocab outcome for test {test_id}: {e}"
            )

        if not complete:
            self.vocab_shortfalls += 1
            logger.warning(
                f"VOCAB SHORTFALL test={test_id} "
                f"linked={outcome['unique_senses']}/{outcome['words_attempted']} "
                f"failed={outcome['senses_failed']} "
                f"skipped={outcome['senses_skipped']} "
                f"both_models_failed={outcome['both_models_failed']} "
                f"reason={stats['shortfall_reason']}"
            )

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

    @retry_transient_db_call
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

        # Whole method under one lock (TASK-737): _generate_vocabulary now
        # calls this from a thread pool, one thread per extracted vocab word.
        # The DB round-trips here are cheap relative to the LLM call the
        # caller makes next, so serializing them fully is the simplest safe
        # option — it turns the in-process race on a brand-new lemma (two
        # threads both cache-miss, both insert) into a queue instead of
        # relying solely on the cross-process 23505 handler below.
        with self._vocab_cache_lock:
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

            # dim_vocabulary is shared across every run, so after a few hundred
            # tests most lemmas in a transcript already exist. Look before
            # inserting: a bare insert raises APIError 23505 on uq_vocab_lemma, and
            # the caller's `for item in vocab_items` loop has no per-item guard, so
            # that one exception aborts vocabulary for the *whole test* at its first
            # already-known word — leaving vocab_sense_ids empty and
            # vocab_token_map NULL while the run still reports "pass".
            existing = db.table('dim_vocabulary') \
                .select('id') \
                .eq('lemma', lemma) \
                .eq('language_id', language_id) \
                .limit(1) \
                .execute()

            if existing.data:
                vocab_id = existing.data[0]['id']
            else:
                try:
                    response = db.table('dim_vocabulary') \
                        .insert(row) \
                        .execute()
                    vocab_id = response.data[0]['id']
                except APIError as exc:
                    # Lost the insert race to a concurrent worker (another
                    # process, or another orchestrator run) between the select
                    # above and this insert — re-read rather than fail.
                    if getattr(exc, 'code', None) != '23505':
                        raise
                    lookup = db.table('dim_vocabulary') \
                        .select('id') \
                        .eq('lemma', lemma) \
                        .eq('language_id', language_id) \
                        .single() \
                        .execute()
                    vocab_id = lookup.data['id']

            self._vocab_cache[cache_key] = vocab_id
            return vocab_id

    def _finalize(self, start_time: float, dry_run: bool) -> TestGenMetrics:
        """
        Calculate final metrics and persist to database.

        Args:
            start_time: Workflow start timestamp
            dry_run: If True, skip persisting metrics

        Returns:
            TestGenMetrics: Complete execution statistics
        """
        if self.metrics is None:
            self.metrics = TestGenMetrics(run_date=datetime.now(timezone.utc))

        self.metrics.execution_time_seconds = int(time.time() - start_time)

        # Persist metrics (unless dry run)
        if not dry_run:
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
        if self.vocab_shortfalls:
            logger.warning(
                f"  Vocab Shortfalls: {self.vocab_shortfalls} test(s) saved with "
                f"incomplete vocabulary — query "
                f"tests.vocab_sense_stats->>'shortfall_reason', repair with "
                f"scripts/backfill_senses.py"
            )
        else:
            logger.info("  Vocab Shortfalls: 0")
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

        dry_run = get_test_gen_config().dry_run
        return self._process_queue_item(item, dry_run)

    # ============================================================
    # BATCH GENERATION (count-based, balanced difficulty)
    # ============================================================

    def run_batch(self, config: BatchConfig) -> TestGenMetrics:
        """Generate a fixed number of tests, fail-closed on judge outages.

        Wrapper around ``_run_batch_impl`` that opens ``batch_mode()``; see
        ``run`` for why the guard sits outside the implementation's ``try``
        and why the serve path is unaffected.

        Args:
            config: BatchConfig with language, count, difficulty, etc.

        Returns:
            TestGenMetrics with per-run statistics.

        Raises:
            JudgeUnavailable: a judge could not run. The batch is abandoned
                rather than shipping unjudged questions; queue items are left
                un-completed so the work can be re-run after the judge is fixed.
        """
        with batch_mode():
            return self._run_batch_impl(config)

    def _run_batch_impl(self, config: BatchConfig) -> TestGenMetrics:
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

        self.metrics = TestGenMetrics(run_date=datetime.now(timezone.utc))

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

            # Track tests generated per queue item (items are cycled when count > len(queue_items))
            per_item_counts: dict[str, int] = {qi['id']: 0 for qi in queue_items}

            # TASK-737: this loop used to generate one test at a time — the
            # single biggest lever for batch-scale throughput, since each test
            # is already a long serial chain of LLM calls internally (Phase 1
            # further parallelized the vocab/question sub-chains, but that
            # only compresses *inside* one test; running N tests at once
            # divides the total wall clock by N directly).
            #
            # BatchModeThreadPoolExecutor so JudgeUnavailable propagates
            # fail-closed from a worker thread — see judges/base.py. All
            # per-slot outcome bookkeeping (metrics, diff_stats,
            # per_item_counts) is collected from the worker's return value and
            # applied only on this thread after future.result(), never
            # mutated inside the worker — the same collect-then-merge shape
            # used by scripts/run_content_build.py's phase_ladder.
            def _generate_one(i: int, diff: int) -> dict:
                qi_idx = i % len(queue_items)
                qi_row = queue_items[qi_idx]

                topic = self.db.get_topic(UUID(qi_row['topic_id']))
                if not topic:
                    return {
                        'outcome': 'topic_missing', 'qi_id': qi_row['id'],
                        'topic_id': qi_row['topic_id'],
                    }

                category_name = self.db.get_category_name(topic.category_id)

                # Rate limiting: paces THIS worker's own call rate, after the
                # call like the original serial loop did (never on a
                # JudgeUnavailable abort — that still propagates immediately,
                # matching the old control flow). With batch_test_workers > 1
                # the aggregate submission rate is now workers/delay rather
                # than 1/delay — a deliberate consequence of adding
                # concurrency, not a silent drop of the --delay flag's effect.
                try:
                    success = self._generate_test(
                        topic=topic,
                        lang_config=lang_config,
                        category_name=category_name,
                        difficulty=diff,
                        test_type=config.test_type,
                        dry_run=config.dry_run,
                    )
                except JudgeUnavailable:
                    raise
                except Exception:
                    if config.delay_ms > 0:
                        time.sleep(config.delay_ms / 1000.0)
                    raise

                if config.delay_ms > 0:
                    time.sleep(config.delay_ms / 1000.0)
                return {
                    'outcome': 'pass' if success else 'skip',
                    'qi_id': qi_row['id'],
                }

            workers = max(1, min(
                get_test_gen_config().batch_test_workers, len(difficulty_schedule),
            ))
            with BatchModeThreadPoolExecutor(max_workers=workers) as pool:
                futures = {}
                for i, diff in enumerate(difficulty_schedule):
                    if i < config.start_index:
                        continue
                    # Stop check gates further SUBMISSION only — futures
                    # already in flight are allowed to finish rather than
                    # being force-cancelled mid-call.
                    if config.stop_check and config.stop_check():
                        logger.info(
                            "Stop requested — no further tests submitted "
                            "after [%d/%d]", i, config.count,
                        )
                        break
                    futures[pool.submit(_generate_one, i, diff)] = (i, diff)

                for future in as_completed(futures):
                    i, diff = futures[future]
                    try:
                        result = future.result()
                    except JudgeUnavailable:
                        # Counting this as one failed slot and continuing
                        # would spend the rest of the batch writing unjudged
                        # questions, visible only as a raised error count in
                        # the summary table. Abort the batch instead — the
                        # `with` block above still waits for already-running
                        # futures to finish before this propagates.
                        logger.error(
                            "[%d/%d] %s | %s | diff=%d | ABORT: judge unavailable",
                            i + 1, config.count, config.language_code,
                            config.test_type, diff,
                        )
                        raise
                    except Exception as e:
                        self.metrics.tests_failed += 1
                        diff_stats[diff]['errors'] += 1
                        logger.error(
                            "[%d/%d] %s | %s | diff=%d | ERROR: %s",
                            i + 1, config.count, config.language_code,
                            config.test_type, diff, str(e),
                        )
                        continue

                    outcome = result['outcome']
                    if outcome == 'topic_missing':
                        logger.warning(
                            "[%d/%d] Topic not found: %s — skipping",
                            i + 1, config.count, result['topic_id'],
                        )
                        diff_stats[diff]['skipped'] += 1
                    elif outcome == 'pass':
                        self.metrics.tests_generated += 1
                        diff_stats[diff]['generated'] += 1
                        per_item_counts[result['qi_id']] += 1
                        logger.info(
                            "[%d/%d] %s | %s | diff=%d (%s) | pass",
                            i + 1, config.count, config.language_code,
                            config.test_type, diff,
                            DIFFICULTY_LABELS.get(diff, '?'),
                        )
                    else:  # 'skip'
                        diff_stats[diff]['skipped'] += 1
                        logger.info(
                            "[%d/%d] %s | %s | diff=%d | skip",
                            i + 1, config.count, config.language_code,
                            config.test_type, diff,
                        )

            # Mark processed queue items complete, using per-item counts so that
            # cycled batches (count > len(queue_items)) record accurate per-item totals.
            if not config.dry_run and self.metrics.tests_generated > 0:
                for qi_row in queue_items:
                    item_count = per_item_counts.get(qi_row['id'], 0)
                    try:
                        self.db.mark_queue_completed(
                            UUID(qi_row['id']),
                            item_count,
                        )
                    except Exception as e:
                        logger.warning(
                            "Failed to mark queue item %s as completed: %s",
                            qi_row['id'], e,
                        )

            # Log summary table
            self._log_batch_summary(
                lang_config.language_name, config.test_type, diff_stats
            )

            return self._finalize(start_time, config.dry_run)

        except JudgeUnavailable:
            # Raised past _finalize() deliberately — see `run`. Note this is
            # also *before* the mark_queue_completed loop above, so the queue
            # items stay pending and the batch can be re-run once the judge's
            # prompt_templates row / model slug is fixed.
            logger.exception("Batch generation ABORTED — judge unavailable")
            raise

        except Exception as e:
            logger.exception(f"Batch generation failed: {e}")
            if self.metrics:
                self.metrics.error_message = str(e)
            return self._finalize(start_time, config.dry_run)

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

        difficulties = list(get_test_gen_config().target_difficulties)
        if not difficulties:
            difficulties = [1, 3, 6, 9]

        per_level = count // len(difficulties)
        remainder = count % len(difficulties)

        # Distribute remainder to middle difficulties first
        mid = len(difficulties) // 2
        schedule: list[int] = []
        for d in difficulties:
            schedule.extend([d] * per_level)

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
