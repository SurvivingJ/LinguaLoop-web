"""Local preview server for the 2026-11 mobile redesign: the REAL app over in-memory fakes.

Real: ``create_app`` (blueprints, auth middleware, security headers, static-asset
versioning), every page template on ``templates/base.html``, every static file.
Fake: the database (the MagicMock Supabase client of ``tests/conftest.py``; any bearer
token authenticates as ``test-user-id-123``) and the language metadata (zh=1, en=2,
ja=3). API responses are NOT meaningful here: drive pages with ``preview.cjs``, which
answers ``/api/*`` from fixture JSON in the browser (Playwright route interception)
before a request ever reaches this server.

It can never reach production: every SUPABASE_* / OPENROUTER_* / OPENAI_* / STRIPE_* /
R2_* variable is removed from the environment and SUPABASE_URL points at a closed local
port before anything is imported.

    python tests/e2e/redesign/serve.py --port 5099

Needs the app's Python deps plus pytest (requirements.txt + requirements-dev.txt).

Component gallery (every shared .ld-* class, real base.html):
    /__preview/components      normal page (app bar + tabs)
    /__preview/task            the same in task mode (Back pill, stage, pinned dock)

For a manual look in a desktop browser, open
    http://127.0.0.1:5099/__preview/login?next=/session&lang=1
which stores a fake token (and the study language) in localStorage and redirects.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---- isolation from every real service, before any app module is imported ----------
for _k in list(os.environ):
    if _k.startswith(("SUPABASE", "OPENROUTER", "OPENAI", "STRIPE", "R2_", "ANTHROPIC",
                      "BATCH_SERVICE", "DATABASE_URL", "TEST_JWT", "TEST_USER", "AZURE")):
        del os.environ[_k]
os.environ["SUPABASE_URL"] = "http://127.0.0.1:9"

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from flask import render_template_string, request  # noqa: E402

from tests.conftest import TestConfig, _make_mock_supabase  # noqa: E402

LANGUAGES = [
    {"id": 1, "language_code": "zh", "language_name": "Chinese", "native_name": "中文"},
    {"id": 2, "language_code": "en", "language_name": "English", "native_name": "English"},
    {"id": 3, "language_code": "ja", "language_name": "Japanese", "native_name": "日本語"},
]
TEST_TYPES = [
    {"id": 1, "type_code": "reading", "type_name": "Reading"},
    {"id": 2, "type_code": "listening", "type_name": "Listening"},
    {"id": 3, "type_code": "dictation", "type_name": "Dictation"},
]


def fake_token(hours: int = 24 * 365) -> str:
    """An unsigned JWT the pages accept (only its exp claim is read client-side)."""
    def b64(obj):
        raw = json.dumps(obj, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    claims = {"sub": "test-user-id-123", "email": "preview@example.com",
              "exp": int(time.time()) + hours * 3600}
    return f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64(claims)}.preview"


LOGIN_PAGE = """<!doctype html><meta charset="utf-8"><title>Preview login</title>
<script>
  localStorage.setItem('jwt_token', {{ token|tojson }});
  localStorage.setItem('user_data', JSON.stringify({id: 'test-user-id-123', email: 'preview@example.com'}));
  localStorage.setItem('nativeLanguagePromptDone', '1');
  {% if lang %}
  localStorage.setItem('selectedLanguageId', {{ lang|tojson }});
  localStorage.setItem('selectedLanguage', JSON.stringify({{ lang_obj|tojson }}));
  {% endif %}
  location.replace({{ next|tojson }});
</script>"""


def build():
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
    for target in (dim1, dim2):
        target.initialize = MagicMock()
        target.get_all_languages = MagicMock(return_value=LANGUAGES)
        target.get_all_test_types = MagicMock(return_value=TEST_TYPES)
        target._test_types_metadata = TEST_TYPES
        target.get_language_code = MagicMock(
            side_effect=lambda lid: {1: "zh", 2: "en", 3: "ja"}.get(lid))

    from app import create_app

    app = create_app(TestConfig)
    app.config["TESTING"] = False
    app.supabase = app.supabase_service = mock_supabase

    @app.route("/__preview/login")
    def preview_login():
        lang = request.args.get("lang")
        lang_obj = None
        if lang:
            row = next((r for r in LANGUAGES if str(r["id"]) == str(lang)), None)
            if row:
                lang_obj = {"id": row["id"], "code": row["language_code"],
                            "name": row["language_name"]}
        return render_template_string(LOGIN_PAGE, token=fake_token(),
                                      next=request.args.get("next", "/session"),
                                      lang=lang, lang_obj=lang_obj)

    gallery = (Path(__file__).parent / "gallery.html").read_text(encoding="utf-8")

    @app.route("/__preview/components")
    def preview_components():
        return render_template_string(gallery, task=False)

    @app.route("/__preview/task")
    def preview_task():
        return render_template_string(gallery, task=True)

    @app.route("/__preview/health")
    def preview_health():
        return {"ok": True}

    return app, stack


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=5099)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    app, stack = build()
    try:
        app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)
    finally:
        stack.close()


if __name__ == "__main__":
    main()
