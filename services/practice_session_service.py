"""
Practice Session Service — unified vocabulary practice surface.

Module-level factory:
  get_practice_session_service()  → returns a process-wide singleton.

Back-compat method retained on PracticeSessionService:
  mark_exercise_complete(...)        ← no-op under the merged engine


Replaces the split between the legacy daily-mixed-session and vocab-dojo
session RPCs with a single mode-dispatched RPC `get_practice_session`.
See [[features/practice-engine.tech]] and ADR-007.

Modes:
  - acquisition  : word-anchored loop (one word → K family-targeted items →
                   inline gate / stress markers)
  - maintenance  : batch-anchored over FSRS-due / BKT-decayed senses, falls
                   through to acquisition if pool empties before time-up
  - auto         : dispatcher (FSRS+decayed >= ladder-active → maintenance)

The methods live in services/practice/ (session_assembly, attempt_recording,
new_word_admission); this module composes them and stays the import point.

This service:
  1. Wraps the RPC for `/api/practice/session` handlers.
  2. Implements ladder top-up (R4.9) from the learner's own evidence before
     calling the RPC. (Pack-based intake was archived 2026-09-21 with the
     language-packs feature — archive/modules/language-packs-2026-09-21.zip.)
  3. Records attempts via record_attempt_with_updates — same logic as
     legacy ExerciseSessionService but with an added session_mode parameter
     that propagates to record_session_progress for weekly counter updates.

Renamed from services/exercise_session_service.py (TASK-106). The legacy
class/factory aliases and the compatibility shim were removed in TASK-220
once the deprecation window elapsed.

Follows the singleton pattern used by TestService / VocabularyKnowledgeService.
"""

from __future__ import annotations

import logging
from typing import Optional

from services import study_plan_service as _plan  # noqa: F401  (read as pss._plan)
from services.practice.attempt_recording import AttemptRecordingMixin
from services.practice.constants import *  # noqa: F401,F403  (tunables, importable from here)
from services.practice.new_word_admission import NewWordAdmissionMixin
from services.practice.session_assembly import SessionAssemblyMixin
from services.supabase_factory import get_supabase_admin

logger = logging.getLogger(__name__)


class PracticeSessionService(
    SessionAssemblyMixin, AttemptRecordingMixin, NewWordAdmissionMixin,
):
    """Unified Practice surface. Wraps get_practice_session + attempt recording."""

    def __init__(self, db=None):
        self.db = db or get_supabase_admin()


# ---------------------------------------------------------------------------
# Module-level singleton factory (matches the codebase pattern used by
# TestService, AuthService, etc.)
# ---------------------------------------------------------------------------
_singleton: Optional[PracticeSessionService] = None


def get_practice_session_service() -> PracticeSessionService:
    """Process-wide singleton."""
    global _singleton
    if _singleton is None:
        _singleton = PracticeSessionService()
    return _singleton
