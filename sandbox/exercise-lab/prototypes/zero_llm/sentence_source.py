"""
Sentence sourcing for the zero-LLM path — the crux measurement (task 2).

``cloze_typed`` and ``jumbled_sentence`` both need a real sentence containing
the target word (production gets this from an LLM's P1 ``sentences`` output).
Without an LLM there are exactly three candidate sources, and this module
measures all three honestly rather than assuming the seeded
``dim_word_senses.example_sentence`` column is representative:

  (a) ``dim_word_senses.example_sentence`` — already populated by
      ``db/build_db.py``, but only for the top ``EMBED_TOP_N_PER_LANGUAGE``
      (8,000) senses per language, and via *substring* matching
      (``lemma in sentence``), which over-counts for CJK (a single-character
      lemma matches inside any longer word that contains that character).
  (b) sentences mined from the 153-test/765-question corpus using REAL
      tokenisation — this module's own contribution. Reuses
      ``services.exercise_generation.language_processor.LanguageProcessor``
      (real jieba for zh, real fugashi-backed spaCy pipeline for ja, real
      spaCy for en — the same production tokenisers, DB-free, no LLM) via its
      ``contains_whole_word`` method, which is CJK-safe (rejects a token
      match found only *inside* a longer word).
  (c) CC-CEDICT / JMdict native example-sentence fields — checked and
      confirmed EMPTY. CC-CEDICT's format has no example-sentence field at
      all; the JMdict JSON used here (``raw/jmdict_eng.json``) has only
      ``kanji``/``kana``/``sense.gloss``, no ``examples`` key. This source
      contributes 0 sentences for every language, always — not a bug, a
      property of the source dictionaries.

For performance (source (b) needs to test up to 121,159 zh lemmas against a
tiny corpus), sentences are tokenised ONCE per corpus sentence, not once per
(lemma, sentence) pair like a naive port of ``contains_whole_word`` would.
Every contiguous run of tokens (bounded to 6 tokens per anchor, mirroring
``contains_whole_word``'s own contiguous-run check) is added to a per-language
set, so a lemma lookup after that is an O(1) set membership test.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from services.exercise_generation.language_processor import LanguageProcessor

_MAX_RUN = 6  # tokens; matches contains_whole_word's implicit bound (len(word))

_EN_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n")
_CJK_SPLIT_RE = re.compile(r"[。！？\n]")


@dataclass
class SentenceIndex:
    language_id: int
    # lemma (exact surface match) -> one real corpus sentence containing it
    by_lemma: dict[str, str] = field(default_factory=dict)
    n_corpus_sentences: int = 0

    def find(self, lemma: str) -> str | None:
        return self.by_lemma.get(lemma)


def _split_sentences(text: str, language_id: int) -> list[str]:
    splitter = _EN_SPLIT_RE if language_id == 2 else _CJK_SPLIT_RE
    return [s.strip() for s in splitter.split(text) if s and s.strip()]


def build_sentence_index(conn: sqlite3.Connection, language_id: int) -> SentenceIndex:
    """Mine every test transcript for this language into a lemma -> sentence
    map, using the REAL production tokenizer (not substring matching)."""
    rows = conn.execute(
        "SELECT transcript FROM tests WHERE language_id = ?", (language_id,)
    ).fetchall()
    processor = LanguageProcessor.for_language(language_id)

    index = SentenceIndex(language_id=language_id)
    for row in rows:
        for sentence in _split_sentences(row["transcript"], language_id):
            try:
                tokens = processor.tokenize(sentence)
            except Exception:
                continue
            if not tokens:
                continue
            index.n_corpus_sentences += 1
            case = str.lower if language_id == 2 else (lambda s: s)
            tokens = [case(t) for t in tokens if t.strip()]
            sep = " " if language_id == 2 else ""
            n = len(tokens)
            for i in range(n):
                run_tokens: list[str] = []
                for j in range(i, min(i + _MAX_RUN, n)):
                    run_tokens.append(tokens[j])
                    acc = sep.join(run_tokens)
                    # First occurrence wins — later sentences don't overwrite,
                    # so a run's example is always the earliest one mined.
                    index.by_lemma.setdefault(acc, sentence)
    return index


def measure_coverage(
    conn: sqlite3.Connection, language_id: int, index: SentenceIndex
) -> dict:
    """Fill-rate numbers for sources (a) and (b) against the FULL vocab for
    this language (not the 8,000-cap subset build_db.py embedded)."""
    total_vocab = conn.execute(
        "SELECT COUNT(*) c FROM dim_vocabulary WHERE language_id = ?",
        (language_id,),
    ).fetchone()["c"]

    case = str.lower if language_id == 2 else (lambda s: s)
    lemmas = [
        r["lemma"] for r in conn.execute(
            "SELECT lemma FROM dim_vocabulary WHERE language_id = ?", (language_id,)
        )
    ]
    mined_hits = sum(1 for lemma in lemmas if case(lemma) in index.by_lemma)

    example_col = conn.execute(
        """SELECT COUNT(DISTINCT v.id) c FROM dim_vocabulary v
           JOIN dim_word_senses ws ON ws.vocab_id = v.id
           WHERE v.language_id = ? AND ws.example_sentence IS NOT NULL
           AND ws.example_sentence != ''""",
        (language_id,),
    ).fetchone()["c"]

    return {
        "language_id": language_id,
        "total_vocab": total_vocab,
        "corpus_sentences_available": index.n_corpus_sentences,
        "example_sentence_column_filled": example_col,
        "example_sentence_column_pct": round(100 * example_col / total_vocab, 2) if total_vocab else 0.0,
        "tokenized_corpus_mined_filled": mined_hits,
        "tokenized_corpus_mined_pct": round(100 * mined_hits / total_vocab, 2) if total_vocab else 0.0,
        "cedict_jmdict_native_examples": 0,  # confirmed absent from both sources, see module docstring
    }


def sentence_for_lemma(
    conn: sqlite3.Connection,
    language_id: int,
    lemma: str,
    example_sentence: str | None,
    index: SentenceIndex,
) -> dict | None:
    """Best available real sentence for this lemma, preferring the already
    -seeded example_sentence column (source a) and falling back to the
    tokenized corpus mine (source b). None if neither has one — this is the
    honest gate that starves cloze_typed/jumbled_sentence of a sense with no
    real sentence anywhere, exactly as production starves them of a sense P1
    never generated one for.
    """
    text = (example_sentence or "").strip()
    if not text:
        case = str.lower if language_id == 2 else (lambda s: s)
        text = index.find(case(lemma)) or ""
    if not text:
        return None
    return {
        "text": text,
        "target_word": lemma,
        "source": "example_sentence_column" if (example_sentence or "").strip() else "corpus_mined",
        "complexity_tier": None,
    }
