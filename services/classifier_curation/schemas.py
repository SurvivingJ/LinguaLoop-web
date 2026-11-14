"""Pydantic schemas for classifier-curation LLM output.

Used with services.llm_service.call_llm(..., schema=..., response_format='json_object'),
which validates the parsed JSON and runs one deterministic repair turn on failure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from services.measure_curation import JudgeRatings, group_validator

from .config import GROUPS

__all__ = ['NounExample', 'NounList', 'ClassifierMeta', 'JudgeRatings']


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

    _group_known = group_validator(GROUPS)
