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

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

from services.test_generation.schemas import likert_to_verdict
from .base import JudgeOutcome, safe_accept, log_judge_verdict

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_ladder_sentence_validity'   # label in llm_calls (judge_ prefix)
_PT_NAME   = 'ladder_sentence_validity_judge'   # task_name in prompt_templates
_PIPELINE  = 'vocab_ladder'

_cfg_cache: dict[int, dict] = {}                # language_id -> cfg dict

_VERDICT_ORDER = {'reject': 0, 'flag': 1, 'accept': 2}  # lower = worse


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

    n = len(sentences_with_reasons)

    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "sentence_validity_judge: template load failed for lang=%d, safe-accept all: %s",
            language_id, exc,
        )
        return [safe_accept(f'template load error: {exc}') for _ in sentences_with_reasons]

    pairs_numbered = '\n'.join(
        f'{i + 1}. Sentence: "{s}"\n   Labeled reason it is wrong: {r or "(none given)"}'
        for i, (s, r) in enumerate(sentences_with_reasons)
    )
    prompt = cfg['template'].format(target=target, pairs_numbered=pairs_numbered)

    try:
        result = call_llm(
            prompt,
            model=cfg['model'],
            temperature=0.0,
            response_format='json',
            provider=cfg['provider'],
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=cfg['version'],
        )
    except Exception as exc:
        logger.warning(
            "sentence_validity_judge: LLM call failed for lang=%d, safe-accept all: %s",
            language_id, exc,
        )
        return [safe_accept(f'llm call error: {exc}') for _ in sentences_with_reasons]

    if not isinstance(result, dict):
        logger.warning(
            "sentence_validity_judge: non-dict response (%s), safe-accept all",
            type(result).__name__,
        )
        return [safe_accept('non-dict judge response') for _ in sentences_with_reasons]

    outcomes: list[JudgeOutcome] = []
    for i in range(n):
        entry = result.get(str(i + 1))
        if not isinstance(entry, dict):
            # A missing or malformed per-sentence verdict must never manufacture
            # a rejection — keep the sentence (safe-accept) and move on.
            outcomes.append(safe_accept('missing per-sentence verdict'))
            continue
        try:
            rating = float(entry.get('rating'))
        except (TypeError, ValueError):
            outcomes.append(safe_accept('unparseable rating'))
            continue
        outcomes.append(JudgeOutcome(
            verdict=likert_to_verdict(rating),
            confidence=rating,
            reason=str(entry.get('reason', ''))[:200],
        ))

    # Log the worst verdict across the batch — one row per call — so the
    # smoke-test query can count accept/flag/reject by task_name
    # LIKE 'judge_ladder_%'.
    worst = min(outcomes, key=lambda o: _VERDICT_ORDER.get(o.verdict, 2))
    log_judge_verdict(
        task_name=_TASK_NAME,
        model=cfg['model'],
        verdict=worst.verdict,
        confidence=worst.confidence,
        pipeline=_PIPELINE,
    )

    return outcomes


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _load_cfg(db, language_id: int) -> dict:
    if language_id not in _cfg_cache:
        _cfg_cache[language_id] = get_template_config(db, _PT_NAME, language_id)
    return _cfg_cache[language_id]
