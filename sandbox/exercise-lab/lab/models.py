"""
Shared, lightweight data structures for the exercise-lab sandbox.

WHY THIS EXISTS: harness.py, mock_llm-backed prototype generators, and the
DB layer all need to agree on one shape for "a dictionary sense" and "a
produced exercise" without importing production's ORM/Supabase client (this
sandbox never imports anything that could reach a network). These are
read-only mirrors of the columns that matter for generation/serving
prototyping - not the full production row, and not an ORM (no persistence
logic lives here, see lab/db.py for that).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SenseRow:
    """Mirrors the columns of one dim_word_senses row (joined to its
    dim_vocabulary parent for convenience) that a generator needs to build
    exercises. See db/schema.sql for the authoritative column list."""

    sense_id: int
    vocab_id: int
    language_id: int
    lemma: str
    part_of_speech: Optional[str]
    frequency_rank: Optional[float]  # Zipf score, NOT a rank - see README
    definition: Optional[str]
    definition_level: str  # 'simple' | 'standard'
    pronunciation: Optional[str]
    example_sentence: Optional[str]
    sense_rank: int
    embedding: Optional[bytes] = None  # packed float32 BLOB, or None


@dataclass
class ExerciseRow:
    """One exercise a Generator produced for one sense. `passed_validation`
    is the generator's own self-assessment (e.g. did a deterministic
    structural check pass) - the harness trusts it as reported, it does not
    re-validate content quality itself."""

    exercise_type: str
    content: dict[str, Any]
    word_sense_id: int
    language_id: int
    ladder_level: Optional[int] = None
    tags: dict[str, Any] = field(default_factory=dict)
    passed_validation: bool = True
