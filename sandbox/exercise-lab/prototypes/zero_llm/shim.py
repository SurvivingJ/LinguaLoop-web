"""
The sqlite ``ctx.db`` shim (task 1) — makes the REAL production deterministic
builders (``services/vocabulary_ladder/deterministic/*.py``) run against
``db/lab.sqlite`` completely unmodified.

How it works
------------
``classifier_match.py``, ``counter_match.py``, ``definition_match.py`` and
``readings.py`` each do ``from services.vocabulary_ladder.deterministic.
dictionaries import get_index`` / ``...lexicon import get_lexicon`` at module
level. Python's import machinery resolves ``from package.module import name``
by first checking ``sys.modules['package.module']`` — if that key is already
present, it is used AS-IS with no re-execution of the real file. So this
module pre-registers ``prototypes/zero_llm/dictionaries.py`` and
``prototypes/zero_llm/lexicon.py`` (sqlite-backed re-implementations of the
exact same public contract — ``get_index(conn, kind, language_id)`` /
``get_lexicon(conn, language_id)`` — see those files' own banners) under the
production module names, THEN triggers the real package's builder-loading
sweep. Every builder module that runs after that point is the genuine,
unmodified production file; only the two DB-touching leaf modules were
swapped, and ``ctx.db`` is simply the sqlite3 connection they now expect.

``classifier_match``, ``counter_match``, ``cloze_typed``, ``definition_match``,
``jumbled_sentence`` and the four ``readings.py`` types (``hanzi_to_pinyin``,
``pinyin_to_hanzi``, ``kanji_to_reading``, ``reading_to_kanji``) all become
reachable this way. ``tone_id_word`` needed no shim at all (phonology.py is
pure string logic, copied verbatim into this prototype directory per its own
banner, but the registered production ``tone.py`` builder is what actually
runs here — it imports ``deterministic.phonology``, which is DB-free and was
never shimmed).
"""

from __future__ import annotations

import sqlite3
import sys
import threading
from dataclasses import dataclass

import prototypes.zero_llm.dictionaries as sb_dictionaries
import prototypes.zero_llm.lexicon as sb_lexicon
from prototypes.zero_llm.semantic_class import classify
from prototypes.zero_llm.sentence_source import SentenceIndex, sentence_for_lemma

_INSTALLED = False
_LOCK = threading.Lock()


def install():
    """Idempotently install the shim and return the real `deterministic`
    package with all seven builder modules loaded against it."""
    global _INSTALLED
    with _LOCK:
        if not _INSTALLED:
            sys.modules["services.vocabulary_ladder.deterministic.dictionaries"] = sb_dictionaries
            sys.modules["services.vocabulary_ladder.deterministic.lexicon"] = sb_lexicon
            _INSTALLED = True
    import services.vocabulary_ladder.deterministic as det
    det._load_builders()
    return det


# ---------------------------------------------------------------------------
# Zipf-decile tiering, replicated from prototypes/zero_llm/lexicon.get_lexicon
# so ctx.tier and the shimmed lexicon's LexEntry.tier are computed identically
# (both must agree for definition_match's tier-matching to mean anything).
# ---------------------------------------------------------------------------

_decile_cache: dict[int, dict[int, int]] = {}


def _decile_table(conn: sqlite3.Connection, language_id: int) -> dict[int, int]:
    if language_id in _decile_cache:
        return _decile_cache[language_id]
    import bisect
    rows = conn.execute(
        "SELECT id, frequency_rank FROM dim_vocabulary WHERE language_id = ?",
        (language_id,),
    ).fetchall()
    freqs = sorted(r["frequency_rank"] for r in rows if r["frequency_rank"] is not None)
    table: dict[int, int] = {}
    for r in rows:
        f = r["frequency_rank"]
        if f is None or not freqs:
            continue
        pos = bisect.bisect_left(freqs, f) / max(len(freqs), 1)
        table[r["id"]] = min(9, int(pos * 10))
    _decile_cache[language_id] = table
    return table


@dataclass
class SenseFactory:
    """Builds a real `SenseContext` for one sense, sourcing everything from
    lab.sqlite (no LLM, no Supabase) — this is the in-memory
    `assets['prompt1_core']` construction the task calls for, wired directly
    into SenseContext rather than through a fake `_load_assets` return value
    (the two are equivalent: `LadderExerciseRenderer.build_rows` only ever
    uses `prompt1_core` to build a SenseContext itself)."""

    conn: sqlite3.Connection
    sentence_indices: dict[int, SentenceIndex]

    def context_for(self, sense_row: dict, variant: str = "A"):
        from services.vocabulary_ladder.deterministic import SenseContext
        from services.vocabulary_ladder.config import (
            SENTENCE_ASSIGNMENTS_A, SENTENCE_ASSIGNMENTS_B,
        )

        language_id = sense_row["language_id"]
        lemma = sense_row["lemma"]
        definition = (sense_row["definition"] or "").strip() or None
        pronunciation = (sense_row["pronunciation"] or "").strip() or None
        pos = sense_row["part_of_speech"]
        semantic_class = classify(language_id, pos, definition)

        sentence = sentence_for_lemma(
            self.conn, language_id, lemma,
            sense_row["example_sentence"], self.sentence_indices[language_id],
        )
        sentences = [sentence] if sentence else []

        core = {
            "definition": definition,
            "pronunciation": pronunciation,
            "semantic_class": semantic_class,
            "morphological_forms": [],  # FIDELITY GAP: not derivable without an LLM; see README §7
            "sentences": sentences,
        }

        assignments = SENTENCE_ASSIGNMENTS_A if variant == "A" else SENTENCE_ASSIGNMENTS_B
        tier = _decile_table(self.conn, language_id).get(sense_row["vocab_id"])

        return SenseContext(
            sense_id=sense_row["sense_id"],
            language_id=language_id,
            lemma=lemma,
            core=core,
            semantic_class=semantic_class,
            tier=tier,
            pronunciation=pronunciation,
            definition=definition,
            db=self.conn,
            nl_language_code="en",
            variant=variant,
            sentence_assignments=assignments,
        )
