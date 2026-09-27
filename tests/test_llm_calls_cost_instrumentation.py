"""Phase 0 cost instrumentation: the new llm_calls columns actually get
written, the writer degrades gracefully before the migration lands, and
call_role/sense_id/generation_batch_id thread through every response path
(including the repair/json_repair branches).

Mirrors tests/test_llm_call_cost_logging.py's doubles and end-to-end pattern:
patch get_client + (where appropriate) the supabase table, drive call_llm,
assert on what the logger tried to insert.
"""

from unittest.mock import patch

import pytest
from pydantic import BaseModel

import services.llm_service as svc


class _RequiredFieldSchema(BaseModel):
    value: int


# ---------------------------------------------------------------------------
# Doubles
# ---------------------------------------------------------------------------

class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _PromptTokensDetails:
    def __init__(self, cached_tokens=None):
        self.cached_tokens = cached_tokens
        self.model_extra = {}


class _CompletionTokensDetails:
    def __init__(self, reasoning_tokens=None):
        self.reasoning_tokens = reasoning_tokens


class _Usage:
    def __init__(self, cost=None, prompt_tokens=None, completion_tokens=None,
                 cached_tokens=None, reasoning_tokens=None):
        self.cost = cost
        self.model_extra = {}
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.prompt_tokens_details = _PromptTokensDetails(cached_tokens)
        self.completion_tokens_details = _CompletionTokensDetails(reasoning_tokens)


class _Response:
    def __init__(self, content='{"ok": true}', usage=None, model=None):
        self.choices = [_Choice(content)]
        self.usage = usage or _Usage()
        self.model = model


class _Completions:
    def __init__(self, response):
        self._response = response

    def create(self, **payload):
        return self._response


class _SequencedCompletions:
    """Returns each queued response in order — one per ``create()`` call —
    for exercising a primary call followed by its repair turn."""

    def __init__(self, responses):
        self._responses = list(responses)

    def create(self, **payload):
        return self._responses.pop(0)


class _Chat:
    def __init__(self, response):
        self.completions = _Completions(response)


class _SequencedChat:
    def __init__(self, responses):
        self.completions = _SequencedCompletions(responses)


class _Client:
    def __init__(self, response, base_url='https://openrouter.ai/api/v1'):
        self.base_url = base_url
        self.chat = _Chat(response)


class _SequencedClient:
    def __init__(self, responses, base_url='https://openrouter.ai/api/v1'):
        self.base_url = base_url
        self.chat = _SequencedChat(responses)


def _capture_log_rows():
    rows = []

    def fake_log(**kwargs):
        rows.append(kwargs)

    return rows, fake_log


# ---------------------------------------------------------------------------
# Token / cache field extraction and threading through call_llm
# ---------------------------------------------------------------------------

def test_extract_usage_tokens_reads_cached_and_reasoning_tokens():
    usage = _Usage(prompt_tokens=100, completion_tokens=40,
                    cached_tokens=64, reasoning_tokens=12)
    result = svc._extract_usage_tokens(_Response(usage=usage))
    assert result == (100, 40, 64, 12)


def test_extract_usage_tokens_all_none_when_no_usage():
    assert svc._extract_usage_tokens(_Response(usage=None)) == (None, None, None, None)


def test_call_llm_logs_prompt_completion_cached_reasoning_tokens():
    rows, fake_log = _capture_log_rows()
    usage = _Usage(cost=0.001, prompt_tokens=200, completion_tokens=50,
                    cached_tokens=80, reasoning_tokens=5)
    client = _Client(_Response(content='{"ok": true}', usage=usage))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash',
                     response_format='json_object', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics')

    assert len(rows) == 1
    assert rows[0]['input_tokens'] == 200
    assert rows[0]['output_tokens'] == 50
    assert rows[0]['cached_tokens'] == 80
    assert rows[0]['reasoning_tokens'] == 5


