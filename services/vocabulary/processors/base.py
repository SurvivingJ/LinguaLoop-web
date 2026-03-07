"""
Abstract base class for language processors.

Each language (English, Chinese, Japanese) has its own processor
that handles tokenization, segmentation, and lemmatization.

Phrase detection and replacement are handled by the pipeline layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LemmaToken:
    """
    A single extracted token with metadata.

    Stop words are retained so phrase detection can find multi-word
    expressions like "look forward TO". Filtering happens later
    in the pipeline.
    """
    index: int
    surface: str
    lemma: str
    pos: str
    is_stop: bool
    is_content: bool


class BaseLanguageProcessor(ABC):
    """
    Abstract base for all language processors.

    Subclasses must implement:
        - extract_lemma_tokens(): tokenize and lemmatize text
        - tokenize_full(): full tokenization for display (token map)
        - is_ready(): health check for required NLP models
    """

    @abstractmethod
    def extract_lemma_tokens(self, text: str) -> list[LemmaToken]:
        """
        Tokenize and lemmatize the input text.

        Returns ALL tokens (including stop words and punctuation).
        The pipeline filters them after phrase detection.

        Args:
            text: Raw input text

        Returns:
            List of LemmaToken objects in document order
        """
        ...

    @abstractmethod
    def tokenize_full(self, text: str) -> list[tuple[str, str, bool]]:
        """
        Full tokenization for building vocab token maps.

        Unlike extract_lemma_tokens(), this includes ALL characters
        (whitespace, punctuation) so that concatenating display texts
        reproduces the original transcript exactly.

        Args:
            text: Raw input text

        Returns:
            List of (display_text, lemma, is_content) tuples.
            display_text includes trailing whitespace where applicable.
        """
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """
        Health check: are all required NLP models available?

        Returns:
            True if processor can handle requests
        """
        ...
