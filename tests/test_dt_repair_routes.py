"""Blueprint dt_repair (tech 4) through the Flask test client, with the
in-memory store of test_dt_repair_service and the re-check boundary patched."""

import json

import pytest

from services.dual_translation.repair import settings
from tests.test_dt_repair_service import CID, SECRETS, _items, scenario, submit  # noqa: F401
from web import rate_limits

BASE = "/api/dual-translation/repair"


def j(resp):
    return json.loads(resp.data)


@pytest.fixture
def open_session(scenario):
    submit(scenario)
    return scenario


def _first(sc):
    return _items(sc)[0]["id"]


def test_happy_path(client, auth_headers, open_session):
    sc = open_session
    iid = _first(sc)
    r = client.get(f"{BASE}/submissions/9001/session", headers=auth_headers)
    assert r.status_code == 200 and j(r)["status"] == "success" and j(r)["session"]["status"] == "open"
    r = client.post(f"{BASE}/items/{iid}/open", headers=auth_headers, json={"surface": "repair_pass"})
    assert r.status_code == 200 and j(r)["step"]["item_id"] == iid
    r = client.post(f"{BASE}/items/{iid}/hint", headers=auth_headers,
                    json={"surface": "repair_pass", "expected_level": 1})
    assert j(r)["hint"]["type"] == "where" and j(r)["where"]["text"] == "sick"
    sc.rc.ok()
    r = client.post(f"{BASE}/items/{iid}/check", headers=auth_headers, json={
        "surface": "repair_pass", "text": "It's a fine way to learn by doing.", "client_check_id": CID.format(1)})
    body = j(r)
    assert set(body) == {"status", "item_id", "result", "reason", "checks_used", "check_cap", "hints_used",
                         "where", "closed", "outcome", "auto_reveal", "answer", "back_later"}
    assert body["result"] == "no_issue_found" and body["answer"]["heading"] == "no_issue"
    second = _items(sc)[1]["id"]
    r = client.post(f"{BASE}/items/{second}/dispute", headers=auth_headers, json={"surface": "repair_pass"})
    assert j(r)["outcome"] == "disputed"
    r = client.post(f"{BASE}/items/{second}/reveal", headers=auth_headers,
                    json={"surface": "repair_pass", "reason": "asked"})
    assert j(r)["outcome"] == "disputed"  # idempotent on a closed item
    r = client.get(f"{BASE}/submissions/9001/result", headers=auth_headers)
    assert r.status_code == 409 and j(r)["error_code"] == "REPAIR_IN_PROGRESS"
    r = client.post(f"{BASE}/sessions/501/finish", headers=auth_headers, json={"closed_early": False})
    assert j(r)["session_status"] == "finished" and j(r)["status"] == "success"
    r = client.get(f"{BASE}/practice/due?language_id=2", headers=auth_headers)
    assert r.status_code == 200 and "items" in j(r) and "total_due" in j(r)


def test_pre_reveal_bodies_have_no_answer(client, auth_headers, open_session):
    iid = _first(open_session)
    bodies = [client.get(f"{BASE}/submissions/9001/session", headers=auth_headers).data,
              client.post(f"{BASE}/items/{iid}/open", headers=auth_headers, json={"surface": "repair_pass"}).data]
    for lvl in (1, 2, 3):
        bodies.append(client.post(f"{BASE}/items/{iid}/hint", headers=auth_headers,
                                  json={"surface": "repair_pass", "expected_level": lvl}).data)
    for raw in bodies:
        text = raw.decode("utf-8")
        for secret in SECRETS:
            assert secret not in json.loads(text).__repr__() and secret not in text


def test_401(client):
    assert client.get(f"{BASE}/submissions/9001/session").status_code == 401


def test_403(client, auth_headers, open_session):
    open_session.store.items[_first(open_session)]["user_id"] = "someone-else"
    r = client.post(f"{BASE}/items/{_first(open_session)}/open", headers=auth_headers,
                    json={"surface": "repair_pass"})
    assert r.status_code == 403 and j(r)["error_code"] == "NOT_OWNER"


def test_404(client, auth_headers, scenario):
    r = client.post(f"{BASE}/items/1/hint", headers=auth_headers, json={"surface": "repair_pass", "expected_level": 1})
    assert r.status_code == 404 and j(r)["error_code"] == "NOT_FOUND"
    r = client.get(f"{BASE}/submissions/9001/session", headers=auth_headers)
    assert j(r)["error_code"] == "NO_SESSION"


