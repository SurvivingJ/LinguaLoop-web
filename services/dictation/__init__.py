"""Dictation grading service.

Word-level alignment + Levenshtein fuzzy match for free-form transcript
scoring. See services/dictation/grader.py for the public API.
"""

from services.dictation.cap import (
    DICTATION_MAX_WORDS,
    MAX_STORED_DIFF_ENTRIES,
    max_words_for_difficulty,
    max_words_for_tier,
)
from services.dictation.grader import (
    GradingResult,
    WordDiff,
    grade_dictation,
)

__all__ = [
    "GradingResult",
    "WordDiff",
    "grade_dictation",
    # TASK-715 tier-scaled transcript cap.
    "DICTATION_MAX_WORDS",
    "MAX_STORED_DIFF_ENTRIES",
    "max_words_for_difficulty",
    "max_words_for_tier",
]
