"""
L1 listening-distractor judge.

L1 is a LISTENING exercise: the learner hears the target word spoken aloud and
picks the matching written option. Good distractors are real words that are
*audio-confusable* with the target (homophones, minimal pairs, mishearable
rhymes / tone-confusions) but mean something different. This judge drops the
bad ones:
  - not a real word in the language;
  - a synonym / near-synonym of the target (a learner who heard the target
    could justifiably pick it, so it isn't a clean wrong answer);
  - similar to the target only in SPELLING, with no phonetic confusability
    (en "tough"/"though"; zh look-alike chars that are tonally distinct) —
    these defeat the listening skill the level trains.

This polarity holds across every language (project memory: L1 is listening).

Filter shape (mirrors judges/cloze.py): ``filter_l1_distractors`` returns
``(kept, judge_meta)``. Fail-open — any error (missing template, LLM failure,
malformed response) keeps every distractor and logs a warning.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_ladder_l1_distractor'   # label in llm_calls
_PT_NAME   = 'ladder_l1_distractor_judge'   # task_name in prompt_templates
_PIPELINE  = 'vocab_ladder'

_cfg_cache: dict[int, dict] = {}            # language_id -> cfg dict


def judge_l1_distractors(
    db,
    target: str,
    distractors: list[str],
    language_id: int,
    model: str | None = None,   # kept for API compat; DB row takes precedence
) -> dict:
    """Rule keep/reject on each L1 distractor.

    Returns::

        {'verdicts': {distractor: 'keep'|'reject', ...},
         'reasons':  {distractor: short_reason, ...},
         'model': ..., 'version': ...}

    On any error the judge keeps every distractor (act as if it wasn't there).
    """
    if not distractors:
        return _empty_result('unknown', 0)

    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "l1_distractor_judge: template load failed for lang=%d, keep all: %s",
            language_id, exc,
        )
        return _all_keep(distractors, model or 'unknown', 0)

    numbered = '\n'.join(f'{i + 1}. {d}' for i, d in enumerate(distractors))
    prompt = cfg['template'].format(target=target, distractors_numbered=numbered)
    judge_model   = cfg['model']
    judge_version = cfg['version']

    try:
        result = call_llm(
            prompt,
            model=judge_model,
            temperature=0.0,
            response_format='json',
            provider=cfg['provider'],
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=judge_version,
        )
    except Exception as exc:
        logger.warning("l1_distractor_judge: LLM call failed, keep all: %s", exc)
        return _all_keep(distractors, judge_model, judge_version)

    if not isinstance(result, dict):
        logger.warning(
            "l1_distractor_judge: non-dict response (%s), keep all",
            type(result).__name__,
        )
        return _all_keep(distractors, judge_model, judge_version)

    verdicts: dict[str, str] = {}
    reasons:  dict[str, str] = {}
    for idx, d in enumerate(distractors):
        entry = result.get(str(idx + 1)) or {}
        if not isinstance(entry, dict):
            verdicts[d] = 'keep'
            reasons[d]  = ''
            continue
        v = str(entry.get('verdict', 'keep')).strip().lower()
        verdicts[d] = 'reject' if v == 'reject' else 'keep'
        reasons[d]  = str(entry.get('reason', ''))[:200]

    return {
        'verdicts': verdicts,
        'reasons':  reasons,
        'model':    judge_model,
        'version':  judge_version,
    }


def filter_l1_distractors(
    db,
    target: str,
    distractors: list[str],
    language_id: int,
    model: str | None = None,
) -> tuple[list[str], dict]:
    """Convenience wrapper: returns ``(kept_distractors, judge_meta)``.

    ``judge_meta`` matches the generalized sidecar shape lifted into
    ``exercises.tags.l1_distractor_judge``::

        {"rejected": N, "kept": M, "model": "...", "version": N,
         "rejected_items": [...]}
    """
    result   = judge_l1_distractors(db, target, distractors, language_id, model)
    kept     = [d for d in distractors if result['verdicts'].get(d) == 'keep']
    rejected = [d for d in distractors if result['verdicts'].get(d) == 'reject']
    meta     = {
        'rejected':       len(rejected),
        'kept':           len(kept),
        'rejected_items': rejected,
        'model':          result['model'],
        'version':        result['version'],
    }
    return kept, meta


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _load_cfg(db, language_id: int) -> dict:
    if language_id not in _cfg_cache:
        _cfg_cache[language_id] = get_template_config(db, _PT_NAME, language_id)
    return _cfg_cache[language_id]


def _empty_result(model: str, version: int) -> dict:
    return {'verdicts': {}, 'reasons': {}, 'model': model, 'version': version}


def _all_keep(distractors: list[str], model: str, version: int) -> dict:
    return {
        'verdicts': {d: 'keep' for d in distractors},
        'reasons':  {d: ''     for d in distractors},
        'model':    model,
        'version':  version,
    }
