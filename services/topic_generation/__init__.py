"""
Topic Generation Module

AI-powered topic generation system for Linguadojo.
Generates diverse, semantically deduplicated topics using a multi-agent pipeline.
"""

from .config import topic_gen_config
from .orchestrator import TopicGenerationOrchestrator
from .database_client import TopicDatabaseClient

__all__ = [
    'topic_gen_config',
    'TopicGenerationOrchestrator',
    'TopicDatabaseClient',
]
