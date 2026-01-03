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
    max_candidates_per_run: int = field(
        default_factory=lambda: int(os.getenv('TOPIC_MAX_CANDIDATES', '10'))
    )

    # LLM Configuration (via OpenRouter)
    llm_model: str = field(
        default_factory=lambda: os.getenv('TOPIC_LLM_MODEL', 'google/gemini-2.0-flash-exp')
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
