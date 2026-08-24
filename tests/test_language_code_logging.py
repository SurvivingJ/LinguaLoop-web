"""`llm_calls.language_code` must actually get written when a caller supplies it,
and must stay NULL (never fabricated) when it doesn't (TASK-758 support).

Mirrors tests/test_llm_call_cost_logging.py's doubles and end-to-end pattern:
patch get_client + _log_llm_call, drive call_llm, assert on the captured
kwargs `_log_llm_call` would have inserted.
"""

from unittest.mock import patch

import pytest

import services.llm_service as svc


# ---------------------------------------------------------------------------
# Doubles (same shape as test_llm_call_cost_logging.py)
# ---------------------------------------------------------------------------

class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Usage:
    def __init__(self, cost=None):
        self.cost = cost
        self.model_extra = {}


class _Response:
    def __init__(self, content='{"ok": true}', usage=None):
        self.choices = [_Choice(content)]
        self.usage = usage or _Usage()


class _Completions:
    def __init__(self, response):
        self._response = response

    def create(self, **payload):
        return self._response


class _Chat:
    def __init__(self, response):
        self.completions = _Completions(response)


class _Client:
    def __init__(self, response, base_url='https://openrouter.ai/api/v1'):
        self.base_url = base_url
        self.chat = _Chat(response)


def _capture_log_rows():
    rows = []

    def fake_log(**kwargs):
        rows.append(kwargs)

    return rows, fake_log


# ---------------------------------------------------------------------------
# call_llm -> _log_llm_call: language_code threads through every response path
# ---------------------------------------------------------------------------

def test_call_llm_logs_the_supplied_language_code():
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response(content='{"ok": true}'))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash',
                     response_format='json_object', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics',
                     language_code='zh')

    assert len(rows) == 1
    assert rows[0]['language_code'] == 'zh'


def test_call_llm_logs_none_when_language_code_omitted():
    """No fabrication: a caller that doesn't know the language must log NULL,
    not guess one from the model or the pipeline."""
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response(content='{"ok": true}'))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash',
                     response_format='json_object', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics')

    assert rows[0]['language_code'] is None


def test_text_path_also_carries_language_code():
    """The text path short-circuits before the schema work — easy to miss
    (same lesson as test_llm_call_cost_logging.py's cost equivalent)."""
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response(content='plain text'))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash',
                     response_format='text', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics',
                     language_code='ja')

    assert rows[0]['language_code'] == 'ja'


def test_log_row_includes_language_code_key():
    """`_log_llm_call` must put the value in the row dict it inserts — pin the
    key name, not just the behaviour (same lesson as the cost_usd test)."""
    captured = {}

    class _Table:
        def insert(self, row):
            captured.update(row)
            return self

        def execute(self):
            return None

    class _DB:
        def table(self, _name):
            return _Table()

    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB()):
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
            cost_usd=None, language_code='en',
        )

    assert 'language_code' in captured
    assert captured['language_code'] == 'en'


def test_log_row_language_code_defaults_to_none():
    """Every existing call_llm caller that hasn't been threaded yet must keep
    working — omitting the kwarg must not raise and must log NULL."""
    captured = {}

    class _Table:
        def insert(self, row):
            captured.update(row)
            return self

        def execute(self):
            return None

    class _DB:
        def table(self, _name):
            return _Table()

    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB()):
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
        )

    assert captured['language_code'] is None