def test_text_path_also_carries_cached_and_reasoning_tokens():
    """The text path short-circuits before schema work — the same lesson the
    cost_usd and language_code tests already pin, extended to the new fields."""
    rows, fake_log = _capture_log_rows()
    usage = _Usage(cached_tokens=10, reasoning_tokens=3)
    client = _Client(_Response(content='plain text', usage=usage))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash',
                     response_format='text', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics')

    assert rows[0]['cached_tokens'] == 10
    assert rows[0]['reasoning_tokens'] == 3


# ---------------------------------------------------------------------------
# Actual served model, from the response
# ---------------------------------------------------------------------------

def test_call_llm_logs_the_actual_model_from_the_response():
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response(content='{"ok": true}',
                                model='google/gemini-3.5-flash-lite-001'))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash-lite',
                     response_format='json_object', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics')

    assert rows[0]['model'] == 'google/gemini-3.5-flash-lite-001'


def test_call_llm_falls_back_to_requested_model_when_response_omits_it():
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response(content='{"ok": true}', model=None))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='google/gemini-3.5-flash-lite',
                     response_format='json_object', provider='openrouter',
                     task_name='unit_probe', pipeline='diagnostics')

    assert rows[0]['model'] == 'google/gemini-3.5-flash-lite'


# ---------------------------------------------------------------------------
# call_role / sense_id / generation_batch_id — explicit args
# ---------------------------------------------------------------------------

def test_call_role_defaults_to_primary_when_omitted():
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response())

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='m', response_format='json_object',
                     provider='openrouter', task_name='t', pipeline='p')

    # call_llm itself passes through whatever it was given (None here);
    # _log_llm_call is the layer that defaults it to 'primary' — pinned below.
    assert rows[0]['call_role'] is None


def test_explicit_call_role_and_sense_id_reach_the_log_call():
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response())

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm('prompt', model='m', response_format='json_object',
                     provider='openrouter', task_name='t', pipeline='p',
                     call_role='retry', sense_id=123,
                     generation_batch_id='batch-xyz')

    assert rows[0]['call_role'] == 'retry'
    assert rows[0]['sense_id'] == 123
    assert rows[0]['generation_batch_id'] == 'batch-xyz'


# ---------------------------------------------------------------------------
# generation_context contextvar fallback
# ---------------------------------------------------------------------------

def test_generation_context_threads_sense_id_and_batch_id_when_not_explicit():
    """The contextvar fallback lives inside ``_log_llm_call`` itself (it
    resolves ``sense_id if sense_id is not None else _ctx_sense_id.get()``),
    so this has to exercise the real function against a fake DB rather than
    mocking ``_log_llm_call`` away — a mock would just echo back the ``None``
    call_llm passes through and never touch the ambient context at all.
    """
    captured = []
    llm_client = _Client(_Response())

    with patch.object(svc, 'get_client', lambda *a, **kw: llm_client), \
         patch('services.supabase_factory.get_supabase_admin',
               lambda: _DB(captured)):
        with svc.generation_context(sense_id=42, generation_batch_id='batch-1'):
            svc.call_llm('prompt', model='m', response_format='json_object',
                         provider='openrouter', task_name='t', pipeline='p')

    assert captured[0]['sense_id'] == 42
    assert captured[0]['generation_batch_id'] == 'batch-1'


def test_explicit_sense_id_overrides_ambient_context():
    rows, fake_log = _capture_log_rows()
    client = _Client(_Response())

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        with svc.generation_context(sense_id=42, generation_batch_id='batch-1'):
            svc.call_llm('prompt', model='m', response_format='json_object',
                         provider='openrouter', task_name='t', pipeline='p',
                         sense_id=99)

    assert rows[0]['sense_id'] == 99


def test_context_resets_after_the_block():
    with svc.generation_context(sense_id=42):
        assert svc._ctx_sense_id.get() == 42
    assert svc._ctx_sense_id.get() is None


