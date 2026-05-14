# services/exercise_generation/language_processor.py

import re
from abc import ABC, abstractmethod
from collections import defaultdict


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

    # Dependency labels that mark the head of a top-level constituent chunk.
    _CONSTITUENT_DEPS = frozenset({
        'nsubj', 'nsubjpass', 'csubj', 'csubjpass',
        'dobj', 'iobj', 'pobj', 'attr', 'oprd', 'dative',
        'prep', 'agent',
        'advcl', 'xcomp', 'ccomp', 'acl', 'relcl',
        'advmod', 'npadvmod', 'nmod',
        'conj', 'expl',
    })

    # Dependencies that stay glued to the ROOT verb (aux chain, negation, particle).
    _ROOT_INTERNAL_DEPS = frozenset({'aux', 'auxpass', 'neg', 'prt', 'cop'})

    def chunk_sentence(self, sentence: str) -> list[str]:
        doc = self.nlp(sentence)
        content_tokens = [t for t in doc if not t.is_punct and not t.is_space]
        if len(content_tokens) < 3:
            raise ValueError(
                f"EnglishProcessor.chunk_sentence: sentence too short: {sentence[:60]}"
            )

        root = next((t for t in doc if t.dep_ == 'ROOT'), None)
        if root is None:
            return self._fallback_chunk(doc, sentence)

        root_i = root.i

        def anchor_of(tok):
            """Walk up the dep tree until we hit ROOT or a constituent child of ROOT."""
            cur = tok
            seen = set()
            while cur.i not in seen:
                seen.add(cur.i)
                if cur.i == root_i:
                    return root
                if cur.head.i == root_i:
                    if cur.dep_ in self._ROOT_INTERNAL_DEPS:
                        return root
                    return cur
                if cur.head.i == cur.i:
                    return cur
                cur = cur.head
            return cur

        groups: dict[int, list] = defaultdict(list)
        for tok in doc:
            if tok.is_punct or tok.is_space:
                continue
            anchor = anchor_of(tok)
            groups[anchor.i].append(tok)

        # Each entry is (sorted_tokens, anchor_token).
        chunk_entries = sorted(
            ((sorted(toks, key=lambda x: x.i), doc[anchor_i])
             for anchor_i, toks in groups.items()),
            key=lambda e: e[0][0].i,
        )

        # Merge a single-token pronoun subject with the adjacent verb chunk,
        # so "She | made | ..." becomes "She made | ..." but a multi-word
        # subject NP like "The quick brown fox | jumps | ..." is preserved.
        chunk_entries = self._merge_pronoun_subject(chunk_entries, root_i)

        chunks = [' '.join(t.text for t in toks) for toks, _ in chunk_entries]

        # Merge a function-word singleton forward into the constituent it introduces.
        chunks = self._merge_function_word_leaders(chunks, doc)

        # Cap at 6 by merging the two smallest adjacent chunks repeatedly.
        while len(chunks) > 6:
            best_i, best_size = 0, float('inf')
            for i in range(len(chunks) - 1):
                sz = len(chunks[i].split()) + len(chunks[i + 1].split())
                if sz < best_size:
                    best_size = sz
                    best_i = i
            chunks = (
                chunks[:best_i]
                + [chunks[best_i] + ' ' + chunks[best_i + 1]]
                + chunks[best_i + 2:]
            )

        if len(chunks) < 3:
            return self._fallback_chunk(doc, sentence)

        return chunks

    def _merge_pronoun_subject(self, entries, root_i):
        """If the nsubj/nsubjpass chunk is a single-token pronoun directly
        before the verb chunk, merge them. Skipped if doing so would drop
        total chunks below 3.
        """
        if len(entries) < 3:
            return entries
        for idx in range(len(entries) - 1):
            toks, anchor = entries[idx]
            if anchor.dep_ not in {'nsubj', 'nsubjpass'}:
                continue
            if len(toks) != 1:
                continue
            if toks[0].pos_ not in {'PRON'}:
                continue
            next_toks, next_anchor = entries[idx + 1]
            if next_anchor.i != root_i:
                continue
            # Merge.
            merged_toks = sorted(toks + next_toks, key=lambda t: t.i)
            new_entries = (
                entries[:idx]
                + [(merged_toks, next_anchor)]
                + entries[idx + 2:]
            )
            if len(new_entries) >= 3:
                return new_entries
            return entries
        return entries

    def _merge_function_word_leaders(self, chunks: list[str], doc) -> list[str]:
        """If a chunk is a single function-word token (DET/ADP/CCONJ/PART/SCONJ),
        merge it forward into the next chunk rather than letting it dangle."""
        FUNC_POS = {'DET', 'ADP', 'CCONJ', 'PART', 'SCONJ'}
        # Build a quick lookup from token text → pos tag for the first occurrence.
        # (For single-token chunks the text is unambiguous in context.)
        pos_lookup = {}
        for tok in doc:
            pos_lookup.setdefault(tok.text, tok.pos_)

        out: list[str] = []
        i = 0
        while i < len(chunks):
            cur = chunks[i]
            words = cur.split()
            if (
                len(words) == 1
                and pos_lookup.get(words[0]) in FUNC_POS
                and i + 1 < len(chunks)
            ):
                # Merge forward
                out.append(cur + ' ' + chunks[i + 1])
                i += 2
            else:
                out.append(cur)
                i += 1
        return out

    def _fallback_chunk(self, doc, sentence: str) -> list[str]:
        """Fallback for sentences where dep-parse yields too few constituents."""
        noun_chunks = list(doc.noun_chunks)
        if len(noun_chunks) >= 2:
            chunks: list[str] = []
            prev_end = 0
            for nc in noun_chunks:
                between = doc[prev_end:nc.start]
                btxt = ' '.join(t.text for t in between
                                if not t.is_punct and not t.is_space).strip()
                if btxt:
                    chunks.append(btxt)
                chunks.append(nc.text.strip())
                prev_end = nc.end
            tail = doc[prev_end:]
            ttxt = ' '.join(t.text for t in tail
                            if not t.is_punct and not t.is_space).strip()
            if ttxt:
                chunks.append(ttxt)
            chunks = [c for c in chunks if c]
            if len(chunks) >= 3:
                return chunks[:6]

        parts = self._simple_split(sentence)
        if len(parts) >= 3:
            return parts[:6]

        raise ValueError(
            f"EnglishProcessor.chunk_sentence: only {len(parts)} chunks for: {sentence[:60]}"
        )

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
    PUNCTUATION = frozenset('，。、！？；：""''（）【】《》—…·')
    CLAUSE_BOUNDARY_PUNCT = frozenset('，、；')

    # Particles / aspectual markers that always cling to the preceding chunk.
    _STICKY_BACK = frozenset({'了', '的', '着', '过', '吗', '呢', '吧', '啊', '哦', '嘛'})

    # POS-tag prefixes that start a new chunk (coverbs, conjunctions).
    _CHUNK_STARTERS_POS = frozenset({'p', 'c'})

    # POS prefixes treated as nominal for the NP→predicate transition rule.
    _NOMINAL_POS = frozenset({'n', 'r', 'm', 'q', 't', 'f', 's'})

    # POS prefixes treated as predicate-leading (split when preceded by nominal).
    _PREDICATE_TRIGGER_POS = frozenset({'v', 'a', 'z', 'd'})

    def split_sentences(self, text: str) -> list[str]:
        parts = self.SENTENCE_END_PATTERN.split(text)
        return [p.strip() for p in parts if p.strip()]

    def tokenize(self, sentence: str) -> list[str]:
        import jieba
        return [t for t in jieba.cut(sentence, cut_all=False)
                if t.strip() and t not in self.PUNCTUATION]

    def chunk_sentence(self, sentence: str) -> list[str]:
        """Chunk a Chinese sentence into 3–6 phrase-level groups.

        Strategy: walk jieba.posseg tokens. Start a new chunk on coverb (p)
        or conjunction (c), at clause-boundary punctuation, or when the POS
        transitions from a nominal (n/r/m/q/t) to a verbal (v/a) — i.e. the
        natural NP→VP break. Particles (了, 的, 着, ...) always cling to the
        preceding chunk.
        """
        import jieba.posseg as pseg
        tagged = [(w.word, w.flag) for w in pseg.cut(sentence)]
        # Strip punctuation from the token stream but remember clause breaks.
        # Insert a synthetic ('', '<BOUND>') marker for clause-boundary punct.
        cleaned: list[tuple[str, str]] = []
        for word, flag in tagged:
            if word in self.CLAUSE_BOUNDARY_PUNCT:
                cleaned.append(('', '<BOUND>'))
            elif word in self.PUNCTUATION or not word.strip():
                continue
            else:
                cleaned.append((word, flag))

        chunks: list[str] = []
        current: list[str] = []
        last_pos: str | None = None

        def flush():
            if current:
                chunks.append(''.join(current))
                current.clear()

        for word, flag in cleaned:
            if flag == '<BOUND>':
                flush()
                last_pos = None
                continue

            pos_prefix = flag[0] if flag else ''

            # Particles stick to the previous chunk.
            if word in self._STICKY_BACK or pos_prefix == 'u':
                if current:
                    current.append(word)
                elif chunks:
                    chunks[-1] = chunks[-1] + word
                else:
                    current.append(word)
                last_pos = pos_prefix
                continue

            # Determine whether this token starts a new chunk.
            starts_new = False
            if not current:
                starts_new = False  # first token of a chunk, just begin
            elif pos_prefix in self._CHUNK_STARTERS_POS:
                starts_new = True
            elif last_pos in self._NOMINAL_POS and pos_prefix in self._PREDICATE_TRIGGER_POS:
                # NP → VP transition (nominal followed by predicate head).
                starts_new = True

            if starts_new:
                flush()
            current.append(word)
            last_pos = pos_prefix

        flush()

        # Enforce max 6 by merging the two shortest adjacent chunks repeatedly.
        while len(chunks) > 6:
            best_i, best_size = 0, 10**9
            for i in range(len(chunks) - 1):
                sz = len(chunks[i]) + len(chunks[i + 1])
                if sz < best_size:
                    best_size = sz
                    best_i = i
            chunks = (
                chunks[:best_i]
                + [chunks[best_i] + chunks[best_i + 1]]
                + chunks[best_i + 2:]
            )

        # If too few, fall back to a coarser jieba-only split (every ~4 tokens).
        if len(chunks) < 3:
            chunks = self._fallback_chunk(sentence)

        if len(chunks) < 3:
            raise ValueError(
                f"ChineseProcessor.chunk_sentence: only {len(chunks)} chunks for: {sentence[:40]}"
            )
        return chunks

    def _fallback_chunk(self, sentence: str) -> list[str]:
        import jieba
        toks = [t for t in jieba.cut(sentence, cut_all=False)
                if t.strip() and t not in self.PUNCTUATION]
        if len(toks) < 3:
            return toks
        # Aim for 3-4 chunks: roughly even split.
        target = min(4, max(3, len(toks) // 2))
        size = max(1, len(toks) // target)
        out, buf = [], []
        for t in toks:
            buf.append(t)
            if len(buf) >= size and len(out) < target - 1:
                out.append(''.join(buf))
                buf = []
        if buf:
            out.append(''.join(buf))
        return out


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
        """Bunsetsu-aware chunking. A chunk = content tokens + their closing
        particle (ADP / case / mark). Punctuation and whitespace are dropped
        but force a chunk boundary.
        """
        doc = self.nlp(sentence)
        chunks: list[str] = []
        current: list[str] = []

        for token in doc:
            if token.is_space:
                continue
            if token.is_punct:
                if current:
                    chunks.append(''.join(current))
                    current = []
                continue
            current.append(token.text)
            if token.pos_ == 'ADP' or token.dep_ in ('case', 'mark'):
                chunks.append(''.join(current))
                current = []

        if current:
            chunks.append(''.join(current))

        chunks = [c for c in chunks if c.strip()]

        # Cap at 6 by merging shortest adjacent.
        while len(chunks) > 6:
            best_i, best_size = 0, 10**9
            for i in range(len(chunks) - 1):
                sz = len(chunks[i]) + len(chunks[i + 1])
                if sz < best_size:
                    best_size = sz
                    best_i = i
            chunks = (
                chunks[:best_i]
                + [chunks[best_i] + chunks[best_i + 1]]
                + chunks[best_i + 2:]
            )

        if len(chunks) < 3:
            raise ValueError(
                f"JapaneseProcessor.chunk_sentence: only {len(chunks)} chunks for: {sentence[:40]}"
            )
        return chunks


def prepare_jumbled_content(content: dict, language_id: int) -> dict:
    """Transform stored jumbled_sentence content into frontend-ready format.

    Takes content with just 'original_sentence' and returns content with
    'chunks' (multi-word phrase groups via the language-specific
    chunk_sentence) and 'correct_ordering' added. Falls back to word-level
    tokenisation only if chunk_sentence cannot produce ≥3 chunks.
    """
    sentence = content['original_sentence']
    processor = LanguageProcessor.for_language(language_id)
    try:
        chunks = processor.chunk_sentence(sentence)
    except (ValueError, Exception):
        chunks = processor.tokenize(sentence)
        if len(chunks) < 2:
            chunks = [sentence]
    return {
        'original_sentence': sentence,
        'chunks': chunks,
        'correct_ordering': list(range(len(chunks))),
    }
