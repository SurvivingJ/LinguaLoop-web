"""Queue item status on generation failure (D-10, D-11).

* D-10: a non-judge exception from `_generate_test` used to be swallowed and the
  item marked completed with 0 tests (never retried, looked successful). It must
  propagate so the run loop marks the item failed.
* D-11: a JudgeUnavailable abort used to leave the item in 'processing' forever
  (later runs select only 'pending'). It must be returned to 'pending' first.

An item has exactly one test (single mandatory tier), so there is no partial
success: `_generate_test` returning False (a legitimate rejection) still
completes with 0 tests, as before.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.exercise_generation.judges.base import JudgeUnavailable
from services.test_generation.database_client import LanguageConfig, Topic
from services.test_generation.orchestrator import QueueItem, TestGenerationOrchestrator


def _setup():
    topic = Topic(
        id=uuid4(), category_id=1, concept_english='seals', lens_id=1,
        keywords=[], semantic_signature=None, target_age_tier=3,
        distinctive_vocabulary=[],
    )
    lang = LanguageConfig(
        id=1, language_code='en', language_name='English', native_name='English',
        prose_model='m', question_model='m', tts_voice_ids=['alloy'],
        tts_speed=1.0, grammar_check_enabled=False,
    )
    item = QueueItem(
        id=uuid4(), topic_id=topic.id, language_id=1, status_id=1,
        created_at=datetime.now(timezone.utc),
    )
    db = MagicMock()
    db.get_topic.return_value = topic
    db.get_language_config.return_value = lang
    db.get_category_name.return_value = 'Nature'
    db.count_recent_tests_for_topic.return_value = 0
    db.get_pending_queue_items.return_value = [item]
    o = object.__new__(TestGenerationOrchestrator)
    o.db = db
    o.metrics = None
    o._finalize = lambda start, dry: o.metrics
    cfg = SimpleNamespace(
        dry_run=False, batch_size=1, topic_recency_window_days=7,
        max_tests_per_topic=3,
    )
    return o, db, item, cfg


def test_generation_exception_marks_item_failed_not_completed():
    o, db, item, cfg = _setup()
    with patch('services.test_generation.orchestrator.get_test_gen_config', lambda: cfg), \
            patch.object(o, '_generate_test', side_effect=RuntimeError('llm down')):
        o._run_impl()
    db.mark_queue_completed.assert_not_called()
    db.mark_queue_failed.assert_called_once()
    assert 'llm down' in db.mark_queue_failed.call_args.args[1]
    assert o.metrics.tests_failed == 1


def test_rejected_test_still_completes_with_zero():
    o, db, item, cfg = _setup()
    with patch('services.test_generation.orchestrator.get_test_gen_config', lambda: cfg), \
            patch.object(o, '_generate_test', return_value=False):
        o._run_impl()
    db.mark_queue_completed.assert_called_once_with(item.id, 0)
    db.mark_queue_failed.assert_not_called()


def test_judge_unavailable_returns_item_to_pending_then_aborts():
    o, db, item, cfg = _setup()
    with patch('services.test_generation.orchestrator.get_test_gen_config', lambda: cfg), \
            patch.object(o, '_generate_test', side_effect=JudgeUnavailable('dead')):
        with pytest.raises(JudgeUnavailable):
            o._run_impl()
    db.update_queue_item_status.assert_called_once_with(item.id, 'pending')
    db.mark_queue_failed.assert_not_called()
    db.mark_queue_completed.assert_not_called()


def test_judge_unavailable_in_dry_run_writes_nothing():
    o, db, item, cfg = _setup()
    cfg.dry_run = True
    with patch('services.test_generation.orchestrator.get_test_gen_config', lambda: cfg), \
            patch.object(o, '_generate_test', side_effect=JudgeUnavailable('dead')):
        with pytest.raises(JudgeUnavailable):
            o._run_impl()
    db.update_queue_item_status.assert_not_called()
