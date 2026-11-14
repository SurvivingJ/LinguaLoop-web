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

from services.llm_service import call_llm
from services.prompt_service import get_template_config  # noqa: F401 — resolved by the runner

from .base import (
    JudgeOutcome, JudgeSpec, accept_item, candidate_outcome, empty_meta,
    llm_call_kwargs, log_verdict, numbered, run_candidate_judge, safe_accept,
    split_rejected,
    log_judge_verdict,  # noqa: F401 — resolved by the runner
)

_TASK_NAME = 'judge_ladder_collocation'    # label in llm_calls (judge_ prefix)
_PT_NAME   = 'ladder_collocation_judge'    # task_name in prompt_templates

_cfg_cache: dict[int, dict] = {}           # language_id -> cfg dict


def _ask(spec, prompt, cfg, language_id):
    return call_llm(
        prompt,
        # RE-DERIVED 2026-10-03 (ADR-028 cost work): this task_name's own
        # measured sample is still too thin to derive a cap from alone
        # (data/eval/runs/phase2_bundle_*/ + phase2_fix_*/ +
        # phase2_smoke_ja_v3/ + phase2_smoke_zh_r/ *.json llm_calls:
        # judge_ladder_collocation n=5, en-only, p99=28, max=28 -- no
        # ja/zh rows at all), so this borrows the pooled distribution of
        # the other short structured-JSON Likert judges it was already
        # being sized against (cloze_distractor_judge,
        # judge_ladder_l1_distractor, judge_ladder_relation/word_family,
        # judge_ladder_particle, judge_ladder_sentence_validity): n=321
        # pooled, p99=128, max=147. cap = max(ceil(p99*2), ceil(max*1.25))
        # = 256, rounded up to 300, matching cloze/l1's own re-derived
        # caps. At gemini-3.5-flash-lite's $2.50/M completion price
        # (this judge's model) this cuts the worst-case reservation from
        # ~$0.004/request to ~$0.0009/request.
        max_tokens=300,
        **llm_call_kwargs(spec, cfg, language_id),
    )


_SPEC = JudgeSpec(
    name='collocation_judge', module=__name__,
    task_name=_TASK_NAME, pt_name=_PT_NAME, ask=_ask,
)


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
    1-2 = an also-valid collocate), so a missing/uncertain verdict keeps it.
    Fail-open: any error keeps every distractor.
    """
    if not distractors:
        return [], empty_meta()

    judged = _judge_candidates(
        db, sentence, target, correct_collocate, distractors, language_id,
    )
    return split_rejected(distractors, judged)


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
        # Nothing to judge is not a judge outage — never abort a batch for it.
        return accept_item('no error_collocate to judge')

    judged = _judge_candidates(
        db, sentence, target, correct_collocate, [error_collocate], language_id,
    )
    if not judged['ok']:
        # The runner already logged the underlying error.
        return safe_accept('collocation judge unavailable — safe-accept')

    outcome = candidate_outcome(judged, error_collocate)
    log_verdict(_SPEC, judged['model'], outcome.verdict, outcome.confidence)
    return outcome


def _judge_candidates(
    db,
    sentence: str,
    target: str,
    correct_collocate: str,
    candidates: list[str],
    language_id: int,
) -> dict:
    """Run the shared collocation prompt over a numbered candidate list."""
    return run_candidate_judge(
        _SPEC, db, language_id, candidates,
        lambda template: template.format(
            sentence=sentence,
            target=target,
            correct_collocate=correct_collocate or '(none provided)',
            candidates_numbered=numbered(candidates),
        ),
    )
