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
     "escalate on low confidence / large diff" rule from the cascade doc). When the
     large-diff branch fires, the re-check is unconditional and Tier 2's inputs are
     fixed before Tier 1 returns, so the two model calls run concurrently (TASK-643);
     the confidence-gated re-check stays sequential (its inputs depend on Tier 1).
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
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from config import Config
from services.dictation.tokenizer import normalize as _dictation_normalize
from services.dimension_service import DimensionService
from services.llm_output_cleaner import clean_json_response
from services.model_arena.llm_runner import call_model_with_usage
from services.dual_translation import prompts, scoring, explainer
from services.dual_translation.router import resolve_tier, TIER_ORDER
from services.dual_translation.tier0 import MAX_BAND, RUBRIC_DIMENSIONS, grade_tier0, _normalize_l2

logger = logging.getLogger(__name__)

# A tier's own confidence below this, OR Tier 0's mismatch ratio above
# LARGE_DIFF_RATIO, makes Tier 2 also re-check accuracy/range (the cascade
# doc's "escalate ... when Tier 1 confidence is low or the diff is large").
CONFIDENCE_ESCALATION_THRESHOLD = 0.6
LARGE_DIFF_RATIO = 0.3

# Cap on the number of tier-0 non-equal diff opcodes passed to the model as
# candidate regions (TASK-624 §7b): hints, not boundaries — enough to focus
# attention without bloating the (uncached) user suffix on a badly-mangled
# reproduction.
DIFF_REGION_CAP = 20

_GENERIC_EXPLANATION_TEMPLATE = "corrected: {corrected_form}"

# Addition errors span zero width in the reference (TASK-624), so corrected_form
# is legitimately empty and the generic template above would render a dangling
# "corrected: ".
_GENERIC_ADDITION_EXPLANATION_TEMPLATE = "remove: {learner_form}"

# 'rubric' | 'taxonomy' -> the active version row's JSONB. Both only change when
# an operator activates a new version, so they're read once per process rather
# than twice per escalated submission (mirrors router._cfg_cache). Entries are
# handed out by reference; every consumer reads them via .get() and none mutate,
# so nothing is copied on the hot path.
_cfg_cache: dict[str, dict] = {}


