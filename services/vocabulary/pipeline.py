"""
Vocabulary Extraction Pipeline

Public API for extracting vocabulary (lemmas + multi-word phrases)
from raw text for language learning test generation.

Usage:
    pipeline = VocabularyExtractionPipeline(openai_client, db_client)
    vocab = pipeline.extract("She threw up after eating ice cream.", "en")
    # → ["throw up", "eat", "ice cream"]

Pipeline stages:
    1. Lemmatization (language-specific processor)
    2. Phrase detection (LLM, if enabled for language)
    3. Component replacement (merge "throw" + "up" → "throw up")
    4. Filtering (remove stop words, keep content words + phrases)
    5. Deduplication
"""

import logging
from typing import Optional

from services.vocabulary.config import get_nlp_metadata
from services.vocabulary.phrase_detector import PhraseDetector
from services.vocabulary.processors.base import BaseLanguageProcessor, LemmaToken
from services.vocabulary.processors.english import EnglishProcessor
from services.vocabulary.processors.chinese import ChineseProcessor
from services.vocabulary.processors.japanese import JapaneseProcessor

logger = logging.getLogger(__name__)


# ============================================================
# PROCESSOR REGISTRY — Add new language processors here
# ============================================================
_PROCESSOR_CLASSES: dict[str, type[BaseLanguageProcessor]] = {
    "en": EnglishProcessor,
    "cn": ChineseProcessor,
    "jp": JapaneseProcessor,
}


