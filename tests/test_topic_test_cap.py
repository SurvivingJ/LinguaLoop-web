"""TASK-740 Phase 4: bounded, spaced test fan-out per topic.

Finding #2 (2026-08-29 review): a topic re-entering `production_queue` had
nothing stopping it from generating an unbounded number of near-duplicate
tests over time — Phase 2 already collapsed generation to exactly one test
per topic per pass, at its mandatory `target_age_tier`, but nothing capped
how many *passes* a topic could go through. This file pins:

1. Under the cap: generation proceeds as normal.
2. At/over the cap: generation is skipped (and logged), the queue item is
   still marked complete with 0 tests, and `_generate_test` is never called.
3. The recency window boundary: `count_recent_tests_for_topic` is called
   with the configured window, and results outside that window (an old
   topic revisited after the window is 0 recent tests) don't count against
   the cap.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.test_generation.config import TestGenConfig
from services.test_generation.database_client import LanguageConfig, Topic
from services.test_generation.orchestrator import QueueItem, TestGenerationOrchestrator


def _orchestrator(db):
    """An orchestrator without __init__ — it reads live config/agents."""
    orch = object.__new__(TestGenerationOrchestrator)
    orch.db = db
    return orch


def _topic(tier_id=3):
    return Topic(
        id=uuid4(),
        category_id=1,
        concept_english='harbour seals',
        lens_id=1,
        keywords=[],
        semantic_signature=None,
        target_age_tier=tier_id,
        distinctive_vocabulary=[],
    )


def _lang_config():
    return LanguageConfig(
        id=1, language_code='en', language_name='English', native_name='English',
        prose_model='m', question_model='m', tts_voice_ids=['alloy'],
        tts_speed=1.0, grammar_check_enabled=False,
    )


def _queue_item(topic_id, language_id=1):
    return QueueItem(
        id=uuid4(), topic_id=topic_id, language_id=language_id,
        status_id=1, created_at=datetime.now(timezone.utc),
    )


def _fake_config(max_tests_per_topic=3, window_days=30):
    cfg = TestGenConfig.__new__(TestGenConfig)
    cfg.max_tests_per_topic = max_tests_per_topic
    cfg.topic_recency_window_days = window_days
    return cfg


def _make_db(topic, lang_config, recent_count):
    db = MagicMock()
    db.get_topic.return_value = topic
    db.get_language_config.return_value = lang_config
    db.get_category_name.return_value = 'Nature'
    db.count_recent_tests_for_topic.return_value = recent_count
    return db


def test_under_cap_generates_normally():
    topic = _topic()
    item = _queue_item(topic.id)
    db = _make_db(topic, _lang_config(), recent_count=1)
    orch = _orchestrator(db)

    with patch(
        'services.test_generation.orchestrator.get_test_gen_config',
        return_value=_fake_config(max_tests_per_topic=3, window_days=30),
    ), patch.object(orch, '_generate_test', return_value=True) as gen:
        result = orch._process_queue_item(item, dry_run=False)

    gen.assert_called_once()
    assert result == 1
    db.mark_queue_completed.assert_called_once_with(item.id, 1)


def test_at_cap_skips_and_logs(caplog):
    topic = _topic()
    item = _queue_item(topic.id)
    db = _make_db(topic, _lang_config(), recent_count=3)
    orch = _orchestrator(db)

    with patch(
        'services.test_generation.orchestrator.get_test_gen_config',
        return_value=_fake_config(max_tests_per_topic=3, window_days=30),
    ), patch.object(orch, '_generate_test', return_value=True) as gen, \
            caplog.at_level('INFO'):
        result = orch._process_queue_item(item, dry_run=False)

    gen.assert_not_called()
    assert result == 0
    db.mark_queue_completed.assert_called_once_with(item.id, 0)
    assert any('Skipping topic' in r.message for r in caplog.records)


def test_over_cap_skips():
    topic = _topic()
    item = _queue_item(topic.id)
    db = _make_db(topic, _lang_config(), recent_count=5)
    orch = _orchestrator(db)

    with patch(
        'services.test_generation.orchestrator.get_test_gen_config',
        return_value=_fake_config(max_tests_per_topic=3, window_days=30),
    ), patch.object(orch, '_generate_test', return_value=True) as gen:
        result = orch._process_queue_item(item, dry_run=False)

    gen.assert_not_called()
    assert result == 0


def test_dry_run_skip_does_not_write():
    """Skip path must respect dry_run the same way the normal path does."""
    topic = _topic()
    item = _queue_item(topic.id)
    db = _make_db(topic, _lang_config(), recent_count=3)
    orch = _orchestrator(db)

    with patch(
        'services.test_generation.orchestrator.get_test_gen_config',
        return_value=_fake_config(max_tests_per_topic=3, window_days=30),
    ), patch.object(orch, '_generate_test', return_value=True):
        orch._process_queue_item(item, dry_run=True)

    db.mark_queue_completed.assert_not_called()
    db.mark_queue_processing.assert_not_called()


def test_count_recent_tests_for_topic_called_with_configured_window():
    """The cap check must pass the configured recency window through to the
    DB query, not a hardcoded value — this is what makes the window
    boundary configurable/testable at all."""
    topic = _topic()
    item = _queue_item(topic.id)
    db = _make_db(topic, _lang_config(), recent_count=0)
    orch = _orchestrator(db)

    with patch(
        'services.test_generation.orchestrator.get_test_gen_config',
        return_value=_fake_config(max_tests_per_topic=3, window_days=7),
    ), patch.object(orch, '_generate_test', return_value=True):
        orch._process_queue_item(item, dry_run=False)

    db.count_recent_tests_for_topic.assert_called_once_with(topic.id, 7)


def test_window_boundary_old_test_not_counted():
    """A topic whose only prior test falls outside the recency window has
    0 recent tests and must not be skipped, even though it has generated
    tests before. This is exercised at the database_client level: the
    query only counts rows with created_at >= cutoff, so a test older than
    the window is excluded by construction."""
    from datetime import datetime, timedelta, timezone

    from services.test_generation.database_client import TestDatabaseClient

    db = object.__new__(TestDatabaseClient)
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.count = 0
    fake_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = fake_response
    db.client = fake_client

    topic_id = uuid4()
    count = db.count_recent_tests_for_topic(topic_id, window_days=30)

    assert count == 0
    fake_client.table.assert_called_with('tests')
    # The cutoff passed to .gte() must be ~30 days back, not some other value.
    gte_call = fake_client.table.return_value.select.return_value.eq.return_value.gte
    cutoff_arg = gte_call.call_args.args[1]
    cutoff_dt = datetime.fromisoformat(cutoff_arg)
    expected = datetime.now(timezone.utc) - timedelta(days=30)
    assert abs((cutoff_dt - expected).total_seconds()) < 5
