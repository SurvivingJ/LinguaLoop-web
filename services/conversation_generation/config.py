"""
Conversation Generation Configuration

Extends main Config with conversation generation specific settings.
All settings can be overridden via environment variables with CONV_GEN_ prefix.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ConvGenConfig:
    """Configuration for conversation generation system."""

    # Generation parameters
    batch_size: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_BATCH_SIZE', '20'))
    )
    turns_min: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_TURNS_MIN', '6'))
    )
    turns_max: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_TURNS_MAX', '20'))
    )
    default_turns: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_DEFAULT_TURNS', '12'))
    )
    target_cefr_levels: List[str] = field(
        default_factory=lambda: ['A2', 'B1', 'B2', 'C1']
    )
    persona_reminder_interval: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_PERSONA_REMINDER', '4'))
    )
    min_quality_score: float = field(
        default_factory=lambda: float(os.getenv('CONV_GEN_MIN_QUALITY', '0.70'))
    )

    # LLM Configuration (OpenRouter primary, Ollama optional)
    conversation_model: str = field(
        default_factory=lambda: os.getenv('CONV_GEN_MODEL', 'google/gemini-2.0-flash-001')
    )
    analysis_model: str = field(
        default_factory=lambda: os.getenv('CONV_GEN_ANALYSIS_MODEL', 'google/gemini-2.0-flash-001')
    )
    temperature: float = field(
        default_factory=lambda: float(os.getenv('CONV_GEN_TEMPERATURE', '0.85'))
    )

    # Ollama support (optional local LLM)
    llm_provider: str = field(
        default_factory=lambda: os.getenv('CONV_GEN_LLM_PROVIDER', 'openrouter')
    )
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv('CONV_GEN_OLLAMA_URL', 'http://localhost:11434/v1')
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv('CONV_GEN_OLLAMA_MODEL', 'qwen2.5:7b-instruct-q4_K_M')
    )

    # Exercise generation
    exercises_per_conversation: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_EXERCISES_PER_CONV', '15'))
    )

    # Retry Configuration
    max_retries: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_MAX_RETRIES', '3'))
    )
    retry_delay: float = field(
        default_factory=lambda: float(os.getenv('CONV_GEN_RETRY_DELAY', '2.0'))
    )

    # Generation mode: 'single_shot' (one LLM call) or 'per_turn' (one call per turn)
    generation_mode: str = field(
        default_factory=lambda: os.getenv('CONV_GEN_GENERATION_MODE', 'single_shot')
    )
    per_turn_max_tokens: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_PER_TURN_MAX_TOKENS', '200'))
    )

    # Batch processing settings
    max_parallel_workers: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_MAX_WORKERS', '1'))
    )
    max_conversations_per_domain: int = field(
        default_factory=lambda: int(os.getenv('CONV_GEN_MAX_PER_DOMAIN', '50'))
    )
    skip_existing_pairs: bool = field(
        default_factory=lambda: os.getenv('CONV_GEN_SKIP_EXISTING', 'true').lower() == 'true'
    )

    # Operational Settings
    dry_run: bool = field(
        default_factory=lambda: os.getenv('CONV_GEN_DRY_RUN', 'false').lower() == 'true'
    )
    log_level: str = field(
        default_factory=lambda: os.getenv('CONV_GEN_LOG_LEVEL', 'INFO')
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
        if self.llm_provider == 'openrouter' and not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not set - LLM calls will fail")

        # Parse target_cefr_levels from env if set
        env_levels = os.getenv('CONV_GEN_CEFR_LEVELS')
        if env_levels:
            try:
                import json
                self.target_cefr_levels = json.loads(env_levels)
            except Exception:
                logger.warning(f"Invalid CONV_GEN_CEFR_LEVELS: {env_levels}")

        # Configure logging level
        logging.getLogger('services.conversation_generation').setLevel(
            getattr(logging, self.log_level.upper(), logging.INFO)
        )

    def validate(self) -> bool:
        """Check if all required configuration is present."""
        errors = []

        if self.llm_provider == 'openrouter' and not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY is required when llm_provider is 'openrouter'")
        if self.llm_provider not in ('openrouter', 'ollama'):
            errors.append(f"Invalid llm_provider: {self.llm_provider}")
        if self.batch_size < 1:
            errors.append("CONV_GEN_BATCH_SIZE must be >= 1")
        if self.turns_min < 2:
            errors.append("CONV_GEN_TURNS_MIN must be >= 2")
        if self.turns_max < self.turns_min:
            errors.append("CONV_GEN_TURNS_MAX must be >= CONV_GEN_TURNS_MIN")
        if not self.target_cefr_levels:
            errors.append("target_cefr_levels must not be empty")

        valid_cefr = {'A1', 'A2', 'B1', 'B2', 'C1', 'C2'}
        for level in self.target_cefr_levels:
            if level not in valid_cefr:
                errors.append(f"Invalid CEFR level: {level}")
        if self.generation_mode not in ('single_shot', 'per_turn'):
            errors.append(f"Invalid generation_mode: {self.generation_mode}")
        if not 1 <= self.max_parallel_workers <= 4:
            errors.append("CONV_GEN_MAX_WORKERS must be 1-4")
        if not 50 <= self.per_turn_max_tokens <= 500:
            errors.append("CONV_GEN_PER_TURN_MAX_TOKENS must be 50-500")

        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False

        return True


# Singleton instance - lazily evaluated
_config_instance: Optional[ConvGenConfig] = None


def get_conv_gen_config() -> ConvGenConfig:
    """Get the conversation generation configuration singleton."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConvGenConfig()
    return _config_instance


# Convenience alias
conv_gen_config = ConvGenConfig()