# ---------------------------------------------------------------------------
# _log_llm_call: call_role default + the DB row it actually builds
# ---------------------------------------------------------------------------

class _Table:
    def __init__(self, captured):
        self._captured = captured

    def insert(self, row):
        self._captured.append(row)
        return self

    def execute(self):
        return None


class _DB:
    def __init__(self, captured):
        self._captured = captured

    def table(self, _name):
        return _Table(self._captured)


def test_log_llm_call_defaults_call_role_to_primary_in_the_row():
    captured = []
    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB(captured)):
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
        )
    assert captured[0]['call_role'] == 'primary'


def test_log_llm_call_rejects_unknown_call_role_to_primary():
    """A typo'd/legacy call_role must not slip an unconstrained value into a
    CHECK-constrained column — fall back rather than let the insert 500."""
    captured = []
    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB(captured)):
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
            call_role='not_a_real_role',
        )
    assert captured[0]['call_role'] == 'primary'


def test_log_llm_call_writes_new_columns_into_the_row():
    captured = []
    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB(captured)):
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
            input_tokens=10, output_tokens=20, cached_tokens=5,
            reasoning_tokens=2, sense_id=7, call_role='repair',
            generation_batch_id='batch-9',
        )
    row = captured[0]
    assert row['prompt_tokens'] == 10
    assert row['completion_tokens'] == 20
    assert row['cached_tokens'] == 5
    assert row['reasoning_tokens'] == 2
    assert row['sense_id'] == 7
    assert row['call_role'] == 'repair'
    assert row['generation_batch_id'] == 'batch-9'


# ---------------------------------------------------------------------------
# Fail-soft: insertion errors never raise back into the caller
# ---------------------------------------------------------------------------

class _AlwaysFailsTable:
    def insert(self, row):
        return self

    def execute(self):
        raise RuntimeError('connection refused')


class _AlwaysFailsDB:
    def table(self, _name):
        return _AlwaysFailsTable()


def test_log_llm_call_never_raises_on_a_genuine_db_outage():
    with patch('services.supabase_factory.get_supabase_admin', lambda: _AlwaysFailsDB()):
        # Must not raise — observability failures are logged (WARNING) and
        # swallowed, never propagated into the generation pipeline.
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
        )


def test_call_llm_never_raises_when_observability_is_completely_down(monkeypatch):
    """End-to-end: a dead observability sink must not break generation."""
    client = _Client(_Response(content='{"ok": true}'))
    monkeypatch.setattr(svc, 'get_client', lambda *a, **kw: client)
    monkeypatch.setattr(
        'services.supabase_factory.get_supabase_admin',
        lambda: _AlwaysFailsDB(),
    )
    monkeypatch.setattr('services.supabase_factory.get_supabase', lambda: None)

    result = svc.call_llm('prompt', model='m', response_format='json_object',
                          provider='openrouter', task_name='t', pipeline='p')
    assert result == {'ok': True}


# ---------------------------------------------------------------------------
# Degrade path: insert fails because the new columns don't exist yet
# ---------------------------------------------------------------------------

class _MissingColumnTable:
    """First insert() raises a PostgREST-style 'unknown column' error; the
    retry (without the new columns) succeeds."""

    def __init__(self, captured):
        self._captured = captured
        self._pending_row = None

    def insert(self, row):
        self._pending_row = row
        return self

    def execute(self):
        row = self._pending_row
        if any(col in row for col in svc._NEW_LLM_CALLS_COLUMNS):
            raise RuntimeError(
                "Could not find the 'sense_id' column of 'llm_calls' in the "
                "schema cache"
            )
        self._captured.append(row)
        return None


class _MissingColumnDB:
    def __init__(self, captured):
        self._captured = captured

    def table(self, _name):
        return _MissingColumnTable(self._captured)


