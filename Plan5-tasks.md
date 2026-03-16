# Plan 5: Corpus Analysis Pipeline — Developer Task List

## Overview

This plan implements a fully statistical corpus analysis pipeline that extracts collocations, fixed phrases, and discourse markers from real texts without LLM involvement. The system ingests URLs, pasted text, and public-domain author corpora; computes PMI, G², and T-Score for every successive n-gram combination (sizes 2–5); classifies results; and packages them into user-facing collocation packs.

**Architecture summary:**
- `LanguageTokenizer` base class with per-language subclasses (`EnglishTokenizer`, `ChineseTokenizer`, `JapaneseTokenizer`) — adding a new language requires only a new subclass
- `CorpusAnalyzer` — all statistical computation (PMI, G², T-Score, n-gram extraction)
- `CollocationClassifier` — discourse marker / fixed phrase / collocation classification with per-language marker sets
- `CorpusIngestionService` — URL fetching, text ingestion, author batch ingestion, pipeline orchestration
- `CollocationPackService` — pack creation, user selection
- `routes/corpus.py` — Flask API endpoints (admin-gated ingest, public pack browsing, pack selection)

**Key constraint:** All statistical computation is Python. SQL does the heavy lifting for aggregation, deduplication, and cross-source queries. No LLM is used anywhere in this pipeline.

**DB tables (defined in Plan 2 migrations):** `corpus_sources`, `corpus_collocations`, `collocation_packs`, `pack_collocations`, `user_pack_selections`

**Language IDs:** Chinese = 1, English = 2, Japanese = 3

---

## Phase 1 — Language Tokenizer Layer

### Task 1.1 — Create `services/corpus/tokenizers.py`

**What to build:** A base tokenizer class and three concrete subclasses. This is the abstraction boundary that makes the system extensible — adding Korean, French, etc. requires only a new subclass. All tokenizers expose identical public interfaces so `CorpusAnalyzer` never branches on language.

**File:** `services/corpus/tokenizers.py`

```python
import re
import spacy
from abc import ABC, abstractmethod

# Module-level model loading (do once at import time, not per call)
_nlp_en = None
_nlp_ja = None

def _get_nlp_en():
    global _nlp_en
    if _nlp_en is None:
        _nlp_en = spacy.load("en_core_web_sm")
    return _nlp_en

def _get_nlp_ja():
    global _nlp_ja
    if _nlp_ja is None:
        _nlp_ja = spacy.load("ja_core_news_sm")
    return _nlp_ja
```

---

#### Class: `LanguageTokenizer` (abstract base)

**Purpose:** Define the interface all tokenizers must satisfy. Enforces that every subclass provides both plain tokenization and POS-tagged tokenization.

```python
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
```

---

#### Class: `EnglishTokenizer`

**Purpose:** spaCy-backed tokenizer for English. Removes stop words, punctuation, and single-character tokens for the plain `tokenize()` path. The `tokenize_with_pos()` path retains all non-whitespace tokens (including stop words) so that POS patterns for phrases like "in other words" are accurate.

```python
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
        Args:
            text: Raw input string.
        Returns:
            list[str]: Filtered lowercase tokens for statistical analysis.
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
        (e.g. 'in other words' → PREP+DET+NOUN) are computed correctly.
        Args:
            text: Raw input string.
        Returns:
            list[tuple[str, str]]: (token, POS_tag) pairs.
        """
        doc = _get_nlp_en()(text)
        return [
            (token.lower_, token.pos_)
            for token in doc
            if not token.is_space and not token.is_punct
        ]
```

---

#### Class: `ChineseTokenizer`

**Purpose:** jieba-backed tokenizer for Mandarin Chinese. jieba provides word segmentation (no spaces in source text). For POS tagging, uses `jieba.posseg`. Tokens shorter than 2 characters are filtered (single hanzi are usually too ambiguous).

```python
class ChineseTokenizer(LanguageTokenizer):

    @property
    def language_id(self) -> int:
        return 1

    @property
    def join_char(self) -> str:
        return ''  # Chinese text has no spaces between words

    def tokenize(self, text: str) -> list[str]:
        """
        Segment Chinese text with jieba (precise mode).
        Filters whitespace-only tokens and single-character tokens.
        Args:
            text: Raw Chinese input string.
        Returns:
            list[str]: Segmented word tokens.
        """
        import jieba
        return [
            t for t in jieba.cut(text, cut_all=False)
            if t.strip() and len(t) > 1
        ]

    def tokenize_with_pos(self, text: str) -> list[tuple[str, str]]:
        """
        Segment and tag with jieba.posseg.
        Returns (word, jieba_flag) pairs, whitespace filtered.
        Args:
            text: Raw Chinese input string.
        Returns:
            list[tuple[str, str]]: (word, jieba_pos_flag) pairs.
        """
        import jieba.posseg as pseg
        return [
            (word, flag)
            for word, flag in pseg.cut(text)
            if word.strip() and len(word) > 1
        ]
```

---

#### Class: `JapaneseTokenizer`

**Purpose:** spaCy `ja_core_news_sm`-backed tokenizer for Japanese. Japanese has no spaces; spaCy handles segmentation. Punctuation and space tokens are removed; no stop-word removal (Japanese stop-word lists are less reliable).

```python
class JapaneseTokenizer(LanguageTokenizer):

    @property
    def language_id(self) -> int:
        return 3

    @property
    def join_char(self) -> str:
        return ' '  # Use space in stored collocation_text for readability

    def tokenize(self, text: str) -> list[str]:
        """
        Tokenize Japanese text via spaCy ja_core_news_sm.
        Removes punctuation and whitespace tokens; retains all content tokens.
        Args:
            text: Raw Japanese input string.
        Returns:
            list[str]: Segmented surface-form tokens.
        """
        doc = _get_nlp_ja()(text)
        return [
            token.text for token in doc
            if not token.is_space and not token.is_punct
        ]

    def tokenize_with_pos(self, text: str) -> list[tuple[str, str]]:
        """
        Returns (surface_form, spaCy_POS) for all non-space, non-punct tokens.
        Args:
            text: Raw Japanese input string.
        Returns:
            list[tuple[str, str]]: (token, POS_tag) pairs.
        """
        doc = _get_nlp_ja()(text)
        return [
            (token.text, token.pos_)
            for token in doc
            if not token.is_space and not token.is_punct
        ]
```

---

#### Factory function: `get_tokenizer`

**Purpose:** Single call-site for obtaining the correct tokenizer by language_id. Keeps all language-branching logic in one place.

```python
def get_tokenizer(language_id: int) -> LanguageTokenizer:
    """
    Return the appropriate LanguageTokenizer subclass instance for a language.
    Args:
        language_id: Integer from dim_languages (1=ZH, 2=EN, 3=JA).
    Returns:
        LanguageTokenizer: Concrete tokenizer instance.
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
```

**Dependencies:** None (standalone module)

---

## Phase 2 — Statistical Analysis Engine

### Task 2.1 — Create `services/corpus/analyzer.py`

**What to build:** `CorpusAnalyzer` encapsulates all statistical computation. It receives a tokenizer at construction (dependency injection), so the same class works for all languages. Methods are sized to be independently testable — no 1-liners, each method does a coherent unit of work.

**File:** `services/corpus/analyzer.py`

```python
import math
from collections import Counter
from typing import Iterator
from services.corpus.tokenizers import LanguageTokenizer
```

---

#### Class: `CorpusAnalyzer`

```python
class CorpusAnalyzer:
    """
    Statistical corpus analysis engine.
    Language-agnostic: receives a LanguageTokenizer at init.
    All n-gram extraction covers ALL combinations of successive words
    (sizes 2–5), not just linguistically motivated segments.
    This captures phrases like 'in other words', 'as a result of', etc.
    """

    # Scoring thresholds as class-level constants for easy tuning
    MIN_FREQUENCY        = 5
    PMI_THRESHOLD_BIGRAM = 3.0
    PMI_THRESHOLD_LONGER = 2.0
    LL_THRESHOLD         = 10.83   # p < 0.001 chi-squared
    T_SCORE_THRESHOLD    = 2.0

    def __init__(self, tokenizer: LanguageTokenizer):
        """
        Args:
            tokenizer: A LanguageTokenizer instance (EnglishTokenizer, etc.).
        """
        self.tokenizer = tokenizer
```

