import math
from collections import Counter
from typing import Iterator
from services.corpus.tokenizers import LanguageTokenizer


class CorpusAnalyzer:
    """
    Statistical corpus analysis engine.
    Language-agnostic: receives a LanguageTokenizer at init.
    All n-gram extraction covers ALL combinations of successive words
    (sizes 2-5), not just linguistically motivated segments.
    This captures phrases like 'in other words', 'as a result of', etc.
    """

    # Frequency: how many times the n-gram must appear to be considered.
    # For small corpora (< SMALL_CORPUS_THRESHOLD tokens) a fixed floor
    # is used; above that the minimum scales proportionally.
    SMALL_CORPUS_THRESHOLD = 10_000
    SMALL_CORPUS_MIN_FREQ  = 8
    LARGE_CORPUS_FREQ_DIVISOR = 10_000

    # Legacy constant kept for callers that pass min_frequency explicitly.
    MIN_FREQUENCY = 5

    # PMI alone is biased towards rare words. These thresholds are the
    # MINIMUM PMI; bigrams must ALSO pass the G² or T-Score gate below.
    PMI_THRESHOLD_BIGRAM = 3.0
    PMI_THRESHOLD_LONGER = 2.0

    # Bigrams must pass at least one of these statistical significance tests
    # in addition to the PMI threshold. This filters out rare-word noise.
    LL_THRESHOLD         = 10.83   # G² >= 10.83 ≈ p < 0.001
    T_SCORE_THRESHOLD    = 2.0     # T >= 2.0 indicates significance

    def __init__(self, tokenizer: LanguageTokenizer):
        self.tokenizer = tokenizer

    def generate_ngrams(self, tokens: list[str], n: int) -> Iterator[tuple]:
        """
        Yield all successive n-grams from a token list as tuples.
        Example: ['a','b','c','d'], n=2 -> ('a','b'), ('b','c'), ('c','d')
        """
        for i in range(len(tokens) - n + 1):
            yield tuple(tokens[i : i + n])

    def extract_all_ngrams(
        self,
        text: str,
        max_n: int = 5
    ) -> dict[int, Counter]:
        """
        Tokenize text and count n-grams from size 1 to max_n.
        SENTENCE-AWARE: n-grams are extracted per sentence so tokens from
        adjacent sentences are never joined into the same window.
        """
        sentences = self.tokenizer.split_sentences(text) or [text]
        combined: dict[int, Counter] = {n: Counter() for n in range(1, max_n + 1)}

        for sentence in sentences:
            tokens = self.tokenizer.tokenize(sentence)
            if not tokens:
                continue
            for n in range(1, min(max_n + 1, len(tokens) + 1)):
                combined[n].update(self.generate_ngrams(tokens, n))

        return combined

    def compute_pmi(
        self,
        bigram: tuple[str, str],
        bigram_count: int,
        unigram_counts: Counter,
        total_tokens: int
    ) -> float:
        """
        Compute Pointwise Mutual Information for a bigram.
        PMI = log2( P(w1,w2) / (P(w1) * P(w2)) )
        Returns 0.0 if either word count is zero.
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

    def compute_log_likelihood(
        self,
        bigram_count: int,
        c_w1: int,
        c_w2: int,
        total_tokens: int
    ) -> float:
        """
        Compute G² (log-likelihood ratio) for a bigram using a 2x2 contingency table.
        Threshold: G² >= 10.83 ~ p < 0.001.
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

    def compute_t_score(
        self,
        bigram_count: int,
        c_w1: int,
        c_w2: int,
        total_tokens: int
    ) -> float:
        """
        Compute T-Score for a bigram.
        t = (C(w1,w2) - E11) / sqrt(C(w1,w2))
        Values >= 2.0 indicate significance.
        """
        if bigram_count <= 0 or total_tokens == 0:
            return 0.0
        E11 = c_w1 * c_w2 / total_tokens
        return (bigram_count - E11) / math.sqrt(bigram_count)

    def compute_lmi(self, bigram_count: int, pmi: float) -> float:
        """Lexical Mutual Information: frequency-weighted PMI. Returns 0.0 if PMI <= 0."""
        return bigram_count * pmi if pmi > 0 else 0.0

    def _score_bigram(
        self,
        bigram: tuple[str, str],
        bigram_count: int,
        unigram_counts: Counter,
        total_tokens: int
    ) -> tuple[float, float, float, float]:
        """
        Compute PMI, G², T-Score, and LMI for a single bigram.
        Returns (pmi, log_likelihood, t_score, lmi).
        """
        w1, w2 = bigram
        c_w1 = unigram_counts.get((w1,), unigram_counts.get(w1, 0))
        c_w2 = unigram_counts.get((w2,), unigram_counts.get(w2, 0))

        pmi = self.compute_pmi(bigram, bigram_count, unigram_counts, total_tokens)
        ll  = self.compute_log_likelihood(bigram_count, c_w1, c_w2, total_tokens)
        t   = self.compute_t_score(bigram_count, c_w1, c_w2, total_tokens)
        lmi = self.compute_lmi(bigram_count, pmi)
        return pmi, ll, t, lmi

    def _average_pmi_for_ngram(
        self,
        ngram: tuple,
        bigram_counts: Counter,
        unigram_counts: Counter,
        total_tokens: int
    ) -> float:
        """
        Compute the average PMI across all consecutive bigram windows in an n-gram.
        Used for n-grams of size 3-5.
        """
        pmi_values = []
        for i in range(len(ngram) - 1):
            bigram = (ngram[i], ngram[i + 1])
            b_count = bigram_counts.get(bigram, 0)
            pmi = self.compute_pmi(bigram, b_count, unigram_counts, total_tokens)
            pmi_values.append(pmi)
        return sum(pmi_values) / len(pmi_values) if pmi_values else 0.0

    @classmethod
    def dynamic_min_frequency(cls, total_tokens: int) -> int:
        """
        Compute the minimum n-gram frequency based on corpus size.

        Below SMALL_CORPUS_THRESHOLD tokens a fixed floor is used to avoid
        surfacing low-confidence collocations from small texts.  Above that
        the threshold scales proportionally so that larger corpora
        naturally demand higher raw counts.
        """
        if total_tokens < cls.SMALL_CORPUS_THRESHOLD:
            return cls.SMALL_CORPUS_MIN_FREQ
        return max(cls.SMALL_CORPUS_MIN_FREQ, total_tokens // cls.LARGE_CORPUS_FREQ_DIVISOR)

    def score_ngrams(
        self,
        text: str,
        min_frequency: int | None = None,
        pmi_threshold_bigram: float = PMI_THRESHOLD_BIGRAM,
        pmi_threshold_longer: float = PMI_THRESHOLD_LONGER,
        require_significance: bool = True,
    ) -> list[dict]:
        """
        Full pipeline: extract all successive n-grams (sizes 2-5), apply
        frequency filter, compute PMI/G²/T-Score, apply PMI threshold.
        Does NOT perform classification (caller uses CollocationClassifier).

        When min_frequency is None (default) it is computed dynamically
        based on corpus size — see dynamic_min_frequency().

        When require_significance=True (default), bigrams must pass BOTH:
          - PMI >= pmi_threshold_bigram
          - G² >= LL_THRESHOLD OR T-Score >= T_SCORE_THRESHOLD
        This prevents high-PMI rare-word noise from passing through.

        Returns list of dicts with keys: collocation_text, head_word, collocate,
        n_gram_size, frequency, pmi_score, log_likelihood, t_score.
        """
        ngrams_by_size = self.extract_all_ngrams(text, max_n=5)
        unigram_counts = ngrams_by_size[1]
        total_tokens   = sum(unigram_counts.values())
        bigram_counts  = ngrams_by_size[2]
        join_char      = self.tokenizer.join_char

        if min_frequency is None:
            min_frequency = self.dynamic_min_frequency(total_tokens)

        results = []

        for n in range(2, 6):
            pmi_threshold = pmi_threshold_bigram if n == 2 else pmi_threshold_longer
            for ngram, freq in ngrams_by_size[n].items():
                if freq < min_frequency:
                    continue

                if n == 2:
                    pmi, ll, t, lmi = self._score_bigram(
                        ngram, freq, unigram_counts, total_tokens
                    )
                    # Require statistical significance beyond just PMI.
                    # PMI alone is biased towards rare words — two uncommon words
                    # appearing together once can score PMI > 10 despite being
                    # meaningless. G² and T-Score account for sample size.
                    if require_significance:
                        if ll < self.LL_THRESHOLD and t < self.T_SCORE_THRESHOLD:
                            continue
                else:
                    pmi = self._average_pmi_for_ngram(
                        ngram, bigram_counts, unigram_counts, total_tokens
                    )
                    ll, t, lmi = 0.0, 0.0, 0.0

                if pmi < pmi_threshold:
                    continue

                results.append({
                    'collocation_text': join_char.join(ngram),
                    'head_word':        ngram[0],
                    'collocate':        join_char.join(ngram[1:]) if len(ngram) > 1 else None,
                    'n_gram_size':      n,
                    'frequency':        freq,
                    'pmi_score':        round(pmi, 4),
                    'log_likelihood':   round(ll, 4),
                    't_score':          round(t, 4),
                    'lmi_score':        round(lmi, 4),
                })

        return results

    def score_dependency_pairs(
        self,
        text: str,
        min_frequency: int | None = None,
        pmi_threshold: float = PMI_THRESHOLD_BIGRAM,
    ) -> list[dict]:
        """
        Extract and score dependency-based bigrams.
        These capture non-adjacent syntactic relationships (e.g. make→decision
        in "make a decision"). Returns list of dicts with same shape as
        score_ngrams output plus extraction_method and dependency_relation.
        """
        pairs = self.tokenizer.extract_dependency_pairs(text)
        if not pairs:
            return []

        # Count occurrences of each (head, dep) pair
        pair_counts = Counter((h, d) for h, d, _ in pairs)
        # Map (head, dep) → most common relation
        rel_map: dict[tuple, Counter] = {}
        for h, d, rel in pairs:
            rel_map.setdefault((h, d), Counter())[rel] += 1

        # Need unigram counts for PMI
        tokens = self.tokenizer.tokenize(text)
        total_tokens = len(tokens)
        unigram_counts = Counter(tokens)

        if min_frequency is None:
            min_frequency = self.dynamic_min_frequency(total_tokens)

        join_char = self.tokenizer.join_char
        results = []
        for (head, dep), freq in pair_counts.items():
            if freq < min_frequency:
                continue

            pmi = self.compute_pmi((head, dep), freq, unigram_counts, total_tokens)
            if pmi < pmi_threshold:
                continue

            c_w1 = unigram_counts.get(head, 0)
            c_w2 = unigram_counts.get(dep, 0)
            ll = self.compute_log_likelihood(freq, c_w1, c_w2, total_tokens)
            t = self.compute_t_score(freq, c_w1, c_w2, total_tokens)
            lmi = self.compute_lmi(freq, pmi)
            best_rel = rel_map[(head, dep)].most_common(1)[0][0]

            results.append({
                'collocation_text': join_char.join([head, dep]),
                'head_word':        head,
                'collocate':        dep,
                'n_gram_size':      2,
                'frequency':        freq,
                'pmi_score':        round(pmi, 4),
                'log_likelihood':   round(ll, 4),
                't_score':          round(t, 4),
                'lmi_score':        round(lmi, 4),
                'extraction_method':    'dependency',
                'dependency_relation':  best_rel,
            })

        return results
