"""
Topic Generation Module

AI-powered topic generation system for LinguaDojo.
Generates diverse, semantically deduplicated topics using a multi-agent pipeline.
Also supports JSON-based topic imports.
"""

from .config import topic_gen_config
from .orchestrator import TopicGenerationOrchestrator
from .database_client import TopicDatabaseClient
from .json_importer import JSONTopicImporter, JSONTopicEntry
from .import_orchestrator import TopicImportOrchestrator, ImportMetrics

__all__ = [
    'topic_gen_config',
    'TopicGenerationOrchestrator',
    'TopicDatabaseClient',
    'JSONTopicImporter',
    'JSONTopicEntry',
    'TopicImportOrchestrator',
    'ImportMetrics',
]
