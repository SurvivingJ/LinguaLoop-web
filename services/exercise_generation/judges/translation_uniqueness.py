"""
Translation uniqueness judge (TASK-525).

The eval scored tl_nl at 0% accept, and the cause was not bad translation — it
was bad *distractors*. A multiple-choice translation item is only well-formed
when exactly one option is an acceptable rendering of the TL sentence. The
generator routinely produced two or three, so a correct learner could be marked
wrong. Before scaling translation types to ZH and JA, that has to be caught.

The question asked, per distractor: *given this TL sentence and its keyed
translation, is this option ALSO an acceptable translation?*

**Rating orientation — read before editing the prompt.** As with the
collocation judge, the Likert scale runs in the direction of *keep*, so that
``likert_to_verdict`` needs no inversion here or in the prompt seeds:

    5 = clearly NOT an acceptable translation  -> ideal distractor -> accept
    3 = arguable                               -> flag  -> kept, surfaced
    1 = a fully acceptable rendering           -> also-correct     -> reject

    rating 5 / 4 -> accept      3 -> flag      2 / 1 -> reject

Getting this backwards would silently keep exactly the distractors the judge
exists to remove, and the item would still look well-formed, so the orientation
is asserted in tests/test_translation_uniqueness_judge.py rather than left to
the prompt author.

Output schema (per distractor, numbered from 1)::

    {"1": {"rating": 1-5, "reason": "..."}, ...}

Fail-open, with the TASK-510 caveat: outside a batch an unreachable judge keeps
every distractor and behaves as if absent. Inside a generation batch
``guard_fail_open`` raises instead, because silently shipping unjudged
translation items is the failure mode this task exists to end.

``nl_language_code`` is required and has no default, per TASK-519 — a default
here is how the v1 corpus became English-only, and the AST lint in
tests/test_nl_keyed_content.py fails the build if one reappears.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config  # noqa: F401 — resolved by the runner

from .base import (
    JudgeOutcome, JudgeSpec, empty_meta, llm_call_kwargs, log_verdict, numbered,
    run_candidate_judge, safe_accept, split_rejected,
    log_judge_verdict,  # noqa: F401 — resolved by the runner
)

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_translation_uniqueness'      # label in llm_calls
_PT_NAME   = 'translation_uniqueness_judge'      # task_name in prompt_templates

_cfg_cache: dict[int, dict] = {}                 # language_id -> cfg dict

# An MCQ wants three wrong answers, but a translation item with two plausible
# distractors is still a usable question; below that the learner is choosing
# from a pair and the item is noise. Blocking rather than padding is
# deliberate — a padded distractor is how also-correct options got in.
MIN_SURVIVING_DISTRACTORS = 2


def _ask(spec, prompt, cfg, language_id):
    # language_code is the study/target language (language_id), not
    # nl_language_code (the learner's native language, a prompt placeholder).
    return call_llm(prompt, **llm_call_kwargs(spec, cfg, language_id))


_SPEC = JudgeSpec(
    name='translation_uniqueness', module=__name__,
    task_name=_TASK_NAME, pt_name=_PT_NAME, ask=_ask,
)


def filter_translation_distractors(
    db,
    tl_sentence: str,
    correct_translation: str,
    distractors: list[str],
    language_id: int,
    nl_language_code: str,
) ->tuple[list[str], dict]:
    """Drop distractors that are themselves acceptable translations.

    Returns ``(kept_distractors, judge_meta)``. ``judge_meta`` matches the
    sidecar shape lifted into ``exercises.tags.translation_uniqueness_judge``::

        {"rejected": N, "kept": M, "rejected_items": [...],
         "model": "...", "version": N}

    A distractor is dropped only on a ``reject`` verdict (rating 1-2 = also an
    acceptable translation). A missing or unparseable verdict keeps it.
    """
    if not distractors:
        return [], empty_meta()

    judged = run_candidate_judge(
        _SPEC, db, language_id, distractors,
        lambda template: template.format(
            tl_sentence=tl_sentence,
            correct_translation=correct_translation or '(none provided)',
            nl_language=nl_language_code or 'the learner native language',
            candidates_numbered=numbered(distractors),
        ),
    )
    kept, meta = split_rejected(distractors, judged)

    if meta['rejected']:
        logger.info(
            "translation_uniqueness: dropped %d/%d also-acceptable distractor(s)",
            meta['rejected'], len(distractors),
        )
    log_verdict(
        _SPEC, judged['model'],
        'reject' if meta['rejected'] else 'accept', float(len(kept)),
    )
    return kept, meta


def judge_translation_item(
    db,
    tl_sentence: str,
    correct_translation: str,
    distractors: list[str],
    language_id: int,
    nl_language_code: str,
) ->tuple[list[str], JudgeOutcome, dict]:
    """Whole-item verdict: filter, then decide whether the item survives.

    Returns ``(kept_distractors, outcome, judge_meta)``. ``outcome.verdict`` is
    ``reject`` when fewer than :data:`MIN_SURVIVING_DISTRACTORS` remain — the
    caller must drop the item rather than ship a two-option question.
    ``confidence`` carries the surviving distractor count.
    """
    kept, meta = filter_translation_distractors(
        db, tl_sentence, correct_translation, distractors,
        language_id, nl_language_code,
    )

    if len(kept) < MIN_SURVIVING_DISTRACTORS:
        return kept, JudgeOutcome(
            verdict='reject',
            confidence=float(len(kept)),
            reason=(
                f'only {len(kept)} distractor(s) survived uniqueness '
                f'(need {MIN_SURVIVING_DISTRACTORS}) — item blocked'
            ),
        ), meta

    return kept, JudgeOutcome(
        verdict='accept',
        confidence=float(len(kept)),
        reason=f'{len(kept)} unique distractor(s)',
    ), meta


__all__ = [
    'MIN_SURVIVING_DISTRACTORS',
    'filter_translation_distractors',
    'judge_translation_item',
    'safe_accept',
]
