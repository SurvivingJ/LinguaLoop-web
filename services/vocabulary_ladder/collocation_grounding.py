# services/vocabulary_ladder/collocation_grounding.py
"""Corpus grounding for the collocate P1 asserts (TASK-523, finding G6).

The problem
-----------
``prompt1_core`` returns a ``primary_collocate`` for every sense, and L5
(collocation gap-fill) and L8 (collocation repair) are both built on it. The
model is asked for "the word this one habitually combines with" and, being a
model, always answers. It returned *advertising* as the primary collocate of
**personalize** — a plausible co-occurrence, not a collocation — and the
resulting L5 item asked learners to choose between four near-synonyms with no
correct answer.

Nothing downstream could catch that. The collocation judge rules on whether a
*distractor* is also a valid collocate; it takes the correct collocate as
given. So the assertion itself needed evidence.

What "evidence" means here
--------------------------
Two sources, tried in order, and the answer is a *tag* rather than a veto:

1. **A bundled frequency list** (English). Static, offline, licence-documented
   — see ``data/collocations/README.md``. A pair present in the list with a
   frequency at or above :data:`MIN_LIST_FREQUENCY` is attested usage.
2. **``corpus_collocations``** (any language whose corpus has been ingested).
   The project's own PMI-scored n-grams. A pair at or above :data:`MIN_PMI` is
   statistically a fixed pair rather than a common co-occurrence.

A pair neither source confirms is tagged ``llm_asserted``, not deleted: the
absence of evidence in a partial corpus is weak evidence of absence, and L5
already has a hard PMI gate of its own. A language with no source at all is
tagged ``no_source``, which is deliberately *not* the same thing — for
Japanese, "we did not find it" would be a claim we have no standing to make.

The tag rides through to ``word_assets`` and onto every L5/L8 exercise's
provenance, so the batch report can say what fraction of the collocation
corpus rests on evidence rather than assertion.
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

GROUNDING_CORPUS = 'corpus_validated'
GROUNDING_ASSERTED = 'llm_asserted'
GROUNDING_NO_SOURCE = 'no_source'

SOURCE_LIST = 'bundled_list'
SOURCE_CORPUS = 'corpus_collocations'

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Shared with the pre-existing L5 gate in asset_pipeline — the same number
# decided "is this a fixed pair" there, and having two thresholds disagree
# about the same question would be worse than either value being wrong.
MIN_PMI = 5.0

# A bundled-list pair this rare is a long-tail artefact of whatever corpus the
# list was built from, not evidence a learner should be taught the pairing.
MIN_LIST_FREQUENCY = 5

# language_id -> the grounding sources available for it, best first. An empty
# tuple means the language has no source, and absence of a hit means nothing.
# Japanese is deliberately empty: the task defers JA grounding until a source
# exists (TASK-523), and pretending otherwise would mislabel every JA
# collocate as unattested.
GROUNDING_SOURCES: dict[int, tuple[str, ...]] = {
    1: (SOURCE_CORPUS,),                # Chinese — conversation corpus ingested
    2: (SOURCE_LIST, SOURCE_CORPUS),    # English — bundled list, then corpus
    3: (),                              # Japanese — deferred, no source
}

# Where the bundled lists live, and their filenames per language.
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data', 'collocations',
)
LIST_FILENAMES: dict[int, str] = {2: 'en_collocations.tsv'}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Grounding:
    """The evidence standing behind one (lemma, collocate) pair."""

    status: str
    reason: str
    source: str | None = None
    score: float | None = None

    @property
    def validated(self) -> bool:
        return self.status == GROUNDING_CORPUS

    @property
    def checkable(self) -> bool:
        """Whether a source existed to check against at all.

        ``no_source`` is not a failed check — it is the absence of one, and a
        report that lumps the two together would show Japanese as having a
        0% validation rate rather than as unmeasured.
        """
        return self.status != GROUNDING_NO_SOURCE

    def to_tag(self) -> dict:
        """The shape persisted on assets and exercise provenance."""
        tag = {'status': self.status, 'reason': self.reason}
        if self.source:
            tag['source'] = self.source
        if self.score is not None:
            tag['score'] = round(float(self.score), 3)
        return tag


# ---------------------------------------------------------------------------
# Bundled list
# ---------------------------------------------------------------------------

@dataclass
class BundledCollocationList:
    """A (head, collocate) → frequency index loaded from a TSV.

    Format (tab-separated, ``#`` comments and a header row ignored)::

        head    collocate   frequency   relation

    Pairs are indexed **unordered**: P1 does not say which side is the head,
    and "make · decision" and "decision · make" are the same fact about the
    language.
    """

    path: str
    pairs: dict[tuple[str, str], int] = field(default_factory=dict)
    loaded: bool = False

    @staticmethod
    def key(a: str, b: str) -> tuple[str, str]:
        first, second = a.strip().casefold(), b.strip().casefold()
        return (first, second) if first <= second else (second, first)

    def load(self) -> 'BundledCollocationList':
        """Read the file. A missing file is normal, not an error.

        The list is a large third-party artefact that the repo documents but
        does not vendor (see the README). When it is absent the grounder falls
        through to the corpus source, which is exactly the behaviour before
        this module existed.
        """
        self.loaded = True
        if not self.path or not os.path.exists(self.path):
            logger.info(
                'No bundled collocation list at %s — falling back to '
                'corpus_collocations for this language', self.path or '(none)',
            )
            return self

        try:
            with open(self.path, encoding='utf-8', newline='') as handle:
                seen_header = False
                for row in csv.reader(handle, delimiter='\t'):
                    if not row or row[0].lstrip().startswith('#'):
                        continue
                    if len(row) < 3:
                        continue
                    head, collocate, frequency = row[0], row[1], row[2]
                    # Only the FIRST non-comment row can be the header. Matching
                    # `head` anywhere drops every real collocation headed by the
                    # noun *head* — head/coach, head/department, head/injury —
                    # and a word that common losing its whole entry is not a
                    # rounding error.
                    if not seen_header:
                        seen_header = True
                        if head.strip().casefold() == 'head':
                            continue
                    try:
                        count = int(frequency)
                    except (TypeError, ValueError):
                        continue
                    key = self.key(head, collocate)
                    # Keep the highest count if a pair appears twice (some
                    # sources list one pair under several relations).
                    if count > self.pairs.get(key, 0):
                        self.pairs[key] = count
        except OSError as exc:
            logger.warning('Could not read collocation list %s: %s', self.path, exc)

        logger.info('Loaded %d collocation pairs from %s', len(self.pairs), self.path)
        return self

    def frequency(self, a: str, b: str) -> int | None:
        if not self.loaded:
            self.load()
        return self.pairs.get(self.key(a, b))


_list_cache: dict[int, BundledCollocationList] = {}


def bundled_list(language_id: int, data_dir: str | None = None) -> BundledCollocationList:
    """Cached per-language bundled list (empty when none is installed)."""
    if language_id in _list_cache and data_dir is None:
        return _list_cache[language_id]

    filename = LIST_FILENAMES.get(language_id)
    path = os.path.join(data_dir or DATA_DIR, filename) if filename else ''
    loaded = BundledCollocationList(path=path).load()
    if data_dir is None:
        _list_cache[language_id] = loaded
    return loaded


def clear_list_cache() -> None:
    """Test-only escape hatch."""
    _list_cache.clear()


# ---------------------------------------------------------------------------
# Grounder
# ---------------------------------------------------------------------------

class CollocationGrounder:
    """Answers "is this pair attested?" for one language at a time."""

    def __init__(self, db=None, data_dir: str | None = None):
        self.db = db
        self.data_dir = data_dir

    def validate(self, lemma: str, collocate: str, language_id: int) -> Grounding:
        """Grade the evidence for a (lemma, collocate) pair."""
        lemma = (lemma or '').strip()
        collocate = (collocate or '').strip()

        # P1 writes the literal string "null" when it has no collocate.
        if not lemma or not collocate or collocate.lower() == 'null':
            return Grounding(
                status=GROUNDING_NO_SOURCE,
                reason='no collocate asserted for this sense',
            )

        sources = GROUNDING_SOURCES.get(language_id)
        if sources is None:
            # An unconfigured language: treat like a deferred one rather than
            # claiming the pair is unattested.
            return Grounding(
                status=GROUNDING_NO_SOURCE,
                reason=f'no grounding source configured for language_id={language_id}',
            )
        if not sources:
            return Grounding(
                status=GROUNDING_NO_SOURCE,
                reason='grounding deferred for this language — no frequency source',
            )

        checked: list[str] = []
        for source in sources:
            if source == SOURCE_LIST:
                hit = self._check_list(lemma, collocate, language_id)
            elif source == SOURCE_CORPUS:
                hit = self._check_corpus(lemma, collocate, language_id)
            else:                                     # pragma: no cover
                continue
            if hit is not None:
                return hit
            checked.append(source)

        return Grounding(
            status=GROUNDING_ASSERTED,
            reason=f'not attested in {", ".join(checked)}',
        )

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def _check_list(self, lemma: str, collocate: str, language_id: int) -> Grounding | None:
        """Bundled frequency list. None means "no hit", not "no list"."""
        source_list = bundled_list(language_id, self.data_dir)
        if not source_list.pairs:
            return None
        count = source_list.frequency(lemma, collocate)
        if count is None or count < MIN_LIST_FREQUENCY:
            return None
        return Grounding(
            status=GROUNDING_CORPUS,
            reason=f'attested {count}x in {os.path.basename(source_list.path)}',
            source=SOURCE_LIST,
            score=float(count),
        )

    def _check_corpus(self, lemma: str, collocate: str, language_id: int) -> Grounding | None:
        """``corpus_collocations`` PMI lookup, either word order.

        A DB error returns None (fall through to the next source and then to
        ``llm_asserted``) rather than raising: grounding is an annotation
        pass, and it must never be the reason a sense fails to generate.
        """
        if self.db is None:
            return None
        try:
            resp = (
                self.db.table('corpus_collocations')
                .select('pmi_score, head_word, collocate')
                .eq('language_id', language_id)
                .or_(
                    f'and(head_word.eq.{lemma},collocate.eq.{collocate}),'
                    f'and(head_word.eq.{collocate},collocate.eq.{lemma})'
                )
                .gte('pmi_score', MIN_PMI)
                .order('pmi_score', desc=True)
                .limit(1)
                .execute()
            )
            rows = resp.data or []
        except Exception as exc:
            logger.warning(
                'corpus_collocations lookup failed for (%r, %r): %s',
                lemma, collocate, exc,
            )
            return None

        if not rows:
            return None
        pmi = rows[0].get('pmi_score')
        return Grounding(
            status=GROUNDING_CORPUS,
            reason=f'corpus_collocations PMI {float(pmi or 0):.2f} >= {MIN_PMI}',
            source=SOURCE_CORPUS,
            score=float(pmi or 0),
        )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def ground_core_asset(core_asset: dict, language_id: int, db=None) -> Grounding:
    """Grade a P1 asset's ``primary_collocate`` and pin the tag onto it.

    Mutates ``core_asset['collocate_grounding']`` in place so the tag is
    stored with the asset and is available to the L8 prompt (which shows the
    model how much to trust the collocate it is being handed) and to the
    renderer (which copies it into exercise provenance).
    """
    from services.vocabulary_ladder.config import get_sentence_target

    sentences = (core_asset or {}).get('sentences') or []
    lemma = get_sentence_target(sentences[0]) if sentences else ''
    collocate = (core_asset or {}).get('primary_collocate') or ''

    grounding = CollocationGrounder(db).validate(lemma, collocate, language_id)
    if isinstance(core_asset, dict):
        core_asset['collocate_grounding'] = grounding.to_tag()
    return grounding
