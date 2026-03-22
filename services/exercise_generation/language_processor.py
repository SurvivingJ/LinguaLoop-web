# services/exercise_generation/language_processor.py

import re
from abc import ABC, abstractmethod


class LanguageProcessor(ABC):
    """
    Abstract base for language-specific NLP operations.
    Instantiate via LanguageProcessor.for_language(language_id).
    All methods are stateless after __init__.
    """

    language_id: int

    @abstractmethod
    def split_sentences(self, text: str) -> list[str]:
        """Split a paragraph or transcript into individual sentences."""

    @abstractmethod
    def chunk_sentence(self, sentence: str) -> list[str]:
        """Split a sentence into 3-6 syntactic chunks for jumbled_sentence exercises."""

    @abstractmethod
    def tokenize(self, sentence: str) -> list[str]:
        """Split a sentence into individual words, filtering out punctuation and whitespace."""

    def matches_pattern(self, sentence: str, pattern_code: str) -> bool:
        """
        Return True if the sentence demonstrates the given grammar pattern.
        Default uses PATTERN_HEURISTICS regex lookup from config.
        """
        from services.exercise_generation.config import PATTERN_HEURISTICS
        heuristic = PATTERN_HEURISTICS.get(pattern_code)
        if heuristic:
            return bool(re.search(heuristic, sentence))
        return False

    def contains_collocation(self, sentence: str, collocation_text: str) -> bool:
        """Return True if collocation_text appears as a contiguous substring."""
        return collocation_text.lower() in sentence.lower()

    def merge_short_chunks(self, chunks: list[str], min_tokens: int = 2) -> list[str]:
        """Merge chunks shorter than min_tokens with their left neighbour."""
        if not chunks:
            return chunks
        merged = [chunks[0]]
        for chunk in chunks[1:]:
            token_count = len(chunk.split()) if chunk.isascii() else len(chunk)
            if token_count < min_tokens:
                merged[-1] = merged[-1] + ' ' + chunk if chunk.isascii() else merged[-1] + chunk
            else:
                merged.append(chunk)
        return merged

    @staticmethod
    def for_language(language_id: int) -> 'LanguageProcessor':
        """Factory method. Returns the correct subclass for the given language_id."""
        mapping = {1: ChineseProcessor, 2: EnglishProcessor, 3: JapaneseProcessor}
        cls = mapping.get(language_id)
        if cls is None:
            raise ValueError(f"No LanguageProcessor for language_id={language_id}")
        return cls()


class EnglishProcessor(LanguageProcessor):
    """English NLP using spaCy en_core_web_sm."""

    language_id = 2

    def __init__(self):
        import spacy
        if not hasattr(EnglishProcessor, '_nlp'):
            EnglishProcessor._nlp = spacy.load('en_core_web_sm')
        self.nlp = EnglishProcessor._nlp

    def split_sentences(self, text: str) -> list[str]:
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    def chunk_sentence(self, sentence: str) -> list[str]:
        doc = self.nlp(sentence)
        noun_chunks = list(doc.noun_chunks)

        if len(noun_chunks) < 2:
            chunks = self._simple_split(sentence)
        else:
            chunks = []
            prev_end = 0
            for nc in noun_chunks:
                between = doc[prev_end:nc.start]
                if between.text.strip():
                    chunks.append(between.text.strip())
                chunks.append(nc.text.strip())
                prev_end = nc.end
            tail = doc[prev_end:]
            if tail.text.strip():
                chunks.append(tail.text.strip())
            chunks = [c for c in chunks if c]

        chunks = self.merge_short_chunks(chunks, min_tokens=2)

        if len(chunks) < 3:
            raise ValueError(
                f"EnglishProcessor.chunk_sentence: only {len(chunks)} chunks for: {sentence[:60]}"
            )
        return chunks[:6]

    def tokenize(self, sentence: str) -> list[str]:
        doc = self.nlp(sentence)
        return [tok.text for tok in doc if not tok.is_punct and not tok.is_space]

    def _simple_split(self, sentence: str) -> list[str]:
        pattern = r'\b(after|before|because|when|while|and|but|although|since|if)\b'
        parts = re.split(pattern, sentence, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip() and not re.fullmatch(pattern, p.strip(), re.IGNORECASE)]

    def contains_collocation(self, sentence: str, collocation_text: str) -> bool:
        words = collocation_text.split()
        if len(words) == 1:
            return bool(re.search(r'\b' + re.escape(collocation_text) + r'\b', sentence, re.IGNORECASE))
        return collocation_text.lower() in sentence.lower()


