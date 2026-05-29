"""
Test Generation Module

Consumes topics from production_queue and generates complete
listening/reading comprehension tests with questions and audio.
"""

from .config import get_test_gen_config
from .orchestrator import TestGenerationOrchestrator
from .database_client import TestDatabaseClient

__all__ = [
    'get_test_gen_config',
    'TestGenerationOrchestrator',
    'TestDatabaseClient'
]
