"""Passage builder for Dual Translation (TASK-603).

Pure logic for turning an existing `tests.transcript` into one or more
`dt_passage` gold rows (2-4 sentence spans) plus one `dt_passage_reference`
per supported L1 (!= the passage's L2). Nothing here touches the DB directly:
the only network-touching function (`generate_l1_reference`) takes its router
resolver and model caller as injectable arguments so the whole module is
unit-testable with everything mocked. The batch runner that wires this to a
live Supabase + OpenRouter is `scripts/build_dt_passages.py`.

Design decisions (confirmed 2026-06-29, see wiki/tasklist/dual-translation.tasks.md
TASK-603 notes):

  * **age_tier is DERIVED, not inherited.** `tests` has no `age_tier`/`register`
    column (verified against wiki/database/schema.tech.md); it carries
    `difficulty` (1-9, NOT NULL). age_tier is `DIFFICULTY_TO_TIER[difficulty]`
    folded to the int 1-6 that `dt_passage.age_tier` (CHECK 1-6) wants — the
    same map test/mystery generation already use. `register` has no source and
    is left NULL (matches the migration's nullable default).

  * **source_ref_id = str(tests.id)** (a uuid) so `routes/dual_translation.py::
    _select_next_passage` (which filters `dt_passage.source_ref_id IN
    test_attempts.test_id`) can serve the row. `source_kind` is locked to
    'test_transcript'; mystery scenes are a separate table and simply not
    sourced here.

  * **Idempotency is in-app** (no content UNIQUE on dt_passage): a passage is a
    duplicate if a row already exists with the same
    (source_ref_id, normalized l2_text). `dedupe_key` produces that tuple;
    `select_new_passages` filters candidates against a set of existing keys.

  * **Segmentation is CJK-aware regex** (no library): split on CJK/Latin
    sentence terminators, then pack into non-overlapping 2-4 sentence windows,
    merging a short (<2) trailing remainder by rebalancing the last two windows
    so every window stays within [2, 4].

  * **Reference generation reuses the grading router** (TASK-600): the L1
    reference is produced by the same cheap slug configured for grading this
    L2 (`resolve_tier(db, 'tier1', l2_language_id)`), recorded as
    `generator_slug` provenance. The reference is a *plain* L1 translation —
    the grader's L2-only / numerical-output contract does NOT apply here.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Callable, Optional

import jaconv

from services.categorical_maps import DIFFICULTY_TO_TIER
from services.dual_translation.router import resolve_tier
from services.model_arena.llm_runner import call_model_with_usage

logger = logging.getLogger(__name__)

# Supported study-language dimension ids (Config.LANGUAGES): 1=zh, 2=en, 3=ja.
# `es` is a UI i18n locale only — dim_languages has no row for it, so it is NOT
# a valid L1/L2 here (see memory webapp-dt-supported-l1l2-langs).
SUPPORTED_LANGUAGE_IDS: tuple[int, ...] = (1, 2, 3)

# ISO 639-1 -> English name, for the reference-translation prompt only.
_LANGUAGE_NAME: dict[str, str] = {'zh': 'Chinese', 'en': 'English', 'ja': 'Japanese'}

# Languages written without inter-word spaces — controls both sentence joining
# and dedupe normalization.
_CJK_CODES = frozenset({'zh', 'ja'})

SOURCE_KIND = 'test_transcript'
DEFAULT_STATUS = 'active'

# Sentence-window bounds (the "2-4 sentence span" rule).
MIN_WINDOW = 2
MAX_WINDOW = 4

# Sentence terminators. CJK 。！？ + ellipsis, plus half-width ! ? that ZH/JA
# text frequently mixes in. Latin . ! ? are only treated as boundaries when
# followed by whitespace or end-of-text (so "Mr. Smith" is not over-split in
# the common case — a residual over-split just lands two fragments in the same
# 2-4 window, so it is harmless to the output).
_CJK_TERMINATORS = '。！？…!?'
_CJK_SENTENCE_RE = re.compile(r'[^' + _CJK_TERMINATORS + r']*[' + _CJK_TERMINATORS + r']+|.+')
_LATIN_SENTENCE_RE = re.compile(r'.*?[.!?]+(?=\s|$)|.+', re.DOTALL)
_WHITESPACE_RE = re.compile(r'\s+')


# ---------------------------------------------------------------------------
# age_tier
# ---------------------------------------------------------------------------

def difficulty_to_age_tier(difficulty: int) -> int:
    """Fold a test's `difficulty` (1-9) to the dt age tier int (1-6).

    Reuses DIFFICULTY_TO_TIER (1-2->T1, 3-4->T2, 5->T3, 6->T4, 7->T5, 8-9->T6),
    the repo's single difficulty->tier map. Unknown/None difficulty falls back
    to T3 (the same default mystery generation uses), keeping the result inside
    the CHECK (1-6) range.
    """
    tier_code = DIFFICULTY_TO_TIER.get(int(difficulty) if difficulty is not None else 0, 'T3')
    return int(tier_code[1:])  # 'T3' -> 3


# ---------------------------------------------------------------------------
# Sentence segmentation + windowing
# ---------------------------------------------------------------------------

def segment_sentences(text: Optional[str], language_code: str) -> list[str]:
    """Split `text` into sentences, CJK-aware.

    Whitespace is collapsed first (so newlines in a transcript don't create
    spurious fragments). Terminators stay attached to the sentence they end.
    A terminator-less trailing fragment is kept as a final sentence.
    """
    cleaned = _WHITESPACE_RE.sub(' ', (text or '')).strip()
    if not cleaned:
        return []

    pattern = _CJK_SENTENCE_RE if (language_code or '').lower() in _CJK_CODES else _LATIN_SENTENCE_RE
    return [m.group(0).strip() for m in pattern.finditer(cleaned) if m.group(0).strip()]


def window_sentences(
    sentences: list[str], min_size: int = MIN_WINDOW, max_size: int = MAX_WINDOW,
) -> list[list[str]]:
    """Pack sentences into non-overlapping windows of `min_size`..`max_size`.

    * Fewer than `min_size` sentences total -> [] (too short to form a valid
      span; the whole transcript is skipped rather than emitting a 1-sentence
      passage).
    * `min_size`..`max_size` sentences -> a single window.
    * More -> greedy `max_size` chunks; if the final chunk is shorter than
      `min_size`, it is merged with the preceding window and the pair is
      rebalanced into two windows that both stay within [min_size, max_size]
      (e.g. a trailing 4+1 becomes 3+2), so no sentence is dropped and no
      window exceeds `max_size`.
    """
    n = len(sentences)
    if n < min_size:
        return []
    if n <= max_size:
        return [list(sentences)]

    windows = [list(sentences[i:i + max_size]) for i in range(0, n, max_size)]

    if len(windows) >= 2 and len(windows[-1]) < min_size:
        tail = windows.pop()
        prev = windows.pop()
        combined = prev + tail
        mid = (len(combined) + 1) // 2
        windows.append(combined[:mid])
        windows.append(combined[mid:])

    return windows


def _join_sentences(sentences: list[str], language_code: str) -> str:
    """Reassemble a window into passage text. CJK joins with no separator
    (sentences already carry their punctuation); space-delimited languages
    join with a single space."""
    if (language_code or '').lower() in _CJK_CODES:
        return ''.join(sentences)
    return ' '.join(sentences)


def join_sentences(sentences: list[str], language_code: str) -> str:
    """Public alias of ``_join_sentences`` for callers outside this module
    (TASK-909: ``passage-from-sentences`` assembles a window's ``l2_text`` and
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
    reference for the learner's L1) and the mean ``tightness`` of its
    references is at least ``floor``; sentences with no recorded tightness are
    left out of the mean, and a range with no recorded tightness at all only
    passes a ``floor`` of 0.

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
            vals = [tightness[idxs[k]] for k in window
                    if tightness.get(idxs[k]) is not None]
            if vals:
                if sum(vals) / len(vals) < floor:
                    continue
            elif floor > 0:
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


# ---------------------------------------------------------------------------
# Passage rows
# ---------------------------------------------------------------------------

def build_passages_for_test(test: dict, language_code: str) -> list[dict]:
    """Build the dt_passage row payloads (no id, no DB) for one test row.

    `test` needs: id (uuid), transcript (str|None), difficulty (int),
    language_id (int). Returns one dict per 2-4 sentence span; an empty/blank
    or too-short transcript yields [].
    """
    windows = window_sentences(segment_sentences(test.get('transcript'), language_code))
    age_tier = difficulty_to_age_tier(test.get('difficulty'))
    rows = []
    for window in windows:
        rows.append({
            'l2_language_id': test['language_id'],
            'source_kind': SOURCE_KIND,
            'source_ref_id': str(test['id']),
            'l2_text': _join_sentences(window, language_code),
            'age_tier': age_tier,
            'register': None,  # no source column on tests; stays NULL
            'status': DEFAULT_STATUS,
        })
    return rows


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def normalize_for_dedupe(text: str, language_code: str) -> str:
    """Normalized form used purely as a dedupe identity (not for grading).

    NFKC (folds full/half-width), kana folding for JA (same NFKC + jaconv pair
    services.dual_translation.tier0 uses), whitespace collapsed and stripped so
    cosmetic re-spacing of an identical span doesn't read as a new passage.
    """
    out = unicodedata.normalize('NFKC', text or '')
    if (language_code or '').lower() == 'ja':
        out = jaconv.kata2hira(out)
    return _WHITESPACE_RE.sub(' ', out).strip().lower()


def dedupe_key(source_ref_id, l2_text: str, language_code: str) -> tuple[str, str]:
    """The (source_ref_id, normalized l2_text) identity a passage dedupes on."""
    return (str(source_ref_id), normalize_for_dedupe(l2_text, language_code))


def select_new_passages(
    candidates: list[dict], existing_keys: set[tuple[str, str]], language_code: str,
) -> list[dict]:
    """Filter candidate passage rows down to those not already present.

    `existing_keys` is the set of `dedupe_key`s already in dt_passage for this
    language. Also de-dupes within the candidate batch itself (two identical
    spans extracted in one run collapse to one).
    """
    seen = set(existing_keys)
    fresh = []
    for row in candidates:
        key = dedupe_key(row['source_ref_id'], row['l2_text'], language_code)
        if key in seen:
            continue
        seen.add(key)
        fresh.append(row)
    return fresh


# ---------------------------------------------------------------------------
# L1 references
# ---------------------------------------------------------------------------

def reference_l1_ids(
    l2_language_id: int, supported_ids: tuple[int, ...] = SUPPORTED_LANGUAGE_IDS,
) -> list[int]:
    """The supported L1 language ids that need a reference for this passage:
    every supported language except the passage's own L2."""
    return [lid for lid in supported_ids if lid != l2_language_id]


def _reference_prompt(l2_text: str, l1_code: str) -> str:
    l1_name = _LANGUAGE_NAME.get((l1_code or '').lower(), l1_code)
    return (
        f"Translate the following passage into natural, fluent {l1_name}. "
        f"Preserve the meaning and register faithfully. "
        f"Output only the translation itself, with no notes, labels, or quotation marks.\n\n"
        f"{l2_text}"
    )


def generate_l1_reference(
    db,
    *,
    l2_text: str,
    l2_language_id: int,
    l1_language_id: int,
    l1_code: str,
    tier: str = 'tier1',
    temperature: float = 0.3,
    resolve: Callable = resolve_tier,
    call: Callable = call_model_with_usage,
) -> Optional[dict]:
    """Generate one L1 reference translation of `l2_text` and return the row
    payload for dt_passage_reference (sans passage_id), or None if no slug is
    available.

    The model slug is resolved via the grading router for this L2 (`resolve`),
    so references ride the same cheap model grading uses; `generator_slug`
    records exactly which slug produced the text. `resolve`/`call` are injected
    for testing. If the router falls open with no usable slug (e.g. the
    router-seed migration isn't applied / the slug is delisted), this returns
    None so the caller can log and skip rather than crash the batch.
    """
    route = resolve(db, tier, l2_language_id)
    slug = getattr(route, 'slug', None)
    if not slug:
        logger.warning(
            "passage_builder: no usable model slug for L2=%s (route reason: %s); "
            "skipping L1=%s reference",
            l2_language_id, getattr(route, 'reason', None), l1_language_id,
        )
        return None

    content, _prompt_tokens, _completion_tokens, _latency = call(
        slug, _reference_prompt(l2_text, l1_code), temperature=temperature,
    )
    l1_text = (content or '').strip()
    if not l1_text:
        logger.warning(
            "passage_builder: empty L1=%s reference from slug %s; skipping",
            l1_language_id, slug,
        )
        return None

    return {
        'l1_language_id': l1_language_id,
        'l1_text': l1_text,
        'generator_slug': slug,
    }
