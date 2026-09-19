# ADAPTED FROM services/vocabulary_ladder/deterministic/lexicon.py:1-393
#
# Same idea and same public methods as production's Lexicon (in-memory,
# process-lifetime, per-language index used by definition_match and the
# sound<->script readers), but the loader queries db/lab.sqlite directly
# instead of a Supabase client (production's `_load_entries`/`_load_components`
# use `db.table(...).select(...).eq(...)`, which this sandbox cannot call -
# no Supabase, ever, per README §1). The query logic and every distractor
# algorithm (definitions_at_tier, homophones, component_neighbours,
# frequency_band_fillers) are reproduced faithfully from the cited file.
#
# One deliberate divergence, called out because it affects a real number in
# results-zero-llm.md: production's `entry.tier` is populated from
# `definition_level` ('simple'/'standard') and compared against
# `ctx.tier`, which is a T1-T6 COMPLEXITY tier computed elsewhere
# (exercise_renderer.py:_get_tier). Those two vocabularies never intersect,
# so `definitions_at_tier(tier=ctx.tier, ...)` can never hit the `tiered`
# branch in production and silently always falls through to the untiered
# pool - a real bug this recon surfaced as a byproduct, not something this
# sandbox should reproduce. Here, `tier` means Zipf-frequency DECILE of the
# language's senses (a real, evaluable complexity proxy, since neither T1-T6
# nor a real definition_level split is meaningful data in this sandbox - see
# README fidelity gap #7, "simple/standard are byte-identical here").
from __future__ import annotations

import random
import re
import sqlite3
import threading
import unicodedata
from dataclasses import dataclass, field


@dataclass
class LexEntry:
    sense_id: int
    lemma: str
    definition: str
    pronunciation: str
    reading_key: str
    tier: int | None          # Zipf decile 0(rarest)-9(commonest), see banner
    frequency: float | None
    sense_rank: int | None


