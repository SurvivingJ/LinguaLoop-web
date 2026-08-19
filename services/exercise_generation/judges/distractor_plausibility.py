"""
Distractor plausibility judge.

Verifies that the three distractors are plausible-but-clearly-wrong.
Catches two failure modes Pydantic cannot see:
- A distractor is also a valid correct answer ("oversharp distractors").
- A distractor is so absurd no learner would pick it ("weak distractors").

Usage::

    from services.exercise_generation.judges.distractor_plausibility import (
        judge_distractor_plausibility,
    )
    outcomes = judge_distractor_plausibility(
        db=db,
        passage="...",
        question_text="...",
        answer="correct answer text",
        distractors=["wrong1", "wrong2", "wrong3"],
        language_id=2,
    )
    # outcomes[i].verdict    in ('accept', 'flag', 'reject')
    # outcomes[i].confidence — per-distractor LLM score 0.0–1.0
    # outcomes[i].reason     — explanation in the target language

The judge prompt asks the LLM to rate ALL distractors in a single call and
return one 5-point Likert RATING (1-5) per distractor.  The overall verdict for
the question (used by question_generator.py) is the worst verdict across all
distractors.

Verdict mapping (v4 Likert — see schemas.likert_to_verdict):
    rating 5 / 4  → accept
    rating 3      → flag   (weak, keep + surface for review)
    rating 2 / 1  → reject (drop question; 2 = off-topic, 1 = also-correct/absurd)
    NO rating     → accept, unjudged (accept_item) — NEVER a flag

The last line is load-bearing. Under the v3 prompt the model frequently
returned reasons with no numbers at all, and the schema fabricated a 3 for
each, so 80% of live ratings were 'flag' verdicts nobody had actually made
and the review queue was unusable. A missing rating is now preserved as None
end to end and accepted outright, so the queue only ever contains real 3s.

The Likert scale replaces the v2 raw 0.0-1.0 float, which a small judge model
could not emit consistently (the same option scored 0.80 in one question and
0.20 in another) — it collapsed "absent from the passage" into "off-topic" and
hard-rejected good same-domain distractors.

``type_code`` and ``keywords`` (v5 — TASK-717)
----------------------------------------------
These fill prompt slots ``{4}`` and ``{5}``, and under v5 the prompt finally
ACTS on both. Until v5 neither did anything: ``keywords`` was never passed by
the caller, so ``{5}`` always rendered the "infer the subject" fallback, and
``{4}`` was printed as a bare label with no type-conditional rule in any of
the three languages. This docstring previously claimed the type "lets the
judge treat a vocabulary distractor differently from a literal-detail one" —
that behaviour existed only here, never in the prompt body.

What v5 actually does with them:

* ``keywords`` — the passage's subject/domain. Band 2 ("off-topic") IS a
  domain-membership test, so v5 declares this line authoritative when present.
  Left empty, the prompt falls back to inferring the domain from the passage,
  which is what every production call did through v3 and v4; a model that
  infers narrowly then rejects and one that infers broadly accepts, and that
  is most of the measured zh/en divergence.
* ``type_code`` — selects one of three rubric families, because "same subject
  as the passage" is a category error for half the question types:
    - ``vocabulary_context`` — distractors are competing MEANINGS of the target
      expression, judged against the WORD. An option unrelated to the passage
      topic is NOT off-topic; that is the question.
    - ``author_purpose`` / ``main_idea`` — distractors are competing authorial
      INTENTS. "Off-topic" means an intent unrelated to the text, not a topic
      the passage omits.
    - ``literal_detail`` / ``supporting_detail`` / ``inference`` — distractors
      are same-domain FACTS; the subject test applies as written.

Both remain optional and both must be passed as STRINGS — ``type_code`` has to
match a rubric bullet literally, so an id integer selects nothing. Extra
positional ``format`` args are ignored by templates that don't reference them,
so this stays compatible with older (v2) prompt rows.

The bands and the 1-5 scale are unchanged from v4 and are TASK-719's business.
See wiki/evaluations/distractor-judge-language-divergence-2026-08-16.
"""

from __future__ import annotations

import logging

from services.llm_service import call_llm
from services.prompt_service import get_template_config

from services.test_generation.schemas import (
    DistractorPlausibilityVerdict,
    likert_to_verdict,
)
from .base import JudgeOutcome, accept_item, safe_accept, log_judge_verdict

logger = logging.getLogger(__name__)

_TASK_NAME = 'judge_distractor_plausibility'   # label in llm_calls
_PT_NAME   = 'test_distractor_plausibility'    # task_name in prompt_templates
_PIPELINE  = 'test_gen'

_cfg_cache: dict[int, dict] = {}               # language_id → cfg dict

_VERDICT_ORDER = {'reject': 0, 'flag': 1, 'accept': 2}  # lower = worse


