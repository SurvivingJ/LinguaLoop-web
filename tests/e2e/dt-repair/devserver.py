"""A local test server for DT guided self-repair: the REAL app over in-memory fakes.

What is real: ``create_app`` (every blueprint, the auth middleware, rate limits, security
headers), the page templates (``templates/dual_translation.html`` on ``base.html``), every
static file, the submit route with its repair hook, the whole ``dt_repair`` blueprint and the
``services/dual_translation/repair`` package (planner, hints, classify, scheduling, service).

What is fake (the boundaries, exactly as in the backend tests):
  * the database - the ``store`` functions are the in-memory ``FakeStore`` of
    ``tests/test_dt_repair_service.py``; the Supabase client is the MagicMock of
    ``tests/conftest.py`` (any bearer token authenticates as ``test-user-id-123``);
  * the model - ``grade_submission`` returns a single-call contract for the two planted errors
    of the Arduino passage, and ``recheck.recheck_sentence`` is a rule-based stand-in (~0.6 s);
  * ``GET /api/dual-translation/next`` - serves that passage and creates a submission row in
    the fake store (the real one selects from dt_passage).
  * the clock and the learner day (``POST /__dev/advance?hours=N`` moves time forward).

It can never reach production: every SUPABASE_* / OPENROUTER_* / OPENAI_* / STRIPE_* / R2_*
variable is removed from the environment and SUPABASE_URL points at a closed local port
before anything is imported.

    $V/bin/python tests/e2e/dt-repair/devserver.py --port 5055
    open http://127.0.0.1:5055/__dev/login  (stores a fake token, then goes to /dual-translation)

Extra dev pages: ``/__dev/daily`` mounts the real daily-practice player
(``static/js/session/players/dt_repair.js``) inside ``base.html``; ``/__dev/state`` dumps the
fake store; ``POST /__dev/reset`` empties it.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---- isolation from every real service, before any app module is imported -------------------
for _k in list(os.environ):
    if _k.startswith(("SUPABASE", "OPENROUTER", "OPENAI", "STRIPE", "R2_", "ANTHROPIC", "BATCH_SERVICE",
                      "DATABASE_URL", "TEST_JWT", "TEST_USER")):
        del os.environ[_k]
os.environ["SUPABASE_URL"] = "http://127.0.0.1:9"
os.environ["DT_GUIDED_REPAIR"] = os.environ.get("DT_GUIDED_REPAIR", "true")

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from flask import jsonify, render_template_string, request  # noqa: E402

from tests.conftest import TestConfig, _make_mock_dimension_service, _make_mock_supabase  # noqa: E402
from tests.test_dt_repair_service import (  # noqa: E402
    GOLD, L1_TEXT, REPRO, FakeStore, contract_for, rc_err,
)

USER = "test-user-id-123"
PASSAGE_ID = 9


def _span(text, form):
    i = text.find(form)
    return [i, i + len(form)] if i >= 0 else None


def rows_for(reproduction: str, first_id: int) -> list:
    """The planted errors still present in what the learner submitted."""
    rows = []
    s = _span(reproduction, "sick")
    if s:
        rows.append({"id": first_id, "sentence_index": 0, "span_reproduction": s,
                     "span_reference": _span(GOLD, "great"), "subtype": "register", "severity": "major",
                     "confidence": 0.9, "confidence_label": "high", "span_source": "exact",
                     "correction_source": "model_quote", "learner_form": "sick", "corrected_form": "great",
                     "explanation": "Register: “sick” → “great”.",
                     "model_note": "“sick” 是俚语，这里应该用 “great”。", "explanation_source": "model"})
    s = _span(reproduction, "without it")
    if s:
        rows.append({"id": first_id + 1, "sentence_index": 2, "span_reproduction": s,
                     "span_reference": _span(GOLD, "with it"), "subtype": "meaning_inversion",
                     "severity": "critical", "confidence": 0.9, "confidence_label": "high",
                     "span_source": "exact", "correction_source": "model_quote",
                     "learner_form": "without it", "corrected_form": "with it",
                     "explanation": "意思反了：“without it” 应为 “with it”。", "model_note": None,
                     "explanation_source": "template"})
    return rows


# reference sentence -> (subtype, severity, forms that are still wrong, corrected form)
RECHECK_RULES = {
    "It's a great way to learn by doing.": ("register", "major", ["sick", "cool", "awesome"], "great"),
    "You can make many things with it.": ("meaning_inversion", "critical", ["without"], "with it"),
}


class RuleRecheck:
    """Stands in for one single-call grader call on one sentence. "zzz" in the revision
    simulates a timeout."""

    def __init__(self, delay_s: float):
        self.delay_s = delay_s
        self.calls = 0

    def __call__(self, db, *, reference_sentence, revised_sentence, **kw):
        self.calls += 1
        time.sleep(self.delay_s)
        base = {"model": "dev/rule-recheck", "prompt_version": "dev", "prompt_variant": "dev",
                "tokens": {"in": 2000, "out": 70, "cached": 1800}, "cost_usd": 0.00008,
                "latency_ms": int(self.delay_s * 1000)}
        if "zzz" in revised_sentence:
            return {**base, "status": "timeout", "errors": []}
        errors = []
        rule = RECHECK_RULES.get(reference_sentence.strip())
        if rule:
            subtype, severity, forms, corrected = rule
            for form in forms:
                span = _span(revised_sentence, form)
                if span:
                    errors.append(rc_err(subtype, severity, span, form, corrected))
                    break
        return {**base, "status": "ok", "errors": errors}


class DevClock:
    def __init__(self):
        self.offset = timedelta(0)

    def __call__(self):
        return datetime.now(timezone.utc) + self.offset


def fake_token() -> str:
    """A JWT-shaped token the page's head script accepts (exp far ahead); alg "none" so the
    server never verifies it locally - the mocked Supabase auth accepts any token."""
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")  # noqa: E731
    return enc({"alg": "none", "typ": "JWT"}) + "." + enc(
        {"sub": USER, "exp": int(time.time()) + 30 * 86400, "email": "test@example.com"}) + ".dev"


LOGIN_PAGE = """<!doctype html><meta charset="utf-8"><title>dev login</title>
<script>
localStorage.setItem('jwt_token', {{ token|tojson }});
localStorage.setItem('user_data', JSON.stringify({id: 'test-user-id-123', email: 'test@example.com'}));
location.replace({{ next|tojson }});
</script>"""

DAILY_PAGE = """{% extends "base.html" %}
{% block title %}Daily repair (dev) | LinguaDojo{% endblock %}
{% block extra_css %}<link rel="stylesheet" href="{{ url_for('static', filename='css/dt-repair.css') }}">{% endblock %}
{% block content %}
<div id="dev-daily" style="max-width:520px;margin:0 auto"></div>
<p id="dev-daily-done" data-done=""></p>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/active-timer.js') }}"></script>
<script src="{{ url_for('static', filename='js/dt-repair-sheet.js') }}"></script>
<script type="module">
  import { mount } from "{{ url_for('static', filename='js/session/players/dt_repair.js') }}";
  const out = document.getElementById('dev-daily-done');
  mount(document.getElementById('dev-daily'), {
    languageId: 2,
    onComplete: (r) => { out.dataset.done = JSON.stringify({ complete: r }); },
    onSkip: () => { out.dataset.done = JSON.stringify({ skip: true }); },
  });