---

##### Method: `generate_ngrams`

**Purpose:** Low-level generator producing all successive n-grams from a token list. This is the core extraction — every contiguous sequence of n tokens is yielded, which is how "in other words" and similar short fixed phrases are captured regardless of their grammatical category.

```python
    def generate_ngrams(self, tokens: list[str], n: int) -> Iterator[tuple]:
        """
        Yield all successive n-grams from a token list as tuples.
        A successive n-gram is every contiguous window of length n.
        Example: ['a','b','c','d'], n=2 → ('a','b'), ('b','c'), ('c','d')
        Args:
            tokens: Flat list of string tokens.
            n:      N-gram size (must be >= 1).
        Yields:
            tuple: Each n-gram as an n-tuple of strings.
        """
        for i in range(len(tokens) - n + 1):
            yield tuple(tokens[i : i + n])
```

---

##### Method: `extract_all_ngrams`

**Purpose:** Full extraction pass over a text. Tokenizes once, then extracts and counts n-grams of sizes 1 through `max_n` in a single pass. Returns a dict keyed by n so callers can access unigram counts (for statistical denominators) and multi-gram counts together.

```python
    def extract_all_ngrams(
        self,
        text: str,
        max_n: int = 5
    ) -> dict[int, Counter]:
        """
        Tokenize text and count all n-grams from size 1 to max_n.
        Size 1 (unigrams) is always included — required as denominators
        for PMI/G²/T-score computation on larger n-grams.
        Args:
            text:  Raw input text string.
            max_n: Maximum n-gram size to extract (default 5).
        Returns:
            dict[int, Counter]: {n: Counter({ngram_tuple: count})}
            e.g. {1: Counter({('word',): 5, ...}), 2: Counter({('a','b'): 3, ...})}
        """
        tokens = self.tokenizer.tokenize(text)
        return {
            n: Counter(self.generate_ngrams(tokens, n))
            for n in range(1, max_n + 1)
        }
```

---

##### Method: `compute_pmi`

**Purpose:** Compute Pointwise Mutual Information for a bigram. PMI measures how much more (or less) a word pair co-occurs compared to what would be expected if they were independent. PMI = 0 → independence; PMI > 0 → positive association; PMI ≥ 3.0 is the bigram significance threshold.

```
Formula:
    PMI(w₁, w₂) = log₂( P(w₁,w₂) / (P(w₁) × P(w₂)) )
                = log₂( C(w₁,w₂) × N / (C(w₁) × C(w₂)) )
```

```python
    def compute_pmi(
        self,
        bigram: tuple[str, str],
        bigram_count: int,
        unigram_counts: Counter,
        total_tokens: int
    ) -> float:
        """
        Compute PMI for a bigram (w₁, w₂).
        Returns 0.0 if either word count is zero or probabilities are invalid.
        Args:
            bigram:         (w₁, w₂) token pair.
            bigram_count:   C(w₁, w₂) — observed co-occurrence count.
            unigram_counts: Counter of all unigrams in the corpus.
            total_tokens:   N — total token count.
        Returns:
            float: PMI score (log₂ scale). Can be negative for repulsion.
        """
        w1, w2 = bigram
        c_w1 = unigram_counts.get((w1,), 0) or unigram_counts.get(w1, 0)
        c_w2 = unigram_counts.get((w2,), 0) or unigram_counts.get(w2, 0)

        if c_w1 == 0 or c_w2 == 0 or total_tokens == 0:
            return 0.0

        p_bigram = bigram_count / total_tokens
        p_w1     = c_w1 / total_tokens
        p_w2     = c_w2 / total_tokens

        try:
            return math.log2(p_bigram / (p_w1 * p_w2))
        except (ValueError, ZeroDivisionError):
            return 0.0
```

---

##### Method: `compute_log_likelihood`

**Purpose:** Compute G² (log-likelihood ratio) for a bigram using a 2×2 contingency table. More reliable than PMI for lower-frequency items because it accounts for the full distribution. Threshold: G² ≥ 10.83 ≈ p < 0.001.

```
Formula:
    G² = 2 × Σ Oᵢⱼ × log(Oᵢⱼ / Eᵢⱼ)
    
    Contingency cells:
        O₁₁ = C(w₁,w₂)           E₁₁ = C(w₁)×C(w₂)/N
        O₁₂ = C(w₁) - O₁₁        E₁₂ = C(w₁)×(N-C(w₂))/N
        O₂₁ = C(w₂) - O₁₁        E₂₁ = (N-C(w₁))×C(w₂)/N
        O₂₂ = N - C(w₁) - C(w₂) + O₁₁   E₂₂ = (N-C(w₁))×(N-C(w₂))/N
```

```python
    def compute_log_likelihood(
        self,
        bigram_count: int,
        c_w1: int,
        c_w2: int,
        total_tokens: int
    ) -> float:
        """
        Compute G² (log-likelihood ratio) for a bigram.
        Uses a 2×2 contingency table: (w₁ present/absent) × (w₂ present/absent).
        Returns 0.0 if any cell has non-positive observed or expected count.
        Args:
            bigram_count:  O₁₁ — observed co-occurrence count C(w₁,w₂).
            c_w1:          C(w₁) — total count of w₁ in corpus.
            c_w2:          C(w₂) — total count of w₂ in corpus.
            total_tokens:  N — total token count.
        Returns:
            float: G² score (always non-negative). Higher = stronger association.
        """
        if total_tokens == 0:
            return 0.0

        O11 = bigram_count
        O12 = c_w1 - O11
        O21 = c_w2 - O11
        O22 = total_tokens - c_w1 - c_w2 + O11

        E11 = c_w1 * c_w2 / total_tokens
        E12 = c_w1 * (total_tokens - c_w2) / total_tokens
        E21 = (total_tokens - c_w1) * c_w2 / total_tokens
        E22 = (total_tokens - c_w1) * (total_tokens - c_w2) / total_tokens

        def safe_cell(O: float, E: float) -> float:
            if O <= 0 or E <= 0:
                return 0.0
            return O * math.log(O / E)

        return 2.0 * (
            safe_cell(O11, E11) +
            safe_cell(O12, E12) +
            safe_cell(O21, E21) +
            safe_cell(O22, E22)
        )
```

---

##### Method: `compute_t_score`

**Purpose:** Compute T-Score for a bigram. T-Score uses the normal approximation to the Poisson distribution. Less sensitive than G² for rare pairs but widely used in lexicography. Threshold: T ≥ 2.0.

```
Formula:
    t = (C(w₁,w₂) - E₁₁) / √C(w₁,w₂)
    where E₁₁ = C(w₁) × C(w₂) / N
```

```python
    def compute_t_score(
        self,
        bigram_count: int,
        c_w1: int,
        c_w2: int,
        total_tokens: int
    ) -> float:
        """
        Compute T-Score for a bigram.
        Returns 0.0 if bigram_count is zero or total_tokens is zero.
        Args:
            bigram_count:  C(w₁,w₂) — observed co-occurrence count.
            c_w1:          C(w₁) — total count of w₁.
            c_w2:          C(w₂) — total count of w₂.
            total_tokens:  N — total token count.
        Returns:
            float: T-Score. Values ≥ 2.0 indicate significance.
        """
        if bigram_count <= 0 or total_tokens == 0:
            return 0.0
        E11 = c_w1 * c_w2 / total_tokens
        return (bigram_count - E11) / math.sqrt(bigram_count)
```

---

##### Method: `_score_bigram`

**Purpose:** Internal helper that computes all three statistics (PMI, G², T-Score) for a single bigram in one call. Grouped here so the `score_ngrams` loop stays readable. Not intended for external callers.

