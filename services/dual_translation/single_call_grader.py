"""Single-call generative grader for Dual Translation (ADR-044).

One cheap structured-output call per submission. The model returns a list of
errors — sentence number, the offending learner text, a taxonomy-v6 type, a
severity and a short English note — and everything else is done in Python:

  * the model's learner fragment is located in the reproduction (it must be
    there verbatim, or be repairable by ``grader_cascade._reconcile_span_form``);
  * the reference-side fragment (``span_reference`` / ``corrected_form``) is
    derived by aligning the learner sentence with its reference sentence — the
    model is not asked for it, because the validated prompt does not ask;
  * each error goes through the same ``grader_cascade._decode_error`` validation
    as the v1/v2 flows, so it comes out in the identical ``dt_error_instance``
    shape with the template-rendered ``explanation`` (ADR-015);
  * accuracy / fidelity / understandability are derived by the unchanged
    ``scoring.compute_dimension_bands`` and ``scoring.compute_overall``.

The prompt, schema and request parameters are the frozen Track B ``p1_expl``
variant (``single_call_prompts``); the per-(model, language) severity rule is the
one frozen in ``data/eval/dt_decision_2026-11-14/track_b/frozen_configs.json``.

Dispatch (``grader_cascade._grade_cascade``, after the Tier 0 short-circuit,
gated by ``Config.DT_SINGLE_CALL_GRADER``, default off):

    primary model  --fails-->  fallback model (once)  --fails-->  configured flow

"Fails" = the call raised, or the response was not a JSON object with an
``errors`` list. ``grade`` then returns ``(None, failure)`` and the cascade grades
the submission with the configured v2/v1 flow, stamping why on
``grader_trace.single_call`` (``mark_fallback``). A single-call failure therefore
never awards silent full marks. Any unexpected exception in here is treated the
same way — this module must not be able to break grading.

Naturalness and range — NOT scored
----------------------------------
The experiment could not validate either dimension: Track B's "naturalness" was
only a derived proxy (band 3 if any naturalness-type error was reported, else 4)
on a gold set with 2-3 informative items per language, and range is band 4 on
every gold item. The existing contract already allows a dimension to be absent
(a v2 grade whose Verifier judgment had no evidence leaves it out of ``scores``
and ``scoring.compute_overall`` renormalises over what is present; the UI skips a
missing dimension). So this flow takes the most conservative reading: it returns
``scores`` for accuracy, fidelity and understandability ONLY, computes
``overall_band`` over those three, and lists the other two under
``grader_trace.single_call.unscored_dimensions``. It never invents a band 4.

Fields the model does not supply
--------------------------------
``source`` (interlingual / intralingual) and ``confidence`` are NOT NULL columns
that the validated prompt does not ask for. They are filled with fixed defaults
(``DEFAULT_SOURCE``, ``DEFAULT_CONFIDENCE`` — the same 0.5 ``_decode_error`` uses
for a missing confidence) and the defaults are named in the trace so nobody
mistakes them for model judgements.

Explanations
------------
``explanation`` stays the template-rendered Rule text (ADR-015). The model's own
short note is English, unreviewed, and may not be in the learner's L1, so it is
kept apart as ``explanation_parts.model_note`` (after the explainer's length /
single-paragraph / score-pattern guards) and never concatenated into
``explanation``. ``explanation_parts.application`` is None unless
``Config.DT_SINGLE_CALL_EXPLAINER`` runs the v2 Explainer as a second call.

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

# Fixed fill-ins for NOT NULL columns the prompt does not ask the model for.
DEFAULT_SOURCE = "intralingual"
DEFAULT_CONFIDENCE = 0.5

# Below this token-level similarity a learner sentence is treated as a free
# rewrite of its reference: no local alignment is attempted and the correction
# shown is the whole reference sentence.
MIN_ALIGN_RATIO = 0.5

# Size caps on what is kept for storage (see migrations/dt_grading_assets.sql).
RAW_RESPONSE_CAP = 4000      # chars of raw text kept, and only for a failed parse
RAW_ERRORS_CAP = 50          # model error entries kept per attempt
RAW_FIELD_CAP = 300          # chars per string field of a kept entry
ERROR_TEXT_CAP = 300         # chars of an attempt's error message

UNSCORED_DIMENSIONS = ("naturalness", "range")

STATUS_OK = "ok"
STATUS_CALL_FAILED = "call_failed"
STATUS_MALFORMED_JSON = "malformed_json"
STATUS_MALFORMED_SHAPE = "malformed_shape"

SPAN_FROM_MODEL = "model"          # the model's fragment, found verbatim
SPAN_REPAIRED = "repaired"         # found only after relocation / folding
SPAN_FROM_SENTENCE = "sentence"    # not found: the whole learner sentence is used
CORRECTION_ALIGNED = "aligned_diff"
CORRECTION_SENTENCE = "reference_sentence"


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
) -> tuple[Optional[dict], Optional[dict]]:
    """Grade one Tier-0-unresolved submission with the single-call flow.

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
    l2_code, l1_code, l2_language_id, l1_language_id,
) -> tuple[Optional[dict], Optional[dict]]:
    from services.dual_translation import grader_cascade as gc  # lazy: gc imports this module's caller

    # ── Preconditions: a frozen prompt for this L2, under a matching taxonomy ──
    if not sc_prompts.supports(l2_code):
        return None, _failure(f"no single-call prompt for l2={l2_code!r}", [], [])
    type_ids = sc_prompts.FROZEN_TYPE_IDS[l2_code]
    missing = [t for t in type_ids if t not in subtypes]
    if missing:
        return None, _failure(
            "taxonomy mismatch: the loaded taxonomy lacks single-call types "
            f"{missing[:5]} (taxonomy v6 required)", [], [],
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
    system_prompt = sc_prompts.build_system_prompt(l2_code, free_translation=free_translation)
    user_prompt = sc_prompts.build_user_prompt(pairs)
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
    errors, per_error, dropped, span_repaired = _decode(
        gc, payload["errors"], pairs=pairs, type_ids=type_ids, subtypes=subtypes,
        taxonomy_cfg=taxonomy_cfg, subtype_meta=subtype_meta, severity_rule=severity_rule,
        l1_code=l1_code, l2_code=l2_code, gold_l2=gold_l2, reproduction=reproduction,
    )
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
    for err in errors:
        parts = err.get("explanation_parts")
        if not isinstance(parts, dict):
            parts = {"rule": err.get("explanation", ""), "application": None}
            err["explanation_parts"] = parts
        parts["model_note"] = err.get("model_note")

    if Config.DT_TAXONOMY_COLUMNS:
        for err in errors:
            err["taxonomy_version"] = taxonomy_version

    # ── Derived scoring (accuracy / fidelity / understandability only) ───
    bands = scoring.compute_dimension_bands(errors, subtype_meta, rubric_cfg)
    present_dims = list(scoring.DERIVED_DIMENSIONS)
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
        "span_repaired": span_repaired,
        "sentence_pairs": {"n": len(pairs), "aligned_ok": bool(alignment.ok)},
        "unscored_dimensions": list(UNSCORED_DIMENSIONS),
        "defaults": {"source": DEFAULT_SOURCE, "confidence": DEFAULT_CONFIDENCE},
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
    answer is kept as the model's own error list, capped per field."""
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
        "response": {"errors": _capped_entries(parsed["errors"])} if ok else None,
        "errors_raw": len(parsed["errors"]) if ok else None,
        "errors_kept": None,
        "dropped": None,
        "raw_response": None if ok or not raw else raw[:RAW_RESPONSE_CAP],
        "raw_truncated": (not ok) and len(raw) > RAW_RESPONSE_CAP,
    }


