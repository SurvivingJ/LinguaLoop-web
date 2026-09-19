# ADAPTED FROM services/vocabulary_ladder/deterministic/dictionaries.py:1-259
#
# Same public contract as production's MeasureIndex (answers_for /
# distractors_for), reading db/lab.sqlite instead of Supabase.
#
# One forced divergence: production groups distractors by
# `distractor_group_id` -> `dim_classifier_distractor_groups.label`
# (dictionaries.py:129-133). The sandbox schema carries the *column*
# (`dim_classifiers.distractor_group_id`) but seeds it as always NULL - there
# is no `dim_classifier_distractor_groups` table in the sandbox's 16-table
# slice and build_db.py never populates group ids (see db/schema.sql comment
# on that column). Grouping here falls back to `semantic_label` instead,
# which the classifier_curation/counter_curation JSON files DO populate for
# every row - a same-spirit adaptation (semantically-coherent foils, generic
# measure words excluded) rather than a re-implementation of the missing
# table.
from __future__ import annotations

import random
import sqlite3
import threading
from dataclasses import dataclass, field

_SCHEMAS: dict[str, dict[str, str]] = {
    'classifier': {
        'words': 'dim_classifiers',
        'pairs': 'dim_classifier_noun_pairs',
        'form': 'hanzi',
        'reading': 'pinyin_display',
        'word_fk': 'classifier_id',
    },
    'counter': {
        'words': 'dim_counters',
        'pairs': 'dim_counter_noun_pairs',
        'form': 'kanji',
        'reading': 'reading_display',
        'word_fk': 'counter_id',
    },
}

GENERIC_FORMS: dict[str, frozenset[str]] = {
    'classifier': frozenset({'个', '個'}),
    'counter': frozenset({'つ', '個', 'こ'}),
}


@dataclass(frozen=True)
class MeasureWord:
    id: int
    form: str
    reading: str
    semantic_label: str
    frequency_rank: float | None

    # Production's MeasureWord also carries `group_id`/`group_label` from
    # `dim_classifier_distractor_groups` (not part of the sandbox's 16-table
    # seed - see module banner). classifier_match.py/counter_match.py (real,
    # unmodified production code) read `key.group_label` on the output row,
    # so it must exist here or those builders raise AttributeError. Aliased
    # to semantic_label per the banner's documented divergence.
    @property
    def group_label(self) -> str:
        return self.semantic_label


@dataclass
class MeasureIndex:
    kind: str
    language_id: int
    words: dict[int, MeasureWord] = field(default_factory=dict)
    by_group: dict[str, list[int]] = field(default_factory=dict)  # keyed by semantic_label
    by_lemma: dict[str, list[int]] = field(default_factory=dict)
    by_sense: dict[int, list[int]] = field(default_factory=dict)

    @property
    def is_loaded(self) -> bool:
        return bool(self.words and self.by_lemma)

    def answers_for(self, lemma: str, sense_id: int | None = None) -> list[MeasureWord]:
        ids: list[int] = []
        if sense_id is not None:
            ids = list(self.by_sense.get(sense_id, ()))
        if not ids:
            ids = list(self.by_lemma.get(lemma, ()))
        generic = GENERIC_FORMS.get(self.kind, frozenset())
        return [
            self.words[i] for i in ids
            if i in self.words and self.words[i].form not in generic
        ]

    def distractors_for(
        self,
        answers: list[MeasureWord],
        count: int = 3,
        rng: random.Random | None = None,
    ) -> list[MeasureWord]:
        rng = rng or random
        if not answers:
            return []
        generic = GENERIC_FORMS.get(self.kind, frozenset())
        taken = {w.id for w in answers}

        primary = answers[0]
        pool: list[MeasureWord] = []
        label = primary.semantic_label
        if label and label != 'general':
            pool = [
                self.words[i] for i in self.by_group.get(label, ())
                if i not in taken and self.words[i].form not in generic
            ]
            rng.shuffle(pool)

        picked = pool[:count]
        if len(picked) < count:
            taken |= {w.id for w in picked}
            filler = [
                w for w in self.words.values()
                if w.id not in taken and w.form not in generic
            ]
            rng.shuffle(filler)
            picked += filler[: count - len(picked)]
        return picked[:count]


_cache: dict[tuple[str, int], MeasureIndex] = {}
_lock = threading.Lock()


def reset_cache() -> None:
    with _lock:
        _cache.clear()


def get_index(conn: sqlite3.Connection, kind: str, language_id: int) -> MeasureIndex:
    key = (kind, language_id)
    with _lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached

    index = MeasureIndex(kind=kind, language_id=language_id)
    schema = _SCHEMAS[kind]
    rows = conn.execute(
        f"SELECT id, {schema['form']} AS form, {schema['reading']} AS reading, "
        f"semantic_label, frequency_rank FROM {schema['words']} WHERE language_id = ?",
        (language_id,),
    ).fetchall()
    for row in rows:
        form = row['form'] or ''
        if not form:
            continue
        word = MeasureWord(
            id=row['id'], form=form, reading=row['reading'] or '',
            semantic_label=row['semantic_label'] or '',
            frequency_rank=row['frequency_rank'],
        )
        index.words[word.id] = word
        if word.semantic_label:
            index.by_group.setdefault(word.semantic_label, []).append(word.id)

    pair_rows = conn.execute(
        f"SELECT lemma_text, noun_sense_id, {schema['word_fk']} AS word_id, is_primary "
        f"FROM {schema['pairs']} WHERE language_id = ? ORDER BY is_primary DESC",
        (language_id,),
    ).fetchall()
    for row in pair_rows:
        word_id = row['word_id']
        lemma = (row['lemma_text'] or '').strip()
        if word_id is None or word_id not in index.words:
            continue
        if lemma:
            bucket = index.by_lemma.setdefault(lemma, [])
            if word_id not in bucket:
                bucket.append(word_id)
        sense_id = row['noun_sense_id']
        if sense_id is not None:
            bucket = index.by_sense.setdefault(sense_id, [])
            if word_id not in bucket:
                bucket.append(word_id)

    with _lock:
        _cache[key] = index
    return index
