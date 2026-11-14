"""Re-check one revised sentence with the single-call grader (tech 6.1).

The only model boundary of the feature. It reuses - does not fork - the grader:
the same system prompt, user-prompt format, strict schema, request extras, JSON
parsing and decoder (``single_call_grader._decode``) as grading, on a one-pair
input (the revised sentence against its reference sentence). Primary model only,
one attempt, a short timeout. ``single_call_grader._attempt`` is not used because
it does not forward a timeout; its parsing is mirrored here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Optional

from config import Config
from services.llm_output_cleaner import clean_json_response
from services.dual_translation import single_call_grader
from services.dual_translation import single_call_prompts as sc_prompts
from services.dual_translation.repair import settings
from services.dual_translation.sentence_pairs import build_sentence_pairs

logger = logging.getLogger(__name__)

STATUS_OK = "ok"
STATUS_CALL_FAILED = "call_failed"
STATUS_TIMEOUT = "timeout"
STATUS_MALFORMED = "malformed"
STATUS_UNSUPPORTED = "unsupported"

TASK_NAME = "dt_repair_recheck"
RAW_RESPONSE_CAP = 4000


def _is_timeout(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    try:
        import openai
        if isinstance(exc, openai.APITimeoutError):
            return True
    except Exception:  # noqa: BLE001 - openai missing in a test env
        pass
    return "timeout" in type(exc).__name__.lower() or "timed out" in str(exc).lower()


def _result(status: str, **extra) -> dict:
    out = {
        "status": status, "errors": [], "model": None,
        "prompt_version": sc_prompts.PROMPT_VERSION,
        "prompt_variant": sc_prompts.prompt_variant(bool(Config.DT_SINGLE_CALL_FREE_TRANSLATION)),
        "tokens": {"in": 0, "out": 0, "cached": None}, "cost_usd": None, "latency_ms": 0,
    }
    out.update(extra)
    return out


def recheck_sentence(
    db, *, reference_sentence: str, revised_sentence: str, l2_code: str, l1_code: str,
    l2_language_id: int, l1_language_id: int, timeout_s: Optional[float] = None,
    taxonomy: Optional[dict] = None,
) -> dict:
    """Grade ``revised_sentence`` against ``reference_sentence`` (tech 6.1 shape).

    ``taxonomy`` may be passed in (tests, smoke runs); otherwise the active one is
    loaded exactly as the cascade does. Never raises."""
    from services.dual_translation import grader_cascade as gc  # lazy, like the grader

    timeout = settings.DT_REPAIR_RECHECK_TIMEOUT_S if timeout_s is None else timeout_s
    if not sc_prompts.supports(l2_code):
        return _result(STATUS_UNSUPPORTED)
    try:
        taxonomy_cfg = taxonomy if taxonomy is not None else gc.get_active_taxonomy(db)
        subtypes = gc._resolve_subtypes(taxonomy_cfg, l1_code, l2_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("dt_repair.recheck: taxonomy unavailable: %s", exc)
        return _result(STATUS_UNSUPPORTED)
    type_ids = sc_prompts.TYPE_IDS[l2_code]
    if set(type_ids) != set(subtypes):
        return _result(STATUS_UNSUPPORTED)

    slug = (Config.DT_SINGLE_CALL_MODEL or "").strip()
    if not slug:
        return _result(STATUS_UNSUPPORTED)
    free = bool(Config.DT_SINGLE_CALL_FREE_TRANSLATION)
    pairs = build_sentence_pairs(reference_sentence, revised_sentence).pairs
    system = sc_prompts.build_system_prompt(l2_code, free_translation=free, band_descriptors="")
    user = sc_prompts.build_user_prompt(pairs, l1_code, l2_code)
    schema = sc_prompts.response_schema(l2_code, l1_code)

    started = time.monotonic()
    try:
        call = single_call_grader.call_structured(
            slug, system, user, schema=schema, max_tokens=sc_prompts.MAX_TOKENS,
            extra=single_call_grader.REQUEST_EXTRAS.get(slug), timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - every failure is a status
        latency = int((time.monotonic() - started) * 1000)
        status = STATUS_TIMEOUT if _is_timeout(exc) else STATUS_CALL_FAILED
        logger.warning("dt_repair.recheck: call to %r failed (%s): %s", slug, status, exc)
        res = _result(status, model=slug, latency_ms=latency)
        _log_failure(res, l2_code, system, user, None, f"{type(exc).__name__}: {exc}")
        return res

    latency_s = call.get("latency_s")
    latency = (int(round(latency_s * 1000)) if isinstance(latency_s, (int, float))
               else int((time.monotonic() - started) * 1000))
    tokens = {"in": int(call.get("tokens_in") or 0), "out": int(call.get("tokens_out") or 0),
              "cached": call.get("cached_tokens")}
    meta = {"model": slug, "tokens": tokens, "cost_usd": call.get("cost_usd"), "latency_ms": latency}
    raw = call.get("content") or ""
    try:
        payload = json.loads(clean_json_response(raw))
    except (ValueError, TypeError) as exc:
        res = _result(STATUS_MALFORMED, **meta)
        _log_failure(res, l2_code, system, user, raw, f"{type(exc).__name__}: {exc}")
        return res
    if not isinstance(payload, dict) or not isinstance(payload.get("errors"), list):
        res = _result(STATUS_MALFORMED, **meta)
        _log_failure(res, l2_code, system, user, raw, "shape")
        return res

    try:
        severity_rule = single_call_grader.SEVERITY_RULES.get(slug, {}).get(
            l2_code, single_call_grader.DEFAULT_SEVERITY_RULE)
        subtype_meta = (taxonomy_cfg or {}).get("subtype_meta", {}) or {}
        decoded, _, _ = single_call_grader._decode(
            gc, payload["errors"], pairs=pairs, type_ids=type_ids, subtypes=subtypes,
            taxonomy_cfg=taxonomy_cfg, subtype_meta=subtype_meta, severity_rule=severity_rule,
            l1_code=l1_code, l2_code=l2_code, gold_l2=reference_sentence,
            reproduction=revised_sentence,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("dt_repair.recheck: decode failed: %s", exc)
        res = _result(STATUS_MALFORMED, **meta)
        _log_failure(res, l2_code, system, user, raw, f"decode: {type(exc).__name__}: {exc}")
        return res

    errors = [{
        "subtype": e.get("subtype"),
        "severity": e.get("severity"),
        "model_severity": e.get("model_severity"),
        "confidence": e.get("confidence"),
        "confidence_label": e.get("confidence_label"),
        "span": list(e.get("span_reproduction") or [0, 0]),
        "learner_form": e.get("learner_form") or "",
        "corrected_form": e.get("corrected_form") or "",
        "correction_source": e.get("correction_source"),
        "span_source": e.get("span_source"),
        "model_note": e.get("model_note"),
    } for e in decoded]
    return _result(STATUS_OK, errors=errors, **meta)


def _log_failure(res: dict, l2_code: str, system: str, user: str, raw: Optional[str], error: str) -> None:
    """One llm_calls row for a failed re-check (successful ones live on the
    dt_repair_event row). Fail-soft."""
    try:
        from services import llm_service

        llm_service._log_llm_call(
            pipeline="dual_translation", task_name=TASK_NAME, template_version=None,
            model=res.get("model") or "", temperature=sc_prompts.TEMPERATURE, seed=None,
            prompt_hash=hashlib.sha256((system + "\n\x00\n" + user).encode("utf-8")).digest(),
            raw_response=(raw[:RAW_RESPONSE_CAP] if raw else None),
            parsed_ok=res["status"] not in (STATUS_CALL_FAILED, STATUS_TIMEOUT),
            schema_ok=False, judge_verdict=None, judge_confidence=None,
            latency_ms=res.get("latency_ms"), artifact_id=None, cost_usd=res.get("cost_usd"),
            language_code=l2_code, max_tokens=sc_prompts.MAX_TOKENS,
            timeout_s=int(settings.DT_REPAIR_RECHECK_TIMEOUT_S),
            input_tokens=res["tokens"]["in"], output_tokens=res["tokens"]["out"],
            cached_tokens=res["tokens"].get("cached"), call_role=llm_service.CALL_ROLE_PRIMARY,
            error=error[:300],
        )
    except Exception as exc:  # noqa: BLE001 - observability never breaks a check
        logger.warning("dt_repair.recheck: llm_calls logging failed: %s", exc)