```python
    def _score_bigram(
        self,
        bigram: tuple[str, str],
        bigram_count: int,
        unigram_counts: Counter,
        total_tokens: int
    ) -> tuple[float, float, float]:
        """
        Compute PMI, G², and T-Score for a single bigram.
        Args:
            bigram:         (w₁, w₂) tuple.
            bigram_count:   C(w₁, w₂).
            unigram_counts: Counter of unigrams (keyed as 1-tuples if from
                            extract_all_ngrams, or plain strings).
            total_tokens:   N.
        Returns:
            tuple[float, float, float]: (pmi, log_likelihood, t_score)
        """
        w1, w2 = bigram
        # Normalise unigram_counts key format: support both ('w',) and 'w'
        c_w1 = unigram_counts.get((w1,), unigram_counts.get(w1, 0))
        c_w2 = unigram_counts.get((w2,), unigram_counts.get(w2, 0))

        pmi = self.compute_pmi(bigram, bigram_count, unigram_counts, total_tokens)
        ll  = self.compute_log_likelihood(bigram_count, c_w1, c_w2, total_tokens)
        t   = self.compute_t_score(bigram_count, c_w1, c_w2, total_tokens)
        return pmi, ll, t
```

---

##### Method: `_average_pmi_for_ngram`

**Purpose:** For n-grams longer than 2 tokens, compute the average PMI across all consecutive bigram pairs within the n-gram. This is the extension of PMI to longer sequences and is what allows the system to score 3–5-grams like "as a result of" by averaging PMI("as","a") + PMI("a","result") + PMI("result","of").

```python
    def _average_pmi_for_ngram(
        self,
        ngram: tuple,
        bigram_counts: Counter,
        unigram_counts: Counter,
        total_tokens: int
    ) -> float:
        """
        Compute the average PMI across all consecutive bigram windows in an n-gram.
        Used for n-grams of size 3–5 where G²/T-Score are not directly applicable.
        Args:
            ngram:          n-tuple of tokens (len >= 3).
            bigram_counts:  Counter of all bigram tuples in the corpus.
            unigram_counts: Counter of unigrams.
            total_tokens:   N.
        Returns:
            float: Mean PMI across (len(ngram)-1) consecutive bigram pairs.
                   Returns 0.0 if no pairs can be scored.
        """
        pmi_values = []
        for i in range(len(ngram) - 1):
            bigram = (ngram[i], ngram[i + 1])
            b_count = bigram_counts.get(bigram, 0)
            pmi = self.compute_pmi(bigram, b_count, unigram_counts, total_tokens)
            pmi_values.append(pmi)
        return sum(pmi_values) / len(pmi_values) if pmi_values else 0.0
```

---

##### Method: `score_ngrams`

**Purpose:** The full analysis pipeline for a text. Calls `extract_all_ngrams`, applies frequency pre-filter, computes statistics for each n-gram, applies PMI threshold, and returns a list of collocation dicts ready for DB insertion. This is the method called by `CorpusIngestionService._run_pipeline`.

```python
    def score_ngrams(
        self,
        text: str,
        min_frequency: int = MIN_FREQUENCY,
        pmi_threshold_bigram: float = PMI_THRESHOLD_BIGRAM,
        pmi_threshold_longer: float = PMI_THRESHOLD_LONGER
    ) -> list[dict]:
        """
        Full pipeline: extract all successive n-grams (sizes 2–5), apply
        frequency filter, compute PMI/G²/T-Score, apply PMI threshold.
        Does NOT perform classification (caller uses CollocationClassifier).
        Args:
            text:                  Raw input text.
            min_frequency:         Minimum occurrence count to consider (default 5).
            pmi_threshold_bigram:  Minimum PMI for bigrams (default 3.0).
            pmi_threshold_longer:  Minimum avg PMI for 3–5-grams (default 2.0).
        Returns:
            list[dict]: Each dict has keys:
                collocation_text  (str)   — space/empty joined n-gram
                n_gram_size       (int)
                frequency         (int)
                pmi_score         (float, 4dp)
                log_likelihood    (float, 4dp)  — 0.0 for n>2
                t_score           (float, 4dp)  — 0.0 for n>2
        """
        ngrams_by_size = self.extract_all_ngrams(text, max_n=5)
        unigram_counts = ngrams_by_size[1]
        total_tokens   = sum(unigram_counts.values())
        bigram_counts  = ngrams_by_size[2]
        join_char      = self.tokenizer.join_char

        results = []

        for n in range(2, 6):
            pmi_threshold = pmi_threshold_bigram if n == 2 else pmi_threshold_longer
            for ngram, freq in ngrams_by_size[n].items():
                if freq < min_frequency:
                    continue

                if n == 2:
                    pmi, ll, t = self._score_bigram(
                        ngram, freq, unigram_counts, total_tokens
                    )
                else:
                    pmi = self._average_pmi_for_ngram(
                        ngram, bigram_counts, unigram_counts, total_tokens
                    )
                    ll, t = 0.0, 0.0

                if pmi < pmi_threshold:
                    continue

                results.append({
                    'collocation_text': join_char.join(ngram),
                    'n_gram_size':      n,
                    'frequency':        freq,
                    'pmi_score':        round(pmi, 4),
                    'log_likelihood':   round(ll, 4),
                    't_score':          round(t, 4),
                })

        return results
```

**Dependencies:** Task 1.1 (`LanguageTokenizer`, `get_tokenizer`)

---

## Phase 3 — Collocation Classifier

### Task 3.1 — Create `services/corpus/classifier.py`

**What to build:** `CollocationClassifier` handles classification logic: discourse marker detection (with per-language sets), fixed phrase detection (very high PMI), and POS pattern generation. The marker sets are class-level constants, making it easy to extend per language.

**File:** `services/corpus/classifier.py`

```python
from services.corpus.tokenizers import LanguageTokenizer, _get_nlp_en, _get_nlp_ja
```

---

#### Class: `CollocationClassifier`

```python
class CollocationClassifier:
    """
    Classify scored n-grams and extract POS patterns.
    One instance per LanguageTokenizer — the tokenizer provides the
    language_id and POS tagging method.
    """

    # English discourse markers — multi-word expressions used as connectives,
    # discourse organizers, or prepositional phrases. Extend this set as needed.
    DISCOURSE_MARKERS_EN: frozenset = frozenset({
        'in other words', 'as a result of', 'on the other hand', 'in addition to',
        'as well as', 'due to the fact', 'in spite of', 'with regard to',
        'in terms of', 'as far as', 'in the meantime', 'for the time being',
        'first of all', 'last but not least', 'in conclusion', 'to sum up',
        'for example', 'for instance', 'in particular', 'on the contrary',
        'at the same time', 'more often than not', 'as a consequence of',
        'in order to', 'with respect to', 'on the basis of', 'as a matter of fact',
        'in the event that', 'as long as', 'on account of', 'by means of',
        'with the exception of', 'in the case of', 'in the light of',
    })

    # Chinese discourse markers (simplified Chinese)
    DISCOURSE_MARKERS_ZH: frozenset = frozenset({
        '换句话说', '另一方面', '除此之外', '总而言之', '与此同时',
        '尽管如此', '事实上', '从某种意义上说', '比如说', '例如',
    })

    # Japanese discourse markers
    DISCOURSE_MARKERS_JA: frozenset = frozenset({
        'つまり', 'そのため', 'したがって', 'それに対して', 'その一方で',
        'さらに', '例えば', '具体的には', 'とはいえ', 'にもかかわらず',
    })

    # PMI threshold above which a collocation is treated as a frozen/fixed phrase
    FIXED_PHRASE_PMI_THRESHOLD: float = 6.0

    # Prepositions whose presence at the start of a 3+-gram suggests discourse use
    DISCOURSE_LEADING_PREPS_EN: frozenset = frozenset({
        'in', 'on', 'at', 'as', 'by', 'for', 'of', 'to', 'with',
        'from', 'into', 'over', 'under', 'about', 'through',
    })

    # Coarse POS mapping: spaCy fine tags → simplified pattern labels
    COARSE_POS_MAP: dict = {
        'NOUN': 'NOUN', 'PROPN': 'NOUN', 'VERB': 'VERB', 'AUX': 'VERB',
        'ADJ': 'ADJ', 'ADV': 'ADV', 'ADP': 'PREP', 'DET': 'DET',
        'CONJ': 'CONJ', 'CCONJ': 'CONJ', 'SCONJ': 'CONJ',
        'NUM': 'NUM', 'PART': 'PART', 'PRON': 'PRON',
    }

    def __init__(self, tokenizer: LanguageTokenizer):
        """
        Args:
            tokenizer: The LanguageTokenizer for the corpus being classified.
                       Used to obtain language_id and POS tagging.
        """
        self.tokenizer = tokenizer
        self._marker_sets = {
            1: self.DISCOURSE_MARKERS_ZH,
            2: self.DISCOURSE_MARKERS_EN,
            3: self.DISCOURSE_MARKERS_JA,
        }
```

