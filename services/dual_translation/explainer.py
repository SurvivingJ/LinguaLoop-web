"""Explainer pass for Dual Translation grading v2 (TASK-630, tech spec §6c/§7e).

One cheap, batched L1 model call per error-bearing submission. It takes the merged
final errors — each already carrying its Rule-template explanation — and asks the
model for a per-error *Application* layer: 1-2 sentences, in the learner's L1, that
name the actual words involved in THIS sentence instead of restating the general
rule. Each returned Application is validated in code and, on any failure, silently
dropped back to Rule-only for that error (ADR-019: the Rule layer already stands on
its own; the Application layer is additive, never load-bearing).

Fail-silent by contract (the whole reason it is a separate module and a separate
call): the Explainer must never block grading, delay the response past its own call,
or flip the grade provisional. Every failure mode — no cheap-tier slug, the call
raising, malformed JSON, or per-error validation rejecting an item — leaves that
error's explanation exactly as the Rule layer produced it, and is logged, not
surfaced.

Contract effect (attached to every error of an error-bearing v2 grade):

    errors[].explanation_parts = {"rule": <rule text>, "application": <text|None>}
    errors[].explanation       = rule                       (application is None)
                               = rule + "\\n" + application  (application present)

The persisted ``dt_error_instance.explanation`` column is that concatenation (§6c —
no schema change); ``explanation_parts`` is a response-only field the route filters
out of the insert.

``call_model_with_usage`` / ``resolve_tier`` are imported into this module's
namespace (not called via their owning modules) so tests can monkeypatch them as
boundaries, mirroring services.dual_translation.grader_cascade.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from services.llm_output_cleaner import clean_json_response
from services.model_arena.llm_runner import call_model_with_usage
from services.dual_translation import prompts
from services.dual_translation.router import resolve_tier

logger = logging.getLogger(__name__)

# §6c per-item validation bounds.
MAX_APPLICATION_CHARS = 240

# "digits formatted like scores" — 3/4, 3 / 4, 12/16 … (§6c). The Application layer
# carries no score authority, so any fraction-shaped number rejects the item.
_SCORE_PATTERN = re.compile(r"\d+\s*/\s*\d+")

# The cheap tier (tech spec §2/§6c: "Explainer — cheap slug"). The router keys the
# slug by the L2 being graded; the prompt language is the learner's L1.
_CHEAP_TIER = "tier1"


def attach_explanations(
    db,
    *,
    errors: list[dict],
    reference: str,
    reproduction: str,
    l1_code: str,
    l2_language_id: int,
    taxonomy_cfg: dict,
) -> tuple[list[dict], int, int, Optional[str]]:
    """Attach ``explanation_parts`` (and, where valid, an Application layer) to every
    error in `errors`, in place, and return ``(errors, tokens_in, tokens_out, reason)``.

    `reason` is None on a clean run, else a short phrase for the caller's
    logging/trace describing why the Application layer was skipped wholesale (no
    slug / call failed / malformed). It is NOT a grading failure and must not flip
    the grade provisional — the caller only uses it (if at all) for token/telemetry.

    Every error always ends up with ``explanation_parts`` set — rule always present,
    ``application`` None unless a validated Application was produced for its index —
    so the v2 contract is uniform whether or not the model call succeeds.
    """
    # Scaffold Rule-only parts first: this is the guaranteed floor, applied even if
    # the model call never happens or throws below.
    for e in errors:
        e["explanation_parts"] = {"rule": e.get("explanation", ""), "application": None}

    if not errors:
        return errors, 0, 0, None

    try:
        return _run(db, errors, reference, reproduction, l1_code, l2_language_id, taxonomy_cfg)
    except Exception as exc:  # noqa: BLE001 — the Explainer is never allowed to break grading
        logger.warning(
            "dual_translation.explainer: unexpected failure, keeping Rule-only: %s", exc,
        )
        return errors, 0, 0, "explainer error"


def _run(
    db, errors: list[dict], reference: str, reproduction: str,
    l1_code: str, l2_language_id: int, taxonomy_cfg: dict,
) -> tuple[list[dict], int, int, Optional[str]]:
    route = resolve_tier(db, _CHEAP_TIER, l2_language_id)
    if route.slug is None:
        logger.info(
            "dual_translation.explainer: no cheap-tier slug for l2_language_id=%s; Rule-only",
            l2_language_id,
        )
        return errors, 0, 0, "no slug"

    system_prompt = prompts.build_explainer_system_prompt(l1_code)
    numbered = [_numbered_error(e, i, taxonomy_cfg, l1_code) for i, e in enumerate(errors)]
    user_prompt = prompts.build_explainer_user_prompt(l1_code, reference, reproduction, numbered)

    try:
        content, t_in, t_out, _latency = call_model_with_usage(
            route.slug, user_prompt, system_prompt=system_prompt, temperature=0.0,
        )
    except Exception as exc:  # noqa: BLE001 — network/API errors fall back to Rule-only
        logger.warning(
            "dual_translation.explainer: call to %r failed, Rule-only: %s", route.slug, exc,
        )
        return errors, 0, 0, "call failed"

    try:
        payload = json.loads(clean_json_response(content))
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "dual_translation.explainer: response from %r was not valid JSON (%s), Rule-only: %.200r",
            route.slug, exc, content,
        )
        return errors, t_in, t_out, "malformed JSON"

    if not prompts.validate_explainer_response(payload):
        logger.warning(
            "dual_translation.explainer: response from %r failed shape validation, Rule-only: %.200r",
            route.slug, payload,
        )
        return errors, t_in, t_out, "malformed shape"

    applied = _apply_explanations(errors, payload.get("explanations", []))
    logger.info(
        "dual_translation.explainer: applied %d/%d Application layers", applied, len(errors),
    )
    return errors, t_in, t_out, None


def _numbered_error(error: dict, index: int, taxonomy_cfg: dict, l1_code: str) -> dict:
    """The compact per-error shape the §7e user prompt lists: index + forms + the
    L1 subtype gloss + the Rule-template text (which the error already carries)."""
    return {
        "i": index,
        "learner_form": error.get("learner_form", ""),
        "corrected_form": error.get("corrected_form", ""),
        "type": _subtype_gloss(taxonomy_cfg, error.get("subtype"), l1_code),
        "rule": error["explanation_parts"]["rule"],
    }


def _apply_explanations(errors: list[dict], raw_explanations) -> int:
    """Overlay each validated Application onto its error, returning how many were
    applied. An item is dropped (→ Rule-only for that error) when its ``error_index``
    is missing/out of range/duplicated or its text fails validation (§6c)."""
    applied = 0
    seen: set[int] = set()
    for item in raw_explanations or []:
        if not isinstance(item, dict):
            continue
        idx = _index(item.get("error_index"))
        if idx is None or not (0 <= idx < len(errors)) or idx in seen:
            continue
        seen.add(idx)
        error = errors[idx]
        text = _validated_application(
            item.get("text"), error.get("learner_form", ""), error.get("corrected_form", ""),
        )
        if text is None:
            continue
        rule = error["explanation_parts"]["rule"]
        error["explanation_parts"]["application"] = text
        error["explanation"] = f"{rule}\n{text}" if rule else text
        applied += 1
    return applied


def _validated_application(text, learner_form: str, corrected_form: str) -> Optional[str]:
    """Return the trimmed Application text if it passes every §6c check, else None
    (→ Rule-only for that error). Checks: is a non-empty string; ≤
    ``MAX_APPLICATION_CHARS``; a single paragraph (no internal line break); mentions
    ``learner_form`` or ``corrected_form`` with ≥2-char overlap; carries no
    score-like digit pattern."""
    if not isinstance(text, str):
        return None
    trimmed = text.strip()
    if not trimmed:
        return None
    if len(trimmed) > MAX_APPLICATION_CHARS:
        return None
    if "\n" in trimmed or "\r" in trimmed:  # single paragraph
        return None
    if _SCORE_PATTERN.search(trimmed):
        return None
    if not _mentions_form(trimmed, learner_form, corrected_form):
        return None
    return trimmed


def _mentions_form(text: str, learner_form: str, corrected_form: str) -> bool:
    """True iff `text` shares a ≥2-character contiguous run with either form (§6c:
    "mentions learner_form or corrected_form"). The 2-char floor stops a single
    incidental shared character (common in CJK) from passing as a mention.

    Windows that straddle a word boundary (a letter + a space, e.g. "s " from
    "has lived") are ignored — they match almost any prose ("This ...") and would
    wave through a text that names none of the actual words. A form that is itself a
    single character (or otherwise yields no whitespace-free 2-char window) is
    matched whole instead."""
    for form in (learner_form, corrected_form):
        if not form:
            continue
        windows = [form[i:i + 2] for i in range(len(form) - 1)]
        solid = [w for w in windows if not any(ch.isspace() for ch in w)]
        if solid:
            if any(w in text for w in solid):
                return True
        elif form.strip() and form in text:  # 1-char (or all-boundary) form: match whole
            return True
    return False


def _index(value) -> Optional[int]:
    """Coerce an ``error_index`` to int, or None if missing/non-integer. A JSON
    boolean is rejected (``int(True) == 1`` would silently target error #1)."""
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _subtype_gloss(taxonomy_cfg: dict, subtype, l1_code: str) -> str:
    """The subtype's gloss in the learner's L1
    (``subtype_glosses[subtype][l1_code]``), falling back to the bare slug when no
    gloss is seeded — same graceful degradation as
    grader_cascade._resolve_subtype_labels, here for the single subtype in L1."""
    if not subtype:
        return ""
    glosses = (taxonomy_cfg or {}).get("subtype_glosses", {})
    per_subtype = glosses.get(subtype, {}) if isinstance(glosses, dict) else {}
    gloss = per_subtype.get(l1_code) if isinstance(per_subtype, dict) else None
    return gloss or subtype
