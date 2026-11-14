"""Guided-repair service orchestration (tech 3.3, 4, 7) against an in-memory
store. ``store`` functions, the clock, the learner day, the language codes, the
budget and ``recheck.recheck_sentence`` are monkeypatched; nothing touches a DB
or the network.

``FakeStore`` / ``scenario`` are reused by the route and submit-hook tests.
"""

import copy
import itertools
import json
from datetime import date, datetime, timedelta, timezone

import pytest

from services.dual_translation.repair import budget, hooks, recheck, service, settings, store
from services.dual_translation.sentence_refs import LANG_CODE

USER = "test-user-id-123"
OTHER = "someone-else"
GOLD = ("It's a great way to learn by doing. Arduino is a powerful tool. "
        "You can make many things with it. This arm is one idea.")
REPRO = ("It's a sick way to learn by doing. Arduino is a powerful tool. "
         "You can make many things without it. This arm is one idea.")
L1_TEXT = "这是一个在实践中学习的好方法。Arduino 是强大的工具。你可以用它做很多东西。这个机械臂只是一个想法。"
NOTE = "“sick” 是俚语，这里应该用 “great”。"
EXPLANATION_2 = "Meaning reversed: “without it” → “with it”."


def _span(text, form):
    i = text.index(form)
    return [i, i + len(form)]


def error_rows():
    return [
        {"id": 101, "sentence_index": 0, "span_reproduction": _span(REPRO, "sick"),
         "span_reference": _span(GOLD, "great"), "subtype": "register", "severity": "major",
         "confidence": 0.9, "confidence_label": "high", "span_source": "exact",
         "correction_source": "model_quote", "learner_form": "sick", "corrected_form": "great",
         "explanation": "Register: “sick” → “great”.", "model_note": NOTE, "explanation_source": "model"},
        {"id": 102, "sentence_index": 2, "span_reproduction": _span(REPRO, "without it"),
         "span_reference": _span(GOLD, "with it"), "subtype": "meaning_inversion", "severity": "critical",
         "confidence": 0.9, "confidence_label": "high", "span_source": "exact",
         "correction_source": "model_quote", "learner_form": "without it", "corrected_form": "with it",
         "explanation": EXPLANATION_2, "model_note": None, "explanation_source": "template"},
    ]


def contract_for(rows):
    return {
        "scores": {"accuracy": 3, "fidelity": 2, "understandability": 3}, "overall_band": 3,
        "diff": [{"op": "replace", "a": "great", "b": "sick"}],
        "errors": [{k: v for k, v in r.items() if k != "id"} for r in rows],
        "highlights": [], "provisional": False,
        "grader_trace": {"tier": "single_call", "tokens": {"in": 2000, "out": 90},
                         "single_call": {"used": True, "prompt_version": "v2"}},
    }


# Strings that must never be in a response before the reveal of that sentence.
SECRETS = ["It's a great way to learn by doing.", "You can make many things with it.",
           "great", "with it", NOTE, EXPLANATION_2, "Register: “sick”"]


