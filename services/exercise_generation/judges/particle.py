"""Particle-uniqueness judge for the Japanese L4 (TASK-527).

One question, asked per candidate: **with this particle in the blank, is the
sentence natural Japanese?**

That framing is the whole judge. A particle exercise is only answerable if
exactly one of the four options produces a natural sentence, and Japanese is
unusually rich in near-misses that break that property:

* ``に`` / ``へ`` with a motion verb — both grammatical, differing in nuance;
* ``は`` / ``が`` — both grammatical, differing in information structure;
* ``を`` / ``が`` with certain stative predicates — both attested.

A model asked "is this a plausible distractor?" will happily say yes to all
three, because they *are* plausible. Asked "does this also yield a natural
sentence?", it says no only when the particle genuinely breaks the sentence,
which is what the item needs.

Polarity matches the other ladder judges: the rating measures how clearly the
candidate is WRONG in the blank.

    5 = clearly ungrammatical or unnatural here → ideal distractor
    3 = borderline
    1 = also produces a natural sentence → an also-correct answer, drop it

Verdicts come from ``schemas.likert_to_verdict`` (5/4 accept, 3 flag, 2/1
reject) — the same call on the same raw rating as ``judges/relation``, with no
per-judge threshold, which is what makes the polarity shared rather than merely
similar. What differs between the two judges is the *question asked*, not how
the answer is scored. Fail-open outside ``batch_mode()``, fail-closed inside it.

Each entry is numerically keyed (0=rating, 1=reason) per TASK-537; the top
level stays keyed by 1-based candidate number.
"""

from __future__ import annotations

from services.llm_service import call_llm, ladder_qwen_reasoning_mode
from services.prompt_service import get_template_config  # noqa: F401 — resolved by the runner
# Re-exported: tests pin that this judge and judges/relation score with the
# same mapper (the runner applies it to both).
from services.test_generation.schemas import likert_to_verdict  # noqa: F401

from .base import (
    JudgeOutcome, JudgeSpec, accept_item, candidate_outcome, empty_meta,
    llm_call_kwargs, log_verdict, numbered, run_candidate_judge, split_rejected,
    log_judge_verdict,  # noqa: F401 — resolved by the runner
)

_TASK_NAME = 'judge_ladder_particle'      # label in llm_calls (judge_ prefix)
_PT_NAME = 'ladder_particle_judge'        # task_name in prompt_templates

_cfg_cache: dict[int, dict] = {}

# RE-DERIVED 2026-10-03 (ADR-028 cost work): see the right-sized value (200)
# at the call site below. This judge runs on qwen3.7-plus (ja-only), unlike
# the other ladder judges in this package (gemini -- unaffected by reasoning
# state). When `LADDER_QWEN_REASONING=on` (the default) restores Phase-1
# reasoning-left-on behaviour for qwen, reasoning tokens count toward
# `max_tokens` and the right-sized cap would truncate; 9000 was this task's
# own TASK-812 cap before the 2026-10-03 re-derivation.
_MAX_TOKENS_REASONING_SAFE = 9000
_MAX_TOKENS_RIGHTSIZED = 200


def _max_tokens() -> int:
    return (_MAX_TOKENS_REASONING_SAFE if ladder_qwen_reasoning_mode() != 'off'
            else _MAX_TOKENS_RIGHTSIZED)


def _ask(spec, prompt, cfg, language_id):
    return call_llm(
        prompt,
        # RE-DERIVED 2026-10-03 (ADR-028 cost work): TASK-812's 9000 was
        # sized against a ja-only n=6 sample inflated by reasoning tokens
        # (qwen reasoning is now OFF), and the larger ja sample TASK-812
        # asked for now exists. data/eval/runs/phase2_bundle_ja/ +
        # phase2_fix_ja/ + phase2_smoke_ja_v3/ *.json llm_calls for
        # judge_ladder_particle (ja-only task): n=32, p99=87.5, max=90.
        # cap = max(ceil(p99*2), ceil(max*1.25)) = 176, rounded up to
        # 200. At qwen3.7-plus's $1.28/M completion price this cuts the
        # worst-case reservation from ~$0.012/request to
        # ~$0.0005/request. See `_max_tokens()` above for the
        # LADDER_QWEN_REASONING=on fallback to the old 9000.
        max_tokens=_max_tokens(),
        **llm_call_kwargs(spec, cfg, language_id),
    )


_SPEC = JudgeSpec(
    name='particle_judge', module=__name__,
    task_name=_TASK_NAME, pt_name=_PT_NAME, ask=_ask,
    # Provider-enforced JSON: a prose answer fails open and keeps every
    # candidate, which is the expensive failure for a uniqueness judge.
    response_format='json_object',
    numeric_entries=True,
)


def filter_particle_foils(
    db,
    sentence_with_blank: str,
    correct_particle: str,
    foils: list[str],
    language_id: int,
) -> tuple[list[str], dict]:
    """Drop particles that also yield a natural sentence in the blank.

    Returns ``(kept, judge_meta)``; ``judge_meta`` is the sidecar lifted into
    ``exercises.tags.particle_judge``.

    A foil is dropped only on a ``reject`` verdict. A missing or unparseable
    rating keeps it (fail-open, v3 Likert contract) — an item with one
    borderline distractor is a worse item, but an item that vanished because
    a response was truncated is no item at all.
    """
    if not foils:
        return [], empty_meta()

    judged = _judge_candidates(
        db, sentence_with_blank, correct_particle, foils, language_id,
    )
    return split_rejected(foils, judged)


def judge_particle(
    db,
    sentence_with_blank: str,
    correct_particle: str,
    candidate: str,
    language_id: int,
) -> JudgeOutcome:
    """Single-candidate verdict, for the planted-defect test and admin tools."""
    if not candidate:
        return accept_item('no candidate particle to judge')

    judged = _judge_candidates(
        db, sentence_with_blank, correct_particle, [candidate], language_id,
    )
    outcome = candidate_outcome(judged, candidate)
    if judged['ok']:
        log_verdict(_SPEC, judged['model'], outcome.verdict, outcome.confidence)
    return outcome


def _judge_candidates(
    db, sentence_with_blank: str, correct_particle: str,
    candidates: list[str], language_id: int,
) -> dict:
    return run_candidate_judge(
        _SPEC, db, language_id, candidates,
        lambda template: template.format(
            sentence_with_blank=sentence_with_blank,
            correct_particle=correct_particle,
            candidates_numbered=numbered(candidates),
        ),
    )
