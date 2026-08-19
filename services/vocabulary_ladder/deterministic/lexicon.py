"""
Per-language lexicon index — the corpus lookup deterministic builders share.

Several generators need to ask the same kinds of question about the *rest* of
the vocabulary, not just the sense in hand:

  * ``definition_match`` — "give me three definitions from senses at this
    word's tier" (a C2 definition among A1 options is answerable without
    knowing the word).
  * ``pinyin_to_hanzi`` / ``reading_to_kanji`` — "give me three real words that
    share this reading" (TASK-529's homophone index), then "three that share a
    character component", then frequency-band filler.

Doing that with one query per sense would be ~9,000 round trips in a full
three-language batch. Instead each language's lexicon is loaded once into
memory — a few thousand rows — and every builder queries the local structure.

Distinct from ``VocabularyKnowledgeService.get_distractors``, which is a
per-sense RPC with no tier guard: that call is still correct for the serve
path, where one round trip is cheap and the corpus may have moved.

Cache lifetime
--------------
Process-lifetime, keyed by language. The batch runner is a short-lived process
and the corpus does not change under it; a long-running web process that
renders the odd sense on demand gets a slightly stale frequency picture, which
costs nothing because these are *distractors*. :func:`reset_cache` exists for
tests and for the queue drain, which may run after a backfill has added senses.

Degradation
-----------
Every accessor returns ``[]`` rather than raising when the database is absent
or a table is empty. ``dim_character_components`` in particular is populated by
a separate licensed import (TASK-529) and may legitimately not exist yet — the
reverse-reading generator must still work off homophones alone.
"""

from __future__ import annotations

import logging
import random
import re
import threading
import unicodedata
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_PAGE = 1000            # supabase-py caps a select at 1000 rows by default


@dataclass
class LexEntry:
    """One sense, flattened to what a distractor picker needs."""

    sense_id: int
    lemma: str
    definition: str
    pronunciation: str
    reading_key: str                 # normalised pronunciation, for homophones
    tier: str | None
    frequency: float | None
    semantic_class: str | None
    sense_rank: int | None


