"""TASK-702 — hydration-shortfall surfacing.

Unit-covers the service-layer half of the fix: ``TestService`` must log a
WARNING whenever ``build_daily_session`` budgeted more test slots for a skill
than it could hydrate (``hydrated_counts[skill] < requested_counts[skill]``).

The RPC half (requested/hydrated counts + the replay fallback + used_minutes)
is verified against the live DB in the migration's acceptance query; here we
pin the Python contract so a future refactor can't silently drop the WARNING.
"""

import logging

from services.test_service import TestService


def test_warns_when_hydrated_below_requested(caplog):
    """The verification scenario: reading budgeted 4, only 2 primary-hydrated,
    with no replay available -> 2 slots dropped."""
    resolver_result = {
        'load_id': 1,
        'requested_counts': {'reading': 4, 'listening': 2},
        'hydrated_counts': {'reading': 2, 'listening': 2},
        'replay_counts': {},
    }
    with caplog.at_level(logging.WARNING, logger='services.test_service'):
        TestService._log_hydration_shortfalls('u-1', 3, resolver_result)

    shortfall_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and 'hydration shortfall' in r.getMessage()
    ]
    assert len(shortfall_warnings) == 1
    msg = shortfall_warnings[0].getMessage()
    assert 'skill=reading' in msg
    assert 'requested=4' in msg
    assert 'hydrated=2' in msg
    assert 'DROPPED' in msg
    # listening was fully hydrated -> no warning for it
    assert 'skill=listening' not in msg


def test_no_warning_when_fully_hydrated(caplog):
    resolver_result = {
        'requested_counts': {'reading': 3},
        'hydrated_counts': {'reading': 3},
        'replay_counts': {},
    }
    with caplog.at_level(logging.WARNING, logger='services.test_service'):
        TestService._log_hydration_shortfalls('u-1', 3, resolver_result)
    assert not [
        r for r in caplog.records if r.levelno == logging.WARNING
    ]


def test_replay_covered_gap_still_warns(caplog):
    """The full verification scenario: reading budgeted 4, only 2 never-attempted
    hydrated, replay covers the other 2. Still a WARNING (primary pool dry), but
    the message records that replay covered the gap with nothing dropped."""
    resolver_result = {
        'requested_counts': {'reading': 4},
        'hydrated_counts': {'reading': 2},   # primary / never-attempted only
        'replay_counts': {'reading': 2},
    }
    with caplog.at_level(logging.WARNING, logger='services.test_service'):
        TestService._log_hydration_shortfalls('u-1', 3, resolver_result)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    msg = warnings[0].getMessage()
    assert 'requested=4' in msg
    assert 'hydrated=2' in msg
    assert 'replay covered' in msg
    assert 'DROPPED' not in msg


def test_missing_skill_in_hydrated_counts_treated_as_zero(caplog):
    """A skill that hydrated nothing is absent from hydrated_counts -> warn."""
    resolver_result = {
        'requested_counts': {'pitch_accent': 1},
        'hydrated_counts': {},
        'replay_counts': {},
    }
    with caplog.at_level(logging.WARNING, logger='services.test_service'):
        TestService._log_hydration_shortfalls('u-1', 5, resolver_result)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert 'hydrated=0' in warnings[0].getMessage()


def test_missing_count_fields_are_safe(caplog):
    """A legacy resolver payload without the new fields must not raise."""
    with caplog.at_level(logging.WARNING, logger='services.test_service'):
        TestService._log_hydration_shortfalls('u-1', 3, {'load_id': 7})
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]
