"""Pydantic schemas for counter-curation LLM output.

Used with services.llm_service.call_llm(..., schema=..., response_format='json_object'),
which validates the parsed JSON and runs one deterministic repair turn on failure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import GROUPS


class NounExample(BaseModel):
    """One noun that takes a given counter."""

    noun: str = Field(..., description="Japanese noun (kanji/kana as normally written)")
    reading: str = Field('', description="Kana reading of the noun")
    gloss: str = Field('', description="Short English gloss")
    example_phrase: str = Field(
        '', description="Short 名詞 + 数詞 + 助数詞 phrase, e.g. ペンを三本")
    also_acceptable_counters: list[str] = Field(
        default_factory=list,
        description="Other counters a native speaker would also accept for this noun",
    )

    @field_validator('also_acceptable_counters', mode='before')
    @classmethod
    def _coerce_list(cls, v):
        """Tolerate a bare string or null where a list was asked for.

        The alternative is a ValidationError that burns a repair turn over a
        field that is advisory anyway.
        """
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v


class NounList(BaseModel):
    nouns: list[NounExample] = Field(default_factory=list)


class CounterMeta(BaseModel):
    """Semantic classification of a single counter."""

    counter: str
    reading: str = ''
    group: str
    difficulty_tier: int = Field(..., ge=1, le=5)
    semantic_label: str = ''
    is_real_counter: bool = Field(
        True,
        description="False if this is not actually a Japanese counter",
    )
    counts_nouns: bool = Field(
        True,
        description=(
            "False for counters whose counted thing is not a noun a learner "
            "could be shown — 階 counts storeys, 度 counts degrees"
        ),
    )

    @field_validator('group')
    @classmethod
    def _group_known(cls, v: str) -> str:
        if v not in GROUPS:
            raise ValueError(f"group {v!r} not in {GROUPS}")
        return v


class JudgeRatings(BaseModel):
    """Per-noun idiomatic-validity ratings, in the same order as the input."""

    ratings: list[int] = Field(default_factory=list, description="Likert 1-5 per noun")
    reasons: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def _align_reasons(self) -> 'JudgeRatings':
        if len(self.reasons) < len(self.ratings):
            self.reasons = self.reasons + [''] * (len(self.ratings) - len(self.reasons))
        return self
