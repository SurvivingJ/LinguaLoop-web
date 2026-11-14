"""Eligibility and step planning (tech 3.2). Pure.

``plan(...)`` turns a persisted grade, its ``dt_error_instance`` rows (with ids)
and the sentence model into the repair session's steps. One step per flagged
sentence, working on that sentence's primary (most serious) error.
"""

from __future__ import annotations

from typing import Optional

from services.dual_translation.repair import hints, settings
from services.dual_translation.repair.sentences import PairModel, local_span

SEVERITY_RANK = {"critical": 3, "major": 2, "minor": 1}
MEANING_TYPES = ("meaning_inversion", "contradiction", "semantic_anomaly", "omission", "addition")
LOCATABLE_SOURCES = ("exact", "normalised", "fuzzy", "diff_hunk")

STATUS_INELIGIBLE = "ineligible"
STATUS_CLEAN = "finished"
STATUS_BYPASSED = "bypassed"
STATUS_OPEN = "open"


def _confidence(err: dict) -> float:
    try:
        return float(err.get("confidence") if err.get("confidence") is not None else 0.5)
    except (TypeError, ValueError):
        return 0.5


def is_eligible_trace(grade: dict, errors: list) -> tuple[bool, str]:
    """The grade-level part of eligibility (no sentence model needed)."""
    if not settings.DT_GUIDED_REPAIR:
        return False, "flag_off"
    if not hints.available():
        return False, "hint_templates_unavailable"
    if grade.get("overall_band") is None:
        return False, "not_persisted"
    trace = grade.get("grader_trace") or {}
    tier = trace.get("tier")
    if tier == "single_call":
        return True, ""
    # A Tier-0 exact / near-exact grade. The v1/v2 flows can also report
    # tier='tier0' when every model call failed; those are not a tier-0 resolution
    # (deterministic_prefilter False) and are not eligible.
    if tier == "tier0" and trace.get("deterministic_prefilter") and not errors:
        return True, ""
    return False, f"tier:{tier}"


def error_sort_key(err: dict, local_start: Optional[int] = None):
    """Severity desc, meaning type first, confidence desc, span start asc, id asc."""
    return (
        -SEVERITY_RANK.get(err.get("severity"), 0),
        0 if err.get("subtype") in MEANING_TYPES else 1,
        -_confidence(err),
        local_start if local_start is not None else 10 ** 9,
        err.get("id") if isinstance(err.get("id"), int) else 10 ** 12,
    )


def location(err: dict, pm: PairModel) -> tuple[bool, Optional[tuple[int, int]]]:
    """(location_available, local learner span or None)."""
    span = local_span(err.get("span_reproduction"), pm.repro_start, pm.repro_end)
    if span is None:
        return False, None
    if err.get("span_source") not in LOCATABLE_SOURCES:
        return False, span
    width = span[1] - span[0]
    length = pm.repro_end - pm.repro_start
    if width > settings.DT_REPAIR_LOCATION_MAX_SHARE * length:
        return False, span
    return True, span


def active_from_error(err: dict, pm: PairModel) -> dict:
    """The item's initial target (tech 6.3 ``active``), local offsets."""
    _, span = location(err, pm)
    return {
        "subtype": err.get("subtype"),
        "severity": err.get("severity"),
        "form": err.get("learner_form") or "",
        "start": span[0] if span else None,
        "end": span[1] if span else None,
        "corrected_form": err.get("corrected_form") or "",
        "correction_source": err.get("correction_source"),
        "span_source": err.get("span_source"),
        "error_id": err.get("id"),
    }


def plan(grade: dict, errors: list, model: list[PairModel], age_tier: Optional[int]) -> dict:
    """-> {eligible, reason, status, steps, direct_items, n_sentences, n_flagged}.

    ``steps`` (open session) and ``direct_items`` (bypass) are dicts with:
    sentence_index, step_kind, ladder, location_available, span (local or None),
    rungs, step_order, error (the primary row), active."""
    ok, reason = is_eligible_trace(grade, errors)
    n_sentences = len(model)
    base = {"eligible": False, "reason": reason, "status": STATUS_INELIGIBLE, "steps": [],
            "direct_items": [], "n_sentences": n_sentences, "n_flagged": 0}
    if not ok:
        return base
    for err in errors:
        idx = err.get("sentence_index")
        if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < n_sentences:
            return {**base, "reason": "sentence_index_missing"}
        if not isinstance(err.get("id"), int):
            return {**base, "reason": "error_id_missing"}

    by_sentence: dict[int, list] = {}
    for err in errors:
        by_sentence.setdefault(err["sentence_index"], []).append(err)
    flagged = sorted(by_sentence)
    result = {**base, "eligible": True, "reason": "", "n_flagged": len(flagged)}

    if not flagged:
        return {**result, "status": STATUS_CLEAN}

    def primary(idx: int) -> dict:
        pm = model[idx]
        return min(by_sentence[idx], key=lambda e: error_sort_key(
            e, (local_span(e.get("span_reproduction"), pm.repro_start, pm.repro_end) or (None,))[0]))

    scores = grade.get("scores") or {}
    if len(flagged) >= settings.DT_REPAIR_BYPASS_FLAGGED or any(v == 1 for v in scores.values()):
        items = []
        for idx in flagged:
            err = primary(idx)
            loc, span = location(err, model[idx])
            items.append({
                "sentence_index": idx, "step_kind": "direct",
                "ladder": _ladder(err, age_tier), "location_available": loc, "span": span,
                "rungs": [], "step_order": None, "error": err, "active": active_from_error(err, model[idx]),
            })
        return {**result, "status": STATUS_BYPASSED, "direct_items": items}

    steps = []
    candidates = []
    for idx in flagged:
        err = primary(idx)
        loc, span = location(err, model[idx])
        ladder = _ladder(err, age_tier)
        unsure = all(_confidence(e) < settings.DT_REPAIR_UNSURE_CONFIDENCE_MAX for e in by_sentence[idx])
        step = {"sentence_index": idx, "ladder": ladder, "location_available": loc, "span": span,
                "error": err, "active": active_from_error(err, model[idx])}
        if unsure:
            step.update(step_kind="unsure", rungs=[])
        elif ladder == "none":
            step.update(step_kind="direct", rungs=[])
        else:
            step.update(step_kind="repair", rungs=hints.rungs(ladder, loc))
            candidates.append(step)
        steps.append(step)

    candidates.sort(key=lambda s: (
        -SEVERITY_RANK.get(s["error"].get("severity"), 0),
        0 if s["error"].get("subtype") in MEANING_TYPES else 1,
        -_confidence(s["error"]),
        s["sentence_index"],
    ))
    for step in candidates[settings.DT_REPAIR_MAX_TARGETS:]:
        step.update(step_kind="direct", rungs=[])

    steps.sort(key=lambda s: s["sentence_index"])
    for order, step in enumerate(steps):
        step["step_order"] = order
    return {**result, "status": STATUS_OPEN, "steps": steps}


def _ladder(err: dict, age_tier: Optional[int]) -> str:
    ladder = hints.ladder_for(err.get("subtype") or "")
    if ladder == "full" and isinstance(age_tier, int) and age_tier in (1, 2):
        return "short"
    return ladder
