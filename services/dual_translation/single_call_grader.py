"""Single-call generative grader for Dual Translation (ADR-044), prompt v2.

One cheap structured-output call per submission. The model returns

  * a list of errors - sentence number, an exact quote of the learner fragment,
    the reference fragment it should have been, a taxonomy-v6 type, a severity, a
    confidence (high / medium / low), a source (interlingual / intralingual) and
    a one-sentence explanation in the learner's L1; then
  * a band (1-4) with a verbatim evidence quote for ``naturalness`` and ``range``.

Everything else is done in Python:

  * each learner quote is LOCATED in the reproduction (``_locate_learner``): exact
    match in the named sentence -> width/kana/case/punctuation-normalised match
    -> exact/normalised match elsewhere (a mis-numbered sentence) -> bounded fuzzy
    match inside the named sentence -> the diff hunk of that sentence that best
    overlaps the quote -> only then the whole sentence. The path taken is the
    error's ``span_source`` and is counted in ``grader_trace.single_call.
    span_resolution``;
  * the reference quote is located the same way in the reference sentence and
    becomes ``span_reference`` / ``corrected_form`` (``correction_source =
    model_quote``); a missing/unlocatable quote falls back to aligning the two
    sentences (``aligned_diff``) and finally to the whole reference sentence;
  * each error goes through the same ``grader_cascade._decode_error`` validation
    as the v1/v2 flows, so it comes out in the identical ``dt_error_instance``
    shape with the template-rendered ``explanation`` (ADR-015);
  * accuracy / fidelity / understandability are derived by the unchanged
    ``scoring.compute_dimension_bands``; naturalness / range are the model's
    judgments; ``scoring.compute_overall`` weighs all five.

Dispatch (``grader_cascade._grade_cascade``, after the Tier 0 short-circuit,
gated by ``Config.DT_SINGLE_CALL_GRADER``, default ON since 2026-11-14):

    primary model  --fails-->  fallback model (once)  --fails-->  configured flow

"Fails" = the call raised, or the response was not a JSON object with an
``errors`` list. ``grade`` then returns ``(None, failure)`` and the cascade grades
the submission with the configured v2/v1 flow, stamping why on
``grader_trace.single_call`` (``mark_fallback``). A single-call failure therefore
never awards silent full marks. Any unexpected exception in here is treated the
same way - this module must not be able to break grading.

Naturalness and range - scored, but NOT validated to the same standard
----------------------------------------------------------------------
All five rubric dimensions are scored, as the grading contract expects. The two
judged dimensions mirror the v2 Verifier: the same rubric band descriptors for
the passage's age tier go in the prompt, and a judgment counts only when its
band is 1-4 AND its evidence quote is found in the learner text
(``_decode_judgments``, the equivalent of ``grader_cascade._judgment_band`` /
``_has_valid_evidence``). In addition a naturalness band below 4 is discarded
when its evidence is only a listed grammar/meaning error, which is already
scored on accuracy or fidelity. A judgment that fails is left out of ``scores``
and ``overall_band`` renormalises over the rest; it is never defaulted to 4.

Be clear about what the evidence is: the v6 gold set has naturalness = 3 on 7 of
91 items and = 4 on the rest, and range = 4 on every item. Agreement on these two
dimensions is therefore measured on almost no variation (see
``data/eval/dt_decision_2026-11-14/prod_check/v2/REPORT.md``); it shows the model
does not invent low bands, not that it can tell a 2 from a 3.

Confidence and source - model judgments
---------------------------------------
``confidence`` is the model's high / medium / low mapped to 0.9 / 0.6 / 0.3
(``single_call_prompts.CONFIDENCE_VALUES``); the label is kept as
``confidence_label``. ``source`` is the model's interlingual / intralingual call,
made knowing the learner's L1 (the taxonomy carries no per-type default source,
so there is nothing to derive it from). Neither has gold labels: the confidence
signal was checked against gold true/false positives (same REPORT), ``source`` is
unvalidated. A missing/invalid value (possible only from a model that ignores the
strict schema) falls back to ``DEFAULT_CONFIDENCE`` / ``DEFAULT_SOURCE`` and is
counted in ``defaulted``.

An entry the model marks ``low`` ("it could well be acceptable") is WITHHELD: not
in ``errors``, not scored, counted in ``dropped.low_confidence`` and listed in
``withheld_low_confidence``. On the gold set all low-confidence entries were
false alarms on correct sentences. ``Config.DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE``
(default off) keeps them, for a UI that has an "unsure" state.

Explanations
------------
``explanation`` stays the template-rendered Rule text (ADR-015). The model's own
explanation is asked for in the learner's L1 and, when it passes the Explainer's
Application-layer guards (``explainer._validated_application``: <= 240 chars,
one paragraph, no score-like digits, mentions the learner or corrected form) plus
a cheap wrong-language check, is SHOWN to the learner as
``explanation_parts.application`` - the field the results UI already renders under
the Rule text. When a guard rejects it, the template stands alone. Each error
records which it was in ``explanation_source`` (model | template | explainer) and
the accepted text in ``model_note``; the reject reason is in the per-error trace.
``Config.DT_SINGLE_CALL_EXPLAINER`` (default off) runs the v2 Explainer as a
second call; its Application layer then takes precedence.

Unknown error types
-------------------
The strict schema restricts ``type`` to the hardcoded exhaustive list. If a model
returns something else anyway, a v5 slug that taxonomy v6 ``legacy_aliases`` maps
onto an allowed type is mapped and counted (``type_aliased``); anything else is
dropped and counted (``dropped.unknown_type``) with a warning. Never silent.

Budget gate
-----------
The route's daily token budget (TASK-601) degrades the v1/v2 flows by capping
``max_tier``. The single call is cheaper than a tier-1-only grade, so it runs
regardless of ``max_tier``; its tokens are still reported in
``grader_trace.tokens`` (what the budget sums), and a fall-back to the configured
flow honours ``max_tier`` as before.

Persistence
-----------
Pure with respect to grade persistence, like the rest of the cascade: the
contract carries a response-only ``grading_assets`` list (one record per model
attempt) that the route pops, stores in ``dt_grading_call`` and never returns to
the client. The one side effect is observability: each attempt is logged to
``llm_calls`` through ``services.llm_service._log_llm_call`` (fail-soft,
``Config.DT_SINGLE_CALL_LOG_LLM_CALLS``).

``call_structured`` and ``_log_call`` are module-level so tests can monkeypatch
them as the model / observability boundaries.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import re
import time
import unicodedata
from typing import Optional

from config import Config
from services.llm_output_cleaner import clean_json_response
from services.dual_translation import explainer, prompts, scoring, word_choice_variant
from services.dual_translation import single_call_prompts as sc_prompts
from services.dual_translation.sentence_pairs import SentencePair, build_sentence_pairs

logger = logging.getLogger(__name__)

FLOW = "single_call"

# Frozen per-(model, L2) severity rule (Track B frozen_configs.json, "explaining"):
#   "model" — use the model's severity;
#   "prior" — use the taxonomy default severity of the predicted type, unless the
#             model said critical.
# A slug with no validated rule uses the model's own severity.
SEVERITY_RULES: dict[str, dict[str, str]] = {
    "openai/gpt-6-luna": {"en": "prior", "zh": "model", "ja": "model"},
    "deepseek/deepseek-v4.1-flash": {"en": "prior", "zh": "model", "ja": "prior"},
}
DEFAULT_SEVERITY_RULE = "model"

# Per-model request extras the validated runs sent (reasoning off). A slug not
# listed sends no `reasoning` key at all.
REQUEST_EXTRAS: dict[str, dict] = {
    "openai/gpt-6-luna": {"reasoning": {"effort": "none"}},
    "deepseek/deepseek-v4.1-flash": {"reasoning": {"enabled": False}},
}

CALL_TIMEOUT_S = 30

# Used only when the model's value is missing/invalid (a model that ignored the
# strict schema); counted in grader_trace.single_call.defaulted.
DEFAULT_SOURCE = "intralingual"
DEFAULT_CONFIDENCE = 0.5

# Entries the model marks with this confidence are withheld from the grade unless
# Config.DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE is on.
WITHHELD_CONFIDENCE = "low"

# Below this token-level similarity a learner sentence is treated as a free
# rewrite of its reference: no local alignment is attempted and the correction
# shown is the whole reference sentence.
MIN_ALIGN_RATIO = 0.5

# Bounded fuzzy quote matching (inside ONE sentence only).
FUZZY_MIN_RATIO = 0.75       # SequenceMatcher ratio of the best window vs the quote
FUZZY_MAX_TOKENS = 400       # sentences longer than this are not fuzzy-searched
FUZZY_MIN_CHARS = {"en": 4}  # shortest quote worth fuzzy-matching (default 2)

# Size caps on what is kept for storage (see migrations/dt_grading_assets.sql).
RAW_RESPONSE_CAP = 4000      # chars of raw text kept, and only for a failed parse
RAW_ERRORS_CAP = 50          # model error entries kept per attempt
RAW_FIELD_CAP = 300          # chars per string field of a kept entry
ERROR_TEXT_CAP = 300         # chars of an attempt's error message

STATUS_OK = "ok"
STATUS_CALL_FAILED = "call_failed"
STATUS_MALFORMED_JSON = "malformed_json"
STATUS_MALFORMED_SHAPE = "malformed_shape"

# span_source: how the learner span was resolved, best to worst.
SPAN_EXACT = "exact"              # the quote, verbatim
SPAN_NORMALISED = "normalised"    # found after width/kana/case/punctuation folding
SPAN_FUZZY = "fuzzy"              # closest window in the named sentence (>= FUZZY_MIN_RATIO)
SPAN_DIFF_HUNK = "diff_hunk"      # the changed region of the sentence overlapping the quote
SPAN_SENTENCE = "sentence"        # last resort: the error is marked on the whole sentence
SPAN_SOURCES = (SPAN_EXACT, SPAN_NORMALISED, SPAN_FUZZY, SPAN_DIFF_HUNK, SPAN_SENTENCE)

CORRECTION_MODEL_QUOTE = "model_quote"     # the model's reference quote, located in REF
CORRECTION_ALIGNED = "aligned_diff"        # found by aligning the two sentences
CORRECTION_SENTENCE = "reference_sentence" # the whole reference sentence
CORRECTION_SOURCES = (CORRECTION_MODEL_QUOTE, CORRECTION_ALIGNED, CORRECTION_SENTENCE)

EXPLANATION_FROM_MODEL = "model"
EXPLANATION_FROM_TEMPLATE = "template"
EXPLANATION_FROM_EXPLAINER = "explainer"

JUDGMENT_OK = "ok"
JUDGMENT_MISSING = "missing"
JUDGMENT_BAD_BAND = "bad_band"
JUDGMENT_NO_EVIDENCE = "no_evidence"
JUDGMENT_DOUBLE_COUNT = "evidence_is_scored_error"


# ---------------------------------------------------------------------------
# Model boundary
# ---------------------------------------------------------------------------

def call_structured(
    slug: str, system_prompt: str, user_prompt: str, *, schema: dict,
    max_tokens: int, extra: Optional[dict] = None, timeout: int = CALL_TIMEOUT_S,
) -> dict:
    """One strict-``json_schema`` OpenRouter call. Returns

        {content, tokens_in, tokens_out, cached_tokens, reasoning_tokens,
         cost_usd, latency_s, provider, finish_reason}

    and raises on any transport/API error. ``cost_usd`` is what OpenRouter reports
    on ``usage.cost`` (None when it reports nothing — never an estimate).

    Separate from ``llm_runner.call_model_with_usage`` because that wrapper
    cannot send ``response_format`` / ``reasoning`` and discards cost and cache
    usage, all of which this flow needs.
    """
    from services import llm_service  # lazy: keeps this module import-light for tests

    client = llm_service.get_client(provider="openrouter")
    extra_body: dict = {"usage": {"include": True}}
    extra_body.update(extra or {})
    start = time.time()
    response = client.chat.completions.create(
        model=slug,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=sc_prompts.TEMPERATURE,
        max_tokens=max_tokens,
        response_format={"type": "json_schema", "json_schema": schema},
        extra_body=extra_body,
        timeout=timeout,
    )
    latency = time.time() - start

    content, finish_reason = "", None
    if response.choices:
        content = response.choices[0].message.content or ""
        finish_reason = getattr(response.choices[0], "finish_reason", None)
    t_in, t_out, cached, reasoning = llm_service._extract_usage_tokens(response)
    provider = getattr(response, "provider", None)
    if provider is None:
        provider = (getattr(response, "model_extra", None) or {}).get("provider")
    return {
        "content": content,
        "tokens_in": int(t_in or 0),
        "tokens_out": int(t_out or 0),
        "cached_tokens": cached,
        "reasoning_tokens": reasoning,
        "cost_usd": llm_service._extract_cost(response),
        "latency_s": latency,
        "provider": provider,
        "finish_reason": finish_reason,
    }


def _log_call(attempt: dict, *, l2_code: str, prompt_hash: bytes, raw_response: Optional[str]) -> None:
    """Record one attempt in ``llm_calls`` via the shared helper (fail-soft there;
    guarded here too so observability can never break grading)."""
    if not Config.DT_SINGLE_CALL_LOG_LLM_CALLS:
        return
    try:
        from services import llm_service

        ok = attempt["status"] == STATUS_OK
        llm_service._log_llm_call(
            pipeline="dual_translation",
            task_name="dt_single_call_grade",
            template_version=None,
            model=attempt["slug"],
            temperature=sc_prompts.TEMPERATURE,
            seed=None,
            prompt_hash=prompt_hash,
            # The parsed answer is stored with the grade (dt_grading_call); the raw
            # text is only worth keeping when it could not be parsed.
            raw_response=None if ok else raw_response,
            parsed_ok=attempt["status"] not in (STATUS_CALL_FAILED, STATUS_MALFORMED_JSON),
            schema_ok=ok,
            judge_verdict=None,
            judge_confidence=None,
            latency_ms=attempt.get("latency_ms"),
            artifact_id=None,
            cost_usd=attempt.get("cost_usd"),
            language_code=l2_code,
            provider=attempt.get("provider"),
            max_tokens=sc_prompts.MAX_TOKENS,
            timeout_s=CALL_TIMEOUT_S,
            input_tokens=attempt["tokens"]["in"],
            output_tokens=attempt["tokens"]["out"],
            cached_tokens=attempt["tokens"].get("cached"),
            reasoning_tokens=attempt["tokens"].get("reasoning"),
            call_role=(llm_service.CALL_ROLE_PRIMARY if attempt["role"] == "primary"
                       else llm_service.CALL_ROLE_RETRY),
            error=attempt.get("error"),
        )
    except Exception as exc:  # noqa: BLE001 — observability must never break grading
        logger.warning("dual_translation.single_call_grader: llm_calls logging failed: %s", exc)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def grade(
    db,
    *,
    tier0_result,
    rubric_cfg: dict,
    taxonomy_cfg: dict,
    subtypes: list[str],
    gold_l2: str,
    reproduction: str,
    l2_code: str,
    l1_code: str,
    l2_language_id: int,
    l1_language_id: Optional[int] = None,
    age_tier: Optional[int] = None,
) -> tuple[Optional[dict], Optional[dict]]:
    """Grade one Tier-0-unresolved submission with the single-call flow.

    ``age_tier`` selects the rubric's naturalness/range band descriptors quoted in
    the prompt (as the v2 Verifier does); None quotes none.

    Returns ``(contract, None)`` on success, or ``(None, failure)`` when the flow
    could not produce a grade — the caller then runs the configured flow and
    passes its contract and ``failure`` to ``mark_fallback``. ``failure`` is
    ``{reason, attempts, assets, tokens}``.
    """
    try:
        return _grade(
            db, tier0_result=tier0_result, rubric_cfg=rubric_cfg, taxonomy_cfg=taxonomy_cfg,
            subtypes=subtypes, gold_l2=gold_l2, reproduction=reproduction, l2_code=l2_code,
            l1_code=l1_code, l2_language_id=l2_language_id, l1_language_id=l1_language_id,
            age_tier=age_tier,
        )
    except Exception as exc:  # noqa: BLE001 — never let this flow break grading
        logger.warning(
            "dual_translation.single_call_grader: unexpected failure, using the configured flow: %s",
            exc, exc_info=True,
        )
        return None, _failure(f"single-call error: {type(exc).__name__}: {str(exc)[:200]}", [], [])


def mark_fallback(contract: dict, failure: dict) -> dict:
    """Stamp a contract produced by the configured (v2/v1) flow with the fact that
    the single-call flow was tried first and why it did not grade. The failed
    attempts' tokens are added to ``grader_trace.tokens`` (they were spent, and
    the daily budget sums that field) and their asset records ride along."""
    trace = contract.setdefault("grader_trace", {})
    tokens = trace.setdefault("tokens", {"in": 0, "out": 0})
    spent = failure.get("tokens") or {}
    tokens["in"] = int(tokens.get("in") or 0) + int(spent.get("in") or 0)
    tokens["out"] = int(tokens.get("out") or 0) + int(spent.get("out") or 0)
    fallback_flow = "v2" if trace.get("framework_version") == 2 else "v1"
    trace["single_call"] = {
        "used": False,
        "path": f"fallback_flow:{fallback_flow}",
        "reason": failure.get("reason"),
        "prompt_version": sc_prompts.PROMPT_VERSION,
        "attempts": failure.get("attempts") or [],
    }
    if failure.get("assets"):
        contract["grading_assets"] = failure["assets"]
    return contract


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------

def _grade(
    db, *, tier0_result, rubric_cfg, taxonomy_cfg, subtypes, gold_l2, reproduction,
    l2_code, l1_code, l2_language_id, l1_language_id, age_tier,
) -> tuple[Optional[dict], Optional[dict]]:
    from services.dual_translation import grader_cascade as gc  # lazy: gc imports this module's caller

    # ── Preconditions: a prompt for this L2 whose type list IS the taxonomy's ──
    if not sc_prompts.supports(l2_code):
        return None, _failure(f"no single-call prompt for l2={l2_code!r}", [], [])
    type_ids = sc_prompts.TYPE_IDS[l2_code]
    missing = [t for t in type_ids if t not in subtypes]
    extra = [t for t in subtypes if t not in type_ids]
    if missing or extra:
        return None, _failure(
            "taxonomy mismatch: the hardcoded single-call type list is not the loaded "
            f"taxonomy's list for {l1_code}-{l2_code} (not in taxonomy: {missing[:5]}; "
            f"not in prompt: {extra[:5]}) - taxonomy v6 required", [], [],
        )
    scoring.scoring_params(rubric_cfg)  # raises (-> fallback) on a pre-v5 rubric

    primary = (Config.DT_SINGLE_CALL_MODEL or "").strip()
    fallback = (Config.DT_SINGLE_CALL_FALLBACK_MODEL or "").strip()
    if not primary:
        return None, _failure("no single-call model configured", [], [])
    slugs = [("primary", primary)]
    if fallback and fallback != primary:
        slugs.append(("fallback", fallback))

    free_translation = bool(Config.DT_SINGLE_CALL_FREE_TRANSLATION)
    variant = sc_prompts.prompt_variant(free_translation)
    alignment = build_sentence_pairs(gold_l2, reproduction)
    pairs = alignment.pairs
    descriptors = _band_descriptors(rubric_cfg, age_tier, l2_code)
    system_prompt = sc_prompts.build_system_prompt(
        l2_code, free_translation=free_translation, band_descriptors=descriptors,
    )
    user_prompt = sc_prompts.build_user_prompt(pairs, l1_code, l2_code)
    schema = sc_prompts.response_schema(l2_code)
    prompt_hash = hashlib.sha256((system_prompt + "\n\x00\n" + user_prompt).encode("utf-8")).digest()

    taxonomy_version = gc.get_active_taxonomy_version(db)
    rubric_version = gc.get_active_rubric_version(db)

    attempts: list[dict] = []
    assets: list[dict] = []
    payload: Optional[dict] = None
    used: Optional[dict] = None
    for role, slug in slugs:
        attempt, raw_text, parsed = _attempt(role, slug, system_prompt, user_prompt, schema)
        attempts.append(attempt)
        asset = _asset_record(
            attempt, raw_text, parsed, l2_code=l2_code, variant=variant,
            taxonomy_version=taxonomy_version, rubric_version=rubric_version,
        )
        assets.append(asset)
        _log_call(attempt, l2_code=l2_code, prompt_hash=prompt_hash,
                  raw_response=asset.get("raw_response"))
        if attempt["status"] == STATUS_OK:
            payload, used = parsed, attempt
            break

    if payload is None:
        reason = "; ".join(f"{a['role']} {a['slug']} {a['status']}" for a in attempts)
        return None, _failure(reason, attempts, assets)

    # ── Decode ──────────────────────────────────────────────────────────
    slug = used["slug"]
    severity_rule = SEVERITY_RULES.get(slug, {}).get(l2_code, DEFAULT_SEVERITY_RULE)
    subtype_meta = (taxonomy_cfg or {}).get("subtype_meta", {}) or {}
    errors, per_error, counts = _decode(
        gc, payload["errors"], pairs=pairs, type_ids=type_ids, subtypes=subtypes,
        taxonomy_cfg=taxonomy_cfg, subtype_meta=subtype_meta, severity_rule=severity_rule,
        l1_code=l1_code, l2_code=l2_code, gold_l2=gold_l2, reproduction=reproduction,
    )
    dropped = counts["dropped"]
    judged_bands, judgment_trace = _decode_judgments(
        payload, reproduction, l2_code, errors=errors, subtype_meta=subtype_meta)
    assets[-1]["severity_rule"] = severity_rule
    assets[-1]["errors_kept"] = len(errors)
    assets[-1]["dropped"] = dict(dropped)

    # ── word_choice variant (v6), exactly as the v2 flow does it ─────────
    variant_basis = None
    if prompts.variants_enabled(subtypes):
        variant_basis = word_choice_variant.resolve_variants(
            db, errors, l2_code=l2_code, l2_language_id=l2_language_id,
            l1_language_id=l1_language_id,
        )
        gc.rerender_variant_explanations(errors, taxonomy_cfg, l1_code)

    # ── Explanation layers ──────────────────────────────────────────────
    # `explanation` stays the Rule template (ADR-015). The model's own L1
    # explanation, when it passed the guards in _decode, is what the UI shows as
    # the Application layer; a rejected one leaves the template on its own.
    tokens_in, tokens_out = _sum_tokens(attempts)
    explainer_trace = None
    if errors and Config.DT_SINGLE_CALL_EXPLAINER:
        errors, exp_in, exp_out, exp_reason = explainer.attach_explanations(
            db, errors=errors, reference=gold_l2, reproduction=reproduction,
            l1_code=l1_code, l2_language_id=l2_language_id, taxonomy_cfg=taxonomy_cfg,
        )
        tokens_in += exp_in
        tokens_out += exp_out
        explainer_trace = {"tokens": {"in": exp_in, "out": exp_out}, "reason": exp_reason}
    explanation_sources = {EXPLANATION_FROM_MODEL: 0, EXPLANATION_FROM_TEMPLATE: 0}
    for err, row in zip(errors, per_error):
        parts = err.get("explanation_parts")
        if not isinstance(parts, dict):
            parts = {"rule": err.get("explanation", ""), "application": None}
            err["explanation_parts"] = parts
        if parts.get("application"):  # the opt-in second Explainer call won
            err["explanation_source"] = EXPLANATION_FROM_EXPLAINER
        elif err.get("model_note"):
            parts["application"] = err["model_note"]
            err["explanation_source"] = EXPLANATION_FROM_MODEL
        else:
            err["explanation_source"] = EXPLANATION_FROM_TEMPLATE
        row["explanation_source"] = err["explanation_source"]
        explanation_sources[err["explanation_source"]] = (
            explanation_sources.get(err["explanation_source"], 0) + 1)

    if Config.DT_TAXONOMY_COLUMNS:
        for err in errors:
            err["taxonomy_version"] = taxonomy_version

    # ── Scoring: three derived dimensions + the two judged ones ──────────
    bands = dict(scoring.compute_dimension_bands(errors, subtype_meta, rubric_cfg))
    present_dims = list(scoring.DERIVED_DIMENSIONS)
    for dim in sc_prompts.JUDGED_DIMENSIONS:
        if dim in judged_bands:
            bands[dim] = judged_bands[dim]
            present_dims.append(dim)
    unscored = [d for d in sc_prompts.JUDGED_DIMENSIONS if d not in judged_bands]
    weights = scoring.resolve_weights(rubric_cfg, l2_code)
    overall_band = scoring.compute_overall(bands, weights, present_dims)
    scores = {dim: bands[dim] for dim in present_dims}

    path = "primary" if used["role"] == "primary" else "fallback_model"
    failed = [a for a in attempts if a["status"] != STATUS_OK]
    reason = "; ".join(f"{a['role']} {a['slug']} {a['status']}" for a in failed) or None
    single_trace = {
        "used": True,
        "path": path,
        "model": slug,
        "provider": used.get("provider"),
        "prompt_version": sc_prompts.PROMPT_VERSION,
        "prompt_variant": variant,
        "severity_rule": severity_rule,
        "parse_status": used["status"],
        "usage": dict(used["tokens"]),
        "cost_usd": _sum_cost(attempts),
        "latency_ms": used.get("latency_ms"),
        "attempts": attempts,
        "errors_raw": len(payload["errors"]),
        "errors_kept": len(errors),
        "dropped": dict(dropped),
        "dropped_total": sum(dropped.values()),
        "withheld_low_confidence": counts["withheld"],
        "type_aliased": counts["type_aliased"],
        "defaulted": dict(counts["defaulted"]),
        "span_resolution": dict(counts["span"]),
        "span_other_sentence": counts["span_other_sentence"],
        "correction_resolution": dict(counts["correction"]),
        "explanation_sources": explanation_sources,
        "explanation_rejections": dict(counts["explanation_rejections"]),
        "sentence_pairs": {"n": len(pairs), "aligned_ok": bool(alignment.ok)},
        "judgments": judgment_trace,
        "unscored_dimensions": unscored,
        "band_descriptors": bool(descriptors),
        "confidence_scale": dict(sc_prompts.CONFIDENCE_VALUES),
        "per_error": per_error,
    }
    if explainer_trace is not None:
        single_trace["explainer"] = explainer_trace

    grader_trace = {
        "tier": FLOW,
        "deterministic_prefilter": False,
        "cache_hit": False,
        "tokens": {"in": tokens_in, "out": tokens_out},
        "slugs": [
            {"requested_tier": FLOW, "tier": FLOW, "slug": a["slug"],
             "fell_open": a["status"] != STATUS_OK}
            for a in attempts
        ],
        "framework_version": FLOW,
        "provisional": False,
        "rejected_count": 0,
        "prompt_version": {
            "rubric": rubric_version,
            "taxonomy": taxonomy_version,
            "single_call": sc_prompts.PROMPT_VERSION,
        },
        "fell_open": False,
        "reason": reason,
        "single_call": single_trace,
    }
    if variant_basis is not None:
        grader_trace["variant_basis"] = variant_basis

    contract = {
        "scores": scores,
        "overall_band": overall_band,
        "diff": tier0_result.diff,
        "errors": errors,
        "highlights": [],
        "grader_trace": grader_trace,
        "provisional": False,
        "grading_assets": assets,
    }
    return contract, None


def _band_descriptors(rubric_cfg: dict, age_tier, l2_code: str) -> str:
    """The active rubric's naturalness/range band descriptors for this age tier
    (the same text the v2 Verifier quotes), or "" when there are none."""
    if age_tier is None:
        return ""
    try:
        return prompts._band_descriptors_text(
            rubric_cfg, sc_prompts.JUDGED_DIMENSIONS, age_tier, l2_code) or ""
    except Exception as exc:  # noqa: BLE001 — descriptors only calibrate; never block grading
        logger.warning("dual_translation.single_call_grader: no band descriptors: %s", exc)
        return ""


def _attempt(role: str, slug: str, system_prompt: str, user_prompt: str, schema: dict):
    """Run one model attempt -> (attempt_record, raw_text, parsed_payload_or_None)."""
    attempt = {
        "role": role, "slug": slug, "status": STATUS_CALL_FAILED, "provider": None,
        "tokens": {"in": 0, "out": 0, "cached": None, "reasoning": None},
        "cost_usd": None, "latency_ms": None, "finish_reason": None, "error": None,
    }
    try:
        result = call_structured(
            slug, system_prompt, user_prompt, schema=schema,
            max_tokens=sc_prompts.MAX_TOKENS, extra=REQUEST_EXTRAS.get(slug),
        )
    except Exception as exc:  # noqa: BLE001 — network/API errors fail this attempt
        logger.warning("dual_translation.single_call_grader: call to %r failed: %s", slug, exc)
        attempt["error"] = f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_CAP]
        return attempt, None, None

    latency = result.get("latency_s")
    attempt.update({
        "provider": result.get("provider"),
        "tokens": {
            "in": int(result.get("tokens_in") or 0),
            "out": int(result.get("tokens_out") or 0),
            "cached": result.get("cached_tokens"),
            "reasoning": result.get("reasoning_tokens"),
        },
        "cost_usd": result.get("cost_usd"),
        "latency_ms": int(round(latency * 1000)) if isinstance(latency, (int, float)) else None,
        "finish_reason": result.get("finish_reason"),
    })
    raw_text = result.get("content") or ""
    try:
        payload = json.loads(clean_json_response(raw_text))
    except (ValueError, TypeError) as exc:
        logger.warning(
            "dual_translation.single_call_grader: response from %r was not valid JSON (%s): %.200r",
            slug, exc, raw_text,
        )
        attempt["status"] = STATUS_MALFORMED_JSON
        attempt["error"] = f"{type(exc).__name__}: {exc}"[:ERROR_TEXT_CAP]
        return attempt, raw_text, None
    if not isinstance(payload, dict) or not isinstance(payload.get("errors"), list):
        logger.warning(
            "dual_translation.single_call_grader: response from %r failed shape validation: %.200r",
            slug, payload,
        )
        attempt["status"] = STATUS_MALFORMED_SHAPE
        return attempt, raw_text, None
    attempt["status"] = STATUS_OK
    return attempt, raw_text, payload


def _asset_record(
    attempt: dict, raw_text: Optional[str], parsed: Optional[dict], *,
    l2_code: str, variant: str, taxonomy_version, rubric_version,
) -> dict:
    """The durable record of one model attempt (-> one ``dt_grading_call`` row).
    Structured JSON, never the prompt: the prompt is reproducible from
    ``prompt_version`` + ``prompt_variant`` + the stored reference/reproduction.
    The raw text is kept (capped) only when it could not be parsed; a parsed
    answer is kept as the model's own error list and two judgments, capped per field."""
    ok = attempt["status"] == STATUS_OK
    raw = raw_text or ""
    return {
        "flow": FLOW,
        "role": attempt["role"],
        "model_slug": attempt["slug"],
        "provider": attempt.get("provider"),
        "prompt_version": sc_prompts.PROMPT_VERSION,
        "prompt_variant": variant,
        "severity_rule": None,
        "l2_code": l2_code,
        "status": attempt["status"],
        "error": attempt.get("error"),
        "finish_reason": attempt.get("finish_reason"),
        "tokens_in": attempt["tokens"]["in"],
        "tokens_out": attempt["tokens"]["out"],
        "cached_tokens": attempt["tokens"].get("cached"),
        "reasoning_tokens": attempt["tokens"].get("reasoning"),
        "cost_usd": attempt.get("cost_usd"),
        "latency_ms": attempt.get("latency_ms"),
        "taxonomy_version": taxonomy_version,
        "rubric_version": rubric_version,
        "response": _capped_response(parsed) if ok else None,
        "errors_raw": len(parsed["errors"]) if ok else None,
        "errors_kept": None,
        "dropped": None,
        "raw_response": None if ok or not raw else raw[:RAW_RESPONSE_CAP],
        "raw_truncated": (not ok) and len(raw) > RAW_RESPONSE_CAP,
    }