class FakeStore:
    def __init__(self):
        self.submissions = {9001: {"id": 9001, "user_id": USER, "passage_id": 9, "l1_language_id": 1,
                                   "reproduction": REPRO, "created_at": "2026-11-10T09:00:00+00:00"}}
        self.passages = {9: {"id": 9, "l2_text": GOLD, "l2_language_id": 2, "age_tier": 4,
                             "status": "active", "source_ref_id": None, "sentence_start": None,
                             "sentence_end": None}}
        self.errors = {9001: error_rows()}
        self.l1 = {(9, 1): L1_TEXT}
        self.sessions, self.items, self.events = {}, {}, []
        self.ids = itertools.count(1)
        self.lock_held = set()
        self.fail_insert_session = False

    def install(self, mp):
        for name in ("get_submission", "get_passage", "get_error_rows", "get_l1_passage_text",
                     "insert_session", "get_session", "get_session_by_submission", "update_session",
                     "open_sessions", "insert_items", "get_item", "get_items", "update_item",
                     "due_candidates", "expire_items", "acquire_check_lock", "release_check_lock",
                     "insert_event", "get_check_event", "last_episode_event"):
            mp.setattr(store, name, getattr(self, name))

    # existing tables
    def get_submission(self, db, sid):
        return copy.deepcopy(self.submissions.get(sid))

    def get_passage(self, db, pid):
        return copy.deepcopy(self.passages.get(pid))

    def get_error_rows(self, db, sid):
        return copy.deepcopy(self.errors.get(sid, []))

    def get_l1_passage_text(self, db, pid, l1):
        return self.l1.get((pid, l1))

    # sessions
    def insert_session(self, db, row):
        if self.fail_insert_session:
            raise RuntimeError('relation "public.dt_repair_session" does not exist')
        for s in self.sessions.values():
            if s["submission_id"] == row["submission_id"]:
                return copy.deepcopy(s)
        sid = 500 + next(self.ids)
        self.sessions[sid] = {"id": sid, "created_at": NOW.isoformat(), "closed_early": None,
                              "finished_at": None, "total_ms": None, **copy.deepcopy(row)}
        return copy.deepcopy(self.sessions[sid])

    def get_session(self, db, sid):
        return copy.deepcopy(self.sessions.get(sid))

    def get_session_by_submission(self, db, sub):
        return next((copy.deepcopy(s) for s in self.sessions.values() if s["submission_id"] == sub), None)

    def update_session(self, db, sid, fields):
        self.sessions[sid].update(copy.deepcopy(fields))

    def open_sessions(self, db, user_id, limit=20):
        return [copy.deepcopy(s) for s in self.sessions.values()
                if s["user_id"] == user_id and s["status"] == "open"]

    # items
    def insert_items(self, db, rows):
        out = []
        for row in rows:
            iid = 7000 + next(self.ids)
            item = {"id": iid, "sitting": 0, "sitting_open": False, "hint_level": 0, "checks_used": 0,
                    "calls_used": 0, "last_text": None, "opened_at": None, "check_lock_until": None,
                    "outcome": None, "answer_reason": None, "max_hint_level": None, "n_checks": 0,
                    "time_ms": None, "first_edit_ms": None, "closed_at": None, "queue_status": "none",
                    "queued_at": None, "due_on": None, "not_before": None, "expires_at": None,
                    "failed_sittings": 0, "hinted_sittings": 0, "last_practiced_at": None}
            item.update(copy.deepcopy(row))
            self.items[iid] = item
            out.append(copy.deepcopy(item))
        return out

    def get_item(self, db, iid):
        return copy.deepcopy(self.items.get(iid))

    def get_items(self, db, sid):
        return [copy.deepcopy(i) for i in sorted(self.items.values(), key=lambda i: i["id"])
                if i["session_id"] == sid]

    def update_item(self, db, iid, fields):
        json.dumps(fields)  # what goes to PostgREST must serialise
        self.items[iid].update(copy.deepcopy(fields))

    def due_candidates(self, db, user_id, l2):
        return [copy.deepcopy(i) for i in self.items.values()
                if i["user_id"] == user_id and i["l2_language_id"] == l2 and i["queue_status"] == "due"]

    def expire_items(self, db, user_id, l2, now_iso):
        for i in self.items.values():
            if i["queue_status"] == "due" and i["expires_at"] and i["expires_at"] <= now_iso:
                i["queue_status"] = "expired"

    def acquire_check_lock(self, db, iid, now_iso, until_iso):
        if iid in self.lock_held:
            return False
        self.lock_held.add(iid)
        return True

    def release_check_lock(self, db, iid):
        self.lock_held.discard(iid)

    # events
    def insert_event(self, db, row):
        json.dumps(row)
        if row.get("client_check_id") and any(
                e["item_id"] == row["item_id"] and e.get("client_check_id") == row["client_check_id"]
                for e in self.events):
            raise store.DuplicateCheck("23505")
        ev = {"id": len(self.events) + 1, **copy.deepcopy(row)}
        self.events.append(ev)
        return ev

    def get_check_event(self, db, iid, ccid):
        return next((copy.deepcopy(e) for e in self.events
                     if e["item_id"] == iid and e.get("client_check_id") == ccid), None)

    def last_episode_event(self, db, iid):
        evs = [e for e in self.events if e["item_id"] == iid and e["kind"] == "episode_closed"]
        return copy.deepcopy(evs[-1]) if evs else None

    def kinds(self, iid):
        return [e["kind"] for e in self.events if e["item_id"] == iid]


NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self):
        self.now = NOW

    def __call__(self):
        return self.now


class FakeRecheck:
    """Replaces recheck.recheck_sentence; ``script`` is a list of results."""

    def __init__(self):
        self.script, self.calls = [], []

    def ok(self, *errors):
        self.script.append({"status": "ok", "errors": list(errors), "model": "m", "prompt_version": "v2",
                            "prompt_variant": "v2", "tokens": {"in": 2000, "out": 70, "cached": 1800},
                            "cost_usd": 0.00008, "latency_ms": 1300})

    def fail(self, status="timeout"):
        self.script.append({"status": status, "errors": [], "model": "m", "prompt_version": "v2",
                            "prompt_variant": "v2", "tokens": {"in": 0, "out": 0, "cached": None},
                            "cost_usd": None, "latency_ms": 5000})

    def __call__(self, db, **kw):
        self.calls.append(kw)
        return self.script.pop(0)


def rc_err(subtype, severity, span, form, corrected="", conf="high"):
    return {"subtype": subtype, "severity": severity, "confidence": 0.9, "confidence_label": conf,
            "span": span, "learner_form": form, "corrected_form": corrected,
            "correction_source": "model_quote", "span_source": "exact", "model_note": None}


@pytest.fixture
def scenario(monkeypatch):
    fs = FakeStore()
    fs.install(monkeypatch)
    clock = Clock()
    rc = FakeRecheck()
    credits = []
    monkeypatch.setattr(service, "_now", clock)
    monkeypatch.setattr(service, "_local_today", lambda db, u, l2: clock.now.date())
    monkeypatch.setattr(service, "_local_date_of", lambda db, u, l2, inst: str(inst)[:10])
    monkeypatch.setattr(service, "_lang_code", lambda lid: LANG_CODE.get(lid))
    monkeypatch.setattr(service, "_taxonomy", lambda db: None)
    monkeypatch.setattr(service, "_credit", lambda db, *a: credits.append(a))
    monkeypatch.setattr(budget, "recheck_allowed", lambda db, u: True)
    monkeypatch.setattr(recheck, "recheck_sentence", rc)
    monkeypatch.setattr(settings, "DT_GUIDED_REPAIR", True)

    class S:
        pass
    s = S()
    s.store, s.clock, s.rc, s.credits = fs, clock, rc, credits
    return s


def submit(scenario, rows=None):
    rows = error_rows() if rows is None else rows
    scenario.store.errors[9001] = rows
    sub = {k: scenario.store.submissions[9001][k] for k in ("id", "user_id", "passage_id", "l1_language_id")}
    return hooks.after_grade(None, user_id=USER, submission_row=sub,
                             passage=scenario.store.passages[9], contract=contract_for(rows),
                             reproduction=REPRO)


def assert_no_secrets(obj, secrets=SECRETS):
    blob = json.dumps(obj, ensure_ascii=False)
    for s in secrets:
        assert s not in blob, s


def body(**kw):
    return {"surface": "repair_pass", **kw}


CID = "1b0c5f3e-0000-4000-8000-00000000000{}"


# ---------------------------------------------------------------------------
# Session creation + redaction
# ---------------------------------------------------------------------------

