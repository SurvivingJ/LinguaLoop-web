"""Dual Translation — remediation card generation (TASK-613) + DB/FSRS
wiring (TASK-614).

The top section is pure functions that turn one graded ``dt_error_instance``
record into remediation card payloads (Feature 2, pipeline step 5 —
[[features/dual-translation-remediation.tech]] §Pipeline). Every card is built
strictly toward ``corrected_form``; ``prompt_payload`` never carries
``learner_form`` at all, so it can never surface as the answer target — the
non-negotiable invariant these cards exist to enforce (see the
``dt_card.prompt_payload`` column comment in ``migrations/dt_cards.sql``).

The bottom section (``generate_cards_for_queued_entries`` and its helpers) is
DB-touching: it fetches the source passage/reproduction text for a promoted
``dt_error_profile_entry``, attaches FK ids, and writes ``dt_card`` rows —
pipeline step 5's DB half plus the ``queued -> drilling`` transition (step 6
scheduling itself is FSRS, reused as-is from ``services/vocabulary/fsrs.py``
by the route layer). ``interleave_by_subtype`` stays pure — it just reorders
an already-fetched list — and is shared by the due-queue endpoint and the
``GET /next`` interleave.
"""

import logging
import math
import os
import re
from datetime import date

from config import Config

logger = logging.getLogger(__name__)

CARD_TYPE_CLOZE = "cloze"
CARD_TYPE_ISOLATE_RETRANSLATE = "isolate_retranslate"

CLOZE_BLANK = "____"

# Practice Engine item shape for an injected error card (TASK-618). The synthetic
# ``exercise_type`` lets any FE keying on that field discriminate remediation
# items; ``type='error_card'`` mirrors the GET /next error-card response so both
# surfaces speak the same shape.
ERROR_EXERCISE_TYPE = "dt_error_card"

# TASK-618: caps for injecting due error cards into a Practice Engine session.
# Read straight from the environment (not Config) to match
# ``DT_ERROR_CARD_INTERLEAVE_EVERY`` and the other DT_* tunables (memory
# ``dt-synthesis-tunables-in-env``). Two independent guards keep remediation
# from crowding out normal practice:
#   MAX      — absolute ceiling on error cards injected per session.
#   FRACTION — error cards may not exceed this share of the normal (sense-linked)
#              items; with no normal items the fraction cap is 0, so error cards
#              interleave INTO a real session rather than standing in for an empty
#              one (that surface stays GET /next's job).
DT_PRACTICE_ERROR_CARD_MAX = max(0, int(os.environ.get("DT_PRACTICE_ERROR_CARD_MAX", "3")))
DT_PRACTICE_ERROR_CARD_FRACTION = float(
    os.environ.get("DT_PRACTICE_ERROR_CARD_FRACTION", "0.34")
)

# A permissive, language-agnostic sentence boundary: split after any Latin or
# CJK terminator, keeping it with the preceding sentence. The split does not
# need to be linguistically perfect — a card that lands a clause short or long
# is still a coherent remediation prompt; it only needs to reliably CONTAIN
# the error span it is built around (guaranteed by the fallback below).
_SENTENCE_END = re.compile(r"[^.!?。!?…]*[.!?。!?…]+")


def _sentence_span(text: str, span: list[int]) -> tuple[int, int]:
    """The (start, end) offsets of the sentence in ``text`` containing ``span``.

    Falls back to the whole text if no detected sentence fully contains the
    span (e.g. terminator-less text, or a boundary the splitter misjudged) —
    a wider fallback context is always safe, just less tightly scoped.
    """
    lo, hi = span[0], span[1]
    start = 0
    for match in _SENTENCE_END.finditer(text):
        end = match.end()
        if start <= lo and hi <= end:
            return start, end
        start = end
    if start <= lo and hi <= len(text):
        return start, len(text)
    return 0, len(text)