</script>
{% endblock %}"""


def build(delay_s: float):
    stack = ExitStack()
    mock_supabase = _make_mock_supabase()
    mock_factory = stack.enter_context(patch("services.supabase_factory.SupabaseFactory"))
    stack.enter_context(patch("services.supabase_factory.get_supabase", return_value=mock_supabase))
    stack.enter_context(patch("services.supabase_factory.get_supabase_admin", return_value=mock_supabase))
    dim1 = stack.enter_context(patch("services.dimension_service.DimensionService"))
    dim2 = stack.enter_context(patch("app.DimensionService"))
    stack.enter_context(patch("app.ServiceFactory"))
    stack.enter_context(patch("app.R2Service"))
    stack.enter_context(patch("app.AuthService"))
    mock_factory.initialize = MagicMock()
    mock_factory.get_anon_client.return_value = mock_supabase
    mock_factory.get_service_client.return_value = mock_supabase
    dim_data = _make_mock_dimension_service()
    for target in (dim1, dim2):
        target.initialize = MagicMock()
        target.get_all_languages = MagicMock(side_effect=dim_data["get_all_languages"])
        target.get_all_test_types = MagicMock(side_effect=dim_data["get_all_test_types"])
        target.get_language_code = MagicMock(side_effect=lambda lid: {1: "zh", 2: "en", 3: "ja"}.get(lid))

    from app import create_app
    import routes.dual_translation as dt_routes
    from services.dual_translation.repair import budget, recheck, service, settings, store
    from services.dual_translation.sentence_refs import LANG_CODE
    from utils.responses import api_success

    app = create_app(TestConfig)
    app.config["TESTING"] = False
    app.supabase = app.supabase_service = mock_supabase

    mp = pytest.MonkeyPatch()
    fs = FakeStore()
    fs.submissions.clear()
    fs.errors.clear()
    fs.install(mp)
    clock = DevClock()
    rc = RuleRecheck(delay_s)
    credits: list = []
    grades: dict = {}
    mp.setattr(service, "_now", clock)
    mp.setattr(service, "_local_today", lambda db, u, l2: clock().date())
    mp.setattr(service, "_local_date_of", lambda db, u, l2, inst: str(inst)[:10] if inst else None)
    mp.setattr(service, "_lang_code", lambda lid: LANG_CODE.get(lid))
    mp.setattr(service, "_taxonomy", lambda db: None)
    mp.setattr(service, "_credit", lambda db, *a: credits.append(a))
    mp.setattr(budget, "recheck_allowed", lambda db, u: True)
    mp.setattr(recheck, "recheck_sentence", rc)
    mp.setattr(settings, "DT_GUIDED_REPAIR", os.environ.get("DT_GUIDED_REPAIR", "true") == "true")

    # the submit route's DB reads/writes and the grader
    mp.setattr(dt_routes, "_get_submission", lambda db, sid: copy.deepcopy(
        {k: fs.submissions[sid][k] for k in ("id", "user_id", "passage_id", "l1_language_id")})
        if sid in fs.submissions else None)
    mp.setattr(dt_routes, "_cached_grade", lambda db, sid: copy.deepcopy(grades.get(sid)))
    mp.setattr(dt_routes, "_get_passage", lambda db, pid: copy.deepcopy(fs.passages.get(pid)))
    mp.setattr(dt_routes, "_tokens_used_today", lambda db, uid: 0)
    mp.setattr(dt_routes, "_persist_grading_assets", lambda *a: None)
    mp.setattr(dt_routes, "credit_study_time", lambda *a, **k: None)

    mode = {"tier": "single_call", "band1": False}

    def grade_submission(db, *, reproduction, **kw):
        sid = grade_submission.current
        rows = rows_for(reproduction, first_id=sid * 10)
        fs.errors[sid] = rows
        contract = contract_for(rows)
        if mode["tier"] != "single_call":   # e.g. a v2-cascade grade: not eligible
            contract["grader_trace"] = {"tier": mode["tier"], "tokens": {"in": 1500, "out": 300}}
        if mode["band1"]:                   # a score of 1: the pass is bypassed
            contract["scores"]["accuracy"] = 1
        return json.loads(json.dumps(contract))

    def persist_grade(db, sid, reproduction, key, contract):
        fs.submissions[sid]["reproduction"] = reproduction
        grades[sid] = json.loads(json.dumps(contract))

    mp.setattr(dt_routes, "grade_submission", grade_submission)
    mp.setattr(dt_routes, "_persist_grade", persist_grade)

    @app.before_request
    def _which_submission():
        # grade_submission does not get the submission id; the URL has it
        parts = request.path.split("/")
        if request.path.startswith("/api/dual-translation/") and request.path.endswith("/submit"):
            grade_submission.current = int(parts[3])

    def get_next():
        sid = 9001 + len(fs.submissions)
        fs.submissions[sid] = {"id": sid, "user_id": USER, "passage_id": PASSAGE_ID, "l1_language_id": 1,
                               "reproduction": "", "created_at": clock().isoformat()}
        return api_success({"type": "passage", "submission_id": sid, "l1_text": L1_TEXT, "age_tier": 4,
                            "rubric_descriptors": {}, "correction_style": "full_explanation"})
    app.view_functions["dual_translation.get_next"] = get_next
    # the page chrome asks for the learner's L1 (the MagicMock DB cannot answer): zh
    app.view_functions["users.get_native_language"] = lambda: api_success({"native_language_id": 1})

    @app.route("/__dev/login")
    def dev_login():
        return render_template_string(LOGIN_PAGE, token=fake_token(),
                                      next=request.args.get("next", "/dual-translation"))

    @app.route("/__dev/daily")
    def dev_daily():
        return render_template_string(DAILY_PAGE)

    @app.route("/__dev/advance", methods=["POST"])
    def dev_advance():
        clock.offset += timedelta(hours=float(request.args.get("hours", "25")))
        return jsonify({"now": clock().isoformat()})

    @app.route("/__dev/state")
    def dev_state():
        return jsonify({"sessions": fs.sessions, "items": fs.items, "events": fs.events,
                        "submissions": fs.submissions, "recheck_calls": rc.calls, "credits": credits,
                        "now": clock().isoformat()})

    @app.route("/__dev/reset", methods=["POST"])
    def dev_reset():
        fs.sessions.clear(); fs.items.clear(); fs.events.clear()  # noqa: E702
        fs.submissions.clear(); fs.errors.clear(); grades.clear()  # noqa: E702
        clock.offset = timedelta(0)
        rc.calls = 0
        mode.update(tier="single_call", band1=False)
        settings.DT_GUIDED_REPAIR = True
        fs.fail_insert_session = False
        store.reset_availability()
        return jsonify({"ok": True})

    @app.route("/__dev/mode", methods=["POST"])
    def dev_mode():
        """?tier=single_call|tier2  ?band1=0|1  ?flag=0|1"""
        if "tier" in request.args:
            mode["tier"] = request.args["tier"]
        if "band1" in request.args:
            mode["band1"] = request.args["band1"] == "1"
        if "flag" in request.args:
            settings.DT_GUIDED_REPAIR = request.args["flag"] == "1"
        return jsonify({**mode, "flag": settings.DT_GUIDED_REPAIR})

    @app.route("/__dev/fail-tables", methods=["POST"])
    def dev_fail_tables():
        fs.fail_insert_session = request.args.get("on", "1") == "1"
        store.reset_availability()
        return jsonify({"fail_insert_session": fs.fail_insert_session})

    return app, stack, mp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5055)
    ap.add_argument("--recheck-delay", type=float, default=0.6)
    args = ap.parse_args()
    app, stack, mp = build(args.recheck_delay)
    try:
        # one thread: the fakes are plain dicts
        app.run(host="127.0.0.1", port=args.port, threaded=False, use_reloader=False)
    finally:
        mp.undo()
        stack.close()


if __name__ == "__main__":
    main()
