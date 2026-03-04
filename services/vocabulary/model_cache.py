"""
Lazy NLP Model Loader

Loads heavy NLP models (spaCy, jieba, fugashi) on first use and caches
them for the lifetime of the process. Thread-safe via threading.Lock.

Usage:
    from services.vocabulary.model_cache import model_cache

    nlp = model_cache.get("spacy_en", lambda: spacy.load("en_core_web_sm"))
"""

import threading
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ModelCache:
    """
    Thread-safe lazy model loader with permanent caching.

    Models are expensive to load (200-500ms each), so we load once
    per process and reuse across all requests.
    """

    def __init__(self):
        self._models: dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str, loader_fn: Callable[[], Any]) -> Any:
        """
        Get cached model, or load it if not yet cached.

        Args:
            key: Unique identifier (e.g., "spacy_en", "jieba_pseg")
            loader_fn: Callable that returns the loaded model

        Returns:
            The loaded model instance
        """
        if key in self._models:
            return self._models[key]

        with self._lock:
            if key not in self._models:
                logger.info(f"Loading NLP model: {key}")
                self._models[key] = loader_fn()
                logger.info(f"Model loaded: {key}")

        return self._models[key]

    def is_loaded(self, key: str) -> bool:
        """Check if a model is already cached."""
        return key in self._models


# Singleton instance
model_cache = ModelCache()