class VocabularyExtractionPipeline:
    """
    Main entry point for vocabulary extraction.

    Orchestrates lemmatization → phrase detection → merging → filtering.
    """

    def __init__(self, openai_client, db_client):
        """
        Args:
            openai_client: OpenAI client instance (direct or via OpenRouter)
            db_client: TestDatabaseClient for DB lookups
        """
        self._db = db_client
        self._phrase_detector = PhraseDetector(openai_client, db_client)
        self._processors: dict[str, BaseLanguageProcessor] = {}

    def _get_processor(self, language_code: str) -> BaseLanguageProcessor:
        """Get or create processor for language."""
        if language_code not in self._processors:
            cls = _PROCESSOR_CLASSES.get(language_code)
            if cls is None:
                raise ValueError(
                    f"No processor for '{language_code}'. "
                    f"Add a class to processors/ and register in _PROCESSOR_CLASSES."
                )
            self._processors[language_code] = cls()
        return self._processors[language_code]

    def extract(self, text: str, language_code: str) -> list[str]:
        """
        Extract vocabulary from text.

        Args:
            text: Raw input text
            language_code: e.g., 'en', 'cn', 'jp'

        Returns:
            Deduplicated list of lemmas and phrases
        """
        if not text or not text.strip():
            return []

        nlp_meta = get_nlp_metadata(language_code)
        lang_config = self._db.get_language_config_by_code(language_code)
        if not lang_config:
            raise ValueError(f"Language '{language_code}' not found or inactive in database")

        # Step 1: Lemmatize
        processor = self._get_processor(language_code)
        lemma_tokens: list[LemmaToken] = processor.extract_lemma_tokens(text)

        if not lemma_tokens:
            return []

        # Step 2: Phrase detection (skip if disabled for language)
        phrases: list[dict] = []
        if nlp_meta.phrase_detection_enabled:
            phrases = self._phrase_detector.detect(
                lemma_tokens=lemma_tokens,
                original_text=text,
                language_id=lang_config.id,
                model=lang_config.prose_model,
            )

        # Step 3: Replace component lemmas with combined phrases
        lemmas = [t.lemma for t in lemma_tokens]
        merged = self._replace_components(lemmas, phrases)

        # Step 4: Filter — keep content words and multi-word phrases
        stop_lemmas = {t.lemma for t in lemma_tokens if t.is_stop}
        content_lemmas = {t.lemma for t in lemma_tokens if t.is_content}

        filtered = [
            v for v in merged
            if " " in v  # Always keep multi-word phrases
            or (v not in stop_lemmas and v in content_lemmas)
        ]

        # Step 5: Deduplicate (preserve order)
        seen = set()
        result = []
        for v in filtered:
            v = v.strip()
            if v and v not in seen:
                seen.add(v)
                result.append(v)

        return result

    @staticmethod
    def _replace_components(
        lemmas: list[str],
        phrases: list[dict],
    ) -> list[str]:
        """
        Replace component lemmas with their combined phrase.

        Handles:
            - Adjacent: ["throw", "up"] → "throw up"
            - Longest-first: prevents partial matches
            - Duplicates: each phrase consumes first unclaimed occurrence

        Algorithm:
            1. Sort phrases by component count (longest first)
            2. For each phrase, find first unclaimed occurrence
            3. Mark components as consumed, replace first with phrase
            4. Return list with consumed tokens removed
        """
        tracked = [{"lemma": l, "consumed": False} for l in lemmas]

        phrases_sorted = sorted(
            phrases,
            key=lambda p: len(p.get("components", [])),
            reverse=True,
        )

        for phrase in phrases_sorted:
            components = phrase.get("components", [])
            n = len(components)
            if n < 2:
                continue

            for i in range(len(tracked) - n + 1):
                window = tracked[i:i + n]

                matches = all(
                    w["lemma"] == components[j] and not w["consumed"]
                    for j, w in enumerate(window)
                )

                if matches:
                    tracked[i]["lemma"] = phrase["phrase"]
                    for j in range(1, n):
                        tracked[i + j]["consumed"] = True
                    break

        return [t["lemma"] for t in tracked if not t["consumed"]]

    def extract_detailed(self, text: str, language_code: str) -> list[dict]:
        """
        Extract vocabulary with full metadata for DB storage.

        Same pipeline as extract() but returns dicts instead of strings,
        preserving POS, phrase_type, and component_lemmas.

        Args:
            text: Raw input text
            language_code: e.g., 'en', 'cn', 'jp'

        Returns:
            List of dicts:
            [
                {"lemma": "throw up", "pos": "VERB", "is_phrase": True,
                 "phrase_type": "phrasal_verb", "components": ["throw", "up"]},
                {"lemma": "eat", "pos": "VERB", "is_phrase": False,
                 "phrase_type": None, "components": None},
            ]
        """
        if not text or not text.strip():
            return []

        nlp_meta = get_nlp_metadata(language_code)
        lang_config = self._db.get_language_config_by_code(language_code)
        if not lang_config:
            raise ValueError(f"Language '{language_code}' not found or inactive in database")

        # Step 1: Lemmatize
        processor = self._get_processor(language_code)
        lemma_tokens: list[LemmaToken] = processor.extract_lemma_tokens(text)

        if not lemma_tokens:
            return []

        # Step 2: Phrase detection (skip if disabled for language)
        phrases: list[dict] = []
        if nlp_meta.phrase_detection_enabled:
            phrases = self._phrase_detector.detect(
                lemma_tokens=lemma_tokens,
                original_text=text,
                language_id=lang_config.id,
                model=lang_config.prose_model,
            )

        # Build lookup maps for metadata
        # lemma → dominant POS (first occurrence wins)
        lemma_pos: dict[str, str] = {}
        for t in lemma_tokens:
            if t.lemma not in lemma_pos and t.is_content:
                lemma_pos[t.lemma] = t.pos

        # phrase string → phrase dict (for phrase_type and components)
        phrase_map: dict[str, dict] = {}
        for p in phrases:
            phrase_map[p.get("phrase", "")] = p

        # Step 3: Replace component lemmas with combined phrases
        lemmas = [t.lemma for t in lemma_tokens]
        merged = self._replace_components(lemmas, phrases)

        # Step 4: Filter — keep content words and multi-word phrases
        stop_lemmas = {t.lemma for t in lemma_tokens if t.is_stop}
        content_lemmas = {t.lemma for t in lemma_tokens if t.is_content}

        filtered = [
            v for v in merged
            if " " in v
            or (v not in stop_lemmas and v in content_lemmas)
        ]

        # Step 5: Deduplicate and build detailed results
        seen = set()
        result = []
        for v in filtered:
            v = v.strip()
            if not v or v in seen:
                continue
            seen.add(v)

            is_phrase = " " in v
            p_info = phrase_map.get(v, {})

            result.append({
                "lemma": v,
                "pos": lemma_pos.get(v) or p_info.get("components", [None])[0] and lemma_pos.get(p_info.get("components", [""])[0]),
                "is_phrase": is_phrase,
                "phrase_type": p_info.get("phrase_type") if is_phrase else None,
                "components": p_info.get("components") if is_phrase else None,
            })

        return result

    def health_check(self) -> dict[str, bool]:
        """
        Check all registered language processors are ready.

        Returns:
            Dict mapping language_code → ready status
        """
        results = {}
        for code, cls in _PROCESSOR_CLASSES.items():
            try:
                processor = self._get_processor(code)
                results[code] = processor.is_ready()
            except Exception:
                results[code] = False
        return results