@dataclass
class Lexicon:
    language_id: int
    entries: list[LexEntry] = field(default_factory=list)
    by_reading: dict[str, list[LexEntry]] = field(default_factory=dict)
    by_lemma: dict[str, LexEntry] = field(default_factory=dict)
    lemma_readings: dict[str, set[str]] = field(default_factory=dict)
    # Always empty: dim_character_components is not part of the sandbox's
    # 16-table seed (README §4/§8). Kept as a real attribute (not omitted)
    # so unmodified production callers (readings.py's `_reverse`) that do
    # `lexicon.component_neighbours(...)` degrade exactly the way production
    # degrades when the table is unpopulated, instead of raising AttributeError.
    components: dict[str, set[str]] = field(default_factory=dict)
    # Perf-only indices (not in production's Lexicon): zh alone seeds 124,933
    # standard-level entries, and both `definitions_at_tier` and
    # `frequency_band_fillers` did a fresh `[e for e in self.entries if ...]`
    # scan on EVERY call in the first draft of this port. At the sample sizes
    # task 4 needs (thousands of senses x 2 variants x several sound<->script
    # builders per sense) that made the measurement run effectively hang.
    # Pre-grouping once at load time turns each call into an O(bucket) lookup
    # instead of an O(|entries|) scan - same output, since the grouping keys
    # (`tier`, `len(lemma)`) are exactly what each method already filtered on.
    by_tier: dict[int | None, list[LexEntry]] = field(default_factory=dict)
    by_length: dict[int, list[LexEntry]] = field(default_factory=dict)

    def is_polyphonic(self, lemma: str) -> bool:
        return len(self.lemma_readings.get(lemma, ())) > 1

    def definitions_at_tier(
        self,
        tier: int | None,
        exclude_sense_ids: set[int],
        count: int = 3,
        rng: random.Random | None = None,
    ) -> list[str]:
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

        tiered = [e for e in self.by_tier.get(tier, ()) if e.definition]
        rng.shuffle(tiered)
        picked = collect(tiered)
        if len(picked) >= count:
            return picked

        rest = [e for e in self.entries if e.tier != tier and e.definition]
        rng.shuffle(rest)
        return picked + collect(rest)[: count - len(picked)]

    def homophones(self, reading: str, exclude: set[str], count: int = 3) -> list[str]:
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

    def frequency_band_fillers(
        self,
        lemma: str,
        exclude: set[str],
        count: int = 3,
        band: float = 0.7,
        rng: random.Random | None = None,
    ) -> list[str]:
        rng = rng or random
        anchor = self.by_lemma.get(lemma)
        target = anchor.frequency if anchor else None
        seen = set(exclude)
        seen.add(lemma)

        candidates = [
            e for e in self.by_length.get(len(lemma), ())
            if e.lemma not in seen
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

    # ADAPTED FROM services/vocabulary_ladder/deterministic/lexicon.py:149-176
    # `self.components` is always {} here (see field comment above), so this
    # unconditionally returns [] - exactly production's degrade path when
    # dim_character_components is unpopulated. Kept as a real method (not
    # omitted) because readings.py's `_reverse` (real, unmodified production
    # code) calls it directly for pinyin_to_hanzi/reading_to_kanji, which then
    # fall through to frequency_band_fillers, same as production.
    def component_neighbours(
        self, lemma: str, exclude: set[str], count: int = 3,
    ) -> list[str]:
        if not self.components:
            return []
        wanted: set[str] = set()
        for char in lemma:
            wanted |= self.components.get(char, set())
        if not wanted:
            return []
        scored: list[tuple[int, str]] = []
        seen = set(exclude)
        for entry in self.entries:
            if entry.lemma in seen or len(entry.lemma) != len(lemma):
                continue
            shared = sum(
                len(self.components.get(c, set()) & wanted) for c in entry.lemma
            )
            if shared:
                scored.append((shared, entry.lemma))
        scored.sort(key=lambda t: -t[0])
        out: list[str] = []
        seen2 = set(exclude)
        for _, lem in scored:
            if lem in seen2:
                continue
            seen2.add(lem)
            out.append(lem)
            if len(out) >= count:
                break
        return out


_PARENTHESISED = re.compile(r'\(([^)]*)\)')


def normalise_reading(pronunciation: str | None) -> str:
    text = (pronunciation or '').strip()
    if not text:
        return ''
    numbered = _PARENTHESISED.search(text)
    if numbered:
        text = numbered.group(1)
    text = unicodedata.normalize('NFC', text)
    return ''.join(text.lower().split())


def _frequency_desc(entry: LexEntry) -> float:
    return -(entry.frequency if entry.frequency is not None else -1.0)


_cache: dict[int, Lexicon] = {}
_lock = threading.Lock()


def reset_cache() -> None:
    with _lock:
        _cache.clear()


def get_lexicon(conn: sqlite3.Connection, language_id: int) -> Lexicon:
    """Load (or return the cached) lexicon for a language from lab.sqlite."""
    with _lock:
        cached = _cache.get(language_id)
    if cached is not None:
        return cached

    lex = Lexicon(language_id=language_id)
    rows = conn.execute(
        """
        SELECT ws.id AS sense_id, v.lemma AS lemma, ws.definition AS definition,
               ws.pronunciation AS pronunciation, ws.sense_rank AS sense_rank,
               v.frequency_rank AS frequency_rank
        FROM dim_word_senses ws
        JOIN dim_vocabulary v ON v.id = ws.vocab_id
        WHERE v.language_id = ? AND ws.definition_level = 'standard'
        """,
        (language_id,),
    ).fetchall()

    freqs = sorted(
        r['frequency_rank'] for r in rows if r['frequency_rank'] is not None
    )

    def decile(f: float | None) -> int | None:
        if f is None or not freqs:
            return None
        import bisect
        pos = bisect.bisect_left(freqs, f) / max(len(freqs), 1)
        return min(9, int(pos * 10))

    for row in rows:
        lemma = (row['lemma'] or '').strip()
        if not lemma:
            continue
        pronunciation = row['pronunciation'] or ''
        lex.entries.append(LexEntry(
            sense_id=row['sense_id'],
            lemma=lemma,
            definition=(row['definition'] or '').strip(),
            pronunciation=pronunciation,
            reading_key=normalise_reading(pronunciation),
            tier=decile(row['frequency_rank']),
            frequency=row['frequency_rank'],
            sense_rank=row['sense_rank'],
        ))

    for entry in lex.entries:
        if entry.reading_key:
            lex.by_reading.setdefault(entry.reading_key, []).append(entry)
            lex.lemma_readings.setdefault(entry.lemma, set()).add(entry.reading_key)
        lex.by_lemma.setdefault(entry.lemma, entry)
        lex.by_tier.setdefault(entry.tier, []).append(entry)
        lex.by_length.setdefault(len(entry.lemma), []).append(entry)

    with _lock:
        _cache[language_id] = lex
    return lex