def judge_distractor_plausibility(
    db,
    passage: str,
    question_text: str,
    answer: str,
    distractors: list[str],
    language_id: int,
    type_code: str = '',
    keywords: str = '',
) -> list[JudgeOutcome]:
    """Run the distractor-plausibility judge, one JudgeOutcome per distractor.

    Returns a list of ``len(distractors)`` JudgeOutcome objects in the same
    order as ``distractors``. Each outcome's ``confidence`` carries the raw
    Likert rating (1.0-5.0); ``verdict`` is derived via ``likert_to_verdict``.

    ``type_code`` (the question type, e.g. ``vocabulary_context``) and
    ``keywords`` (the passage's subject/domain) feed prompt placeholders
    ``{4}`` and ``{5}``. Under v5 both are load-bearing — see the module
    docstring for what the prompt does with each, and why passing ``type_code``
    as anything other than the literal code string silently selects no rubric.
    Both are optional; when ``keywords`` is absent the prompt falls back to
    inferring the subject from the passage.

    On any error (missing template, LLM failure, schema error, length
    mismatch) returns ``[safe_accept() for _ in distractors]`` and logs a
    warning — failure mode is "let them all through", not "block the pipeline".
    """
    if not distractors:
        return []

    n = len(distractors)

    try:
        cfg = _load_cfg(db, language_id)
    except Exception as exc:
        logger.warning(
            "distractor_plausibility: failed to load template for lang=%d, safe-accept: %s",
            language_id, exc,
        )
        return [safe_accept(f'template load error: {exc}') for _ in distractors]

    distractors_numbered = '\n'.join(
        f'{i + 1}. {d}' for i, d in enumerate(distractors)
    )
    prompt = cfg['template'].format(
        passage,
        question_text,
        answer,
        distractors_numbered,
        type_code or '(unspecified)',
        keywords or '(infer the subject from the passage above)',
    )

    try:
        verdict_obj: DistractorPlausibilityVerdict = call_llm(
            prompt,
            model=cfg['model'],
            temperature=0.0,
            response_format='json_object',
            schema=DistractorPlausibilityVerdict,
            provider='openrouter',
            pipeline=_PIPELINE,
            task_name=_TASK_NAME,
            template_version=cfg['version'],
        )
    except Exception as exc:
        logger.warning(
            "distractor_plausibility: LLM call failed for lang=%d, safe-accept: %s",
            language_id, exc,
        )
        return [safe_accept(f'llm call error: {exc}') for _ in distractors]

    ratings = verdict_obj.per_distractor
    reasons = verdict_obj.reasons

    # Length-mismatch handling. The schema validator keeps per_distractor and
    # reasons the same length, but that length need not equal n:
    #
    # • TOO MANY (len > n): the judge model intermittently HALLUCINATES extra
    #   distractors — it emits the per-distractor numbered shape with more rows
    #   than asked (e.g. deepseek-v4-flash returning 5 ratings for 3 distractors;
    #   rows 4-5 are duplicates of earlier rows or are explicitly flagged
    #   "this number does not exist"). The real distractors are always rated
    #   FIRST and in order, so truncate the surplus. Falling open here would
    #   accept EVERY distractor (including genuinely bad ones); truncation keeps
    #   the model's real judgment of the n we actually asked about. Measured
    #   ~14% of ja calls (2026-06-06) — too common to silently bypass the judge.
    #
    # • TOO FEW (len < n): we cannot fabricate the missing judgments — safe-accept.
    if len(ratings) > n:
        logger.warning(
            "distractor_plausibility: model returned %d ratings for %d "
            "distractors (lang=%d); truncating %d hallucinated extra(s)",
            len(ratings), n, language_id, len(ratings) - n,
        )
        ratings = ratings[:n]
        reasons = reasons[:n]
    elif len(ratings) < n:
        logger.warning(
            "distractor_plausibility: length mismatch — got %d confidences for "
            "%d distractors, safe-accept all",
            len(ratings), n,
        )
        return [safe_accept('length mismatch in judge response') for _ in distractors]

    # A None rating means the model answered but gave no number for this
    # distractor. That is not a weak distractor and must not become a 'flag':
    # flagging it is what filled the review queue with judgments nobody made.
    # Accept the item outright and log the gap so it stays countable.
    unrated = sum(1 for r in ratings if r is None)
    if unrated:
        logger.warning(
            "distractor_plausibility: model returned NO rating for %d/%d "
            "distractors (lang=%d, model=%s); accepting those unjudged rather "
            "than flagging them",
            unrated, n, language_id, cfg['model'],
        )

    outcomes = [
        accept_item('judge returned no rating for this distractor')
        if rating is None else
        JudgeOutcome(
            verdict=likert_to_verdict(rating),
            confidence=float(rating),  # carries the 1-5 Likert rating
            reason=reasons[i] if i < len(reasons) else '',
        )
        for i, rating in enumerate(ratings)
    ]

    # Log the worst-case verdict for the batch (binding constraint for the
    # question as a whole) so the smoke-test query sees one row per call.
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
