import re
import spacy
from abc import ABC, abstractmethod
from services.vocabulary.model_cache import model_cache


def _get_nlp_en():
    return model_cache.get("spacy_en", lambda: spacy.load("en_core_web_sm"))


def _get_nlp_ja():
    return model_cache.get("spacy_ja", lambda: spacy.load("ja_core_news_sm"))


class LanguageTokenizer(ABC):

    @abstractmethod
    def tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into word tokens suitable for n-gram extraction.
        Returns a flat list of strings. Must NOT include punctuation, whitespace,
        or stop words (for languages where stop-word removal is appropriate).
        For Chinese/Japanese, no lowercasing; for English, lowercase.
        """
        ...

    @abstractmethod
    def tokenize_with_pos(self, text: str) -> list[tuple[str, str]]:
        """
        Tokenize and return (token, POS_tag) pairs.
        POS tags are library-native (spaCy Universal Dependencies for EN/JA,
        jieba part-of-speech codes for ZH).
        Used by CollocationClassifier.get_pos_pattern().
        """
        ...

    @property
    @abstractmethod
    def language_id(self) -> int:
        """Return the integer language_id for this tokenizer."""
        ...

    @property
    @abstractmethod
    def join_char(self) -> str:
        """
        Character used to join n-gram tokens into a display string.
        English/Japanese: ' ' (space). Chinese: '' (empty, no spaces).
        """
        ...

    @abstractmethod
    def extract_named_entities(self, text: str) -> set[str]:
        """
        Return surface forms of named entities (people, places, organisations)
        found in the text. Used to filter proper-noun collocations like
        company names ('东吴证券') and place names ('成渝地区').
        """
        ...

    @abstractmethod
    def extract_dependency_pairs(self, text: str) -> list[tuple[str, str, str]]:
        """
        Extract syntactically related word pairs from a dependency parse.
        Returns list of (head_word, dependent_word, dep_relation) triples.
        """
        ...

    @abstractmethod
    def split_sentences(self, text: str) -> list[str]:
        """Split text into sentence strings using language-appropriate boundaries."""
        ...

    def tokenize_doc(self, text: str):
        """
        Return the raw NLP document object (e.g. spaCy Doc) for single-pass parsing.
        Style analysis calls this once and reuses the Doc across feature extractors.
        Returns None for tokenizers without a full NLP pipeline (e.g. jieba).
        """
        return None


class EnglishTokenizer(LanguageTokenizer):

    @property
    def language_id(self) -> int:
        return 2

    @property
    def join_char(self) -> str:
        return ' '

    def tokenize(self, text: str) -> list[str]:
        """
        Returns lowercase alphabetic tokens, stop words removed, len > 1.
        """
        doc = _get_nlp_en()(text)
        return [
            token.lower_ for token in doc
            if not token.is_stop
            and not token.is_punct
            and not token.is_space
            and token.is_alpha
            and len(token.text) > 1
        ]

    def tokenize_with_pos(self, text: str) -> list[tuple[str, str]]:
        """
        Returns (lowercase_token, spaCy_POS) for all non-space, non-punct tokens.
        Stop words are RETAINED here so POS patterns for discourse markers
        (e.g. 'in other words' -> PREP+DET+NOUN) are computed correctly.
        """
        doc = _get_nlp_en()(text)
        return [
            (token.lower_, token.pos_)
            for token in doc
            if not token.is_space and not token.is_punct
        ]

    def extract_named_entities(self, text: str) -> set[str]:
        _SKIP_LABELS = {'PERSON', 'ORG', 'GPE', 'LOC', 'FAC', 'NORP', 'PRODUCT'}
        doc = _get_nlp_en()(text)
        return {ent.text.lower() for ent in doc.ents if ent.label_ in _SKIP_LABELS}

    COLLOCATION_DEPS = {'dobj', 'nsubj', 'amod', 'compound', 'nmod', 'advmod', 'attr'}

    def extract_dependency_pairs(self, text: str) -> list[tuple[str, str, str]]:
        doc = _get_nlp_en()(text)
        pairs = []
        for token in doc:
            if token.dep_ in self.COLLOCATION_DEPS and not token.is_stop and not token.is_punct:
                head = token.head.lower_
                dep = token.lower_
                if len(head) > 1 and len(dep) > 1 and head != dep:
                    pairs.append((head, dep, token.dep_))
        return pairs

    def split_sentences(self, text: str) -> list[str]:
        parts = re.split(r'(?<=[.!?])\s+', text)
        return [p.strip() for p in parts if p.strip()]

    def tokenize_doc(self, text: str):
        """Return spaCy Doc for single-pass parsing."""
        return _get_nlp_en()(text)


class ChineseTokenizer(LanguageTokenizer):

    @property
    def language_id(self) -> int:
        return 1

    @property
    def join_char(self) -> str:
        return ''

    @staticmethod
    def _is_numeric(t: str) -> bool:
        """Check if token is entirely numeric (digits, decimal points, commas)."""
        return all(c in '0123456789０１２３４５６７８９.,，。、％%' for c in t)

    def tokenize(self, text: str) -> list[str]:
        """
        Segment Chinese text with jieba (precise mode).
        Filters whitespace-only tokens, single-character tokens, and numbers.
        """
        import jieba
        return [
            t for t in jieba.cut(text, cut_all=False)
            if t.strip() and len(t) > 1 and not self._is_numeric(t)
        ]

    def tokenize_with_pos(self, text: str) -> list[tuple[str, str]]:
        """
        Segment and tag with jieba.posseg.
        Returns (word, jieba_flag) pairs, whitespace and numbers filtered.
        """
        import jieba.posseg as pseg
        return [
            (word, flag)
            for word, flag in pseg.cut(text)
            if word.strip() and len(word) > 1 and not self._is_numeric(word)
        ]

    def extract_named_entities(self, text: str) -> set[str]:
        """
        Extract named entities using jieba POS tags.
        Only nr (person) and nt (organisation) are used — ns (place) and
        nz (other proper noun) are too noisy in jieba and flag common
        words like 上山, 东西, 乌云 as place names.
        """
        import jieba.posseg as pseg
        _NER_TAGS = {'nr', 'nrt', 'nt'}
        return {word for word, flag in pseg.cut(text) if flag in _NER_TAGS and len(word) > 1}

    def extract_dependency_pairs(self, text: str) -> list[tuple[str, str, str]]:
        return []  # jieba has no dependency parser; use n-gram extraction only

    def split_sentences(self, text: str) -> list[str]:
        parts = re.split(r'[。！？；…]+', text)
        return [p.strip() for p in parts if p.strip()]

    # ChineseTokenizer uses jieba which has no Doc object — inherits base None


class JapaneseTokenizer(LanguageTokenizer):
    """
    spaCy-backed tokenizer for Japanese corpus analysis.
    NOTE: The vocabulary pipeline (services/vocabulary/processors/japanese.py)
    uses fugashi+UniDic for lemmatization. This tokenizer uses spaCy ja_core_news_sm
    because CollocationClassifier requires Universal Dependencies POS tags.
    """

    @property
    def language_id(self) -> int:
        return 3

    @property
    def join_char(self) -> str:
        return ' '

    def tokenize(self, text: str) -> list[str]:
        """
        Tokenize Japanese text via spaCy ja_core_news_sm.
        Removes punctuation, whitespace, and numeric tokens.
        """
        doc = _get_nlp_ja()(text)
        return [
            token.text for token in doc
            if not token.is_space and not token.is_punct and not token.like_num
        ]

    def tokenize_with_pos(self, text: str) -> list[tuple[str, str]]:
        """
        Returns (surface_form, spaCy_POS) for all non-space, non-punct, non-numeric tokens.
        """
        doc = _get_nlp_ja()(text)
        return [
            (token.text, token.pos_)
            for token in doc
            if not token.is_space and not token.is_punct and not token.like_num
        ]

    def extract_named_entities(self, text: str) -> set[str]:
        _SKIP_LABELS = {'PERSON', 'ORG', 'GPE', 'LOC', 'FAC', 'NORP', 'PRODUCT'}
        doc = _get_nlp_ja()(text)
        return {ent.text for ent in doc.ents if ent.label_ in _SKIP_LABELS}

    COLLOCATION_DEPS = {'obj', 'nsubj', 'amod', 'compound', 'nmod', 'advmod', 'obl'}

    def extract_dependency_pairs(self, text: str) -> list[tuple[str, str, str]]:
        doc = _get_nlp_ja()(text)
        pairs = []
        for token in doc:
            if token.dep_ in self.COLLOCATION_DEPS and not token.is_punct:
                head = token.head.text
                dep = token.text
                if len(head) > 1 and len(dep) > 1 and head != dep:
                    pairs.append((head, dep, token.dep_))
        return pairs

    def split_sentences(self, text: str) -> list[str]:
        parts = re.split(r'[。！？]+', text)
        return [p.strip() for p in parts if p.strip()]

    def tokenize_doc(self, text: str):
        """Return spaCy Doc for single-pass parsing."""
        return _get_nlp_ja()(text)


def get_tokenizer(language_id: int) -> LanguageTokenizer:
    """
    Return the appropriate LanguageTokenizer subclass instance for a language.
    Args:
        language_id: Integer from dim_languages (1=ZH, 2=EN, 3=JA).
    Raises:
        ValueError: If language_id is not supported.
    """
    _registry = {
        1: ChineseTokenizer,
        2: EnglishTokenizer,
        3: JapaneseTokenizer,
    }
    cls = _registry.get(language_id)
    if cls is None:
        raise ValueError(f"No tokenizer registered for language_id={language_id}")
    return cls()