def _capped_entries(entries: list) -> list:
    out = []
    for entry in entries[:RAW_ERRORS_CAP]:
        if isinstance(entry, dict):
            out.append({
                str(k)[:40]: (v[:RAW_FIELD_CAP] if isinstance(v, str) else v)
                for k, v in list(entry.items())[:8]
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
) -> tuple[list[dict], list[dict], dict, int]:
    """Model entries -> (decoded errors, per-error trace rows, drop counts, repaired).

    An entry is dropped (and counted) when its type/severity is not in the schema
    enums (``invalid_entry``), when its learner fragment cannot be located AND it
    names no usable sentence (``span_unlocatable``), or when the shared
    ``_decode_error`` validation rejects it (``decode_rejected``). A fragment that
    cannot be located in a sentence the model did name is REPAIRED to that whole
    learner sentence (Track B scored it the same way) and counted in
    ``span_repaired`` together with relocated fragments."""
    errors: list[dict] = []
    per_error: list[dict] = []
    dropped = {"invalid_entry": 0, "span_unlocatable": 0, "decode_rejected": 0}
    span_repaired = 0

    for entry in raw_errors:
        if (not isinstance(entry, dict) or entry.get("type") not in type_ids
                or entry.get("type") not in subtypes
                or entry.get("severity") not in sc_prompts.SEVERITIES):
            dropped["invalid_entry"] += 1
            logger.warning("dual_translation.single_call_grader: dropping invalid entry: %.200r", entry)
            continue
        subtype, model_severity = entry["type"], entry["severity"]

        number = entry.get("sentence")
        named = (pairs[number - 1]
                 if isinstance(number, int) and not isinstance(number, bool) and 1 <= number <= len(pairs)
                 else None)
        span, learner_form, span_source = _locate_fragment(gc, entry.get("span"), named, reproduction, l2_code)
        if span is None:
            dropped["span_unlocatable"] += 1
            logger.warning(
                "dual_translation.single_call_grader: dropping entry whose learner text cannot be located: %.200r",
                entry,
            )
            continue
        if span_source != SPAN_FROM_MODEL:
            span_repaired += 1

        sentence_index = _pair_index(pairs, span[0])
        pair = pairs[sentence_index] if sentence_index is not None else named
        span_ref, corrected_form, correction_source = _reference_counterpart(
            pair, span, span_source, gold_l2, reproduction, l2_code,
        )

        severity = _apply_severity_rule(severity_rule, model_severity, subtype, subtype_meta)
        raw = {
            "span_repro": span,
            "span_ref": span_ref,
            "learner_form": learner_form,
            "corrected_form": corrected_form,
            "category": gc._enum_index(prompts.CATEGORY_ENUM, gc._derive_category(taxonomy_cfg, subtype)),
            "source": gc._enum_index(prompts.SOURCE_ENUM, DEFAULT_SOURCE),
            "severity": gc._enum_index(prompts.SEVERITY_ENUM, severity),
            "subtype": gc._enum_index(subtypes, subtype),
            "confidence": DEFAULT_CONFIDENCE,
        }
        decoded = gc._decode_error(raw, subtypes, taxonomy_cfg, l1_code, reproduction, gold_l2, l2_code)
        if decoded is None:
            dropped["decode_rejected"] += 1
            continue

        explanation = entry.get("explanation")
        decoded["sentence_index"] = sentence_index
        decoded["model_severity"] = model_severity
        decoded["model_note"] = _validated_model_note(explanation)
        decoded["span_source"] = span_source
        decoded["correction_source"] = correction_source
        errors.append(decoded)
        per_error.append({
            "sentence_index": sentence_index,
            "subtype": subtype,
            "model_severity": model_severity,
            "applied_severity": severity,
            "span_source": span_source,
            "correction_source": correction_source,
            "model_explanation": explanation[:RAW_FIELD_CAP] if isinstance(explanation, str) else None,
            "confidence": None,  # the prompt does not ask for one
        })
    return errors, per_error, dropped, span_repaired


def _locate_fragment(gc, fragment, named: Optional[SentencePair], reproduction: str, l2_code: str):
    """Locate the model's learner fragment in the reproduction.

    -> (span, learner_form, span_source), or (None, "", None) when it cannot be
    located and no sentence fallback exists. Order: verbatim inside the sentence
    the model named (the Track B rule); else ``_reconcile_span_form`` anywhere in
    the text, nearest the named sentence, with width/kana/case folding; else the
    whole named learner sentence."""
    text = fragment.strip() if isinstance(fragment, str) else ""
    if text:
        if named is not None:
            idx = reproduction.find(text, named.repro.start, named.repro.end)
            if idx >= 0:
                return [idx, idx + len(text)], text, SPAN_FROM_MODEL
        anchor = named.repro.start if named is not None else None
        hint = [anchor, anchor] if anchor is not None else None
        span, form = gc._reconcile_span_form(reproduction, hint, text, l2_code)
        if span is not None:
            return span, form, SPAN_REPAIRED
    if named is not None:
        bounds = _stripped_bounds(reproduction, named.repro.start, named.repro.end)
        if bounds is not None:
            return list(bounds), reproduction[bounds[0]:bounds[1]], SPAN_FROM_SENTENCE
    return None, "", None


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


def _validated_model_note(text) -> Optional[str]:
    """The model's short note, or None. Reuses the Explainer's Application-layer
    guards (``explainer.MAX_APPLICATION_CHARS``, single paragraph, no score-like
    digits). The "must quote a form" guard is deliberately NOT applied: the note
    is English prose about a zh/ja fragment and rarely quotes it, and unlike an
    Application layer it is never merged into ``explanation``."""
    if not isinstance(text, str):
        return None
    trimmed = text.strip()
    if not trimmed or len(trimmed) > explainer.MAX_APPLICATION_CHARS:
        return None
    if "\n" in trimmed or "\r" in trimmed:
        return None
    if explainer._SCORE_PATTERN.search(trimmed):
        return None
    return trimmed


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
    if span_source == SPAN_FROM_SENTENCE or pair.ref.end <= pair.ref.start:
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
