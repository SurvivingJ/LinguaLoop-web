"""TASK-1211 — FSRS review dating on ONE app-wide review time zone.

Owner decision (2026-11-23): no per-learner local day for flashcards; the FSRS
day rolls over at midnight AEST for everyone. ``services.day_boundary.REVIEW_TIMEZONE``
(Python) and ``public.review_today()`` (SQL, migrations/fsrs_review_today_aest.sql)
are the two places the zone is configured.

Pinned here:
  (a) a review at 23:30 AEST is dated that AEST day; at 00:30 AEST it is dated
      the next one (the UTC date is the same at both instants);
  (b) a card given a 1-day interval is not due again on the same AEST day and
      is due on the next;
  (c) ``/due`` reads with the same date the writers stamp.

Time is frozen by patching ``day_boundary._utcnow`` (the suite has no freezegun).
"""

import json
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services import day_boundary
from services.vocabulary.fsrs import CardState, GOOD, schedule_review

# 2026-11-23 13:30 UTC = 23:30 AEST on the 23rd; 14:30 UTC = 00:30 AEST on the 24th.
BEFORE_MIDNIGHT_AEST = datetime(2026, 11, 23, 13, 30, tzinfo=timezone.utc)
AFTER_MIDNIGHT_AEST = datetime(2026, 11, 23, 14, 30, tzinfo=timezone.utc)


def _freeze(monkeypatch, moment):
    monkeypatch.setattr(day_boundary, '_utcnow', lambda: moment, raising=False)


# ---------------------------------------------------------------------------
# The helper and its configuration
# ---------------------------------------------------------------------------

def test_review_zone_is_aest_without_daylight_saving():
    assert day_boundary.REVIEW_TIMEZONE == 'Australia/Brisbane'
    # Brisbane has no DST: midnight is 14:00 UTC in both January and July.
    assert day_boundary.review_today(datetime(2026, 1, 15, 13, 59, tzinfo=timezone.utc)) == date(2026, 1, 15)
    assert day_boundary.review_today(datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)) == date(2026, 1, 16)
    assert day_boundary.review_today(datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)) == date(2026, 7, 16)


def test_review_today_rolls_over_at_aest_midnight():
    assert day_boundary.review_today(BEFORE_MIDNIGHT_AEST) == date(2026, 11, 23)
    assert day_boundary.review_today(AFTER_MIDNIGHT_AEST) == date(2026, 11, 24)
    assert day_boundary.review_today_iso(AFTER_MIDNIGHT_AEST) == '2026-11-24'


def test_review_today_without_an_argument_reads_the_clock(monkeypatch):
    _freeze(monkeypatch, AFTER_MIDNIGHT_AEST)
    assert day_boundary.review_today() == date(2026, 11, 24)
    assert day_boundary.review_today_iso() == '2026-11-24'


def test_python_and_sql_name_the_same_review_zone():
    """The SQL mirror public.review_today() must use the same zone literal."""
    from pathlib import Path
    import re

    sql = (Path(__file__).resolve().parent.parent / 'migrations' / 'fsrs_review_day_aest.sql').read_text()
    body = sql.split('CREATE OR REPLACE FUNCTION public.review_today(', 1)[1].split('$function$;', 1)[0]
    assert re.findall(r"AT TIME ZONE '([^']+)'", body) == [day_boundary.REVIEW_TIMEZONE]


def test_the_zone_is_one_constant(monkeypatch):
    """Changing the one constant moves every Python reader and writer."""
    monkeypatch.setattr(day_boundary, 'REVIEW_TIMEZONE', 'UTC')
    assert day_boundary.review_today(AFTER_MIDNIGHT_AEST) == date(2026, 11, 23)


# ---------------------------------------------------------------------------
# (a) writers date the review on the AEST day
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('moment, expected', [
    (BEFORE_MIDNIGHT_AEST, date(2026, 11, 23)),
    (AFTER_MIDNIGHT_AEST, date(2026, 11, 24)),
])
def test_schedule_review_defaults_to_the_review_day(monkeypatch, moment, expected):
    _freeze(monkeypatch, moment)
    new = schedule_review(CardState(), GOOD)
    assert new.last_review == expected


class _Q:
    def __init__(self, log, table):
        self.log, self.table, self.payload = log, table, None

    def update(self, row):
        self.payload = row
        return self

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        self.log.append((self.table, self.payload))
        return SimpleNamespace(data=[])


class _DB:
    def __init__(self):
        self.log = []

    def table(self, name):
        return _Q(self.log, name)