def _sentence_index(text: str, span: list[int]) -> int:
    """The ordinal (0-based) index, among the sentences ``_SENTENCE_END``
    finds in ``text``, of the sentence containing ``span`` -- or ``-1`` if
    none fully contains it (mirrors ``_sentence_span``'s primary-loop
    condition; deliberately does NOT mirror its whole-text fallback, since a
    caller using this to pick a corresponding sentence on the OTHER side of a
    translation has no safe guess to make there either)."""
    lo, hi = span[0], span[1]
    start = 0
    for i, match in enumerate(_SENTENCE_END.finditer(text)):
        end = match.end()
        if start <= lo and hi <= end:
            return i
        start = end
    return -1


def _split_sentences(text: str) -> list[str]:
    """``text`` split into trimmed sentences via ``_SENTENCE_END`` (a
    terminator-less trailing fragment, if any, is dropped -- same boundary
    the regex draws everywhere else in this module)."""
    return [match.group().strip() for match in _SENTENCE_END.finditer(text)]


def _blank(text: str, local_span: list[int], marker: str = CLOZE_BLANK) -> str:
    """``text`` with ``local_span`` replaced by ``marker``. Works identically
    for a deletion span and a zero-width insertion-point span (an omission
    error), since both are just ``text[:start] + marker + text[end:]``."""
    return (text[:local_span[0]] + marker + text[local_span[1]:]).strip()


def _blank_span_for(sentence: str, local_span: list[int], corrected_form: str) -> list[int]:
    """The span to blank out of ``sentence``.

    Normally ``local_span`` — the grader's span, translated into sentence-local
    offsets — because ``span_reference`` is guaranteed to cover ``corrected_form``:
    ``_reconcile_span_form`` establishes that at decode time and
    ``tests/test_dt_error_span_invariant.py`` asserts it on every persisted row.

    **This is belt-and-braces, not the fix.** It was written against 15 live rows
    whose spans pointed at one clause while ``corrected_form`` named a different
    one — but those rows were all written before the reconciler landed on
    2026-07-19, and have since been realigned at the source by
    ``scripts/dt_backfill_error_spans.py``. The upstream defect is closed; nothing
    is expected to reach here misaligned any more.

    It is kept anyway because the failure it prevents is disproportionate to its
    cost: blanking a drifted span hides an unrelated clause AND leaves the answer
    sitting in the prompt, turning productive recall into copying — a card that
    silently tests nothing. Two layers is cheap insurance against one atom of
    untrusted model output.

    So when the span does not actually cover ``corrected_form`` but the
    corrected text occurs verbatim exactly once in the sentence, blank that
    occurrence instead. Deliberately conservative: ambiguous cases (no match, or
    more than one) keep the grader's span, which is the pre-existing behaviour.
    """
    lo, hi = local_span[0], local_span[1]
    if sentence[lo:hi] == corrected_form:
        return local_span
    if not corrected_form:
        return local_span

    first = sentence.find(corrected_form)
    if first == -1:
        return local_span
    if sentence.find(corrected_form, first + 1) != -1:
        return local_span  # ambiguous — do not guess
    return [first, first + len(corrected_form)]


def _l1_context_for(gold_l2: str, l1_text: str, span: list[int]) -> str:
    """The L1 reference text to show alongside an L2 card built around
    ``span``, scoped to the ONE L1 sentence corresponding to that span's
    sentence when that correspondence can be trusted, not the whole
    ``l1_text`` passage.

    ``l1_text`` is the passage's L1 text (the window's sentence references,
    joined; it used to be a holistic whole-passage translation), not
    guaranteed sentence-aligned with the L2 side, so there is no ground truth for "sentence N on the L1 side
    is sentence N on the L2 side." Matching sentence COUNTS on both sides is
    used as the only available signal that the correspondence is likely
    1:1 -- when it holds, index into ``l1_text``'s sentences positionally.
    Any mismatch (or an unmatched span, e.g. a terminator-less trailing
    fragment) falls back to the whole ``l1_text``: a wider context is always
    safe, just less tightly scoped -- the same tradeoff ``_sentence_span``
    makes for the L2 side.
    """
    l1_context = l1_text
    index = _sentence_index(gold_l2, span)
    if index != -1:
        l2_sentences = _split_sentences(gold_l2)
        l1_sentences = _split_sentences(l1_text)
        if len(l1_sentences) == len(l2_sentences) and index < len(l1_sentences):
            l1_context = l1_sentences[index]
    return l1_context


