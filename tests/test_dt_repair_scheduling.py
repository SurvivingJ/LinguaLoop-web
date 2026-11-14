"""Daily-practice queue rules (tech 7.1-7.3). Pure."""

from datetime import date, datetime, timedelta, timezone

import pytest

from services.dual_translation.repair import scheduling

TODAY = date(2026, 11, 14)


@pytest.mark.parametrize("kind,outcome,level,queued", [
    ("repair", "answer_shown", 4, True),
    ("direct", "shown_directly", 4, True),
    ("repair", "skipped", 0, True),
    ("repair", "self_repaired", 2, True),
    ("repair", "repaired_alternative", 3, True),
    ("repair", "self_repaired", 1, False),
    ("repair", "self_repaired", 0, False),
    ("repair", "disputed", 4, False),
    ("unsure", "unsure_revised", 0, False),
    ("unsure", "unsure_dismissed", 0, False),
    ("unsure", "unsure_skipped", 0, False),
])
def test_queued_on_close(kind, outcome, level, queued):
    assert scheduling.queued_on_close(kind, outcome, level) is queued


def test_first_queue_state_non_utc_learner_day():
    # 23:30 UTC on the 14th is already the 15th for a learner in Tokyo.
    closed = datetime(2026, 11, 14, 23, 30, tzinfo=timezone.utc)
    st = scheduling.first_queue_state(date(2026, 11, 15), closed)
    assert st["queue_status"] == "due" and st["due_on"] == "2026-11-16"
    assert st["not_before"] == (closed + timedelta(hours=20)).isoformat()
    assert st["expires_at"] == (closed + timedelta(days=30)).isoformat()


def _after(outcome, hint=1, sitting=1, failed=0, hinted=0):
    return scheduling.after_sitting(outcome=outcome, sitting_max_hint=hint, sitting=sitting,
                                    failed_sittings=failed, hinted_sittings=hinted, local_today=TODAY)


def test_unaided_fix_resolves():
    assert _after("self_repaired", hint=1)["queue_status"] == "resolved"
    assert _after("repaired_alternative", hint=0)["queue_status"] == "resolved"


def test_hinted_fix_returns_in_three_days():
    out = _after("self_repaired", hint=3)
    assert out["queue_status"] == "due" and out["due_on"] == "2026-11-17" and out["hinted_sittings"] == 1
    assert _after("self_repaired", hint=2, hinted=1)["queue_status"] == "due"


def test_failed_sittings_2_4_retire():
    one = _after("answer_shown", hint=4)
    assert one["due_on"] == "2026-11-16" and one["failed_sittings"] == 1
    two = _after("answer_shown", hint=4, failed=1, sitting=2)
    assert two["due_on"] == "2026-11-18" and two["failed_sittings"] == 2
    assert _after("answer_shown", hint=4, failed=2, sitting=3)["queue_status"] == "retired"


def test_disputed_and_skipped():
    assert _after("disputed")["queue_status"] == "disputed"
    skipped = _after("skipped")
    assert skipped["queue_status"] == "due" and skipped["due_on"] == "2026-11-15"
    assert skipped["failed_sittings"] == 0


def test_max_sittings_retires():
    assert _after("skipped", sitting=5)["queue_status"] == "retired"
    assert _after("self_repaired", hint=1, sitting=5)["queue_status"] == "resolved"


def test_is_due():
    now = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
    base = {"queue_status": "due", "due_on": "2026-11-14",
            "not_before": "2026-11-14T10:00:00+00:00", "expires_at": "2026-12-01T00:00:00+00:00"}
    assert scheduling.is_due(base, TODAY, now)
    assert not scheduling.is_due({**base, "due_on": "2026-11-15"}, TODAY, now)
    assert not scheduling.is_due({**base, "not_before": "2026-11-14T13:00:00+00:00"}, TODAY, now)
    assert not scheduling.is_due({**base, "expires_at": "2026-11-14T11:00:00+00:00"}, TODAY, now)
    assert not scheduling.is_due({**base, "queue_status": "resolved"}, TODAY, now)


def test_due_order():
    items = [{"id": 1, "subtype": "register", "max_hint_level": 4, "queued_at": "b"},
             {"id": 2, "subtype": "meaning_inversion", "max_hint_level": 2, "queued_at": "c"},
             {"id": 3, "subtype": "register", "max_hint_level": 4, "queued_at": "a"},
             {"id": 4, "subtype": "register", "max_hint_level": 2, "queued_at": "a"}]
    assert [i["id"] for i in sorted(items, key=scheduling.due_order_key)] == [2, 3, 1, 4]
