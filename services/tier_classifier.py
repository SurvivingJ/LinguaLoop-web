"""Age-tier assignment via jev (ADR-029).

One jev *score* question places a text on the six-step tier scale
(T1 toddler ... T6 educated professional). The answer is a probability mass
over the six tiers; the assigned tier is the probability-weighted expected
tier, rounded half-up. Probabilities and confidence are kept with the result.

jev's expected tier is monotone with difficulty but not on the 1-6 scale: on a
blind ja gold set the tiers sit at expected-tier ~ 1.3 / 2.4-3.6 / 4.0-4.2 /
4.3-5.2 / 5.5 / 5.9, so round-half-up put whole tier bands one tier high. The
score -> tier step is therefore a per-language ordered threshold table
(``SCORE_THRESHOLDS``), fitted on that gold set (ADR-029, recalibration). The raw
jev score is always stored, so a tier can be re-derived under a new table.

Prompts are written entirely in the content language (zh in Chinese, ja in
Japanese, en in English) and reuse the tier descriptions in
``services.categorical_maps`` (``TIER_DISPLAY_NAMES`` / ``TIER_CONSTRAINTS``)
verbatim, as the jev tier experiment did (wiki/evaluations/
jev-judge-feasibility-2026-09-26.md §3.4).

Nothing here falls back: a jev failure raises ``services.jev_client.JevError``.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Mapping, Optional

from services.categorical_maps import (
    DIFFICULTY_TO_TIER, TIER_CONSTRAINTS, TIER_DISPLAY_NAMES, VALID_TIERS,
)
from services import jev_client
from services.jev_client import JevError

logger = logging.getLogger(__name__)

LANG_IDS = {'zh': 1, 'en': 2, 'ja': 3}
N_TIERS = len(VALID_TIERS)

#: Longest passage sent to jev (its context is 32k tokens shared with the
#: rubric). The longest live transcript is ~6.8k characters.
MAX_PASSAGE_CHARS = 24_000

LOG_PIPELINE = 'tier_assignment'
#: Cut points on jev's raw 0-5 score: tier = 1 + (number of cut points <= score).
#: The default is round half up. ja was fitted 2026-09-27 against 59 passages
#: labelled blind by two readers: 39 -> 57 of 59 match, 52.3 of 59 under
#: 5-fold cross-validation (tests/fixtures/ja_tier_calibration_gold.json).
#: zh is a single uniform shift of the default (score - 0.25): it and the five-cut
#: fit tied under cross-validation (52.0 vs 51.5 of 60, default 44), so the
#: simpler one was kept. en was measured the same way (60 passages, two blind
#: readers) and stays on the default: no calibration beat it under
#: cross-validation (default 46/60, best 47/60 = noise).
#: scripts/build_tier_gold_sample.py + scripts/fit_tier_thresholds.py redo any of it.
DEFAULT_THRESHOLDS = (0.5, 1.5, 2.5, 3.5, 4.5)
SCORE_THRESHOLDS = {
    'ja': (0.95, 2.65, 3.25, 4.2, 4.4),
    'zh': (0.75, 1.75, 2.75, 3.75, 4.75),
}
CALIBRATION_LABELS = {'ja': 'ja-2026-09-27', 'zh': 'zh-2026-09-27'}

PASSAGE_TASK = 'jev_tier_passage'
TOPIC_TASK = 'jev_tier_topic'

_QUESTION_KEY = 'tier'

_STATE_KEY = {'zh': '文章', 'en': 'passage', 'ja': '文章'}

_PASSAGE_INSTRUCTIONS = {
    'zh': '请将文章的语言难度，按从最简单（幼儿）到最高级（专业人士）排列的年龄层量表进行定位。',
    'en': ("Place the passage's language difficulty on the age-tier scale, "
           'ordered from simplest (toddler) to most advanced (professional).'),
    'ja': '文章の言語的な難易度を、最も簡単（幼児）から最も高度（専門家）まで並べた年齢層の尺度上に位置づけてください。',
}

# Topics are English (concept_english + distinctive vocabulary), so the topic
# prompt is English regardless of the study language it will later be rendered in.
_TOPIC_INSTRUCTIONS = (
    'Place this topic on the age-tier scale, ordered from simplest (toddler) '
    'to most advanced (professional), according to the youngest reader who '
    'could reach the language needed to discuss it: the topic itself and its '
    'distinctive vocabulary.'
)


@dataclass(frozen=True)
class TierAssessment:
    #: Assigned tier, 1-6 (``dim_complexity_tiers.id``).
    tier: int
    #: Probability-weighted expected tier on the 1-6 scale (score + 1).
    expected_tier: float
    #: jev's raw 0-5 score, as returned.
    score: float
    confidence: Optional[float]
    #: {tier id: probability}, always all six keys.
    probabilities: dict
    model: str
    cost_usd: Optional[float]
    #: Which score -> tier table produced ``tier`` ('default' or a dated label).
    calibration: str = 'default'

    @property
    def code(self) -> str:
        return f'T{self.tier}'


def thresholds_for(language_code: Optional[str]) -> tuple:
    return SCORE_THRESHOLDS.get(language_code, DEFAULT_THRESHOLDS)


def calibration_for(language_code: Optional[str]) -> str:
    return CALIBRATION_LABELS.get(language_code, 'default')


def tier_from_score(score: float, language_code: Optional[str] = None) -> int:
    """jev's 0-based score -> tier id 1-6 using the language's threshold table."""
    if score is None or isinstance(score, bool) or not math.isfinite(score):
        raise JevError(f'unusable tier score: {score!r}')
    return 1 + sum(score >= cut for cut in thresholds_for(language_code))


def _describe(tier: str, language_id: int) -> str:
    name = TIER_DISPLAY_NAMES[tier][language_id]
    constraint = TIER_CONSTRAINTS[tier][language_id]
    sep = ': ' if language_id == LANG_IDS['en'] else '：'
    return f'{name}{sep}{constraint}'


def _score_question(language_code: str, instructions: str) -> dict:
    language_id = LANG_IDS[language_code]
    return {
        'type': 'score',
        'instructions': instructions,
        # score-mode criteria is an ordered array: index 0 = T1 ... 5 = T6
        'criteria': [_describe(t, language_id) for t in VALID_TIERS],
    }


def build_passage_request(language_code: str, text: str) -> tuple:
    """``(state, questions)`` for a passage in ``language_code``."""
    if language_code not in LANG_IDS:
        raise ValueError(f'unsupported language for tier assignment: {language_code!r}')
    if len(text) > MAX_PASSAGE_CHARS:
        logger.warning(
            'passage of %d chars truncated to %d for tier assignment',
            len(text), MAX_PASSAGE_CHARS,
        )
        text = text[:MAX_PASSAGE_CHARS]
    state = {_STATE_KEY[language_code]: text}
    questions = {_QUESTION_KEY: _score_question(
        language_code, _PASSAGE_INSTRUCTIONS[language_code])}
    return state, questions


def build_topic_request(concept: str, vocabulary: str = '') -> tuple:
    state = {'topic': concept}
    if vocabulary:
        state['distinctive vocabulary'] = vocabulary
    questions = {_QUESTION_KEY: _score_question('en', _TOPIC_INSTRUCTIONS)}
    return state, questions


def assessment_from_answers(
    answers: Mapping, *, model: str, cost_usd: Optional[float] = None,
    language_code: Optional[str] = None,
) -> TierAssessment:
    answer = answers.get(_QUESTION_KEY) if isinstance(answers, Mapping) else None
    if not isinstance(answer, Mapping) or answer.get('type') != 'score':
        raise JevError(f'tier answer missing or not a score answer: {answer!r}')
    raw_score = answer.get('score')
    if not isinstance(raw_score, (int, float)):
        raise JevError(f'tier answer has no numeric score: {answer!r}')
    score = min(max(float(raw_score), 0.0), N_TIERS - 1.0)
    raw_probs = answer.get('probabilities') or {}
    probabilities = {
        i + 1: float(raw_probs.get(str(i), 0.0) or 0.0) for i in range(N_TIERS)
    }
    confidence = answer.get('confidence')
    return TierAssessment(
        tier=tier_from_score(score, language_code),
        expected_tier=score + 1.0,
        score=score,
        confidence=float(confidence) if confidence is not None else None,
        probabilities=probabilities,
        model=model,
        cost_usd=cost_usd,
        calibration=calibration_for(language_code),
    )


def _summarizer(language_code: Optional[str]):
    def summarize(answers: dict) -> tuple:
        answer = answers.get(_QUESTION_KEY) or {}
        score = answer.get('score')
        verdict = (f'T{tier_from_score(score, language_code)}'
                   if isinstance(score, (int, float)) else None)
        return verdict, answer.get('confidence')
    return summarize


def _assess(state, questions, *, task_name, language_code) -> TierAssessment:
    result = jev_client.call_jev(
        state, questions, pipeline=LOG_PIPELINE, task_name=task_name,
        language_code=language_code, summarize=_summarizer(language_code),
    )
    return assessment_from_answers(
        result.answers, model=result.model, cost_usd=result.cost_usd,
        language_code=language_code,
    )


def classify_passage(text: str, language_code: str) -> TierAssessment:
    """Assign an age tier to a passage. Raises JevError; never guesses."""
    if not text or not text.strip():
        raise ValueError('cannot assign a tier to an empty passage')
    state, questions = build_passage_request(language_code, text)
    return _assess(state, questions, task_name=PASSAGE_TASK,
                   language_code=language_code)


def classify_topic(concept: str, vocabulary: str = '') -> TierAssessment:
    """Assign an age tier to a topic from its concept and vocabulary."""
    if not concept or not concept.strip():
        raise ValueError('cannot assign a tier to an empty topic')
    state, questions = build_topic_request(concept, vocabulary)
    return _assess(state, questions, task_name=TOPIC_TASK, language_code='en')


# ── tier -> legacy difficulty ────────────────────────────────────────────────
#
# ``tests.difficulty`` (1-9) is derived one-way from the tier and still read by
# dictation_max_words(), get_recommended_tests, build_daily_session and
# tests_containing_sense. Derived from DIFFICULTY_TO_TIER (itself pinned to
# dim_complexity_tiers by tests/test_difficulty_to_tier_matches_db.py) rather
# than re-typed, so it cannot become a fourth copy of the bands. Lowest
# difficulty in each band == dim_complexity_tiers.difficulty_min, which is what
# the test-generation orchestrator writes.
TIER_ID_TO_DIFFICULTY: dict = {
    int(tier[1:]): min(d for d, t in DIFFICULTY_TO_TIER.items() if t == tier)
    for tier in VALID_TIERS
}


def difficulty_for_tier(tier_id: int) -> int:
    return TIER_ID_TO_DIFFICULTY[tier_id]