def build_cloze_card(error: dict, gold_l2: str, l1_text: str = "") -> dict:
    """Cloze card payload: the sentence containing the error, with ONLY the
    corrected element blanked (SuperMemo minimum-information principle — one
    atom per card), plus the L1 reference sentence so the learner knows what
    meaning the blank is supposed to express. Answer target is always
    ``corrected_form``.

    ``l1_context`` is what makes the blank solvable rather than a guessing
    game: a blanked L2 sentence alone under-determines the answer whenever
    more than one plausible word could fill the gap (near-synonyms, word-choice
    errors chief among them) -- the learner needs to know what was MEANT, not
    just what shape fits. See ``_l1_context_for`` for how it is scoped to the
    one corresponding L1 sentence. Defaults to ``""`` (degrading to no L1
    context) so existing callers that only have ``gold_l2`` still work.
    """
    span = error["span_reference"]
    sent_start, sent_end = _sentence_span(gold_l2, span)
    local_span = [span[0] - sent_start, span[1] - sent_start]
    sentence = gold_l2[sent_start:sent_end]
    blank_span = _blank_span_for(sentence, local_span, error["corrected_form"])

    return {
        "prompt": _blank(sentence, blank_span),
        "answer": error["corrected_form"],
        "l1_context": _l1_context_for(gold_l2, l1_text, span) if l1_text else "",
    }


def build_isolate_retranslate_card(error: dict, gold_l2: str, l1_text: str) -> dict:
    """Isolate-and-re-translate card payload: the L1 reference as context plus
    the ONE gold L2 sentence the learner must reproduce, for back-translation
    after a spaced delay. Answer target is always ``corrected_form``.

    ``l1_context`` is scoped to the ONE L1 sentence corresponding to
    ``target_sentence`` when that correspondence can be trusted, not the whole
    ``l1_text`` passage (see ``_l1_context_for``). The FE's fixed instruction
    copy is "Translate this into the language you are studying" pointing
    straight at ``l1_context`` -- if that is the whole 2-4 sentence passage
    while only one sentence is ever graded (``answer``/``target_sentence`` are
    always scoped to one sentence), the card asks for one thing and grades
    another.
    """
    span = error["span_reference"]
    sent_start, sent_end = _sentence_span(gold_l2, span)
    target_sentence = gold_l2[sent_start:sent_end].strip()

    return {
        "l1_context": _l1_context_for(gold_l2, l1_text, span),
        "target_sentence": target_sentence,
        "answer": error["corrected_form"],
    }


def build_cards(error: dict, gold_l2: str, l1_text: str) -> list[dict]:
    """Build the ``dt_card``-insert-ready dicts (minus FK ids) for one error.

    Normally both card types. The cloze card is DROPPED when its prompt would
    still contain the answer — a card that shows what it is asking for tests
    nothing. This is the second half of the belt-and-braces described in
    ``_blank_span_for``: the span↔form invariant is enforced upstream at decode
    time, so with the pre-2026-07-19 rows now backfilled this drop is not
    expected to fire. If it ever does, the WARNING is the signal that the
    upstream invariant has regressed — treat it as a bug report, not as routine.
    The isolate-retranslate card still covers the subtype in that case, so the
    cluster is not left unremediated.

    Caller (the DB wiring below) attaches ``user_id``, ``profile_entry_id``,
    and ``origin_error_id`` before inserting into ``dt_card``.
    """
    built = []

    cloze = build_cloze_card(error, gold_l2, l1_text)
    if cloze["answer"] and cloze["answer"] in cloze["prompt"]:
        logger.warning(
            "Dropping cloze card for subtype=%s: prompt still contains the answer "
            "(span_reference %s does not align with corrected_form).",
            error.get("subtype"), error.get("span_reference"),
        )
    else:
        built.append({
            "card_type": CARD_TYPE_CLOZE,
            "subtype": error["subtype"],
            "prompt_payload": cloze,
        })

    built.append({
        "card_type": CARD_TYPE_ISOLATE_RETRANSLATE,
        "subtype": error["subtype"],
        "prompt_payload": build_isolate_retranslate_card(error, gold_l2, l1_text),
    })
    return built


