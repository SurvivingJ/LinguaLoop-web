"""
Collocation judge — one prompt, two call sites (L5 filter + L8 verdict).

L5 (collocation gap-fill) presents ``TARGET ___`` and asks the learner to pick
the right collocate. Its distractors must be genuine NON-collocates: if a
distractor is itself a natural collocate of TARGET in the sentence, it is an
also-correct answer and poisons the item. ``filter_collocation_distractors``
drops those.

L8 (collocation repair) plants ONE wrong collocate (``error_collocate``) in the
sentence and asks the learner to spot/repair it. The exercise is only valid when
that error word is a genuine non-collocate — clearly unnatural with TARGET. The
old fix was a brittle string-match retry (``_l8_correctness_ok`` in
prompt3_transforms.py); ``judge_collocation_repair`` replaces it with a semantic
verdict.

Both share ONE prompt and one underlying question, asked per candidate word in
the sentence with TARGET: how clearly is CANDIDATE a genuine non-collocate
(unnatural / wrong with TARGET here) versus a valid, idiomatic collocate?

Per project convention (tasklist decision 7 / memory ``distractor-judge-v3-likert``)
the judge reports a 5-point Likert ``rating`` per candidate — never a raw
0.0-1.0 float — mapped to a verdict by ``schemas.likert_to_verdict``:

    rating 5 / 4 -> accept      3 -> flag      2 / 1 -> reject

The rating measures how clearly the candidate is a genuine NON-collocate:
  5 = obviously unnatural with TARGET → ideal distractor / valid L8 error word;
  1 = a fully idiomatic, also-correct collocate → an also-right answer.

Output schema (per candidate, numbered from 1)::

    {"1": {"rating": 1-5, "reason": "..."}, ...}

  - L5 filter: keep a distractor unless its verdict is ``reject`` (rating 1-2,
    an also-valid collocate); ``accept``/``flag`` candidates are kept.
  - L8 verdict: the single ``error_collocate`` maps straight to a JudgeOutcome
    via its rating — a confident non-collocate (5/4) accepts the repair
    exercise, an also-valid collocate (2/1) rejects it.

Fail-open (both paths): any error — missing template, LLM failure, malformed
response — keeps every L5 distractor / safe-accepts the L8 exercise. The judge
behaves as if it were absent; it never blocks generation.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

from services.test_generation.schemas import likert_to_verdict
from .base import JudgeOutcome, safe_accept, log_judge_verdict

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_ladder_collocation'    # label in llm_calls (judge_ prefix)
_PT_NAME   = 'ladder_collocation_judge'    # task_name in prompt_templates
_PIPELINE  = 'vocab_ladder'

_cfg_cache: dict[int, dict] = {}           # language_id -> cfg dict

_VERDICT_ORDER = {'reject': 0, 'flag': 1, 'accept': 2}  # lower = worse
_KEEP_RATING   = 5.0                        # fail-open / missing-entry rating


# ---------------------------------------------------------------------------
# L5 — filter shape
# ---------------------------------------------------------------------------

def filter_collocation_distractors(
    db,
    sentence: str,
    target: str,
    correct_collocate: str,
    distractors: list[str],
    language_id: int,
) -> tuple[list[str], dict]:
    """Drop distractors that are themselves valid collocates of ``target``.

    Returns ``(kept_distractors, judge_meta)``; ``judge_meta`` matches the
    generalized sidecar lifted into ``exercises.tags.collocation_judge``::

        {"rejected": N, "kept": M, "rejected_items": [...],
         "model": "...", "version": N}

    A distractor is dropped only when its Likert verdict is ``reject`` (rating
    1-2 = an also-valid collocate). Fail-open: any error keeps every distractor.
    """
    if not distractors:
        return [], _empty_meta('unknown', 0)

    judged   = _judge_candidates(
        db, sentence, target, correct_collocate, distractors, language_id,
    )
    verdicts = judged['verdicts']
    # Keep genuine non-collocates; only a "reject" verdict (also-valid collocate)
    # drops the distractor, so a missing/uncertain verdict keeps it (fail-open).
    kept     = [d for d in distractors if verdicts.get(d) != 'reject']
    rejected = [d for d in distractors if verdicts.get(d) == 'reject']
    meta = {
        'rejected':       len(rejected),
        'kept':           len(kept),
        'rejected_items': rejected,
        'model':          judged['model'],
        'version':        judged['version'],
    }
    return kept, meta


# ---------------------------------------------------------------------------
# L8 — verdict shape
# ---------------------------------------------------------------------------

def judge_collocation_repair(
    db,
    sentence: str,
    target: str,
    correct_collocate: str,
    error_collocate: str,
    language_id: int,
) -> JudgeOutcome:
    """Verdict on whether ``error_collocate`` is a genuine non-collocate.

    ``accept`` (rating 5/4) → the error word is clearly wrong (a sound repair
    exercise); ``reject`` (rating 2/1) → the error word could pass as a valid
    collocate (broken exercise — the failure the old ``_l8_correctness_ok`` hack
    was patching); ``flag`` (rating 3) → uncertain. ``confidence`` carries the
    raw 1-5 rating.

    Fail-open: any error → ``safe_accept`` (ship the exercise unchanged, as
    before the judge existed).
    """
    if not error_collocate:
        return safe_accept('no error_collocate to judge')

    judged = _judge_candidates(
        db, sentence, target, correct_collocate, [error_collocate], language_id,
    )
    if not judged['ok']:
        # _judge_candidates already logged the underlying error.
        return safe_accept('collocation judge unavailable — safe-accept')

    verdict = judged['verdicts'].get(error_collocate, 'flag')
    rating  = judged['ratings'].get(error_collocate, _KEEP_RATING)
    reason  = judged['reasons'].get(error_collocate, '')
    outcome = JudgeOutcome(verdict=verdict, confidence=rating, reason=reason)

    log_judge_verdict(
        task_name=_TASK_NAME,
        model=judged['model'],
        verdict=outcome.verdict,
        confidence=outcome.confidence,
        pipeline=_PIPELINE,
    )
    return outcome


# ---------------------------------------------------------------------------
# Shared internals
# ---------------------------------------------------------------------------

def _judge_candidates(
    db,
    sentence: str,
    target: str,
    correct_collocate: str,
    candidates: list[str],
    language_id: int,
) -> dict:
    """Run the shared collocation prompt over a numbered candidate list.

    Returns::

        {'verdicts': {cand: 'accept'|'flag'|'reject'},   # likert_to_verdict
         'ratings':  {cand: float},                       # raw 1-5 Likert
         'reasons':  {cand: str},
         'model': ..., 'version': ..., 'ok': bool}

    ``ok`` is False on any fail-open path (template/LLM/parse error); in that
    case every candidate is reported as ``accept`` at the keep rating so the L5
    filter keeps it and the L8 verdict safe-accepts. A missing or unparseable
    per-candidate rating never manufactures a ``reject`` — it maps to ``flag``
    (keep), mirroring the v3 Likert contract.
    """
    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "collocation_judge: template load failed for lang=%d, fail-open: %s",
            language_id, exc,
        )
        return _failopen(candidates, 'unknown', 0)

    numbered = '\n'.join(f'{i + 1}. {c}' for i, c in enumerate(candidates))
    prompt = cfg['template'].format(
        sentence=sentence,
        target=target,
        correct_collocate=correct_collocate or '(none provided)',
        candidates_numbered=numbered,
    )
    model, version = cfg['model'], cfg['version']

    try:
        result = call_llm(
            prompt,
            model=model,
            temperature=0.0,
            response_format='json',
            provider=cfg['provider'],
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=version,
        )
    except Exception as exc:
        logger.warning("collocation_judge: LLM call failed, fail-open: %s", exc)
        return _failopen(candidates, model, version)

    if not isinstance(result, dict):
        logger.warning(
            "collocation_judge: non-dict response (%s), fail-open",
            type(result).__name__,
        )
        return _failopen(candidates, model, version)

    verdicts: dict[str, str]   = {}
    ratings:  dict[str, float] = {}
    reasons:  dict[str, str]   = {}
    for idx, c in enumerate(candidates):
        entry = result.get(str(idx + 1))
        if not isinstance(entry, dict):
            # Missing per-candidate verdict → keep (flag), never reject.
            verdicts[c], ratings[c], reasons[c] = 'flag', 3.0, ''
            continue
        try:
            rating = float(entry.get('rating'))
        except (TypeError, ValueError):
            verdicts[c], ratings[c], reasons[c] = 'flag', 3.0, ''
            continue
        verdicts[c] = likert_to_verdict(rating)
        ratings[c]  = rating
        reasons[c]  = str(entry.get('reason', ''))[:200]

    return {
        'verdicts': verdicts,
        'ratings':  ratings,
        'reasons':  reasons,
        'model':    model,
        'version':  version,
        'ok':       True,
    }


def _load_cfg(db, language_id: int) -> dict:
    if language_id not in _cfg_cache:
        _cfg_cache[language_id] = get_template_config(db, _PT_NAME, language_id)
    return _cfg_cache[language_id]


def _failopen(candidates: list[str], model: str, version: int) -> dict:
    return {
        'verdicts': {c: 'accept'      for c in candidates},
        'ratings':  {c: _KEEP_RATING  for c in candidates},
        'reasons':  {c: ''            for c in candidates},
        'model':    model,
        'version':  version,
        'ok':       False,
    }


def _empty_meta(model: str, version: int) -> dict:
    return {
        'rejected': 0, 'kept': 0, 'rejected_items': [],
        'model': model, 'version': version,
    }
