"""
Conversation Batch Processor

Domain-based batch generation that bypasses the queue system.
Iterates validated scenarios for a domain, finds compatible persona pairs,
generates conversations, quality-checks, and persists.
"""

import time
import logging
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional
from uuid import uuid4

from .config import conv_gen_config
from .database_client import (
    ConversationDatabaseClient,
    Scenario,
    PersonaPair,
)
from .agents import ConversationWriter, ConversationAnalyzer
from .quality_checker import ConversationQualityChecker
from .exercise_adapter import ConversationExerciseAdapter
from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


@dataclass
class BatchMetrics:
    """Metrics for a batch generation run."""
    domains_processed: int = 0
    scenarios_processed: int = 0
    conversations_generated: int = 0
    conversations_failed_qc: int = 0
    conversations_failed_error: int = 0
    exercises_generated: int = 0
    execution_time_seconds: int = 0


class ConversationBatchProcessor:
    """Domain-based batch conversation generation."""

    def __init__(self):
        self.db = ConversationDatabaseClient()
        self.writer = ConversationWriter()
        self.analyzer = ConversationAnalyzer()
        self.quality_checker = ConversationQualityChecker()
        self.exercise_adapter = ConversationExerciseAdapter()

        # Prompt cache
        self._prompt_cache: dict[str, str] = {}

    def run_all_domains(
        self,
        language_id: int,
        max_per_domain: int | None = None,
        max_workers: int | None = None,
        generate_exercises: bool = True,
        stop_check: Callable[[], bool] | None = None,
    ) -> BatchMetrics:
        """
        Generate conversations for all active domains for a language.

        Args:
            language_id: Language ID (1=Chinese, 2=English, 3=Japanese).
            max_per_domain: Max conversations per domain (default from config).
            max_workers: Parallel worker count (default from config).
            generate_exercises: Whether to generate exercises for passing conversations.

        Returns:
            BatchMetrics with run statistics.
        """
        max_per_domain = max_per_domain or conv_gen_config.max_conversations_per_domain
        max_workers = max_workers or conv_gen_config.max_parallel_workers

        start_time = time.time()
        metrics = BatchMetrics()

        domains = self.db.get_domains(active_only=True)
        if not domains:
            logger.info("No active domains found")
            return metrics

        logger.info(
            "Starting batch generation for %d domains, language_id=%d",
            len(domains), language_id,
        )

        for domain in domains:
            if stop_check and stop_check():
                logger.info("Stop requested — aborting remaining domains")
                break
            domain_metrics = self.run_domain(
                domain_id=domain.id,
                language_id=language_id,
                max_conversations=max_per_domain,
                max_workers=max_workers,
                generate_exercises=generate_exercises,
                stop_check=stop_check,
            )
            metrics.domains_processed += 1
            metrics.scenarios_processed += domain_metrics.scenarios_processed
            metrics.conversations_generated += domain_metrics.conversations_generated
            metrics.conversations_failed_qc += domain_metrics.conversations_failed_qc
            metrics.conversations_failed_error += domain_metrics.conversations_failed_error
            metrics.exercises_generated += domain_metrics.exercises_generated

        metrics.execution_time_seconds = int(time.time() - start_time)

        logger.info(
            "Batch complete: %d domains, %d conversations generated, "
            "%d failed QC, %d errors, %ds elapsed",
            metrics.domains_processed,
            metrics.conversations_generated,
            metrics.conversations_failed_qc,
            metrics.conversations_failed_error,
            metrics.execution_time_seconds,
        )
        return metrics

    def run_domain(
        self,
        domain_id: int,
        language_id: int,
        max_conversations: int | None = None,
        max_workers: int | None = None,
        generate_exercises: bool = True,
        stop_check: Callable[[], bool] | None = None,
    ) -> BatchMetrics:
        """
        Generate conversations for all validated scenarios in a domain.

        Args:
            domain_id: Domain ID from conversation_domains.
            language_id: Language ID.
            max_conversations: Max conversations for this domain.
            max_workers: Parallel worker count.
            generate_exercises: Whether to generate exercises for passing conversations.

        Returns:
            BatchMetrics for this domain.
        """
        max_conversations = max_conversations or conv_gen_config.max_conversations_per_domain
        max_workers = max_workers or conv_gen_config.max_parallel_workers
        metrics = BatchMetrics()

        scenarios = self.db.get_validated_scenarios_for_domain(domain_id, language_id)
        if not scenarios:
            domain = self.db.get_domain(domain_id)
            domain_name = domain.domain_name if domain else f"ID {domain_id}"
            logger.info(
                "No validated scenarios for domain '%s', language_id=%d. Skipping.",
                domain_name, language_id,
            )
            return metrics

        domain = self.db.get_domain(domain_id)
        domain_name = domain.domain_name if domain else f"ID {domain_id}"
        logger.info(
            "=== Domain: %s | language_id=%d | %d validated scenarios ===",
            domain_name, language_id, len(scenarios),
        )

        # Bulk-fetch existing (scenario_id, persona_pair_id) in one query
        existing_keys: set[tuple[int, int]] = set()
        if conv_gen_config.skip_existing_pairs:
            scenario_ids = [s.id for s in scenarios]
            existing_keys = self.db.get_existing_conversation_keys(scenario_ids)

        # Build list of (scenario, pair) tasks
        tasks = []
        for scenario in scenarios:
            pairs = self.db.get_pairs_for_scenario(
                scenario=scenario,
                language_id=language_id,
                limit=4,
            )
            for pair in pairs:
                if len(tasks) >= max_conversations:
                    break

                # Skip existing scenario+pair combinations (already fetched in bulk)
                if conv_gen_config.skip_existing_pairs:
                    if (scenario.id, pair.id) in existing_keys:
                        continue

                tasks.append((scenario, pair))

            if len(tasks) >= max_conversations:
                break

        if not tasks:
            logger.info("  No new conversations to generate (all pairs exist)")
            return metrics

        metrics.scenarios_processed = len(set(s.id for s, _ in tasks))
        logger.info("  Conversations to generate: %d", len(tasks))

        if conv_gen_config.dry_run:
            logger.info("  DRY RUN - skipping LLM calls")
            return metrics

        # Generate conversations (sequential or parallel)
        if max_workers <= 1:
            for scenario, pair in tasks:
                if stop_check and stop_check():
                    logger.info("Stop requested — aborting remaining conversations")
                    break
                result = self._generate_one(scenario, pair, language_id, generate_exercises)
                self._update_metrics(metrics, result)
        else:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                futures = {
                    executor.submit(
                        self._generate_one, scenario, pair, language_id, generate_exercises
                    ): (scenario, pair)
                    for scenario, pair in tasks
                }
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    self._update_metrics(metrics, result)

        logger.info(
            "  Domain '%s' complete: %d generated, %d failed QC, %d errors",
            domain_name,
            metrics.conversations_generated,
            metrics.conversations_failed_qc,
            metrics.conversations_failed_error,
        )
        return metrics

    def _generate_one(
        self,
        scenario: Scenario,
        pair: PersonaPair,
        language_id: int,
        generate_exercises: bool = True,
    ) -> dict:
        """
        Generate a single conversation for a scenario + persona pair.

        Returns:
            dict with 'status' ('generated', 'failed_qc', 'error'),
            and optionally 'conversation_id', 'exercises'.
        """
        try:
            persona_a = self.db.get_persona(pair.persona_a_id)
            persona_b = self.db.get_persona(pair.persona_b_id)
            if not persona_a or not persona_b:
                raise ValueError(f"Personas not found for pair {pair.id}")

            # Generate conversation
            if conv_gen_config.generation_mode == 'per_turn':
                turns = self.writer.generate_conversation_per_turn(
                    scenario=scenario,
                    persona_a=persona_a,
                    persona_b=persona_b,
                    language_id=language_id,
                )
            else:
                conv_template = self._get_prompt(
                    'conversation_generation', language_id,
                )
                turns = self.writer.generate_conversation(
                    prompt_template=conv_template,
                    scenario=scenario,
                    persona_a=persona_a,
                    persona_b=persona_b,
                    language_id=language_id,
                )

            if not turns:
                raise ValueError("Empty turns returned")

            # Analyze
            analysis_template = self._get_prompt(
                'conversation_analysis', language_id,
            )
            corpus_features = self.analyzer.analyze(
                turns=turns,
                language_id=language_id,
                complexity_tier=scenario.complexity_tier or 'T3',
                prompt_template=analysis_template,
            )

            # Quality check
            language_config = self.db.get_language_config(language_id)
            language_code = language_config.get('language_code', 'en')
            qc_result = self.quality_checker.check(turns, language_id, language_code)

            model = self.db.get_conversation_model(language_id)
            batch_id = str(uuid4())

            # Insert conversation regardless of QC
            conversation_data = {
                'scenario_id': scenario.id,
                'persona_pair_id': pair.id,
                'language_id': language_id,
                'model_used': model,
                'temperature': conv_gen_config.temperature,
                'turn_count': len(turns),
                'turns': turns,
                'corpus_features': {
                    **corpus_features,
                    'qc_dimensions': qc_result.dimensions,
                },
                'quality_score': qc_result.score,
                'passed_qc': qc_result.passed,
                'generation_batch_id': batch_id,
            }

            conversation_id = self.db.insert_conversation(conversation_data)

            status_marker = 'PASS' if qc_result.passed else 'FAIL'
            logger.info(
                "  [%s] %s x %s | score=%.3f",
                status_marker, persona_a.name, persona_b.name, qc_result.score,
            )

            if not qc_result.passed:
                return {'status': 'failed_qc'}

            # Generate exercises for passing conversations (if enabled)
            if not generate_exercises:
                return {
                    'status': 'generated',
                    'conversation_id': conversation_id,
                    'exercises': 0,
                }

            exercise_count = self._generate_exercises(
                conversation_id=conversation_id,
                turns=turns,
                language_id=language_id,
                complexity_tier=scenario.complexity_tier or 'T3',
                corpus_features=corpus_features,
            )

            return {
                'status': 'generated',
                'conversation_id': conversation_id,
                'exercises': exercise_count,
            }

        except Exception as exc:
            logger.error("  [ERROR] Generation failed: %s", exc, exc_info=True)
            return {'status': 'error', 'error': str(exc)}

    def _generate_exercises(
        self,
        conversation_id: str,
        turns: list[dict],
        language_id: int,
        complexity_tier: str,
        corpus_features: dict,
    ) -> int:
        """Generate exercises from a conversation. Returns exercise count."""
        sentence_pool = self.exercise_adapter.build_sentence_pool(
            conversation_id=conversation_id,
            turns=turns,
            language_id=language_id,
            complexity_tier=complexity_tier,
            corpus_features=corpus_features,
        )

        if not sentence_pool:
            logger.warning(
                "Empty sentence pool for conversation %s", conversation_id,
            )
            return 0

        from services.exercise_generation.orchestrator import (
            ExerciseGenerationOrchestrator,
        )

        db_client = get_supabase_admin()
        exercise_orch = ExerciseGenerationOrchestrator(db=db_client)

        result = exercise_orch.run(
            source_type='conversation',
            source_id=conversation_id,
            language_id=language_id,
            sentence_pool=sentence_pool,
        )

        total = result.get('total', 0)
        logger.info(
            "  Generated %d exercises for conversation %s", total, conversation_id,
        )
        return total

    def _get_prompt(self, task_name: str, language_id: int) -> str:
        """Get a prompt template with caching."""
        cache_key = f"{task_name}:{language_id}"
        if cache_key not in self._prompt_cache:
            self._prompt_cache[cache_key] = self.db.get_prompt_template(
                task_name, language_id,
            )
        return self._prompt_cache[cache_key]

    @staticmethod
    def _update_metrics(metrics: BatchMetrics, result: dict) -> None:
        """Update metrics based on a single generation result."""
        status = result.get('status', 'error')
        if status == 'generated':
            metrics.conversations_generated += 1
            metrics.exercises_generated += result.get('exercises', 0)
        elif status == 'failed_qc':
            metrics.conversations_failed_qc += 1
        else:
            metrics.conversations_failed_error += 1