def interleave_by_subtype(due_cards: list[dict]) -> list[dict]:
    """Round-robin ``due_cards`` across their ``subtype`` key so a review
    session never presents a long same-subtype run back-to-back (Rohrer &
    Taylor spacing/interleaving —
    [[features/dual-translation-remediation.tech]] §Testing Strategy:
    "Interleaving: due queue does not block-group a single subtype.").
    Within-subtype order is preserved; subtype order follows first
    appearance in ``due_cards``. Pure — takes and returns plain dicts.
    """
    buckets: dict[str, list[dict]] = {}
    order: list[str] = []
    for card in due_cards:
        subtype = card["subtype"]
        if subtype not in buckets:
            buckets[subtype] = []
            order.append(subtype)
        buckets[subtype].append(card)

    result: list[dict] = []
    while any(buckets[s] for s in order):
        for s in order:
            if buckets[s]:
                result.append(buckets[s].pop(0))
    return result


# ============================================================================
# DB wiring (TASK-614) — materialise dt_card rows for promoted profile
# entries. Everything above this line is pure; everything below touches db.
# ============================================================================

# TASK-1003 (B-03): every read below is batched over all of a learner's
# queued entries, so card generation costs a constant number of round trips
# instead of ~8 per entry. Explicit id-set lookups (submission ids -> error
# rows -> passages) rather than embedded selects, matching
# ``scripts/dt_nightly_synthesis.py``'s convention of not depending on
# PostgREST FK-relationship auto-detection.

# PostgREST's max-rows cap (Supabase default): a response never holds more, so
# reads that can exceed it are paged with .range().
_PAGE = 1000
# Ids per in_() filter: in_() lists travel in the URL.
_IN_CHUNK = 500

_ERROR_COLUMNS = ("id", "submission_id", "span_reference", "corrected_form",
                  "learner_form", "subtype")


def _chunks(seq: list, size: int = _IN_CHUNK):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _paged(make_query) -> list[dict]:
    """Every row of ``make_query()`` (a fresh, totally ordered query each
    call), fetched ``_PAGE`` rows at a time."""
    from services.pagination import fetch_all

    return fetch_all(make_query, _PAGE)


def _newest_first_key(row: dict):
    """Sort key matching ``ORDER BY created_at DESC, id DESC`` (Postgres puts
    NULLs first in a DESC sort), for merging per-chunk winners."""
    created = row.get("created_at")
    if created is None:
        return (1, None, row["id"])
    try:
        from datetime import datetime
        return (0, datetime.fromisoformat(str(created)), row["id"])
    except ValueError:
        return (0, str(created), row["id"])


def _latest_errors_by_key(db, submission_l2: dict, wanted: set[tuple]) -> dict:
    """``{(subtype, l2_language_id): error}``: the most recent
    ``dt_error_instance`` of each wanted subtype among the submissions in
    ``submission_l2`` (``{submission_id: l2 of its passage}``), per language —
    the representative error a card gets built from. Was one
    ``_latest_error_for_subtype`` call (2 round trips) per entry, which ignored
    the language (B-02).

    One query per ``_IN_CHUNK`` submissions (normally one), newest first,
    paged only until every wanted key has been seen. ``id DESC`` breaks
    ``created_at`` ties deterministically (the per-entry ``limit(1)`` left them
    to the planner).
    """
    subtypes = sorted({subtype for subtype, _ in wanted})
    best: dict = {}
    for chunk in _chunks(sorted(submission_l2)):
        found: dict = {}
        start = 0
        while True:
            page = (
                db.table("dt_error_instance")
                .select(", ".join(_ERROR_COLUMNS + ("created_at",)))
                .in_("submission_id", chunk)
                .in_("subtype", subtypes)
                .order("created_at", desc=True)
                .order("id", desc=True)
                .range(start, start + _PAGE - 1)
                .execute()
                .data
                or []
            )
            for row in page:
                key = (row["subtype"], submission_l2.get(row["submission_id"]))
                if key in wanted:
                    found.setdefault(key, row)
            if len(page) < _PAGE or len(found) == len(wanted):
                break
            start += _PAGE
        for key, row in found.items():
            if key not in best or _newest_first_key(row) > _newest_first_key(best[key]):
                best[key] = row
    return {key: {c: row.get(c) for c in _ERROR_COLUMNS} for key, row in best.items()}


