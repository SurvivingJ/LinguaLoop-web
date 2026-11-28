"""Passage helpers for Dual Translation (TASK-603, TASK-909).

Pure logic shared by the routes that build `dt_passage` sentence windows from
`test_sentences` (ADR-037): the derived age tier, the window-text joining
convention, and primed-window selection. Nothing here touches the DB.

The original whole-transcript passage builder (segmenting a transcript into
2-4 sentence spans, in-app dedupe, and generating one whole-passage L1
reference per L1) lost its last production caller with
`scripts/build_dt_passages.py` (removed 2026-11-17) and was deleted with its
tests; sentence segmentation now lives only in
`services/dual_translation/sentence_refs.py`.

Design decisions (confirmed 2026-06-29, see wiki/tasklist/dual-translation.tasks.md
TASK-603 notes):

  * **age_tier is DERIVED, not inherited.** `tests` has no `age_tier`/`register`
    column (verified against wiki/database/schema.tech.md); it carries
    `difficulty` (1-9, NOT NULL). age_tier is `DIFFICULTY_TO_TIER[difficulty]`
    folded to the int 1-6 that `dt_passage.age_tier` (CHECK 1-6) wants — the
    same map test generation already uses. `register` has no source and
    is left NULL (matches the migration's nullable default).

  * **source_ref_id = str(tests.id)** (a uuid) so `routes/dual_translation.py::
    _choose_next` (which filters `dt_passage.source_ref_id IN
    test_attempts.test_id`) can serve the row. `source_kind` is locked to
    'test_transcript'.
"""

from __future__ import annotations

from typing import Optional

from services import language_registry
from services.categorical_maps import DIFFICULTY_TO_TIER

# Languages written without inter-word spaces — controls sentence joining.
_CJK_CODES = frozenset(language_registry.cjk_codes())

SOURCE_KIND = 'test_transcript'
DEFAULT_STATUS = 'active'

# Sentence-window bounds (the "2-4 sentence span" rule).
MIN_WINDOW = 2
MAX_WINDOW = 4


# ---------------------------------------------------------------------------
# age_tier
# ---------------------------------------------------------------------------

def difficulty_to_age_tier(difficulty: int) -> int:
    """Fold a test's `difficulty` (1-9) to the dt age tier int (1-6).

    Reuses DIFFICULTY_TO_TIER (1-2->T1, 3-4->T2, 5->T3, 6->T4, 7->T5, 8-9->T6),
    the repo's single difficulty->tier map. Unknown/None difficulty falls back
    to T3, keeping the result inside
    the CHECK (1-6) range.
    """
    tier_code = DIFFICULTY_TO_TIER.get(int(difficulty) if difficulty is not None else 0, 'T3')
    return int(tier_code[1:])  # 'T3' -> 3


# ---------------------------------------------------------------------------
# Window text
# ---------------------------------------------------------------------------

def _join_sentences(sentences: list[str], language_code: str) -> str:
    """Reassemble a window into passage text. CJK joins with no separator
    (sentences already carry their punctuation); space-delimited languages
    join with a single space."""
    if (language_code or '').lower() in _CJK_CODES:
        return ''.join(sentences)
    return ' '.join(sentences)


def join_sentences(sentences: list[str], language_code: str) -> str:
    """Public alias of ``_join_sentences`` for callers outside this module
    (TASK-909: ``open_range_passage`` assembles a window's ``l2_text`` and
    ``l1_text`` with exactly the convention the batch builder uses)."""
    return _join_sentences(sentences, language_code)


# ---------------------------------------------------------------------------
# Primed-window selection (TASK-909, ADR-037)
# ---------------------------------------------------------------------------

def _sentence_senses(sentence: dict, token_map: Optional[list]) -> set[int]:
    """Sense ids a ``test_sentences`` row covers.

    Prefers an explicit ``sense_ids`` list on the row (fixtures, pre-computed
    callers); otherwise slices ``token_map`` (``tests.vocab_token_map``,
    ``[[surface, sense_id], ...]``) by the row's half-open token span. A row
    with no token span and no sense list covers nothing.
    """
    explicit = sentence.get('sense_ids')
    if explicit is not None:
        return {int(s) for s in explicit if s}
    ts, te = sentence.get('token_start'), sentence.get('token_end')
    if token_map is None or ts is None or te is None:
        return set()
    return {int(sid) for _, sid in token_map[int(ts):int(te)] if sid}