def _capped_response(parsed: dict) -> dict:
    out = {"errors": _capped_entries(parsed["errors"])}
    for dim in sc_prompts.JUDGED_DIMENSIONS:
        judgment = parsed.get(dim)
        if isinstance(judgment, dict):
            out[dim] = _capped_entries([judgment])[0]
    return out


def _capped_entries(entries: list) -> list:
    out = []
    for entry in entries[:RAW_ERRORS_CAP]:
        if isinstance(entry, dict):
            out.append({
                str(k)[:40]: (v[:RAW_FIELD_CAP] if isinstance(v, str) else v)
                for k, v in list(entry.items())[:10]
                if isinstance(v, (str, int, float, bool)) or v is None
            })
        else:
            out.append({"_invalid": str(entry)[:RAW_FIELD_CAP]})
    return out


def _failure(reason: str, attempts: list, assets: list) -> dict:
    t_in, t_out = _sum_tokens(attempts)
    return {"reason": reason, "attempts": attempts, "assets": assets,
            "tokens": {"in": t_in, "out": t_out}}


def _sum_tokens(attempts: list) -> tuple[int, int]:
    return (sum(a["tokens"]["in"] for a in attempts), sum(a["tokens"]["out"] for a in attempts))


def _sum_cost(attempts: list) -> Optional[float]:
    costs = [a["cost_usd"] for a in attempts if isinstance(a.get("cost_usd"), (int, float))]
    return round(sum(costs), 8) if costs else None


