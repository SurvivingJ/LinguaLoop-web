"""
DEPRECATED 2026-05-21 — moved to services.practice_session_service.

This shim re-exports ExerciseSessionService so existing callers
(routes/exercises.py, tests, scripts) keep working. Remove after the
deprecation cycle ends (TASK-220, T+30 days post Study Plans flip).

See [[features/practice-engine.tech]] and ADR-007 for the merger rationale.
"""

from services.practice_session_service import (  # noqa: F401
    PracticeSessionService,
    ExerciseSessionService,
)
