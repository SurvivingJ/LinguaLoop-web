"""
Chinese Processor — jieba

Segments Chinese text into words using jieba with POS tagging.
Chinese does not inflect, so no lemmatization is needed (lemma = surface form).

Chengyu (4-character idioms) are automatically segmented as single tokens.
Phrase detection is DISABLED for Chinese (config.phrase_detection_enabled = False).
"""

import logging
from services.vocabulary.processors.base import BaseLanguageProcessor, LemmaToken
from services.vocabulary.model_cache import model_cache

logger = logging.getLogger(__name__)

_CONTENT_POS = {"n", "v", "a", "d", "i", "l", "vn", "an"}

_STOP_WORDS = frozenset({
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
    '都', '一', '上', '也', '很', '到', '说', '要', '去', '你',
    '会', '着', '没有', '看', '好', '自己', '这', '那', '但', '与',
    '或', '因为', '所以', '如果', '虽然', '但是', '然后', '一个',
    '他', '她', '它', '们', '把', '被', '让', '从', '向', '对',
    '还', '又', '而', '且', '只', '才', '已', '来', '过', '吗',
    '呢', '吧', '啊', '哦', '嗯', '了', '的话', '什么', '怎么',
})


def _load_jieba():
    """Load jieba POS tagger and force initialization."""
    import jieba.posseg as pseg
    list(pseg.cut("初始化"))  # Warm up
    return pseg


class ChineseProcessor(BaseLanguageProcessor):
    """Chinese segmentation using jieba with POS tagging."""

    def _get_tagger(self):
        return model_cache.get("jieba_pseg", _load_jieba)

    def extract_lemma_tokens(self, text: str) -> list[LemmaToken]:
        pseg = self._get_tagger()
        word_pos_pairs = list(pseg.cut(text))

        tokens = []
        for i, (word, pos) in enumerate(word_pos_pairs):
            word = word.strip()
            if not word:
                continue

            # Check if first char of POS tag is a content POS
            is_content = pos in _CONTENT_POS or (len(pos) > 0 and pos[0] in {'n', 'v', 'a'})

            tokens.append(LemmaToken(
                index=i,
                surface=word,
                lemma=word,  # No inflection — lemma = surface
                pos=pos,
                is_stop=word in _STOP_WORDS,
                is_content=is_content,
            ))

        return tokens

    def is_ready(self) -> bool:
        try:
            self._get_tagger()
            return True
        except Exception as e:
            logger.error(f"Chinese processor not ready: {e}")
            return False