# ---------------------------------------------------------------------------
# Decoding the model's error list
# ---------------------------------------------------------------------------

def _decode(
    gc, raw_errors: list, *, pairs: list[SentencePair], type_ids, subtypes, taxonomy_cfg,
    subtype_meta, severity_rule, l1_code, l2_code, gold_l2, reproduction,
) -> tuple[list[dict], list[dict], dict]:
    """Model entries -> (decoded errors, per-error trace rows, counts).

    ``counts`` = {dropped, type_aliased, defaulted, span, span_other_sentence,
    correction, explanation_rejections}. An entry is dropped - always counted and
    logged, never silently - when it is not an object or its severity is not in
    the enum (``invalid_entry``), when its type is neither in the hardcoded list
    nor a legacy alias of one (``unknown_type``), when its learner quote cannot be
    located AND it names no usable sentence (``span_unlocatable``), or when the
    shared ``_decode_error`` validation rejects it (``decode_rejected``). An entry
    the model itself marked confidence = low is withheld (``low_confidence``;
    ``Config.DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE`` keeps it)."""
    errors: list[dict] = []
    per_error: list[dict] = []
    counts = {
        "dropped": {"invalid_entry": 0, "unknown_type": 0, "low_confidence": 0,
                    "span_unlocatable": 0, "decode_rejected": 0},
        "withheld": [],
        "type_aliased": 0,
        "defaulted": {"confidence": 0, "source": 0},
        "span": {name: 0 for name in SPAN_SOURCES},
        "span_other_sentence": 0,
        "correction": {name: 0 for name in CORRECTION_SOURCES},
        "explanation_rejections": {},
    }
    dropped = counts["dropped"]

    for entry in raw_errors:
        if not isinstance(entry, dict) or entry.get("severity") not in sc_prompts.SEVERITIES:
            dropped["invalid_entry"] += 1
            logger.warning("dual_translation.single_call_grader: dropping invalid entry: %.200r", entry)
            continue
        subtype, aliased_from = _resolve_type(entry.get("type"), type_ids, subtypes, taxonomy_cfg)
        if subtype is None:
            dropped["unknown_type"] += 1
            logger.warning(
                "dual_translation.single_call_grader: dropping entry with unknown error type %r: %.200r",
                entry.get("type"), entry,
            )
            continue
        if aliased_from is not None:
            counts["type_aliased"] += 1
            logger.warning(
                "dual_translation.single_call_grader: mapped legacy error type %r -> %r",
                aliased_from, subtype,
            )
        model_severity = entry["severity"]

        confidence, confidence_label = _confidence(entry.get("confidence"))
        if confidence is None:
            confidence, confidence_label = DEFAULT_CONFIDENCE, None
            counts["defaulted"]["confidence"] += 1
        if confidence_label == WITHHELD_CONFIDENCE and not Config.DT_SINGLE_CALL_SHOW_LOW_CONFIDENCE:
            # The model's own "this could well be acceptable". On gold every such
            # entry was a false alarm on a correct sentence, so it is neither shown
            # nor scored - but it is counted and kept in the trace for review.
            dropped["low_confidence"] += 1
            counts["withheld"].append({
                key: (value[:RAW_FIELD_CAP] if isinstance(value, str) else value)
                for key, value in entry.items()
                if key in ("sentence", "learner_quote", "reference_quote", "type", "severity")
            })
            continue
        source = entry.get("source")
        if source not in sc_prompts.SOURCES:
            source = DEFAULT_SOURCE
            counts["defaulted"]["source"] += 1

        number = entry.get("sentence")
        named = (pairs[number - 1]
                 if isinstance(number, int) and not isinstance(number, bool) and 1 <= number <= len(pairs)
                 else None)
        located = _locate_learner(
            gc, entry.get("learner_quote"), entry.get("reference_quote"), named,
            gold_l2, reproduction, l2_code,
        )
        if located is None:
            dropped["span_unlocatable"] += 1
            logger.warning(
                "dual_translation.single_call_grader: dropping entry whose learner text cannot be located: %.200r",
                entry,
            )
            continue
        span, learner_form, span_source, hunk_ref = located

        if named is not None and named.repro.start <= span[0] and span[1] <= named.repro.end:
            sentence_index = number - 1  # also covers a zero-width point at a sentence edge
        else:
            sentence_index = _pair_index(pairs, span[0])
        pair = pairs[sentence_index] if sentence_index is not None else named
        if named is not None and pair is not named:
            counts["span_other_sentence"] += 1
        span_ref, corrected_form, correction_source = _reference_side(
            gc, entry.get("reference_quote"), pair, span, learner_form, span_source, hunk_ref,
            gold_l2, reproduction, l2_code,
        )

        severity = _apply_severity_rule(severity_rule, model_severity, subtype, subtype_meta)
        raw = {
            "span_repro": span,
            "span_ref": span_ref,
            "learner_form": learner_form,
            "corrected_form": corrected_form,
            "category": gc._enum_index(prompts.CATEGORY_ENUM, gc._derive_category(taxonomy_cfg, subtype)),
            "source": gc._enum_index(prompts.SOURCE_ENUM, source),
            "severity": gc._enum_index(prompts.SEVERITY_ENUM, severity),
            "subtype": gc._enum_index(subtypes, subtype),
            "confidence": confidence,
        }
        decoded = gc._decode_error(raw, subtypes, taxonomy_cfg, l1_code, reproduction, gold_l2, l2_code)
        if decoded is None:
            dropped["decode_rejected"] += 1
            logger.warning(
                "dual_translation.single_call_grader: entry rejected by the shared decode: %.200r", entry)
            continue

        explanation = entry.get("explanation")
        shown, rejection = _validate_explanation(
            explanation, decoded["learner_form"], decoded["corrected_form"], l1_code)
        if rejection is not None:
            counts["explanation_rejections"][rejection] = (
                counts["explanation_rejections"].get(rejection, 0) + 1)
        counts["span"][span_source] += 1
        counts["correction"][correction_source] += 1

        decoded["sentence_index"] = sentence_index
        decoded["model_severity"] = model_severity
        decoded["confidence_label"] = confidence_label
        decoded["model_note"] = shown
        decoded["span_source"] = span_source
        decoded["correction_source"] = correction_source
        errors.append(decoded)
        per_error.append({
            "sentence_index": sentence_index,
            "subtype": subtype,
            "type_aliased_from": aliased_from,
            "model_severity": model_severity,
            "applied_severity": severity,
            "confidence": confidence,
            "confidence_label": confidence_label,
            "source": source,
            "span_source": span_source,
            "correction_source": correction_source,
            "model_explanation": explanation[:RAW_FIELD_CAP] if isinstance(explanation, str) else None,
            "explanation_rejected": rejection,
        })
    return errors, per_error, counts