@dataclass
class Lexicon:
    """An in-memory slice of one language's vocabulary."""

    language_id: int
    entries: list[LexEntry] = field(default_factory=list)
    by_reading: dict[str, list[LexEntry]] = field(default_factory=dict)
    by_lemma: dict[str, LexEntry] = field(default_factory=dict)
    lemma_readings: dict[str, set[str]] = field(default_factory=dict)
    components: dict[str, set[str]] = field(default_factory=dict)

    def is_polyphonic(self, lemma: str) -> bool:
        """Whether the corpus records more than one reading for this lemma.

        Drives the contextual-reading requirement (TASK-516): for 行 or 重 the
        question "what is the reading?" has no single answer, so the item must
        show the P1 sentence that fixes which one is meant.
        """
        return len(self.lemma_readings.get(lemma, ())) > 1

    # -- definition distractors -------------------------------------------

    def definitions_at_tier(
        self,
        tier: str | None,
        exclude_sense_ids: set[int],
        count: int = 3,
        rng: random.Random | None = None,
    ) -> list[str]:
        """Distinct definitions from other senses at the same complexity tier.

        The tier guard is the point (TASK-516): ``get_distractors`` samples the
        whole language, so an A1 word could end up with three C2 definitions
        beside it and the answer becomes obvious from register alone. Falls
        back to the untiered pool only when the tier has too few senses to fill
        the options — a slightly easy item beats no item.
        """
        rng = rng or random
        seen: set[str] = set()

        def collect(pool: list[LexEntry]) -> list[str]:
            out: list[str] = []
            for entry in pool:
                text = (entry.definition or '').strip()
                if not text or text in seen or entry.sense_id in exclude_sense_ids:
                    continue
                seen.add(text)
                out.append(text)
                if len(out) >= count:
                    break
            return out

        tiered = [e for e in self.entries if e.tier == tier and e.definition]
        rng.shuffle(tiered)
        picked = collect(tiered)
        if len(picked) >= count:
            return picked

        rest = [e for e in self.entries if e.tier != tier and e.definition]
        rng.shuffle(rest)
        return picked + collect(rest)[: count - len(picked)]

    # -- reading distractors (TASK-529) -----------------------------------

    def homophones(self, reading: str, exclude: set[str], count: int = 3) -> list[str]:
        """Real lemmas sharing this reading — the strongest reverse-direction foil.

        Ordered most-frequent-first: a homophone the learner has actually met
        is a live temptation, one they have never seen is noise.
        """
        pool = self.by_reading.get(normalise_reading(reading), [])
        out: list[str] = []
        seen = set(exclude)
        for entry in sorted(pool, key=_frequency_desc):
            if entry.lemma in seen:
                continue
            seen.add(entry.lemma)
            out.append(entry.lemma)
            if len(out) >= count:
                break
        return out

    def component_neighbours(
        self, lemma: str, exclude: set[str], count: int = 3,
    ) -> list[str]:
        """Lemmas sharing a character component with ``lemma``.

        The 张/章/掌 case: not homophones of each other in every tone, but
        visually confusable because they share structure. Requires
        ``dim_character_components`` to be populated; returns [] otherwise.
        """
        if not self.components:
            return []
        wanted: set[str] = set()
        for char in lemma:
            wanted |= self.components.get(char, set())
        if not wanted:
            return []

        scored: list[tuple[int, LexEntry]] = []
        seen = set(exclude)
        for entry in self.entries:
            if entry.lemma in seen or len(entry.lemma) != len(lemma):
                continue
            shared = 0
            for char in entry.lemma:
                shared += len(self.components.get(char, set()) & wanted)
            if shared:
                scored.append((shared, entry))
        scored.sort(key=lambda pair: (-pair[0], _frequency_desc(pair[1])))

        out: list[str] = []
        for _, entry in scored:
            if entry.lemma in seen:
                continue
            seen.add(entry.lemma)
            out.append(entry.lemma)
            if len(out) >= count:
                break
        return out

    def frequency_band_fillers(
        self,
        lemma: str,
        exclude: set[str],
        count: int = 3,
        band: float = 0.7,
        rng: random.Random | None = None,
    ) -> list[str]:
        """Same-length lemmas of similar frequency — the last-resort padding.

        Matching frequency matters more than it looks: padding a common word's
        options with obscure ones lets the learner answer by recognition alone.

        The band *widens* rather than giving up. A word at the very top or
        bottom of the frequency range has no neighbours within ±0.7, and
        returning nothing there would drop the exercise entirely — trading a
        real item for a marginal gain in distractor quality. Order is always
        nearest-frequency-first, so the widening only ever appends worse
        matches after the good ones are exhausted.
        """
        rng = rng or random
        anchor = self.by_lemma.get(lemma)
        target = anchor.frequency if anchor else None
        seen = set(exclude)
        seen.add(lemma)

        candidates = [
            e for e in self.entries
            if e.lemma not in seen and len(e.lemma) == len(lemma)
        ]
        rng.shuffle(candidates)
        if target is not None:
            candidates.sort(
                key=lambda e: (
                    abs(e.frequency - target) if e.frequency is not None else 99,
                    0 if (e.frequency is not None
                          and abs(e.frequency - target) <= band) else 1,
                )
            )

        out: list[str] = []
        for entry in candidates:
            if entry.lemma in seen:
                continue
            seen.add(entry.lemma)
            out.append(entry.lemma)
            if len(out) >= count:
                break
        return out


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

_PARENTHESISED = re.compile(r'\(([^)]*)\)')


def normalise_reading(pronunciation: str | None) -> str:
    """Reduce a stored pronunciation to a comparable homophone key.

    Chinese rows carry both notations (``"zhāng (zhang1)"``); the numbered form
    in parentheses is the stable one, so it wins when present. Tone *is* part
    of the key — 张 and 章 are homophones, 张 and 掌 are not, and conflating
    them would produce distractors a native speaker would never confuse.

    Japanese readings are already kana; they are just stripped and NFC-folded.
    """
    text = (pronunciation or '').strip()
    if not text:
        return ''
    numbered = _PARENTHESISED.search(text)
    if numbered:
        text = numbered.group(1)
    text = unicodedata.normalize('NFC', text)
    return ''.join(text.lower().split())