def clear_caches() -> None:
    """Test/ops hook: drop the cached rubric/taxonomy so the next load re-reads
    the DB (e.g. after an operator activates a new version). Mirrors
    services.dual_translation.router.clear_caches."""
    _cfg_cache.clear()


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
    framework_v2: Optional[bool] = None,
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
        framework_v2: TASK-628 dispatch override. None (default) reads
            Config.DT_FRAMEWORK_V2; pass True/False to force the v2 Detector/
            Verifier flow or the v1 tier1/tier2 flow explicitly (tests). The v2
            path derives scores in Python and never silent-full-marks on failure.
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

    # TASK-624: the tier-0 diff's non-equal opcodes become candidate regions the
    # model must account for (§7b). Tier 0 already computed the diff; we never
    # re-diff. Empty for a pure-normalization diff (but such a submission would
    # have resolved at Tier 0 and never reached here).
    # TASK-634 (3): the diff tokens are doubly-normalized (dictation-normalize on
    # top of tier0 NFKC/kata2hira), so they often don't occur literally in the raw
    # gold/reproduction — passing them straight through steers the model toward
    # forms it then can't verify against the raw texts. Map each token back to the
    # raw substring it came from before handing it over as a hint.
    regions = _diff_regions(tier0_result.diff, gold_l2, reproduction, l2_code)

    # TASK-628: Evidence-First Grading v2 (Detector/Verifier). Gated by
    # Config.DT_FRAMEWORK_V2 (default OFF); `framework_v2` overrides for tests.
    # Tier 0 short-circuit + the shared rubric/taxonomy/subtype/region context
    # above are identical to v1; only the model-call flow below diverges. The v1
    # tier1/tier2 body stays the shipping path until the flag flips post-harness.
    use_framework_v2 = Config.DT_FRAMEWORK_V2 if framework_v2 is None else framework_v2
    if use_framework_v2:
        return _grade_v2(
            db,
            tier0_result=tier0_result,
            rubric_cfg=rubric_cfg,
            taxonomy_cfg=taxonomy_cfg,
            subtypes=subtypes,
            subtype_labels=subtype_labels,
            regions=regions,
            gold_l2=gold_l2,
            reproduction=reproduction,
            l2_code=l2_code,
            l1_code=l1_code,
            l2_language_id=l2_language_id,
            age_tier=age_tier,
            max_tier=max_tier,
        )

    scores: dict[str, int] = {}
    errors: list[dict] = []
    slugs_trace: list[dict] = []
    tokens_in = tokens_out = 0
    fail_reasons: list[str] = []
    highest_tier = "tier0"

    tier1_dims = prompts.TIER_DIMENSIONS["tier1"]
    tier2_dims = prompts.TIER_DIMENSIONS["tier2"]

    # TASK-643: when the tier-0 diff is large, the Tier-2 re-check is unconditional
    # — `recheck` below is forced True regardless of Tier-1's confidence, so Tier
    # 2's extra_dims (== tier1_dims), and therefore its entire prompt, are fixed
    # before Tier 1 runs. Issue the two multi-second model calls concurrently
    # instead of back-to-back: submit Tier 2 to a request-scoped worker and drive
    # Tier 1 on the main thread. Every other path stays sequential — a confidence-
    # gated re-check's extra_dims depend on tier1_confidence, which only exists
    # once Tier 1 has returned. The integration below is byte-for-byte the same in
    # both paths (trace/token/score/error merge order preserved); only WHERE the
    # Tier-2 call executes differs.
    forced_recheck = tier0_result.mismatch_ratio > LARGE_DIFF_RATIO
    tier1_route = resolve_tier(db, "tier1", l2_language_id) if _tier_allowed("tier1", max_tier) else None
    concurrent_recheck = (
        forced_recheck
        and _tier_allowed("tier2", max_tier)
        and tier1_route is not None
        and tier1_route.slug is not None
    )

    tier2_route = None
    tier2_future = None
    executor = None
    try:
        if concurrent_recheck:
            tier2_route = resolve_tier(db, "tier2", l2_language_id)
            if tier2_route.slug is not None:
                executor = ThreadPoolExecutor(max_workers=1)
                tier2_future = executor.submit(
                    _call_tier,
                    tier2_route.slug, "tier2", l2_code, rubric_cfg, age_tier, subtypes,
                    subtype_labels, gold_l2, reproduction, extra_dims=tier1_dims, regions=regions,
                )

        # ── Tier 1: accuracy + range ────────────────────────────────────────
        tier1_confidence = 0.0
        if tier1_route is not None:
            slugs_trace.append(tier1_route.as_trace_entry())
            if tier1_route.slug is not None:
                highest_tier = "tier1"
                raw1, t_in, t_out, reason1 = _call_tier(
                    tier1_route.slug, "tier1", l2_code, rubric_cfg, age_tier, subtypes, subtype_labels,
                    gold_l2, reproduction, regions=regions,
                )
                tokens_in += t_in
                tokens_out += t_out
                if raw1 is None:
                    fail_reasons.append(f"tier1 {reason1}")
                else:
                    # Missing/invalid confidence escalates the Tier-2 re-check
                    # (default 0.0 < CONFIDENCE_ESCALATION_THRESHOLD) rather than
                    # sailing through as fully-confident — TASK-623 leniency fix.
                    tier1_confidence = _safe_float(raw1.get("confidence"), default=0.0)
                    _merge_scores(scores, raw1.get("scores", {}), tier1_dims)
                    errors.extend(_decode_errors(
                        raw1.get("errors", []), subtypes, taxonomy_cfg, l1_code, reproduction, gold_l2, l2_code,
                    ))
            else:
                fail_reasons.append("tier1 unavailable")
        for dim in tier1_dims:
            scores.setdefault(dim, MAX_BAND)

        # ── Tier 2: understandability + fidelity + naturalness (always, once here) ─
        # `recheck` is exactly `forced_recheck` OR the confidence gate; when a
        # concurrent Tier-2 call was issued, forced_recheck is True, so extra_dims
        # here matches the tier1_dims the future was submitted with.
        recheck = tier1_confidence < CONFIDENCE_ESCALATION_THRESHOLD or forced_recheck
        extra_dims = tier1_dims if recheck else ()
        if _tier_allowed("tier2", max_tier):
            if tier2_route is None:
                tier2_route = resolve_tier(db, "tier2", l2_language_id)
            slugs_trace.append(tier2_route.as_trace_entry())
            if tier2_route.slug is not None:
                highest_tier = "tier2"
                if tier2_future is not None:
                    raw2, t_in, t_out, reason2 = tier2_future.result()
                else:
                    raw2, t_in, t_out, reason2 = _call_tier(
                        tier2_route.slug, "tier2", l2_code, rubric_cfg, age_tier, subtypes, subtype_labels,
                        gold_l2, reproduction, extra_dims=extra_dims, regions=regions,
                    )
                tokens_in += t_in
                tokens_out += t_out
                if raw2 is None:
                    fail_reasons.append(f"tier2 {reason2}")
                else:
                    _merge_scores(scores, raw2.get("scores", {}), tier2_dims + extra_dims)
                    errors.extend(_decode_errors(
                        raw2.get("errors", []), subtypes, taxonomy_cfg, l1_code, reproduction, gold_l2, l2_code,
                    ))
            else:
                fail_reasons.append("tier2 unavailable")
        for dim in tier2_dims:
            scores.setdefault(dim, MAX_BAND)
    finally:
        if executor is not None:
            executor.shutdown(wait=False)

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
    services.prompt_service.get_template_config's contract.

    Cached process-wide after the first successful read; call `clear_caches()`
    to pick up a newly activated version."""
    if "rubric" not in _cfg_cache:
        _cfg_cache["rubric"] = _fetch_active_config(
            db,
            table="dt_rubric_version",
            column="config",
            missing_msg="No active dt_rubric_version row. Seed + activate one (TASK-604).",
        )
    return _cfg_cache["rubric"]


def get_active_taxonomy(db) -> dict:
    """Load the active dt_taxonomy_version row's taxonomy. No silent fallback —
    an operator must seed + activate a row (at minimum a baseline; full
    per-pair localisation is TASK-616).

    Cached process-wide after the first successful read; call `clear_caches()`
    to pick up a newly activated version."""
    if "taxonomy" not in _cfg_cache:
        _cfg_cache["taxonomy"] = _fetch_active_config(
            db,
            table="dt_taxonomy_version",
            column="taxonomy",
            missing_msg="No active dt_taxonomy_version row. Seed + activate one (TASK-604/616).",
        )
    return _cfg_cache["taxonomy"]


def _fetch_active_config(db, *, table: str, column: str, missing_msg: str) -> dict:
    """Read the highest-version active row's JSONB from `table`. Raising rather
    than caching a miss keeps a transient outage from pinning a bad read for the
    life of the process."""
    resp = (
        db.table(table)
        .select(column)
        .eq("is_active", True)
        .order("version", desc=True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise RuntimeError(missing_msg)
    return resp.data[0][column]


def render_explanation(taxonomy_cfg: dict, subtype: str, l1_code: str, learner_form: str, corrected_form: str) -> tuple[str, bool]:
    """Render an error's `explanation` from the (subtype, L1) template table.

    Returns (text, used_fallback). `used_fallback=True` means no template
    exists yet for this (subtype, L1) pair — the spec requires a non-blank
    generic fallback rather than an empty explanation; the caller logs this
    for the authoring queue (never persisted as a field — dt_error_instance
    has no such column).
    """
    def _generic() -> str:
        if not corrected_form:
            return _GENERIC_ADDITION_EXPLANATION_TEMPLATE.format(learner_form=learner_form)
        return _GENERIC_EXPLANATION_TEMPLATE.format(corrected_form=corrected_form)

    templates = (taxonomy_cfg or {}).get("templates", {})
    template = templates.get(subtype, {}).get(l1_code)
    if not template:
        return _generic(), True
    try:
        rendered = template.format(learner_form=learner_form, corrected_form=corrected_form)
    except (KeyError, IndexError):
        logger.warning("dual_translation.grader_cascade: template for subtype=%r l1=%r has bad placeholders", subtype, l1_code)
        return _generic(), True
    if not corrected_form and "{corrected_form}" in template:
        # Template quotes a correction the model never produced; fall back rather
        # than show the learner an empty quotation.
        return _generic(), True
    return rendered, False


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
    regions: list[dict] | None = None,
) -> tuple[Optional[dict], int, int, Optional[str]]:
    """Call one cascade tier and return
    (parsed_payload_or_None, tokens_in, tokens_out, fail_reason).

    A None payload means fail-open: unparseable JSON, wrong shape, scores that
    don't cover the dimensions this tier asked for (TASK-635), or the call
    itself raising (network/API error) — every failure mode collapses to the
    same "this tier contributed nothing" signal for the caller. `fail_reason` is
    None on success, else the phrase the caller puts in grader_trace.reason.
    """
    system_prompt = prompts.build_system_prompt(
        tier, l2_code, rubric_cfg, age_tier, subtypes,
        subtype_labels=subtype_labels, extra_dims=extra_dims,
    )
    user_prompt = prompts.build_user_prompt(l2_code, gold_l2, reproduction, regions=regions)

    try:
        content, tokens_in, tokens_out, _latency = call_model_with_usage(
            slug, user_prompt, system_prompt=system_prompt, temperature=0.0,
        )
    except Exception as exc:
        logger.warning("dual_translation.grader_cascade: %s call to %r failed: %s", tier, slug, exc)
        return None, 0, 0, "call failed"

    try:
        payload = json.loads(clean_json_response(content))
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "dual_translation.grader_cascade: %s response from %r was not valid JSON (%s): %.200r",
            tier, slug, exc, content,
        )
        return None, tokens_in, tokens_out, "malformed JSON"

    # Hold the response to exactly the dimensions this tier's prompt asked for:
    # a well-formed payload that simply omits them is still unusable, because
    # every absent dimension would default to MAX_BAND below (TASK-635).
    asked = prompts.asked_dimensions(tier, extra_dims)
    if not prompts.validate_raw_response(payload, required_dims=asked):
        missing = prompts.missing_score_dims(payload, asked)
        reason = f"incomplete scores: {', '.join(missing)}" if missing else "malformed JSON"
        logger.warning(
            "dual_translation.grader_cascade: %s response from %r failed validation (%s): %.200r",
            tier, slug, reason, payload,
        )
        return None, tokens_in, tokens_out, reason

    return payload, tokens_in, tokens_out, None


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


def _diff_regions(
    diff: list,
    gold_l2: str = "",
    reproduction: str = "",
    language_code: str = "",
) -> list[dict]:
    """Turn the tier-0 WordDiff opcode list into candidate regions for the model
    (TASK-624 §7b): every non-'equal' opcode as ``{"op","ref","repro"}`` (the
    reference-side and learner-side token text), capped at ``DIFF_REGION_CAP``.

    Kept deliberately text-shaped, not character-offset-shaped: the tier-0 diff
    is token-level (services.dictation.grader), so its exact character spans are
    not available here — but the differing token text is a faithful, usable hint
    that the model then locates against the full REFERENCE/LEARNER texts it also
    receives. Regions are hints, not boundaries (the accounted-for rule).

    TASK-634 (3): the tier-0 diff was computed on doubly-normalized text
    (dictation-normalize on top of tier0 _normalize_l2 — lower/diacritic/punct
    stripping plus NFKC/kata2hira), so a raw token such as "The dog." surfaces in
    the diff as "the" / "dog". Feeding those normalized tokens straight to the
    model as region hints steers it toward forms that don't occur literally in the
    raw REFERENCE/LEARNER text it must quote back (the §7a span-discipline rule),
    which is exactly what drops the error at decode time. So each token is mapped
    back to the raw substring it was normalized from, per side, in order (a cursor
    keeps repeated tokens matching successive occurrences). A token that can't be
    relocated (empty, or absent when no raw text is supplied) degrades to the
    normalized token itself — unchanged from the pre-TASK-634 behaviour."""
    ref_lookup = _RawTokenLocator(gold_l2, language_code)
    repro_lookup = _RawTokenLocator(reproduction, language_code)
    regions: list[dict] = []
    for entry in diff or []:
        if not isinstance(entry, dict) or entry.get("op") == "equal":
            continue
        regions.append({
            "op": entry.get("op"),
            "ref": ref_lookup.locate(entry.get("correct") or ""),
            "repro": repro_lookup.locate(entry.get("user") or ""),
        })
        if len(regions) >= DIFF_REGION_CAP:
            break
    return regions


class _RawTokenLocator:
    """Maps fully-normalized diff tokens back to raw substrings of one text side
    (TASK-634 (3)).

    Folds the raw text once, char-by-char, through the same pipeline that produced
    the diff tokens (``_char_fold_diff`` = tier0 width/kana + dictation normalize),
    recording a folded→raw character index map. A diff token — already in that
    folded form — is then found as a substring of the folded text and its span
    mapped back to the raw string, yielding a substring that genuinely occurs in
    the raw text. A per-instance cursor advances past each match so a token that
    repeats in the diff resolves to successive raw occurrences rather than always
    the first."""

    def __init__(self, text: str, language_code: str):
        self._text = text or ""
        self._language_code = language_code
        self._folded, self._index_map = _fold_map(
            self._text, lambda ch: _char_fold_diff(ch, language_code)
        )
        self._cursor = 0

    def locate(self, token: str) -> str:
        if not token or not self._folded:
            return token
        pos = self._folded.find(token, self._cursor)
        if pos == -1:
            # Fall back to a from-the-top scan: the diff's opcode order is a good
            # heuristic for the cursor but not a guarantee (merged/reordered
            # regions), so a monotonic miss shouldn't strand the token.
            pos = self._folded.find(token)
            if pos == -1:
                return token
        end = pos + len(token)
        raw_start = self._index_map[pos]
        raw_end = self._index_map[end - 1] + 1
        self._cursor = end
        return self._text[raw_start:raw_end]


def _decode_errors(
    raw_errors: list,
    subtypes: list[str],
    taxonomy_cfg: dict,
    l1_code: str,
    reproduction: str,
    reference: str,
    l2_code: str = "",
) -> list[dict]:
    decoded = []
    for raw in raw_errors:
        item = _decode_error(raw, subtypes, taxonomy_cfg, l1_code, reproduction, reference, l2_code)
        if item is not None:
            decoded.append(item)
    return decoded


def _decode_error(
    raw: dict,
    subtypes: list[str],
    taxonomy_cfg: dict,
    l1_code: str,
    reproduction: str,
    reference: str,
    l2_code: str = "",
) -> Optional[dict]:
    """Validate + decode one raw model-reported error into the dt_error_instance
    shape. Returns None (drop, log) on any malformed field — untrusted model
    output must never crash the whole submission over one bad entry.

    TASK-624 substring repair: a model whose ``learner_form``/``span_repro`` (or
    ``corrected_form``/``span_ref``) disagree is reconciled by locating the form
    in the text before dropping — an off-by-one span is repaired, not discarded
    (the baseline lost a real error this way). An omission/addition point (empty
    form at a valid zero-width span) is also kept, not dropped."""
    if not prompts.error_has_required_keys(raw):
        logger.warning("dual_translation.grader_cascade: dropping error with missing keys: %r", raw)
        return None

    span_repro, learner_form = _reconcile_span_form(reproduction, raw.get("span_repro"), raw.get("learner_form"), l2_code)
    span_ref, corrected_form = _reconcile_span_form(reference, raw.get("span_ref"), raw.get("corrected_form"), l2_code)
    if span_repro is None or span_ref is None or (not learner_form and not corrected_form):
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


def _reconcile_span_form(text: str, span, form, language_code: str = "") -> tuple[Optional[list[int]], str]:
    """Reconcile one (span, form) pair against its text (TASK-624 / TASK-634).

    Returns (span, form) with the span corrected to where `form` actually sits in
    `text`, or (None, form) if the pair is unrepairable (drop). Rules:
      * form present and the span already matches it (in bounds) → keep as-is.
      * form present but span wrong/out of bounds → relocate to the occurrence of
        `form` whose start is NEAREST the model's original span start, not the
        first occurrence (TASK-634 (1): on a repeated token an off-by-one span
        must not teleport the highlight to a different, correct occurrence).
      * form present but no exact occurrence → normalization-aware fallback
        (TASK-634 (2)): fold both `text` and `form` through _normalize_l2 (NFKC +
        kata2hira for JA) + casefold and search the folded text; a full/half-width,
        kana, or case mismatch resolves here instead of silently dropping a real
        error (the ADR-019 evidence-first invariant). The span maps back to raw
        offsets and `form` becomes the raw substring (span↔form must stay exact).
      * form present but absent even under folding → unrepairable (None).
      * form empty (an omission/addition point) → keep iff the span is a valid,
        in-bounds offset pair (including zero-width); the empty form is legitimate.
    """
    text = text or ""
    n = len(text)
    form = form if isinstance(form, str) else ("" if form is None else str(form))
    valid = _valid_span(span)
    anchor = _span_start(span)

    if form:
        if valid is not None and valid[1] <= n and text[valid[0]:valid[1]] == form:
            return valid, form
        idx = _nearest_occurrence(text, form, anchor)
        if idx != -1:
            return [idx, idx + len(form)], form
        folded_span = _folded_locate(text, form, language_code, anchor)
        if folded_span is not None:
            raw_start, raw_end = folded_span
            return [raw_start, raw_end], text[raw_start:raw_end]
        return None, form

    if valid is not None and valid[1] <= n:
        return valid, ""
    return None, ""


def _span_start(span) -> Optional[int]:
    """The model's reported start offset, used as the relocation anchor. Tolerant
    of an otherwise-malformed span (only span[0] needs to be a non-negative int) so
    a span that's wrong in its END can still anchor to the intended occurrence."""
    if not isinstance(span, (list, tuple)) or not span:
        return None
    try:
        start = int(span[0])
    except (TypeError, ValueError):
        return None
    return start if start >= 0 else None


