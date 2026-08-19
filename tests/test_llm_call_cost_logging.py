"""
`llm_calls.cost_usd` must actually get written (TASK-515 support).

Why this file exists: the column existed, `run_generation_batch --ceiling`
projected spend from it, and the admin cost reporting read it — but nothing ever
populated it. 12,947 logged calls all carried NULL, so the budget ceiling
computed $0 spent no matter how much a batch actually cost, and silently never
fired. A ceiling that cannot trip is worse than no ceiling, because it is
trusted.

These tests pin the two halves of the fix: asking OpenRouter for usage
accounting, and threading the returned cost into the log row.
"""

from unittest.mock import patch

import pytest

import services.llm_service as svc


# ---------------------------------------------------------------------------
# Doubles
# ---------------------------------------------------------------------------

class _Usage:
    """Usage with `cost` as a real attribute (what a typed SDK model gives)."""

    def __init__(self, cost):
        self.cost = cost
        self.model_extra = {}


class _UsageExtraOnly:
    """Usage carrying `cost` only in `model_extra`.

    This is the shape that actually arrives: the OpenAI SDK's Usage model does
    not declare a `cost` field, so OpenRouter's addition lands in the pydantic
    extras bag rather than as an attribute. Reading only the attribute would
    return None against a live provider while passing a naive test.
    """

    def __init__(self, cost):
        self.model_extra = {'cost': cost}


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content='{"ok": true}', usage=None):
        self.choices = [_Choice(content)]
        self.usage = usage


class _Completions:
    def __init__(self, response):
        self._response = response
        self.last_payload = None

    def create(self, **payload):
        self.last_payload = payload
        return self._response


class _Chat:
    def __init__(self, response):
        self.completions = _Completions(response)


class _Client:
    def __init__(self, response, base_url='https://openrouter.ai/api/v1'):
        self.base_url = base_url
        self.chat = _Chat(response)


# ---------------------------------------------------------------------------
# _extract_cost
# ---------------------------------------------------------------------------

def test_extract_cost_reads_attribute():
    assert svc._extract_cost(_Response(usage=_Usage(0.00042))) == pytest.approx(0.00042)


def test_extract_cost_reads_model_extra():
    """The path that matters against a real OpenRouter response."""
    assert svc._extract_cost(
        _Response(usage=_UsageExtraOnly(0.0013))) == pytest.approx(0.0013)


def test_extract_cost_returns_none_when_provider_reports_nothing():
    """None, not 0.0.

    0.0 would read downstream as 'this call was free' and quietly deflate a
    running spend total; None reads as 'unknown', which is the truth.
    """
    assert svc._extract_cost(_Response(usage=None)) is None
    assert svc._extract_cost(_Response(usage=_Usage(None))) is None


def test_extract_cost_survives_a_non_numeric_cost():
    assert svc._extract_cost(_Response(usage=_Usage('not-a-number'))) is None


# ---------------------------------------------------------------------------
# Usage accounting is requested — only from OpenRouter
# ---------------------------------------------------------------------------

def test_openrouter_call_requests_usage_accounting():
    """Without this request body, OpenRouter returns tokens but never a price."""
    client = _Client(_Response(usage=_Usage(0.0002)))
    svc._make_one_call(
        client=client, model='m', messages=[{'role': 'user', 'content': 'hi'}],
        temperature=0.0, max_tokens=None, response_format='json_object',
        seed=None, timeout=10,
    )
    assert client.chat.completions.last_payload['extra_body'] == {
        'usage': {'include': True}}


def test_non_openrouter_call_does_not_send_the_openrouter_extra_body():
    """Ollama and friends reject unknown body keys; the flag is provider-scoped."""
    client = _Client(_Response(usage=None), base_url='http://localhost:11434/v1')
    svc._make_one_call(
        client=client, model='m', messages=[{'role': 'user', 'content': 'hi'}],
        temperature=0.0, max_tokens=None, response_format='json_object',
        seed=None, timeout=10,
    )
    assert 'extra_body' not in client.chat.completions.last_payload


def test_is_openrouter_detects_by_base_url():
    assert svc._is_openrouter(_Client(_Response())) is True
    assert svc._is_openrouter(
        _Client(_Response(), base_url='http://localhost:11434/v1')) is False
    assert svc._is_openrouter(object()) is False


# ---------------------------------------------------------------------------
# End to end: the cost reaches the log row
# ---------------------------------------------------------------------------

def _capture_log_rows():
    rows = []

    def fake_log(**kwargs):
        rows.append(kwargs)

    return rows, fake_log


def test_call_llm_logs_the_reported_cost():
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response(content='{"ok": true}', usage=_UsageExtraOnly(0.00311)))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash',
                     response_format='json_object', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics')

    assert len(rows) == 1
    assert rows[0]['cost_usd'] == pytest.approx(0.00311)


def test_call_llm_logs_none_cost_without_inventing_a_number():
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response(content='{"ok": true}', usage=None))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash',
                     response_format='json_object', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics')

    assert rows[0]['cost_usd'] is None


def test_text_responses_also_carry_cost():
    """The text path short-circuits before the schema work — easy to miss."""
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response(content='plain text', usage=_Usage(0.0007)))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash',
                     response_format='text', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics')

    assert rows[0]['cost_usd'] == pytest.approx(0.0007)


def test_log_row_includes_cost_usd_key():
    """`_log_llm_call` must put the value in the row dict it inserts.

    Pinning the key name specifically: the original defect was not a wrong
    value, it was an absent key, which no value-level assertion would catch.
    """
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
            cost_usd=0.005,
        )

    assert 'cost_usd' in captured
    assert captured['cost_usd'] == pytest.approx(0.005)
