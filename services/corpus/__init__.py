"""
services.corpus
~~~~~~~~~~~~~~~
Corpus analysis pipeline for LinguaLoop.

Primary public classes:
    CorpusIngestionService  — ingest URLs, pasted text, or author corpora
    CollocationPackService  — create and manage collocation packs
    CorpusAnalyzer          — statistical n-gram scoring (PMI, G², T-Score)
    CollocationClassifier   — classify and tag collocations
    get_tokenizer           — factory for LanguageTokenizer subclasses
"""

from services.corpus.tokenizers import (
    LanguageTokenizer,
    EnglishTokenizer,
    ChineseTokenizer,
    JapaneseTokenizer,
    get_tokenizer,
)
from services.corpus.analyzer import CorpusAnalyzer
from services.corpus.classifier import CollocationClassifier
from services.corpus.ingestion import CorpusIngestionService
from services.corpus.pack_service import CollocationPackService
from services.corpus.verifier import substitution_entropy, is_worth_keeping

__all__ = [
    'LanguageTokenizer',
    'EnglishTokenizer',
    'ChineseTokenizer',
    'JapaneseTokenizer',
    'get_tokenizer',
    'CorpusAnalyzer',
    'CollocationClassifier',
    'CorpusIngestionService',
    'CollocationPackService',
    'substitution_entropy',
    'is_worth_keeping',
]