def _nearest_occurrence(text: str, form: str, anchor: Optional[int]) -> int:
    """Index of the occurrence of `form` in `text` whose start is closest to
    `anchor` (ties → earliest), or -1 if `form` never occurs. With no anchor,
    the first occurrence (matching the pre-TASK-634 text.find behaviour)."""
    starts = []
    pos = text.find(form)
    while pos != -1:
        starts.append(pos)
        pos = text.find(form, pos + 1)
    if not starts:
        return -1
    if anchor is None:
        return starts[0]
    return min(starts, key=lambda i: (abs(i - anchor), i))


def _folded_locate(text: str, form: str, language_code: str, anchor: Optional[int]) -> Optional[tuple[int, int]]:
    """Normalization-aware search (TASK-634 (2)): find `form` in `text` under an
    NFKC + kata2hira(JA) + casefold folding and return the raw [start, end) span of
    the occurrence nearest `anchor`, or None if absent even folded.

    Both `text` and `form` are folded char-by-char; the fold can change string
    length (NFKC), so a folded→raw index map carries each folded position back to
    the raw offset it originated from."""
    char_fold = lambda ch: _char_fold_l2(ch, language_code)
    folded, index_map = _fold_map(text, char_fold)
    folded_form = "".join(char_fold(ch) for ch in form)
    if not folded_form or not folded:
        return None

    starts = []
    pos = folded.find(folded_form)
    while pos != -1:
        starts.append(pos)
        pos = folded.find(folded_form, pos + 1)
    if not starts:
        return None

    if anchor is None:
        chosen = starts[0]
    else:
        chosen = min(starts, key=lambda p: (abs(index_map[p] - anchor), index_map[p]))
    raw_start = index_map[chosen]
    raw_end = index_map[chosen + len(folded_form) - 1] + 1
    return raw_start, raw_end


