# services/vocabulary_ladder/sense_neighbours.py
"""Embedding-band sanity checks over ``dim_word_senses.embedding`` (TASK-521).

What the band is for
--------------------
A synonym-match foil has a narrow window to sit in. Too far from the target
and it is not a distractor at all — nobody hesitates between *precision* and
*bicycle*. Too close and it *is* a synonym, so the item has two right answers.
The usable range is the middle: semantically adjacent, not equivalent.

Cosine similarity over the sense embeddings is a cheap, deterministic proxy
for that judgement, and it is used here as a *sanity check* rather than as the
decision. The relation judge still rules; this only catches the two failures
the judge is worst at — a foil that is obviously unrelated (the model padding
out four options) and a foil that is a near-duplicate of the answer.

Degrading when there is nothing to compare
------------------------------------------
The embedding backfill is operator-gated and may not have run. Every function
here returns "no opinion" rather than a verdict when the column is empty, the
RPC is missing, or the sense has no vector. A quality check that starts
rejecting content because its data source is absent is worse than no check.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

#: A foil below this cosine is unrelated — not a distractor, just a filler.
BAND_MIN = 0.35
#: A foil above this cosine is a near-duplicate of the target sense, and is
#: very likely an also-correct answer.
BAND_MAX = 0.88

#: The RPC installed by the TASK-521 migration.
#:
#: Not ``nearest_senses``. That function searches for the k nearest senses; this
#: one scores a *given* list of candidates, which is what a band check needs — a
#: foil that falls outside the band must come back with its similarity so the
#: caller can reject it, not be omitted from a k-nearest result. Pointing at
#: ``nearest_senses`` (its original value) also passed arguments that function
#: has never accepted, so every call raised PGRST202 and was swallowed as
#: "RPC unavailable".
SIMILARITY_RPC = 'sense_similarity_to_lemmas'


@dataclass(frozen=True)
class BandCheck:
    """The verdict on one foil, or the absence of one."""

    #: True in band, False out of band, None when the check could not run.
    in_band: bool | None
    similarity: float | None
    reason: str

    @property
    def usable(self) -> bool:
        """Whether the caller may act on this. False means "no opinion"."""
        return self.in_band is not None


UNAVAILABLE = BandCheck(
    in_band=None, similarity=None,
    reason='no sense embedding available — band check skipped',
)


def neighbour_similarities(
    db, sense_id: int, language_id: int, candidates: list[str],
) -> dict[str, float]:
    """Cosine similarity between a sense and each candidate word.

    Resolves candidates to senses of the same language and returns the best
    similarity found per candidate. Words with no sense row, and senses with
    no embedding, are simply absent from the result — the caller reads a
    missing key as "no opinion", never as zero.

    Returns ``{}`` on any error. The RPC may not exist in a given environment
    (the migration is applied separately from the code), and a syn/ant batch
    must not fail because an optional index is missing.
    """
    if db is None or not candidates:
        return {}

    try:
        resp = db.rpc(SIMILARITY_RPC, {
            'p_sense_id': sense_id,
            'p_language_id': language_id,
            'p_lemmas': candidates,
        }).execute()
        rows = resp.data or []
    except Exception as exc:
        # WARNING, not INFO. This used to be the normal path — the RPC name and
        # arguments did not match anything that existed — and at INFO the
        # failure was indistinguishable from the backfill not having run.
        logger.warning(
            '%s failed for sense %s (%s) — band checks skipped',
            SIMILARITY_RPC, sense_id, exc,
        )
        return {}

    best: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        lemma = (row.get('lemma') or '').strip()
        similarity = row.get('similarity')
        if not lemma or similarity is None:
            continue
        try:
            value = float(similarity)
        except (TypeError, ValueError):
            continue
        if value > best.get(lemma, -1.0):
            best[lemma] = value
    return best


def check_band(
    similarity: float | None,
    band_min: float = BAND_MIN,
    band_max: float = BAND_MAX,
) -> BandCheck:
    """Grade one similarity against the mid band."""
    if similarity is None:
        return UNAVAILABLE
    if similarity < band_min:
        return BandCheck(
            in_band=False, similarity=similarity,
            reason=f'cosine {similarity:.2f} < {band_min} — unrelated, not a distractor',
        )
    if similarity > band_max:
        return BandCheck(
            in_band=False, similarity=similarity,
            reason=f'cosine {similarity:.2f} > {band_max} — near-duplicate, likely also correct',
        )
    return BandCheck(
        in_band=True, similarity=similarity,
        reason=f'cosine {similarity:.2f} within [{band_min}, {band_max}]',
    )


def band_check_foils(
    db, sense_id: int, language_id: int, foils: list[str],
    band_min: float = BAND_MIN, band_max: float = BAND_MAX,
) -> dict[str, BandCheck]:
    """Grade every foil. Foils with no embedding get :data:`UNAVAILABLE`."""
    similarities = neighbour_similarities(db, sense_id, language_id, foils)
    return {
        foil: check_band(similarities.get(foil), band_min, band_max)
        for foil in foils
    }