---

##### Method: `classify_collocation`

**Purpose:** Assign one of three type labels to a scored n-gram. Checks discourse marker set first (exact match on normalised text), then checks preposition-led heuristic for English 3+-grams, then applies fixed-phrase PMI threshold, and defaults to 'collocation'. Type labels are stored in `corpus_collocations.collocation_type`.

```python
    def classify_collocation(
        self,
        text: str,
        pmi: float,
        frequency: int,
        n: int
    ) -> str:
        """
        Classify an n-gram into one of three types:
          'discourse_marker' — known multi-word connective or prepositional phrase
          'fixed_phrase'     — very high PMI; essentially frozen expression
          'collocation'      — statistically significant but compositional

        Classification priority: discourse_marker > fixed_phrase > collocation.

        Args:
            text:      The n-gram display string (space-joined for EN/JA,
                       no-space for ZH).
            pmi:       PMI score (or average PMI for n > 2).
            frequency: Observed frequency of the n-gram.
            n:         N-gram size.
        Returns:
            str: One of 'discourse_marker', 'fixed_phrase', 'collocation'.
        """
        lang_id = self.tokenizer.language_id
        marker_set = self._marker_sets.get(lang_id, frozenset())

        normalised = text.lower().strip()
        if normalised in marker_set:
            return 'discourse_marker'

        # English heuristic: 3+-gram starting with a preposition likely
        # functions as a discourse marker even if not in the explicit set
        if lang_id == 2 and n >= 3:
            first_word = normalised.split()[0] if ' ' in normalised else ''
            if first_word in self.DISCOURSE_LEADING_PREPS_EN:
                return 'discourse_marker'

        if pmi >= self.FIXED_PHRASE_PMI_THRESHOLD:
            return 'fixed_phrase'

        return 'collocation'
```

---

##### Method: `get_pos_pattern`

**Purpose:** Build a simplified POS pattern string for an n-gram (e.g. "PREP+DET+NOUN", "VERB+NOUN"). Stored in `corpus_collocations.pos_pattern` for downstream exercise generation that needs to know the grammatical structure of a phrase. For Chinese, returns 'UNKNOWN' because jieba POS codes require a separate mapping.

```python
    def get_pos_pattern(self, text: str) -> str:
        """
        Return a '+'-separated string of coarse POS tags for the n-gram.
        Examples: 'VERB+NOUN', 'PREP+DET+NOUN', 'ADJ+NOUN', 'DET+NOUN+PREP+NOUN'

        Uses tokenize_with_pos() from the tokenizer, then maps fine tags to
        coarse labels via COARSE_POS_MAP. Unknown tags are passed through as-is.

        For Chinese (language_id=1): returns 'UNKNOWN' — jieba pos flags
        require a separate mapping; extend ChineseTokenizer.get_pos_pattern()
        in a future task if needed.

        Args:
            text: The n-gram display string (as stored in collocation_text).
        Returns:
            str: Coarse POS pattern, e.g. 'PREP+DET+NOUN'. Empty string if
                 no taggable tokens found.
        """
        if self.tokenizer.language_id == 1:
            return 'UNKNOWN'

        pairs = self.tokenizer.tokenize_with_pos(text)
        tags = [
            self.COARSE_POS_MAP.get(pos, pos)
            for _, pos in pairs
            if pos not in ('PUNCT', 'SPACE', 'X', '')
        ]
        return '+'.join(tags)
```

---

##### Method: `classify_and_tag`

**Purpose:** Convenience method that runs both `classify_collocation` and `get_pos_pattern` in a single call, returning a dict. Used by `CorpusAnalyzer.score_ngrams` results enrichment step in the ingestion pipeline.

```python
    def classify_and_tag(
        self,
        text: str,
        pmi: float,
        frequency: int,
        n: int
    ) -> dict:
        """
        Run classify_collocation and get_pos_pattern together.
        Args:
            text:      N-gram display string.
            pmi:       PMI score.
            frequency: Observed frequency.
            n:         N-gram size.
        Returns:
            dict: {'collocation_type': str, 'pos_pattern': str}
        """
        return {
            'collocation_type': self.classify_collocation(text, pmi, frequency, n),
            'pos_pattern':      self.get_pos_pattern(text),
        }
```

**Dependencies:** Task 1.1

---

## Phase 4 — Ingestion Service

### Task 4.1 — Create `services/corpus/ingestion.py`

**What to build:** `CorpusIngestionService` orchestrates the full pipeline from raw input to stored collocations. It composes `CorpusAnalyzer` and `CollocationClassifier` internally. The three public entry points (`ingest_url`, `ingest_text`, `ingest_author_corpus`) all funnel into `_run_pipeline`.

**File:** `services/corpus/ingestion.py`

```python
import re
import httpx
from bs4 import BeautifulSoup
from services.corpus.tokenizers import get_tokenizer
from services.corpus.analyzer import CorpusAnalyzer
from services.corpus.classifier import CollocationClassifier
```

---

#### Class: `CorpusIngestionService`

```python
class CorpusIngestionService:
    """
    Orchestrates ingestion of text from URLs, paste, or author corpora.
    Composes CorpusAnalyzer and CollocationClassifier.
    Uses the Supabase client pattern consistent with the rest of the codebase.
    """

    # Maximum word count stored inline in corpus_sources.raw_text.
    # Texts larger than this have raw_text=NULL and path stored separately.
    INLINE_TEXT_WORD_LIMIT = 50_000

    # HTTP fetch settings
    FETCH_TIMEOUT_SECONDS = 30
    HTTP_HEADERS = {
        'User-Agent': 'LinguaLoop-Corpus-Bot/1.0'
    }

    def __init__(self, db):
        """
        Args:
            db: Supabase client instance (from Flask g or passed directly).
        """
        self.db = db
```

---

##### Method: `ingest_url`

**Purpose:** Public entry point for URL-based ingestion. Fetches the page, strips navigation/ads/boilerplate using BeautifulSoup, extracts the main content block, then delegates to `_run_pipeline`. Returns the new `corpus_source_id`.

```python
    def ingest_url(
        self,
        url: str,
        language_id: int,
        tags: list[str]
    ) -> int:
        """
        Fetch a web page, extract main text, run corpus analysis pipeline.
        Removes <nav>, <footer>, <aside>, <script>, <style>, <header> before
        text extraction. Prefers <article> or <main> over full <body>.

        Args:
            url:         Full URL (must include scheme).
            language_id: Target language (1=ZH, 2=EN, 3=JA).
            tags:        List of tag strings for this source (e.g. ['news', 'economics']).
        Returns:
            int: corpus_source_id of the newly created row.
        Raises:
            httpx.HTTPStatusError: On non-2xx HTTP response.
            ValueError: If no extractable text found.
        """
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=self.FETCH_TIMEOUT_SECONDS,
            headers=self.HTTP_HEADERS
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(['nav', 'footer', 'aside', 'script', 'style', 'header']):
            tag.decompose()

        main = soup.find('article') or soup.find('main') or soup.body
        raw_text = main.get_text(separator=' ', strip=True) if main else soup.get_text()
        raw_text = re.sub(r'\s+', ' ', raw_text).strip()

        if not raw_text:
            raise ValueError(f"No extractable text at URL: {url}")

        title = soup.title.string.strip() if soup.title and soup.title.string else url

        return self._run_pipeline(
            raw_text=raw_text,
            source_type='url',
            source_url=url,
            source_title=title,
            language_id=language_id,
            tags=tags,
        )
```

