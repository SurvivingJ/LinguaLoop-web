"""WP-INT: the frontend/backend contract of guided self-repair, captured from the REAL routes.

Every flow the sheet, the two hosts and the daily player drive is run through the Flask
test client: the real submit route (with the repair hook), the real ``dt_repair`` blueprint,
the real ``service`` / ``planner`` / ``hints`` / ``classify`` / ``scheduling`` code. Only the
boundaries are replaced: the DB (``store`` functions -> the in-memory ``FakeStore`` of
``test_dt_repair_service``), the model (``recheck.recheck_sentence`` and, for submit,
``grade_submission``), the clock and the learner day.

Each captured response is written to ``tests/unit/fixtures/dt-repair/real/<name>.json`` as
``{"http": <status>, "body": <json>}``. The JS side reads those files
(``tests/unit/dt-repair-contract.test.js``): it checks that the stand-in API the frontend was
built against (``tests/e2e/dt-repair/mock-api.js``) answers with the same shapes, that every
field the sheet reads is present, and drives the real sheet through the real responses.

Drift guard: this test FAILS when the backend's responses no longer match the committed
files. After an intended contract change, regenerate them with

    DT_REPAIR_WRITE_FIXTURES=1 python -m pytest tests/test_dt_repair_contract.py -q

and re-run ``npx vitest run tests/unit/dt-repair-contract.test.js``.
"""

import copy
import json
import os
from datetime import timedelta
from pathlib import Path

import pytest

import routes.dual_translation as dt_routes
from services.dual_translation.repair import budget, settings, store
from tests.test_dt_repair_service import (  # noqa: F401  (scenario is a fixture)
    CID, GOLD, NOW, REPRO, SECRETS, USER, contract_for, error_rows, rc_err, scenario,
)

BASE = "/api/dual-translation/repair"
OUT = Path(os.environ.get("DT_REPAIR_FIXTURES_DIR") or Path(__file__).parent / "unit" / "fixtures" / "dt-repair" / "real")
WRITE = os.environ.get("DT_REPAIR_WRITE_FIXTURES") == "1"


class Recorder:
    def __init__(self):
        self.captured: dict = {}

    def __call__(self, name: str, resp) -> dict:
        body = json.loads(resp.data)
        assert name not in self.captured, name
        self.captured[name] = {"http": resp.status_code, "body": body}
        return body

    def finish(self):
        """Write (DT_REPAIR_WRITE_FIXTURES=1) or compare with the committed files."""
        mismatched = []
        for name, value in self.captured.items():
            path = OUT / f"{name}.json"
            text = json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
            if WRITE:
                OUT.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            elif not path.exists() or json.loads(path.read_text(encoding="utf-8")) != value:
                mismatched.append(name)
        assert not mismatched, (
            f"real backend responses differ from tests/unit/fixtures/dt-repair/real/ for {mismatched}; "
            "if the change is intended, regenerate with DT_REPAIR_WRITE_FIXTURES=1 and re-run the JS "
            "contract test (tests/unit/dt-repair-contract.test.js)")


@pytest.fixture
def rec():
    r = Recorder()
    yield r
    r.finish()


@pytest.fixture
def wired(scenario, monkeypatch):
    """The real submit route over the scenario: the grade is a single-call contract."""
    state = {"contract": contract_for(error_rows()), "persisted": None}

    def persist(db, sid, reproduction, key, contract):
        state["persisted"] = json.loads(json.dumps(contract))

    monkeypatch.setattr(dt_routes, "_get_submission", lambda db, sid: copy.deepcopy(
        {k: scenario.store.submissions[sid][k] for k in ("id", "user_id", "passage_id", "l1_language_id")})
        if sid in scenario.store.submissions else None)
    monkeypatch.setattr(dt_routes, "_cached_grade", lambda db, sid: copy.deepcopy(state["persisted"]))
    monkeypatch.setattr(dt_routes, "_get_passage", lambda db, pid: copy.deepcopy(scenario.store.passages[pid]))
    monkeypatch.setattr(dt_routes, "_tokens_used_today", lambda db, uid: 0)
    monkeypatch.setattr(dt_routes, "grade_submission",
                        lambda db, **kw: json.loads(json.dumps(state["contract"])))
    monkeypatch.setattr(dt_routes, "_persist_grade", persist)
    monkeypatch.setattr(dt_routes, "_persist_grading_assets", lambda *a: None)
    monkeypatch.setattr(dt_routes, "credit_study_time", lambda *a, **k: None)
    scenario.state = state
    return scenario


