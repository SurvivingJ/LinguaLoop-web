"""
llm_service plumbing: retry ladders, SDK retries, failed-primary logging.

Pins four defects found in review (D-01, D-02, D-03, D-04):

* D-01: a ClaudeCliError (timeout / non-zero exit) must not enter the
  malformed-JSON repair branch. Before the fix one failing headless JSON call
  ran 3 tenacity attempts x (primary + repair) = 6 subprocess invocations; it
  must be 3.
* D-02: a billed primary call that returns malformed JSON / empty content must
  still write its own llm_calls row (parsed_ok=False), not only the repair row.
* D-03: the OpenAI SDK's own retries (default 2) stacked inside tenacity's 3
  attempts (up to 9 HTTP tries). call_llm's client is built with
  max_retries=0; a default get_client() call keeps the SDK default.
"""

from unittest.mock import patch

import pytest

import services.llm_service as svc
from services import claude_cli_client as cli


@pytest.fixture(autouse=True)
def _instant_tenacity_and_clean_clients(monkeypatch):
    monkeypatch.setattr(svc.call_llm.retry, 'sleep', lambda *_a, **_k: None)
    saved = dict(svc._clients)
    svc._clients.clear()
    try:
        yield
    finally:
        svc._clients.clear()
        svc._clients.update(saved)


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]
        self.usage = None
        self.model = None


class _CountingCompletions:
    def __init__(self, behaviours):
        self._behaviours = list(behaviours)
        self.calls = 0

    def create(self, **payload):
        self.calls += 1
        b = self._behaviours[min(self.calls - 1, len(self._behaviours) - 1)]
        if isinstance(b, Exception):
            raise b
        return _Response(b)


class _Chat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    base_url = 'claude-cli://local'

    def __init__(self, behaviours):
        self.completions = _CountingCompletions(behaviours)
        self.chat = _Chat(self.completions)


# ---------------------------------------------------------------------------
# D-01
# ---------------------------------------------------------------------------

def test_cli_error_is_not_sent_into_json_repair():
    client = _FakeClient([cli.ClaudeCliError('Claude CLI timed out after 60s')])
    with patch.object(svc, 'get_client', return_value=client), \
            patch.object(svc, '_log_llm_call'):
        with pytest.raises(cli.ClaudeCliError):
            svc.call_llm('hi', provider='claude_cli', response_format='json')
    assert client.completions.calls == 3  # tenacity only; was 6


def test_malformed_json_from_real_content_is_still_repaired():
    client = _FakeClient(['not json at all', '{"ok": true}'])
    with patch.object(svc, 'get_client', return_value=client), \
            patch.object(svc, '_log_llm_call'):
        out = svc.call_llm('hi', provider='claude_cli', response_format='json')
    assert out == {'ok': True}
    assert client.completions.calls == 2


# ---------------------------------------------------------------------------
# D-02
# ---------------------------------------------------------------------------

def test_failed_primary_with_malformed_json_is_logged():
    client = _FakeClient(['not json at all', '{"ok": true}'])
    with patch.object(svc, 'get_client', return_value=client), \
            patch.object(svc, '_log_llm_call') as log:
        svc.call_llm('hi', provider='claude_cli', response_format='json',
                     task_name='t')
    rows = [c.kwargs for c in log.call_args_list]
    primaries = [r for r in rows if not r['task_name'].endswith('__json_repair')]
    assert len(primaries) == 1
    assert primaries[0]['parsed_ok'] is False
    assert primaries[0]['raw_response'] == 'not json at all'
    assert primaries[0]['task_name'] == 't'
    assert primaries[0]['error']


def test_failed_primary_with_empty_content_is_logged_and_still_raises():
    client = _FakeClient([''])
    with patch.object(svc, 'get_client', return_value=client), \
            patch.object(svc, '_log_llm_call') as log:
        with pytest.raises(RuntimeError):
            svc.call_llm('hi', provider='claude_cli', response_format='text')
    # one row per failing primary (text path re-raises; tenacity does not
    # retry a plain RuntimeError)
    rows = [c.kwargs for c in log.call_args_list]
    assert len(rows) == 1
    assert rows[0]['parsed_ok'] is False


# ---------------------------------------------------------------------------
# D-03
# ---------------------------------------------------------------------------

def test_default_get_client_keeps_sdk_retries():
    with patch.object(svc, 'OpenAI') as ctor:
        svc.get_client('ollama')
    assert 'max_retries' not in ctor.call_args.kwargs


def test_call_llm_client_is_built_with_no_sdk_retries():
    seen = {}

    def fake_ctor(**kw):
        seen.update(kw)
        return _FakeClient(['{"ok": true}'])

    with patch.object(svc, 'OpenAI', side_effect=fake_ctor), \
            patch.object(svc, '_log_llm_call'):
        svc.call_llm('hi', provider='ollama', response_format='json')
    assert seen.get('max_retries') == 0


def test_llm_runner_style_client_is_not_shared_with_call_llm():
    """get_client() default and call_llm's opt-in clients are cached apart."""
    with patch.object(svc, 'OpenAI', side_effect=lambda **kw: dict(kw)):
        default = svc.get_client('ollama')
        no_retry = svc.get_client('ollama', max_retries=0)
    assert 'max_retries' not in default
    assert no_retry['max_retries'] == 0


# ---------------------------------------------------------------------------
# D-04
# ---------------------------------------------------------------------------

def test_payload_timeout_takes_precedence_over_cli_default():
    """Documented precedence: payload timeout (call_llm always sends one) wins;
    CLAUDE_CLI_TIMEOUT only applies to a direct client call with no timeout."""
    import inspect
    src = inspect.getsource(cli.ClaudeCliClient)
    assert "payload.get('timeout') or CLAUDE_CLI_TIMEOUT" in src
    assert 'exercise_generation.llm_client' not in inspect.getsource(svc)
