"""
Topic Generation Orchestrator

Coordinates the daily topic generation workflow:
1. Select next category for rotation
2. Generate topic candidates via Explorer
3. Check novelty via Archivist
4. Validate cultural fit via Gatekeeper
5. Queue approved topics for content generation
"""

import time
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from uuid import UUID

from .config import topic_gen_config
from .database_client import (
    TopicDatabaseClient,
    GenerationMetrics,
    TopicCandidate,
    Category,
    Language,
    Lens
)
from .agents import (
    EmbeddingService,
    ExplorerAgent,
    ArchivistAgent,
    GatekeeperAgent
)

logger = logging.getLogger(__name__)


class NoEligibleCategoryError(Exception):
    """Raised when no categories are available for generation."""
    pass


class TopicGenerationOrchestrator:
    """Coordinates daily topic generation workflow."""

    def __init__(self):
        """Initialize the orchestrator and all agents."""
        # Validate configuration
        if not topic_gen_config.validate():
            raise ValueError("Invalid topic generation configuration")

        # Initialize database client
        self.db = TopicDatabaseClient()

        # Initialize agents
        self.embedder = EmbeddingService()
        self.explorer = ExplorerAgent()
        self.archivist = ArchivistAgent(self.db, self.embedder)
        self.gatekeeper = GatekeeperAgent()

        # Metrics tracking
        self.metrics: Optional[GenerationMetrics] = None

        logger.info("TopicGenerationOrchestrator initialized")

    def run(self) -> GenerationMetrics:
        """
        Execute daily topic generation workflow.

        Returns:
            GenerationMetrics: Execution statistics

        Workflow:
            1. Load dimension tables (languages, lenses)
            2. Select next category
            3. Fetch prompt templates
            4. Explorer generates candidates
            5. For each candidate (max quota):
                a. Check novelty (Archivist)
                b. If novel: save topic, run Gatekeeper for each language
                c. Queue approved language pairs
            6. Update category usage
            7. Log metrics
        """
        start_time = time.time()

        try:
            logger.info("=" * 60)
            logger.info("Starting Topic Generation Run")
            logger.info("=" * 60)

            # Step 1: Load dimension data
            languages = self.db.get_active_languages()
            lenses = self.db.get_active_lenses()
            lens_map = {lens.lens_code.lower(): lens for lens in lenses}

            if not languages:
                raise ValueError("No active languages configured")
            if not lenses:
                raise ValueError("No active lenses configured")

            logger.info(f"Loaded {len(languages)} languages, {len(lenses)} lenses")

            # Step 2: Select next category
            category = self.db.get_next_category()
            if not category:
                raise NoEligibleCategoryError("No eligible categories available")

            # Initialize metrics
            self.metrics = GenerationMetrics(
                run_date=datetime.utcnow(),
                category_id=category.id,
                category_name=category.name
            )

            logger.info(f"Selected category: {category.name}")

            # Step 3: Fetch prompts
            explorer_prompt = self.db.get_prompt_template('explorer_ideation')
            gatekeeper_prompt = self.db.get_prompt_template('gatekeeper_check')

            if not explorer_prompt:
                raise ValueError("Explorer prompt template not found")
            if not gatekeeper_prompt:
                raise ValueError("Gatekeeper prompt template not found")

            # Step 4: Generate candidates
            candidates = self.explorer.generate_candidates(
                category_name=category.name,
                active_lenses=lenses,
                prompt_template=explorer_prompt,
                num_candidates=topic_gen_config.max_candidates_per_run
            )

            self.metrics.candidates_proposed = len(candidates)
            self.metrics.api_calls_llm = self.explorer.api_call_count

            if not candidates:
                logger.warning("Explorer returned no candidates")
                return self._finalize(start_time, category)

            logger.info(f"Explorer generated {len(candidates)} candidates")

            # Step 5: Process candidates
            approved_count = 0
            queue_items: List[Tuple[UUID, int]] = []

            for candidate in candidates:
                if approved_count >= topic_gen_config.daily_topic_quota:
                    logger.info(f"Reached daily quota of {topic_gen_config.daily_topic_quota}")
                    break

                # Validate lens exists
                lens = lens_map.get(candidate.lens_code.lower())
                if not lens:
                    logger.warning(f"Unknown lens code: {candidate.lens_code}")
                    continue

                # Check novelty
                signature = self.archivist.construct_semantic_signature(
                    category.name,
                    candidate.concept,
                    lens,
                    candidate.keywords
                )

                is_novel, rejection_reason, embedding = self.archivist.check_novelty(
                    category.id,
                    signature,
                    topic_gen_config.similarity_threshold
                )

                if not is_novel:
                    self.metrics.topics_rejected_similarity += 1
                    logger.debug(f"Rejected (similarity): {candidate.concept[:40]}...")
                    continue

                # Topic is novel - save it (even if dry run, for testing)
                if topic_gen_config.dry_run:
                    logger.info(f"[DRY RUN] Would save topic: {candidate.concept[:50]}...")
                    topic_id = UUID('00000000-0000-0000-0000-000000000000')
                else:
                    topic_id = self.db.insert_topic(
                        category_id=category.id,
                        concept=candidate.concept,
                        lens_id=lens.id,
                        keywords=candidate.keywords,
                        embedding=embedding,
                        semantic_signature=signature
                    )

                # Gatekeeper validation for each language
                approved_languages = self._run_gatekeeper(
                    candidate,
                    languages,
                    gatekeeper_prompt
                )

                if approved_languages:
                    for lang in approved_languages:
                        queue_items.append((topic_id, lang.id))
                    approved_count += 1
                    logger.info(
                        f"Topic approved for {len(approved_languages)} languages: "
                        f"{candidate.concept[:40]}..."
                    )
                else:
                    logger.info(f"Topic rejected by all gatekeepers: {candidate.concept[:40]}...")

            # Step 6: Batch queue insertion
            if queue_items and not topic_gen_config.dry_run:
                self.db.batch_insert_queue(queue_items)
            elif queue_items:
                logger.info(f"[DRY RUN] Would queue {len(queue_items)} items")

            self.metrics.topics_generated = approved_count

            # Step 7: Update category
            if not topic_gen_config.dry_run:
                self.db.update_category_usage(category.id)
                if approved_count > 0:
                    self.db.increment_category_topics(category.id, approved_count)

            return self._finalize(start_time, category)

        except Exception as e:
            logger.exception(f"Generation run failed: {e}")
            if self.metrics:
                self.metrics.error_message = str(e)
            return self._finalize(start_time, None)

    def _run_gatekeeper(
        self,
        candidate: TopicCandidate,
        languages: List[Language],
        prompt_template: str
    ) -> List[Language]:
        """
        Validate topic across all languages with short-circuit.

        Args:
            candidate: Topic to validate
            languages: All active languages
            prompt_template: Gatekeeper prompt

        Returns:
            List of approved Language objects
        """
        approved = self.gatekeeper.validate_for_all_languages(
            candidate=candidate,
            languages=languages,
            prompt_template=prompt_template
        )

        # Track rejections in metrics
        total_checked = min(
            len(languages),
            len(approved) + topic_gen_config.gatekeeper_short_circuit_threshold
        )
        rejections = total_checked - len(approved)
        self.metrics.topics_rejected_gatekeeper += rejections

        return approved

    def _finalize(
        self,
        start_time: float,
        category: Optional[Category]
    ) -> GenerationMetrics:
        """
        Calculate final metrics and persist to database.

        Args:
            start_time: Workflow start timestamp
            category: Category that was processed (or None on early failure)

        Returns:
            GenerationMetrics: Complete execution statistics
        """
        if self.metrics is None:
            self.metrics = GenerationMetrics(
                run_date=datetime.utcnow(),
                category_id=0,
                category_name="Unknown"
            )

        self.metrics.execution_time_seconds = int(time.time() - start_time)

        # Calculate API costs
        self.metrics.api_calls_llm = (
            self.explorer.api_call_count +
            self.gatekeeper.api_call_count
        )
        self.metrics.api_calls_embedding = self.embedder.api_call_count

        # Cost estimation (rough)
        # Gemini Flash: ~$0.10/1M input, ~$0.40/1M output
        # Embeddings: ~$0.02/1M tokens
        llm_cost = self.metrics.api_calls_llm * 0.001  # ~$0.001 per call
        embed_cost = self.metrics.api_calls_embedding * 0.0001
        self.metrics.total_cost_usd = llm_cost + embed_cost

        # Persist metrics (unless dry run)
        if not topic_gen_config.dry_run:
            try:
                self.db.insert_generation_run(self.metrics)
            except Exception as e:
                logger.error(f"Failed to save metrics: {e}")
        else:
            logger.info("[DRY RUN] Metrics not saved to database")

        # Log summary
        logger.info("=" * 60)
        logger.info("Generation Run Complete")
        logger.info("=" * 60)
        logger.info(f"  Category: {self.metrics.category_name}")
        logger.info(f"  Topics Generated: {self.metrics.topics_generated}")
        logger.info(f"  Rejected (Similarity): {self.metrics.topics_rejected_similarity}")
        logger.info(f"  Rejected (Gatekeeper): {self.metrics.topics_rejected_gatekeeper}")
        logger.info(f"  Candidates Proposed: {self.metrics.candidates_proposed}")
        logger.info(f"  Duration: {self.metrics.execution_time_seconds}s")
        logger.info(f"  Est. Cost: ${self.metrics.total_cost_usd:.4f}")
        if self.metrics.error_message:
            logger.error(f"  Error: {self.metrics.error_message}")
        logger.info("=" * 60)

        return self.metrics
