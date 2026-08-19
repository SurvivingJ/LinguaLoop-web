"""TASK-716 / ADR-022 — local-day boundary resolution.

Pins the three things the ADR calls out as load-bearing:
  1. the date is the LEARNER's, not UTC's;
  2. an unusable timezone fails safe to UTC and never raises inside the
     resolver (ADR-020);
  3. routes/study_session.py and services/test_service.py derive it from ONE
     helper, so a single request cannot see two different "today"s.
"""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from services import day_boundary
from services.day_boundary import (
    DEFAULT_TIMEZONE,
    is_valid_timezone,
    local_date,
    local_today_iso,
    plan_timezone,
    plan_today_iso,
    resolve_zone,
)


def _fake_db(rows):
    """Minimal supabase-py stand-in for the single query plan_timezone makes."""
    db = MagicMock()
    chain = db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value
    chain.execute.return_value = MagicMock(data=rows)
    return db


# ---------------------------------------------------------------------------
# 1. The learner's date, not UTC's
# ---------------------------------------------------------------------------

# 15:30 UTC on 2026-08-07 is 00:30 on 2026-08-08 in Tokyo (UTC+9).
FROZEN = datetime(2026, 8, 7, 15, 30, tzinfo=timezone.utc)


def test_utc_plus_9_gets_the_next_local_date():
    assert local_date('Asia/Tokyo', FROZEN) == date(2026, 8, 8)


def test_utc_plan_gets_the_current_date_at_the_same_instant():
    assert local_date('UTC', FROZEN) == date(2026, 8, 7)


def test_utc_plus_9_learner_at_22_00_local_gets_their_own_date():
    """The ADR's headline symptom: an evening learner must not be handed
    tomorrow's load. 22:00 Tokyo on the 7th is 13:00 UTC on the 7th."""
    at_22_local = datetime(2026, 8, 7, 13, 0, tzinfo=timezone.utc)
    assert local_date('Asia/Tokyo', at_22_local) == date(2026, 8, 7)


def test_negative_offset_can_still_be_the_previous_date():
    # 15:30 UTC is 08:30 the same day in Los Angeles (UTC-7 in August)...
    assert local_date('America/Los_Angeles', FROZEN) == date(2026, 8, 7)
    # ...but 02:00 UTC on the 8th is still the 7th there.
    early = datetime(2026, 8, 8, 2, 0, tzinfo=timezone.utc)
    assert local_date('America/Los_Angeles', early) == date(2026, 8, 7)


def test_naive_datetime_is_treated_as_utc():
    assert local_date('Asia/Tokyo', datetime(2026, 8, 7, 15, 30)) == date(2026, 8, 8)


# ---------------------------------------------------------------------------
# 2. Fail-safe to UTC (ADR-020) — never raises
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('bad', [
    None,
    '',
    '   ',
    'Not/AZone',
    'es',              # a UI locale, which V1 validation would have accepted
    '+09:00',          # a raw offset, not an IANA name
    12345,             # not even a string
])
def test_unusable_timezone_yields_the_utc_date_rather_than_raising(bad):
    assert local_date(bad, FROZEN) == date(2026, 8, 7)


def test_resolve_zone_never_raises_and_falls_back_to_utc():
    assert resolve_zone('Nope/Nope') is timezone.utc
    assert resolve_zone(None) is timezone.utc


def test_is_valid_timezone_accepts_iana_and_rejects_the_rest():
    assert is_valid_timezone('Asia/Tokyo')
    assert is_valid_timezone('UTC')
    assert not is_valid_timezone('es')
    assert not is_valid_timezone('')
    assert not is_valid_timezone(None)
    assert not is_valid_timezone('+09:00')


def test_plan_timezone_falls_back_when_the_db_raises():
    db = MagicMock()
    db.table.side_effect = RuntimeError('connection reset')
    assert plan_timezone(db, 'u1', 1) == DEFAULT_TIMEZONE


def test_plan_timezone_falls_back_when_no_plan_row_exists():
    assert plan_timezone(_fake_db([]), 'u1', 1) == DEFAULT_TIMEZONE


def test_plan_timezone_falls_back_on_a_null_column():
    assert plan_timezone(_fake_db([{'timezone': None}]), 'u1', 1) == DEFAULT_TIMEZONE


def test_plan_today_iso_uses_the_stored_zone():
    db = _fake_db([{'timezone': 'Asia/Tokyo'}])
    assert plan_today_iso(db, 'u1', 1, FROZEN) == '2026-08-08'


def test_plan_today_iso_with_a_garbage_stored_zone_is_the_utc_date():
    db = _fake_db([{'timezone': 'Mars/Olympus_Mons'}])
    assert plan_today_iso(db, 'u1', 1, FROZEN) == '2026-08-07'


# ---------------------------------------------------------------------------
# 3. ONE derivation — the divergence the ADR warns about
# ---------------------------------------------------------------------------

def test_route_and_service_resolve_through_the_same_helper():
    """Both call sites must funnel into services.day_boundary.

    If either grows its own datetime.now(timezone.utc).date() again, one
    request can key daily_test_loads under two different dates — silent and
    very hard to trace. Asserting on the imported symbol is the cheapest way
    to keep that from regressing.
    """
    import routes.study_session as study_session
    import services.test_service as test_service

    assert study_session.plan_today_iso is day_boundary.plan_today_iso
    assert test_service.plan_today_iso is day_boundary.plan_today_iso


def test_route_today_iso_delegates(monkeypatch):
    import routes.study_session as study_session

    seen = {}

    def fake(db, user_id, language_id, *a, **kw):
        seen['args'] = (user_id, language_id)
        return '2026-08-08'

    monkeypatch.setattr(study_session, 'plan_today_iso', fake)
    assert study_session._today_iso(object(), 'u1', 3) == '2026-08-08'
    assert seen['args'] == ('u1', 3)


def test_local_today_iso_matches_local_date():
    assert local_today_iso('Asia/Tokyo', FROZEN) == local_date('Asia/Tokyo', FROZEN).isoformat()
