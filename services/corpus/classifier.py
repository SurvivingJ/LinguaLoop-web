from services.corpus.tokenizers import LanguageTokenizer, _get_nlp_en, _get_nlp_ja
from services.corpus.constants import (
    EN_QUOTE_ANCHORS,
    ZH_QUOTE_ANCHORS, ZH_LIGHT_SCAFFOLD_NOUNS,
    JA_QUOTE_ANCHORS, JA_LIGHT_SCAFFOLD_NOUNS,
)


class CollocationClassifier:
    """
    Classify scored n-grams and extract POS patterns.
    One instance per LanguageTokenizer — the tokenizer provides the
    language_id and POS tagging method.
    """

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

    DISCOURSE_MARKERS_ZH: frozenset = frozenset({
        '换句话说', '另一方面', '除此之外', '总而言之', '与此同时',
        '尽管如此', '事实上', '从某种意义上说', '比如说', '例如',
    })

    DISCOURSE_MARKERS_JA: frozenset = frozenset({
        'つまり', 'そのため', 'したがって', 'それに対して', 'その一方で',
        'さらに', '例えば', '具体的には', 'とはいえ', 'にもかかわらず',
    })

    FIXED_PHRASE_PMI_THRESHOLD: float = 6.0

    DISCOURSE_LEADING_PREPS_EN: frozenset = frozenset({
        'in', 'on', 'at', 'as', 'by', 'for', 'of', 'to', 'with',
        'from', 'into', 'over', 'under', 'about', 'through',
    })

    COARSE_POS_MAP: dict = {
        'NOUN': 'NOUN', 'PROPN': 'NOUN', 'VERB': 'VERB', 'AUX': 'VERB',
        'ADJ': 'ADJ', 'ADV': 'ADV', 'ADP': 'PREP', 'DET': 'DET',
        'CONJ': 'CONJ', 'CCONJ': 'CONJ', 'SCONJ': 'CONJ',
        'NUM': 'NUM', 'PART': 'PART', 'PRON': 'PRON',
    }

    # Linguistically motivated POS patterns worth teaching.
    # Collocations whose POS pattern is not in this set are dropped
    # (discourse_markers and fixed_phrases are exempt).
    VALID_POS_PATTERNS_EN: frozenset = frozenset({
        'VERB+NOUN', 'VERB+DET+NOUN', 'VERB+ADJ+NOUN',
        'ADJ+NOUN',
        'NOUN+NOUN',
        'NOUN+PREP+NOUN',
        'ADV+VERB', 'ADV+ADJ',
        'VERB+PREP+NOUN',
        'PREP+DET+NOUN', 'PREP+ADJ+NOUN', 'PREP+NOUN',
        'VERB+PRON',
        'DET+NOUN',
        'DET+ADJ+NOUN',
    })

    VALID_POS_PATTERNS_JA: frozenset = frozenset({
        'VERB+NOUN', 'ADJ+NOUN', 'NOUN+NOUN', 'NOUN+VERB',
        'ADV+VERB', 'ADV+ADJ',
    })

    VALID_POS_PATTERNS_ZH: frozenset = frozenset({
        'VERB+NOUN', 'ADJ+NOUN', 'NOUN+NOUN', 'NOUN+VERB',
        'ADV+VERB', 'ADV+ADJ',
        'VERB+VERB',                  # serial verb constructions
        'PREP+NOUN', 'PREP+VERB',     # prepositional phrases
        'NOUN+PREP+NOUN',             # NP-PP-NP
        'VERB+ADJ',                   # resultative complements
        'DET+NOUN',                   # classifier + noun
    })

    def __init__(self, tokenizer: LanguageTokenizer):
        self.tokenizer = tokenizer
        self._marker_sets = {
            1: self.DISCOURSE_MARKERS_ZH,
            2: self.DISCOURSE_MARKERS_EN,
            3: self.DISCOURSE_MARKERS_JA,
        }

    def is_valid_collocation(self, ngram_tokens: list[str]) -> bool:
        """
        Return False if this n-gram contains a quote anchor or is a bare
        scaffold-noun bigram. Short-circuits on first failure.

        Args:
            ngram_tokens: Token list (split from collocation_text).
        Returns:
            True if the n-gram should be kept.
        """
        lang_id = self.tokenizer.language_id
        token_set = set(ngram_tokens)

        if lang_id == 2:  # English
            if token_set & EN_QUOTE_ANCHORS:
                return False

        elif lang_id == 1:  # Chinese
            if token_set & ZH_QUOTE_ANCHORS:
                return False
            if len(ngram_tokens) == 2 and ngram_tokens[-1] in ZH_LIGHT_SCAFFOLD_NOUNS:
                return False

        elif lang_id == 3:  # Japanese
            if token_set & JA_QUOTE_ANCHORS:
                return False
            if len(ngram_tokens) == 2 and ngram_tokens[-1] in JA_LIGHT_SCAFFOLD_NOUNS:
                return False

        return True

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

    # jieba POS flags → coarse Universal POS mapping
    # See: https://github.com/fxsjy/jieba (POS tagging)
    _JIEBA_POS_MAP: dict = {
        'n': 'NOUN', 'nr': 'NOUN', 'ns': 'NOUN', 'nt': 'NOUN', 'nz': 'NOUN',
        'ng': 'NOUN', 'nrt': 'NOUN', 'nrfg': 'NOUN',
        'v': 'VERB', 'vd': 'VERB', 'vn': 'VERB', 'vg': 'VERB',
        'a': 'ADJ', 'ad': 'ADJ', 'an': 'ADJ', 'ag': 'ADJ',
        'd': 'ADV',
        'p': 'PREP',
        'r': 'PRON',
        'm': 'NUM', 'mq': 'NUM',
        'q': 'DET',   # classifier/measure word → DET for consistency
        'c': 'CONJ',
        'u': 'PART', 'uj': 'PART', 'ud': 'PART', 'uv': 'PART', 'ul': 'PART',
        'e': 'PART',  # interjection
        'f': 'NOUN',  # directional noun
        's': 'NOUN',  # place
        't': 'NOUN',  # time
        'b': 'ADJ',   # distinguishing word (区别词) → ADJ
        'z': 'ADJ',   # status word (状态词) → ADJ
        'l': 'NOUN',  # idiom component
        'i': 'NOUN',  # idiom
    }

    def get_pos_pattern(self, text: str) -> str:
        """
        Return a '+'-separated string of coarse POS tags for the n-gram.
        Examples: 'VERB+NOUN', 'PREP+DET+NOUN', 'ADJ+NOUN'

        For Chinese (language_id=1): uses jieba POS tags mapped to
        Universal POS via _JIEBA_POS_MAP.  Falls back to LLM for
        unresolvable cases.
        """
        if self.tokenizer.language_id == 1:
            return self._get_chinese_pos_pattern(text)

        pairs = self.tokenizer.tokenize_with_pos(text)
        tags = [
            self.COARSE_POS_MAP.get(pos, pos)
            for _, pos in pairs
            if pos not in ('PUNCT', 'SPACE', 'X', '')
        ]
        return '+'.join(tags)

    def _get_chinese_pos_pattern(self, text: str) -> str:
        """
        Get POS pattern for Chinese text using jieba POS tags.

        jieba's POS tagger provides granular flags (n, v, a, d, p, etc.)
        that we map to the same coarse POS set used for EN/JA.
        """
        pairs = self.tokenizer.tokenize_with_pos(text)
        if not pairs:
            return 'UNKNOWN'

        tags = []
        for _, flag in pairs:
            coarse = self._JIEBA_POS_MAP.get(flag)
            if coarse:
                tags.append(coarse)
            elif flag and flag not in ('x', 'w', ''):
                # Unknown jieba flag — skip punctuation-like tags
                tags.append(flag.upper())

        return '+'.join(tags) if tags else 'UNKNOWN'

    def is_valid_pattern(self, pos_pattern: str) -> bool:
        """Return True if pos_pattern is a linguistically motivated collocation structure."""
        if not pos_pattern or pos_pattern == 'UNKNOWN':
            return True  # Don't filter when POS tagging is unavailable
        lang_id = self.tokenizer.language_id
        if lang_id == 2:
            valid_set = self.VALID_POS_PATTERNS_EN
        elif lang_id == 3:
            valid_set = self.VALID_POS_PATTERNS_JA
        elif lang_id == 1:
            valid_set = self.VALID_POS_PATTERNS_ZH
        else:
            return True
        return pos_pattern in valid_set

    def classify_and_tag(
        self,
        text: str,
        pmi: float,
        frequency: int,
        n: int
    ) -> dict:
        """
        Run classify_collocation and get_pos_pattern together.
        Returns {'collocation_type': str, 'pos_pattern': str}.
        """
        return {
            'collocation_type': self.classify_collocation(text, pmi, frequency, n),
            'pos_pattern':      self.get_pos_pattern(text),
        }

    def discover_discourse_markers(
        self,
        candidates: list[dict],
    ) -> set[str]:
        """
        Use an LLM to identify discourse markers among high-PMI n-grams
        that are not in the static frozensets.

        Args:
            candidates: List of collocation dicts. Only n-grams with
                        n_gram_size >= 2 and pmi_score >= 4.0 are sent.

        Returns:
            Set of collocation_text strings that the LLM identified as
            discourse markers or fixed transition phrases.
        """
        import logging
        logger = logging.getLogger(__name__)

        lang_id = self.tokenizer.language_id
        lang_names = {1: 'Chinese', 2: 'English', 3: 'Japanese'}
        language = lang_names.get(lang_id, 'Unknown')

        # Filter to multi-word, high-PMI candidates not already classified
        marker_set = self._marker_sets.get(lang_id, frozenset())
        filtered = [
            c for c in candidates
            if c.get('n_gram_size', 0) >= 2
            and c.get('pmi_score', 0) >= 4.0
            and c['collocation_text'].lower().strip() not in marker_set
        ]

        if not filtered:
            return set()

        # Cap at 120 candidates per LLM call
        filtered = filtered[:120]

        numbered = '\n'.join(
            f"{i+1}. \"{c['collocation_text']}\" (PMI={c.get('pmi_score', 0)}, freq={c.get('frequency', 0)})"
            for i, c in enumerate(filtered)
        )

        prompt = f"""You are a {language} linguistics expert. Below is a list of statistically significant multi-word expressions extracted from a {language} corpus.

Identify which of these are **discourse markers** or **fixed transition phrases** — expressions used to organise discourse, signal relationships between clauses, or connect ideas (e.g. "on the other hand", "as a result", "in addition").

Do NOT include:
- Regular collocations (verb+noun, adj+noun combinations like "strong wind")
- Content phrases that are topic-specific
- Proper nouns or names

Return a JSON object with a single key "discourse_markers" containing an array of objects, each with:
- "index": the item number (1-based)
- "text": the exact expression text

Only include items you are confident are discourse markers or transition phrases.

Candidates:
{numbered}"""

        try:
            from services.corpus.llm_client import call_llm
            result = call_llm(prompt)
            markers = result.get('discourse_markers', [])

            discovered = set()
            for m in markers:
                text = m.get('text', '').strip()
                if text:
                    discovered.add(text.lower())

            if discovered:
                logger.info(
                    f"LLM discovered {len(discovered)} new discourse markers: "
                    f"{list(discovered)[:5]}..."
                )

            return discovered

        except Exception as exc:
            logger.warning(f"Discourse marker discovery failed: {exc}")
            return set()