def _resolve_type(value, type_ids, subtypes, taxonomy_cfg) -> tuple[Optional[str], Optional[str]]:
    """-> (subtype, aliased_from). A type in the hardcoded list is returned as is.
    Otherwise a slug that the taxonomy's ``legacy_aliases`` maps onto an allowed
    type is mapped (aliased_from = the model's slug). Anything else -> (None, None)."""
    if not isinstance(value, str):
        return None, None
    if value in type_ids and value in subtypes:
        return value, None
    alias = ((taxonomy_cfg or {}).get("legacy_aliases") or {}).get(value)
    target = alias.get("to") if isinstance(alias, dict) else None
    if isinstance(target, str) and target in type_ids and target in subtypes:
        return target, value
    return None, None


def _confidence(value) -> tuple[Optional[float], Optional[str]]:
    """The model's confidence -> (number, label), or (None, None) when unusable.
    A bare number in [0, 1] (a model that ignored the enum) is accepted and
    bucketed to the nearest label."""
    if isinstance(value, str) and value in sc_prompts.CONFIDENCE_VALUES:
        return sc_prompts.CONFIDENCE_VALUES[value], value
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1:
        number = float(value)
        label = min(sc_prompts.CONFIDENCE_VALUES,
                    key=lambda name: abs(sc_prompts.CONFIDENCE_VALUES[name] - number))
        return number, label
    return None, None


