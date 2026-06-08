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

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

from services.test_generation.schemas import likert_to_verdict
from .base import JudgeOutcome, safe_accept, log_judge_verdict

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_ladder_p1_sentence'    # label in llm_calls (judge_ prefix)
_PT_NAME   = 'ladder_p1_sentence_judge'    # task_name in prompt_templates
_PIPELINE  = 'vocab_ladder'

_cfg_cache: dict[int, dict] = {}           # language_id -> cfg dict

_VERDICT_ORDER = {'reject': 0, 'flag': 1, 'accept': 2}  # lower = worse


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

    n = len(sentences)

    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "p1_sentence_judge: template load failed for lang=%d, safe-accept all: %s",
            language_id, exc,
        )
        return [safe_accept(f'template load error: {exc}') for _ in sentences]

    sentences_numbered = '\n'.join(f'{i + 1}. {s}' for i, s in enumerate(sentences))
    prompt = cfg['template'].format(
        lemma=lemma,
        definition=definition or '(none provided)',
        sense_fingerprint=sense_fingerprint or '(none provided)',
        register=register or 'neutral',
        sentences_numbered=sentences_numbered,
    )

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
            "p1_sentence_judge: LLM call failed for lang=%d, safe-accept all: %s",
            language_id, exc,
        )
        return [safe_accept(f'llm call error: {exc}') for _ in sentences]

    if not isinstance(result, dict):
        logger.warning(
            "p1_sentence_judge: non-dict response (%s), safe-accept all",
            type(result).__name__,
        )
        return [safe_accept('non-dict judge response') for _ in sentences]

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

    # Log the worst verdict across the corpus — it's the binding signal for the
    # asset as a whole (one row per call) so the smoke-test query can count
    # accept/flag/reject by task_name LIKE 'judge_ladder_%'.
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
