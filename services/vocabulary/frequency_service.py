"""
Zipf Frequency Score Service

Pure utility functions for looking up word frequency scores via the wordfreq library.
No database access — just input/output.

Zipf scale: ~0 (extremely rare) to ~8 (most common words like "the").
Returns None when wordfreq has no data for the lemma.
"""

import logging
from typing import Optional

from wordfreq import zipf_frequency

logger = logging.getLogger(__name__)

# App language codes → wordfreq language codes
_LANG_MAP: dict[str, str] = {
    "cn": "zh",
    "jp": "ja",
    "en": "en",
}

# Penalty subtracted from component-average for phrase scores
_PHRASE_PENALTY = 0.5

# Floor: scores below this are treated as "unknown" (wordfreq returns 0.0 for unknown)
_MIN_SCORE = 0.01


def _to_wordfreq_lang(language_code: str) -> str:
    """Map app language code to wordfreq language code."""
    wf_lang = _LANG_MAP.get(language_code)
    if wf_lang is None:
        raise ValueError(
            f"No wordfreq mapping for language '{language_code}'. "
            f"Known: {list(_LANG_MAP.keys())}"
        )
    return wf_lang


def get_zipf_score(lemma: str, language_code: str) -> Optional[float]:
    """
    Get the Zipf frequency score for a single lemma.

    Args:
        lemma: The word/lemma to look up.
        language_code: App language code ('en', 'cn', 'jp').

    Returns:
        Float Zipf score (typically 1.0–7.0), or None if unknown.
    """
    wf_lang = _to_wordfreq_lang(language_code)
    score = zipf_frequency(lemma, wf_lang)
    if score < _MIN_SCORE:
        return None
    return round(score, 2)


def get_zipf_score_for_phrase(
    phrase_lemma: str,
    component_lemmas: list[str],
    language_code: str,
) -> Optional[float]:
    """
    Estimate a Zipf score for a multi-word phrase.

    Strategy: try direct lookup first, then average component scores minus a penalty.
    Requires at least half of components to have scores.

    Args:
        phrase_lemma: The full phrase (used for direct lookup first).
        component_lemmas: Individual word components.
        language_code: App language code.

    Returns:
        Float Zipf score or None.
    """
    direct = get_zipf_score(phrase_lemma, language_code)
    if direct is not None:
        return direct

    if not component_lemmas:
        return None

    scores = []
    for comp in component_lemmas:
        s = get_zipf_score(comp, language_code)
        if s is not None:
            scores.append(s)

    # Require at least half the components to have scores
    if len(scores) < max(1, len(component_lemmas) // 2):
        return None

    avg = sum(scores) / len(scores)
    result = max(avg - _PHRASE_PENALTY, 0.0)
    return round(result, 2)


def compute_zipf_for_vocab_item(
    item: dict, language_code: str
) -> Optional[float]:
    """
    Compute Zipf score for a vocabulary item dict (as produced by extract_detailed).

    Handles both single words and phrases via the appropriate lookup.

    Args:
        item: Dict with 'lemma', optionally 'is_phrase', 'components'.
        language_code: App language code.

    Returns:
        Float Zipf score or None.
    """
    lemma = item["lemma"]
    if item.get("is_phrase") and item.get("components"):
        return get_zipf_score_for_phrase(lemma, item["components"], language_code)
    return get_zipf_score(lemma, language_code)