---

##### Method: `ingest_text`

**Purpose:** Public entry point for pasted/programmatic text ingestion. No HTTP fetch needed. Normalises whitespace and delegates to `_run_pipeline`.

```python
    def ingest_text(
        self,
        text: str,
        title: str,
        language_id: int,
        tags: list[str]
    ) -> int:
        """
        Ingest a plain text string directly (e.g. pasted by admin in UI).
        Args:
            text:        Raw text content.
            title:       Human-readable title for the corpus source.
            language_id: Target language.
            tags:        Tag strings.
        Returns:
            int: corpus_source_id.
        """
        raw_text = re.sub(r'\s+', ' ', text).strip()
        return self._run_pipeline(
            raw_text=raw_text,
            source_type='text',
            source_url=None,
            source_title=title,
            language_id=language_id,
            tags=tags,
        )
```

---

##### Method: `ingest_author_corpus`

**Purpose:** Batch ingest multiple texts from a single public-domain author. Concatenates all texts with double newline separators (preserves sentence boundaries across texts), then runs a single pipeline pass so frequencies are computed across the full author corpus rather than per-text.

```python
    def ingest_author_corpus(
        self,
        author_name: str,
        texts: list[str],
        language_id: int,
        extra_tags: list[str] | None = None
    ) -> int:
        """
        Ingest multiple public-domain texts attributed to one author as a
        single combined corpus source.

        Concatenating before analysis means collocations that appear across
        multiple works (author's idiolect markers) will cross the threshold.

        Args:
            author_name: Author's full name (used as source_title and in tag).
            texts:       List of raw text strings (one per work/chapter/file).
            language_id: Target language.
            extra_tags:  Additional tag strings beyond the auto-generated author tag.
        Returns:
            int: corpus_source_id.
        """
        combined = '\n\n'.join(texts)
        author_slug = author_name.lower().replace(' ', '_')
        tags = [f'author_{author_slug}', 'literature']
        if extra_tags:
            tags.extend(extra_tags)

        return self._run_pipeline(
            raw_text=combined,
            source_type='author',
            source_url=None,
            source_title=author_name,
            language_id=language_id,
            tags=tags,
        )
```

---

##### Method: `_run_pipeline`

**Purpose:** Core pipeline — the single internal method that all three public entry points converge on. Inserts the `corpus_sources` row, runs analysis, enriches results with classification, batch-inserts `corpus_collocations` in chunks of 500, and marks the source as processed.

```python
    def _run_pipeline(
        self,
        raw_text: str,
        source_type: str,
        source_url: str | None,
        source_title: str,
        language_id: int,
        tags: list[str],
    ) -> int:
        """
        Core pipeline: store source → analyse → classify → insert collocations
        → mark processed.

        Chunk size of 500 rows per insert matches Supabase recommended batch size.
        raw_text is stored inline only if word_count < INLINE_TEXT_WORD_LIMIT;
        larger texts have raw_text=NULL and raw_text_path set externally (R2).

        Args:
            raw_text:     Normalised text to analyse.
            source_type:  'url', 'text', or 'author'.
            source_url:   Original URL or None.
            source_title: Display title for the source.
            language_id:  Target language.
            tags:         Tag list.
        Returns:
            int: corpus_source_id of the inserted corpus_sources row.
        """
        word_count = len(raw_text.split())

        # 1. Insert corpus_sources row
        source_result = self.db.table('corpus_sources').insert({
            'source_type':   source_type,
            'source_url':    source_url,
            'source_title':  source_title,
            'language_id':   language_id,
            'tags':          tags,
            'raw_text':      raw_text if word_count < self.INLINE_TEXT_WORD_LIMIT else None,
            'raw_text_path': None,
            'word_count':    word_count,
            'processed_at':  None,
        }).execute()
        corpus_source_id = source_result.data[0]['id']

        # 2. Analyse text
        tokenizer  = get_tokenizer(language_id)
        analyzer   = CorpusAnalyzer(tokenizer)
        classifier = CollocationClassifier(tokenizer)

        scored = analyzer.score_ngrams(raw_text)

        # 3. Enrich with classification
        rows = []
        for item in scored:
            classification = classifier.classify_and_tag(
                text=item['collocation_text'],
                pmi=item['pmi_score'],
                frequency=item['frequency'],
                n=item['n_gram_size'],
            )
            rows.append({
                'corpus_source_id': corpus_source_id,
                'language_id':      language_id,
                'collocation_text': item['collocation_text'],
                'n_gram_size':      item['n_gram_size'],
                'frequency':        item['frequency'],
                'pmi_score':        item['pmi_score'],
                'log_likelihood':   item['log_likelihood'],
                't_score':          item['t_score'],
                'collocation_type': classification['collocation_type'],
                'pos_pattern':      classification['pos_pattern'],
                'tags':             tags,
                'is_validated':     False,
            })

        # 4. Batch insert in chunks of 500
        for i in range(0, len(rows), 500):
            self.db.table('corpus_collocations').insert(rows[i : i + 500]).execute()

        # 5. Mark source as processed
        self.db.table('corpus_sources').update({
            'processed_at': 'NOW()',
        }).eq('id', corpus_source_id).execute()

        return corpus_source_id
```

**Dependencies:** Tasks 1.1, 2.1, 3.1

---

## Phase 5 — Collocation Pack Service

### Task 5.1 — Create `services/corpus/pack_service.py`

**What to build:** `CollocationPackService` wraps all pack CRUD operations. Pack creation pulls the top-N collocations by PMI from a source and links them to the pack. The SQL for ranking and selecting collocations is done database-side for efficiency.

**File:** `services/corpus/pack_service.py`

---

#### Class: `CollocationPackService`

```python
class CollocationPackService:
    """
    Create and manage collocation packs from corpus sources.
    A pack is a curated, user-browsable set of collocations.
    """

    DEFAULT_TOP_N          = 100
    DEFAULT_MIN_PMI        = 3.0

    def __init__(self, db):
        """
        Args:
            db: Supabase client instance.
        """
        self.db = db
```

---

##### Method: `create_pack_from_corpus`

**Purpose:** Materialise a collocation pack from the top-PMI results of a single corpus source. Fetches qualifying collocations via Supabase query (SQL ORDER BY pmi_score DESC, LIMIT top_n), inserts a `collocation_packs` row, then bulk-inserts the `pack_collocations` join rows.

```python
    def create_pack_from_corpus(
        self,
        corpus_source_id: int,
        pack_name: str,
        description: str,
        pack_type: str,
        language_id: int,
        top_n: int = DEFAULT_TOP_N,
        min_pmi: float = DEFAULT_MIN_PMI,
    ) -> int:
        """
        Create a collocation pack from the highest-PMI collocations of a
        corpus source.

        Args:
            corpus_source_id: ID of the processed corpus_sources row.
            pack_name:        Display name (e.g. 'Economics Reporting').
            description:      Short description shown to users.
            pack_type:        One of 'author', 'genre', 'topic'.
            language_id:      Language of the pack.
            top_n:            Number of top collocations to include (default 100).
            min_pmi:          Minimum pmi_score to qualify (default 3.0).
        Returns:
            int: pack_id of the new collocation_packs row.
        Raises:
            ValueError: If no qualifying collocations exist for the source.
        """
        collocations = (
            self.db.table('corpus_collocations')
            .select('id, collocation_text, pmi_score, collocation_type')
            .eq('corpus_source_id', corpus_source_id)
            .gte('pmi_score', min_pmi)
            .order('pmi_score', desc=True)
            .limit(top_n)
            .execute()
        )

        if not collocations.data:
            raise ValueError(
                f"No collocations with pmi >= {min_pmi} "
                f"for corpus_source_id={corpus_source_id}"
            )

        source = (
            self.db.table('corpus_sources')
            .select('tags')
            .eq('id', corpus_source_id)
            .single()
            .execute()
            .data
        )
        tags = source.get('tags', [])

        pack = self.db.table('collocation_packs').insert({
            'pack_name':   pack_name,
            'description': description,
            'language_id': language_id,
            'tags':        tags,
            'source_type': 'corpus',
            'pack_type':   pack_type,
            'total_items': len(collocations.data),
            'is_public':   True,
        }).execute()
        pack_id = pack.data[0]['id']

        joins = [
            {'pack_id': pack_id, 'collocation_id': c['id']}
            for c in collocations.data
        ]
        for i in range(0, len(joins), 500):
            self.db.table('pack_collocations').insert(joins[i : i + 500]).execute()

        return pack_id
```

