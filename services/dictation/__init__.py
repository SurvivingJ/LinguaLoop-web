"""Dictation grading service.

Word-level alignment + Levenshtein fuzzy match for free-form transcript
scoring. See services/dictation/grader.py for the public API.
"""

from services.dictation.grader import (
    GradingResult,
    WordDiff,
    grade_dictation,
)

__all__ = ["GradingResult", "WordDiff", "grade_dictation"]