def test_insert_degrades_to_pre_migration_columns_on_unknown_column_error():
    captured = []
    svc._warned_missing_llm_calls_columns = False  # isolate from other tests
    try:
        with patch('services.supabase_factory.get_supabase_admin',
                   lambda: _MissingColumnDB(captured)):
            svc._log_llm_call(
                pipeline='p', task_name='t', template_version=None, model='m',
                temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
                parsed_ok=True, schema_ok=None, judge_verdict=None,
                judge_confidence=None, latency_ms=1, artifact_id=None,
                cost_usd=0.01, sense_id=7, call_role='repair',
            )
    finally:
        svc._warned_missing_llm_calls_columns = False

    # The row still landed — degraded, not dropped.
    assert len(captured) == 1
    row = captured[0]
    assert row['cost_usd'] == pytest.approx(0.01)
    assert 'sense_id' not in row
    assert 'call_role' not in row
    for col in svc._NEW_LLM_CALLS_COLUMNS:
        assert col not in row


def test_missing_column_warning_fires_once_per_process(caplog):
    import logging

    captured = []
    svc._warned_missing_llm_calls_columns = False
    try:
        with patch('services.supabase_factory.get_supabase_admin',
                   lambda: _MissingColumnDB(captured)):
            with caplog.at_level(logging.WARNING, logger='services.llm_service'):
                for _ in range(3):
                    svc._log_llm_call(
                        pipeline='p', task_name='t', template_version=None,
                        model='m', temperature=0.0, seed=None,
                        prompt_hash=None, raw_response='x', parsed_ok=True,
                        schema_ok=None, judge_verdict=None,
                        judge_confidence=None, latency_ms=1, artifact_id=None,
                    )
    finally:
        svc._warned_missing_llm_calls_columns = False

    degrade_warnings = [
        r for r in caplog.records
        if 'not yet applied' in r.getMessage() or 'missing the cost-instrumentation' in r.getMessage()
    ]
    assert len(degrade_warnings) == 1
    assert len(captured) == 3  # all three rows still landed, degraded


def test_insert_llm_call_row_reraises_genuine_non_column_errors():
    """A real outage must not be silently reinterpreted as 'missing columns'
    and masked by a fallback retry that also fails for an unrelated reason."""

    class _NetworkErrorTable:
        def insert(self, row):
            return self

        def execute(self):
            raise ConnectionError('connection reset by peer')

    class _NetworkErrorDB:
        def table(self, _name):
            return _NetworkErrorTable()

    with pytest.raises(ConnectionError):
        svc._insert_llm_call_row(_NetworkErrorDB(), {'pipeline': 'p'})


# ---------------------------------------------------------------------------
# call_role on the REAL repair paths (not just an explicit kwarg) — driven
# through call_llm end-to-end so the internal repair helpers' own call_role
# is what's actually pinned, not a value a test handed them.
# ---------------------------------------------------------------------------

def test_schema_validation_repair_logs_call_role_repair():
    """A schema-invalid first response triggers ``_repair_and_retry``, which
    must log its own row with call_role='repair'."""
    rows, fake_log = _capture_log_rows()
    client = _SequencedClient([
        _Response(content='{"value": "not-an-int"}'),  # fails schema
        _Response(content='{"value": 5}'),              # repair succeeds
    ])

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        result = svc.call_llm(
            'prompt', model='m', response_format='json_object',
            provider='openrouter', task_name='t', pipeline='p',
            schema=_RequiredFieldSchema,
        )

    assert result.value == 5
    # First row: the failed primary attempt (schema_ok=False, no call_role
    # override — defaults resolve inside _log_llm_call, not here).
    assert rows[0]['schema_ok'] is False
    # Second row: the repair turn itself.
    assert rows[1]['task_name'] == 't__repair'
    assert rows[1]['call_role'] == svc.CALL_ROLE_REPAIR
    assert rows[1]['schema_ok'] is True