def test_503_when_flag_off(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "DT_GUIDED_REPAIR", False)
    for method, path in (("get", "/submissions/1/session"), ("get", "/submissions/1/result"),
                         ("post", "/items/1/open"), ("post", "/items/1/hint"), ("post", "/items/1/check"),
                         ("post", "/items/1/reveal"), ("post", "/items/1/dispute"), ("post", "/items/1/skip"),
                         ("post", "/sessions/1/finish"), ("get", "/practice/due?language_id=2")):
        r = getattr(client, method)(BASE + path, headers=auth_headers, json={} if method == "post" else None)
        assert r.status_code == 503 and j(r)["error_code"] == "REPAIR_DISABLED", path


def test_409_codes(client, auth_headers, open_session):
    sc = open_session
    iid = _first(sc)
    sc.store.lock_held.add(iid)
    r = client.post(f"{BASE}/items/{iid}/check", headers=auth_headers, json={
        "surface": "repair_pass", "text": "It's a cool way.", "client_check_id": CID.format(1)})
    assert r.status_code == 409 and j(r)["error_code"] == "CHECK_IN_PROGRESS"
    sc.store.lock_held.clear()
    second = _items(sc)[1]["id"]
    client.post(f"{BASE}/items/{second}/hint", headers=auth_headers, json={"surface": "repair_pass", "expected_level": 1})
    r = client.post(f"{BASE}/items/{second}/hint", headers=auth_headers, json={"surface": "repair_pass", "expected_level": 2})
    assert j(r)["error_code"] == "NO_MORE_HINTS"
    client.post(f"{BASE}/items/{second}/reveal", headers=auth_headers, json={"surface": "repair_pass", "reason": "asked"})
    r = client.post(f"{BASE}/items/{second}/check", headers=auth_headers, json={
        "surface": "repair_pass", "text": "abc", "client_check_id": CID.format(2)})
    assert j(r)["error_code"] == "ITEM_CLOSED"
    r = client.post(f"{BASE}/items/{iid}/open", headers=auth_headers, json={"surface": "daily_practice"})
    assert j(r)["error_code"] == "NOT_DUE"
    r = client.post(f"{BASE}/items/{iid}/check", headers=auth_headers, json={
        "surface": "daily_practice", "text": "It's a cool way.", "client_check_id": CID.format(3)})
    assert j(r)["error_code"] == "NOT_OPENED"
    client.post(f"{BASE}/sessions/501/finish", headers=auth_headers, json={"closed_early": True})
    r = client.post(f"{BASE}/items/{iid}/open", headers=auth_headers, json={"surface": "repair_pass"})
    assert r.status_code == 409 and j(r)["error_code"] in ("SESSION_CLOSED", "ITEM_CLOSED")


def test_text_too_long_and_bad_request(client, auth_headers, open_session):
    iid = _first(open_session)
    r = client.post(f"{BASE}/items/{iid}/check", headers=auth_headers, json={
        "surface": "repair_pass", "text": "x" * 500, "client_check_id": CID.format(1)})
    assert r.status_code == 400 and j(r)["error_code"] == "TEXT_TOO_LONG"
    r = client.post(f"{BASE}/items/{iid}/check", headers=auth_headers, json={"surface": "nope"})
    assert r.status_code == 400 and j(r)["error_code"] == "BAD_REQUEST"
    r = client.get(f"{BASE}/practice/due?language_id=x", headers=auth_headers)
    assert r.status_code == 400
    r = client.post(f"{BASE}/sessions/501/finish", headers=auth_headers, json={})
    assert r.status_code == 400


def test_rate_limit_entries():
    limits = rate_limits.ENDPOINT_LIMITS
    assert limits["dt_repair.check"][0][0] == "20 per minute; 300 per hour"
    assert limits["dt_repair.hint"][0][0] == "60 per minute"
    assert limits["dt_repair.practice_due"][0][0] == "30 per minute"


def test_endpoint_names_exist(app):
    for name in ("get_session", "get_result", "open_item", "hint", "check", "reveal", "dispute",
                 "skip", "finish", "practice_due"):
        assert f"dt_repair.{name}" in app.view_functions
