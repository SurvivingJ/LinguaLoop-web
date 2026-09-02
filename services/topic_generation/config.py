"""
Topic Generation Configuration

Extends main Config with topic generation specific settings.
All settings can be overridden via environment variables.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Default novelty thresholds per ADR-003 age tier. Stricter where the concept
# space is small, looser where it is wide. See the field comment on
# TopicGenConfig.similarity_threshold_by_tier for the measurement behind these.
DEFAULT_TIER_SIMILARITY_THRESHOLDS: dict = {
    1: 0.82,
    2: 0.84,
    3: 0.86,
    4: 0.87,
    5: 0.89,
    6: 0.90,
}


def _parse_tier_thresholds(raw: str) -> dict:
    """Parse ``'1:0.80,6:0.92'`` into ``{1: 0.80, 6: 0.92}``.

    An empty or unparseable value yields the defaults rather than an empty map:
    silently disabling tier scaling because someone fat-fingered an env var is
    the failure mode this whole task exists to remove.
    """
    if not raw.strip():
        return dict(DEFAULT_TIER_SIMILARITY_THRESHOLDS)
    parsed = dict(DEFAULT_TIER_SIMILARITY_THRESHOLDS)
    for pair in raw.split(','):
        if not pair.strip():
            continue
        tier, _, value = pair.partition(':')
        try:
            parsed[int(tier.strip())] = float(value.strip())
        except ValueError:
            logger.warning(
                'TOPIC_SIMILARITY_THRESHOLDS_BY_TIER: ignoring unparseable '
                'entry %r; keeping the default for that tier', pair,
            )
    return parsed


@dataclass
class TopicGenConfig:
    """Configuration for topic generation system."""

    # Generation parameters
    daily_topic_quota: int = field(
        default_factory=lambda: int(os.getenv('TOPIC_DAILY_QUOTA', '5'))
    )
    similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv('TOPIC_SIMILARITY_THRESHOLD', '0.85'))
    )
    # TASK-742 (plan §3, T3.2) — the novelty threshold scales with tier.
    #
    # A single global threshold under-rejects at low tiers. The legitimate
    # concept space for a five-year-old is small and its vocabulary is
    # constrained, so three genuinely near-identical T1 topics ("a child
    # building a block tower" / "...a toy castle with blocks" / "...with
    # colorful blocks") all sit below 0.85 and were all accepted, while only
    # one topic pair in the whole corpus exceeded 0.90. At T6 the space is
    # wide enough that two topics scoring 0.88 really are different articles,
    # and rejecting them costs coverage the corpus cannot spare.
    #
    # Set TOPIC_SIMILARITY_THRESHOLDS_BY_TIER to a comma-separated
    # tier:threshold list to override; an unlisted tier (or an untiered
    # candidate) falls back to `similarity_threshold`.
    similarity_threshold_by_tier: dict = field(
        default_factory=lambda: _parse_tier_thresholds(
            os.getenv('TOPIC_SIMILARITY_THRESHOLDS_BY_TIER', '')
        )
    )
    max_candidates_per_run: int = field(
        default_factory=lambda: int(os.getenv('TOPIC_MAX_CANDIDATES', '10'))
    )

    # Per-tier ideation (ADR-003 age tiers). The Explorer runs once per tier so
    # a run yields a spread across levels and each tier gets its own prompt
    # (concrete for low tiers -> abstract/jargon for high tiers).
    tiers_to_generate: list = field(
        default_factory=lambda: [
            int(t) for t in os.getenv('TOPIC_TIERS', '1,2,3,4,5,6').split(',') if t.strip()
        ]
    )
    candidates_per_tier: int = field(
        default_factory=lambda: int(os.getenv('TOPIC_CANDIDATES_PER_TIER', '6'))
    )
    topics_per_tier: int = field(
        default_factory=lambda: int(os.getenv('TOPIC_TOPICS_PER_TIER', '1'))
    )
    # Fallback angle when the Explorer leaves lens null; keeps the semantic
    # signature meaningful and satisfies topics.lens_id (NOT NULL) until the
    # column is made nullable.
    default_lens_code: str = field(
        default_factory=lambda: os.getenv('TOPIC_DEFAULT_LENS', 'practical')
    )

    # LLM Configuration (via OpenRouter).
    #
    # Was google/gemini-2.0-flash-001 until 2026-08-14, by which point OpenRouter
    # had delisted that slug — so every Explorer and Gatekeeper call 404'd and
    # topic generation produced nothing at all. Unlike the judges, these agents
    # have no fail-open path; the run just raises.
    #
    # google/gemini-3.5-flash-lite since 2026-08-16: the system now runs exactly
    # ONE gemini slug everywhere (migrations/consolidate_gemini_on_3_5_flash_lite.sql),
    # and this default is the only place that policy lives in code rather than in
    # prompt_templates. Explorer is English-only, and under the routing policy
    # (migrations/generator_model_routing_policy.sql) en routes to gemini.
    #
    # This is a code default, not a prompt_templates row: explorer_ideation_t1..t6
    # and gatekeeper_check carry prompt *text* only (model IS NULL), so the
    # nightly slug-health probe cannot see it. Re-check it by hand when a slug
    # rotates — see services/model_health.py — and verify the new slug against
    # services.model_arena.pricing.fetch_model_list() before changing it.
    llm_model: str = field(
        default_factory=lambda: os.getenv('TOPIC_LLM_MODEL', 'google/gemini-3.5-flash-lite')
    )
    llm_temperature: float = field(
        default_factory=lambda: float(os.getenv('TOPIC_LLM_TEMPERATURE', '0.8'))
    )

    # Embedding Configuration (via OpenAI)
    embedding_model: str = field(
        default_factory=lambda: os.getenv('TOPIC_EMBEDDING_MODEL', 'text-embedding-3-small')
    )
    embedding_dimensions: int = 1536  # Fixed for text-embedding-3-small

    # Gatekeeper Configuration
    gatekeeper_temperature: float = field(
        default_factory=lambda: float(os.getenv('TOPIC_GATEKEEPER_TEMPERATURE', '0.3'))
    )
    gatekeeper_short_circuit_threshold: int = field(
        default_factory=lambda: int(os.getenv('TOPIC_GATEKEEPER_SHORT_CIRCUIT', '3'))
    )

    # Operational Settings
    dry_run: bool = field(
        default_factory=lambda: os.getenv('TOPIC_DRY_RUN', 'false').lower() == 'true'
    )
    log_level: str = field(
        default_factory=lambda: os.getenv('TOPIC_LOG_LEVEL', 'INFO')
    )

    # API Keys (fallback to main config)
    openrouter_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv('OPENROUTER_API_KEY')
    )
    openai_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv('OPENAI_API_KEY')
    )

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not set - LLM calls will fail")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set - embedding calls will fail")

        # Configure logging level
        logging.getLogger('services.topic_generation').setLevel(
            getattr(logging, self.log_level.upper(), logging.INFO)
        )

    def threshold_for_tier(self, tier: Optional[int]) -> float:
        """The novelty threshold to apply to a candidate at ``tier``.

        Falls back to the flat ``similarity_threshold`` for an untiered
        candidate — 43 live topics carry no target_age_tier, and an unknown
        tier is not a reason to stop deduplicating them.
        """
        if tier is None:
            return self.similarity_threshold
        return self.similarity_threshold_by_tier.get(
            int(tier), self.similarity_threshold
        )

    def validate(self) -> bool:
        """Check if all required configuration is present."""
        errors = []

        if not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY is required")
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        if self.daily_topic_quota < 1:
            errors.append("TOPIC_DAILY_QUOTA must be >= 1")
        if not 0.5 <= self.similarity_threshold <= 1.0:
            errors.append("TOPIC_SIMILARITY_THRESHOLD must be between 0.5 and 1.0")
        for tier, value in sorted(self.similarity_threshold_by_tier.items()):
            if not 0.5 <= value <= 1.0:
                errors.append(
                    f"TOPIC_SIMILARITY_THRESHOLDS_BY_TIER: tier {tier} "
                    f"threshold {value} must be between 0.5 and 1.0"
                )

        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False

        return True


# Singleton instance - lazily evaluated
_config_instance: Optional[TopicGenConfig] = None


def get_topic_gen_config() -> TopicGenConfig:
    """Get the topic generation configuration singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = TopicGenConfig()
    return _config_instance


# Convenience alias
topic_gen_config = TopicGenConfig()
