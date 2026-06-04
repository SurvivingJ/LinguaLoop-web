"""
Test Generation — Pydantic schemas

Schemas for LLM-structured outputs in the test generation pipeline.
Use these as the `schema=` argument to services.llm_service.call_llm to
get post-validation + one-shot repair retry behaviour.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, model_validator


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
        return out

    @model_validator(mode='after')
    def _validate(self) -> 'AnswerEntailmentVerdict':
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f'confidence {self.confidence!r} must be in [0.0, 1.0]'
            )
        return self


class DistractorPlausibilityVerdict(BaseModel):
    """Judge output: are the distractors plausible-but-clearly-wrong?

    The judge prompt uses numeric keys so the prompt body can be authored
    entirely in the target language (no English field names in ZH/JA rows).

    The LLM returns one confidence per distractor and one reason per
    distractor — both as lists of the same length as the distractor list:

        {"1": [0.9, 0.4, 0.85], "2": ["reason0", "reason1", "reason2"]}
        → per_distractor=[0.9, 0.4, 0.85], reasons=["reason0", ...]

    ``_validate`` enforces that the two lists have matching lengths and that
    all confidence values are in [0.0, 1.0].
    """

    per_distractor: list[float]
    reasons: list[str]

    @model_validator(mode='before')
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        # The judge model intermittently returns off-schema shapes that survive
        # call_llm's repair retry: a bare list of per-distractor dicts
        # (``[{"distractor_1": 0.2}, ...]``), a ``per_distractor`` list with no
        # ``reasons``, or alias keys. Coerce the common variants into
        # ``{per_distractor, reasons}`` so the judge yields a real verdict
        # instead of failing open (safe_accept) — which made cross-language
        # behaviour a non-reproducible lottery.

        def _as_score(x):
            if isinstance(x, bool):
                return None
            if isinstance(x, (int, float)):
                return float(x)
            if isinstance(x, str):
                try:
                    return float(x.strip())
                except ValueError:
                    return None
            return None

        def _pair(item):
            """Extract (score, reason) from one per-distractor element."""
            if isinstance(item, (int, float, str)):
                return _as_score(item), ''
            if isinstance(item, dict):
                score, reason = None, ''
                for k, v in item.items():
                    kl = str(k).lower()
                    if 'reason' in kl or 'explanation' in kl:
                        reason = str(v)
                    elif score is None:
                        s = _as_score(v)
                        if s is not None:
                            score = s
                return score, reason
            return None, ''

        # Bare list → unzip into the two parallel lists.
        if isinstance(data, list):
            scores, reasons = [], []
            for item in data:
                s, r = _pair(item)
                scores.append(s if s is not None else 0.0)
                reasons.append(r)
            return {'per_distractor': scores, 'reasons': reasons}

        if not isinstance(data, dict):
            return data

        out: dict[str, Any] = {}
        for k, v in data.items():
            if k in ('1', 1):
                out['per_distractor'] = v
            elif k in ('2', 2):
                out['reasons'] = v
            else:
                out[k] = v

        # Alias keys for the scores list.
        if 'per_distractor' not in out:
            for alias in ('scores', 'confidences', 'plausibility',
                          'plausibilities'):
                if isinstance(out.get(alias), list):
                    out['per_distractor'] = out[alias]
                    break

        # A list of {score, reason} dicts under per_distractor → unzip.
        pd = out.get('per_distractor')
        if isinstance(pd, list) and pd and all(isinstance(x, dict) for x in pd):
            scores, reasons = [], []
            for item in pd:
                s, r = _pair(item)
                scores.append(s if s is not None else 0.0)
                reasons.append(r)
            out['per_distractor'] = scores
            if not out.get('reasons'):
                out['reasons'] = reasons

        # Reasons missing or wrong length → pad/truncate to per_distractor.
        if isinstance(out.get('per_distractor'), list):
            n = len(out['per_distractor'])
            reasons = out.get('reasons')
            if not isinstance(reasons, list):
                reasons = []
            # The model occasionally emits a non-string (e.g. a float score
            # duplicated) in the reasons list — coerce so it never fails open.
            reasons = [str(r) for r in reasons]
            if len(reasons) < n:
                reasons = reasons + [''] * (n - len(reasons))
            elif len(reasons) > n:
                reasons = reasons[:n]
            out['reasons'] = reasons

        return out

    @model_validator(mode='after')
    def _validate(self) -> 'DistractorPlausibilityVerdict':
        if len(self.per_distractor) != len(self.reasons):
            raise ValueError(
                f'per_distractor length ({len(self.per_distractor)}) must '
                f'match reasons length ({len(self.reasons)})'
            )
        for i, c in enumerate(self.per_distractor):
            if not 0.0 <= c <= 1.0:
                raise ValueError(
                    f'per_distractor[{i}]={c!r} must be in [0.0, 1.0]'
                )
        return self
