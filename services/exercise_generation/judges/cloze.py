"""
Cloze distractor judge — refactored into the judges package.

Replaces the flat ``services.exercise_generation.cloze_judge`` module.
Public API is identical so the backward-compat shim in ``cloze_judge.py``
can re-export without any caller changes.

Key differences from the original:
- Model is loaded from ``prompt_templates`` via ``get_template_config``, and is
  routed per-language. No hardcoded ``DEFAULT_JUDGE_MODEL`` constant. The slugs
  are deliberately NOT listed here: they have rotated repeatedly (the gemini arm
  alone went 2.5-flash-lite -> 3.5-flash-lite on 2026-08-16) and a comment
  restating them just rots. Query prompt_templates for the live values.
- Calls ``services.llm_service.call_llm`` (unified service) so cloze judge
  calls appear in ``llm_calls`` with ``pipeline='vocab_ladder'``,
  ``task_name='cloze_distractor_judge'``, and the per-language model.
- Failure mode: fail-open outside ``batch_mode()`` (any error →
  safe-default-keep, act as if the judge wasn't there); fail-closed inside
  it, via ``guard_fail_open`` — see TASK-510 / an armB_ja eval run
  (2026-10-04) where a stale model slug 404'd on every cloze call and this
  judge, not yet wired into the batch-mode contract, silently shipped every
  cloze exercise unjudged.
"""

from __future__ import annotations

from services.llm_service import call_llm
from services.prompt_service import get_template_config  # noqa: F401 — resolved by the runner

from .base import JudgeSpec, llm_call_kwargs, numbered, run_keep_reject_judge

_TASK_NAME = 'cloze_distractor_judge'

# Simple in-process cache: (task_name, language_id) → cfg dict
_cfg_cache: dict[tuple[str, int], dict] = {}


def _ask(spec, prompt, cfg, language_id):
    return call_llm(
        prompt,
        # RE-DERIVED 2026-10-03 (ADR-028 cost work): data/eval/runs/
        # phase2_bundle_*/ + phase2_fix_*/ + phase2_smoke_ja_v3/ +
        # phase2_smoke_zh_r/ *.json llm_calls for cloze_distractor_judge
        # (reasoning off): n=40 pooled, p99=128, max=128 (en, n=38,
        # governs; zh n=2 is sparse but smaller). cap =
        # max(ceil(p99*2), ceil(max*1.25)) = 256, rounded up to 300 --
        # still >=2x TASK-812's own p99 measurement. At
        # gemini-3.5-flash-lite's $2.50/M completion price (en's model)
        # this cuts the worst-case reservation from ~$0.003/request to
        # ~$0.0009/request.
        max_tokens=300,
        **llm_call_kwargs(spec, cfg, language_id),
    )


_SPEC = JudgeSpec(
    name='cloze_judge', module=__name__,
    task_name=_TASK_NAME, pt_name=_TASK_NAME, ask=_ask,
    provider='openrouter', keyed_cache=True,
)


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
        return {'verdicts': {}, 'reasons': {}, 'model': 'unknown', 'version': 0}

    return run_keep_reject_judge(
        _SPEC, db, language_id, distractors,
        lambda template: template.format(
            sentence_with_blank=sentence_with_blank,
            correct_answer=correct_answer,
            distractors_numbered=numbered(distractors),
        ),
        fallback_model=model,
    )


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