def _fold_map(text: str, char_fold) -> tuple[str, list[int]]:
    """Fold `text` one character at a time via `char_fold` (str -> str, possibly
    empty or multi-char), returning the folded string and a parallel index map
    where ``index_map[i]`` is the raw offset of ``folded[i]``. Per-character folding
    is what makes the map possible: a whole-string normalize would lose the
    per-position correspondence NFKC's length changes require."""
    folded_parts: list[str] = []
    index_map: list[int] = []
    for raw_idx, ch in enumerate(text):
        for folded_ch in char_fold(ch):
            folded_parts.append(folded_ch)
            index_map.append(raw_idx)
    return "".join(folded_parts), index_map


def _char_fold_l2(ch: str, language_code: str) -> str:
    """Width/kana/case fold for one character (TASK-634 (2)): the same tier0
    _normalize_l2 (NFKC + kata2hira for JA) the deterministic pre-pass uses, plus
    casefold so a capitalised EN echo matches its lower-case source. Deliberately
    does NOT strip punctuation/diacritics — that heavier fold is only for the
    diff-token relocation (_char_fold_diff), not for verifying model-reported
    forms, which should stay punctuation-faithful."""
    return _normalize_l2(ch, language_code).casefold()


def _char_fold_diff(ch: str, language_code: str) -> str:
    """Full fold for one character (TASK-634 (3)): tier0 _normalize_l2 followed by
    the dictation normalize (lower/diacritic/punct strip) — the exact pipeline that
    produced the tier-0 diff tokens, so a raw char folds to the same form those
    tokens carry and a token can be located back in the raw text."""
    return _dictation_normalize(_normalize_l2(ch, language_code))


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


