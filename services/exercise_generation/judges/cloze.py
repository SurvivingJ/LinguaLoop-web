"""
Cloze distractor judge — refactored into the judges package.

Replaces the flat ``services.exercise_generation.cloze_judge`` module.
Public API is identical so the backward-compat shim in ``cloze_judge.py``
can re-export without any caller changes.

Key differences from the original:
- Model is loaded from ``prompt_templates`` via ``get_template_config``
  (per-language: zh→deepseek-chat, en→gemini-2.5-flash-lite, ja→qwen-72b).
  No hardcoded ``DEFAULT_JUDGE_MODEL`` constant.
- Calls ``services.llm_service.call_llm`` (unified service) so cloze judge
  calls appear in ``llm_calls`` with ``pipeline='vocab_ladder'``,
  ``task_name='cloze_distractor_judge'``, and the per-language model.
- Failure mode is unchanged: any error → safe-default-keep (act as if the
  judge wasn't there).
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

logger = logging.getLogger(__name__)

_TASK_NAME = 'cloze_distractor_judge'
_PIPELINE  = 'vocab_ladder'

# Simple in-process cache: (task_name, language_id) → cfg dict
_cfg_cache: dict[tuple[str, int], dict] = {}


def judge_distractors(
    db,
    sentence_with_blank: str,
    correct_answer: str,
    distractors: list[str],
    language_id: int,
    model: str | None = None,   # kept for API compat; DB row takes precedence
) -> dict:
    """Rule on each distractor.

    Returns::

        {
          'verdicts': {distractor: 'keep' | 'reject', ...},
          'reasons':  {distractor: short_reason, ...},
          'model':    model_id_used,
          'version':  template_version,
        }

    On any error (template missing, LLM failure, malformed response) the
    judge falls back to keeping every distractor and logs a warning.
    """
    if not distractors:
        return _empty_result('unknown', 0)

    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "cloze_judge: failed to load template/model for lang=%d, keeping all: %s",
            language_id, exc,
        )
        return _all_keep(distractors, model or 'unknown', 0)

    numbered = '\n'.join(f'{i + 1}. {d}' for i, d in enumerate(distractors))
    prompt = cfg['template'].format(
        sentence_with_blank=sentence_with_blank,
        correct_answer=correct_answer,
        distractors_numbered=numbered,
    )
    judge_model   = cfg['model']
    judge_version = cfg['version']

    try:
        result = call_llm(
            prompt,
            model=judge_model,
            temperature=0.0,
            response_format='json',
            provider='openrouter',
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=judge_version,
        )
    except Exception as exc:
        logger.warning("cloze_judge: LLM call failed, keeping all: %s", exc)
        return _all_keep(distractors, judge_model, judge_version)

    if not isinstance(result, dict):
        logger.warning(
            "cloze_judge: non-dict response (%s), keeping all", type(result).__name__
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


def filter_distractors(
    db,
    sentence_with_blank: str,
    correct_answer: str,
    distractors: list[str],
    language_id: int,
    model: str | None = None,
) -> tuple[list[str], dict]:
    """Convenience wrapper: returns ``(kept_distractors, judge_meta)``.

    ``judge_meta`` matches the shape stored under ``exercises.tags.cloze_judge``::

        {"rejected": N, "model": "...", "version": N, "rejected_items": [...]}
    """
    result   = judge_distractors(
        db, sentence_with_blank, correct_answer, distractors, language_id, model,
    )
    kept     = [d for d in distractors if result['verdicts'].get(d) == 'keep']
    rejected = [d for d in distractors if result['verdicts'].get(d) == 'reject']
    meta     = {
        'rejected':       len(rejected),
        'rejected_items': rejected,
        'model':          result['model'],
        'version':        result['version'],
    }
    return kept, meta


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _load_cfg(db, language_id: int) -> dict:
    """Load (template, model, provider, version) with a simple in-process cache."""
    key = (_TASK_NAME, language_id)
    if key not in _cfg_cache:
        _cfg_cache[key] = get_template_config(db, _TASK_NAME, language_id)
    return _cfg_cache[key]


def _empty_result(model: str, version: int) -> dict:
    return {'verdicts': {}, 'reasons': {}, 'model': model, 'version': version}


def _all_keep(distractors: list[str], model: str, version: int) -> dict:
    return {
        'verdicts': {d: 'keep' for d in distractors},
        'reasons':  {d: ''     for d in distractors},
        'model':    model,
        'version':  version,
    }