def _sentence_chars(sentence: dict) -> int:
    text = sentence.get('l2_text')
    if text is not None:
        return len(text)
    cs, ce = sentence.get('char_start'), sentence.get('char_end')
    if cs is not None and ce is not None:
        return max(0, int(ce) - int(cs))
    return 0


def window_meets_floor(idxs, tightness: dict[int, float], floor: float,
                       agreed: frozenset = frozenset()) -> bool:
    """The tightness gate for one window (shared by both selectors).

    Mean tightness of the window's references must be at least ``floor``.
    Sentences in ``agreed`` (two independent reviews passed the exact text,
    ADR-050) and sentences with no score are left out of the mean. A window
    with nothing left to average passes when every sentence is agreed, else
    only a ``floor`` of 0.
    """
    idxs = list(idxs)
    vals = [tightness[i] for i in idxs if i not in agreed and tightness.get(i) is not None]
    if vals:
        return sum(vals) / len(vals) >= floor
    if idxs and all(i in agreed for i in idxs):
        return True
    return floor <= 0


def select_window_for_primed(
    sentences: list[dict],
    primed_sense_ids,
    wrong_sense_ids,
    refs_ok: set[int],
    tightness: dict[int, float],
    floor: float,
    min_size: int = MIN_WINDOW,
    max_size: int = MAX_WINDOW,
    token_map: Optional[list] = None,
    agreed: frozenset = frozenset(),
) -> Optional[tuple[int, int]]:
    """Pick the Produce window for a prestudied test (TASK-909).

    Pure function; the demo's ``chooseWindow`` (wiki/demos/test-prestudy-demo.html)
    is the reference implementation. Every contiguous range of ``min_size``..
    ``max_size`` sentences is scored

        primed senses covered * 10 + wrong-question senses covered * 3 - chars / 100

    and the best range wins; ties go to the first candidate found, which —
    because lengths are tried ascending and starts ascending — means the
    shorter, then the earlier, window. A range is only eligible when every
    sentence index is in ``refs_ok`` (has an active ``pass``/``rewritten``
    reference for the learner's L1) and it passes ``window_meets_floor``: the
    mean ``tightness`` of its references is at least ``floor``, leaving out
    sentences in ``agreed`` (ADR-050) and sentences with no recorded
    tightness.

    Args:
        sentences: ``test_sentences`` rows (``idx``, ``l2_text`` or
            ``char_start``/``char_end``, ``token_start``/``token_end``, or an
            explicit ``sense_ids`` list), in index order.
        primed_sense_ids / wrong_sense_ids: sense ids the learner primed and
            the senses behind questions answered wrongly.
        refs_ok: sentence indices with a usable reference.
        tightness: ``{idx: tightness}`` for those references (may be sparse).
        token_map: ``tests.vocab_token_map``; needed when rows carry token
            spans rather than ``sense_ids``.

    Returns ``(start_idx, end_idx)`` inclusive, or ``None`` when no eligible
    range exists (too few sentences, or no fully covered window).
    """
    rows = sorted(sentences or [], key=lambda r: int(r['idx']))
    n = len(rows)
    if n == 0 or min_size < 1 or max_size < min_size:
        return None
    primed = {int(s) for s in (primed_sense_ids or []) if s}
    wrong = {int(s) for s in (wrong_sense_ids or []) if s}
    covered = [_sentence_senses(r, token_map) for r in rows]
    chars = [_sentence_chars(r) for r in rows]
    idxs = [int(r['idx']) for r in rows]

    best: Optional[tuple[float, int, int]] = None
    for length in range(min_size, min(max_size, n) + 1):
        for a in range(0, n - length + 1):
            window = range(a, a + length)
            if any(idxs[k] not in refs_ok for k in window):
                continue
            if not window_meets_floor([idxs[k] for k in window], tightness, floor, agreed):
                continue
            senses: set[int] = set()
            for k in window:
                senses |= covered[k]
            p = len(senses & primed)
            w = len(senses & wrong)
            score = p * 10 + w * 3 - sum(chars[k] for k in window) / 100
            if best is None or score > best[0]:
                best = (score, idxs[a], idxs[a + length - 1])
    if best is None:
        return None
    return best[1], best[2]
