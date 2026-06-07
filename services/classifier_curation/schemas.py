"""Pydantic schemas for classifier-curation LLM output.

Used with services.llm_service.call_llm(..., schema=..., response_format='json_object'),
which validates the parsed JSON and runs one deterministic repair turn on failure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from .config import GROUPS


class NounExample(BaseModel):
    """One noun that takes a given classifier."""
    noun: str = Field(..., description="Simplified-Chinese noun")
    pinyin: str = Field('', description="Pinyin with tone marks")
    gloss: str = Field('', description="Short English gloss")
    example_sentence: str = Field('', description="Short 数词+量词+名词 phrase, e.g. 一束鲜花")
    ge_also_acceptable: bool = Field(
        False, description="True if 个 is also a natural classifier for this noun"
    )


class NounList(BaseModel):
    nouns: list[NounExample] = Field(default_factory=list)


class ClassifierMeta(BaseModel):
    """Semantic classification of a single measure word."""
    hanzi: str
    pinyin: str = ''            # numeric tone, e.g. shu4
    pinyin_display: str = ''    # diacritics, e.g. shù
    group: str
    difficulty_tier: int = Field(..., ge=1, le=4)
    semantic_label: str = ''

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