def _window_l1_texts(db, windows: list[tuple[dict, object]]) -> dict:
    """``{(passage_id, l1_language_id): l1_text}`` for sentence-window
    passages: each window's sentences' reviewed references (ADR-037), joined.
    A window is absent (caller uses ``''``) when the passage has no sentence
    range or any sentence lacks a usable reference. Two queries for all
    windows; the per-window equivalent is
    ``services.dual_translation.repair.sentences._range_l1_texts`` (same
    filters). The L1 context is optional, so a failed read degrades every
    window to ``''`` rather than blocking card generation."""
    # lazy: the repair package imports this module's siblings
    from services.dual_translation.passage_builder import join_sentences
    from services.dual_translation.repair.sentences import _USABLE_VERDICTS
    from services.dual_translation.sentence_refs import LANG_CODE

    usable = []
    for passage, l1_language_id in windows:
        if passage.get("sentence_start") is None or passage.get("sentence_end") is None \
                or not passage.get("source_ref_id") or l1_language_id is None:
            continue
        usable.append((passage, l1_language_id))
    if not usable:
        return {}

    try:
        spans = [(p["id"], int(l1), str(p["source_ref_id"]),
                  int(p["sentence_start"]), int(p["sentence_end"])) for p, l1 in usable]
        test_ids = sorted({s[2] for s in spans})
        lo = min(s[3] for s in spans)
        hi = max(s[4] for s in spans)
        sentence_rows = _paged(lambda: (
            db.table("test_sentences").select("id, idx, test_id")
            .in_("test_id", test_ids).gte("idx", lo).lte("idx", hi)
            .order("test_id").order("idx").order("id")
        ))
        by_window = {
            (pid, l1): [r for r in sentence_rows
                        if str(r["test_id"]) == test_id and start <= r["idx"] <= end]
            for pid, l1, test_id, start, end in spans
        }
        sentence_ids = sorted({r["id"] for rows in by_window.values() for r in rows})
        l1_ids = sorted({s[1] for s in spans})
        refs: list[dict] = []
        for chunk in _chunks(sentence_ids):
            refs.extend(_paged(lambda chunk=chunk: (
                db.table("test_sentence_references")
                .select("sentence_id, l1_language_id, l1_text, review_verdict")
                .in_("sentence_id", chunk)
                .in_("l1_language_id", l1_ids)
                .eq("is_active", True)
                .in_("review_verdict", list(_USABLE_VERDICTS))
                .order("id")
            )))
    except Exception as exc:  # noqa: BLE001 - the L1 context is optional
        logger.warning("dual_translation.cards: window L1 lookup failed: %s", exc)
        return {}

    ref_by_key = {(r["sentence_id"], r["l1_language_id"]): r for r in refs
                  if r.get("review_verdict") in _USABLE_VERDICTS}
    out = {}
    for (pid, l1), rows in by_window.items():
        if not rows:
            continue
        texts = []
        for row in rows:
            ref = ref_by_key.get((row["id"], l1))
            if not ref or not (ref.get("l1_text") or "").strip():
                texts = None
                break
            texts.append(ref["l1_text"].strip())
        if texts:
            out[(pid, l1)] = join_sentences(texts, LANG_CODE.get(l1, "en"))
    return out