---

##### Method: `create_cross_source_pack`

**Purpose:** Create a pack that aggregates collocations across multiple corpus sources (e.g. all economics articles = one genre pack). Uses a SQL RPC call to avoid N+1 queries — the DB does the join, deduplication, and ranking in one shot.

```python
    def create_cross_source_pack(
        self,
        source_ids: list[int],
        pack_name: str,
        description: str,
        pack_type: str,
        language_id: int,
        top_n: int = DEFAULT_TOP_N,
        min_pmi: float = DEFAULT_MIN_PMI,
    ) -> int:
        """
        Create a pack from the highest-PMI collocations across multiple sources.
        Uses a Supabase RPC (see SQL below) to aggregate and deduplicate efficiently.

        The RPC returns the top_n distinct collocation_text values by MAX(pmi_score)
        across all supplied corpus_source_ids.

        Args:
            source_ids:   List of corpus_source_id integers to aggregate.
            pack_name:    Display name.
            description:  Description.
            pack_type:    'author', 'genre', or 'topic'.
            language_id:  Language of the pack.
            top_n:        Number of top distinct collocations to include.
            min_pmi:      Minimum pmi_score.
        Returns:
            int: pack_id.
        Raises:
            ValueError: If source_ids is empty or no qualifying collocations found.
        """
        if not source_ids:
            raise ValueError("source_ids must be non-empty")

        result = self.db.rpc(
            'get_top_collocations_for_sources',
            {
                'p_source_ids': source_ids,
                'p_min_pmi':    min_pmi,
                'p_top_n':      top_n,
            }
        ).execute()

        if not result.data:
            raise ValueError("No qualifying collocations found for supplied sources")

        pack = self.db.table('collocation_packs').insert({
            'pack_name':   pack_name,
            'description': description,
            'language_id': language_id,
            'tags':        [],
            'source_type': 'corpus',
            'pack_type':   pack_type,
            'total_items': len(result.data),
            'is_public':   True,
        }).execute()
        pack_id = pack.data[0]['id']

        joins = [
            {'pack_id': pack_id, 'collocation_id': row['id']}
            for row in result.data
        ]
        for i in range(0, len(joins), 500):
            self.db.table('pack_collocations').insert(joins[i : i + 500]).execute()

        return pack_id
```

---

##### Method: `get_packs_for_user`

**Purpose:** Retrieve all public packs for a language, with a flag indicating whether the user has already selected each. Uses a SQL LEFT JOIN so this is a single DB call rather than two.

```python
    def get_packs_for_user(
        self,
        language_id: int,
        user_id: str
    ) -> list[dict]:
        """
        Return all public collocation packs for a language, annotated with
        whether the user has selected each pack.

        Uses a Supabase RPC (see SQL below) for the LEFT JOIN in one query.

        Args:
            language_id: Filter to this language.
            user_id:     Supabase auth user UUID string.
        Returns:
            list[dict]: Each item has pack fields plus 'is_selected' (bool).
        """
        result = self.db.rpc(
            'get_packs_with_user_selection',
            {'p_language_id': language_id, 'p_user_id': user_id}
        ).execute()
        return result.data or []
```

---

##### Method: `select_pack`

**Purpose:** Record that a user has opted into a pack. Uses upsert to be idempotent (double-selecting does not create a duplicate row).

```python
    def select_pack(self, user_id: str, pack_id: int) -> None:
        """
        Upsert a user_pack_selections row for the given user and pack.
        Idempotent — safe to call if the user has already selected the pack.
        Args:
            user_id: Supabase auth user UUID.
            pack_id: ID of the collocation_packs row.
        """
        self.db.table('user_pack_selections').upsert({
            'user_id': user_id,
            'pack_id': pack_id,
        }).execute()
```

**Dependencies:** Tasks 1.1, 2.1, 3.1, 4.1

---

## Phase 6 — SQL Functions and Migrations

### Task 6.1 — Supabase SQL: RPC `get_top_collocations_for_sources`

**Purpose:** Server-side aggregation across multiple corpus sources. Called by `CollocationPackService.create_cross_source_pack`. Groups by `collocation_text`, takes `MAX(pmi_score)` to rank, filters by minimum PMI, returns the top-N collocation rows.

**Migration file:** `supabase/migrations/YYYYMMDD_corpus_rpcs.sql`

```sql
-- ============================================================
-- RPC: get_top_collocations_for_sources
-- Aggregates collocations across multiple corpus sources,
-- deduplicates by collocation_text, ranks by max PMI,
-- returns top-N results above a minimum PMI threshold.
-- ============================================================
CREATE OR REPLACE FUNCTION get_top_collocations_for_sources(
    p_source_ids  INTEGER[],
    p_min_pmi     FLOAT,
    p_top_n       INTEGER
)
RETURNS TABLE (
    id                BIGINT,
    collocation_text  TEXT,
    n_gram_size       INTEGER,
    pmi_score         FLOAT,
    log_likelihood    FLOAT,
    t_score           FLOAT,
    collocation_type  TEXT,
    pos_pattern       TEXT,
    language_id       INTEGER
)
LANGUAGE SQL
STABLE
AS $$
    -- For each distinct collocation_text, pick the row with the
    -- highest PMI (DISTINCT ON ordered by pmi_score DESC), then
    -- take the global top-N of those winners.
    SELECT DISTINCT ON (cc.collocation_text)
        cc.id,
        cc.collocation_text,
        cc.n_gram_size,
        cc.pmi_score,
        cc.log_likelihood,
        cc.t_score,
        cc.collocation_type,
        cc.pos_pattern,
        cc.language_id
    FROM corpus_collocations cc
    WHERE cc.corpus_source_id = ANY(p_source_ids)
      AND cc.pmi_score >= p_min_pmi
    ORDER BY cc.collocation_text, cc.pmi_score DESC
    LIMIT p_top_n;
$$;
```

---

### Task 6.2 — Supabase SQL: RPC `get_packs_with_user_selection`

**Purpose:** Single query returning all public packs for a language annotated with whether the current user has selected each. Used by `CollocationPackService.get_packs_for_user` and the `GET /corpus/packs` API endpoint.

```sql
-- ============================================================
-- RPC: get_packs_with_user_selection
-- Returns public packs for a language, annotated with
-- whether the requesting user has already selected each.
-- ============================================================
CREATE OR REPLACE FUNCTION get_packs_with_user_selection(
    p_language_id  INTEGER,
    p_user_id      TEXT
)
RETURNS TABLE (
    id               BIGINT,
    pack_name        TEXT,
    description      TEXT,
    pack_type        TEXT,
    tags             TEXT[],
    total_items      INTEGER,
    difficulty_range TEXT,
    is_selected      BOOLEAN
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        cp.id,
        cp.pack_name,
        cp.description,
        cp.pack_type,
        cp.tags,
        cp.total_items,
        cp.difficulty_range,
        (ups.user_id IS NOT NULL) AS is_selected
    FROM collocation_packs cp
    LEFT JOIN user_pack_selections ups
        ON ups.pack_id = cp.id
       AND ups.user_id = p_user_id
    WHERE cp.language_id = p_language_id
      AND cp.is_public = TRUE
    ORDER BY cp.pack_name;
$$;
```

---