def _decode_judgments(
    payload: dict, reproduction: str, l2_code: str, *, errors: list = (), subtype_meta: dict = None,
) -> tuple[dict, dict]:
    """The model's naturalness / range judgments -> ({dim: band}, trace).

    Mirrors the v2 Verifier's gate (``grader_cascade._judgment_band``): a judgment
    counts only with a band in 1..4 AND evidence that is really in the learner
    text. Here the evidence is a quote, so "valid" means it is found in the
    reproduction verbatim or after normalisation.

    One more evidence rule, for naturalness only (``JUDGMENT_DOUBLE_COUNT``): a
    band below 4 whose evidence is just a listed error of a type the taxonomy maps
    to accuracy or fidelity is not evidence about naturalness - that error is
    already scored on its own dimension (``scoring.compute_dimension_bands``).
    On gold the model lowered naturalness this way for about a third of the items
    that had any grammar error. Evidence that touches a naturalness-mapped error,
    or no listed error at all, stands.

    A judgment that fails any rule is left out (the overall renormalises); it is
    never replaced by a default band."""
    from services.dual_translation import grader_cascade as gc

    subtype_meta = subtype_meta or {}
    bands: dict[str, int] = {}
    trace: dict[str, dict] = {}
    for dim in sc_prompts.JUDGED_DIMENSIONS:
        judgment = payload.get(dim) if isinstance(payload, dict) else None
        if not isinstance(judgment, dict):
            trace[dim] = {"status": JUDGMENT_MISSING}
            continue
        band = judgment.get("band")
        if isinstance(band, bool) or not isinstance(band, int) or band not in sc_prompts.BANDS:
            trace[dim] = {"status": JUDGMENT_BAD_BAND}
            continue
        evidence = judgment.get("evidence")
        quote = evidence.strip() if isinstance(evidence, str) else ""
        hit = _find_quote(gc, reproduction, 0, len(reproduction), quote, l2_code) if quote else None
        if hit is None:
            trace[dim] = {"status": JUDGMENT_NO_EVIDENCE, "band": band}
            continue
        if dim == "naturalness" and band < max(sc_prompts.BANDS):
            touched = [
                (subtype_meta.get(e.get("subtype")) or {}).get("dimension")
                for e in errors
                if not e.get("is_mistake") and _overlaps(e.get("span_reproduction"), hit)
            ]
            if touched and "naturalness" not in touched:
                trace[dim] = {"status": JUDGMENT_DOUBLE_COUNT, "band": band,
                              "evidence_span": [hit[0], hit[1]]}
                continue
        bands[dim] = band
        trace[dim] = {"status": JUDGMENT_OK, "band": band, "evidence_span": [hit[0], hit[1]]}
    return bands, trace