def _taxonomy_stamp(db) -> dict:
    """TASK-851: ``{"taxonomy_version": <active version>}`` for every new
    ``dt_card``, or ``{}``. Empty while ``Config.DT_TAXONOMY_COLUMNS`` is off
    (``dt_card.taxonomy_version`` may not exist yet — PostgREST would reject the
    insert) and when the version read fails (NULL = unstamped, by design)."""
    if not Config.DT_TAXONOMY_COLUMNS:
        return {}
    from services.dual_translation import grader_cascade  # lazy: flag-on path only

    version = grader_cascade.get_active_taxonomy_version(db)
    if version is None:
        logger.warning("dual_translation.cards: active taxonomy version unreadable — cards written unstamped")
        return {}
    return {"taxonomy_version": version}


def _plan_cards(db, user_id: str, entries: list[dict]) -> list[tuple[int, list[dict]]]:
    """``[(entry_id, card rows minus the taxonomy stamp)]`` in entry order, for
    the entries that have a usable latest error on a resolvable passage. All
    reads, no writes."""
    submissions = _paged(lambda: (
        db.table("dt_submission").select("id, passage_id, l1_language_id")
        .eq("user_id", user_id).order("id")
    ))
    if not submissions:
        return []
    submission_by_id = {s["id"]: s for s in submissions}

    # B-02: an error's language is its submission's passage's l2. The passages
    # of every submission in the entries' languages are read once (they also
    # supply the card text), and only those submissions are searched for errors.
    languages = sorted({e["l2_language_id"] for e in entries})
    passages: dict = {}
    for chunk in _chunks(sorted({s["passage_id"] for s in submissions})):
        for p in (
            db.table("dt_passage")
            .select("id, l2_language_id, l2_text, source_ref_id, sentence_start, sentence_end")
            .in_("id", chunk)
            .in_("l2_language_id", languages)
            .execute()
            .data
            or []
        ):
            passages[p["id"]] = p
    submission_l2 = {s["id"]: passages[s["passage_id"]]["l2_language_id"]
                     for s in submissions if s["passage_id"] in passages}
    if not submission_l2:
        return []

    latest = _latest_errors_by_key(
        db, submission_l2, {(e["subtype"], e["l2_language_id"]) for e in entries})

    sources = {}  # entry id -> (error, passage, l1_language_id)
    for entry in entries:
        error = latest.get((entry["subtype"], entry["l2_language_id"]))
        if error is None:
            continue
        submission = submission_by_id[error["submission_id"]]
        sources[entry["id"]] = (error, passages[submission["passage_id"]],
                                submission["l1_language_id"])

    l1_texts = _window_l1_texts(db, [(p, l1) for _, p, l1 in sources.values()])

    plans = []
    for entry in entries:
        if entry["id"] not in sources:
            continue
        error, passage, l1_language_id = sources[entry["id"]]
        l1_text = l1_texts.get((passage["id"], l1_language_id), "")
        rows = [
            {
                **payload,
                "user_id": user_id,
                "profile_entry_id": entry["id"],
                "origin_error_id": error["id"],
                "state": "new",
            }
            for payload in build_cards(error, passage["l2_text"], l1_text)
        ]
        plans.append((entry["id"], rows))
    return plans


def _mark_drilling(db, entry_ids: list[int]) -> None:
    db.table("dt_error_profile_entry").update(
        {"remediation_status": "drilling"}
    ).in_("id", entry_ids).execute()


def _write_one_by_one(db, plans: list[tuple[int, list[dict]]]) -> None:
    """Fallback after the multi-row card insert failed: card and flip each
    entry on its own, so one bad entry no longer blocks the others. Entries
    that already have cards (the failed batch may in fact have committed) are
    only flipped, never carded twice. An entry is flipped to ``drilling`` only
    once its cards exist. Raises the first error after trying every entry."""
    ids = [entry_id for entry_id, _ in plans]
    existing = (
        db.table("dt_card").select("profile_entry_id").in_("profile_entry_id", ids)
        .execute().data or []
    )
    carded = {row["profile_entry_id"] for row in existing}
    first_error = None
    for entry_id, rows in plans:
        try:
            if entry_id not in carded:
                db.table("dt_card").insert(rows).execute()
            _mark_drilling(db, [entry_id])
        except Exception as exc:  # noqa: BLE001 - re-raised below
            logger.warning("dual_translation.cards: carding entry %s failed: %s", entry_id, exc)
            first_error = first_error or exc
    if first_error is not None:
        raise first_error


