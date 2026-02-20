"""
Topic Import Orchestrator

Coordinates the JSON-based topic import workflow:
1. Parse and validate JSON file
2. Create/lookup category
3. For each topic entry:
   a. Convert to TopicCandidate
   b. Check novelty via Archivist (optional)
   c. Insert to topics table
   d. Validate via Gatekeeper for each language (optional)
   e. Queue approved language pairs
"""

import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID

from .config import topic_gen_config
from .json_importer import JSONTopicImporter, JSONTopicEntry
from .database_client import (
    TopicDatabaseClient,
    TopicCandidate,
    Category,
    Language,
    Lens
)
from .agents import (
    EmbeddingService,
    ArchivistAgent,
    GatekeeperAgent
)

logger = logging.getLogger(__name__)


@dataclass
class ImportMetrics:
    """Metrics for topic import runs."""
    total_entries: int = 0
    topics_imported: int = 0
    topics_rejected_similarity: int = 0
    topics_rejected_gatekeeper: int = 0
    topics_skipped_invalid_language: int = 0
    queue_entries_created: int = 0
    api_calls_embedding: int = 0
    api_calls_llm: int = 0
    execution_time_seconds: int = 0
    error_message: Optional[str] = None


class TopicImportOrchestrator:
    """Orchestrates JSON topic import into the topic generation system."""

    def __init__(
        self,
        json_file_path: str,
        category_name: Optional[str] = None,
        default_lens_code: str = 'cultural',
        skip_gatekeeper: bool = False,
        skip_novelty: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize the import orchestrator.

        Args:
            json_file_path: Path to JSON file containing topics
            category_name: Category name (defaults to "Import: {filename}")
            default_lens_code: Default lens for entries without one
            skip_gatekeeper: Skip cultural validation
            skip_novelty: Skip duplicate checking
            dry_run: Validate without database changes
        """
        self.json_file_path = json_file_path
        self.default_lens_code = default_lens_code
        self.skip_gatekeeper = skip_gatekeeper
        self.skip_novelty = skip_novelty
        self.dry_run = dry_run

        # Default category name from filename
        if category_name:
            self.category_name = category_name
        else:
            filename = Path(json_file_path).stem
            self.category_name = f"Import: {filename}"

        # Initialize components
        self.importer = JSONTopicImporter(default_lens_code=default_lens_code)
        self.db = TopicDatabaseClient()
        self.embedder = EmbeddingService()
        self.archivist = ArchivistAgent(self.db, self.embedder)
        self.gatekeeper = GatekeeperAgent() if not skip_gatekeeper else None

        # Load dimension data
        self._lenses: dict = {}
        self._load_lenses()

        self.metrics = ImportMetrics()

    def _load_lenses(self) -> None:
        """Load lens lookup table."""
        lenses = self.db.get_active_lenses()
        self._lenses = {lens.lens_code.lower(): lens for lens in lenses}
        logger.info(f"Loaded {len(self._lenses)} lenses")

    def _get_lens(self, lens_code: str) -> Optional[Lens]:
        """Get lens by code, falling back to default."""
        lens = self._lenses.get(lens_code.lower())
        if not lens:
            lens = self._lenses.get(self.default_lens_code.lower())
        return lens

    def run(self) -> ImportMetrics:
        """
        Execute the import workflow.

        Returns:
            ImportMetrics: Execution statistics
        """
        start_time = time.time()

        try:
            logger.info("=" * 60)
            logger.info("Starting Topic Import")
            logger.info(f"  File: {self.json_file_path}")
            logger.info(f"  Category: {self.category_name}")
            logger.info(f"  Dry Run: {self.dry_run}")
            logger.info(f"  Skip Novelty: {self.skip_novelty}")
            logger.info(f"  Skip Gatekeeper: {self.skip_gatekeeper}")
            logger.info("=" * 60)

            # Step 1: Parse JSON
            entries = self.importer.parse_json(self.json_file_path)
            self.metrics.total_entries = len(entries)
            logger.info(f"Parsed {len(entries)} entries from JSON")

            # Step 2: Validate and cache language codes
            all_language_codes = set()
            for entry in entries:
                all_language_codes.update(entry.languages)

            language_map = self.db.get_languages_by_codes(list(all_language_codes))
            invalid_codes = all_language_codes - set(language_map.keys())
            if invalid_codes:
                logger.warning(f"Unknown language codes will be skipped: {invalid_codes}")

            # Step 3: Get or create category
            category = self._get_or_create_category()

            # Step 4: Load gatekeeper prompt if needed
            gatekeeper_prompt = None
            if self.gatekeeper:
                gatekeeper_prompt = self.db.get_prompt_template('gatekeeper_check')
                if not gatekeeper_prompt:
                    logger.warning("Gatekeeper prompt not found, disabling gatekeeper")
                    self.gatekeeper = None

            # Step 5: Process each entry
            queue_items: List[Tuple[UUID, int]] = []

            for i, entry in enumerate(entries):
                logger.info(f"Processing entry {i+1}/{len(entries)}: {entry.topic[:50]}...")

                result = self._process_entry(
                    entry=entry,
                    category=category,
                    language_map=language_map,
                    gatekeeper_prompt=gatekeeper_prompt
                )

                if result:
                    topic_id, approved_language_ids = result
                    for lang_id in approved_language_ids:
                        queue_items.append((topic_id, lang_id))

            # Step 6: Batch queue insertion
            if queue_items and not self.dry_run:
                count = self.db.batch_insert_queue(queue_items)
                self.metrics.queue_entries_created = count
            elif queue_items:
                self.metrics.queue_entries_created = len(queue_items)
                logger.info(f"[DRY RUN] Would queue {len(queue_items)} items")

            # Step 7: Update category metrics
            if not self.dry_run and self.metrics.topics_imported > 0:
                self.db.increment_category_topics(
                    category.id,
                    self.metrics.topics_imported
                )

            return self._finalize(start_time)

        except Exception as e:
            logger.exception(f"Import failed: {e}")
            self.metrics.error_message = str(e)
            return self._finalize(start_time)

    def _get_or_create_category(self) -> Category:
        """Get existing category or create new one."""
        existing = self.db.get_category_by_name(self.category_name)
        if existing:
            logger.info(f"Using existing category: {self.category_name} (id={existing.id})")
            return existing

        if self.dry_run:
            logger.info(f"[DRY RUN] Would create category: {self.category_name}")
            return Category(
                id=0,
                name=self.category_name,
                status_id=1,
                target_language_id=None,
                last_used_at=None,
                cooldown_days=0
            )

        return self.db.create_category(self.category_name)

    def _process_entry(
        self,
        entry: JSONTopicEntry,
        category: Category,
        language_map: dict,
        gatekeeper_prompt: Optional[str]
    ) -> Optional[Tuple[UUID, List[int]]]:
        """
        Process a single topic entry.

        Returns:
            Tuple of (topic_id, approved_language_ids) or None if rejected
        """
        # Convert to TopicCandidate
        candidate = self.importer.entry_to_candidate(entry)

        # Get lens
        lens = self._get_lens(candidate.lens_code)
        if not lens:
            logger.warning(f"No valid lens for entry, skipping: {entry.topic[:40]}...")
            return None

        # Resolve entry's languages
        entry_languages: List[Language] = []
        for code in entry.languages:
            lang = language_map.get(code.lower())
            if lang:
                entry_languages.append(lang)
            else:
                self.metrics.topics_skipped_invalid_language += 1

        if not entry_languages:
            logger.warning(f"No valid languages for entry, skipping: {entry.topic[:40]}...")
            return None

        # Novelty check
        embedding = []
        if not self.skip_novelty:
            signature = self.archivist.construct_semantic_signature(
                category_name=category.name,
                concept=candidate.concept,
                lens=lens,
                keywords=candidate.keywords
            )

            is_novel, rejection_reason, embedding = self.archivist.check_novelty(
                category_id=category.id,
                semantic_signature=signature,
                threshold=topic_gen_config.similarity_threshold
            )

            if not is_novel:
                self.metrics.topics_rejected_similarity += 1
                logger.info(f"Rejected (similarity): {entry.topic[:40]}...")
                return None
        else:
            # Still need embedding for topic storage
            signature = self.archivist.construct_semantic_signature(
                category_name=category.name,
                concept=candidate.concept,
                lens=lens,
                keywords=candidate.keywords
            )
            embedding = self.embedder.embed_single(signature)

        # Insert topic
        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert topic: {entry.topic[:50]}...")
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

        self.metrics.topics_imported += 1

        # Gatekeeper validation
        if self.gatekeeper and gatekeeper_prompt:
            approved_languages = self.gatekeeper.validate_for_all_languages(
                candidate=candidate,
                languages=entry_languages,
                prompt_template=gatekeeper_prompt
            )

            rejections = len(entry_languages) - len(approved_languages)
            self.metrics.topics_rejected_gatekeeper += rejections

            if not approved_languages:
                logger.info(f"No languages approved by gatekeeper: {entry.topic[:40]}...")
                return (topic_id, [])

            approved_ids = [lang.id for lang in approved_languages]
            logger.info(
                f"Gatekeeper approved {len(approved_languages)}/{len(entry_languages)} "
                f"languages for: {entry.topic[:40]}..."
            )
            return (topic_id, approved_ids)
        else:
            # Skip gatekeeper - queue all entry languages
            approved_ids = [lang.id for lang in entry_languages]
            return (topic_id, approved_ids)

    def _finalize(self, start_time: float) -> ImportMetrics:
        """Calculate final metrics and log summary."""
        self.metrics.execution_time_seconds = int(time.time() - start_time)
        self.metrics.api_calls_embedding = self.embedder.api_call_count

        if self.gatekeeper:
            self.metrics.api_calls_llm = self.gatekeeper.api_call_count

        logger.info("=" * 60)
        logger.info("Import Complete")
        logger.info("=" * 60)
        logger.info(f"  Total Entries: {self.metrics.total_entries}")
        logger.info(f"  Topics Imported: {self.metrics.topics_imported}")
        logger.info(f"  Rejected (Similarity): {self.metrics.topics_rejected_similarity}")
        logger.info(f"  Rejected (Gatekeeper): {self.metrics.topics_rejected_gatekeeper}")
        logger.info(f"  Queue Entries: {self.metrics.queue_entries_created}")
        logger.info(f"  Duration: {self.metrics.execution_time_seconds}s")
        if self.metrics.error_message:
            logger.error(f"  Error: {self.metrics.error_message}")
        logger.info("=" * 60)

        return self.metrics