def _overlaps(span, hit) -> bool:
    """True when an error span [start, end] shares a character with (or, for a
    zero-width point, lies inside) the evidence [start, end)."""
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        return False
    start, end = span
    if start == end:
        return hit[0] <= start <= hit[1]
    return start < hit[1] and hit[0] < end


# ---------------------------------------------------------------------------
# Locating a quote
# ---------------------------------------------------------------------------

def _punct_fold(gc, ch: str, l2_code: str) -> str:
    """Width/kana/case fold, with punctuation dropped and any whitespace as one
    space: a quote that lost its full stop or has straight for curly quotes."""
    if ch.isspace():
        return " "
    if unicodedata.category(ch).startswith("P"):
        return ""
    return gc._char_fold_l2(ch, l2_code)


def _find_quote(gc, text: str, lo: int, hi: int, quote: str, l2_code: str):
    """``quote`` inside ``text[lo:hi]`` -> (start, end, SPAN_EXACT | SPAN_NORMALISED)
    in ``text`` offsets, or None. Exact first; then the cascade's width/kana/case
    fold; then that fold with punctuation dropped."""
    idx = text.find(quote, lo, hi)
    if idx >= 0:
        return idx, idx + len(quote), SPAN_EXACT
    segment = text[lo:hi]
    for fold in (lambda ch: gc._char_fold_l2(ch, l2_code), lambda ch: _punct_fold(gc, ch, l2_code)):
        folded, index_map = gc._fold_map(segment, fold)
        folded_quote = "".join(fold(ch) for ch in quote).strip()
        if not folded_quote:
            continue
        pos = folded.find(folded_quote)
        if pos >= 0:
            start = lo + index_map[pos]
            end = lo + index_map[pos + len(folded_quote) - 1] + 1
            return start, end, SPAN_NORMALISED
    return None