def _mark_drilling_one_by_one(db, entry_ids: list[int]) -> None:
    """Fallback after the single status update failed (the cards are already
    in): flip each entry on its own; raise the first error after trying all."""
    first_error = None
    for entry_id in entry_ids:
        try:
            _mark_drilling(db, [entry_id])
        except Exception as exc:  # noqa: BLE001 - re-raised below
            logger.warning("dual_translation.cards: flipping entry %s failed: %s", entry_id, exc)
            first_error = first_error or exc
    if first_error is not None:
        raise first_error


def generate_cards_for_queued_entries(db, user_id: str) -> int:
    """Materialise ``dt_card`` rows for this user's promoted (``queued``)
    ``dt_error_profile_entry`` clusters that don't have cards yet, then flip
    each to ``drilling`` — the DB-wiring half of pipeline steps 5-6
    ([[features/dual-translation-remediation.tech]] §Pipeline) that the pure
    functions above intentionally leave undone. Idempotent: a profile entry
    that already has a ``dt_card`` row is skipped, so calling this on every
    ``GET /next``/``GET /cards/due`` request is safe.

    TASK-1003: a constant number of round trips whatever the number of queued
    entries — queued entries, their existing cards, then (only when something
    is uncarded) the learner's submissions, their passages in the entries'
    languages, the latest error per (subtype, language), the window sentences
    and references, the taxonomy version (flag on), one multi-row ``dt_card``
    insert and one status update. Each entry is carded from the latest error
    of its subtype in its own L2 (B-02); with none it stays ``queued``. An
    entry is only ever
    flipped to ``drilling`` after its cards are written; if the batch insert
    or the update fails, each entry is retried on its own (see
    ``_write_one_by_one``) and the first error is raised.

    Returns the number of profile entries newly carded.
    """
    queued = (
        db.table("dt_error_profile_entry")
        .select("id, subtype, l2_language_id")
        .eq("user_id", user_id)
        .eq("remediation_status", "queued")
        .execute()
        .data
        or []
    )
    entry_ids = [e["id"] for e in queued]
    if not entry_ids:
        return 0

    existing = (
        db.table("dt_card")
        .select("profile_entry_id")
        .in_("profile_entry_id", entry_ids)
        .execute()
        .data
        or []
    )
    already_carded = {row["profile_entry_id"] for row in existing}
    uncarded = [e for e in queued if e["id"] not in already_carded]
    if not uncarded:
        return 0

    plans = _plan_cards(db, user_id, uncarded)
    if not plans:
        return 0

    stamp = _taxonomy_stamp(db)
    if stamp:
        plans = [(entry_id, [{**row, **stamp} for row in rows]) for entry_id, rows in plans]

    try:
        db.table("dt_card").insert([row for _, rows in plans for row in rows]).execute()
    except Exception as exc:  # noqa: BLE001 - fall back to per-entry writes
        logger.warning("dual_translation.cards: batch card insert failed, retrying per entry: %s", exc)
        _write_one_by_one(db, plans)
        return len(plans)

    carded_ids = [entry_id for entry_id, _ in plans]
    try:
        _mark_drilling(db, carded_ids)
    except Exception as exc:  # noqa: BLE001 - fall back to per-entry updates
        logger.warning("dual_translation.cards: batch status update failed, retrying per entry: %s", exc)
        _mark_drilling_one_by_one(db, carded_ids)
    return len(plans)


# ============================================================================
# Practice Engine injection (TASK-618) — surface due error cards as a separate,
# non-sense-linked stream that the practice session assembler interleaves into
# the normal (sense-keyed) items. Reuses interleave_by_subtype above.
# ============================================================================

