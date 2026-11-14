"""The submit hook in routes/dual_translation.py (tech 3.3, 4.1; TASK-959)."""

import json

import pytest

import routes.dual_translation as dt_routes
from services.dual_translation.repair import hooks, settings
from tests.test_dt_repair_service import (  # noqa: F401
    GOLD, REPRO, SECRETS, USER, contract_for, error_rows, scenario,
)


def j(resp):
    return json.loads(resp.data)


@pytest.fixture
def route(scenario, monkeypatch):
    """Wire the submit route to the scenario: grade = a single-call contract."""
    state = {"contract": contract_for(error_rows()), "cached": None, "persisted": []}
    monkeypatch.setattr(dt_routes, "_get_submission", lambda db, sid: {
        "id": 9001, "user_id": USER, "passage_id": 9, "l1_language_id": 1})
    monkeypatch.setattr(dt_routes, "_cached_grade", lambda db, sid: state["cached"])
    monkeypatch.setattr(dt_routes, "_get_passage", lambda db, pid: scenario.store.passages[9])
    monkeypatch.setattr(dt_routes, "_tokens_used_today", lambda db, uid: 0)
    monkeypatch.setattr(dt_routes, "grade_submission", lambda db, **kw: json.loads(json.dumps(state["contract"])))
    monkeypatch.setattr(dt_routes, "_persist_grade", lambda *a: state["persisted"].append(a[-1]))
    monkeypatch.setattr(dt_routes, "_persist_grading_assets", lambda *a: None)
    monkeypatch.setattr(dt_routes, "credit_study_time", lambda *a, **k: None)
    state["scenario"] = scenario
    return state


def post(client, headers):
    return client.post("/api/dual-translation/9001/submit", headers=headers, json={"reproduction": REPRO})


def test_flag_off_is_byte_identical(client, auth_headers, route, monkeypatch):
    monkeypatch.setattr(settings, "DT_GUIDED_REPAIR", False)
    r = post(client, auth_headers)
    assert r.status_code == 200
    assert j(r) == {"status": "success", **route["contract"]}
    assert route["scenario"].store.sessions == {}


def test_ineligible_grade_is_byte_identical(client, auth_headers, route):
    route["contract"]["grader_trace"] = {"tier": "tier2", "tokens": {"in": 1, "out": 1}}
    r = post(client, auth_headers)
    assert j(r) == {"status": "success", **route["contract"]} and "repair" not in j(r)


def test_open_session_is_redacted(client, auth_headers, route):
    r = post(client, auth_headers)
    body = j(r)
    assert r.status_code == 200 and body["redacted"] is True and body["repair"]["status"] == "open"
    text = r.data.decode("utf-8")
    for secret in SECRETS:
        assert secret not in text
    # side effects still read the unredacted contract
    assert route["persisted"][0]["errors"]


def test_clean_and_bypass(client, auth_headers, route):
    route["contract"] = contract_for([])
    route["scenario"].store.errors[9001] = []
    body = j(post(client, auth_headers))
    assert body["repair"]["clean"] is True and "redacted" not in body


def test_bypass(client, auth_headers, route):
    route["contract"]["scores"]["accuracy"] = 1
    body = j(post(client, auth_headers))
    assert body["repair"]["status"] == "bypassed" and body["errors"] == route["contract"]["errors"]


def test_cached_path_returns_the_existing_session(client, auth_headers, route):
    first = j(post(client, auth_headers))
    route["cached"] = route["contract"]
    again = j(post(client, auth_headers))
    assert again["repair"]["session_id"] == first["repair"]["session_id"] and again["redacted"] is True
    assert len(route["scenario"].store.sessions) == 1


def test_cached_path_creates_a_missing_session(client, auth_headers, route):
    route["cached"] = route["contract"]
    body = j(post(client, auth_headers))
    assert body["repair"]["status"] == "open"


def test_hook_exception_gives_full_contract(client, auth_headers, route, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(hooks.service, "start_session", boom)
    r = post(client, auth_headers)
    assert r.status_code == 200 and j(r) == {"status": "success", **route["contract"]}


def test_missing_tables_give_full_contract(client, auth_headers, route):
    route["scenario"].store.fail_insert_session = True
    r = post(client, auth_headers)
    assert r.status_code == 200 and j(r) == {"status": "success", **route["contract"]}


def test_missing_tables_are_detected_once_and_logged_once(client, auth_headers, route, caplog, monkeypatch):
    """WP-INT: before the migration is applied every submit would fail the session
    insert. The first failure marks the tables unavailable (one warning, no error);
    later submits skip the repair DB work entirely and log nothing."""
    from services.dual_translation.repair import store
    sc = route["scenario"]
    sc.store.fail_insert_session = True
    calls = {"open_sessions": 0}
    real_open = sc.store.open_sessions

    def counting(db, user_id, limit=20):
        calls["open_sessions"] += 1
        return real_open(db, user_id, limit)
    monkeypatch.setattr(store, "open_sessions", counting)
    caplog.set_level("DEBUG", logger="services.dual_translation.repair")
    for _ in range(3):
        r = post(client, auth_headers)
        assert r.status_code == 200 and j(r) == {"status": "success", **route["contract"]}
    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING"]
    errors = [rec for rec in caplog.records if rec.levelname == "ERROR"]
    assert len(warnings) == 1 and "dt_guided_self_repair.sql" in warnings[0].getMessage()
    assert errors == []
    assert calls["open_sessions"] == 1  # only the first submit touched the repair tables
    assert not store.tables_available()
    # the daily-block count and the token add-on skip the DB too
    from services.dual_translation.repair import budget, service
    assert service.count_due(None, "u", 2) == 0
    assert budget.recheck_tokens_today(None, "u") == 0
    # after the retry window the tables are probed again (migration applied -> sessions)
    sc.store.fail_insert_session = False
    store._availability["unavailable_until"] = 0.0
    assert j(post(client, auth_headers))["repair"]["status"] == "open"


def test_missing_table_error_recognition():
    from services.dual_translation.repair import store
    assert store.is_missing_table_error(RuntimeError(
        "{'code': 'PGRST205', 'message': \"Could not find the table 'public.dt_repair_session' in the schema cache\"}"))
    assert store.is_missing_table_error(RuntimeError('relation "public.dt_repair_item" does not exist'))
    assert not store.is_missing_table_error(RuntimeError("connection reset by peer"))


def test_provisional_grade_gets_no_session(client, auth_headers, route):
    route["contract"]["overall_band"] = None
    body = j(post(client, auth_headers))
    assert "repair" not in body and route["scenario"].store.sessions == {}


def test_tokens_used_today_adds_recheck_tokens(monkeypatch):
    class Q:
        def __init__(self, data): self.data = data
        def __getattr__(self, n): return lambda *a, **k: self
        def execute(self): return self
    tables = {"dt_submission": [{"id": 5}], "dt_grade": [{"grader_trace": {"tokens": {"in": 100, "out": 40}}}],
              "dt_repair_event": [{"tokens_in": 2000, "tokens_out": 70, "model_slug": "m"}]}

    class DB:
        def table(self, name): return Q(tables.get(name, []))
    assert dt_routes._tokens_used_today(DB(), "u") == 2210

    class Broken(DB):
        def table(self, name):
            if name == "dt_repair_event":
                raise RuntimeError("relation does not exist")
            return super().table(name)
    assert dt_routes._tokens_used_today(Broken(), "u") == 140