# ===========================================================================
# TASK-628 — Evidence-First Grading v2 (Detector / Verifier cascade).
#
# Dispatched from grade_submission when Config.DT_FRAMEWORK_V2 is on and Tier 0
# did not resolve. Flow (tech spec §2):
#   DETECTOR (tier1 slug) — errors[] + highlights[], NO scores.
#   VERIFIER (tier2 slug) — verdicts (confirm/reject/adjust) on the proposed
#                           errors + added_errors + naturalness/range judgments
#                           with mandatory evidence spans.
#   MERGE (Python)        — confirmed + adjusted + added.
#   DERIVED SCORING       — services.dual_translation.scoring (TASK-627): the
#                           accuracy/fidelity/understandability bands come from
#                           severity-weighted penalties, naturalness/range from
#                           the judgments; overall is the renormalized weighted mean.
#
# Failure modes never silent-full-mark (the v1 leniency this whole framework
# replaces):
#   * Detector fails → Verifier still runs (empty proposed list = a full detection
#     pass) → provisional=True.
#   * Verifier fails → Detector's errors are used unverified; naturalness/range
#     have no judgment and drop out of the (renormalized) mean → provisional=True.
#   * Both fail → no scores (overall_band=None); the route persists nothing so the
#     learner's retry re-grades (a grade with no evidence would poison the cache —
#     TASK-633/ADR-019).
# ===========================================================================

# Arbiter escalation trigger (tech spec §2), config-gated by
# Config.DT_TIER3_ARBITER_ENABLED (default OFF). The Verifier rejecting at least
# this fraction of the proposed errors, OR reporting confidence below this floor,
# escalates to a Tier-3 arbiter re-adjudication. Replaces the v1 escalation
# constants (CONFIDENCE_ESCALATION_THRESHOLD / LARGE_DIFF_RATIO), which have no
# meaning in the two-role flow.
ARBITER_REJECT_RATE = 0.5
ARBITER_CONFIDENCE_FLOOR = 0.5

# Cap on positive-evidence highlights returned to the client (tech spec §6a).
HIGHLIGHT_CAP = 3