def _to_practice_item(row: dict) -> dict:
    """Shape one due ``dt_card`` row as a Practice Engine session item.

    Deliberately NOT sense-linked (``word_sense_id`` is None) — error cards are
    keyed to ``subtype``, never to a sense, so they bypass sense-pool selection
    entirely. Carries ``card_id`` so the FE submits the grade to the existing
    dual-translation ``POST /cards/<id>/review`` endpoint (FSRS state lives on
    ``dt_card``), not to ``POST /api/practice/attempt``.
    """
    return {
        "id": f"dt-error-{row['id']}",
        "exercise_type": ERROR_EXERCISE_TYPE,
        "type": "error_card",
        "is_error_exercise": True,
        "word_sense_id": None,
        "card_id": row["id"],
        "card_type": row["card_type"],
        "subtype": row["subtype"],
        "prompt_payload": row["prompt_payload"],
        "state": row.get("state"),
        "due_date": row.get("due_date"),
    }


def _due_error_card_rows(db, user_id: str, language_id: int | None) -> list[dict]:
    """This user's due ``dt_card`` rows (``due_date`` today-or-earlier, or a
    never-reviewed ``new`` card), oldest-due first.

    When ``language_id`` is given, restrict to cards whose source error cluster
    is in that L2. ``dt_card`` has no language column, so scope is resolved
    through ``profile_entry_id -> dt_error_profile_entry.l2_language_id`` — a
    Japanese practice session must never surface a Chinese remediation card.
    The two-step id-set lookup (entries -> cards) matches this module's
    no-embedded-select convention (see ``generate_cards_for_queued_entries``).
    """
    entry_ids: list[int] | None = None
    if language_id is not None:
        entries = (
            db.table("dt_error_profile_entry")
            .select("id")
            .eq("user_id", user_id)
            .eq("l2_language_id", language_id)
            .execute()
            .data
            or []
        )
        entry_ids = [e["id"] for e in entries]
        if not entry_ids:
            return []

    today = date.today().isoformat()
    query = (
        db.table("dt_card")
        .select("id, card_type, subtype, prompt_payload, state, due_date")
        .eq("user_id", user_id)
        .or_(f"due_date.lte.{today},state.eq.new")
    )
    if entry_ids is not None:
        query = query.in_("profile_entry_id", entry_ids)
    return query.order("due_date").execute().data or []


def select_error_exercises_for_practice(
    db,
    user_id: str,
    *,
    language_id: int | None = None,
    normal_item_count: int = 0,
    max_cards: int | None = None,
    fraction: float | None = None,
) -> list[dict]:
    """Up to a capped number of due error-remediation exercises, shaped as
    Practice Engine items and interleaved by subtype, for the session assembler
    to inject into a practice session (TASK-618).

    NON-sense-linked stream — never runs through sense-pool selection. Cap is
    ``min(available_due, max_cards, ceil(fraction * normal_item_count))`` so
    remediation never crowds out normal practice; with no normal items the
    fraction cap is 0 and nothing is injected (GET /next remains the surface for
    a due queue with no accompanying practice). Materialises cards for any
    newly-``queued`` profile entries first (idempotent), so a user who only ever
    opens Practice still gets freshly-promoted clusters carded. Returns ``[]``
    when nothing is due or the cap is 0.
    """
    max_cards = DT_PRACTICE_ERROR_CARD_MAX if max_cards is None else max_cards
    fraction = DT_PRACTICE_ERROR_CARD_FRACTION if fraction is None else fraction

    if max_cards <= 0 or normal_item_count <= 0:
        return []
    cap = min(max_cards, math.ceil(normal_item_count * fraction))
    if cap <= 0:
        return []

    generate_cards_for_queued_entries(db, user_id)
    rows = _due_error_card_rows(db, user_id, language_id)
    if not rows:
        return []

    interleaved = interleave_by_subtype([_to_practice_item(r) for r in rows])
    return interleaved[:cap]