### Task 6.3 — Supabase SQL: Cross-source corpus statistics view

**Purpose:** Aggregated statistics view for admin monitoring of corpus coverage. Shows per-language collocation counts, average PMI, and type distribution. Useful for deciding when a corpus needs more sources.

```sql
-- ============================================================
-- View: corpus_statistics
-- Admin view showing collocation coverage by language and type.
-- ============================================================
CREATE OR REPLACE VIEW corpus_statistics AS
SELECT
    cc.language_id,
    dl.language_name,
    cc.collocation_type,
    cc.n_gram_size,
    COUNT(*)                   AS collocation_count,
    ROUND(AVG(cc.pmi_score)::NUMERIC, 3)   AS avg_pmi,
    ROUND(AVG(cc.frequency)::NUMERIC, 1)   AS avg_frequency,
    COUNT(*) FILTER (WHERE cc.is_validated = TRUE) AS validated_count
FROM corpus_collocations cc
JOIN dim_languages dl ON dl.id = cc.language_id
GROUP BY cc.language_id, dl.language_name, cc.collocation_type, cc.n_gram_size
ORDER BY cc.language_id, cc.n_gram_size, cc.collocation_type;
```

---

### Task 6.4 — Supabase SQL: Indexes for corpus query performance

**Purpose:** The corpus tables will grow large quickly. These indexes cover the most common query patterns: lookups by source, by language + PMI ranking, and by collocation text for deduplication checks.

```sql
-- ============================================================
-- Indexes: corpus_collocations performance
-- ============================================================

-- Primary lookup: all collocations for a source, ordered by PMI
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_source_pmi
    ON corpus_collocations (corpus_source_id, pmi_score DESC);

-- Language + PMI range queries (used by cross-source pack creation
-- and any future full-corpus browse endpoints)
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_lang_pmi
    ON corpus_collocations (language_id, pmi_score DESC);

-- Collocation text lookup for existence checks / deduplication
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_text_lang
    ON corpus_collocations (language_id, collocation_text);

-- Filter by type (discourse_marker, fixed_phrase, collocation)
CREATE INDEX IF NOT EXISTS idx_corpus_collocations_type
    ON corpus_collocations (language_id, collocation_type);

-- corpus_sources: find unprocessed sources for background job
CREATE INDEX IF NOT EXISTS idx_corpus_sources_unprocessed
    ON corpus_sources (processed_at)
    WHERE processed_at IS NULL;

-- pack_collocations: lookups in both directions
CREATE INDEX IF NOT EXISTS idx_pack_collocations_pack
    ON pack_collocations (pack_id);
CREATE INDEX IF NOT EXISTS idx_pack_collocations_collocation
    ON pack_collocations (collocation_id);
```

---

## Phase 7 — API Endpoints

### Task 7.1 — Create `routes/corpus.py`

**What to build:** Flask Blueprint with three endpoints. Follows the existing pattern in `routes/tests.py`: `@supabase_jwt_required` on all routes, `@admin_required` for mutation endpoints, Supabase client from `g`, service classes instantiated per request.

**File:** `routes/corpus.py`

```python
from flask import Blueprint, request, jsonify, g
from auth import supabase_jwt_required, admin_required
from services.corpus.ingestion import CorpusIngestionService
from services.corpus.pack_service import CollocationPackService

corpus_bp = Blueprint('corpus', __name__, url_prefix='/corpus')


def _get_db():
    """Return the Supabase client from Flask g (consistent with existing routes)."""
    return g.supabase
```

---

#### Endpoint: `POST /corpus/ingest`

**Purpose:** Admin-only ingestion trigger. Accepts `source_type='url'` or `source_type='text'` in the JSON body. Runs the full pipeline synchronously (consider moving to a background task if texts are large — see Task 8.1).

```python
@corpus_bp.route('/ingest', methods=['POST'])
@supabase_jwt_required
@admin_required
def ingest_corpus():
    """
    Ingest a new corpus source and run the full analysis pipeline.
    Admin-only.

    Request body (JSON):
        source_type  (str, required): 'url' or 'text'
        language_id  (int, required): 1=ZH, 2=EN, 3=JA
        tags         (list[str], optional): Tag strings for this source
        url          (str): Required when source_type='url'
        text         (str): Required when source_type='text'
        title        (str): Required when source_type='text'

    Response (200):
        {"success": true, "corpus_source_id": <int>}

    Response (400):
        {"error": "<message>"}

    Response (502):
        {"error": "Failed to fetch URL: <detail>"}
    """
    body        = request.get_json(force=True)
    source_type = body.get('source_type')
    language_id = body.get('language_id')
    tags        = body.get('tags', [])

    if not source_type or not language_id:
        return jsonify({'error': 'source_type and language_id are required'}), 400

    service = CorpusIngestionService(db=_get_db())

    try:
        if source_type == 'url':
            url = body.get('url')
            if not url:
                return jsonify({'error': 'url is required for source_type=url'}), 400
            corpus_source_id = service.ingest_url(url, language_id, tags)

        elif source_type == 'text':
            text  = body.get('text')
            title = body.get('title', 'Untitled')
            if not text:
                return jsonify({'error': 'text is required for source_type=text'}), 400
            corpus_source_id = service.ingest_text(text, title, language_id, tags)

        else:
            return jsonify({'error': f'Unsupported source_type: {source_type}'}), 400

    except Exception as exc:
        return jsonify({'error': str(exc)}), 502

    return jsonify({'success': True, 'corpus_source_id': corpus_source_id})
```

---

#### Endpoint: `GET /corpus/packs`

**Purpose:** Return public collocation packs for a language, annotated with the requesting user's selection state. Uses `CollocationPackService.get_packs_for_user` which calls the `get_packs_with_user_selection` RPC.

```python
@corpus_bp.route('/packs', methods=['GET'])
@supabase_jwt_required
def list_packs():
    """
    List public collocation packs for a language, with user selection state.

    Query params:
        language_id (int, required): Filter packs by language.

    Response (200):
        {"packs": [
            {
              "id": <int>,
              "pack_name": <str>,
              "description": <str>,
              "pack_type": <str>,
              "tags": [<str>],
              "total_items": <int>,
              "difficulty_range": <str|null>,
              "is_selected": <bool>
            },
            ...
        ]}

    Response (400):
        {"error": "language_id is required"}
    """
    language_id_str = request.args.get('language_id')
    if not language_id_str:
        return jsonify({'error': 'language_id is required'}), 400

    try:
        language_id = int(language_id_str)
    except ValueError:
        return jsonify({'error': 'language_id must be an integer'}), 400

    user_id = g.supabase_claims.get('sub')
    service = CollocationPackService(db=_get_db())
    packs   = service.get_packs_for_user(language_id, user_id)
    return jsonify({'packs': packs})
```

---

#### Endpoint: `POST /corpus/packs/<pack_id>/select`

**Purpose:** User opts into a collocation pack. Idempotent (upsert). No body required — pack selection is a simple toggle recorded by user_id + pack_id.

```python
@corpus_bp.route('/packs/<int:pack_id>/select', methods=['POST'])
@supabase_jwt_required
def select_pack(pack_id: int):
    """
    Record that the authenticated user has selected a collocation pack.
    Idempotent — re-selecting the same pack is safe.

    Path param:
        pack_id (int): ID of the collocation_packs row.

    Response (200):
        {"success": true}
    """
    user_id = g.supabase_claims.get('sub')
    service = CollocationPackService(db=_get_db())
    service.select_pack(user_id, pack_id)
    return jsonify({'success': True})
```

---

#### Blueprint registration (in `app.py`)

**Note — existing codebase change (minimal):** Register the new blueprint in `app.py`. This is the only change to existing files required by Plan 5.

```python
# In app.py, alongside existing blueprint registrations:
from routes.corpus import corpus_bp
app.register_blueprint(corpus_bp)
```

**Dependencies:** Tasks 4.1, 5.1

---

## Phase 8 — Background Processing (Optional but Recommended)

### Task 8.1 — Background ingestion task wrapper

