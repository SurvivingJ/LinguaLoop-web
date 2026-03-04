"""
NLP Metadata Registry

Language-specific NLP configuration that doesn't belong in the database.
Database config (models, TTS, etc.) comes from TestDatabaseClient.get_language_config().
This file only holds NLP library metadata.

To add a new language:
    1. Add entry to _NLP_METADATA below
    2. Create processor class in processors/
    3. Register in _PROCESSOR_CLASSES (pipeline.py)
    4. Insert prompt rows in prompt_templates table
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class NLPTool(str, Enum):
    """Which NLP library handles tokenization for this language."""
    SPACY = "spacy"
    JIEBA = "jieba"
    FUGASHI = "fugashi"


@dataclass(frozen=True)
class NLPMetadata:
    """
    NLP-specific configuration for a language.

    Merged with LanguageConfig (from DB) at runtime to get the full picture.
    """
    nlp_tool: NLPTool
    spacy_model: Optional[str] = None
    needs_lemmatization: bool = True
    needs_segmentation: bool = False
    phrase_detection_enabled: bool = True
    content_pos_tags: tuple[str, ...] = ()


# ============================================================
# NLP METADATA — Add new languages here
# ============================================================

_NLP_METADATA: dict[str, NLPMetadata] = {
    "en": NLPMetadata(
        nlp_tool=NLPTool.SPACY,
        spacy_model="en_core_web_sm",
        needs_lemmatization=True,
        needs_segmentation=False,
        phrase_detection_enabled=True,
        content_pos_tags=("NOUN", "VERB", "ADJ", "ADV"),
    ),
    "cn": NLPMetadata(
        nlp_tool=NLPTool.JIEBA,
        needs_lemmatization=False,
        needs_segmentation=True,
        phrase_detection_enabled=False,
        content_pos_tags=("n", "v", "a", "d", "i", "l", "vn", "an"),
    ),
    "jp": NLPMetadata(
        nlp_tool=NLPTool.FUGASHI,
        needs_lemmatization=True,
        needs_segmentation=True,
        phrase_detection_enabled=True,
        content_pos_tags=("名詞", "動詞", "形容詞", "形状詞", "副詞"),
    ),
}


def get_nlp_metadata(language_code: str) -> NLPMetadata:
    """
    Get NLP metadata for a language.

    Args:
        language_code: ISO code ('en', 'cn', 'jp')

    Returns:
        NLPMetadata for the language

    Raises:
        ValueError: If no metadata exists for the language
    """
    if language_code not in _NLP_METADATA:
        raise ValueError(
            f"No NLP metadata for language '{language_code}'. "
            f"Add an entry to _NLP_METADATA in services/vocabulary/config.py"
        )
    return _NLP_METADATA[language_code]


def supported_languages() -> list[str]:
    """Return list of language codes with NLP metadata configured."""
    return list(_NLP_METADATA.keys())
