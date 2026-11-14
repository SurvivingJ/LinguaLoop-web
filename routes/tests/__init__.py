"""Test routes - test catalogue, opening a test, submission, sentences and
prestudy. One blueprint (``tests``) across the modules of this package.

The names below are imported by other route modules and by tests
(``from routes.tests import ...``); keep them importable from here.
"""

from services.test_service import DimensionService, TestService, get_test_service

from .blueprint import tests_bp
from . import catalog, submit, sentences, prestudy  # noqa: F401  (register the routes)
from .catalog import normalize_audio_url
from .submit import (
    _apply_timing_and_progress,
    _attach_explanations,
    _build_submission_response,
    _call_dictation_submission_rpc,
    _call_pinyin_submission_rpc,
    _call_pitch_accent_submission_rpc,
    _call_submission_rpc,
    _complete_daily_slot,
    _credit_attempt_window,
    _is_missing_function_error,
    _normalize_timing,
    _submission_failure_response,
    _unwrap_rpc_response,
    _update_vocabulary_tracking,
)
from .sentences import (
    _has_attempt_today,
    _load_active_references,
    _load_sentence_rows,
    _resolve_sentence_l1,
    build_sentence_payload,
)
from .prestudy import _PRESTUDY_MAX_ANSWERS, _PRESTUDY_MAX_EXERCISE_ANSWERS

__all__ = [
    'tests_bp', 'DimensionService', 'TestService', 'get_test_service', 'normalize_audio_url',
    '_apply_timing_and_progress', '_attach_explanations', '_build_submission_response',
    '_call_dictation_submission_rpc', '_call_pinyin_submission_rpc',
    '_call_pitch_accent_submission_rpc', '_call_submission_rpc', '_complete_daily_slot',
    '_credit_attempt_window', '_is_missing_function_error', '_normalize_timing',
    '_submission_failure_response', '_unwrap_rpc_response', '_update_vocabulary_tracking',
    '_has_attempt_today', '_load_active_references', '_load_sentence_rows',
    '_resolve_sentence_l1', 'build_sentence_payload',
    '_PRESTUDY_MAX_ANSWERS', '_PRESTUDY_MAX_EXERCISE_ANSWERS',
]
