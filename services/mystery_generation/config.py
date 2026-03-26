"""
Mystery Generation Configuration
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MysteryGenConfig:
    """Configuration for mystery generation pipeline."""

    # Mystery structure
    scene_count: int = 5
    questions_per_scene: int = 2
    finale_deduction_questions: int = 1
    min_words_per_scene: int = 100
    max_words_per_scene: int = 200
    mcq_options: int = 4

    archetypes: List[str] = field(default_factory=lambda: [
        'alibi_trick', 'locked_room', 'poison', 'impersonation', 'misdirection'
    ])

    # LLM Configuration (via OpenRouter)
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv('OPENROUTER_API_KEY', '')
    )
    plot_model: str = field(
        default_factory=lambda: os.getenv('MYSTERY_GEN_PLOT_MODEL', 'google/gemini-2.0-flash-exp')
    )
    scene_model: str = field(
        default_factory=lambda: os.getenv('MYSTERY_GEN_SCENE_MODEL', 'google/gemini-2.0-flash-exp')
    )
    question_model: str = field(
        default_factory=lambda: os.getenv('MYSTERY_GEN_QUESTION_MODEL', 'google/gemini-2.0-flash-exp')
    )
    plot_temperature: float = 0.9
    scene_temperature: float = 0.8
    question_temperature: float = 0.7

    # System user ID (for gen_user field — must exist in users table)
    system_user_id: Optional[str] = field(
        default_factory=lambda: os.getenv('TEST_GEN_SYSTEM_USER_ID', 'de6fd05b-0871-45d4-a2d8-0195fdf5355e')
    )

    # Retry
    max_retries: int = 3
    retry_delay: float = 2.0

    # CEFR difficulty mapping
    difficulty_to_cefr: dict = field(default_factory=lambda: {
        1: 'A1', 2: 'A1', 3: 'A2', 4: 'B1', 5: 'B1',
        6: 'B2', 7: 'C1', 8: 'C2', 9: 'C2'
    })

    def validate(self) -> bool:
        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not set")
            return False
        return True


# Singleton
mystery_gen_config = MysteryGenConfig()


def get_mystery_gen_config() -> MysteryGenConfig:
    return mystery_gen_config
