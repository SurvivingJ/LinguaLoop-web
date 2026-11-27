"""LLM_CALLS_DB_LOGGING switch on services/llm_service._log_llm_call.

When false, the llm_calls insert is skipped (a bulk run must not grow a
database near its size cap) while the daily CSV log and the cost hooks still
see the call. Read at call time, not import time.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services import llm_service
from services import supabase_factory


class _Client:
    def __init__(self):
        self.inserts = []

    def table(self, name):
        client = self

        class _Q:
            def insert(self, row):
                client.inserts.append((name, dict(row)))
                return self

            def execute(self):
                return SimpleNamespace(data=[])
        return _Q()


@pytest.fixture
def sinks(monkeypatch):
    client = _Client()
    csv_rows, events = [], []
    monkeypatch.setattr(supabase_factory, 'get_supabase_admin', lambda: client)
    monkeypatch.setattr(supabase_factory, 'get_supabase', lambda: client)
    monkeypatch.setattr(llm_service, '_log_llm_call_csv', csv_rows.append)
    unsubscribe = llm_service.subscribe_llm_cost_hook(events.append)
    yield SimpleNamespace(client=client, csv=csv_rows, events=events)
    unsubscribe()


def _log():
    llm_service._log_llm_call(
        pipeline='exercise_explanations', task_name='spot_error_explanation',
        template_version=2, model='m/x', temperature=0.2, seed=None, prompt_hash=b'\x01',
        raw_response='{"sentences": []}', parsed_ok=True, schema_ok=None,
        judge_verdict=None, judge_confidence=None, latency_ms=12, artifact_id='e1',
        cost_usd=0.0002,
    )


def test_default_writes_the_db_row(sinks, monkeypatch):
    monkeypatch.delenv('LLM_CALLS_DB_LOGGING', raising=False)
    assert llm_service.llm_calls_db_logging_enabled() is True
    _log()
    assert [name for name, _ in sinks.client.inserts] == ['llm_calls']
    assert len(sinks.csv) == 1 and len(sinks.events) == 1


@pytest.mark.parametrize('value', ['false', 'FALSE', ' False ', '0', 'no', 'off'])
def test_false_skips_the_db_row_but_keeps_csv_and_cost_hook(sinks, monkeypatch, value):
    monkeypatch.setenv('LLM_CALLS_DB_LOGGING', value)
    assert llm_service.llm_calls_db_logging_enabled() is False
    _log()
    assert sinks.client.inserts == []
    assert len(sinks.csv) == 1 and sinks.csv[0]['task_name'] == 'spot_error_explanation'
    assert len(sinks.events) == 1 and sinks.events[0]['cost_usd'] == 0.0002


@pytest.mark.parametrize('value', ['true', 'True', '1', 'yes', ''])
def test_other_values_keep_db_logging_on(sinks, monkeypatch, value):
    monkeypatch.setenv('LLM_CALLS_DB_LOGGING', value)
    _log()
    assert len(sinks.client.inserts) == 1


def test_read_at_call_time(sinks, monkeypatch):
    monkeypatch.setenv('LLM_CALLS_DB_LOGGING', 'false')
    _log()
    monkeypatch.setenv('LLM_CALLS_DB_LOGGING', 'true')
    _log()
    assert len(sinks.client.inserts) == 1
    assert len(sinks.csv) == 2
