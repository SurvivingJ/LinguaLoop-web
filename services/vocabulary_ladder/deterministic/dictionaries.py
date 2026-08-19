"""
Measure-word dictionaries — Chinese classifiers and Japanese counters.

Both languages force the same choice on a learner: to say "three ___" you must
know which measure word the noun takes. Chinese calls them classifiers (量词),
Japanese counters (助数詞), and pedagogically they behave identically — a small
closed set, organised into semantic groups, with a generic fallback that makes
every item trivially answerable if you let it in.

That last point is the design constraint. 个 in Chinese and つ/個 in Japanese are
the "when in doubt" measure words; a learner who answers 个 every time is right
often enough that an item offering it teaches nothing. Both are excluded here
by form, mirroring the exclusion baked into ``get_classifier_drill_session``.

Distractors come from the answer's own semantic group (round-flat-things,
long-thin-things, machines, …) so the item asks *which* group the noun belongs
to rather than whether the learner can spot a nonsense option. Groups labelled
``general`` are the exception: their members are not semantically coherent, so
group-based foils would be arbitrary and the picker falls through to
low-difficulty-tier padding instead.

One index per (language, kind) is loaded once per process — a batch renders
thousands of senses and must not issue a dictionary query per noun.
"""

from __future__ import annotations

import logging
import random
import threading
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_PAGE = 1000

# Table names differ, shape does not.
_SCHEMAS: dict[str, dict[str, str]] = {
    'classifier': {
        'words': 'dim_classifiers',
        'pairs': 'dim_classifier_noun_pairs',
        'groups': 'dim_classifier_distractor_groups',
        'form': 'hanzi',
        'reading': 'pinyin_display',
        'word_fk': 'classifier_id',
    },
    'counter': {
        'words': 'dim_counters',
        'pairs': 'dim_counter_noun_pairs',
        'groups': 'dim_counter_distractor_groups',
        'form': 'counter',
        'reading': 'reading',
        'word_fk': 'counter_id',
    },
}

# Generic measure words, excluded as both answers and distractors.
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
    group_id: int | None
    group_label: str
    difficulty_tier: int | None


@dataclass
class MeasureIndex:
    """One language's measure-word dictionary, queryable by noun."""

    kind: str
    language_id: int
    words: dict[int, MeasureWord] = field(default_factory=dict)
    by_group: dict[int, list[int]] = field(default_factory=dict)
    by_lemma: dict[str, list[int]] = field(default_factory=dict)
    by_sense: dict[int, list[int]] = field(default_factory=dict)

    @property
    def is_loaded(self) -> bool:
        return bool(self.words and self.by_lemma)

    def answers_for(self, lemma: str, sense_id: int | None = None) -> list[MeasureWord]:
        """Every acceptable measure word for this noun, primary first.

        Multi-acceptable is the norm, not an edge case (书 takes 本 and 册), so
        callers must treat the whole list as correct rather than only ``[0]``.
        Sense-keyed pairs win over lemma-keyed ones: 打 as "dozen" and 打 as
        "to hit" do not share a classifier.
        """
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
        """Three foils from the answer's semantic group, padded if thin.

        Always returns ``count`` when the dictionary holds enough words at all —
        an item with two options is worse than no item, so the caller checks
        the length and skips rather than shipping a degraded MCQ.
        """
        rng = rng or random
        if not answers:
            return []
        generic = GENERIC_FORMS.get(self.kind, frozenset())
        taken = {w.id for w in answers}

        primary = answers[0]
        pool: list[MeasureWord] = []
        if primary.group_label != 'general' and primary.group_id is not None:
            pool = [
                self.words[i] for i in self.by_group.get(primary.group_id, ())
                if i not in taken and self.words[i].form not in generic
            ]
            pool.sort(key=lambda w: (w.difficulty_tier or 99, rng.random()))

        picked = pool[:count]
        if len(picked) < count:
            taken |= {w.id for w in picked}
            filler = [
                w for w in self.words.values()
                if w.id not in taken and w.form not in generic
                and (w.difficulty_tier or 99) <= 2
            ]
            rng.shuffle(filler)
            picked += filler[: count - len(picked)]
        return picked[:count]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

_cache: dict[tuple[str, int], MeasureIndex] = {}
_lock = threading.Lock()


def reset_cache() -> None:
    with _lock:
        _cache.clear()


def get_index(db, kind: str, language_id: int) -> MeasureIndex:
    """Load (or return the cached) dictionary for a (kind, language).

    A missing table is a normal state — ``dim_counters`` does not exist until
    the TASK-530 migration is applied — so failure yields an empty index and
    the builder skips with a reason rather than raising.
    """
    key = (kind, language_id)
    with _lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached

    index = MeasureIndex(kind=kind, language_id=language_id)
    schema = _SCHEMAS.get(kind)
    if db is not None and schema is not None:
        try:
            _load(db, schema, index)
        except Exception as exc:
            logger.info(
                '%s dictionary unavailable for language %s: %s',
                kind, language_id, exc,
            )

    with _lock:
        _cache[key] = index
    if index.is_loaded:
        logger.info(
            '%s dictionary language=%s: %d words, %d nouns',
            kind, language_id, len(index.words), len(index.by_lemma),
        )
    return index


def _load(db, schema: dict[str, str], index: MeasureIndex) -> None:
    groups: dict[int, str] = {}
    resp = db.table(schema['groups']).select('id, label').execute()
    for row in resp.data or []:
        groups[row['id']] = row.get('label') or ''

    resp = (
        db.table(schema['words'])
        .select(
            f"id, {schema['form']}, {schema['reading']}, semantic_label, "
            f'distractor_group_id, difficulty_tier'
        )
        .eq('language_id', index.language_id)
        .execute()
    )
    for row in resp.data or []:
        group_id = row.get('distractor_group_id')
        word = MeasureWord(
            id=row['id'],
            form=row.get(schema['form']) or '',
            reading=row.get(schema['reading']) or '',
            semantic_label=row.get('semantic_label') or '',
            group_id=group_id,
            group_label=groups.get(group_id, ''),
            difficulty_tier=row.get('difficulty_tier'),
        )
        if not word.form:
            continue
        index.words[word.id] = word
        if group_id is not None:
            index.by_group.setdefault(group_id, []).append(word.id)

    offset = 0
    while True:
        resp = (
            db.table(schema['pairs'])
            .select(
                f"lemma_text, noun_sense_id, {schema['word_fk']}, "
                f'is_primary, frequency_score'
            )
            .eq('language_id', index.language_id)
            .order('is_primary', desc=True)
            .range(offset, offset + _PAGE - 1)
            .execute()
        )
        rows = resp.data or []
        for row in rows:
            word_id = row.get(schema['word_fk'])
            lemma = (row.get('lemma_text') or '').strip()
            if word_id is None or word_id not in index.words:
                continue
            if lemma:
                bucket = index.by_lemma.setdefault(lemma, [])
                if word_id not in bucket:
                    bucket.append(word_id)
            sense_id = row.get('noun_sense_id')
            if sense_id is not None:
                bucket = index.by_sense.setdefault(sense_id, [])
                if word_id not in bucket:
                    bucket.append(word_id)
        if len(rows) < _PAGE:
            break
        offset += _PAGE