def _fuzzy_find(gc, text: str, lo: int, hi: int, quote: str, l2_code: str):
    """The window of ``text[lo:hi]`` most similar to ``quote`` -> (start, end), or
    None when nothing reaches ``FUZZY_MIN_RATIO``. Bounded: one sentence, at most
    ``FUZZY_MAX_TOKENS`` tokens, windows within a third of the quote's length."""
    quote = quote.strip()
    if len(quote) < FUZZY_MIN_CHARS.get(l2_code, 2):
        return None
    tokens = _tokens(text[lo:hi], l2_code)
    if not tokens or len(tokens) > FUZZY_MAX_TOKENS:
        return None
    offsets = _offsets(tokens)
    fold = lambda value: "".join(gc._char_fold_l2(ch, l2_code) for ch in value)  # noqa: E731
    folded_quote = fold(quote)
    n = len(_tokens(quote, l2_code))
    slack = max(1, n // 3)
    best = None  # (ratio, -length, i, j)
    for size in range(max(1, n - slack), n + slack + 1):
        for i in range(0, len(tokens) - size + 1):
            if tokens[i].isspace() or tokens[i + size - 1].isspace():
                continue
            window = "".join(tokens[i:i + size])
            ratio = difflib.SequenceMatcher(None, fold(window), folded_quote, autojunk=False).ratio()
            key = (ratio, -len(window), i, i + size)
            if best is None or key[:2] > best[:2]:
                best = key
    if best is None or best[0] < FUZZY_MIN_RATIO:
        return None
    return lo + offsets[best[2]], lo + offsets[best[3]]


def _content_tokens(gc, text: str, l2_code: str) -> set:
    return {
        "".join(gc._char_fold_l2(ch, l2_code) for ch in token)
        for token in _tokens(text, l2_code)
        if not token.isspace() and not all(unicodedata.category(ch).startswith("P") for ch in token)
    }


def _diff_hunks(pair: SentencePair, gold_l2: str, reproduction: str, l2_code: str) -> list[dict]:
    """The changed regions between a reference sentence and its learner sentence:
    [{ref: (start, end), lrn: (start, end)}] in absolute offsets, whitespace-only
    changes left out. Empty for a free rewrite (< ``MIN_ALIGN_RATIO``), where the
    "hunk" would be most of the sentence."""
    ref_text = gold_l2[pair.ref.start:pair.ref.end]
    lrn_text = reproduction[pair.repro.start:pair.repro.end]
    a, b = _tokens(ref_text, l2_code), _tokens(lrn_text, l2_code)
    similarity = difflib.SequenceMatcher(
        None, [t for t in a if not t.isspace()], [t for t in b if not t.isspace()], autojunk=False,
    ).ratio()
    if similarity < MIN_ALIGN_RATIO:
        return []
    a_off, b_off = _offsets(a), _offsets(b)
    hunks = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if not "".join(a[i1:i2]).strip() and not "".join(b[j1:j2]).strip():
            continue
        hunks.append({
            "ref": (pair.ref.start + a_off[i1], pair.ref.start + a_off[i2]),
            "lrn": (pair.repro.start + b_off[j1], pair.repro.start + b_off[j2]),
        })
    return hunks


def _best_hunk(gc, hunks: list[dict], learner_quote: str, reference_quote: str,
               gold_l2: str, reproduction: str, l2_code: str) -> Optional[dict]:
    """The diff hunk that overlaps the model's quotes: the learner side must share
    a token with the learner quote, or the reference side with the reference
    quote. Among overlapping hunks the best-overlapping wins, then the smallest."""
    lrn_q = _content_tokens(gc, learner_quote, l2_code)
    ref_q = _content_tokens(gc, reference_quote, l2_code)
    best = None
    for hunk in hunks:
        lrn_t = _content_tokens(gc, reproduction[hunk["lrn"][0]:hunk["lrn"][1]], l2_code)
        ref_t = _content_tokens(gc, gold_l2[hunk["ref"][0]:hunk["ref"][1]], l2_code)
        score = 0.0
        if lrn_q and lrn_t:
            score = max(score, len(lrn_q & lrn_t) / len(lrn_q | lrn_t))
        if ref_q and ref_t:
            score = max(score, len(ref_q & ref_t) / len(ref_q | ref_t))
        if score <= 0:
            continue
        size = (hunk["lrn"][1] - hunk["lrn"][0]) + (hunk["ref"][1] - hunk["ref"][0])
        key = (score, -size)
        if best is None or key > best[0]:
            best = (key, hunk)
    return best[1] if best else None


def _locate_learner(gc, learner_quote, reference_quote, named: Optional[SentencePair],
                    gold_l2: str, reproduction: str, l2_code: str):
    """Locate the model's learner quote in the reproduction.

    -> (span, learner_form, span_source, hunk_ref) or None (cannot be located and
    no sentence to fall back on). ``hunk_ref`` is the reference side of the diff
    hunk when the span came from one, else None. Resolution order:

      1. exact, inside the sentence the model named            -> exact
      2. normalised (width/kana/case, then punctuation-free)   -> normalised
      3. exact / normalised anywhere else in the text (the model mis-numbered the
         sentence); nearest the named sentence wins            -> exact / normalised
      4. bounded fuzzy match inside the named sentence         -> fuzzy
      5. the diff hunk of the named sentence that overlaps the learner quote (or
         whose reference side overlaps the reference quote)    -> diff_hunk
      6. the whole named learner sentence                      -> sentence
    """
    quote = learner_quote.strip() if isinstance(learner_quote, str) else ""
    ref_quote = reference_quote.strip() if isinstance(reference_quote, str) else ""

    if quote:
        if named is not None:
            hit = _find_quote(gc, reproduction, named.repro.start, named.repro.end, quote, l2_code)
            if hit is not None:
                return [hit[0], hit[1]], reproduction[hit[0]:hit[1]], hit[2], None
        anchor = named.repro.start if named is not None else None
        span, form = gc._reconcile_span_form(
            reproduction, [anchor, anchor] if anchor is not None else None, quote, l2_code)
        if span is not None:
            return span, form, (SPAN_EXACT if form == quote else SPAN_NORMALISED), None
        if named is not None:
            fuzzy = _fuzzy_find(gc, reproduction, named.repro.start, named.repro.end, quote, l2_code)
            if fuzzy is not None:
                return [fuzzy[0], fuzzy[1]], reproduction[fuzzy[0]:fuzzy[1]], SPAN_FUZZY, None
    if named is None:
        return None

    sentence = _stripped_bounds(reproduction, named.repro.start, named.repro.end)
    hunk = _best_hunk(
        gc, _diff_hunks(named, gold_l2, reproduction, l2_code), quote, ref_quote,
        gold_l2, reproduction, l2_code,
    )
    if hunk is not None:
        bounds = _stripped_bounds(reproduction, *hunk["lrn"])
        if bounds is None:
            # The learner dropped text here: a zero-width point, corrected by the
            # reference side of the hunk (which is never empty in that case).
            point = hunk["lrn"][0]
            return [point, point], "", SPAN_DIFF_HUNK, hunk["ref"]
        if sentence is None or bounds != sentence:
            return list(bounds), reproduction[bounds[0]:bounds[1]], SPAN_DIFF_HUNK, hunk["ref"]
    if sentence is not None:
        return list(sentence), reproduction[sentence[0]:sentence[1]], SPAN_SENTENCE, None
    return None


def _stripped_bounds(text: str, start: int, end: int) -> Optional[tuple[int, int]]:
    """[start, end) narrowed to exclude surrounding whitespace; None if empty."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return (start, end) if end > start else None


def _pair_index(pairs: list[SentencePair], offset: int) -> Optional[int]:
    """0-based index of the sentence pair whose learner span contains ``offset``."""
    for idx, pair in enumerate(pairs):
        if pair.repro.start <= offset < pair.repro.end:
            return idx
    return None


def _apply_severity_rule(rule: str, model_severity: str, subtype: str, subtype_meta: dict) -> str:
    if rule == "prior" and model_severity != "critical":
        default = (subtype_meta.get(subtype) or {}).get("default_severity")
        if default in sc_prompts.SEVERITIES:
            return default
    return model_severity


_HAN_RE = re.compile(r"[一-鿿㐀-䶿]")
_KANA_RE = re.compile(r"[぀-ヿ]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def _validate_explanation(text, learner_form: str, corrected_form: str, l1_code: str):
    """The model's explanation -> (text to show, None) or (None, reject reason).

    The verdict is the Explainer's own Application-layer guard
    (``explainer._validated_application``: <= ``MAX_APPLICATION_CHARS``, a single
    paragraph, no score-like digits, mentions the learner or the corrected form),
    plus one cheap check the Explainer does not need because its whole prompt is
    in the L1: the text must look like the learner's L1. The reason names the
    first guard that fails; ``missing`` = the model sent no text."""
    if not isinstance(text, str) or not text.strip():
        return None, "missing"
    trimmed = text.strip()
    if len(trimmed) > explainer.MAX_APPLICATION_CHARS:
        return None, "too_long"
    if "\n" in trimmed or "\r" in trimmed:
        return None, "multi_paragraph"
    if explainer._SCORE_PATTERN.search(trimmed):
        return None, "score_pattern"
    if explainer._validated_application(trimmed, learner_form, corrected_form) is None:
        return None, "no_form_mention"
    if _wrong_language(trimmed, l1_code, (learner_form, corrected_form)):
        return None, "wrong_language"
    return trimmed, None


def _wrong_language(text: str, l1_code: str, forms) -> bool:
    """True when ``text`` (with the quoted L2 forms taken out) is clearly not in
    the learner's L1: an English L1 needs more Latin letters than CJK characters;
    a Chinese L1 needs Han characters and more of them than kana; a Japanese L1
    needs kana. Other L1s are not checked."""
    body = text
    for form in forms:
        if form:
            body = body.replace(form, " ")
    han, kana, latin = (len(rx.findall(body)) for rx in (_HAN_RE, _KANA_RE, _LATIN_RE))
    if l1_code == "en":
        return latin <= han + kana
    if l1_code == "zh":
        return han < 4 or kana > han
    if l1_code == "ja":
        return kana < 2
    return False


# ---------------------------------------------------------------------------
# Reference-side counterpart of a learner fragment
# ---------------------------------------------------------------------------

_EN_TOKEN_RE = re.compile(r"\s+|\w+(?:'\w+)?|[^\w\s]")


def _tokens(text: str, l2_code: str) -> list[str]:
    """Alignment tokens that tile ``text`` exactly: words/spaces/punctuation for
    English, single characters otherwise (same tokenisation as Track B's diff)."""
    if l2_code == "en":
        return _EN_TOKEN_RE.findall(text)
    return list(text)


def _reference_side(
    gc, reference_quote, pair: Optional[SentencePair], span: list[int], learner_form: str,
    span_source: str, hunk_ref, gold_l2: str, reproduction: str, l2_code: str,
) -> tuple[list[int], str, str]:
    """-> (span_reference, corrected_form, correction_source) for a learner span.

      1. the model's reference quote, located in the reference sentence (exact ->
         normalised -> bounded fuzzy), as long as it differs from the learner
         form and is not the whole sentence                    -> model_quote
      2. the reference side of the diff hunk the span came from -> aligned_diff
      3. ``_reference_counterpart``: carry the learner span across a token
         alignment of the two sentences                        -> aligned_diff
      4. the whole reference sentence                          -> reference_sentence
    The returned form always sits exactly at the returned span in ``gold_l2``."""
    if pair is None:
        return [0, 0], "", CORRECTION_SENTENCE
    quote = reference_quote.strip() if isinstance(reference_quote, str) else ""
    if quote and pair.ref.end > pair.ref.start:
        hit = _find_quote(gc, gold_l2, pair.ref.start, pair.ref.end, quote, l2_code)
        if hit is None:
            fuzzy = _fuzzy_find(gc, gold_l2, pair.ref.start, pair.ref.end, quote, l2_code)
            hit = (fuzzy[0], fuzzy[1]) if fuzzy is not None else None
        if hit is not None:
            form = gold_l2[hit[0]:hit[1]]
            whole = _stripped_bounds(gold_l2, pair.ref.start, pair.ref.end)
            is_sentence = whole is not None and (hit[0], hit[1]) == whole
            if form.strip() != learner_form.strip() and not is_sentence:
                return [hit[0], hit[1]], form, CORRECTION_MODEL_QUOTE
    if hunk_ref is not None:
        bounds = _stripped_bounds(gold_l2, hunk_ref[0], hunk_ref[1])
        if bounds is None:  # the learner added text with no reference counterpart
            return [hunk_ref[0], hunk_ref[0]], "", CORRECTION_ALIGNED
        return [bounds[0], bounds[1]], gold_l2[bounds[0]:bounds[1]], CORRECTION_ALIGNED
    return _reference_counterpart(pair, span, span_source, gold_l2, reproduction, l2_code)


def _reference_counterpart(
    pair: Optional[SentencePair], span: list[int], span_source: str,
    gold_l2: str, reproduction: str, l2_code: str,
) -> tuple[list[int], str, str]:
    """-> (span_reference, corrected_form, correction_source) for a learner span.

    The learner sentence is aligned with its reference sentence token by token and
    the learner span is carried across the alignment, so "This was a small
    computer" maps to "This is a small computer" and "was" to "is". When the
    mapped text shows no difference (the model pointed next to a dropped word), a
    deletion touching the span is pulled in. When there is nothing local to show —
    the span is the whole sentence, the sentence is a free rewrite
    (< ``MIN_ALIGN_RATIO``), or the mapped text is still identical — the
    correction is the whole reference sentence (``reference_sentence``).
    The returned form always sits exactly at the returned span in ``gold_l2``."""
    if pair is None:
        return [0, 0], "", CORRECTION_SENTENCE
    whole = _whole_reference_sentence(pair, gold_l2)
    if span_source == SPAN_SENTENCE or pair.ref.end <= pair.ref.start:
        return whole
    lrn_start, lrn_end = pair.repro.start, pair.repro.end
    if not (lrn_start <= span[0] and span[1] <= lrn_end):
        return whole

    ref_text = gold_l2[pair.ref.start:pair.ref.end]
    lrn_text = reproduction[lrn_start:lrn_end]
    a, b = _tokens(ref_text, l2_code), _tokens(lrn_text, l2_code)
    # Similarity over content tokens only: matching spaces would make two
    # unrelated English sentences look half-aligned.
    similarity = difflib.SequenceMatcher(
        None, [t for t in a if not t.isspace()], [t for t in b if not t.isspace()], autojunk=False,
    ).ratio()
    if similarity < MIN_ALIGN_RATIO:
        return whole
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    a_off, b_off = _offsets(a), _offsets(b)
    local_start, local_end = span[0] - lrn_start, span[1] - lrn_start
    j_start = next((j for j in range(len(b)) if b_off[j + 1] > local_start), len(b))
    j_end = next((j for j in range(len(b), 0, -1) if b_off[j - 1] < local_end), 0)
    if j_end <= j_start:
        return whole

    opcodes = matcher.get_opcodes()
    i_start = i_end = None
    for tag, i1, i2, j1, j2 in opcodes:
        if j1 <= j_start < j2:
            i_start = i1 + (j_start - j1) if tag == "equal" else i1
        if j1 <= j_end - 1 < j2:
            i_end = i1 + (j_end - j1) if tag == "equal" else i2
    if i_start is None or i_end is None or i_end < i_start:
        return whole

    if "".join(a[i_start:i_end]).strip() == "".join(b[j_start:j_end]).strip():
        # No visible difference inside the span: pull in a deletion (reference
        # text the learner dropped) that touches either edge of it.
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "delete" and j1 in (j_start, j_end):
                i_start, i_end = min(i_start, i1), max(i_end, i2)
        if "".join(a[i_start:i_end]).strip() == "".join(b[j_start:j_end]).strip():
            return whole

    bounds = _stripped_bounds(gold_l2, pair.ref.start + a_off[i_start], pair.ref.start + a_off[i_end])
    if bounds is None:  # the learner added text with no reference counterpart
        point = pair.ref.start + a_off[i_start]
        return [point, point], "", CORRECTION_ALIGNED
    return [bounds[0], bounds[1]], gold_l2[bounds[0]:bounds[1]], CORRECTION_ALIGNED


def _whole_reference_sentence(pair: SentencePair, gold_l2: str) -> tuple[list[int], str, str]:
    bounds = _stripped_bounds(gold_l2, pair.ref.start, pair.ref.end)
    if bounds is None:
        return [pair.ref.start, pair.ref.start], "", CORRECTION_SENTENCE
    return [bounds[0], bounds[1]], gold_l2[bounds[0]:bounds[1]], CORRECTION_SENTENCE


def _offsets(tokens: list[str]) -> list[int]:
    out = [0]
    for token in tokens:
        out.append(out[-1] + len(token))
    return out