class TestStart:
    def test_open_session_is_redacted(self, scenario):
        resp = submit(scenario)
        assert resp["redacted"] is True and resp["errors"] == [] and resp["diff"] == []
        assert "grader_trace" not in resp and resp["n_errors"] == 2
        rep = resp["repair"]
        assert rep["status"] == "open" and rep["clean"] is False and rep["n_sentences"] == 4
        assert rep["n_clean"] == 2 and rep["prompt_l1_passage"] == L1_TEXT
        steps = rep["steps"]
        assert [s["sentence_index"] for s in steps] == [0, 2]
        assert steps[0]["ladder"] == "full" and steps[0]["hint_rungs"] == [1, 2, 3]
        assert steps[1]["ladder"] == "short" and steps[1]["hint_rungs"] == [1]
        assert steps[0]["learner_sentence"] == "It's a sick way to learn by doing."
        assert steps[0]["prompt_l1"] == "这是一个在实践中学习的好方法。"
        assert steps[0]["check_cap"] == 4 and steps[0]["where"] is None
        assert_no_secrets(resp)

    def test_clean(self, scenario):
        resp = submit(scenario, rows=[])
        assert resp["repair"]["clean"] is True and resp["repair"]["status"] == "finished"
        assert resp["repair"]["steps"] == [] and "redacted" not in resp

    def test_bypass_band_one(self, scenario, monkeypatch):
        rows = error_rows()
        c = contract_for(rows)
        c["scores"]["accuracy"] = 1
        scenario.store.errors[9001] = rows
        sub = scenario.store.submissions[9001]
        resp = hooks.after_grade(None, user_id=USER, submission_row=sub, passage=scenario.store.passages[9],
                                 contract=c, reproduction=REPRO)
        assert resp["repair"]["status"] == "bypassed" and resp["repair"]["steps"] == []
        assert resp["errors"] == c["errors"]
        items = list(scenario.store.items.values())
        assert all(i["outcome"] == "shown_directly" and i["queue_status"] == "due" for i in items)
        assert all(i["step_order"] is None for i in items)

    def test_not_eligible_returns_the_same_contract(self, scenario):
        c = contract_for(error_rows())
        c["grader_trace"] = {"tier": "tier2"}
        sub = scenario.store.submissions[9001]
        assert hooks.after_grade(None, user_id=USER, submission_row=sub,
                                 passage=scenario.store.passages[9], contract=c) is c

    def test_missing_tables_return_the_full_contract(self, scenario):
        scenario.store.fail_insert_session = True
        c = contract_for(error_rows())
        sub = scenario.store.submissions[9001]
        assert hooks.after_grade(None, user_id=USER, submission_row=sub,
                                 passage=scenario.store.passages[9], contract=c, reproduction=REPRO) is c


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def _items(scenario):
    return sorted(scenario.store.items.values(), key=lambda i: i["sentence_index"])


