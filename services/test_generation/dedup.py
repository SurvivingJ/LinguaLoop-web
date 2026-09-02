"""
TASK-740 Phase 5 — question/passage-level dedup (finding #3, 2026-08-29 review).

Generation-time half of the dedup decision (Q5: both generation-time AND
per-user recency; the per-user recency half lives on the session-builder
side and is a separate, gated change — see wiki/decisions).

Two checks, run in order, scoped to (topic_id, target_age_tier):
  1. Exact duplicate — SHA-256 of the normalized passage text matches an
     existing test's passage_hash at the same topic+tier. Cheap, exact,
     backed by a UNIQUE index (migrations/task740_phase5_question_passage_dedup.sql)
     as a hard backstop behind this application-level check.
  2. Near duplicate — cosine similarity of the passage embedding against
     other passages at the same topic+tier exceeds
     config.passage_dedup_similarity_threshold. Catches a reworded repeat
     that doesn't hash-collide (different opening sentence, synonym swap,
     reordered clauses) but reads as the same passage.

Both checks are scoped to (topic_id, target_age_tier) — a passage about the
same topic at a different tier is *supposed* to differ in complexity, so it
is deliberately never compared across tiers.
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from .config import get_test_gen_config

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r'\s+')


def normalize_passage(text: str) -> str:
    """Normalize passage text for hashing.

    Collapses all whitespace runs to a single space, strips leading/trailing
    whitespace, and casefolds. This is deliberately loose: the goal is to
    treat "the same passage with different formatting or capitalization" as
    the same passage, while any actual wording change still produces a
    different hash (that's what the embedding-based near-dup check is for).
    Casefolding is a no-op for CJK text (ja/zh have no case), so this
    normalization is safe to apply uniformly across languages.
    """
    return _WHITESPACE_RE.sub(' ', text.strip()).casefold()


def compute_passage_hash(text: str) -> str:
    """SHA-256 hex digest of the normalized passage text."""
    normalized = normalize_passage(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


@dataclass
class DedupResult:
    is_duplicate: bool
    reason: Optional[str] = None  # 'exact' | 'near' | None
    similarity: Optional[float] = None
    matched_test_id: Optional[str] = None


class PassageDedupChecker:
    """Checks a candidate passage against existing tests at the same
    (topic_id, target_age_tier) for exact or near duplication.

    `db` is the test_generation TestGenDatabaseClient (or anything exposing
    the same `.client` supabase handle) — reused rather than opening a
    second connection.
    """

    def __init__(self, db, embedding_service=None):
        self.db = db
        self._embedding_service = embedding_service

    @property
    def embedding_service(self):
        # Lazy + optional: importing services.topic_generation pulls in its
        # config (which requires OPENAI_API_KEY at construction) — only pay
        # that cost if a near-dup check is actually going to run, and let a
        # missing key degrade to "near-dup check skipped" rather than
        # blocking generation outright (see check_duplicate).
        if self._embedding_service is None:
            from services.topic_generation.agents.embedder import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def check_exact_duplicate(
        self, topic_id: UUID, tier_id: int, passage_hash: str
    ) -> DedupResult:
        response = (
            self.db.client.table('tests')
            .select('id')
            .eq('topic_id', str(topic_id))
            .eq('target_age_tier', tier_id)
            .eq('passage_hash', passage_hash)
            .limit(1)
            .execute()
        )
        if response.data:
            return DedupResult(
                is_duplicate=True,
                reason='exact',
                matched_test_id=response.data[0]['id'],
            )
        return DedupResult(is_duplicate=False)

    def check_near_duplicate(
        self, topic_id: UUID, tier_id: int, embedding: list
    ) -> DedupResult:
        cfg = get_test_gen_config()
        response = self.db.client.rpc(
            'match_test_passages_by_topic_tier',
            {
                'p_topic_id': str(topic_id),
                'p_tier_id': tier_id,
                'query_embedding': embedding,
                'match_threshold': cfg.passage_dedup_similarity_threshold,
                'match_count': 1,
            },
        ).execute()
        if response.data:
            match = response.data[0]
            return DedupResult(
                is_duplicate=True,
                reason='near',
                similarity=match.get('similarity'),
                matched_test_id=match.get('id'),
            )
        return DedupResult(is_duplicate=False)

    def check_duplicate(
        self, topic_id: UUID, tier_id: int, passage: str
    ) -> tuple[DedupResult, str, Optional[list]]:
        """Run both checks. Returns (result, passage_hash, embedding).

        embedding is None if the near-dup check couldn't run (e.g. no
        OPENAI_API_KEY configured) — a passage-level failure here is a
        degraded dedup pass, not a reason to fail the whole test, so it
        just logs and falls through to "not a duplicate" for that half.
        """
        passage_hash = compute_passage_hash(passage)

        exact = self.check_exact_duplicate(topic_id, tier_id, passage_hash)
        if exact.is_duplicate:
            return exact, passage_hash, None

        embedding: Optional[list] = None
        try:
            embedding = self.embedding_service.embed_single(passage)
        except Exception as exc:
            logger.warning(
                f"Near-dup embedding failed for topic {topic_id} tier "
                f"{tier_id}, skipping near-dup check for this passage: {exc}"
            )
            return DedupResult(is_duplicate=False), passage_hash, None

        near = self.check_near_duplicate(topic_id, tier_id, embedding)
        return near, passage_hash, embedding


# Appended to the prose prompt on the one allowed retry after a duplicate is
# detected — a plain-text nudge rather than a template placeholder, since
# prompt_templates rows are shared across every generation and shouldn't
# carry dedup-retry language for the common (no-collision) case.
DEDUP_RETRY_NUDGE = (
    "\n\nIMPORTANT: A previous attempt at this topic and level produced a "
    "passage too similar to one already used. Write a distinctly different "
    "passage this time — a different scenario, angle, or set of concrete "
    "details — while still matching the topic and difficulty level above."
)
