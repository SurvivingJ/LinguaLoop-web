"""
Japanese Processor — fugashi + UniDic

Segments and lemmatizes Japanese text using fugashi (MeCab wrapper)
with the UniDic-lite dictionary.

UniDic's 'lemma' field returns dictionary forms:
    '食べました' → '食べる'
    '走っている' → '走る'

Particles (助詞) and auxiliaries (助動詞) are kept for phrase detection
but flagged as non-content.
"""

import logging
from services.vocabulary.processors.base import BaseLanguageProcessor, LemmaToken
from services.vocabulary.model_cache import model_cache

logger = logging.getLogger(__name__)

_CONTENT_POS = {"名詞", "動詞", "形容詞", "形状詞", "副詞"}
_SKIP_POS = {"助詞", "助動詞", "記号", "補助記号", "空白"}


def _load_fugashi():
    """Load fugashi tagger with UniDic."""
    from fugashi import Tagger
    return Tagger()


class JapaneseProcessor(BaseLanguageProcessor):
    """Japanese segmentation + lemmatization using fugashi + UniDic."""

    def _get_tagger(self):
        return model_cache.get("fugashi_tagger", _load_fugashi)

    def extract_lemma_tokens(self, text: str) -> list[LemmaToken]:
        tagger = self._get_tagger()
        words = list(tagger(text))

        tokens = []
        for i, word in enumerate(words):
            surface = word.surface
            if not surface.strip():
                continue

            pos = word.feature.pos1
            lemma = word.feature.lemma

            # UniDic returns '*' when no lemma is available
            if not lemma or lemma == '*':
                lemma = surface

            tokens.append(LemmaToken(
                index=i,
                surface=surface,
                lemma=lemma,
                pos=pos,
                is_stop=pos in _SKIP_POS,
                is_content=pos in _CONTENT_POS,
            ))

        return tokens

    def is_ready(self) -> bool:
        try:
            self._get_tagger()
            return True
        except Exception as e:
            logger.error(f"Japanese processor not ready: {e}")
            return False
