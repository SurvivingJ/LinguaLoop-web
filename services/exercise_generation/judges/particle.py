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

import logging

from services.exercise_generation.schemas import (
    JUDGE_RATING_KEY, JUDGE_REASON_KEY, read_index,
)
from services.llm_service import call_llm
from services.prompt_service import get_template_config
from services.test_generation.schemas import likert_to_verdict

from .base import JudgeOutcome, accept_item, guard_fail_open, log_judge_verdict

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_ladder_particle'      # label in llm_calls (judge_ prefix)
_PT_NAME = 'ladder_particle_judge'        # task_name in prompt_templates
_PIPELINE = 'vocab_ladder'

_cfg_cache: dict[int, dict] = {}

_KEEP_RATING = 5.0


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
        return [], _empty_meta('unknown', 0)

    judged = _judge_candidates(
        db, sentence_with_blank, correct_particle, foils, language_id,
    )
    verdicts = judged['verdicts']
    kept = [f for f in foils if verdicts.get(f) != 'reject']
    rejected = [f for f in foils if verdicts.get(f) == 'reject']
    return kept, {
        'rejected': len(rejected),
        'kept': len(kept),
        'rejected_items': rejected,
        'model': judged['model'],
        'version': judged['version'],
    }


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
    outcome = JudgeOutcome(
        verdict=judged['verdicts'].get(candidate, 'flag'),
        confidence=judged['ratings'].get(candidate, _KEEP_RATING),
        reason=judged['reasons'].get(candidate, ''),
    )
    if judged['ok']:
        log_judge_verdict(
            task_name=_TASK_NAME, model=judged['model'],
            verdict=outcome.verdict, confidence=outcome.confidence,
            pipeline=_PIPELINE,
        )
    return outcome


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _judge_candidates(
    db, sentence_with_blank: str, correct_particle: str,
    candidates: list[str], language_id: int,
) -> dict:
    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            'particle_judge: template load failed for lang=%d, fail-open: %s',
            language_id, exc,
        )
        return _failopen(candidates, 'unknown', 0)

    numbered = '\n'.join(f'{i + 1}. {c}' for i, c in enumerate(candidates))
    prompt = cfg['template'].format(
        sentence_with_blank=sentence_with_blank,
        correct_particle=correct_particle,
        candidates_numbered=numbered,
    )
    model, version = cfg['model'], cfg['version']

    try:
        result = call_llm(
            prompt,
            model=model,
            temperature=0.0,
            # Provider-enforced JSON: a prose answer fails open and keeps every
            # candidate, which is the expensive failure for a uniqueness judge.
            response_format='json_object',
            provider=cfg['provider'],
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=version,
        )
    except Exception as exc:
        logger.warning('particle_judge: LLM call failed, fail-open: %s', exc)
        return _failopen(candidates, model, version)

    if not isinstance(result, dict):
        logger.warning(
            'particle_judge: non-dict response (%s), fail-open',
            type(result).__name__,
        )
        return _failopen(candidates, model, version)

    verdicts: dict[str, str] = {}
    ratings: dict[str, float] = {}
    reasons: dict[str, str] = {}
    for idx, candidate in enumerate(candidates):
        # Top level stays keyed by 1-based candidate number; inside an entry
        # the numeric contract applies — 0=rating, 1=reason.
        entry = read_index(result, idx + 1)
        if not isinstance(entry, dict):
            verdicts[candidate], ratings[candidate], reasons[candidate] = 'flag', 3.0, ''
            continue
        try:
            rating = float(read_index(entry, JUDGE_RATING_KEY))
        except (TypeError, ValueError):
            verdicts[candidate], ratings[candidate], reasons[candidate] = 'flag', 3.0, ''
            continue
        verdicts[candidate] = likert_to_verdict(rating)
        ratings[candidate] = rating
        reasons[candidate] = str(read_index(entry, JUDGE_REASON_KEY) or '')[:200]

    return {
        'verdicts': verdicts, 'ratings': ratings, 'reasons': reasons,
        'model': model, 'version': version, 'ok': True,
    }


def _load_cfg(db, language_id: int) -> dict:
    if language_id not in _cfg_cache:
        _cfg_cache[language_id] = get_template_config(db, _PT_NAME, language_id)
    return _cfg_cache[language_id]


def _failopen(candidates: list[str], model: str, version: int) -> dict:
    # In a generation batch this raises instead of returning (TASK-510).
    guard_fail_open('particle_judge', f'model={model!r} version={version}')
    return {
        'verdicts': {c: 'accept' for c in candidates},
        'ratings': {c: _KEEP_RATING for c in candidates},
        'reasons': {c: '' for c in candidates},
        'model': model, 'version': version, 'ok': False,
    }


def _empty_meta(model: str, version: int) -> dict:
    return {
        'rejected': 0, 'kept': 0, 'rejected_items': [],
        'model': model, 'version': version,
    }
