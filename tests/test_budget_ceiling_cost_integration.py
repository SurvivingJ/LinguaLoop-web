"""Budget ceiling, exercised end-to-end from a mocked LLM response.

tests/test_generation_batch_workers.py already pins the ceiling-abort
arithmetic in run_chunk, but it does so by monkeypatching
``run_generation_batch.spend_since`` directly — it never proves that a real
LLM response carrying a cost actually turns into a row ``spend_since`` can
read. This file closes that gap: it mocks only the OpenRouter HTTP call (via
services.llm_service's client pool), lets the REAL call_llm -> _log_llm_call
-> spend_since chain run unmocked, and checks the ceiling still trips.

Why this matters (TASK-515 support, restated): the whole point of Phase 0 is
that a budget ceiling is only as trustworthy as the column it reads. A test
that mocks spend_since proves the arithmetic; this one proves the wiring in
front of it — that a dollar OpenRouter reports is a dollar spend_since counts.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

import pytest

import services.llm_service as svc
from scripts import run_generation_batch as batch


# ---------------------------------------------------------------------------
# A fake Supabase-like DB whose 'llm_calls' table is a real, queryable list —
# writes from _log_llm_call land in the same store spend_since() reads from.
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, data):
        self.data = data


class _LLMCallsTable:
    """Serves both the insert side (_log_llm_call) and the select side
    (spend_since / _judge_verdicts_since) against one shared row list."""

    def __init__(self, rows: list):
        self._rows = rows
        self._pending_insert = None
        self._since = None
        self._not_null_col = None
        self.not_ = self

    def insert(self, row):
        self._pending_insert = dict(row)
        return self

    def select(self, *_a, **_k):
        return self

    def gte(self, _col, since_iso):
        self._since = since_iso
        return self

    def is_(self, col, _val):
        self._not_null_col = col
        return self

    def execute(self):
        if self._pending_insert is not None:
            row = self._pending_insert
            row.setdefault('created_at', datetime.now(timezone.utc).isoformat())
            self._rows.append(row)
            self._pending_insert = None
            return _Resp([row])

        rows = self._rows
        if self._since is not None:
            rows = [r for r in rows if r.get('created_at', '') >= self._since]
        if self._not_null_col is not None:
            rows = [r for r in rows if r.get(self._not_null_col) is not None]
        return _Resp(list(rows))


class _GenericTable:
    """Swallows the exercises/word_assets chains _process_sense runs —
    same shape as test_generation_batch_workers.py's _FakeQuery."""

    def __init__(self, sink=None, rows=None):
        self._sink = sink
        self._rows = rows
        self.not_ = self

    def delete(self):
        return self

    def insert(self, rows):
        return _GenericTable(self._sink, rows)

    def eq(self, *_a, **_k):
        return self

    def is_(self, *_a, **_k):
        return self

    def execute(self):
        if self._rows is not None and self._sink is not None:
            self._sink.extend(self._rows)
        return self


class _CombinedDB:
    """Routes 'llm_calls' to a real queryable store, everything else to a
    no-op sink — exactly what run_chunk touches for a scripted-success sense.
    """

    def __init__(self):
        self.llm_calls_rows: list = []
        self.other_inserted: list = []

    def table(self, name):
        if name == 'llm_calls':
            return _LLMCallsTable(self.llm_calls_rows)
        return _GenericTable(self.other_inserted)


# ---------------------------------------------------------------------------
# A minimal fake OpenRouter client — the only thing actually mocked
# ---------------------------------------------------------------------------

class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Usage:
    def __init__(self, cost):
        self.cost = cost
        self.model_extra = {}


class _Response:
    def __init__(self, content, cost):
        self.choices = [_Choice(content)]
        self.usage = _Usage(cost)
        self.model = None


class _Completions:
    def __init__(self, cost_per_call: float):
        self._cost_per_call = cost_per_call

    def create(self, **_payload):
        return _Response('{"ok": true}', self._cost_per_call)


class _Chat:
    def __init__(self, cost_per_call: float):
        self.completions = _Completions(cost_per_call)


class _FakeOpenRouterClient:
    """base_url deliberately contains 'openrouter' — this is what
    ``_is_openrouter`` keys off to request usage accounting at all."""

    def __init__(self, cost_per_call: float):
        self.base_url = 'https://openrouter.ai/api/v1'
        self.chat = _Chat(cost_per_call)


# ---------------------------------------------------------------------------
# A pipeline whose "generation" is one real call_llm() call per sense —
# exercising the actual cost-logging path, not a scripted status dict.
# ---------------------------------------------------------------------------