def _submit(client, headers, sc, rows=None, contract=None):
    rows = error_rows() if rows is None else rows
    sc.store.errors[9001] = rows
    sc.state["contract"] = contract if contract is not None else contract_for(rows)
    return client.post("/api/dual-translation/9001/submit", headers=headers, json={"reproduction": REPRO})


def _ids(sc):
    return [i["id"] for i in sorted(sc.store.items.values(), key=lambda i: i["sentence_index"])]


def _pass(**kw):
    return {"surface": "repair_pass", **kw}


def _daily(**kw):
    return {"surface": "daily_practice", **kw}


def test_repair_pass_main_flow(client, auth_headers, wired, rec):
    sc = wired
    body = rec("submit_open", _submit(client, auth_headers, sc))
    first, second = _ids(sc)
    assert body["repair"]["status"] == "open"
    rec("session_open", client.get(f"{BASE}/submissions/9001/session", headers=auth_headers))
    rec("open_pass", client.post(f"{BASE}/items/{first}/open", headers=auth_headers, json=_pass()))
    rec("hint_where", client.post(f"{BASE}/items/{first}/hint", headers=auth_headers,
                                  json=_pass(expected_level=1, since_prev_ms=900)))
    rec("hint_where_repeat", client.post(f"{BASE}/items/{first}/hint", headers=auth_headers,
                                         json=_pass(expected_level=1)))
    rec("hint_kind", client.post(f"{BASE}/items/{first}/hint", headers=auth_headers, json=_pass(expected_level=2)))
    rec("hint_clue", client.post(f"{BASE}/items/{first}/hint", headers=auth_headers, json=_pass(expected_level=3)))
    rec("hint_no_more", client.post(f"{BASE}/items/{first}/hint", headers=auth_headers,
                                    json=_pass(expected_level=4)))
    rec("check_unchanged", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a sick way to learn by doing.", client_check_id=CID.format(0))))
    sc.rc.fail("timeout")
    rec("check_error", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a cool way to learn by doing.", client_check_id=CID.format(1))))
    sc.rc.ok(rc_err("register", "major", [7, 11], "cool", "great"))
    rec("check_still", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a cool way to learn by doing.", client_check_id=CID.format(2), first_edit_ms=1200)))
    rec("check_replay", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a cool way to learn by doing.", client_check_id=CID.format(2))))
    sc.rc.ok()
    rec("check_fixed", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a great way to learn by doing!", client_check_id=CID.format(3))))
    rec("check_closed", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a great way to learn!", client_check_id=CID.format(4))))
    rec("open_second", client.post(f"{BASE}/items/{second}/open", headers=auth_headers, json=_pass()))
    rec("hint_where_second", client.post(f"{BASE}/items/{second}/hint", headers=auth_headers,
                                         json=_pass(expected_level=1)))
    rec("reveal", client.post(f"{BASE}/items/{second}/reveal", headers=auth_headers, json=_pass(reason="asked")))
    rec("reveal_repeat", client.post(f"{BASE}/items/{second}/reveal", headers=auth_headers,
                                     json=_pass(reason="asked")))
    rec("result_in_progress", client.get(f"{BASE}/submissions/9001/result", headers=auth_headers))
    rec("finish", client.post(f"{BASE}/sessions/501/finish", headers=auth_headers,
                              json={"closed_early": False, "active_ms": 61000,
                                    "client_event_id": CID.format(9)}))
    rec("finish_repeat", client.post(f"{BASE}/sessions/501/finish", headers=auth_headers,
                                     json={"closed_early": True}))
    rec("session_finished", client.get(f"{BASE}/submissions/9001/session", headers=auth_headers))
    rec("result", client.get(f"{BASE}/submissions/9001/result", headers=auth_headers))
    rec("submit_cached_finished", _submit(client, auth_headers, sc))


def test_alternative_and_dispute(client, auth_headers, wired, rec):
    sc = wired
    _submit(client, auth_headers, sc)
    first, second = _ids(sc)
    sc.rc.ok()
    rec("check_alt", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a fine way to learn by doing.", client_check_id=CID.format(1))))
    rec("dispute", client.post(f"{BASE}/items/{second}/dispute", headers=auth_headers, json=_pass()))
    rec("dispute_repeat", client.post(f"{BASE}/items/{second}/dispute", headers=auth_headers, json=_pass()))
    rec("submit_cached_open", _submit(client, auth_headers, sc))
    rec("finish_closed_early", client.post(f"{BASE}/sessions/501/finish", headers=auth_headers,
                                           json={"closed_early": True}))


def test_auto_reveal_and_budget(client, auth_headers, wired, rec, monkeypatch):
    sc = wired
    _submit(client, auth_headers, sc)
    first, second = _ids(sc)
    for n in range(4):
        sc.rc.ok(rc_err("register", "major", [7, 11], f"c{n}l", "great"))
        r = client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
            text=f"It's a c{n}l way to learn by doing.", client_check_id=CID.format(n)))
    rec("check_auto_reveal", r)
    monkeypatch.setattr(budget, "recheck_allowed", lambda db, u: False)
    rec("check_budget_exhausted", client.post(f"{BASE}/items/{second}/check", headers=auth_headers, json=_pass(
        text="You can make many things using it.", client_check_id=CID.format(8))))


def test_unsure_and_direct_steps(client, auth_headers, wired, rec):
    sc = wired
    rows = error_rows()
    rows[0]["confidence"] = 0.3          # every error of sentence 0 below the unsure threshold
    rows[0]["confidence_label"] = "low"
    rows[1]["subtype"] = "word_choice"   # ladder 'none' -> a direct step
    rows[1]["severity"] = "major"
    rec("submit_open_mixed", _submit(client, auth_headers, sc, rows))
    first, second = _ids(sc)
    rec("open_unsure", client.post(f"{BASE}/items/{first}/open", headers=auth_headers, json=_pass()))
    rec("dispute_unsure", client.post(f"{BASE}/items/{first}/dispute", headers=auth_headers, json=_pass()))
    rec("reveal_direct", client.post(f"{BASE}/items/{second}/reveal", headers=auth_headers,
                                     json=_pass(reason="direct")))


def test_submit_variants(client, auth_headers, wired, rec, monkeypatch):
    sc = wired
    rec("submit_clean", _submit(client, auth_headers, sc, rows=[]))
    sc.store.sessions.clear()
    sc.store.items.clear()
    sc.state["persisted"] = None
    bypass = contract_for(error_rows())
    bypass["scores"]["accuracy"] = 1
    rec("submit_bypassed", _submit(client, auth_headers, sc, contract=bypass))
    sc.store.sessions.clear()
    sc.store.items.clear()
    sc.state["persisted"] = None
    tier2 = contract_for(error_rows())
    tier2["grader_trace"] = {"tier": "tier2", "tokens": {"in": 1500, "out": 300}}
    rec("submit_ineligible", _submit(client, auth_headers, sc, contract=tier2))
    sc.state["persisted"] = None
    sc.store.fail_insert_session = True
    rec("submit_tables_missing", _submit(client, auth_headers, sc))
    sc.store.fail_insert_session = False
    store.reset_availability()
    sc.state["persisted"] = None
    monkeypatch.setattr(settings, "DT_GUIDED_REPAIR", False)
    rec("submit_flag_off", _submit(client, auth_headers, sc))
    rec("flag_off_503", client.get(f"{BASE}/practice/due?language_id=2", headers=auth_headers))


def test_daily_practice(client, auth_headers, wired, rec):
    """Captured in the order the daily sheet makes its calls (the due list puts the
    meaning-changing sentence first)."""
    sc = wired
    _submit(client, auth_headers, sc)
    first, second = _ids(sc)
    client.post(f"{BASE}/items/{first}/reveal", headers=auth_headers, json=_pass(reason="asked"))
    client.post(f"{BASE}/sessions/501/finish", headers=auth_headers, json={"closed_early": False})
    rec("practice_due_none", client.get(f"{BASE}/practice/due?language_id=2", headers=auth_headers))
    sc.clock.now = NOW + timedelta(days=1, hours=1)
    due = rec("practice_due", client.get(f"{BASE}/practice/due?language_id=2", headers=auth_headers))
    assert [s["item_id"] for s in due["items"]] == [second, first]  # meaning type first
    rec("daily_check_not_opened", client.post(f"{BASE}/items/{second}/check", headers=auth_headers, json=_daily(
        text="You can make lots of things without it.", client_check_id=CID.format(1))))
    rec("daily_open", client.post(f"{BASE}/items/{second}/open", headers=auth_headers, json=_daily(since_prev_ms=0)))
    wrong = "You can make lots of things without it."
    start = wrong.index("without it")
    sc.rc.ok(rc_err("meaning_inversion", "critical", [start, start + 10], "without it", "with it"))
    rec("daily_check_still", client.post(f"{BASE}/items/{second}/check", headers=auth_headers, json=_daily(
        text=wrong, client_check_id=CID.format(2))))
    rec("daily_check_fixed", client.post(f"{BASE}/items/{second}/check", headers=auth_headers, json=_daily(
        text="You can make many things with it.", client_check_id=CID.format(3),
        active_ms=42000, client_event_id=CID.format(7))))  # equal to the reference: tier-0, no call
    rec("daily_open_second", client.post(f"{BASE}/items/{first}/open", headers=auth_headers, json=_daily()))
    rec("daily_hint_kind", client.post(f"{BASE}/items/{first}/hint", headers=auth_headers,
                                       json=_daily(expected_level=2)))
    rec("daily_hint_clue", client.post(f"{BASE}/items/{first}/hint", headers=auth_headers,
                                       json=_daily(expected_level=3)))
    rec("daily_reveal", client.post(f"{BASE}/items/{first}/reveal", headers=auth_headers,
                                    json=_daily(reason="asked", active_ms=30000, client_event_id=CID.format(8))))
    rec("daily_dispute_closed", client.post(f"{BASE}/items/{first}/dispute", headers=auth_headers, json=_daily()))
    rec("daily_open_not_due", client.post(f"{BASE}/items/{first}/open", headers=auth_headers, json=_daily()))
    sc.clock.now = NOW + timedelta(days=4, hours=1)
    rec("practice_due_after", client.get(f"{BASE}/practice/due?language_id=2", headers=auth_headers))
    client.post(f"{BASE}/items/{first}/open", headers=auth_headers, json=_daily())
    rec("daily_skip", client.post(f"{BASE}/items/{first}/skip", headers=auth_headers, json=_daily()))
    assert sc.store.items[second]["queue_status"] == "resolved"
    assert sc.store.items[first]["queue_status"] == "due"


def test_errors(client, auth_headers, wired, rec):
    sc = wired
    _submit(client, auth_headers, sc)
    first, _ = _ids(sc)
    rec("error_401", client.get(f"{BASE}/submissions/9001/session"))
    rec("error_404_no_session", client.get(f"{BASE}/submissions/9002/session", headers=auth_headers))
    sc.store.items[first]["user_id"] = "someone-else"
    rec("error_403", client.post(f"{BASE}/items/{first}/open", headers=auth_headers, json=_pass()))
    sc.store.items[first]["user_id"] = USER
    sc.store.lock_held.add(first)
    rec("error_409_check_in_progress", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a cool way to learn by doing.", client_check_id=CID.format(1))))
    sc.store.lock_held.clear()
    rec("error_400_too_long", client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="x" * 401, client_check_id=CID.format(2))))


# ---------------------------------------------------------------------------
# Leak check over everything the browser receives before a sentence's reveal
# ---------------------------------------------------------------------------

def test_nothing_before_reveal_carries_the_answer(client, auth_headers, wired):
    """Every response of a full pass, taken in the order the sheet makes the calls, up to the
    reveal of each sentence: no reference sentence, no corrected form, no explanation."""
    sc = wired
    seen = [_submit(client, auth_headers, sc).data]
    first, second = _ids(sc)
    seen.append(client.get(f"{BASE}/submissions/9001/session", headers=auth_headers).data)
    for iid in (first, second):
        seen.append(client.post(f"{BASE}/items/{iid}/open", headers=auth_headers, json=_pass()).data)
    for lvl in (1, 2, 3):
        seen.append(client.post(f"{BASE}/items/{first}/hint", headers=auth_headers,
                                json=_pass(expected_level=lvl)).data)
    seen.append(client.post(f"{BASE}/items/{second}/hint", headers=auth_headers, json=_pass(expected_level=1)).data)
    sc.rc.ok(rc_err("register", "major", [7, 11], "cool", "great"))
    seen.append(client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a cool way to learn by doing.", client_check_id=CID.format(1))).data)
    sc.rc.fail("timeout")
    seen.append(client.post(f"{BASE}/items/{first}/check", headers=auth_headers, json=_pass(
        text="It's a nice way to learn by doing.", client_check_id=CID.format(2))).data)
    seen.append(client.get(f"{BASE}/submissions/9001/result", headers=auth_headers).data)  # 409
    for raw in seen:
        text = raw.decode("utf-8")
        for secret in SECRETS:
            assert secret not in text, (secret, text[:300])
    # after the reveal of sentence 0 only its own answer arrives
    after = client.post(f"{BASE}/items/{first}/reveal", headers=auth_headers, json=_pass(reason="asked")).data
    assert "It's a great way to learn by doing." in after.decode("utf-8")
    for raw in (after, client.get(f"{BASE}/submissions/9001/session", headers=auth_headers).data):
        assert "You can make many things with it." not in raw.decode("utf-8")
