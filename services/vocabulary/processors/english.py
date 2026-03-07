"""
English Processor — spaCy + LemmInflect

Tokenizes and lemmatizes English text using spaCy (en_core_web_sm).
LemmInflect patches spaCy to improve lemma accuracy:
    - Verbs: 79.5% → 96.1%
    - Adjectives: 60.5% → 93.9%

Named entities (London, Apple Inc.) are preserved but flagged.
"""

import logging
from services.vocabulary.processors.base import BaseLanguageProcessor, LemmaToken
from services.vocabulary.model_cache import model_cache

logger = logging.getLogger(__name__)

_CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV"}


def _load_english_model():
    """Load spaCy + lemminflect (patches spaCy on import)."""
    import spacy
    import lemminflect  # noqa: F401 — patches spaCy on import

    return spacy.load("en_core_web_sm")


class EnglishProcessor(BaseLanguageProcessor):
    """English lemmatization using spaCy + LemmInflect."""

    def _get_nlp(self):
        return model_cache.get("spacy_en", _load_english_model)

    def extract_lemma_tokens(self, text: str) -> list[LemmaToken]:
        nlp = self._get_nlp()
        doc = nlp(text)

        tokens = []
        for token in doc:
            if token.is_space or (token.is_punct and not token.is_alpha):
                continue

            # LemmInflect patches token._.lemma() for better accuracy
            lemma = (
                token._.lemma()
                if hasattr(token._, "lemma") and token._.lemma()
                else token.lemma_
            )

            tokens.append(LemmaToken(
                index=token.i,
                surface=token.text,
                lemma=lemma.lower().strip(),
                pos=token.pos_,
                is_stop=token.is_stop,
                is_content=token.pos_ in _CONTENT_POS,
            ))

        return tokens

    def tokenize_full(self, text: str) -> list[tuple[str, str, bool]]:
        nlp = self._get_nlp()
        doc = nlp(text)
        result = []
        for token in doc:
            lemma = (
                token._.lemma()
                if hasattr(token._, "lemma") and token._.lemma()
                else token.lemma_
            )
            is_content = token.pos_ in _CONTENT_POS and not token.is_stop
            result.append((token.text_with_ws, lemma.lower().strip(), is_content))
        return result

    def is_ready(self) -> bool:
        try:
            self._get_nlp()
            return True
        except Exception as e:
            logger.error(f"English processor not ready: {e}")
            return False