class TestHintsAndChecks:
    def test_full_flow_still_then_fixed(self, scenario):
        submit(scenario)
        first = _items(scenario)[0]
        iid = first["id"]
        opened = service.open_item(None, USER, iid, body())
        assert opened["step"]["hint_level"] == 0
        h1 = service.next_hint(None, USER, iid, body(expected_level=1))
        assert h1["hint"] == {"type": "where", "text": None, "lang": None}
        assert h1["where"] == {"start": 7, "end": 11, "text": "sick", "point": False}
        assert (h1["hint_number"], h1["hint_total"], h1["next"]) == (1, 3, "hint")
        again = service.next_hint(None, USER, iid, body(expected_level=1))
        assert again["hint_level"] == 1
        h2 = service.next_hint(None, USER, iid, body(expected_level=2))
        assert h2["hint"] == {"type": "kind", "text": "语体不符", "lang": "zh"}
        h3 = service.next_hint(None, USER, iid, body(expected_level=3))
        assert h3["hint"]["type"] == "clue" and "“sick”" in h3["hint"]["text"] and h3["next"] == "answer"
        with pytest.raises(service.RepairError) as e:
            service.next_hint(None, USER, iid, body(expected_level=4))
        assert e.value.code == "NO_MORE_HINTS"

        scenario.rc.ok(rc_err("register", "major", [7, 11], "cool", "great"))
        still = service.check(None, USER, iid, body(text="It's a cool way to learn by doing.",
                                                     client_check_id=CID.format(1), first_edit_ms=900))
        assert still["result"] == "still_flagged" and still["reason"] == "target_present"
        assert still["where"] == {"start": 7, "end": 11, "text": "cool", "point": False}
        assert still["checks_used"] == 1 and still["hints_used"] == 3 and still["closed"] is False

        scenario.rc.ok()
        fixed = service.check(None, USER, iid, body(text="It's a great way to learn by doing!",
                                                    client_check_id=CID.format(2)))
        assert fixed["result"] == "fixed" and fixed["closed"] and fixed["outcome"] == "self_repaired"
        assert fixed["answer"] is None
        item = scenario.store.items[iid]
        assert item["max_hint_level"] == 3 and item["queue_status"] == "due" and item["first_edit_ms"] == 900
        kinds = scenario.store.kinds(iid)
        assert kinds == ["step_opened", "hint_shown", "hint_shown", "hint_shown", "revision_checked",
                         "revision_checked", "episode_closed"]
        hint_events = [e for e in scenario.store.events if e["kind"] == "hint_shown"]
        assert [e["hint_source"] for e in hint_events] == ["grader_span", "template", "template"]
        assert hint_events[1]["hint_template_id"] == "register.zh.kind"
        checks = [e for e in scenario.store.events if e["kind"] == "revision_checked"]
        assert checks[0]["text"] == "It's a cool way to learn by doing." and checks[0]["latency_ms"] == 1300
        assert checks[0]["tokens_in"] == 2000 and checks[0]["cost_usd"] == 0.00008
        assert checks[0]["result_detail"]["r"] == "target_present"
        assert len(scenario.rc.calls) == 2
        assert scenario.rc.calls[0]["reference_sentence"] == "It's a great way to learn by doing."

    def test_no_secrets_before_reveal(self, scenario):
        responses = [submit(scenario)]
        first, second = _items(scenario)
        responses.append(service.get_session(None, USER, 9001))
        for iid in (first["id"], second["id"]):
            responses.append(service.open_item(None, USER, iid, body()))
            responses.append(service.next_hint(None, USER, iid, body(expected_level=1)))
        for lvl in (2, 3):
            responses.append(service.next_hint(None, USER, first["id"], body(expected_level=lvl)))
        scenario.rc.ok(rc_err("register", "major", [7, 11], "cool", "great"))
        responses.append(service.check(None, USER, first["id"], body(
            text="It's a cool way to learn by doing.", client_check_id=CID.format(1))))
        responses.append(service.check(None, USER, first["id"], body(
            text="It's a cool way to learn by doing.", client_check_id=CID.format(2))))  # unchanged
        for r in responses:
            assert_no_secrets(r)
        # After the reveal of sentence 0 its answer is there, sentence 2's is not.
        rev = service.reveal(None, USER, first["id"], body(reason="asked"))
        assert rev["answer"]["answer_sentence"] == "It's a great way to learn by doing."
        assert_no_secrets(service.get_session(None, USER, 9001),
                          ["You can make many things with it.", EXPLANATION_2])

    def test_unchanged_makes_no_call_and_no_event(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        r = service.check(None, USER, iid, body(text="  It's a sick way to\nlearn by doing. ",
                                                client_check_id=CID.format(1)))
        assert r["result"] == "unchanged" and scenario.rc.calls == []
        assert "revision_checked" not in scenario.store.kinds(iid)

    def test_tier0_equal_makes_no_call(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        r = service.check(None, USER, iid, body(text="It's a great way to learn by doing.",
                                                client_check_id=CID.format(1)))
        assert r["result"] == "fixed" and scenario.rc.calls == []
        assert scenario.store.items[iid]["queue_status"] == "none"  # fixed with no hint: not queued

    def test_replay_returns_stored_result_without_a_call(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        scenario.rc.ok(rc_err("register", "major", [7, 11], "cool", "great"))
        b = body(text="It's a cool way to learn by doing.", client_check_id=CID.format(1))
        first = service.check(None, USER, iid, b)
        again = service.check(None, USER, iid, b)
        assert again == first and len(scenario.rc.calls) == 1

    def test_check_in_progress(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        scenario.store.lock_held.add(iid)
        with pytest.raises(service.RepairError) as e:
            service.check(None, USER, iid, body(text="It's a cool way.", client_check_id=CID.format(1)))
        assert e.value.code == "CHECK_IN_PROGRESS"

    def test_alternative_is_no_issue_found_with_answer(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        scenario.rc.ok()
        r = service.check(None, USER, iid, body(text="It's a fine way to learn by doing.",
                                                client_check_id=CID.format(1)))
        assert r["result"] == "no_issue_found" and r["outcome"] == "repaired_alternative"
        assert r["answer"]["heading"] == "no_issue"

    def test_auto_reveal_at_cap(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        for n in range(4):
            scenario.rc.ok(rc_err("register", "major", [7, 11], f"c{n}l", "great"))
            r = service.check(None, USER, iid, body(text=f"It's a c{n}l way to learn by doing.",
                                                    client_check_id=CID.format(n)))
        assert r["closed"] and r["auto_reveal"] and r["outcome"] == "answer_shown"
        assert r["checks_used"] == 4 and r["answer"]["heading"] == "compare"
        item = scenario.store.items[iid]
        assert item["answer_reason"] == "auto_cap" and item["hint_level"] == 4
        assert item["queue_status"] == "due"

    def test_error_keeps_item_open(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        scenario.rc.fail("timeout")
        r = service.check(None, USER, iid, body(text="It's a cool way to learn by doing.",
                                                client_check_id=CID.format(1)))
        assert r["result"] == "error" and r["reason"] == "timeout" and not r["closed"]
        assert r["checks_used"] == 0
        ev = [e for e in scenario.store.events if e["kind"] == "revision_checked"][0]
        assert ev["result"] == "error" and ev["text"] == "It's a cool way to learn by doing."
        scenario.rc.fail("malformed")
        r = service.check(None, USER, iid, body(text="It's a cool way to learn by doing.",
                                                client_check_id=CID.format(2)))
        assert r["result"] == "error" and r["reason"] == "call_failed"

    def test_budget_exhausted(self, scenario, monkeypatch):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        monkeypatch.setattr(budget, "recheck_allowed", lambda db, u: False)
        r = service.check(None, USER, iid, body(text="It's a cool way.", client_check_id=CID.format(1)))
        assert r["result"] == "budget_exhausted" and r["closed"] and r["answer"]
        assert scenario.store.items[iid]["answer_reason"] == "budget" and scenario.rc.calls == []

    def test_calls_per_sitting_cap(self, scenario, monkeypatch):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        scenario.store.items[iid]["calls_used"] = settings.DT_REPAIR_MAX_CALLS_PER_SITTING
        r = service.check(None, USER, iid, body(text="It's a cool way.", client_check_id=CID.format(1)))
        assert r["result"] == "budget_exhausted"

    def test_new_error_switches_active_for_hints(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        service.next_hint(None, USER, iid, body(expected_level=1))
        scenario.rc.ok(rc_err("preposition", "major", [17, 20], "for", "to"))
        r = service.check(None, USER, iid, body(text="It's a great way for learn by doing.",
                                                client_check_id=CID.format(1)))
        assert r["reason"] == "new_error" and r["where"]["text"] == "for"
        h2 = service.next_hint(None, USER, iid, body(expected_level=2))
        assert h2["hint"]["text"] == "介词"

    @pytest.mark.parametrize("text,code", [("", "BAD_REQUEST"), ("x" * 401, "TEXT_TOO_LONG"),
                                           ("y" * 120, "TEXT_TOO_LONG"), (5, "BAD_REQUEST")])
    def test_text_validation(self, scenario, text, code):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        with pytest.raises(service.RepairError) as e:
            service.check(None, USER, iid, body(text=text, client_check_id=CID.format(1)))
        assert e.value.code == code and e.value.status == 400

    def test_missing_client_check_id(self, scenario):
        submit(scenario)
        with pytest.raises(service.RepairError) as e:
            service.check(None, USER, _items(scenario)[0]["id"], body(text="x"))
        assert e.value.code == "BAD_REQUEST"


class TestRevealDisputeFinish:
    def test_reveal_answer_object(self, scenario):
        submit(scenario)
        second = _items(scenario)[1]
        r = service.reveal(None, USER, second["id"], body(reason="asked"))
        a = r["answer"]
        assert r["outcome"] == "answer_shown" and a["heading"] == "compare"
        assert a["learner_sentence"] == "You can make many things without it."
        assert a["answer_sentence"] == "You can make many things with it."
        ls = a["learner_marks"][0]
        assert a["learner_sentence"][ls[0]:ls[1]] == "without it"
        am = a["answer_marks"][0]
        assert a["answer_sentence"][am[0]:am[1]] == "with it"
        assert a["explanation"] == EXPLANATION_2 and a["explanation_lang"] == "zh" and a["l2"] == "en"
        again = service.reveal(None, USER, second["id"], body(reason="asked"))
        assert again["answer"] == a
        assert scenario.store.kinds(second["id"]).count("answer_shown") == 1

    def test_model_note_explanation(self, scenario):
        submit(scenario)
        r = service.reveal(None, USER, _items(scenario)[0]["id"], body(reason="asked"))
        assert r["answer"]["explanation"] == NOTE

    def test_reference_sentence_correction_is_unmarked(self, scenario):
        rows = error_rows()
        rows[1]["correction_source"] = "reference_sentence"
        submit(scenario, rows)
        a = service.reveal(None, USER, _items(scenario)[1]["id"], body(reason="asked"))["answer"]
        assert a["learner_marks"] == [] and a["answer_marks"] == []

    def test_dispute(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        r = service.dispute(None, USER, iid, body())
        assert r["outcome"] == "disputed" and r["answer"]["heading"] == "disputed"
        assert scenario.store.items[iid]["queue_status"] == "none"
        assert service.dispute(None, USER, iid, body())["outcome"] == "disputed"

    def test_unsure_dispute_is_kept(self, scenario):
        rows = error_rows()
        rows[0]["confidence"] = 0.3
        submit(scenario, rows)
        iid = _items(scenario)[0]["id"]
        assert scenario.store.items[iid]["step_kind"] == "unsure"
        r = service.dispute(None, USER, iid, body())
        assert r == {"item_id": iid, "closed": True, "outcome": "unsure_dismissed", "answer": None}
        assert "kept" in scenario.store.kinds(iid)

    def test_finish_and_summary_and_result(self, scenario, monkeypatch):
        submit(scenario)
        first, second = _items(scenario)
        service.check(None, USER, first["id"], body(text="It's a great way to learn by doing.",
                                                    client_check_id=CID.format(1)))
        with pytest.raises(service.RepairError) as e:
            service.full_result(None, USER, 9001)
        assert e.value.code == "REPAIR_IN_PROGRESS"
        r = service.finish(None, USER, 501, {"closed_early": True, "active_ms": 400000})
        assert r["session_status"] == "finished" and r["result_available"]
        assert r["summary"] == {"fixed_yourself": 1, "needed_help": 0, "saved_to_practice": 1}
        assert scenario.store.items[second["id"]]["outcome"] == "skipped"
        assert scenario.credits == [(USER, 2, 300, "dt_repair_session", 501)]
        assert service.finish(None, USER, 501, {"closed_early": False}) == r
        import routes.dual_translation as dt_routes
        monkeypatch.setattr(dt_routes, "_cached_grade", lambda db, sid: {"errors": ["full"]})
        assert service.full_result(None, USER, 9001) == {"errors": ["full"]}
        with pytest.raises(service.RepairError) as e:
            service.check(None, USER, second["id"], body(text="x y", client_check_id=CID.format(9)))
        assert e.value.code == "ITEM_CLOSED"

    def test_stale_session_is_abandoned_on_read(self, scenario):
        submit(scenario)
        scenario.clock.now = NOW + timedelta(hours=25)
        s = service.get_session(None, USER, 9001)
        assert s["status"] == "abandoned" and all(st["state"] == "closed" for st in s["steps"])

    def test_session_closed_409(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        scenario.store.sessions[501]["status"] = "finished"
        with pytest.raises(service.RepairError) as e:
            service.open_item(None, USER, iid, body())
        assert e.value.code == "SESSION_CLOSED"


class TestOwnership:
    def test_not_owner(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        for fn, args in ((service.open_item, (iid, body())), (service.check, (iid, body())),
                         (service.next_hint, (iid, body(expected_level=1))),
                         (service.reveal, (iid, body(reason="asked"))), (service.dispute, (iid, body())),
                         (service.finish, (501, {"closed_early": False})),
                         (service.get_session, (9001,)), (service.full_result, (9001,))):
            with pytest.raises(service.RepairError) as e:
                fn(None, OTHER, *args)
            assert e.value.status == 403

    def test_not_found(self, scenario):
        with pytest.raises(service.RepairError) as e:
            service.open_item(None, USER, 1, body())
        assert e.value.status == 404
        with pytest.raises(service.RepairError) as e:
            service.get_session(None, USER, 9001)
        assert e.value.code == "NO_SESSION"


class TestDailyPractice:
    def _queue_one(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        service.reveal(None, USER, iid, body(reason="asked"))
        service.finish(None, USER, 501, {"closed_early": False})
        return iid

    def test_due_selection_and_sitting(self, scenario):
        iid = self._queue_one(scenario)
        assert service.practice_due(None, USER, 2)["items"] == []  # not before tomorrow + 20 h
        scenario.clock.now = NOW + timedelta(days=1, hours=1)
        due = service.practice_due(None, USER, 2)
        assert due["total_due"] == 2  # sentence 0 (answer shown) and 2 (skipped at finish)
        step = next(s for s in due["items"] if s["item_id"] == iid)
        assert step["hint_level"] == 1 and step["check_cap"] == 3 and step["from_date"] == "2026-11-10"
        assert step["where"]["text"] == "sick" and step["state"] == "open"
        assert_no_secrets(due)
        daily = {"surface": "daily_practice"}
        opened = service.open_item(None, USER, iid, daily)["step"]
        assert opened["hint_level"] == 1 and scenario.store.items[iid]["sitting"] == 1
        scenario.rc.ok()
        r = service.check(None, USER, iid, {**daily, "text": "It's a great way to learn by doing!",
                                            "client_check_id": CID.format(5),
                                            "active_ms": 50000, "client_event_id": CID.format(7)})
        assert r["result"] == "fixed" and r["hints_used"] == 0
        assert scenario.store.items[iid]["queue_status"] == "resolved"
        assert scenario.credits[-1] == (USER, 2, 50, "dt_repair_event", CID.format(7))

    def test_not_due_and_skip(self, scenario):
        iid = self._queue_one(scenario)
        daily = {"surface": "daily_practice"}
        with pytest.raises(service.RepairError) as e:
            service.open_item(None, USER, iid, daily)
        assert e.value.code == "NOT_DUE"
        scenario.clock.now = NOW + timedelta(days=1, hours=1)
        service.open_item(None, USER, iid, daily)
        service.skip(None, USER, iid, daily)
        item = scenario.store.items[iid]
        assert item["queue_status"] == "due" and item["due_on"] == "2026-11-16"
        assert item["failed_sittings"] == 0
        with pytest.raises(service.RepairError) as e:
            service.skip(None, USER, iid, body())
        assert e.value.status == 400

    def test_daily_reveal_counts_failure(self, scenario):
        iid = self._queue_one(scenario)
        scenario.clock.now = NOW + timedelta(days=1, hours=1)
        daily = {"surface": "daily_practice"}
        service.open_item(None, USER, iid, daily)
        r = service.reveal(None, USER, iid, {**daily, "reason": "asked"})
        assert r["answer"]["heading"] == "compare"
        item = scenario.store.items[iid]
        assert item["failed_sittings"] == 1 and item["due_on"] == "2026-11-17"

    def test_expired_items(self, scenario):
        iid = self._queue_one(scenario)
        scenario.clock.now = NOW + timedelta(days=31)
        assert service.practice_due(None, USER, 2)["total_due"] == 0
        assert scenario.store.items[iid]["queue_status"] == "expired"

    def test_not_served_while_its_session_is_open(self, scenario):
        submit(scenario)
        iid = _items(scenario)[0]["id"]
        scenario.store.items[iid].update(queue_status="due", due_on="2026-11-01",
                                         not_before="2026-11-01T00:00:00+00:00",
                                         expires_at="2026-12-30T00:00:00+00:00")
        assert service.count_due(None, USER, 2) == 0
