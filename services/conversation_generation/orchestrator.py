"""
Conversation Generation Orchestrator

Coordinates the conversation generation workflow:
1. Fetch pending items from conversation_generation_queue
2. For each queue item, load scenario + persona pair
3. Generate multi-turn conversation via ConversationWriter
4. Analyze conversation via ConversationAnalyzer
5. Save conversation to database
6. Generate exercises via existing ExerciseGenerationOrchestrator
7. Track metrics and update queue status
"""

import time
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .config import conv_gen_config
from .database_client import (
    ConversationDatabaseClient,
    ConvQueueItem,
    ConvGenMetrics,
)
from .agents import (
    PersonaDesigner,
    ScenarioPlanner,
    ConversationWriter,
    ConversationAnalyzer,
)
from .exercise_adapter import ConversationExerciseAdapter
from .quality_checker import ConversationQualityChecker
from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


class NoQueueItemsError(Exception):
    """Raised when no pending queue items are available."""
    pass


class ConversationGenerationOrchestrator:
    """Coordinates conversation generation workflow."""

    def __init__(self):
        """Initialize the orchestrator and all agents."""
        if not conv_gen_config.validate():
            raise ValueError("Invalid conversation generation configuration")

        # Initialize database client
        self.db = ConversationDatabaseClient()

        # Initialize agents
        self.persona_designer = PersonaDesigner()
        self.scenario_planner = ScenarioPlanner()
        self.conversation_writer = ConversationWriter()
        self.conversation_analyzer = ConversationAnalyzer()

        # Exercise adapter
        self.exercise_adapter = ConversationExerciseAdapter()

        # Quality checker
        self.quality_checker = ConversationQualityChecker()

        # Prompt template cache
        self._prompt_cache: dict[str, str] = {}

        # Metrics tracking
        self.metrics: Optional[ConvGenMetrics] = None

    def run(self) -> ConvGenMetrics:
        """
        Execute the conversation generation pipeline.

        Returns:
            ConvGenMetrics with run statistics.
        """
        start_time = time.time()
        self.metrics = ConvGenMetrics(run_date=datetime.utcnow())

        logger.info("Starting conversation generation run")

        # Fetch pending queue items
        queue_items = self.db.get_pending_queue_items(
            limit=conv_gen_config.batch_size
        )

        if not queue_items:
            logger.info("No pending queue items - nothing to do")
            raise NoQueueItemsError("No pending conversation queue items")

        logger.info("Processing %d queue items", len(queue_items))

        for item in queue_items:
            try:
                self._process_queue_item(item)
                self.metrics.queue_items_processed += 1
            except Exception as exc:
                logger.error(
                    "Failed to process queue item %s: %s", item.id, exc,
                    exc_info=True,
                )
                self.db.update_queue_status(
                    item.id, 'failed', error_log=str(exc)[:500]
                )
                self.metrics.conversations_failed += 1

        # Calculate execution time
        elapsed = int(time.time() - start_time)
        self.metrics.execution_time_seconds = elapsed

        logger.info(
            "Conversation generation complete: %d items processed, "
            "%d conversations generated, %d failed, %d exercises, %ds elapsed",
            self.metrics.queue_items_processed,
            self.metrics.conversations_generated,
            self.metrics.conversations_failed,
            self.metrics.exercises_generated,
            elapsed,
        )

        return self.metrics

    def _process_queue_item(self, item: ConvQueueItem) -> None:
        """Process a single conversation generation queue item."""
        logger.info("Processing queue item %s (scenario=%d, pair=%d, lang=%d)",
                     item.id, item.scenario_id, item.persona_pair_id, item.language_id)

        # Mark as in-progress
        self.db.update_queue_status(item.id, 'processing')

        # Load scenario and personas
        scenario = self.db.get_scenario(item.scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {item.scenario_id} not found")

        pair = self.db.get_persona_pair(item.persona_pair_id)
        if not pair:
            raise ValueError(f"Persona pair {item.persona_pair_id} not found")

        persona_a = self.db.get_persona(pair.persona_a_id)
        persona_b = self.db.get_persona(pair.persona_b_id)
        if not persona_a or not persona_b:
            raise ValueError(f"Personas not found for pair {pair.id}")

        # Get language model
        model = self.db.get_conversation_model(item.language_id)

        # Load prompt templates (per-language)
        conv_template = self._get_prompt('conversation_generation', item.language_id)
        analysis_template = self._get_prompt('conversation_analysis', item.language_id)

        # Generate the conversation
        batch_id = uuid4()

        if conv_gen_config.dry_run:
            logger.info("DRY RUN - skipping LLM call for queue item %s", item.id)
            self.db.update_queue_status(item.id, 'completed', conversations_generated=0)
            return

        if conv_gen_config.generation_mode == 'per_turn':
            turns = self.conversation_writer.generate_conversation_per_turn(
                scenario=scenario,
                persona_a=persona_a,
                persona_b=persona_b,
                language_id=item.language_id,
                model=model,
            )
        else:
            turns = self.conversation_writer.generate_conversation(
                prompt_template=conv_template,
                scenario=scenario,
                persona_a=persona_a,
                persona_b=persona_b,
                language_id=item.language_id,
                model=model,
            )

        if not turns:
            raise ValueError("Conversation generation returned empty turns")

        # Analyze the conversation
        corpus_features = self.conversation_analyzer.analyze(
            turns=turns,
            language_id=item.language_id,
            cefr_level=scenario.cefr_level or 'B1',
            prompt_template=analysis_template,
            model=model,
        )

        # Quality score from multi-dimensional checker
        language_config = self.db.get_language_config(item.language_id)
        language_code = language_config.get('language_code', 'en')
        qc_result = self.quality_checker.check(turns, item.language_id, language_code)
        quality_score = qc_result.score

        # Insert conversation record
        conversation_data = {
            'scenario_id': item.scenario_id,
            'persona_pair_id': item.persona_pair_id,
            'language_id': item.language_id,
            'model_used': model,
            'temperature': conv_gen_config.temperature,
            'turn_count': len(turns),
            'turns': turns,
            'corpus_features': {**corpus_features, 'qc_dimensions': qc_result.dimensions},
            'quality_score': quality_score,
            'passed_qc': qc_result.passed,
            'generation_batch_id': str(batch_id),
        }

        conversation_id = self.db.insert_conversation(conversation_data)
        self.metrics.conversations_generated += 1

        logger.info(
            "Inserted conversation %s (quality=%.2f, qc=%s)",
            conversation_id, quality_score,
            quality_score >= conv_gen_config.min_quality_score,
        )

        # Generate exercises if conversation passed QC
        if qc_result.passed:
            exercise_count = self._generate_exercises(
                conversation_id=conversation_id,
                turns=turns,
                language_id=item.language_id,
                cefr_level=scenario.cefr_level or 'B1',
                corpus_features=corpus_features,
            )
            self.metrics.exercises_generated += exercise_count

        # Update queue status
        self.db.update_queue_status(
            item.id, 'completed', conversations_generated=1,
        )

    def _generate_exercises(
        self,
        conversation_id: str,
        turns: list[dict],
        language_id: int,
        cefr_level: str,
        corpus_features: dict,
    ) -> int:
        """
        Generate exercises from a conversation using the existing
        exercise generation pipeline.

        Returns the number of exercises generated.
        """
        from services.exercise_generation.config import CONVERSATION_DISTRIBUTION
        from services.exercise_generation.validators import ExerciseValidator
        from services.exercise_generation.difficulty import DifficultyCalibrator

        # Build sentence pool from conversation turns
        sentence_pool = self.exercise_adapter.build_sentence_pool(
            conversation_id=conversation_id,
            turns=turns,
            language_id=language_id,
            cefr_level=cefr_level,
            corpus_features=corpus_features,
        )

        if not sentence_pool:
            logger.warning("Empty sentence pool for conversation %s", conversation_id)
            return 0

        # Use existing exercise generators via the exercise generation orchestrator
        from services.exercise_generation.orchestrator import ExerciseGenerationOrchestrator

        db_client = get_supabase_admin()
        exercise_orch = ExerciseGenerationOrchestrator(db=db_client)

        result = exercise_orch.run(
            source_type='conversation',
            source_id=conversation_id,
            language_id=language_id,
            sentence_pool=sentence_pool,
        )

        total = result.get('total', 0)
        logger.info("Generated %d exercises for conversation %s", total, conversation_id)
        return total

    def _compute_quality_score(self, turns: list[dict], features: dict) -> float:
        """Deprecated: use self.quality_checker.check() instead."""
        import warnings
        warnings.warn(
            "_compute_quality_score is deprecated, use ConversationQualityChecker",
            DeprecationWarning, stacklevel=2,
        )
        checker = getattr(self, 'quality_checker', None) or ConversationQualityChecker()
        result = checker.check(turns, language_id=2)
        return result.score

    def _get_prompt(self, task_name: str, language_id: int) -> str:
        """Get a prompt template for a language, with caching."""
        cache_key = f"{task_name}:{language_id}"
        if cache_key not in self._prompt_cache:
            self._prompt_cache[cache_key] = self.db.get_prompt_template(
                task_name, language_id,
            )
        return self._prompt_cache[cache_key]
