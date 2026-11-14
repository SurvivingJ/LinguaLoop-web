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
``(kept, judge_meta)``. Fail-open outside ``batch_mode()`` — any error
(missing template, LLM failure, malformed response) keeps every distractor
and logs a warning. Fail-closed inside it, via ``guard_fail_open`` (TASK-510).
"""

from __future__ import annotations

from services.llm_service import call_llm
from services.prompt_service import get_template_config  # noqa: F401 — resolved by the runner

from .base import JudgeSpec, llm_call_kwargs, numbered, run_keep_reject_judge

_TASK_NAME = 'judge_ladder_l1_distractor'   # label in llm_calls
_PT_NAME   = 'ladder_l1_distractor_judge'   # task_name in prompt_templates

_cfg_cache: dict[int, dict] = {}            # language_id -> cfg dict


def _ask(spec, prompt, cfg, language_id):
    return call_llm(
        prompt,
        # RE-DERIVED 2026-10-03 (ADR-028 cost work): TASK-812's 14000 was
        # sized against a p99 that was inflated by reasoning tokens
        # (qwen reasoning is now OFF). With reasoning off,
        # data/eval/runs/phase2_bundle_*/ + phase2_fix_*/ +
        # phase2_smoke_ja_v3/ + phase2_smoke_zh_r/ *.json llm_calls for
        # judge_ladder_l1_distractor show completion_tokens pooled
        # across languages: n=73, p99=121, max=121 (en, n=34, governs;
        # ja n=38 tops out at 75; zh n=1 is sparse but smaller, not the
        # governing case). cap = max(ceil(p99*2), ceil(max*1.25)) = 242,
        # rounded up to 250. At gemini-3.5-flash-lite's $2.50/M
        # completion price (en's model) this cuts the worst-case
        # reservation from ~$0.035/request to ~$0.001/request.
        max_tokens=250,
        **llm_call_kwargs(spec, cfg, language_id),
    )


_SPEC = JudgeSpec(
    name='l1_distractor_judge', module=__name__,
    task_name=_TASK_NAME, pt_name=_PT_NAME, ask=_ask,
)


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
        return {'verdicts': {}, 'reasons': {}, 'model': 'unknown', 'version': 0}

    return run_keep_reject_judge(
        _SPEC, db, language_id, distractors,
        lambda template: template.format(
            target=target, distractors_numbered=numbered(distractors),
        ),
        fallback_model=model,
    )


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
