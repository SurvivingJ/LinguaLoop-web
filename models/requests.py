# models/requests.py
"""Pydantic request models for API input validation."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


# One extraction runs an LLM pipeline over the whole text; cap what a request can submit.
VOCAB_EXTRACT_MAX_CHARS = 20000


class VocabularyExtractRequest(BaseModel):
    """Request body for POST /api/vocabulary/extract."""
    text: str = Field(min_length=1, max_length=VOCAB_EXTRACT_MAX_CHARS)
    language_code: str = Field(min_length=1, max_length=16)

    @field_validator('text', 'language_code')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class PaymentIntentRequest(BaseModel):
    """Request body for POST /api/payments/create-intent."""
    package_id: str


class ErrorLogRequest(BaseModel):
    """Request body for POST /api/errors/log."""
    error_type: str = Field(min_length=1, max_length=100)
    error_message: str = Field(min_length=1)
    url: Optional[str] = None
    metadata: Optional[dict] = None

    @field_validator('error_type', 'error_message')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator('metadata')
    @classmethod
    def validate_metadata_size(cls, v: dict | None) -> dict | None:
        if v is not None:
            import json
            if len(json.dumps(v)) > 10240:
                raise ValueError('metadata exceeds 10KB limit')
        return v


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