**What to build:** For large texts (author corpora, long news articles), synchronous ingestion blocks the HTTP response. Wrap `CorpusIngestionService._run_pipeline` in a background task using the existing Railway deployment pattern. This task is only needed if synchronous ingestion proves too slow in practice — implement after initial testing.

**File:** `services/corpus/tasks.py`

```python
import threading
from services.corpus.ingestion import CorpusIngestionService


def run_ingestion_async(
    payload: dict,
    db_factory,
) -> None:
    """
    Run CorpusIngestionService._run_pipeline in a background thread.
    Use this for large author corpora or batch URL ingestion.

    Args:
        payload:    Dict with keys: raw_text, source_type, source_url,
                    source_title, language_id, tags.
        db_factory: Callable returning a fresh Supabase client
                    (cannot use Flask g outside request context).
    """
    def _worker():
        db      = db_factory()
        service = CorpusIngestionService(db=db)
        service._run_pipeline(**payload)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
```

---

### Task 8.2 — Unprocessed source sweep (cron-style)

**What to build:** A script analogous to `services/test_generation/run_test_generation.py` that finds `corpus_sources` rows with `processed_at IS NULL` and processes them. Handles cases where `_run_pipeline` was interrupted mid-flight.

**File:** `services/corpus/run_corpus_processing.py`

```python
"""
Entry point for scheduled / manual reprocessing of unprocessed corpus sources.
Can be run via Railway cron or manually:
    python services/corpus/run_corpus_processing.py

Finds corpus_sources where processed_at IS NULL and re-runs the analysis
pipeline on each, using the stored raw_text.
"""
import os
from supabase import create_client
from services.corpus.ingestion import CorpusIngestionService


def sweep_unprocessed_sources() -> int:
    """
    Find all corpus_sources with processed_at IS NULL and reprocess them.
    Only processes sources that have raw_text stored inline (not offloaded to R2).

    Returns:
        int: Number of sources successfully processed.
    """
    url  = os.environ['SUPABASE_URL']
    key  = os.environ['SUPABASE_SERVICE_KEY']
    db   = create_client(url, key)

    unprocessed = (
        db.table('corpus_sources')
        .select('id, raw_text, language_id, source_type, source_url, source_title, tags')
        .is_('processed_at', 'NULL')
        .not_.is_('raw_text', 'NULL')   # Skip R2-offloaded texts
        .execute()
    )

    if not unprocessed.data:
        print("No unprocessed sources found.")
        return 0

    service   = CorpusIngestionService(db=db)
    processed = 0

    for source in unprocessed.data:
        try:
            service._run_pipeline(
                raw_text=source['raw_text'],
                source_type=source['source_type'],
                source_url=source['source_url'],
                source_title=source['source_title'],
                language_id=source['language_id'],
                tags=source['tags'] or [],
            )
            processed += 1
            print(f"Processed corpus_source id={source['id']}: {source['source_title']}")
        except Exception as exc:
            print(f"Failed corpus_source id={source['id']}: {exc}")

    return processed


if __name__ == '__main__':
    n = sweep_unprocessed_sources()
    print(f"Done. Processed {n} sources.")
```

**Dependencies:** Tasks 4.1, 2.1, 3.1

---

## Phase 9 — Package Initialisation

### Task 9.1 — Create `services/corpus/__init__.py`

**What to build:** Package init that re-exports the primary public classes for cleaner import paths elsewhere in the codebase (e.g. exercise generation services that will consume corpus data in later plans).

**File:** `services/corpus/__init__.py`

```python
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
]
```

---

## Phase 10 — Seed Data

### Task 10.1 — Seed script for initial collocation packs

**What to build:** A one-time seed script that ingests a curated starter set of public-domain texts and creates the initial packs described in Plan 5.6. Run manually after deployment.

**File:** `scripts/seed_corpus_packs.py`

```python
"""
One-time seed script: ingest starter corpus sources and create initial packs.

Usage:
    python scripts/seed_corpus_packs.py

Requires: SUPABASE_URL, SUPABASE_SERVICE_KEY in environment.

Public-domain texts are fetched from Project Gutenberg or provided inline.
Adjust SOURCES list as needed.
"""
import os
from supabase import create_client
from services.corpus.ingestion import CorpusIngestionService
from services.corpus.pack_service import CollocationPackService

# ---------------------------------------------------------------------------
# Starter source definitions
# Each entry: (source_type, identifier, language_id, tags, pack_meta)
# ---------------------------------------------------------------------------
SOURCES = [
    {
        'source_type': 'url',
        'url': 'https://www.theguardian.com/business/economics',
        'language_id': 2,
        'tags': ['economics_reporting', 'news'],
        'pack': {
            'pack_name':   'Economics Reporting',
            'description': 'Collocations from economics news reporting',
            'pack_type':   'genre',
        },
    },
    {
        'source_type': 'url',
        # Gulliver's Travels — full public domain text via Gutenberg
        'url': 'https://www.gutenberg.org/files/829/829-0.txt',
        'language_id': 2,
        'tags': ['author_jonathan_swift', 'literature'],
        'pack': {
            'pack_name':   'Jonathan Swift',
            'description': "Collocations from Swift's prose",
            'pack_type':   'author',
        },
    },
]


def run_seed():
    """
    Ingest each source and create its corresponding pack.
    Safe to re-run — duplicate corpus_sources rows will be created
    but existing pack data is unaffected.
    """
    url  = os.environ['SUPABASE_URL']
    key  = os.environ['SUPABASE_SERVICE_KEY']
    db   = create_client(url, key)

    ingestor    = CorpusIngestionService(db=db)
    pack_svc    = CollocationPackService(db=db)

    for s in SOURCES:
        print(f"Ingesting: {s.get('url', s.get('title', '?'))}")

        if s['source_type'] == 'url':
            source_id = ingestor.ingest_url(
                url=s['url'],
                language_id=s['language_id'],
                tags=s['tags'],
            )
        elif s['source_type'] == 'text':
            source_id = ingestor.ingest_text(
                text=s['text'],
                title=s['title'],
                language_id=s['language_id'],
                tags=s['tags'],
            )
        else:
            print(f"  Skipping unknown source_type: {s['source_type']}")
            continue

        print(f"  corpus_source_id={source_id}. Creating pack...")
        pack_id = pack_svc.create_pack_from_corpus(
            corpus_source_id=source_id,
            pack_name=s['pack']['pack_name'],
            description=s['pack']['description'],
            pack_type=s['pack']['pack_type'],
            language_id=s['language_id'],
        )
        print(f"  pack_id={pack_id} created: {s['pack']['pack_name']}")

    print("Seed complete.")


if __name__ == '__main__':
    run_seed()
```

---

## Summary: File Manifest

| File | Phase | New / Modified |
|---|---|---|
| `services/corpus/__init__.py` | 9 | New |
| `services/corpus/tokenizers.py` | 1 | New |
| `services/corpus/analyzer.py` | 2 | New |
| `services/corpus/classifier.py` | 3 | New |
| `services/corpus/ingestion.py` | 4 | New |
| `services/corpus/pack_service.py` | 5 | New |
| `services/corpus/tasks.py` | 8 | New |
| `services/corpus/run_corpus_processing.py` | 8 | New |
| `routes/corpus.py` | 7 | New |
| `supabase/migrations/YYYYMMDD_corpus_rpcs.sql` | 6 | New |
| `scripts/seed_corpus_packs.py` | 10 | New |
| `app.py` | 7 | **Modified** (1 line: register blueprint) |

## Dependency Graph

```
Phase 1 (tokenizers.py)
    └── Phase 2 (analyzer.py)
    └── Phase 3 (classifier.py)
            └── Phase 4 (ingestion.py)
            │       └── Phase 7 (routes/corpus.py)
            │       └── Phase 8 (tasks.py, run_corpus_processing.py)
            └── Phase 5 (pack_service.py)
                    └── Phase 6 (SQL RPCs)
                    └── Phase 7 (routes/corpus.py)
                    └── Phase 10 (seed script)
Phase 9 (__init__.py) — depends on all of 1–5
```
