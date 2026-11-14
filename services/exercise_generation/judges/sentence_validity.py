"""
Sentence-validity judge — serves L6 (semantic discrimination) and L7 (spot the
incorrect sentence).

L6 shows ONE correct sentence among THREE crafted-wrong ones and asks the
learner to find the correct one; L7 shows several correct sentences and ONE
crafted-wrong one and asks the learner to spot the wrong one. In both, every
"wrong" sentence is generated to be wrong for a SPECIFIC labeled reason (its
explanation / error_description). The exercise breaks in two ways the structural
validators cannot see:
  (a) the "wrong" sentence is actually grammatical / acceptable — there is then
      no single correct answer (L6) or nothing to spot (L7);
  (b) the sentence IS wrong, but for a DIFFERENT reason than the one labeled, so
      the explanation shown to the learner is misleading.

This judge rules, per candidate sentence: is it wrong ONLY for its labeled
reason? It rejects a sentence that is actually fine, or that is mislabeled.

Per project convention (tasklist decision 7 / memory ``distractor-judge-v3-likert``)
the judge reports a 5-point Likert ``rating`` per sentence — never a raw
0.0-1.0 float — mapped to a verdict by ``schemas.likert_to_verdict``:

    rating 5 / 4 -> accept      3 -> flag      2 / 1 -> reject

The rating measures how cleanly the sentence is wrong for its labeled reason:
  5 = clearly wrong, and precisely for the labeled reason (ideal);
  4 = wrong for the labeled reason, minor doubt;
  3 = borderline;
  2 = wrong, but for a DIFFERENT reason than labeled (mislabeled);
  1 = actually acceptable / grammatical — not wrong at all (unusable).

Output schema (per sentence, numbered from 1)::

    {"1": {"rating": 1-5, "reason": "..."}, ...}

Failure-safe contract (mirrors the other judges): any error — missing template,
LLM failure, malformed or length-mismatched response — yields
``[safe_accept() for _ in sentences_with_reasons]``. The judge behaves as if it
were absent; it never blocks generation. The caller logs the underlying error.
"""

from __future__ import annotations

from services.llm_service import call_llm
from services.prompt_service import get_template_config  # noqa: F401 — resolved by the runner

from .base import (
    JudgeOutcome, JudgeSpec, llm_call_kwargs, run_likert_judge,
    log_judge_verdict,  # noqa: F401 — resolved by the runner
)

_TASK_NAME = 'judge_ladder_sentence_validity'   # label in llm_calls (judge_ prefix)
_PT_NAME   = 'ladder_sentence_validity_judge'   # task_name in prompt_templates

_cfg_cache: dict[int, dict] = {}                # language_id -> cfg dict


def _ask(spec, prompt, cfg, language_id):
    return call_llm(
        prompt,
        # RE-DERIVED 2026-10-03 (ADR-028 cost work): TASK-812's 16000 was
        # itself still oversized -- that baseline's p99=5247 was inflated
        # by reasoning tokens the qwen rows no longer emit (reasoning is
        # now OFF). With reasoning off, data/eval/runs/phase2_bundle_*/
        # + phase2_fix_*/ + phase2_smoke_ja_v3/ + phase2_smoke_zh_r/
        # *.json llm_calls for judge_ladder_sentence_validity show
        # completion_tokens pooled across languages: n=71, p99=146,
        # max=147 (en, n=68, governs; ja n=1 and zh n=2 are both smaller
        # and sparse, consistent with/bounded by en). cap =
        # max(ceil(p99*2), ceil(max*1.25)) = 292, rounded up to 300. At
        # gemini-3.5-flash-lite's $2.50/M completion price (en's model)
        # this cuts the worst-case reservation from ~$0.040/request to
        # ~$0.001/request.
        max_tokens=300,
        **llm_call_kwargs(spec, cfg, language_id),
    )


_SPEC = JudgeSpec(
    name='sentence_validity_judge', module=__name__,
    task_name=_TASK_NAME, pt_name=_PT_NAME, ask=_ask,
)


def judge_wrong_sentences(
    db,
    target: str,
    sentences_with_reasons: list[tuple[str, str]],
    language_id: int,
) -> list[JudgeOutcome]:
    """Rule on each crafted-wrong sentence; one JudgeOutcome per item, in order.

    ``sentences_with_reasons`` is an ordered list of ``(sentence_text,
    labeled_reason)`` pairs — the wrong sentence and the reason it is supposed to
    be wrong (its explanation / error_description). The returned list is always
    exactly ``len(sentences_with_reasons)`` long and index-aligned.

    ``accept`` → the sentence is cleanly wrong for its labeled reason (keep it);
    ``reject`` → the sentence is actually acceptable, or wrong for a different
    reason than labeled (drop it); ``flag`` → borderline (keep + surface).
    ``confidence`` carries the raw 1-5 Likert rating.

    On any error returns ``[safe_accept() for _ in sentences_with_reasons]`` and
    logs a warning.
    """
    if not sentences_with_reasons:
        return []

    pairs_numbered = '\n'.join(
        f'{i + 1}. Sentence: "{s}"\n   Labeled reason it is wrong: {r or "(none given)"}'
        for i, (s, r) in enumerate(sentences_with_reasons)
    )
    return run_likert_judge(
        _SPEC, db, language_id, len(sentences_with_reasons),
        lambda template: template.format(target=target, pairs_numbered=pairs_numbered),
    )