def test_malformed_json_repair_logs_call_role_json_repair():
    """A non-JSON first response triggers ``_repair_malformed_json``."""
    rows, fake_log = _capture_log_rows()
    client = _SequencedClient([
        _Response(content='not valid json at all'),
        _Response(content='{"ok": true}'),
    ])

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        result = svc.call_llm(
            'prompt', model='m', response_format='json_object',
            provider='openrouter', task_name='t', pipeline='p',
        )

    assert result == {'ok': True}
    assert len(rows) == 1  # only the repair call logs (the malformed
    # first attempt never reaches _log_llm_call — json.JSONDecodeError is
    # raised before any of call_llm's three _log_llm_call call sites).
    assert rows[0]['task_name'] == 't__json_repair'
    assert rows[0]['call_role'] == svc.CALL_ROLE_JSON_REPAIR


def test_sense_id_and_batch_id_reach_the_repair_rows_too():
    """The repair helpers must forward sense_id/generation_batch_id, not just
    call_role — otherwise a repaired call's cost is invisible to a per-sense
    cost breakdown even though the primary attempt's was captured."""
    rows, fake_log = _capture_log_rows()
    client = _SequencedClient([
        _Response(content='{"value": "nope"}'),
        _Response(content='{"value": 1}'),
    ])

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch.object(svc, '_log_llm_call', fake_log):
        svc.call_llm(
            'prompt', model='m', response_format='json_object',
            provider='openrouter', task_name='t', pipeline='p',
            schema=_RequiredFieldSchema, sense_id=555,
            generation_batch_id='batch-555',
        )

    repair_row = next(r for r in rows if r['task_name'] == 't__repair')
    assert repair_row['sense_id'] == 555
    assert repair_row['generation_batch_id'] == 'batch-555'


# ---------------------------------------------------------------------------
# Cost-hook subscribers (ADR-028 Phase 0) -- the fix for the inert harness
# cost cap. `_log_llm_call` always writes `llm_calls` through
# `get_supabase_admin()` directly, so a caller that injects its own Supabase
# client (e.g. an eval harness) never sees that write. These tests pin the
# in-process observer mechanism that lets such a caller see real spend
# anyway, independent of the DB write's outcome.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_cost_hook_subscribers():
    """Every test in this module gets a clean subscriber list -- it's a
    module-level global in services.llm_service, so a test that forgets to
    unsubscribe would otherwise leak into every later test in the process."""
    svc._cost_hook_subscribers.clear()
    yield
    svc._cost_hook_subscribers.clear()


def test_subscribe_llm_cost_hook_receives_the_expected_fields():
    events = []
    svc.subscribe_llm_cost_hook(events.append)

    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB([])):
        svc._log_llm_call(
            pipeline='vocab_ladder', task_name='vocab_prompt1_core',
            template_version=3, model='qwen/qwen3.7-plus',
            temperature=0.2, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=True, judge_verdict=None,
            judge_confidence=None, latency_ms=456, artifact_id=None,
            cost_usd=0.0123, language_code='en',
            input_tokens=100, output_tokens=50, cached_tokens=10,
            reasoning_tokens=0, sense_id=14010, call_role='primary',
            generation_batch_id='batch-abc',
        )

    assert len(events) == 1
    event = events[0]
    assert event['task_name'] == 'vocab_prompt1_core'
    assert event['model'] == 'qwen/qwen3.7-plus'
    assert event['cost_usd'] == pytest.approx(0.0123)
    assert event['prompt_tokens'] == 100
    assert event['completion_tokens'] == 50
    assert event['cached_tokens'] == 10
    assert event['reasoning_tokens'] == 0
    assert event['call_role'] == 'primary'
    assert event['sense_id'] == 14010
    assert event['latency_ms'] == 456
    assert event['generation_batch_id'] == 'batch-abc'