@pytest.mark.parametrize('moment, expected', [
    (BEFORE_MIDNIGHT_AEST, '2026-11-23'),
    (AFTER_MIDNIGHT_AEST, '2026-11-24'),
])
def test_practice_attempt_stamps_the_review_day(monkeypatch, moment, expected):
    from services.practice_session_service import PracticeSessionService

    _freeze(monkeypatch, moment)
    svc = PracticeSessionService.__new__(PracticeSessionService)
    svc.db = _DB()
    row = {'id': 9, 'stability': 0.5, 'difficulty': 5.0, 'due_date': '2026-11-20',
           'last_review': '2026-11-19T00:00:00+00:00', 'reps': 2, 'lapses': 0,
           'state': 'learning'}
    svc._apply_fsrs_review(row, 42, True, 9000)
    ((table, payload),) = [e for e in svc.db.log if e[1] is not None]
    assert table == 'user_flashcards'
    assert payload['last_review'] == expected
    # the 1-day interval is counted from the same day
    assert payload['due_date'] == (date.fromisoformat(expected) + timedelta(days=1)).isoformat()


# ---------------------------------------------------------------------------
# Flashcard routes: (a) review writer, (b) 1-day interval, (c) /due
# ---------------------------------------------------------------------------

def _chain(data, count=None):
    chain = MagicMock()
    chain.execute.return_value = SimpleNamespace(data=data, count=count or 0)
    for m in ('select', 'eq', 'neq', 'lte', 'single', 'order', 'or_',
              'limit', 'offset', 'insert', 'update', 'delete', 'filter'):
        getattr(chain, m).return_value = chain
    return chain


LEARNING_CARD = {'id': 7, 'sense_id': 42, 'language_id': 1, 'stability': 0.5,
                 'difficulty': 5.0, 'due_date': '2026-11-23',
                 'last_review': '2026-11-22T00:00:00+00:00', 'reps': 2, 'lapses': 0,
                 'state': 'learning'}


def _review(client, auth_headers, monkeypatch, moment):
    _freeze(monkeypatch, moment)
    chain = _chain(dict(LEARNING_CARD))
    db = MagicMock()
    db.table.return_value = chain
    with patch('routes.flashcards.get_db', return_value=db), \
            patch('routes.flashcards.VocabularyKnowledgeService'):
        resp = client.post('/api/flashcards/review', headers=auth_headers,
                           json={'card_id': 7, 'rating': GOOD})
    assert resp.status_code == 200, resp.data
    return chain.update.call_args[0][0]


def _due_today(client, auth_headers, monkeypatch, moment):
    """The date /due filters with (``due_date.lte.<today>``)."""
    _freeze(monkeypatch, moment)
    chain = _chain([])
    db = MagicMock()
    db.table.return_value = chain
    with patch('routes.flashcards.get_db', return_value=db), \
            patch('services.vocabulary.gloss_lookup.get_user_definition_language_id', return_value=None):
        resp = client.get('/api/flashcards/due?language_id=1', headers=auth_headers)
    assert resp.status_code == 200, resp.data
    (filt,) = chain.or_.call_args[0]
    return filt.split(',')[0].split('due_date.lte.')[1]


@pytest.mark.parametrize('moment, expected', [
    (BEFORE_MIDNIGHT_AEST, '2026-11-23'),
    (AFTER_MIDNIGHT_AEST, '2026-11-24'),
])
def test_review_route_stamps_the_review_day(client, auth_headers, monkeypatch, moment, expected):
    payload = _review(client, auth_headers, monkeypatch, moment)
    assert payload['last_review'] == expected


def test_one_day_interval_is_not_due_the_same_aest_day_but_is_the_next(client, auth_headers, monkeypatch):
    # Reviewed at 00:30 AEST on the 24th (14:30 UTC on the 23rd).
    payload = _review(client, auth_headers, monkeypatch, AFTER_MIDNIGHT_AEST)
    assert payload['last_review'] == '2026-11-24'
    assert payload['due_date'] == '2026-11-25'          # a 1-day interval

    # 23:30 AEST on the 24th (13:30 UTC on the 24th): same AEST day, not due.
    same_day = datetime(2026, 11, 24, 13, 30, tzinfo=timezone.utc)
    today = _due_today(client, auth_headers, monkeypatch, same_day)
    assert today == '2026-11-24'
    assert not payload['due_date'] <= today

    # 00:30 AEST on the 25th (14:30 UTC on the 24th): the next AEST day, due —
    # although the UTC date has not changed since the previous check.
    next_day = datetime(2026, 11, 24, 14, 30, tzinfo=timezone.utc)
    today = _due_today(client, auth_headers, monkeypatch, next_day)
    assert today == '2026-11-25'
    assert payload['due_date'] <= today


@pytest.mark.parametrize('moment', [BEFORE_MIDNIGHT_AEST, AFTER_MIDNIGHT_AEST])
def test_due_reads_with_the_writers_date(client, auth_headers, monkeypatch, moment):
    written = _review(client, auth_headers, monkeypatch, moment)['last_review']
    assert _due_today(client, auth_headers, monkeypatch, moment) == written


def test_due_route_response_is_unchanged_in_shape(client, auth_headers, monkeypatch):
    _freeze(monkeypatch, AFTER_MIDNIGHT_AEST)
    chain = _chain([])
    db = MagicMock()
    db.table.return_value = chain
    with patch('routes.flashcards.get_db', return_value=db):
        resp = client.get('/api/flashcards/due?language_id=1', headers=auth_headers)
    assert json.loads(resp.data)['total'] == 0
