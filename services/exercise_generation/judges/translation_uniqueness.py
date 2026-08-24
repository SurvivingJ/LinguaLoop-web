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
from services.prompt_service import get_template_config

from services.test_generation.schemas import likert_to_verdict
from .base import JudgeOutcome, guard_fail_open, log_judge_verdict, safe_accept

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_translation_uniqueness'      # label in llm_calls
_PT_NAME   = 'translation_uniqueness_judge'      # task_name in prompt_templates
_PIPELINE  = 'vocab_ladder'

_cfg_cache: dict[int, dict] = {}                 # language_id -> cfg dict

_KEEP_RATING = 5.0

# language_id → llm_calls.language_code — see answer_entailment.py. This is
# the study/target language (language_id), not nl_language_code (the
# learner's native language, used only for a prompt placeholder below).
_LANG_ID_TO_CODE: dict[int, str] = {1: 'zh', 2: 'en', 3: 'ja'}

# An MCQ wants three wrong answers, but a translation item with two plausible
# distractors is still a usable question; below that the learner is choosing
# from a pair and the item is noise. Blocking rather than padding is
# deliberate — a padded distractor is how also-correct options got in.
MIN_SURVIVING_DISTRACTORS = 2


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
        return [], _empty_meta('unknown', 0)

    judged = _judge_candidates(
        db, tl_sentence, correct_translation, distractors,
        language_id, nl_language_code,
    )
    verdicts = judged['verdicts']
    kept     = [d for d in distractors if verdicts.get(d) != 'reject']
    rejected = [d for d in distractors if verdicts.get(d) == 'reject']

    if rejected:
        logger.info(
            "translation_uniqueness: dropped %d/%d also-acceptable distractor(s)",
            len(rejected), len(distractors),
        )
    log_judge_verdict(
        task_name=_TASK_NAME,
        model=judged['model'],
        verdict='reject' if rejected else 'accept',
        confidence=float(len(kept)),
        pipeline=_PIPELINE,
    )

    return kept, {
        'rejected':       len(rejected),
        'kept':           len(kept),
        'rejected_items': rejected,
        'model':          judged['model'],
        'version':        judged['version'],
    }


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


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _judge_candidates(
    db,
    tl_sentence: str,
    correct_translation: str,
    candidates: list[str],
    language_id: int,
    nl_language_code: str,
) -> dict:
    """Run the uniqueness prompt over a numbered candidate list.

    Returns ``{'verdicts', 'ratings', 'reasons', 'model', 'version', 'ok'}``.
    ``ok`` is False on any fail-open path, in which case every candidate is
    reported as ``accept`` so nothing is dropped on a judge outage.
    """
    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "translation_uniqueness: template load failed for lang=%d, "
            "fail-open: %s", language_id, exc,
        )
        return _failopen(candidates, 'unknown', 0)

    numbered = '\n'.join(f'{i + 1}. {c}' for i, c in enumerate(candidates))
    prompt = cfg['template'].format(
        tl_sentence=tl_sentence,
        correct_translation=correct_translation or '(none provided)',
        nl_language=nl_language_code or 'the learner native language',
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
            language_code=_LANG_ID_TO_CODE.get(language_id),
        )
    except Exception as exc:
        logger.warning("translation_uniqueness: LLM call failed, fail-open: %s", exc)
        return _failopen(candidates, model, version)

    if not isinstance(result, dict):
        logger.warning(
            "translation_uniqueness: non-dict response (%s), fail-open",
            type(result).__name__,
        )
        return _failopen(candidates, model, version)

    verdicts: dict[str, str]   = {}
    ratings:  dict[str, float] = {}
    reasons:  dict[str, str]   = {}
    for idx, candidate in enumerate(candidates):
        entry = result.get(str(idx + 1))
        if not isinstance(entry, dict):
            verdicts[candidate], ratings[candidate], reasons[candidate] = 'flag', 3.0, ''
            continue
        try:
            rating = float(entry.get('rating'))
        except (TypeError, ValueError):
            verdicts[candidate], ratings[candidate], reasons[candidate] = 'flag', 3.0, ''
            continue
        verdicts[candidate] = likert_to_verdict(rating)
        ratings[candidate]  = rating
        reasons[candidate]  = str(entry.get('reason', ''))[:200]

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
    # In a generation batch this raises rather than returning — an unreachable
    # judge must abort the batch, not ship unjudged translation items (TASK-510).
    guard_fail_open('translation_uniqueness', f'model={model!r} version={version}')
    return {
        'verdicts': {c: 'accept'     for c in candidates},
        'ratings':  {c: _KEEP_RATING for c in candidates},
        'reasons':  {c: ''           for c in candidates},
        'model':    model,
        'version':  version,
        'ok':       False,
    }


def _empty_meta(model: str, version: int) -> dict:
    return {
        'rejected': 0, 'kept': 0, 'rejected_items': [],
        'model': model, 'version': version,
    }


__all__ = [
    'MIN_SURVIVING_DISTRACTORS',
    'filter_translation_distractors',
    'judge_translation_item',
    'safe_accept',
]