def _grade_v2(
    db,
    *,
    tier0_result,
    rubric_cfg: dict,
    taxonomy_cfg: dict,
    subtypes: list[str],
    subtype_labels: list[str],
    regions: list[dict],
    gold_l2: str,
    reproduction: str,
    l2_code: str,
    l1_code: str,
    l2_language_id: int,
    age_tier: int,
    max_tier: str,
) -> dict:
    """The v2 Detector/Verifier grading flow (TASK-628). Pure w.r.t. persistence —
    returns the contract dict; the route decides whether to persist it."""
    diff = tier0_result.diff
    slugs_trace: list[dict] = []
    fail_reasons: list[str] = []
    tokens_in = tokens_out = 0
    highest_tier = "tier0"

    # ── DETECTOR (tier1 slug): errors + highlights, no scores ───────────
    detector_errors: list[dict] = []
    highlights: list[dict] = []
    detector_ok = False
    det_sys = prompts.build_detector_system_prompt(
        l2_code, rubric_cfg, subtypes, subtype_labels=subtype_labels,
    )
    det_usr = prompts.build_user_prompt(l2_code, gold_l2, reproduction, regions=regions)
    payload, t_in, t_out, reason, tier = _run_role(
        db, "tier1", "detector", l2_language_id, max_tier, det_sys, det_usr,
        slugs_trace, prompts.validate_detector_response,
    )
    tokens_in += t_in
    tokens_out += t_out
    if tier is not None:
        highest_tier = tier
    if reason is not None:
        fail_reasons.append(reason)
    if payload is not None:
        detector_ok = True
        detector_errors = _decode_errors(
            payload.get("errors", []), subtypes, taxonomy_cfg, l1_code,
            reproduction, gold_l2, l2_code,
        )
        highlights = _decode_highlights(payload.get("highlights", []), reproduction)

    proposed = [_proposed_entry(e, i, subtypes) for i, e in enumerate(detector_errors)]

    # ── VERIFIER (tier2 slug): verdicts + added_errors + judgments ──────
    verifier_ok = False
    verifier_payload: Optional[dict] = None
    verifier_confidence = 0.0
    ver_sys = prompts.build_verifier_system_prompt(
        l2_code, rubric_cfg, age_tier, subtypes, subtype_labels=subtype_labels,
    )
    ver_usr = prompts.build_verifier_user_prompt(l2_code, gold_l2, reproduction, proposed)
    payload, t_in, t_out, reason, tier = _run_role(
        db, "tier2", "verifier", l2_language_id, max_tier, ver_sys, ver_usr,
        slugs_trace, prompts.validate_verifier_response,
    )
    tokens_in += t_in
    tokens_out += t_out
    if tier is not None:
        highest_tier = tier
    if reason is not None:
        fail_reasons.append(reason)
    if payload is not None:
        verifier_ok = True
        verifier_payload = payload
        verifier_confidence = _safe_float(payload.get("confidence"), default=0.0)

    # ── MERGE ───────────────────────────────────────────────────────────
    rejected_count = 0
    judgments: dict = {}
    if verifier_ok:
        kept, added, rejected_count = _apply_verdicts(
            detector_errors,
            verifier_payload.get("verdicts", []),
            verifier_payload.get("added_errors", []),
            subtypes, taxonomy_cfg, l1_code, reproduction, gold_l2, l2_code,
        )
        judgments = verifier_payload.get("judgments", {})
    else:
        # Verifier failed → detector errors are shown unverified (no verdicts).
        kept, added = list(detector_errors), []

    final_errors = kept + added

    # ── ARBITER (tier3, config-gated, default OFF) ──────────────────────
    arbiter_trace = None
    if verifier_ok and Config.DT_TIER3_ARBITER_ENABLED:
        (final_errors, rejected_count, judgments, arb_tier,
         t_in, t_out, arbiter_trace) = _maybe_arbitrate(
            db,
            detector_errors=detector_errors,
            proposed=proposed,
            verifier_confidence=verifier_confidence,
            rejected_count=rejected_count,
            kept=kept,
            added=added,
            judgments=judgments,
            subtypes=subtypes,
            subtype_labels=subtype_labels,
            taxonomy_cfg=taxonomy_cfg,
            rubric_cfg=rubric_cfg,
            l1_code=l1_code,
            l2_code=l2_code,
            l2_language_id=l2_language_id,
            gold_l2=gold_l2,
            reproduction=reproduction,
            age_tier=age_tier,
            slugs_trace=slugs_trace,
        )
        tokens_in += t_in
        tokens_out += t_out
        if arb_tier is not None:
            highest_tier = arb_tier

    provisional = not (detector_ok and verifier_ok)

    # ── EXPLAINER (cheap slug, L1 prose; error-bearing submissions only) ─
    # TASK-630 §6c/§7e: one batched L1 call adds a per-error instance-specific
    # Application layer atop the Rule template, and attaches explanation_parts
    # {rule, application|null} to every error. Fail-silent by contract — it never
    # blocks, delays past its own call, or flips the grade provisional; on any
    # failure each error keeps its Rule-only explanation. Skipped when there are no
    # final errors (nothing to explain), which includes the both-tiers-failed
    # no-scores case (final_errors is empty there). Its tokens are still counted.
    if final_errors:
        final_errors, exp_in, exp_out, _exp_reason = explainer.attach_explanations(
            db,
            errors=final_errors,
            reference=gold_l2,
            reproduction=reproduction,
            l1_code=l1_code,
            l2_language_id=l2_language_id,
            taxonomy_cfg=taxonomy_cfg,
        )
        tokens_in += exp_in
        tokens_out += exp_out

    # ── DERIVED SCORING ─────────────────────────────────────────────────
    subtype_meta = (taxonomy_cfg or {}).get("subtype_meta", {})
    if detector_ok or verifier_ok:
        bands = dict(scoring.compute_dimension_bands(final_errors, subtype_meta, rubric_cfg))
        present_dims = list(scoring.DERIVED_DIMENSIONS)
        if verifier_ok:
            for dim in prompts.JUDGE_DIMENSIONS:
                band = _judgment_band(judgments, dim, reproduction)
                if band is not None:
                    bands[dim] = band
                    present_dims.append(dim)
        weights = scoring.resolve_weights(rubric_cfg, l2_code)
        overall_band = scoring.compute_overall(bands, weights, present_dims)
        scores_out = {dim: bands[dim] for dim in present_dims}
    else:
        # Both tiers failed → NO scores. Never a silent full-marks default; the
        # route declines to persist (overall_band is None) and invites a retry.
        scores_out = {}
        overall_band = None
        highlights = []

    grader_trace = {
        "tier": highest_tier,
        "deterministic_prefilter": False,
        "cache_hit": False,
        "tokens": {"in": tokens_in, "out": tokens_out},
        "slugs": slugs_trace,
        "framework_version": 2,
        "provisional": provisional,
        "rejected_count": rejected_count,
        "prompt_version": {
            "rubric": get_active_rubric_version(db),
            "taxonomy": get_active_taxonomy_version(db),
        },
        "fell_open": provisional,
        "reason": "; ".join(fail_reasons) or None,
    }
    if arbiter_trace is not None:
        grader_trace["arbiter"] = arbiter_trace

    return {
        "scores": scores_out,
        "overall_band": overall_band,
        "diff": diff,
        "errors": final_errors,
        "highlights": highlights,
        "grader_trace": grader_trace,
        "provisional": provisional,
    }


def get_active_rubric_version(db) -> Optional[int]:
    """The active dt_rubric_version.version, for grader_trace.prompt_version
    (TASK-628). Cached like the config reads; None if unavailable — a missing
    version number is non-critical trace metadata, never a grading blocker."""
    if "rubric_version" not in _cfg_cache:
        _cfg_cache["rubric_version"] = _fetch_active_scalar(db, table="dt_rubric_version", column="version")
    return _cfg_cache["rubric_version"]


def get_active_taxonomy_version(db) -> Optional[int]:
    """The active dt_taxonomy_version.version, for grader_trace.prompt_version."""
    if "taxonomy_version" not in _cfg_cache:
        _cfg_cache["taxonomy_version"] = _fetch_active_scalar(db, table="dt_taxonomy_version", column="version")
    return _cfg_cache["taxonomy_version"]


