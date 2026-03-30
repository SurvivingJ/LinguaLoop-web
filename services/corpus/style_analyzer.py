"""
Corpus style analysis engine.

Extracts stylistic features from a text corpus beyond statistically significant
collocations: raw frequency n-grams, sentence structure patterns, syntactic
preferences, discourse patterns, and vocabulary profiles. These features
characterise an author's or publication's writing style and are packaged into
"style packs" for language learners.
"""

import logging
import math
import re
from collections import Counter

from services.corpus.tokenizers import LanguageTokenizer
from services.corpus.analyzer import CorpusAnalyzer
from services.corpus.classifier import CollocationClassifier
from services.vocabulary.frequency_service import get_zipf_score

logger = logging.getLogger(__name__)

# Language ID → wordfreq language code
_LANG_ID_TO_WF = {1: 'cn', 2: 'en', 3: 'jp'}

# MATTR (Moving-Average Type-Token Ratio) window size
_MATTR_WINDOW = 500

# Maximum number of items to store per feature category
_TOP_K_NGRAMS = 50
_TOP_K_PATTERNS = 20
_TOP_K_OPENERS = 20
_TOP_K_TRANSITIONS = 20
_TOP_K_KEYNESS = 50

# Minimum frequency for sentence patterns
_MIN_PATTERN_FREQ = 3

# Zipf band boundaries for vocabulary profile
_ZIPF_BANDS = [(0, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 8)]


