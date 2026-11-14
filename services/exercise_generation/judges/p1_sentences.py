"""
P1 sentence-corpus judge — the highest-leverage ladder judge.

Prompt 1 emits the ~10 base sentences that every downstream ladder level
(L3-L9) draws from. A single bad sentence — wrong sense, off-register, target
not a whole word / whole sense — silently poisons every level that inherits it,
and P1 (unlike P2/P3) has no judge. This judge rules on each sentence before the
variant fan-out so the pipeline can flag (and attempt to repair) the bad ones.

Three checks per sentence, folded into one Likert rating:
  - sense-match  : the target carries the intended sense (sense_fingerprint),
                   not a homonym or a different sense.
  - register     : the sentence's formality matches the declared register.
  - whole-sense  : the target appears as a discrete whole word doing the
                   sense's job, not as a substring or an incidental other sense.

Verdict shape (per sentence), 5-point Likert via ``likert_to_verdict``:
    rating 5 / 4 -> accept      3 -> flag      2 / 1 -> reject

Failure-safe contract (mirrors the other judges): any error — missing template,
LLM failure, malformed or length-mismatched response — yields
``[safe_accept() for _ in sentences]``. The judge behaves as if it were absent;
it never blocks the pipeline. The caller logs the underlying error.
"""

from __future__ import annotations

from services.llm_service import call_llm
from services.prompt_service import get_template_config  # noqa: F401 — resolved by the runner

from .base import (
    JudgeOutcome, JudgeSpec, llm_call_kwargs, numbered, run_likert_judge,
    log_judge_verdict,  # noqa: F401 — resolved by the runner
)

_TASK_NAME = 'judge_ladder_p1_sentence'    # label in llm_calls (judge_ prefix)
_PT_NAME   = 'ladder_p1_sentence_judge'    # task_name in prompt_templates

_cfg_cache: dict[int, dict] = {}           # language_id -> cfg dict


def _ask(spec, prompt, cfg, language_id):
    return call_llm(prompt, **llm_call_kwargs(spec, cfg, language_id))


_SPEC = JudgeSpec(
    name='p1_sentence_judge', module=__name__,
    task_name=_TASK_NAME, pt_name=_PT_NAME, ask=_ask,
)


def judge_p1_sentences(
    db,
    lemma: str,
    definition: str,
    sense_fingerprint: str,
    register: str,
    sentences: list[str],
    language_id: int,
) -> list[JudgeOutcome]:
    """Rule on each P1 sentence; return one JudgeOutcome per sentence, in order.

    ``sentences`` is the ordered list of sentence *texts* (not the sentence
    dicts). The returned list is always exactly ``len(sentences)`` long and
    index-aligned, so the caller can map a verdict straight back to a sentence
    index without any renumbering — see the index-stability constraint in
    ``VocabAssetPipeline``.

    On any error returns ``[safe_accept() for _ in sentences]`` and logs a
    warning. ``confidence`` carries the raw 1-5 Likert rating.
    """
    if not sentences:
        return []

    return run_likert_judge(
        _SPEC, db, language_id, len(sentences),
        lambda template: template.format(
            lemma=lemma,
            definition=definition or '(none provided)',
            sense_fingerprint=sense_fingerprint or '(none provided)',
            register=register or 'neutral',
            sentences_numbered=numbered(sentences),
        ),
    )