def _fetch_active_scalar(db, *, table: str, column: str):
    """Read one scalar column off the highest-version active row of `table`.
    Unlike `_fetch_active_config` this never raises — the version is metadata, so
    a read failure degrades to None rather than blocking a submission."""
    try:
        resp = (
            db.table(table)
            .select(column)
            .eq("is_active", True)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 — non-critical trace metadata
        logger.warning("dual_translation.grader_cascade: could not read %s.%s: %s", table, column, exc)
        return None
    if not resp.data:
        return None
    return resp.data[0].get(column)


def _run_role(
    db, tier: str, role: str, l2_language_id: int, max_tier: str,
    system_prompt: str, user_prompt: str, slugs_trace: list[dict], validator,
) -> tuple[Optional[dict], int, int, Optional[str], Optional[str]]:
    """Resolve `tier`'s slug, call the model with the given prompts, and return
    (payload_or_None, tokens_in, tokens_out, fail_reason, attempted_tier).

    attempted_tier is the tier name when a slug was actually called (so the caller
    can advance grader_trace.tier), else None. fail_reason is None on success, else
    a `"{role} …"` phrase for grader_trace.reason. A tier that is budget-gated out
    or has no usable slug reports `"{role} unavailable"` and no attempted_tier."""
    if not _tier_allowed(tier, max_tier):
        return None, 0, 0, f"{role} unavailable", None
    route = resolve_tier(db, tier, l2_language_id)
    slugs_trace.append(route.as_trace_entry())
    if route.slug is None:
        return None, 0, 0, f"{role} unavailable", None
    payload, t_in, t_out, reason = _invoke_model(route.slug, role, system_prompt, user_prompt, validator)
    fail_reason = f"{role} {reason}" if reason else None
    return payload, t_in, t_out, fail_reason, tier


def _invoke_model(
    slug: str, role: str, system_prompt: str, user_prompt: str, validator,
) -> tuple[Optional[dict], int, int, Optional[str]]:
    """Call one v2 model role and return (payload_or_None, t_in, t_out, reason).

    None payload = fail-open for this role: the call raised, the response was not
    JSON, or it failed the role's shape validator. Every failure collapses to the
    same "this role contributed nothing" signal, which flags the grade provisional
    upstream (never a silent full-marks default — the whole point of v2)."""
    try:
        content, t_in, t_out, _latency = call_model_with_usage(
            slug, user_prompt, system_prompt=system_prompt, temperature=0.0,
        )
    except Exception as exc:  # noqa: BLE001 — network/API errors fail the role open
        logger.warning("dual_translation.grader_cascade: %s call to %r failed: %s", role, slug, exc)
        return None, 0, 0, "call failed"

    try:
        payload = json.loads(clean_json_response(content))
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning(
            "dual_translation.grader_cascade: %s response from %r was not valid JSON (%s): %.200r",
            role, slug, exc, content,
        )
        return None, t_in, t_out, "malformed JSON"

    if not validator(payload):
        logger.warning(
            "dual_translation.grader_cascade: %s response from %r failed shape validation: %.200r",
            role, slug, payload,
        )
        return None, t_in, t_out, "malformed shape"

    return payload, t_in, t_out, None


def _proposed_entry(decoded: dict, index: int, subtypes: list[str]) -> dict:
    """Map a decoded detector error (slug form, reconciled spans) back to the
    compact numbered index-form the Verifier reads (§7d)."""
    return {
        "i": index,
        "span_repro": decoded["span_reproduction"],
        "span_ref": decoded["span_reference"],
        "category": _enum_index(prompts.CATEGORY_ENUM, decoded["category"]),
        "source": _enum_index(prompts.SOURCE_ENUM, decoded["source"]),
        "severity": _enum_index(prompts.SEVERITY_ENUM, decoded["severity"]),
        "subtype": _enum_index(subtypes, decoded["subtype"]),
        "learner_form": decoded["learner_form"],
        "corrected_form": decoded["corrected_form"],
    }


def _enum_index(enum_values, slug) -> int:
    """Inverse of _enum_lookup for a slug known to be present (decoded errors are
    already validated). -1 for the impossible miss rather than raising."""
    try:
        return list(enum_values).index(slug)
    except ValueError:
        return -1


def _decode_highlights(raw_highlights, reproduction: str, cap: int = HIGHLIGHT_CAP) -> list[dict]:
    """Validate + cap the detector's positive-evidence highlights (§6a: ≤3
    enforced in code). Each item is ``{span_repro:[a,b], reason:index}``; drop any
    whose span is malformed / out of bounds or whose reason index is out of range."""
    out: list[dict] = []
    n = len(reproduction or "")
    for h in raw_highlights or []:
        if not isinstance(h, dict):
            continue
        span = _valid_span(h.get("span_repro"))
        reason = _enum_lookup(prompts.HIGHLIGHT_REASON_ENUM, h.get("reason"))
        if span is None or span[1] > n or reason is None:
            continue
        out.append({"span_reproduction": span, "reason": reason})
        if len(out) >= cap:
            break
    return out


def _apply_verdicts(
    detector_errors: list[dict], raw_verdicts, raw_added,
    subtypes: list[str], taxonomy_cfg: dict, l1_code: str,
    reproduction: str, reference: str, l2_code: str,
) -> tuple[list[dict], list[dict], int]:
    """Merge the Verifier's verdicts into the detector's proposed errors and decode
    its added_errors. Returns (kept_errors, added_errors, rejected_count).

    Verdict rules (§6b):
      * a verdict for an unknown/out-of-range error_index is dropped;
      * duplicate verdicts for one index → the first wins;
      * a proposed error with NO verdict defaults to CONFIRM (the detector already
        passed validation — fail-safe toward showing the error);
      * reject (1) drops the error and increments rejected_count (logged, never
        persisted or shown);
      * adjust (2) patches severity/subtype/spans and re-renders the explanation.
    """
    verdict_by_index: dict[int, dict] = {}
    for v in raw_verdicts or []:
        if not isinstance(v, dict):
            continue
        try:
            idx = int(v.get("error_index"))
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(detector_errors):
            verdict_by_index.setdefault(idx, v)  # first verdict wins

    kept: list[dict] = []
    rejected_count = 0
    for i, error in enumerate(detector_errors):
        code = _verdict_code(verdict_by_index.get(i))
        if code == 1:  # reject
            rejected_count += 1
            logger.info(
                "dual_translation.grader_cascade: verifier rejected detector error #%d (%s): %r",
                i, error.get("subtype"), error.get("learner_form"),
            )
            continue
        if code == 2:  # adjust
            error = _apply_verdict_adjustment(
                error, verdict_by_index[i], subtypes, taxonomy_cfg, l1_code, reproduction, reference, l2_code,
            )
        kept.append(error)

    added = _decode_errors(raw_added, subtypes, taxonomy_cfg, l1_code, reproduction, reference, l2_code)
    return kept, added, rejected_count


def _verdict_code(verdict) -> int:
    """The verdict integer (0 confirm / 1 reject / 2 adjust). A missing or
    malformed verdict fail-safes to 0 (confirm) — never silently drop a validated
    detector error on a garbled verdict."""
    if not isinstance(verdict, dict):
        return 0
    try:
        code = int(verdict.get("verdict"))
    except (TypeError, ValueError):
        return 0
    return code if code in (0, 1, 2) else 0


def _apply_verdict_adjustment(
    error: dict, verdict: dict, subtypes: list[str], taxonomy_cfg: dict, l1_code: str,
    reproduction: str, reference: str, l2_code: str,
) -> dict:
    """Apply an `adjust` verdict's optional corrected fields to a decoded error
    (§6b: severity/subtype/spans). Only fields the verdict actually supplies (and
    that resolve/reconcile) change; the explanation is re-rendered because the
    subtype and/or forms may have moved."""
    adj = dict(error)
    if "severity" in verdict:
        sev = _enum_lookup(prompts.SEVERITY_ENUM, verdict.get("severity"))
        if sev is not None:
            adj["severity"] = sev
    if "subtype" in verdict:
        sub = _enum_lookup(subtypes, verdict.get("subtype"))
        if sub is not None:
            adj["subtype"] = sub
    if "span_repro" in verdict:
        span, form = _reconcile_span_form(reproduction, verdict.get("span_repro"), adj["learner_form"], l2_code)
        if span is not None:
            adj["span_reproduction"], adj["learner_form"] = span, form
    if "span_ref" in verdict:
        span, form = _reconcile_span_form(reference, verdict.get("span_ref"), adj["corrected_form"], l2_code)
        if span is not None:
            adj["span_reference"], adj["corrected_form"] = span, form
    explanation, _ = render_explanation(
        taxonomy_cfg, adj["subtype"], l1_code, adj["learner_form"], adj["corrected_form"],
    )
    adj["explanation"] = explanation
    return adj


def _judgment_band(judgments, dim: str, reproduction: str) -> Optional[int]:
    """The Verifier's band for one judged dimension, or None if the judgment lacks
    a valid evidence span or a usable band (§4: discarded → dimension missing →
    renormalized). Returning None here is what stops an evidence-free judgment from
    silently pulling the overall toward a full mark."""
    j = judgments.get(dim) if isinstance(judgments, dict) else None
    if not isinstance(j, dict):
        return None
    if not _has_valid_evidence(j.get("evidence_spans"), reproduction):
        return None
    band = j.get("band")
    if isinstance(band, bool):
        return None
    try:
        value = float(band)
    except (TypeError, ValueError):
        return None
    if not (1 <= value <= MAX_BAND):
        return None
    return int(round(value))


def _has_valid_evidence(spans, reproduction: str) -> bool:
    """True iff `spans` has at least one well-formed, in-bounds [start,end] into
    the learner text — the mandatory-evidence gate for a judgment (§4)."""
    if not isinstance(spans, list) or not spans:
        return False
    n = len(reproduction or "")
    for span in spans:
        v = _valid_span(span)
        if v is not None and v[1] <= n:
            return True
    return False


def _maybe_arbitrate(
    db, *, detector_errors, proposed, verifier_confidence, rejected_count,
    kept, added, judgments, subtypes, subtype_labels, taxonomy_cfg, rubric_cfg,
    l1_code, l2_code, l2_language_id, gold_l2, reproduction, age_tier, slugs_trace,
):
    """Config-gated Tier-3 arbiter (default OFF). Fires when the Verifier rejected
    ≥ ARBITER_REJECT_RATE of the proposals OR its confidence < ARBITER_CONFIDENCE_
    FLOOR. Re-adjudicates by re-running the Verifier role on the Tier-3 slug over
    the full proposed list; on success its merge REPLACES the Tier-2 result.

    (Re-runs the full proposed list rather than only the contested subset — a
    deliberate simplification of §2's "contested errors only": the arbiter's
    verdict on an uncontested error is a no-op confirm, and re-indexing a subset
    would fork the merge logic. Cost only matters on this OFF-by-default path.)

    Returns (final_errors, rejected_count, judgments, attempted_tier, t_in, t_out,
    trace). attempted_tier is 'tier3' only when the arbiter actually re-adjudicated."""
    num_proposed = len(proposed)
    reject_rate = (rejected_count / num_proposed) if num_proposed else 0.0
    fires = reject_rate >= ARBITER_REJECT_RATE or verifier_confidence < ARBITER_CONFIDENCE_FLOOR
    trace = {
        "triggered": fires,
        "reject_rate": round(reject_rate, 3),
        "verifier_confidence": verifier_confidence,
        "used": False,
    }
    # Not gated on max_tier: the budget cap governs the normal cascade depth,
    # while the arbiter is a separate config-gated opt-in already fenced by
    # verifier_ok (which required tier2 to run) and the trigger above.
    if not fires:
        return kept + added, rejected_count, judgments, None, 0, 0, trace

    route = resolve_tier(db, "tier3", l2_language_id)
    slugs_trace.append(route.as_trace_entry())
    if route.slug is None:
        return kept + added, rejected_count, judgments, None, 0, 0, trace

    sys_prompt = prompts.build_verifier_system_prompt(
        l2_code, rubric_cfg, age_tier, subtypes, subtype_labels=subtype_labels,
    )
    usr_prompt = prompts.build_verifier_user_prompt(l2_code, gold_l2, reproduction, proposed)
    payload, t_in, t_out, _reason = _invoke_model(
        route.slug, "arbiter", sys_prompt, usr_prompt, prompts.validate_verifier_response,
    )
    if payload is None:
        return kept + added, rejected_count, judgments, None, t_in, t_out, trace

    a_kept, a_added, a_rejected = _apply_verdicts(
        detector_errors, payload.get("verdicts", []), payload.get("added_errors", []),
        subtypes, taxonomy_cfg, l1_code, reproduction, gold_l2, l2_code,
    )
    trace["used"] = True
    return a_kept + a_added, a_rejected, payload.get("judgments", {}), "tier3", t_in, t_out, trace
