# models/requests.py
"""Pydantic request models for API input validation."""

from pydantic import BaseModel, Field
from typing import Optional


class WordQuizResult(BaseModel):
    """A single word quiz result."""
    sense_id: int
    selected_answer: str
    correct_answer: str
    is_correct: bool
    response_time_ms: Optional[int] = None


class WordQuizRequest(BaseModel):
    """Request body for POST /api/vocabulary/word-quiz."""
    language_id: int
    attempt_id: Optional[str] = None
    results: list[WordQuizResult] = Field(min_length=1)
