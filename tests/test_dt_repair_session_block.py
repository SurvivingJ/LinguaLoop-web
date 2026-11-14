"""The dt_repair block of the daily study session (tech 7.6)."""

from datetime import date
from types import SimpleNamespace

import pytest
from flask import Flask

from services.dual_translation.repair import service as repair_service
from services.dual_translation.repair import settings as repair_settings
from services.study_session import queue as q
from services.study_session import session


def test_status():
    assert q.dt_repair_status({}, []) == "check"
    assert q.dt_repair_status({}, ["dt_repair"]) == "done"
    assert q.dt_repair_status({"excluded_modules": ["dual_translation"]}, []) == "off"
    assert q.dt_repair_status({}, [], enabled=False) == "off"


def test_placement():
    dt = {"kind": "dual_translation", "id": "dual_translation_1"}
    pr = {"kind": "practice", "id": "practice_acq_1"}
    t = {"kind": "test", "id": "t1"}
    assert [i["id"] for i in q.insert_dt_repair([t, pr, dt], 2, False)] == ["t1", "practice_acq_1", "dt_repair", "dual_translation_1"]
    assert [i["id"] for i in q.insert_dt_repair([t, pr], 2, False)] == ["t1", "dt_repair", "practice_acq_1"]
    out = q.insert_dt_repair([t], 2, False)
    assert out[-1] == {"kind": "dt_repair", "id": "dt_repair", "items": 2, "is_completed": False}


def test_no_weekly_credit():
    assert q.surface_skill_for("dt_repair") is None


def test_with_dt_repair():
    assert session.with_dt_repair([], "check", {"dt_repair_due": (0, None)}) == []
    assert session.with_dt_repair([], "check", {"dt_repair_due": (3, None)})[0]["items"] == 3
    assert session.with_dt_repair([], "check", {"dt_repair_due": (None, RuntimeError("x"))}) == []
    assert session.with_dt_repair([], "off", {}) == []
    assert session.with_dt_repair([], "done", {})[0]["is_completed"] is True


def _build(monkeypatch, targets, completed=(), count=2):
    from services import intro_drill
    import services.vocabulary_ladder.speed_round as sr
    monkeypatch.setattr(intro_drill, "ENABLED", False)
    monkeypatch.setattr(sr, "get_speed_round_composer",
                        lambda: SimpleNamespace(has_enough_mastered=lambda u, l: False))
    calls = []

    def count_due(db, u, lang, today):
        calls.append((u, lang, today))
        if isinstance(count, Exception):
            raise count
        return count
    monkeypatch.setattr(repair_service, "count_due", count_due)
    test_service = SimpleNamespace(get_or_create_daily_load=lambda u, l: {'tests': [], 'load_date': '2026-11-14'})
    practice = SimpleNamespace(admit_daily_new_words=lambda u, l: {'admitted': [], 'needs_rebuild': False},
                               new_word_state=lambda u, l: None)
    query = SimpleNamespace(execute=lambda: SimpleNamespace(data=[
        {'daily_session_targets': targets, 'completed_blocks': list(completed)}]))
    for name in ('select', 'eq', 'limit'):
        setattr(query, name, lambda *a, **k: query)
    db = SimpleNamespace(table=lambda name: query)
    with Flask(__name__).test_request_context('/api/study-session?language_id=2'):
        body = session.build_study_session(db, 'u', 2, '2026-11-14', test_service=test_service,
                                           practice_service=practice, mpnw=lambda: 3.0)
    return body, calls


def _ids(body):
    return [i["id"] for i in body["queue"]]


def test_block_present_when_due(monkeypatch):
    body, calls = _build(monkeypatch, {})
    assert "dt_repair" in _ids(body) and calls == [("u", 2, "2026-11-14")]
    assert body["progress"]["total"] == len(body["queue"])


def test_no_block_without_due_items(monkeypatch):
    assert "dt_repair" not in _ids(_build(monkeypatch, {}, count=0)[0])


def test_no_block_when_dt_excluded_or_flag_off(monkeypatch):
    body, calls = _build(monkeypatch, {"excluded_modules": ["dual_translation"]})
    assert "dt_repair" not in _ids(body) and calls == []
    monkeypatch.setattr(repair_settings, "DT_GUIDED_REPAIR", False)
    body, calls = _build(monkeypatch, {})
    assert "dt_repair" not in _ids(body) and calls == []


def test_done_stays_completed(monkeypatch):
    body, calls = _build(monkeypatch, {}, completed=["dt_repair"])
    block = next(i for i in body["queue"] if i["id"] == "dt_repair")
    assert block["is_completed"] is True and calls == []


def test_counting_failure_means_no_block(monkeypatch):
    body, _ = _build(monkeypatch, {}, count=RuntimeError("relation does not exist"))
    assert "dt_repair" not in _ids(body)


def test_complete_block_accepts_dt_repair():
    updates = []
    row = {'id': 1, 'completed_blocks': [], 'daily_session_targets': {}, 'test_ids': []}

    class Q:
        def __getattr__(self, n): return lambda *a, **k: self
        def update(self, payload):
            updates.append(payload)
            return self
        def execute(self): return SimpleNamespace(data=[row])
    db = SimpleNamespace(table=lambda name: Q(), rpc=lambda *a: (_ for _ in ()).throw(AssertionError("no rpc")))
    blocks = session.complete_block(db, 'u', 2, '2026-11-14', 'dt_repair')
    assert blocks == ['dt_repair'] and updates == [{'completed_blocks': ['dt_repair']}]