class _CostLoggingPipeline:
    """generate_for_sense places one real (mocked-transport) call_llm() call
    per sense, at a fixed cost, then reports success — so run_chunk's ceiling
    check is fed by genuine llm_calls rows rather than a stubbed number."""

    cost_per_call: float = 0.50

    def __init__(self, _db=None):
        pass

    def generate_for_sense(self, sense_id, language_id):
        svc.call_llm(
            f'generate sense {sense_id}',
            model='google/gemini-3.5-flash-lite',
            response_format='json_object',
            provider='openrouter',
            pipeline='vocab_ladder',
            task_name='vocab_prompt1_core',
            sense_id=sense_id,
        )
        return {'status': 'success', 'errors': []}


class _NoOpRenderer:
    def __init__(self, _db=None):
        self.last_skips: list = []

    def build_rows(self, sense_id, _language_id):
        return [{'word_sense_id': sense_id}]


def _senses(n: int) -> list[dict]:
    return [{'sense_id': i, 'lemma': f'word{i}'} for i in range(1, n + 1)]


@pytest.fixture
def _wire_real_cost_path(monkeypatch):
    """Point run_chunk's late imports at the cost-logging fakes, patch the LLM
    transport, and route llm_service's observability writes at the SAME
    _CombinedDB instance run_chunk itself queries via spend_since — that
    shared instance is what makes this an integration test rather than two
    independently-mocked halves.
    """
    import services.vocabulary_ladder.asset_pipeline as ap
    import services.vocabulary_ladder.exercise_renderer as er
    import services.vocabulary_ladder.queue_drain as qd

    db = _CombinedDB()
    fake_client = _FakeOpenRouterClient(_CostLoggingPipeline.cost_per_call)

    monkeypatch.setattr(ap, 'VocabAssetPipeline', _CostLoggingPipeline)
    monkeypatch.setattr(er, 'LadderExerciseRenderer', _NoOpRenderer)
    monkeypatch.setattr(qd, 'enqueue', lambda *a, **k: True)
    monkeypatch.setattr(svc, 'get_client', lambda *a, **kw: fake_client)
    monkeypatch.setattr(
        'services.supabase_factory.get_supabase_admin', lambda: db,
    )
    # Deliberately NOT monkeypatching batch.spend_since or
    # batch._judge_verdicts_since — those must run for real against `db`.
    return db


def test_real_llm_cost_reaches_spend_since_and_trips_the_ceiling(_wire_real_cost_path):
    db = _wire_real_cost_path

    # 20 senses x $0.50/call = $10 actual spend; a $1 ceiling must abort well
    # before the chunk finishes. workers=1 keeps the interleaving deterministic
    # so the "every 10 completed" check lands predictably.
    report = batch.run_chunk(db, 1, _senses(20), 1.00, False, workers=1)

    assert report.aborted_reason is not None
    assert 'exceeds ceiling' in report.aborted_reason
    # The abort must have fired before all 20 were attempted.
    assert report.succeeded < 20
    # And the cost it read must be real, not a stub — every $0.50 sense that
    # got to run should show up in spend_since's own accounting.
    assert report.cost_usd >= 0.50 * report.succeeded


def test_llm_calls_rows_actually_carry_the_reported_cost(_wire_real_cost_path):
    """Sanity check on the fixture itself: prove the rows landed with
    cost_usd set, independent of the ceiling logic."""
    db = _wire_real_cost_path

    batch.run_chunk(db, 1, _senses(3), None, False, workers=1)

    assert len(db.llm_calls_rows) == 3
    for row in db.llm_calls_rows:
        assert row['cost_usd'] == pytest.approx(0.50)
        assert row['pipeline'] == 'vocab_ladder'


def test_ceiling_is_not_tripped_when_spend_stays_under_it(_wire_real_cost_path):
    db = _wire_real_cost_path

    # 12 senses x $0.50 = $6, but a $100 ceiling should never fire.
    report = batch.run_chunk(db, 1, _senses(12), 100.00, False, workers=1)

    assert report.aborted_reason is None
    assert report.succeeded == 12


# ---------------------------------------------------------------------------
# spend_since itself: sums cost_usd, filters by time, ignores NULLs
# ---------------------------------------------------------------------------

def test_spend_since_sums_only_rows_with_a_cost_and_since_the_cutoff():
    db = _CombinedDB()
    db.llm_calls_rows.extend([
        {'cost_usd': 0.10, 'created_at': '2026-01-01T00:00:00+00:00'},
        {'cost_usd': 0.20, 'created_at': '2026-01-02T00:00:00+00:00'},
        {'cost_usd': None, 'created_at': '2026-01-02T00:00:01+00:00'},  # NULL cost, excluded
        {'cost_usd': 0.30, 'created_at': '2025-12-31T00:00:00+00:00'},  # before cutoff, excluded
    ])

    spent = batch.spend_since(db, '2026-01-01T00:00:00+00:00')

    assert spent == pytest.approx(0.30)  # only the two rows from 2026-01-01 onward with non-null cost