class StyleAnalyzer:
    """
    Extract stylistic features from a text corpus.

    Composes CorpusAnalyzer and CollocationClassifier, reusing the existing
    tokenization and n-gram infrastructure. Uses single-pass spaCy parsing
    via tokenize_doc() where available.
    """

    def __init__(self, tokenizer: LanguageTokenizer):
        self.tokenizer = tokenizer
        self.corpus_analyzer = CorpusAnalyzer(tokenizer)
        self.classifier = CollocationClassifier(tokenizer)

    def analyze(
        self,
        text: str,
        reference_ngrams: dict[int, Counter] | None = None,
        reference_total_tokens: int = 0,
    ) -> dict:
        """
        Run full style analysis on a text.

        Args:
            text: The raw corpus text.
            reference_ngrams: Optional pre-computed n-gram counters from a
                reference corpus (keyed by n-gram size) for keyness comparison.
            reference_total_tokens: Total token count in the reference corpus.

        Returns:
            Dict with keys: raw_frequency_ngrams, characteristic_ngrams,
            sentence_structures, syntactic_preferences, discourse_patterns,
            vocabulary_profile, total_tokens, total_sentences.
        """
        sentences = self.tokenizer.split_sentences(text) or [text]
        ngrams_by_size = self.corpus_analyzer.extract_all_ngrams(text, max_n=5)
        total_tokens = sum(ngrams_by_size[1].values())
        join_char = self.tokenizer.join_char

        # Single-pass spaCy Doc for EN/JA (None for ZH)
        doc = self.tokenizer.tokenize_doc(text)

        profile = {
            'total_tokens': total_tokens,
            'total_sentences': len(sentences),
            'raw_frequency_ngrams': self._extract_raw_frequency_ngrams(
                ngrams_by_size, join_char
            ),
            'characteristic_ngrams': self._extract_keyness(
                ngrams_by_size, total_tokens, join_char,
                reference_ngrams, reference_total_tokens,
            ),
            'sentence_structures': self._extract_sentence_structures(
                sentences, doc
            ),
            'syntactic_preferences': self._extract_syntactic_preferences(
                sentences, doc
            ),
            'discourse_patterns': self._extract_discourse_patterns(
                text, sentences
            ),
            'vocabulary_profile': self._extract_vocabulary_profile(
                ngrams_by_size[1], total_tokens
            ),
        }

        logger.info(
            f"Style analysis complete: {total_tokens:,} tokens, "
            f"{len(sentences):,} sentences"
        )
        return profile

    # ── A. Raw Frequency N-grams ─────────────────────────────────────────

    def _extract_raw_frequency_ngrams(
        self,
        ngrams_by_size: dict[int, Counter],
        join_char: str,
    ) -> dict:
        """Top-K most frequent n-grams per size (1-5), no PMI gating."""
        result = {}
        for n in range(1, 6):
            top = ngrams_by_size[n].most_common(_TOP_K_NGRAMS)
            result[str(n)] = [
                {
                    'text': join_char.join(ngram) if isinstance(ngram, tuple) else ngram,
                    'frequency': freq,
                    'rank': rank + 1,
                }
                for rank, (ngram, freq) in enumerate(top)
            ]
        return result

    # ── B. Characteristic N-grams (Keyness) ──────────────────────────────

    def _extract_keyness(
        self,
        ngrams_by_size: dict[int, Counter],
        total_tokens: int,
        join_char: str,
        reference_ngrams: dict[int, Counter] | None,
        reference_total_tokens: int,
    ) -> list[dict]:
        """
        Find n-grams that are over-represented compared to a reference.

        For unigrams: uses wordfreq as baseline (always available).
        For n-grams (n>=2): uses provided reference_ngrams if available.
        """
        results = []
        lang_code = _LANG_ID_TO_WF.get(self.tokenizer.language_id)

        if total_tokens == 0:
            return results

        # Unigram keyness via wordfreq
        if lang_code:
            for (token,), author_freq in ngrams_by_size[1].most_common(500):
                author_rate = author_freq / total_tokens
                zipf = get_zipf_score(token, lang_code)
                if zipf is None:
                    # Unknown to wordfreq = potentially very distinctive
                    ref_rate = 1e-7
                else:
                    # Convert Zipf score to approximate rate
                    # Zipf = log10(freq_per_billion), so freq_per_billion = 10^zipf
                    ref_rate = (10 ** zipf) / 1e9

                if ref_rate > 0 and author_rate > ref_rate:
                    ratio = author_rate / ref_rate
                    if ratio >= 2.0:  # At least 2x over-represented
                        results.append({
                            'text': token,
                            'n_gram_size': 1,
                            'keyness_score': round(math.log2(ratio), 3),
                            'author_freq': author_freq,
                            'author_rate': round(author_rate, 6),
                        })

        # N-gram keyness (n>=2) against reference corpus
        if reference_ngrams and reference_total_tokens > 0:
            for n in range(2, 6):
                ref_counter = reference_ngrams.get(n, Counter())
                if not ref_counter:
                    continue
                for ngram, author_freq in ngrams_by_size[n].most_common(200):
                    author_rate = author_freq / total_tokens
                    ref_freq = ref_counter.get(ngram, 0)
                    ref_rate = (ref_freq / reference_total_tokens) if ref_freq > 0 else 1e-7
                    ratio = author_rate / ref_rate
                    if ratio >= 2.0:
                        results.append({
                            'text': join_char.join(ngram),
                            'n_gram_size': n,
                            'keyness_score': round(math.log2(ratio), 3),
                            'author_freq': author_freq,
                            'author_rate': round(author_rate, 6),
                        })

        # Sort by keyness score descending, take top K
        results.sort(key=lambda x: x['keyness_score'], reverse=True)
        return results[:_TOP_K_KEYNESS]

    # ── C. Sentence Structure Patterns ───────────────────────────────────

    def _extract_sentence_structures(
        self,
        sentences: list[str],
        doc,
    ) -> dict:
        """
        Extract abstract sentence structure templates and length statistics.

        For EN/JA (spaCy): uses POS tags from the Doc.
        For ZH (jieba): uses jieba POS tags via tokenize_with_pos().
        """
        lengths = []
        pattern_counter: Counter = Counter()
        pattern_examples: dict[str, str] = {}  # first example per pattern
        coarse_map = self.classifier.COARSE_POS_MAP

        if doc is not None:
            # spaCy-based: iterate sentence spans from the Doc
            for sent in doc.sents:
                tokens = [t for t in sent if not t.is_space and not t.is_punct]
                length = len(tokens)
                if length == 0:
                    continue
                lengths.append(length)

                # Build POS template
                tags = [coarse_map.get(t.pos_, t.pos_) for t in tokens]
                template = ' '.join(tags)
                pattern_counter[template] += 1
                if template not in pattern_examples:
                    pattern_examples[template] = sent.text.strip()
        else:
            # jieba-based (Chinese): use tokenize_with_pos per sentence
            for sentence in sentences:
                pos_pairs = self.tokenizer.tokenize_with_pos(sentence)
                length = len(pos_pairs)
                if length == 0:
                    continue
                lengths.append(length)

                # jieba POS tags are different — just use them directly
                tags = [flag for _, flag in pos_pairs]
                template = ' '.join(tags)
                pattern_counter[template] += 1
                if template not in pattern_examples:
                    pattern_examples[template] = sentence[:100]

        # Build length distribution histogram (buckets of 5)
        length_dist = Counter()
        for l in lengths:
            bucket = f"{(l // 5) * 5}-{(l // 5) * 5 + 4}"
            length_dist[bucket] += 1

        # Top patterns
        top_patterns = [
            {
                'template': template,
                'frequency': freq,
                'example': pattern_examples.get(template, ''),
            }
            for template, freq in pattern_counter.most_common(_TOP_K_PATTERNS)
            if freq >= _MIN_PATTERN_FREQ
        ]

        avg_length = sum(lengths) / len(lengths) if lengths else 0.0

        return {
            'patterns': top_patterns,
            'avg_sentence_length': round(avg_length, 1),
            'length_distribution': dict(
                sorted(length_dist.items(), key=lambda x: int(x[0].split('-')[0]))
            ),
        }

    # ── D. Syntactic Preferences ─────────────────────────────────────────

    def _extract_syntactic_preferences(
        self,
        sentences: list[str],
        doc,
    ) -> dict:
        """
        Quantify syntactic tendencies: passive voice, subordinate/relative
        clauses, questions, clause depth.

        Requires dependency parsing (EN/JA only). Returns empty dict for ZH.
        """
        if doc is None:
            # Chinese: use regex heuristics for basic features
            return self._extract_chinese_syntactic_preferences(sentences)

        total_sents = 0
        passive_count = 0
        subordinate_count = 0
        relative_clause_count = 0
        question_count = 0
        clause_depths = []

        for sent in doc.sents:
            total_sents += 1
            sent_text = sent.text.strip()

            # Passive voice: nsubjpass or auxpass dependency
            has_passive = any(
                t.dep_ in ('nsubjpass', 'auxpass') for t in sent
            )
            if has_passive:
                passive_count += 1

            # Subordinate clause: SCONJ token or 'mark' dependency
            has_subordinate = any(
                t.pos_ == 'SCONJ' or t.dep_ == 'mark' for t in sent
            )
            if has_subordinate:
                subordinate_count += 1

            # Relative clause
            has_relcl = any(t.dep_ == 'relcl' for t in sent)
            if has_relcl:
                relative_clause_count += 1

            # Question
            if sent_text.endswith('?'):
                question_count += 1

            # Clause depth: max depth in dependency tree
            def token_depth(token):
                depth = 0
                while token.head != token:
                    token = token.head
                    depth += 1
                return depth

            max_depth = max((token_depth(t) for t in sent), default=0)
            clause_depths.append(max_depth)

        if total_sents == 0:
            return {}

        return {
            'passive_ratio': round(passive_count / total_sents, 3),
            'subordinate_clause_ratio': round(subordinate_count / total_sents, 3),
            'relative_clause_ratio': round(relative_clause_count / total_sents, 3),
            'question_ratio': round(question_count / total_sents, 3),
            'avg_clause_depth': round(
                sum(clause_depths) / len(clause_depths), 1
            ) if clause_depths else 0.0,
            'total_sentences_analyzed': total_sents,
        }

    def _extract_chinese_syntactic_preferences(
        self,
        sentences: list[str],
    ) -> dict:
        """
        LLM-based syntactic preference detection for Chinese.

        Samples up to 80 representative sentences and asks the LLM to
        identify syntactic constructions that jieba/regex cannot detect:
        把-constructions, 被-passives, topic-comment structures, serial
        verb constructions, aspect markers (了/着/过), and question types.

        Falls back to basic regex counts if the LLM call fails.
        """
        total = len(sentences)
        if total == 0:
            return {}

        # Basic regex counts (always computed — used as fallback and supplement)
        ba_count = sum(1 for s in sentences if '把' in s)
        bei_count = sum(1 for s in sentences if '被' in s)
        question_count = sum(1 for s in sentences if s.endswith('？') or s.endswith('?'))

        regex_result = {
            'ba_construction_ratio': round(ba_count / total, 3),
            'bei_passive_ratio': round(bei_count / total, 3),
            'question_ratio': round(question_count / total, 3),
            'total_sentences_analyzed': total,
        }

        # Sample sentences for LLM analysis
        import random
        sample_size = min(80, total)
        if total > sample_size:
            sampled = random.sample(sentences, sample_size)
        else:
            sampled = sentences

        try:
            from services.corpus.llm_client import call_llm

            numbered = '\n'.join(
                f"{i+1}. {s}" for i, s in enumerate(sampled)
            )

            prompt = f"""You are a Chinese linguistics expert. Analyse these {len(sampled)} Chinese sentences and count syntactic constructions.

Sentences:
{numbered}

For each category below, count how many sentences contain that construction. A sentence may contain multiple constructions.

Return a JSON object with these exact keys (all values are integers):
- "ba_constructions": sentences using 把 to mark the object (not incidental 把)
- "bei_passives": sentences using 被-passive construction
- "topic_comment": sentences with a fronted topic distinct from the subject (e.g. "这本书，我看过了")
- "serial_verb": sentences with serial verb constructions (连动句, two+ verbs sharing a subject)
- "aspect_le": sentences using 了 as a perfective/change-of-state marker
- "aspect_zhe": sentences using 着 as a continuous aspect marker
- "aspect_guo": sentences using 过 as an experiential aspect marker
- "rhetorical_questions": sentences using rhetorical question patterns (难道, 不是...吗, etc.)
- "direct_questions": sentences ending with ？ that are genuine information-seeking questions
- "complex_complements": sentences using resultative or directional complements (e.g. 看完, 走出来)
- "total_analysed": the number of sentences you analysed (should be {len(sampled)})"""

            result = call_llm(prompt)

            # Compute ratios from LLM counts
            n = result.get('total_analysed', len(sampled))
            if not isinstance(n, (int, float)) or n <= 0:
                n = len(sampled)

            llm_prefs = {}
            ratio_keys = [
                ('ba_constructions', 'ba_construction_ratio'),
                ('bei_passives', 'bei_passive_ratio'),
                ('topic_comment', 'topic_comment_ratio'),
                ('serial_verb', 'serial_verb_ratio'),
                ('aspect_le', 'aspect_le_ratio'),
                ('aspect_zhe', 'aspect_zhe_ratio'),
                ('aspect_guo', 'aspect_guo_ratio'),
                ('rhetorical_questions', 'rhetorical_question_ratio'),
                ('direct_questions', 'question_ratio'),
                ('complex_complements', 'complex_complement_ratio'),
            ]
            for llm_key, ratio_key in ratio_keys:
                count = result.get(llm_key, 0)
                if isinstance(count, (int, float)) and count >= 0:
                    llm_prefs[ratio_key] = round(count / n, 3)

            llm_prefs['total_sentences_analyzed'] = total
            llm_prefs['llm_sample_size'] = len(sampled)

            logger.info(
                f"Chinese syntactic analysis via LLM: "
                f"{len(llm_prefs) - 2} features extracted from {len(sampled)} sentences"
            )
            return llm_prefs

        except Exception as exc:
            logger.warning(
                f"LLM-based Chinese syntactic analysis failed: {exc}. "
                f"Falling back to regex counts."
            )
            return regex_result

    # ── E. Discourse Patterns ────────────────────────────────────────────

    def _extract_discourse_patterns(
        self,
        text: str,
        sentences: list[str],
    ) -> dict:
        """
        Analyse transition word usage, connective density, and sentence openers.
        Reuses discourse marker sets from CollocationClassifier.
        """
        lang_id = self.tokenizer.language_id
        marker_sets = {
            1: self.classifier.DISCOURSE_MARKERS_ZH,
            2: self.classifier.DISCOURSE_MARKERS_EN,
            3: self.classifier.DISCOURSE_MARKERS_JA,
        }
        markers = marker_sets.get(lang_id, frozenset())

        # Count discourse marker occurrences in the text
        text_lower = text.lower()
        marker_counts: Counter = Counter()
        for marker in markers:
            count = text_lower.count(marker.lower())
            if count > 0:
                marker_counts[marker] = count

        total_markers = sum(marker_counts.values())
        total_sentences = len(sentences)

        # Sentence openers: first 1-3 tokens of each sentence
        opener_counter: Counter = Counter()
        for sentence in sentences:
            tokens = self.tokenizer.tokenize(sentence)
            if tokens:
                # Use first 2 tokens as opener (or 1 if only 1 token)
                opener_len = min(2, len(tokens))
                opener = self.tokenizer.join_char.join(tokens[:opener_len])
                opener_counter[opener] += 1

        return {
            'connective_density': round(total_markers / total_sentences, 3) if total_sentences else 0.0,
            'total_discourse_markers': total_markers,
            'top_transitions': [
                {'text': marker, 'frequency': freq}
                for marker, freq in marker_counts.most_common(_TOP_K_TRANSITIONS)
            ],
            'sentence_openers': [
                {'text': opener, 'frequency': freq}
                for opener, freq in opener_counter.most_common(_TOP_K_OPENERS)
            ],
        }

    # ── F. Vocabulary Profile ────────────────────────────────────────────

    def _extract_vocabulary_profile(
        self,
        unigram_counts: Counter,
        total_tokens: int,
    ) -> dict:
        """
        Compute lexical diversity metrics and frequency distribution.
        """
        if total_tokens == 0:
            return {}

        # unigram_counts keys are tuples like ('word',) from extract_all_ngrams
        # Flatten to simple strings
        word_counts: Counter = Counter()
        for key, count in unigram_counts.items():
            word = key[0] if isinstance(key, tuple) else key
            word_counts[word] = count

        types = len(word_counts)
        tokens = total_tokens

        # Type-Token Ratio
        ttr = types / tokens if tokens > 0 else 0.0

        # Hapax legomena ratio
        hapax = sum(1 for c in word_counts.values() if c == 1)
        hapax_ratio = hapax / types if types > 0 else 0.0

        # Moving-Average TTR (MATTR)
        mattr = self._compute_mattr(word_counts, tokens)

        # Average word length (by characters)
        total_chars = sum(len(w) * c for w, c in word_counts.items())
        avg_word_length = total_chars / tokens if tokens > 0 else 0.0

        # Zipf frequency distribution
        lang_code = _LANG_ID_TO_WF.get(self.tokenizer.language_id)
        zipf_dist = {}
        if lang_code:
            band_counts = {f"{lo}-{hi}": 0 for lo, hi in _ZIPF_BANDS}
            unknown_count = 0
            for word in word_counts:
                score = get_zipf_score(word, lang_code)
                if score is None:
                    unknown_count += 1
                    continue
                placed = False
                for lo, hi in _ZIPF_BANDS:
                    if lo <= score < hi:
                        band_counts[f"{lo}-{hi}"] += 1
                        placed = True
                        break
                if not placed and score >= _ZIPF_BANDS[-1][1]:
                    band_counts[f"{_ZIPF_BANDS[-1][0]}-{_ZIPF_BANDS[-1][1]}"] += 1

            total_scored = sum(band_counts.values()) + unknown_count
            if total_scored > 0:
                zipf_dist = {
                    band: round(count / total_scored, 3)
                    for band, count in band_counts.items()
                }
                zipf_dist['unknown'] = round(unknown_count / total_scored, 3)

        return {
            'ttr': round(ttr, 4),
            'mattr': round(mattr, 4) if mattr else None,
            'hapax_ratio': round(hapax_ratio, 4),
            'avg_word_length': round(avg_word_length, 1),
            'unique_words': types,
            'zipf_distribution': zipf_dist,
        }

    def _compute_mattr(self, word_counts: Counter, total_tokens: int) -> float | None:
        """
        Compute Moving-Average Type-Token Ratio.

        MATTR slides a window across the token stream and averages the TTR
        of each window. More robust than simple TTR for varying text lengths.

        We approximate this from the unigram frequency distribution rather than
        reconstructing the full token stream, using a sampling approach.
        """
        if total_tokens < _MATTR_WINDOW:
            return None

        # Reconstruct a token stream from counts (order doesn't matter for MATTR
        # approximation since we're sampling windows)
        token_stream = []
        for word, count in word_counts.items():
            token_stream.extend([word] * count)

        # Shuffle would be ideal but is expensive; just compute windowed TTR
        # on the natural order
        ttrs = []
        for i in range(0, len(token_stream) - _MATTR_WINDOW + 1, _MATTR_WINDOW // 4):
            window = token_stream[i:i + _MATTR_WINDOW]
            ttrs.append(len(set(window)) / _MATTR_WINDOW)

        return sum(ttrs) / len(ttrs) if ttrs else None