def test_cost_hook_fires_even_when_the_db_write_fails():
    """The hook must not depend on the Supabase write succeeding -- that's
    the whole reason it exists (observability sinks are best-effort/fail-soft
    by design, but the *caller watching cost* still needs to know)."""
    events = []
    svc.subscribe_llm_cost_hook(events.append)

    with patch('services.supabase_factory.get_supabase_admin', lambda: _AlwaysFailsDB()):
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
            cost_usd=0.5,
        )

    assert len(events) == 1
    assert events[0]['cost_usd'] == pytest.approx(0.5)


def test_cost_hook_uses_ambient_sense_id_from_generation_context():
    """A caller (e.g. the harness) that never passes sense_id explicitly to
    call_llm must still see it on the hook event, via the same contextvar
    fallback the DB row itself uses."""
    events = []
    svc.subscribe_llm_cost_hook(events.append)
    client = _Client(_Response())

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch('services.supabase_factory.get_supabase_admin', lambda: None), \
         patch('services.supabase_factory.get_supabase', lambda: None):
        with svc.generation_context(sense_id=777, generation_batch_id='batch-777'):
            svc.call_llm('prompt', model='m', response_format='json_object',
                         provider='openrouter', task_name='t', pipeline='p')

    assert len(events) == 1
    assert events[0]['sense_id'] == 777
    assert events[0]['generation_batch_id'] == 'batch-777'


def test_multiple_subscribers_all_receive_the_event():
    events_a, events_b = [], []
    svc.subscribe_llm_cost_hook(events_a.append)
    svc.subscribe_llm_cost_hook(events_b.append)

    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB([])):
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
            cost_usd=0.02,
        )

    assert len(events_a) == 1 and len(events_b) == 1


def test_unsubscribe_stops_further_notifications():
    events = []
    unsubscribe = svc.subscribe_llm_cost_hook(events.append)
    unsubscribe()

    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB([])):
        svc._log_llm_call(
            pipeline='p', task_name='t', template_version=None, model='m',
            temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
            parsed_ok=True, schema_ok=None, judge_verdict=None,
            judge_confidence=None, latency_ms=1, artifact_id=None,
            cost_usd=0.02,
        )

    assert events == []


def test_broken_subscriber_never_raises_into_the_caller(caplog):
    """Fail-soft: a subscriber that raises must be logged and swallowed, not
    propagated -- the whole point is that observability can't break
    generation, and a cost-hook subscriber is still observability."""
    import logging

    def _broken(_event):
        raise RuntimeError('subscriber blew up')

    good_events = []
    svc.subscribe_llm_cost_hook(_broken)
    svc.subscribe_llm_cost_hook(good_events.append)

    with patch('services.supabase_factory.get_supabase_admin', lambda: _DB([])):
        with caplog.at_level(logging.WARNING, logger='services.llm_service'):
            svc._log_llm_call(
                pipeline='p', task_name='t', template_version=None, model='m',
                temperature=0.0, seed=None, prompt_hash=None, raw_response='x',
                parsed_ok=True, schema_ok=None, judge_verdict=None,
                judge_confidence=None, latency_ms=1, artifact_id=None,
                cost_usd=0.02,
            )

    # The broken subscriber didn't stop the second one from firing, and
    # didn't raise out of _log_llm_call.
    assert len(good_events) == 1
    assert any('cost-hook subscriber raised' in r.getMessage() for r in caplog.records)


def test_call_llm_never_raises_when_a_cost_hook_subscriber_is_broken():
    """End-to-end: call_llm itself must survive a broken cost-hook subscriber,
    the same way it survives a dead DB/CSV sink."""
    def _broken(_event):
        raise RuntimeError('nope')

    svc.subscribe_llm_cost_hook(_broken)
    client = _Client(_Response(content='{"ok": true}'))

    with patch.object(svc, 'get_client', lambda *a, **kw: client), \
         patch('services.supabase_factory.get_supabase_admin', lambda: None), \
         patch('services.supabase_factory.get_supabase', lambda: None):
        result = svc.call_llm('prompt', model='m', response_format='json_object',
                              provider='openrouter', task_name='t', pipeline='p')

    assert result == {'ok': True}