class ChineseProcessor(LanguageProcessor):
    """Mandarin Chinese NLP using jieba for tokenisation and chunking."""

    language_id = 1

    SENTENCE_END_PATTERN = re.compile(r'(?<=[。！？])')
    BOUNDARY_MARKERS = frozenset({'，', '。', '、', '了', '在', '和', '与', '但', '因为', '所以'})
    PUNCTUATION = frozenset('，。、！？；：""''（）【】《》—…·')

    def split_sentences(self, text: str) -> list[str]:
        parts = self.SENTENCE_END_PATTERN.split(text)
        return [p.strip() for p in parts if p.strip()]

    def tokenize(self, sentence: str) -> list[str]:
        import jieba
        return [t for t in jieba.cut(sentence, cut_all=False)
                if t.strip() and t not in self.PUNCTUATION]

    def chunk_sentence(self, sentence: str) -> list[str]:
        import jieba
        tokens = [t for t in jieba.cut(sentence, cut_all=False) if t.strip()]
        chunks = []
        current: list[str] = []

        for token in tokens:
            current.append(token)
            if token in self.BOUNDARY_MARKERS or len(current) >= 4:
                chunk_text = ''.join(current).strip('，。、')
                if chunk_text:
                    chunks.append(chunk_text)
                current = []

        if current:
            chunks.append(''.join(current).strip('，。、'))

        chunks = [c for c in chunks if len(c) >= 1]
        chunks = chunks[:6]

        if len(chunks) < 3:
            raise ValueError(
                f"ChineseProcessor.chunk_sentence: only {len(chunks)} chunks for: {sentence[:40]}"
            )
        return chunks


class JapaneseProcessor(LanguageProcessor):
    """Japanese NLP using spaCy ja_core_news_sm."""

    language_id = 3

    def __init__(self):
        import spacy
        if not hasattr(JapaneseProcessor, '_nlp'):
            JapaneseProcessor._nlp = spacy.load('ja_core_news_sm')
        self.nlp = JapaneseProcessor._nlp

    def split_sentences(self, text: str) -> list[str]:
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    def tokenize(self, sentence: str) -> list[str]:
        doc = self.nlp(sentence)
        return [tok.text for tok in doc if not tok.is_punct and not tok.is_space]

    def chunk_sentence(self, sentence: str) -> list[str]:
        doc = self.nlp(sentence)
        chunks = []
        current: list[str] = []

        for token in doc:
            current.append(token.text)
            if token.pos_ == 'ADP' or token.dep_ in ('case', 'mark'):
                chunks.append(''.join(current))
                current = []

        if current:
            chunks.append(''.join(current))

        chunks = [c for c in chunks if c.strip()]
        chunks = chunks[:6]

        if len(chunks) < 3:
            raise ValueError(
                f"JapaneseProcessor.chunk_sentence: only {len(chunks)} chunks for: {sentence[:40]}"
            )
        return chunks


def prepare_jumbled_content(content: dict, language_id: int) -> dict:
    """Transform stored jumbled_sentence content into frontend-ready format.

    Takes content with just 'original_sentence' and returns content with
    'chunks' (individual words) and 'correct_ordering' added.
    """
    sentence = content['original_sentence']
    processor = LanguageProcessor.for_language(language_id)
    words = processor.tokenize(sentence)
    if len(words) < 2:
        words = [sentence]
    return {
        'original_sentence': sentence,
        'chunks': words,
        'correct_ordering': list(range(len(words))),
    }
