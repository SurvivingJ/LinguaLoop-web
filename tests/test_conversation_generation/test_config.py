"""Tests for ConvGenConfig."""

import os
import pytest
from unittest.mock import patch


class TestConvGenConfig:
    """Tests for conversation generation configuration."""

    def test_default_values(self):
        """Config has sensible defaults without env vars."""
        from services.conversation_generation.config import ConvGenConfig

        config = ConvGenConfig()
        assert config.batch_size == 20
        assert config.turns_min == 6
        assert config.turns_max == 20
        assert config.default_turns == 12
        assert config.temperature == 0.85
        assert config.llm_provider == 'openrouter'
        assert config.min_quality_score == 0.70
        assert 'T3' in config.target_complexity_tiers

    def test_env_override(self):
        """Config reads from environment variables."""
        with patch.dict(os.environ, {
            'CONV_GEN_BATCH_SIZE': '5',
            'CONV_GEN_TURNS_MIN': '4',
            'CONV_GEN_TURNS_MAX': '10',
            'CONV_GEN_TEMPERATURE': '0.5',
            'CONV_GEN_LLM_PROVIDER': 'ollama',
        }):
            from services.conversation_generation.config import ConvGenConfig
            config = ConvGenConfig()
            assert config.batch_size == 5
            assert config.turns_min == 4
            assert config.turns_max == 10
            assert config.temperature == 0.5
            assert config.llm_provider == 'ollama'

    def test_validate_success(self):
        """Validation passes with Ollama provider (no API key needed)."""
        with patch.dict(os.environ, {'CONV_GEN_LLM_PROVIDER': 'ollama'}):
            from services.conversation_generation.config import ConvGenConfig
            config = ConvGenConfig()
            assert config.validate() is True

    def test_validate_invalid_provider(self):
        """Validation fails with unknown provider."""
        with patch.dict(os.environ, {'CONV_GEN_LLM_PROVIDER': 'invalid'}):
            from services.conversation_generation.config import ConvGenConfig
            config = ConvGenConfig()
            assert config.validate() is False

    def test_validate_turns_range(self):
        """Validation fails when turns_max < turns_min."""
        with patch.dict(os.environ, {
            'CONV_GEN_LLM_PROVIDER': 'ollama',
            'CONV_GEN_TURNS_MIN': '20',
            'CONV_GEN_TURNS_MAX': '5',
        }):
            from services.conversation_generation.config import ConvGenConfig
            config = ConvGenConfig()
            assert config.validate() is False
