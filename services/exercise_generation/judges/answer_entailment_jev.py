"""
jev backend for the answer-entailment judge.

Replaces the LLM's 1-5 Likert rating with one ``noul`` (yes/no probability)
question to ``typesafe/jev-1.13``: "does the passage support this candidate as
the answer to this question?". The probability is mapped onto the same
accept / flag / reject contract, so nothing downstream changes.

Why the cutoffs are not 0.5
---------------------------
Calibrated 2026-09-26 on 1,050 structurally-gold items (a question's answer =
positive, its distractors = negative) against the live judge -- see
``wiki/evaluations/jev-entailment-calibration-2026-09-26.md``. jev's scores are
bimodal: distractors sit almost entirely below 0.35, stated answers mostly above
0.7. The reject cutoff is anywhere in the 0.30-0.40 plateau (false-rejects of
real answers are flat there); 0.60 is the lowest accept cutoff that takes zh
false-accepts to zero. Raising accept only widens the flag band.

    P(yes) <  reject_below          -> reject
    P(yes) >= accept_at             -> accept
    otherwise                       -> flag  (kept + surfaced for review)

The dict is per language so it can be retuned without touching this logic; all
three currently share (0.30, 0.60) because the data supports no per-language
difference. The gold labels are structural, not human-adjudicated, so these are
defensible cutoffs, not proven-optimal ones.

Prompts are entirely in the content language (zh/ja/en) -- a hard rule for this
project; the JSON keys stay ASCII because they are protocol, not prose.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.jev_client import DEFAULT_MODEL, JevError, call_jev

# language_id -> (reject_below, accept_at)
CUTOFFS: dict[int, tuple[float, float]] = {
    1: (0.30, 0.60),   # zh
    2: (0.30, 0.60),   # en
    3: (0.30, 0.60),   # ja
}

_LANG_CODE = {1: 'zh', 2: 'en', 3: 'ja'}

# state = {"passage", "question", "candidate"}; one question, key "entailed".
RUBRIC: dict[int, dict] = {
    1: {
        'entailed': {
            'type': 'noul',
            'instructions': '根据passage字段中的文章内容，candidate字段里的答案是否准确回答了question字段提出的问题？',
            'criteria': {
                'true': '文章明确陈述了该答案，或者该答案是文章内容唯一可以推出的结论。',
                'false': '文章没有支持该答案，该答案只是话题相关但未被文章证实，或者与文章内容矛盾。',
            },
        },
    },
    2: {
        'entailed': {
            'type': 'noul',
            'instructions': 'Based on the article in the `passage` field, does the answer in the `candidate` field correctly answer the question in the `question` field?',
            'criteria': {
                'true': 'The passage explicitly states this answer, or it is the uniquely inferable conclusion from the passage.',
                'false': 'The passage does not support this answer -- it is merely on the same topic, unsupported, or contradicted by the passage.',
            },
        },
    },
    3: {
        'entailed': {
            'type': 'noul',
            'instructions': 'passageフィールドの文章の内容に基づくと、candidateフィールドの答えはquestionフィールドの質問に正しく答えていますか？',
            'criteria': {
                'true': '文章がその答えを明確に述べているか、文章の内容から一意に推論できる結論である。',
                'false': '文章はその答えを裏付けていない。話題は関連しているだけで文章に根拠がないか、文章の内容と矛盾している。',
            },
        },
    },
}

# jev returns no text, so the reason is synthesised. It is still fed back to the
# question generator as "avoid" context on a reject, hence a sentence rather
# than a bare number. {p} is P(yes).
_REASONS: dict[int, dict[str, str]] = {
    1: {
        'accept': '文章支持该答案（jev P(是)={p:.2f}）',
        'flag': '文章对该答案的支持不确定（jev P(是)={p:.2f}）',
        'reject': '文章不支持该答案（jev P(是)={p:.2f}）',
    },
    2: {
        'accept': 'The passage supports this answer (jev P(yes)={p:.2f}).',
        'flag': 'Unclear whether the passage supports this answer (jev P(yes)={p:.2f}).',
        'reject': 'The passage does not support this answer (jev P(yes)={p:.2f}).',
    },
    3: {
        'accept': '文章はこの答えを裏付けています（jev P(はい)={p:.2f}）',
        'flag': '文章がこの答えを裏付けているか不確かです（jev P(はい)={p:.2f}）',
        'reject': '文章はこの答えを裏付けていません（jev P(はい)={p:.2f}）',
    },
}


@dataclass
class JevVerdict:
    verdict: str          # 'accept' | 'flag' | 'reject'
    probability: float    # jev's P(yes)
    reason: str
    model: str            # dated snapshot that answered
    cost_usd: float | None


def probability_to_verdict(p: float, language_id: int) -> str:
    """Map jev's P(yes) to accept / flag / reject with the language's cutoffs."""
    reject_below, accept_at = CUTOFFS[language_id]
    if p < reject_below:
        return 'reject'
    if p >= accept_at:
        return 'accept'
    return 'flag'


def evaluate(
    passage: str,
    question_text: str,
    answer: str,
    language_id: int,
    *,
    task_name: str,
    pipeline: str = 'test_gen',
) -> JevVerdict:
    """Ask jev whether the passage supports ``answer``. Raises ``JevError``.

    A response that arrives without a usable ``noul`` in [0, 1] is treated as a
    failure, not as an item-level gap: this judge is the guard against
    hallucinated answers, so a jev that answered nothing is a jev that did not
    run, and the caller falls back to the LLM judge.
    """
    if language_id not in RUBRIC:
        raise JevError(f'no jev entailment rubric for language_id={language_id}')

    result = call_jev(
        state={'passage': passage, 'question': question_text, 'candidate': answer},
        questions=RUBRIC[language_id],
        pipeline=pipeline,
        task_name=task_name,
        language_code=_LANG_CODE.get(language_id),
    )
    ans = result.answers.get('entailed')
    p = ans.get('noul') if isinstance(ans, dict) else None
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0.0 <= p <= 1.0:
        raise JevError(f'jev returned no usable noul for "entailed": {ans!r}')
    p = float(p)
    verdict = probability_to_verdict(p, language_id)
    return JevVerdict(
        verdict=verdict,
        probability=p,
        reason=_REASONS[language_id][verdict].format(p=p),
        model=result.model,
        cost_usd=result.cost_usd,
    )
