"""Grading cascade orchestrator for dual-translation (TASK-606).

The "heart" of Feature 1: turns a Tier-0-unresolved submission into the full §2.2
contract (scores, overall_band, diff, errors[] with eager explanations, grader_trace).
Never persists anything — TASK-607's route handler owns the dt_grade/dt_error_instance
INSERTs; this module is a pure function of (gold, reproduction, config) -> contract dict.

Flow:
  1. services.dual_translation.tier0.grade_tier0 — reused unmodified. If it resolves
     (exact/near-exact), short-circuit straight to the contract; no model call.
  2. Tier 1 (services.dual_translation.router, slug for 'tier1'): grades accuracy+range,
     tags those dimensions' errors. L2-only prompt (services.dual_translation.prompts),
     numerical-index JSON only.
  3. Tier 2 (slug for 'tier2'): grades understandability+fidelity+naturalness — these
     three dimensions are Tier-2-exclusive, so this call always happens once Tier 0 has
     not resolved. If Tier 1's confidence was low or Tier 0's diff was large, Tier 2's
     prompt ALSO re-checks accuracy+range and those values override Tier 1's (the
     "escalate on low confidence / large diff" rule from the cascade doc).
  4. Eager explanation rendering: every decoded error's `explanation` is rendered from
     the active dt_taxonomy_version's per-subtype × per-L1 template table — never model
     prose, per ADR-015.
  5. Fail-open: a tier with no usable slug (router fell all the way to tier0) or a
     response that fails JSON parsing/shape validation contributes nothing; that tier's
     owned dimensions default to MAX_BAND and contribute no errors, rather than hard-
     failing the submission. In the worst case (every tier unusable) the whole
     submission ends up identical to a Tier 0 full-marks grade — a deliberate, generous
     reading of the spec's "fail-open to Tier 0 marks on malformed grader JSON" for the
     total-outage case; see the wiki note for the partial-failure nuance.

`get_active_rubric`/`get_active_taxonomy` and `call_model_with_usage` are imported into
this module's namespace (not called via their owning modules) specifically so tests can
monkeypatch them as boundaries, mirroring services.dual_translation.router's existing
`get_template_config`/`fetch_model_list` pattern.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from services.dimension_service import DimensionService
from services.llm_output_cleaner import clean_json_response
from services.model_arena.llm_runner import call_model_with_usage
from services.dual_translation import prompts
from services.dual_translation.router import resolve_tier, TIER_ORDER
from services.dual_translation.tier0 import MAX_BAND, RUBRIC_DIMENSIONS, grade_tier0

logger = logging.getLogger(__name__)

# A tier's own confidence below this, OR Tier 0's mismatch ratio above
# LARGE_DIFF_RATIO, makes Tier 2 also re-check accuracy/range (the cascade
# doc's "escalate ... when Tier 1 confidence is low or the diff is large").
CONFIDENCE_ESCALATION_THRESHOLD = 0.6
LARGE_DIFF_RATIO = 0.3

_GENERIC_EXPLANATION_TEMPLATE = "corrected: {corrected_form}"


def grade_submission(
    db,
    *,
    passage_id: int,
    gold_l2: str,
    reproduction: str,
    l2_language_id: int,
    l1_language_id: int,
    age_tier: int,
    max_tier: str = "tier2",
) -> dict:
    """Grade one submission end-to-end and return the §2.2 contract dict.

    Args:
        db: Supabase client, threaded through to the rubric/taxonomy/router reads.
        passage_id: dt_passage.id (Tier 0's cache key).
        gold_l2: dt_passage.l2_text (raw, NOT tier0-normalized — spans reported by
            the model are character offsets into this exact string).
        reproduction: dt_submission.reproduction (raw).
        l2_language_id: dim_languages.id of the language being graded.
        l1_language_id: dim_languages.id of the learner's L1 (selects which
            language explanations are rendered in).
        age_tier: 1-6 (ADR-003) — selects rubric band descriptors; naturalness
            visibility at tiers 1-2 is a UI concern (TASK-608), not handled here.
        max_tier: budget-gate hook for TASK-601 — pass 'tier1' to skip Tier 2
            entirely (those dimensions then fail open to MAX_BAND).
    """
    l2_code = DimensionService.get_language_code(l2_language_id)
    if not l2_code:
        raise ValueError(f"No dim_languages row for l2_language_id={l2_language_id}")
    l1_code = DimensionService.get_language_code(l1_language_id)
    if not l1_code:
        raise ValueError(f"No dim_languages row for l1_language_id={l1_language_id}")

    tier0_result = grade_tier0(passage_id, gold_l2, reproduction, l2_code)
    if tier0_result.resolved:
        return {
            "scores": tier0_result.scores,
            "overall_band": tier0_result.overall_band,
            "diff": tier0_result.diff,
            "errors": [],
            "grader_trace": tier0_result.grader_trace,
        }

    rubric_cfg = get_active_rubric(db)
    taxonomy_cfg = get_active_taxonomy(db)
    subtypes = _resolve_subtypes(taxonomy_cfg, l1_code, l2_code)
    subtype_labels = _resolve_subtype_labels(taxonomy_cfg, subtypes, l2_code)

    scores: dict[str, int] = {}
    errors: list[dict] = []
    slugs_trace: list[dict] = []
    tokens_in = tokens_out = 0
    fail_reasons: list[str] = []
    highest_tier = "tier0"

    # ── Tier 1: accuracy + range ────────────────────────────────────────────
    tier1_dims = prompts.TIER_DIMENSIONS["tier1"]
    tier1_confidence = 0.0
    if _tier_allowed("tier1", max_tier):
        route1 = resolve_tier(db, "tier1", l2_language_id)
        slugs_trace.append(route1.as_trace_entry())
        if route1.slug is not None:
            highest_tier = "tier1"
            raw1, t_in, t_out = _call_tier(
                route1.slug, "tier1", l2_code, rubric_cfg, age_tier, subtypes, subtype_labels,
                gold_l2, reproduction,
            )
            tokens_in += t_in
            tokens_out += t_out
            if raw1 is None:
                fail_reasons.append("tier1 malformed JSON")
            else:
                tier1_confidence = _safe_float(raw1.get("confidence"), default=1.0)
                _merge_scores(scores, raw1.get("scores", {}), tier1_dims)
                errors.extend(_decode_errors(raw1.get("errors", []), subtypes, taxonomy_cfg, l1_code))
        else:
            fail_reasons.append("tier1 unavailable")
    for dim in tier1_dims:
        scores.setdefault(dim, MAX_BAND)

    # ── Tier 2: understandability + fidelity + naturalness (always, once here) ─
    tier2_dims = prompts.TIER_DIMENSIONS["tier2"]
    recheck = tier1_confidence < CONFIDENCE_ESCALATION_THRESHOLD or tier0_result.mismatch_ratio > LARGE_DIFF_RATIO
    extra_dims = tier1_dims if recheck else ()
    if _tier_allowed("tier2", max_tier):
        route2 = resolve_tier(db, "tier2", l2_language_id)
        slugs_trace.append(route2.as_trace_entry())
        if route2.slug is not None:
            highest_tier = "tier2"
            raw2, t_in, t_out = _call_tier(
                route2.slug, "tier2", l2_code, rubric_cfg, age_tier, subtypes, subtype_labels,
                gold_l2, reproduction, extra_dims=extra_dims,
            )
            tokens_in += t_in
            tokens_out += t_out
            if raw2 is None:
                fail_reasons.append("tier2 malformed JSON")
            else:
                _merge_scores(scores, raw2.get("scores", {}), tier2_dims + extra_dims)
                errors.extend(_decode_errors(raw2.get("errors", []), subtypes, taxonomy_cfg, l1_code))
        else:
            fail_reasons.append("tier2 unavailable")
    for dim in tier2_dims:
        scores.setdefault(dim, MAX_BAND)

    overall_band = compute_overall_band(scores, rubric_cfg, l2_code)
    fell_open = bool(fail_reasons)

    grader_trace = {
        "tier": highest_tier,
        "deterministic_prefilter": False,
        "cache_hit": False,
        "tokens": {"in": tokens_in, "out": tokens_out},
        "slugs": slugs_trace,
        "fell_open": fell_open,
        "reason": "; ".join(fail_reasons) or None,
    }

    return {
        "scores": scores,
        "overall_band": overall_band,
        "diff": tier0_result.diff,
        "errors": errors,
        "grader_trace": grader_trace,
    }


def compute_overall_band(scores: dict[str, int], rubric_cfg: dict, l2_code: str) -> int:
    """Weighted mean of the 5 dimension scores, per dt_rubric_version.config
    (default weights overridden per-language), rounded to the nearest band
    and clipped to [1,4]. Falls back to an equal-weight mean if rubric_cfg has
    no weights configured yet (TASK-604 content may not exist)."""
    weights_cfg = (rubric_cfg or {}).get("weights", {})
    default_weights = weights_cfg.get("default", {})
    overrides = weights_cfg.get("by_language", {}).get(l2_code, {})

    raw_weights = {
        dim: overrides.get(dim, default_weights.get(dim, 1.0 / len(RUBRIC_DIMENSIONS)))
        for dim in RUBRIC_DIMENSIONS
    }
    total_weight = sum(raw_weights.values()) or 1.0
    weighted_sum = sum(scores.get(dim, MAX_BAND) * (w / total_weight) for dim, w in raw_weights.items())

    band = round(weighted_sum)
    return max(1, min(MAX_BAND, band))


def get_active_rubric(db) -> dict:
    """Load the active dt_rubric_version row's config. No silent fallback —
    an operator must seed + activate a row (TASK-604); mirrors
    services.prompt_service.get_template_config's contract."""
    resp = (
        db.table("dt_rubric_version")
        .select("config")
        .eq("is_active", True)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise RuntimeError("No active dt_rubric_version row. Seed + activate one (TASK-604).")
    return resp.data[0]["config"]


def get_active_taxonomy(db) -> dict:
    """Load the active dt_taxonomy_version row's taxonomy. No silent fallback —
    an operator must seed + activate a row (at minimum a baseline; full
    per-pair localisation is TASK-616)."""
    resp = (
        db.table("dt_taxonomy_version")
        .select("taxonomy")
        .eq("is_active", True)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise RuntimeError("No active dt_taxonomy_version row. Seed + activate one (TASK-604/616).")
    return resp.data[0]["taxonomy"]


def render_explanation(taxonomy_cfg: dict, subtype: str, l1_code: str, learner_form: str, corrected_form: str) -> tuple[str, bool]:
    """Render an error's `explanation` from the (subtype, L1) template table.

    Returns (text, used_fallback). `used_fallback=True` means no template
    exists yet for this (subtype, L1) pair — the spec requires a non-blank
    generic fallback rather than an empty explanation; the caller logs this
    for the authoring queue (never persisted as a field — dt_error_instance
    has no such column).
    """
    templates = (taxonomy_cfg or {}).get("templates", {})
    template = templates.get(subtype, {}).get(l1_code)
    if not template:
        return _GENERIC_EXPLANATION_TEMPLATE.format(corrected_form=corrected_form), True
    try:
        return template.format(learner_form=learner_form, corrected_form=corrected_form), False
    except (KeyError, IndexError):
        logger.warning("dual_translation.grader_cascade: template for subtype=%r l1=%r has bad placeholders", subtype, l1_code)
        return _GENERIC_EXPLANATION_TEMPLATE.format(corrected_form=corrected_form), True


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _tier_allowed(tier: str, max_tier: str) -> bool:
    return TIER_ORDER.index(tier) <= TIER_ORDER.index(max_tier)


def _call_tier(
    slug: str,
    tier: str,
    l2_code: str,
    rubric_cfg: dict,
    age_tier: int,
    subtypes: list[str],
    subtype_labels: list[str],
    gold_l2: str,
    reproduction: str,
    *,
    extra_dims: tuple[str, ...] = (),
) -> tuple[Optional[dict], int, int]:
    """Call one cascade tier and return (parsed_payload_or_None, tokens_in, tokens_out).

    None means fail-open: unparseable JSON, wrong shape, or the call itself
    raised (network/API error) — every failure mode collapses to the same
    "this tier contributed nothing" signal for the caller.
    """
    system_prompt = prompts.build_system_prompt(
        tier, l2_code, rubric_cfg, age_tier, subtypes,
        subtype_labels=subtype_labels, extra_dims=extra_dims,
    )
    user_prompt = prompts.build_user_prompt(l2_code, gold_l2, reproduction)

    try:
        content, tokens_in, tokens_out, _latency = call_model_with_usage(
            slug, user_prompt, system_prompt=system_prompt, temperature=0.0,
        )
    except Exception as exc:
        logger.warning("dual_translation.grader_cascade: %s call to %r failed: %s", tier, slug, exc)
        return None, 0, 0

    try:
        payload = json.loads(clean_json_response(content))
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "dual_translation.grader_cascade: %s response from %r was not valid JSON (%s): %.200r",
            tier, slug, exc, content,
        )
        return None, tokens_in, tokens_out

    if not prompts.validate_raw_response(payload):
        logger.warning("dual_translation.grader_cascade: %s response from %r had the wrong shape: %.200r", tier, slug, payload)
        return None, tokens_in, tokens_out

    return payload, tokens_in, tokens_out


def _merge_scores(scores: dict[str, int], raw_scores: dict, dims: tuple[str, ...]) -> None:
    for dim in dims:
        if dim in raw_scores:
            scores[dim] = _clip_band(raw_scores[dim])


def _clip_band(value) -> int:
    try:
        band = int(round(float(value)))
    except (TypeError, ValueError):
        return MAX_BAND
    return max(1, min(MAX_BAND, band))


def _safe_float(value, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_subtypes(taxonomy_cfg: dict, l1_code: str, l2_code: str) -> list[str]:
    """Resolve the subtype list for this directed pair, falling back to an
    L2-only baseline key if no per-pair table has been seeded yet (TASK-616
    ships real per-pair tables; until then every L1 shares the L2 baseline,
    which also maximizes prompt-cache reuse — see prompts.py module docstring)."""
    pairs = (taxonomy_cfg or {}).get("pairs", {})
    pair_key = f"{l1_code}-{l2_code}"
    if pair_key in pairs:
        return list(pairs[pair_key].get("subtypes", []))
    if l2_code in pairs:
        return list(pairs[l2_code].get("subtypes", []))
    raise RuntimeError(
        f"No dt_taxonomy_version subtype table for pair={pair_key!r} or baseline={l2_code!r}. "
        "Seed at least an L2 baseline (TASK-604/616)."
    )


def _resolve_subtype_labels(taxonomy_cfg: dict, subtypes: list[str], l2_code: str) -> list[str]:
    """What to show the model for each subtype, in l2_code, via
    dt_taxonomy_version.taxonomy['subtype_glosses'][subtype][l2_code].

    Falls back to the bare English subtype slug (and logs once per subtype)
    when no gloss exists yet — keeps the cascade functional pre-TASK-616
    content at the cost of that one subtype line reading as English inside
    an otherwise L2-only ZH/JA prompt; prompts.build_system_prompt's docstring
    carries the same caveat.
    """
    glosses = (taxonomy_cfg or {}).get("subtype_glosses", {})
    labels = []
    for subtype in subtypes:
        gloss = glosses.get(subtype, {}).get(l2_code)
        if not gloss:
            logger.info(
                "dual_translation.grader_cascade: no subtype_glosses entry for subtype=%r l2=%r — "
                "showing the bare English slug in this %r prompt; flagged for authoring (TASK-616)",
                subtype, l2_code, l2_code,
            )
            gloss = subtype
        labels.append(gloss)
    return labels


def _decode_errors(raw_errors: list, subtypes: list[str], taxonomy_cfg: dict, l1_code: str) -> list[dict]:
    decoded = []
    for raw in raw_errors:
        item = _decode_error(raw, subtypes, taxonomy_cfg, l1_code)
        if item is not None:
            decoded.append(item)
    return decoded


def _decode_error(raw: dict, subtypes: list[str], taxonomy_cfg: dict, l1_code: str) -> Optional[dict]:
    """Validate + decode one raw model-reported error into the dt_error_instance
    shape. Returns None (drop, log) on any malformed field — untrusted model
    output must never crash the whole submission over one bad entry."""
    if not prompts.error_has_required_keys(raw):
        logger.warning("dual_translation.grader_cascade: dropping error with missing keys: %r", raw)
        return None

    span_repro = _valid_span(raw.get("span_repro"))
    span_ref = _valid_span(raw.get("span_ref"))
    learner_form = raw.get("learner_form")
    corrected_form = raw.get("corrected_form")
    if span_repro is None or span_ref is None or not learner_form or not corrected_form:
        logger.warning("dual_translation.grader_cascade: dropping error with invalid spans/forms: %r", raw)
        return None

    category = _enum_lookup(prompts.CATEGORY_ENUM, raw.get("category"))
    source = _enum_lookup(prompts.SOURCE_ENUM, raw.get("source"))
    severity = _enum_lookup(prompts.SEVERITY_ENUM, raw.get("severity"))
    subtype = _enum_lookup(subtypes, raw.get("subtype"))
    if category is None or source is None or severity is None or subtype is None:
        logger.warning("dual_translation.grader_cascade: dropping error with out-of-range enum index: %r", raw)
        return None

    explanation, used_fallback = render_explanation(taxonomy_cfg, subtype, l1_code, learner_form, corrected_form)
    if used_fallback:
        logger.info("dual_translation.grader_cascade: no explanation template for subtype=%r l1=%r — flagged for authoring", subtype, l1_code)

    return {
        "span_reproduction": span_repro,
        "span_reference": span_ref,
        "category": category,
        "subtype": subtype,
        "source": source,
        "severity": severity,
        "learner_form": learner_form,
        "corrected_form": corrected_form,
        "explanation": explanation,
        "confidence": _safe_float(raw.get("confidence"), default=0.5),
        "is_mistake": bool(raw.get("is_mistake", False)),
    }


def _valid_span(span) -> Optional[list[int]]:
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        return None
    try:
        start, end = int(span[0]), int(span[1])
    except (TypeError, ValueError):
        return None
    if start < 0 or end < start:
        return None
    return [start, end]


def _enum_lookup(enum_values, index) -> Optional[str]:
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return None
    if 0 <= idx < len(enum_values):
        return enum_values[idx]
    return None
