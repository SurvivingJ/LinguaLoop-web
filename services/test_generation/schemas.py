"""
Test Generation — Pydantic schemas

Schemas for LLM-structured outputs in the test generation pipeline.
Use these as the `schema=` argument to services.llm_service.call_llm to
get post-validation + one-shot repair retry behaviour.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, model_validator


# Fallback used when a judge dumps a bare score (e.g. "0.1") or an empty string
# into a reason field. A real sentence keeps the regen `avoid_context` feedback
# usable instead of poisoning it with "rejected: 0.1".
_REASON_FALLBACK = '(no reason provided by judge)'


def _clean_reason(r: Any) -> str:
    """Coerce a judge reason to a non-empty sentence.

    The judge model intermittently emits a bare number (a duplicated score)
    or an empty string where a reason belongs. Both are useless as regen
    feedback, so they are replaced with a deterministic fallback sentence.
    """
    s = str(r).strip()
    if not s:
        return _REASON_FALLBACK
    try:
        float(s)  # a bare number is a leaked score, not a reason
    except ValueError:
        return s
    return _REASON_FALLBACK


# v3 distractor-plausibility judge: the judge now emits a 5-point Likert RATING
# per distractor instead of a raw 0.0-1.0 float. Code maps the rating to a
# verdict here so the cut points are tunable without re-prompting:
#   5, 4 -> accept    3 -> flag (weak, keep + surface)    2, 1 -> reject
# (2 = off-topic / different subject, 1 = also-correct or absurd). This replaces
# base.classify() for that judge only; answer-entailment keeps its float.
LIKERT_TO_VERDICT: dict[int, str] = {
    5: 'accept', 4: 'accept', 3: 'flag', 2: 'reject', 1: 'reject',
}


def likert_to_verdict(rating: int) -> str:
    """Map a 1-5 Likert rating to 'accept' | 'flag' | 'reject'.

    Unknown / out-of-range values default to 'flag' (neutral keep) rather than
    'reject' — a parse glitch must never manufacture a spurious rejection, which
    is the exact failure v3 exists to remove.
    """
    return LIKERT_TO_VERDICT.get(int(rating), 'flag')


class TopicTranslation(BaseModel):
    """Translated topic + keyword list returned by the topic_translator agent.

    The prompt asks for `{"topic": str, "keywords": list[str]}`. Keywords are
    accepted as either a list of strings or a comma-separated string (model
    sometimes returns the latter); the normaliser coerces both to a list.
    Empty / missing keywords are tolerated — they default to an empty list.
    """
    topic: str
    keywords: list[str] = []

    @model_validator(mode='before')
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        kws = out.get('keywords')
        if isinstance(kws, str):
            out['keywords'] = [k.strip() for k in kws.split(',') if k.strip()]
        elif kws is None:
            out['keywords'] = []
        return out


class TranscriptResponse(BaseModel):
    """Wrapper for the legacy `transcript_generation` prompt output.

    The prompt asks for `{"transcript": "...", "difficulty_level": N}`.
    Using a schema here means call_llm's JSON path handles markdown fences,
    BOM, and stray prose around the JSON — eliminating the brittle
    `if transcript.startswith('{') and transcript.endswith('}')` check.
    """
    transcript: str
    difficulty_level: Optional[int] = None


class MCQuestion(BaseModel):
    """A multiple-choice reading/listening comprehension question.

    The LLM is asked to return one of two shapes — the active DB-templated
    shape (`question_text`/`choices`/`answer`/`explanation`) or the legacy
    numeric-key fallback (`1`/`2`/`3`/`4`/`5`). The validator below normalises
    both to the canonical fields and rejects the call (triggering call_llm's
    one-shot repair retry) when:

      * `choices` is not a length-4 list of distinct non-empty strings, or
      * `answer` (after letter-index promotion: A/B/C/D -> choices[i]) does
        not match any item in `choices`.

    Successful validation populates `correct_answer_index` as the canonical
    pointer to the correct option, eliminating the silent-corruption mode in
    the old parser (which fell back to choices[0] on any mismatch).
    """

    question_text: str
    choices: list[str]
    answer: str
    correct_answer_index: int
    explanation: Optional[str] = None
    distractor_types: Optional[list[Optional[str]]] = None

    @model_validator(mode='before')
    @classmethod
    def _normalize_and_validate(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Accept any of the variant key names the prompts emit.
        aliases = {
            '1': 'question_text', 'Question': 'question_text', 'question': 'question_text',
            '2': 'choices',       'Options': 'choices',        'options': 'choices',
            '3': 'answer',        'Answer': 'answer',          'correct_answer': 'answer',
            'rationale': 'explanation',
            '5': 'distractor_types',
        }
        normalized: dict[str, Any] = {}
        for k, v in data.items():
            normalized[aliases.get(k, k)] = v

        # --- choices ----------------------------------------------------------
        choices = normalized.get('choices')
        if not isinstance(choices, list):
            raise ValueError("choices must be a list")
        if len(choices) != 4:
            raise ValueError(f"choices must have exactly 4 items, got {len(choices)}")
        cleaned = [str(c).strip() for c in choices]
        if any(not c for c in cleaned):
            raise ValueError("choices must all be non-empty after strip")
        if len({c.lower() for c in cleaned}) != 4:
            raise ValueError("choices must be distinct (case-insensitive)")
        normalized['choices'] = cleaned

        # --- answer -----------------------------------------------------------
        answer = normalized.get('answer')
        if not isinstance(answer, str):
            raise ValueError("answer must be a string")
        answer_stripped = answer.strip()
        if not answer_stripped:
            raise ValueError("answer is empty")

        # Letter-index promotion: model sometimes returns "A"/"B"/"C"/"D".
        if answer_stripped in ('A', 'B', 'C', 'D'):
            answer_stripped = cleaned[ord(answer_stripped) - ord('A')]

        if answer_stripped not in cleaned:
            raise ValueError(
                f"answer {answer_stripped!r} not in choices {cleaned!r}"
            )

        normalized['answer'] = answer_stripped
        correct_index = cleaned.index(answer_stripped)
        normalized['correct_answer_index'] = correct_index

        # --- distractor_types -------------------------------------------------
        # When present it must align 1:1 with choices: exactly 4 entries, with
        # the correct choice's slot null (it is not a distractor). A short/long
        # list silently corrupts the per-choice tagging, so reject it (which
        # triggers call_llm's one-shot repair retry).
        dt = normalized.get('distractor_types')
        if dt is not None:
            if not isinstance(dt, list):
                raise ValueError("distractor_types must be a list")
            if len(dt) != 4:
                raise ValueError(
                    f"distractor_types must have 4 entries, got {len(dt)}"
                )
            if dt[correct_index] is not None:
                raise ValueError(
                    f"distractor_types[{correct_index}] (the correct choice) "
                    f"must be null, got {dt[correct_index]!r}"
                )

        return normalized


# ---------------------------------------------------------------------------
# Judge verdict schemas (Wave 2)
# ---------------------------------------------------------------------------

class AnswerEntailmentVerdict(BaseModel):
    """Judge output: does the passage support the correct answer?

    The judge prompt uses numeric keys so the prompt body can be authored
    entirely in the target language (no English field names leak into ZH/JA
    prompts).  The ``_normalize`` validator maps both the numeric-key shape
    returned by non-English prompts and the named-key shape the English
    prompt may return:

        {"1": 0.85, "2": "reasoning text"} → confidence=0.85, reason="..."
        {"confidence": 0.85, "reason": "..."}  → passthrough

    Confidence is clamped to [0.0, 1.0] by ``_validate``.
    """

    confidence: float
    reason: str

    @model_validator(mode='before')
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out: dict[str, Any] = {}
        for k, v in data.items():
            if k in ('1', 1):
                out['confidence'] = v
            elif k in ('2', 2):
                out['reason'] = v
            else:
                out[k] = v
        # An empty or bare-numeric reason is useless as regen feedback; replace
        # it with a deterministic sentence. Leave a missing key alone so the
        # required-field validation still fires.
        if 'reason' in out:
            out['reason'] = _clean_reason(out['reason'])
        return out

    @model_validator(mode='after')
    def _validate(self) -> 'AnswerEntailmentVerdict':
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f'confidence {self.confidence!r} must be in [0.0, 1.0]'
            )
        return self


class DistractorPlausibilityVerdict(BaseModel):
    """Judge output: a 5-point Likert RATING per distractor (v3).

    The judge prompt uses numeric keys so the prompt body can be authored
    entirely in the target language (no English field names in ZH/JA rows).

    The LLM returns one integer rating (1-5) per distractor and one reason per
    distractor — both as lists of the same length as the distractor list:

        {"1": [5, 5, 2], "2": ["reason0", "reason1", "reason2"]}
        → per_distractor=[5, 5, 2], reasons=["reason0", ...]

    The rating replaces the old raw 0.0-1.0 float: a small judge model is far
    more self-consistent choosing among a few anchored labels than emitting a
    calibrated continuous score (the v2 float was where the 0.80-vs-0.20
    inconsistency came from). Code maps the integer to a verdict via
    ``likert_to_verdict``; the verdict math leaves the model entirely.

    ``_validate`` enforces matching list lengths and ratings in [1, 5].
    """

    per_distractor: list[int]
    reasons: list[str]

    @model_validator(mode='before')
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        # The judge model intermittently returns off-schema shapes that survive
        # call_llm's repair retry: a bare list, a ``per_distractor`` list with no
        # ``reasons``, alias keys, or a list of {rating, reason} dicts. Coerce
        # the common variants into ``{per_distractor, reasons}`` so the judge
        # yields a real verdict instead of failing open (safe_accept). An
        # unparseable rating falls back to 3 (a neutral "flag"), NOT a reject —
        # the whole point of v3 is to stop spurious rejects, so a parse glitch
        # must not manufacture one.

        _FALLBACK_RATING = 3  # neutral 'flag' when a rating cannot be parsed

        def _as_likert(x):
            """Coerce a value to an int Likert rating in [1, 5], or None."""
            if isinstance(x, bool):
                return None
            v = None
            if isinstance(x, (int, float)):
                v = float(x)
            elif isinstance(x, str):
                try:
                    v = float(x.strip())
                except ValueError:
                    return None
            if v is None:
                return None
            r = int(round(v))
            return 1 if r < 1 else 5 if r > 5 else r

        # Keys that name a distractor's position, NOT its rating — must never be
        # read as the score (the model emits ``{"distractor": "1", "rating": 4}``
        # and the index 1 would otherwise masquerade as the rating).
        _INDEX_KEYS = ('distractor', 'index', 'idx', 'option', 'choice',
                       'number', 'num', 'item', 'id')
        _RATING_KEYS = ('rating', 'score', 'likert', 'plausibility', 'verdict')

        def _pair(item):
            """Extract (rating, reason) from one per-distractor element.

            Handles a scalar, a ``[rating, reason]`` list, or a dict with named
            keys. For dicts, an explicit rating-ish key wins; an index/id key is
            never treated as the rating.
            """
            if isinstance(item, (int, float, str)):
                return _as_likert(item), ''
            if isinstance(item, list):
                rating, reason = None, ''
                for x in item:
                    s = _as_likert(x)
                    if s is not None and rating is None:
                        rating = s
                    elif isinstance(x, str) and not reason:
                        reason = x
                return rating, reason
            if isinstance(item, dict):
                rating, reason = None, ''
                # Pass 1: honour explicit rating / reason keys.
                for k, v in item.items():
                    kl = str(k).lower()
                    if 'reason' in kl or 'explanation' in kl:
                        reason = str(v)
                    elif any(t in kl for t in _RATING_KEYS):
                        s = _as_likert(v)
                        if s is not None:
                            rating = s
                # Pass 2: fall back to the first scoreable non-index value.
                if rating is None:
                    for k, v in item.items():
                        kl = str(k).lower()
                        if 'reason' in kl or 'explanation' in kl:
                            continue
                        if any(t in kl for t in _INDEX_KEYS):
                            continue
                        s = _as_likert(v)
                        if s is not None:
                            rating = s
                            break
                return rating, reason
            return None, ''

        # Resolve `data` into an `out` dict carrying per_distractor + reasons.
        if isinstance(data, list):
            # Bare list → unzip into the two parallel lists.
            ratings, reasons = [], []
            for item in data:
                s, r = _pair(item)
                ratings.append(s if s is not None else _FALLBACK_RATING)
                reasons.append(r)
            out: dict[str, Any] = {'per_distractor': ratings, 'reasons': reasons}
        elif isinstance(data, dict):
            # The model frequently misreads the numeric-key convention: instead
            # of the intended {"1": [ratings], "2": [reasons]} (field selectors),
            # it emits {"1": [rating, reason], "2": [...], "3": [...]} where each
            # numeric key is a DISTRACTOR. That read only 2 of N entries → a
            # length mismatch → safe_accept fall-open (24% of v3 groups in the
            # 2026-06-06 fixture re-score). Detect and unzip it here.
            dig = {str(k): v for k, v in data.items() if str(k).isdigit()}
            seq = [str(i) for i in range(1, len(dig) + 1)]
            contiguous = len(dig) >= 2 and set(dig) == set(seq)
            first = dig.get('1')
            # Distinguish the canonical field-selector shape
            #   {"1": [ratings], "2": [reasons]}
            # from the per-distractor shape {"1": [rating, reason], "2": [...]}.
            # The reliable discriminator is "2": a reasons array starts with a
            # STRING; a per-distractor pair starts with a NUMBER. "1" must itself
            # be a list (a scalar "1" means ratings are keyed by distractor).
            canonical = False
            if set(dig) <= {'1', '2'} and isinstance(first, list) and first:
                two = dig.get('2')
                if not isinstance(two, list) or not two:
                    canonical = True               # only "1", or "2" not a list
                else:
                    canonical = _as_likert(two[0]) is None  # "2"=[reason,...]
            if contiguous and not canonical:
                ratings, reasons = [], []
                for k in seq:
                    rt, rs = _pair(dig[k])
                    ratings.append(rt if rt is not None else _FALLBACK_RATING)
                    reasons.append(rs)
                out = {'per_distractor': ratings, 'reasons': reasons}
            else:
                out = {}
                for k, v in data.items():
                    if k in ('1', 1):
                        out['per_distractor'] = v
                    elif k in ('2', 2):
                        out['reasons'] = v
                    else:
                        out[k] = v
        else:
            return data

        # Alias keys for the ratings list.
        if 'per_distractor' not in out:
            for alias in ('ratings', 'scores', 'confidences', 'plausibility',
                          'plausibilities'):
                if isinstance(out.get(alias), list):
                    out['per_distractor'] = out[alias]
                    break

        # A list of {rating, reason} dicts under per_distractor → unzip.
        pd = out.get('per_distractor')
        if isinstance(pd, list) and pd and all(isinstance(x, dict) for x in pd):
            ratings, reasons = [], []
            for item in pd:
                s, r = _pair(item)
                ratings.append(s if s is not None else _FALLBACK_RATING)
                reasons.append(r)
            out['per_distractor'] = ratings
            if not out.get('reasons'):
                out['reasons'] = reasons

        # Coerce every rating to a valid Likert int (handles a plain list of
        # mixed floats/strings the model may emit, e.g. [5, "4", 2.0]).
        if isinstance(out.get('per_distractor'), list):
            out['per_distractor'] = [
                (_as_likert(x) if _as_likert(x) is not None else _FALLBACK_RATING)
                for x in out['per_distractor']
            ]

        # Reasons missing or wrong length → pad/truncate to per_distractor,
        # then coerce each to a real sentence: the model occasionally emits a
        # non-string (a duplicated rating) or an empty slot, both of which would
        # otherwise poison the regen avoid_context. _clean_reason fixes those.
        if isinstance(out.get('per_distractor'), list):
            n = len(out['per_distractor'])
            reasons = out.get('reasons')
            if not isinstance(reasons, list):
                reasons = []
            if len(reasons) < n:
                reasons = reasons + [''] * (n - len(reasons))
            elif len(reasons) > n:
                reasons = reasons[:n]
            out['reasons'] = [_clean_reason(r) for r in reasons]

        return out

    @model_validator(mode='after')
    def _validate(self) -> 'DistractorPlausibilityVerdict':
        if len(self.per_distractor) != len(self.reasons):
            raise ValueError(
                f'per_distractor length ({len(self.per_distractor)}) must '
                f'match reasons length ({len(self.reasons)})'
            )
        for i, c in enumerate(self.per_distractor):
            if not 1 <= c <= 5:
                raise ValueError(
                    f'per_distractor[{i}]={c!r} must be a Likert rating in [1, 5]'
                )
        return self
