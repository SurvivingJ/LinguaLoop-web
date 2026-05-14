"""Cloze distractor judge.

Post-generation verifier that rejects distractors which could themselves
pass as the correct answer in the cloze sentence. Uses a cheap LLM
(default: google/gemini-2.5-flash-lite) keyed to the
`cloze_distractor_judge` prompt template.

Asymmetric design: the cloze generator runs on a strong model (Opus/Qwen),
while the judge runs on a cheap fast model. The judge only needs to rule
in/out, which is well-suited to small verifier models.
"""

import json
import logging

from services.exercise_generation.llm_client import call_llm

logger = logging.getLogger(__name__)

CLOZE_JUDGE_TASK = 'cloze_distractor_judge'
CLOZE_JUDGE_VERSION = 1
DEFAULT_JUDGE_MODEL = 'google/gemini-2.5-flash-lite'

_TEMPLATE_CACHE: dict[str, str] = {}


def judge_distractors(
    db,
    sentence_with_blank: str,
    correct_answer: str,
    distractors: list[str],
    language_id: int,
    model: str = DEFAULT_JUDGE_MODEL,
) -> dict:
    """Rule on each distractor. Returns:

        {
          'verdicts': {distractor: 'keep' | 'reject', ...},
          'reasons':  {distractor: short_reason, ...},
          'model':    model_id,
          'version':  CLOZE_JUDGE_VERSION,
        }

    On any error (template missing, LLM failure, malformed JSON) the judge
    falls back to keeping every distractor and logs a warning. This is the
    safer default: failure mode is "act like the judge wasn't there",
    not "drop all distractors".
    """
    if not distractors:
        return _empty_result(model)

    try:
        template = _load_template(db)
    except Exception as exc:
        logger.warning("cloze_judge: failed to load template, keeping all: %s", exc)
        return _all_keep(distractors, model)

    numbered = '\n'.join(f'{i + 1}. {d}' for i, d in enumerate(distractors))
    prompt = template.format(
        sentence_with_blank=sentence_with_blank,
        correct_answer=correct_answer,
        distractors_numbered=numbered,
    )

    try:
        result = call_llm(prompt, model=model, response_format='json')
    except Exception as exc:
        logger.warning("cloze_judge: LLM call failed, keeping all: %s", exc)
        return _all_keep(distractors, model)

    if not isinstance(result, dict):
        logger.warning("cloze_judge: non-dict response, keeping all: %r", type(result))
        return _all_keep(distractors, model)

    verdicts: dict[str, str] = {}
    reasons: dict[str, str] = {}
    for idx, d in enumerate(distractors):
        entry = result.get(str(idx + 1)) or {}
        if not isinstance(entry, dict):
            verdicts[d] = 'keep'
            reasons[d] = ''
            continue
        verdict = str(entry.get('verdict', 'keep')).strip().lower()
        verdicts[d] = 'reject' if verdict == 'reject' else 'keep'
        reasons[d] = str(entry.get('reason', ''))[:200]

    return {
        'verdicts': verdicts,
        'reasons': reasons,
        'model': model,
        'version': CLOZE_JUDGE_VERSION,
    }


def filter_distractors(
    db,
    sentence_with_blank: str,
    correct_answer: str,
    distractors: list[str],
    language_id: int,
    model: str = DEFAULT_JUDGE_MODEL,
) -> tuple[list[str], dict]:
    """Convenience wrapper: returns (kept_distractors, judge_meta).

    judge_meta has the shape stored under exercises.tags.cloze_judge:
        {"rejected": N, "model": "...", "version": 1, "rejected_items": [...]}
    """
    result = judge_distractors(
        db, sentence_with_blank, correct_answer,
        distractors, language_id, model,
    )
    kept = [d for d in distractors if result['verdicts'].get(d) == 'keep']
    rejected = [d for d in distractors if result['verdicts'].get(d) == 'reject']
    meta = {
        'rejected': len(rejected),
        'rejected_items': rejected,
        'model': result['model'],
        'version': result['version'],
    }
    return kept, meta


def _load_template(db) -> str:
    if CLOZE_JUDGE_TASK in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[CLOZE_JUDGE_TASK]
    result = (
        db.table('prompt_templates')
        .select('template_text')
        .eq('task_name', CLOZE_JUDGE_TASK)
        .order('version', desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise RuntimeError(f"No prompt template for task_name='{CLOZE_JUDGE_TASK}'")
    text = result.data[0]['template_text']
    _TEMPLATE_CACHE[CLOZE_JUDGE_TASK] = text
    return text


def _empty_result(model: str) -> dict:
    return {'verdicts': {}, 'reasons': {}, 'model': model, 'version': CLOZE_JUDGE_VERSION}


def _all_keep(distractors: list[str], model: str) -> dict:
    return {
        'verdicts': {d: 'keep' for d in distractors},
        'reasons': {d: '' for d in distractors},
        'model': model,
        'version': CLOZE_JUDGE_VERSION,
    }
