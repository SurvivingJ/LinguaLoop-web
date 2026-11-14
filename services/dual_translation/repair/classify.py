"""Re-check result -> fixed / no_issue_found / still_flagged (tech 6.3). Pure.

"Fixed" means exactly: the originally flagged error (same subtype, or an error
overlapping where the flagged words still sit) is no longer reported for the
sentence, no new major/critical error appeared, and the corrected form is
present. ``no_issue_found`` is the same without the corrected form (a valid
alternative). Remaining minor errors block neither.
"""

from __future__ import annotations

from typing import Optional

from services.dual_translation.repair import planner, settings
from services.dual_translation.tier0 import _normalize_l2

FIXED = "fixed"
NO_ISSUE = "no_issue_found"
STILL = "still_flagged"
REASON_TARGET = "target_present"
REASON_NEW = "new_error"

DETAIL_MAX_ERRORS = 5
NOTE_MAX = 240
SERIOUS = ("major", "critical")


def _fold_map(text: str, l2_code: str) -> tuple[str, list[int]]:
    parts, index = [], []
    for i, ch in enumerate(text or ""):
        for f in _normalize_l2(ch, l2_code).casefold():
            parts.append(f)
            index.append(i)
    return "".join(parts), index


def norm(text: str, l2_code: str) -> str:
    """Comparison form: tier-0 width/kana fold, case fold, whitespace collapsed."""
    return " ".join(_normalize_l2(text or "", l2_code).casefold().split())


def locate(text: str, form: str, l2_code: str, anchor: Optional[int]) -> Optional[tuple[int, int]]:
    """Raw [start, end) of the (normalised) occurrence of ``form`` in ``text``
    nearest ``anchor``; None when ``form`` is empty or absent."""
    form = (form or "").strip()
    if not form or not text:
        return None
    folded, index = _fold_map(text, l2_code)
    folded_form, _ = _fold_map(form, l2_code)
    if not folded_form:
        return None
    starts = []
    pos = folded.find(folded_form)
    while pos != -1:
        starts.append(pos)
        pos = folded.find(folded_form, pos + 1)
    if not starts:
        return None
    chosen = starts[0] if anchor is None else min(starts, key=lambda p: (abs(index[p] - anchor), index[p]))
    return index[chosen], index[chosen + len(folded_form) - 1] + 1


def _overlaps(span, target: tuple[int, int]) -> bool:
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        return False
    s, e = span
    ts, te = target
    if s == e:
        return ts <= s <= te
    if ts == te:
        return s <= ts <= e
    return s < te and ts < e


def _active_from(err: dict) -> dict:
    span = err.get("span") or [None, None]
    return {
        "subtype": err.get("subtype"), "severity": err.get("severity"),
        "form": err.get("learner_form") or "", "start": span[0], "end": span[1],
        "corrected_form": err.get("corrected_form") or "",
        "correction_source": err.get("correction_source"), "span_source": err.get("span_source"),
        "model_note": (err.get("model_note") or None),
    }


def where_for(active: dict, text: str) -> Optional[dict]:
    """A Where object for ``active`` in ``text`` when its location is usable
    (span source not ``sentence``, inside the text, width <= the share)."""
    s, e = active.get("start"), active.get("end")
    if not isinstance(s, int) or not isinstance(e, int) or s < 0 or e < s or e > len(text or ""):
        return None
    if active.get("span_source") not in planner.LOCATABLE_SOURCES:
        return None
    if (e - s) > settings.DT_REPAIR_LOCATION_MAX_SHARE * max(1, len((text or "").strip())):
        return None
    return {"start": s, "end": e, "text": text[s:e], "point": s == e}


def _sort_key(err: dict):
    span = err.get("span") or [None]
    return planner.error_sort_key({**err, "id": 0}, span[0] if isinstance(span[0], int) else None)


def classify(active: dict, revised: str, reference_sentence: str, errors: list, l2_code: str) -> dict:
    """-> {result, reason, active (the new target, or the old one when not
    still_flagged), detail (compact, for result_detail)}."""
    target = locate(revised, active.get("form") or "", l2_code, active.get("start"))
    matches = [e for e in errors
               if e.get("subtype") == active.get("subtype")
               or (target is not None and _overlaps(e.get("span"), target))]
    others = [e for e in errors if e not in matches]
    serious = [e for e in others if e.get("severity") in SERIOUS]

    if matches:
        chosen = min(matches, key=lambda e: (0 if e.get("subtype") == active.get("subtype") else 1,
                                             *_sort_key(e)))
        result, reason, new_active = STILL, REASON_TARGET, _active_from(chosen)
    elif serious:
        result, reason, new_active = STILL, REASON_NEW, _active_from(min(serious, key=_sort_key))
    else:
        reason = None
        new_active = active
        if active.get("correction_source") == "reference_sentence":
            fixed = norm(revised, l2_code) == norm(reference_sentence, l2_code)
        else:
            fixed = norm(active.get("corrected_form") or "", l2_code) in norm(revised, l2_code)
        result = FIXED if fixed else NO_ISSUE

    detail = {"r": reason, "e": [
        [e.get("subtype"), e.get("severity"), (e.get("span") or [None, None])[0],
         (e.get("span") or [None, None])[1], e.get("confidence_label")]
        for e in sorted(errors, key=_sort_key)[:DETAIL_MAX_ERRORS]
    ]}
    if result == STILL and new_active.get("model_note"):
        detail["x"] = str(new_active["model_note"])[:NOTE_MAX]
    return {"result": result, "reason": reason, "active": new_active, "detail": detail}
