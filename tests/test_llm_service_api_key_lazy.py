"""`OPENROUTER_API_KEY` must not be permanently frozen empty at import time.

Why this file exists: `services.llm_service` resolved
``OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')`` once, at module
import. Several standalone scripts (e.g. scripts/run_exercise_gen_eval.py,
scripts/smoke_llm_calls_logging.py) import ``services.llm_service`` — directly
or transitively — before calling their own ``load_dotenv()``. When that
happens, the module constant is baked in as ``''`` and stays that way for the
rest of the process: every OpenRouter call afterwards sends a blank bearer
token and gets a 401, even though the key is now sitting in `os.environ`.

The fix makes `_resolve_provider`/`get_client` re-read `os.environ` on every
call (falling back to the module constant only when the env var is unset at
call time), so a key set after import — by a late `load_dotenv()`, or by a
test — is picked up immediately. These tests pin that behaviour and the
client-cache keying it depends on.
"""

from unittest.mock import patch

import pytest

import services.llm_service as svc


@pytest.fixture(autouse=True)
def _clean_client_cache():
    """Isolate the module-level client pool across tests.

    `svc._clients` is a process-wide singleton cache keyed by
    `(base_url, api_key)`. Leaving entries from one test visible to the next
    would hide a real cache-key bug (stale client reused for a new key) or
    manufacture a fake pass (a fresh client created for a key that should
    have been cached).
    """
    saved = dict(svc._clients)
    svc._clients.clear()
    try:
        yield
    finally:
        svc._clients.clear()
        svc._clients.update(saved)


def test_resolve_provider_uses_key_set_after_import(monkeypatch):
    """A key present in the environment NOW must win, even if the module
    constant was frozen empty at import time (simulated here directly)."""
    monkeypatch.setattr(svc, 'OPENROUTER_API_KEY', '')  # simulate frozen-empty import
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-set-after-import')

    base_url, api_key = svc._resolve_provider('openrouter')

    assert api_key == 'sk-set-after-import'
    assert base_url == svc.OPENROUTER_BASE_URL


def test_resolve_provider_falls_back_to_module_constant_when_env_unset(monkeypatch):
    """If the env var is unset at call time, fall back to whatever the
    module constant captured at import (the pre-existing, already-correct
    behaviour for the common case where the key was loaded before import)."""
    monkeypatch.setattr(svc, 'OPENROUTER_API_KEY', 'sk-from-import-time')
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)

    _, api_key = svc._resolve_provider('openrouter')

    assert api_key == 'sk-from-import-time'


def test_get_client_constructs_openai_with_live_key(monkeypatch):
    """get_client() must hand the OpenAI constructor the CURRENT key, not a
    value frozen at import, and must key its singleton cache on that value
    so a later key change produces a distinct client rather than reusing a
    stale one."""
    monkeypatch.setattr(svc, 'OPENROUTER_API_KEY', '')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-live-key')

    captured = {}

    class _FakeOpenAI:
        def __init__(self, api_key, base_url):
            captured['api_key'] = api_key
            captured['base_url'] = base_url

    with patch.object(svc, 'OpenAI', _FakeOpenAI):
        client = svc.get_client('openrouter')

    assert captured['api_key'] == 'sk-live-key'
    assert isinstance(client, _FakeOpenAI)

    # Changing the env-resolved key must produce a NEW cache entry (the pool
    # is keyed on (base_url, api_key)), not silently reuse the old client
    # under the old blank-key cache slot.
    monkeypatch.setenv('OPENROUTER_API_KEY', 'sk-rotated-key')
    with patch.object(svc, 'OpenAI', _FakeOpenAI):
        client2 = svc.get_client('openrouter')

    assert captured['api_key'] == 'sk-rotated-key'
    assert client2 is not client