def _frequency_desc(entry: LexEntry) -> float:
    """Sort key: most frequent first.

    ``dim_vocabulary.frequency_rank`` holds a **Zipf score** (observed range
    0.25–6.56), so higher is more common. The column name is a historical
    misnomer and reading it as a rank inverts every ordering that touches it.
    """
    return -(entry.frequency if entry.frequency is not None else -1.0)


# ---------------------------------------------------------------------------
# Loading + cache
# ---------------------------------------------------------------------------

_cache: dict[int, Lexicon] = {}
_lock = threading.Lock()


def reset_cache() -> None:
    """Drop every cached language. For tests and post-backfill drains."""
    with _lock:
        _cache.clear()


def get_lexicon(db, language_id: int) -> Lexicon:
    """Load (or return the cached) lexicon for a language.

    Never raises: a load failure yields an empty lexicon and every accessor
    degrades to ``[]``, so a database blip costs distractor *quality*, not the
    whole batch.
    """
    with _lock:
        cached = _cache.get(language_id)
    if cached is not None:
        return cached

    lex = Lexicon(language_id=language_id)
    if db is not None:
        try:
            lex.entries = _load_entries(db, language_id)
            lex.components = _load_components(db)
        except Exception as exc:
            logger.error('lexicon load failed for language %s: %s', language_id, exc)
            lex.entries = []

    for entry in lex.entries:
        if entry.reading_key:
            lex.by_reading.setdefault(entry.reading_key, []).append(entry)
            lex.lemma_readings.setdefault(entry.lemma, set()).add(entry.reading_key)
        lex.by_lemma.setdefault(entry.lemma, entry)

    with _lock:
        _cache[language_id] = lex
    logger.info(
        'lexicon language=%s: %d senses, %d reading keys, %d component chars',
        language_id, len(lex.entries), len(lex.by_reading), len(lex.components),
    )
    return lex


def _load_entries(db, language_id: int) -> list[LexEntry]:
    """Page through the language's senses joined to their vocabulary rows."""
    entries: list[LexEntry] = []
    offset = 0
    while True:
        resp = (
            db.table('dim_word_senses')
            .select(
                'id, definition, pronunciation, sense_rank, definition_level,'
                'dim_vocabulary!inner(lemma, language_id, frequency_rank, semantic_class)'
            )
            .eq('dim_vocabulary.language_id', language_id)
            .range(offset, offset + _PAGE - 1)
            .execute()
        )
        rows = resp.data or []
        for row in rows:
            vocab = row.get('dim_vocabulary') or {}
            lemma = (vocab.get('lemma') or '').strip()
            if not lemma:
                continue
            pronunciation = row.get('pronunciation') or ''
            entries.append(LexEntry(
                sense_id=row['id'],
                lemma=lemma,
                definition=(row.get('definition') or '').strip(),
                pronunciation=pronunciation,
                reading_key=normalise_reading(pronunciation),
                tier=row.get('definition_level'),
                frequency=vocab.get('frequency_rank'),
                semantic_class=vocab.get('semantic_class'),
                sense_rank=row.get('sense_rank'),
            ))
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return entries


def _load_components(db) -> dict[str, set[str]]:
    """Character → component set, from ``dim_character_components``.

    An absent or empty table is a normal state before the TASK-529 import has
    been run, so a failure here is logged at debug and swallowed.
    """
    mapping: dict[str, set[str]] = {}
    offset = 0
    while True:
        try:
            resp = (
                db.table('dim_character_components')
                .select('character, components')
                .range(offset, offset + _PAGE - 1)
                .execute()
            )
        except Exception as exc:
            logger.debug('dim_character_components unavailable: %s', exc)
            return mapping
        rows = resp.data or []
        for row in rows:
            char = row.get('character')
            if char:
                mapping[char] = set(row.get('components') or ())
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return mapping
