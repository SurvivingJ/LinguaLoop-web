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

    ``l1_text`` is a holistic LLM translation of the whole passage
    (``passage_builder.generate_l1_reference``), not sentence-aligned by
    construction, so there is no ground truth for "sentence N on the L1 side
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

def _latest_error_for_subtype(db, user_id: str, subtype: str) -> dict | None:
    """The most recent ``dt_error_instance`` for this user in this subtype
    cluster — the representative error a card gets built from. Explicit
    id-set lookups (submission_ids -> error rows) rather than an embedded
    select, matching ``scripts/dt_nightly_synthesis.py``'s convention of not
    depending on PostgREST FK-relationship auto-detection.
    """
    subs = (
        db.table("dt_submission").select("id").eq("user_id", user_id).execute().data
        or []
    )
    submission_ids = [s["id"] for s in subs]
    if not submission_ids:
        return None

    errors = (
        db.table("dt_error_instance")
        .select("id, submission_id, span_reference, corrected_form, learner_form, subtype")
        .in_("submission_id", submission_ids)
        .eq("subtype", subtype)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return errors[0] if errors else None


def _source_texts(db, submission_id: int) -> tuple[str | None, str]:
    """``(gold_l2, l1_text)`` for the passage backing ``submission_id``.
    ``gold_l2`` is ``None`` if the submission or its passage can no longer be
    resolved (caller skips card generation for that error in that case);
    ``l1_text`` degrades to ``''`` rather than blocking (isolate-retranslate
    cards lose their L1 context but the cloze card is unaffected).
    """
    subs = (
        db.table("dt_submission")
        .select("passage_id, l1_language_id")
        .eq("id", submission_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not subs:
        return None, ""
    passage_id = subs[0]["passage_id"]
    l1_language_id = subs[0]["l1_language_id"]

    passages = (
        db.table("dt_passage")
        .select("l2_text")
        .eq("id", passage_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not passages:
        return None, ""
    gold_l2 = passages[0]["l2_text"]

    refs = (
        db.table("dt_passage_reference")
        .select("l1_text")
        .eq("passage_id", passage_id)
        .eq("l1_language_id", l1_language_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    l1_text = refs[0]["l1_text"] if refs else ""
    return gold_l2, l1_text


def generate_cards_for_queued_entries(db, user_id: str) -> int:
    """Materialise ``dt_card`` rows for this user's promoted (``queued``)
    ``dt_error_profile_entry`` clusters that don't have cards yet, then flip
    each to ``drilling`` — the DB-wiring half of pipeline steps 5-6
    ([[features/dual-translation-remediation.tech]] §Pipeline) that the pure
    functions above intentionally leave undone. Idempotent: a profile entry
    that already has a ``dt_card`` row is skipped, so calling this on every
    ``GET /next``/``GET /cards/due`` request is safe.

    Returns the number of profile entries newly carded.
    """
    queued = (
        db.table("dt_error_profile_entry")
        .select("id, subtype")
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

    carded = 0
    for entry in queued:
        if entry["id"] in already_carded:
            continue

        error = _latest_error_for_subtype(db, user_id, entry["subtype"])
        if error is None:
            continue

        gold_l2, l1_text = _source_texts(db, error["submission_id"])
        if gold_l2 is None:
            continue

        payloads = build_cards(error, gold_l2, l1_text)
        rows = [
            {
                **payload,
                "user_id": user_id,
                "profile_entry_id": entry["id"],
                "origin_error_id": error["id"],
                "state": "new",
            }
            for payload in payloads
        ]
        db.table("dt_card").insert(rows).execute()
        db.table("dt_error_profile_entry").update(
            {"remediation_status": "drilling"}
        ).eq("id", entry["id"]).execute()
        carded += 1

    return carded


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
