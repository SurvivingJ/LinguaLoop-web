#!/usr/bin/env python3
"""
Phase 0 (TASK-808 prep) — non-persisting cost/quality harness for the
vocabulary-ladder exercise generation pipeline.

Runs the REAL generation pipeline (services.vocabulary_ladder.asset_pipeline.
VocabAssetPipeline._generate_for_sense_impl + services.vocabulary_ladder.
exercise_renderer.LadderExerciseRenderer.build_rows) for a list of senses,
capturing every generated asset, rendered exercise row, and render-judge
verdict to local JSON — WITHOUT writing anything to word_assets, exercises,
dim_vocabulary, dim_word_senses, or generation_queue.

This file creates no dependency on, and makes no edits to, any existing
pipeline file. It only *injects* a fake Supabase client into the two
pipeline classes above (both already accept `db=` in their constructors) and
calls the pipeline's own methods directly.

Persistence is intercepted as follows
--------------------------------------
Reads (select/.rpc() lookups) go straight to the real Supabase admin client,
because the pipeline needs live dictionary/corpus data to generate anything
sensible.

Writes are split into two buckets:

  * CAPTURED_WRITE_TABLES ('word_assets', 'exercises', 'dim_vocabulary',
    'dim_word_senses', 'generation_queue') — every insert/upsert/update/
    delete on these tables is recorded in memory and NEVER reaches the
    database. This is the harness's whole reason to exist.

  * PASSTHROUGH_WRITE_TABLES ('llm_calls') — left live on purpose. This is
    the cost/latency measurement the harness exists to read back; blocking
    it would defeat the point. Every row is also mirrored into this
    process's own in-memory ledger so `--max-cost-usd` and the summary can
    read a cost total even in an environment where the
    generation_batch_id/sense_id columns (migrations/
    llm_calls_cost_instrumentation.sql) have not been applied yet.

Any write attempted on a table in neither bucket, or any `.rpc()` call not
on the read-only allowlist below, raises `UnexpectedWriteError` and aborts
the run — fail closed rather than silently letting an unanticipated write
through. See the module docstring on `InterceptingClient` for exactly why
each table/RPC is where it is.

Known write path this harness deliberately avoids rather than intercepts
--------------------------------------------------------------------------
`VocabAssetPipeline.generate_for_sense()` (the public wrapper) calls
`services.timing.log_stage_seconds()` after the real work is done, which
fetches its OWN Supabase client via `get_supabase_admin()` — bypassing
whatever `db=` this harness injected — and inserts into
`generation_stage_timings`. There is no way to intercept that from outside
without patching `services.timing` or `services.supabase_factory`, which is
out of scope (new files only). This harness sidesteps it entirely by calling
the private `VocabAssetPipeline._generate_for_sense_impl()` directly (this
is also the entry point named in the TASK-808 prep brief) — the stage-timing
side effect only exists on the public wrapper, so it is never invoked, and
`result['stage_seconds']` (the same data `log_stage_seconds` would have
persisted) is captured into this harness's own JSON output instead.

Usage
-----
    PYTHONPATH=. python scripts/run_exercise_gen_eval.py \\
        --reference data/eval/exercise_gen_reference_set_2026-09.json \\
        --lang zh --use top_up_candidates --limit 30 \\
        --label zh_topup_baseline --max-cost-usd 3.0

    PYTHONPATH=. python scripts/run_exercise_gen_eval.py \\
        --senses 12345,67890 --lang ja --out data/eval/runs/adhoc/
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import re
import sys
import threading
import time
import traceback
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable, Iterable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger('exercise_gen_eval')

LANG_CODE_TO_ID: dict[str, int] = {'zh': 1, 'en': 2, 'ja': 3}

# Every table this harness has confirmed (by reading asset_pipeline.py and
# exercise_renderer.py end to end) is written by generate_for_sense /
# _generate_for_sense_impl / build_rows / render_all:
#   - word_assets:      VocabAssetPipeline._store_asset (upsert)
#   - dim_vocabulary:    VocabAssetPipeline._update_vocabulary_metadata (update)
#   - dim_word_senses:   VocabAssetPipeline._update_vocabulary_metadata (update)
#   - exercises:         LadderExerciseRenderer.render_all (insert) -- not
#                         reached by this harness (it calls build_rows(),
#                         which never writes), kept in the allowlist as a
#                         belt-and-braces guard in case a future caller uses
#                         render_all() instead.
#   - generation_queue:  not reached by generate_for_sense/build_rows today
#                         (only services/vocabulary_ladder/queue_drain.py
#                         touches it), included defensively per the task
#                         brief so a future coupling doesn't silently write.
CAPTURED_WRITE_TABLES: frozenset[str] = frozenset({
    'word_assets', 'exercises', 'dim_vocabulary', 'dim_word_senses',
    'generation_queue',
})

# llm_calls is the measurement, not a side effect -- left live, and also
# mirrored into this process's own cost ledger (see InterceptingTable).
PASSTHROUGH_WRITE_TABLES: frozenset[str] = frozenset({'llm_calls'})

# Every `.rpc()` call reachable from _generate_for_sense_impl / build_rows,
# confirmed by grepping services/vocabulary_ladder, services/exercise_generation
# and services/vocabulary for `.rpc(` and tracing which of those call sites
# are actually on this code path:
#   - tests_containing_sense:    VocabAssetPipeline._fetch_corpus_sentences
#   - get_distractors:           VocabularyKnowledgeService (L2 render, via
#                                 exercise_renderer._render_definition_match)
#   - sense_similarity_to_lemmas: services/vocabulary_ladder/sense_neighbours.py,
#                                 used by asset_generators/syn_ant.py (typed L*)
# All three are read-only lookups (cosine similarity / candidate fetch), not
# mutations. Anything else raises -- fail closed.
READ_ONLY_RPC_ALLOWLIST: frozenset[str] = frozenset({
    'tests_containing_sense', 'get_distractors', 'sense_similarity_to_lemmas',
})

COST_QUERY_SQL_TEMPLATE = """\
SELECT task_name, call_role, model,
       COUNT(*)          AS calls,
       SUM(cost_usd)     AS total_cost_usd,
       AVG(cost_usd)     AS avg_cost_usd
FROM llm_calls
WHERE generation_batch_id = '{batch_id}'
GROUP BY task_name, call_role, model
ORDER BY total_cost_usd DESC NULLS LAST;
"""


class UnexpectedWriteError(RuntimeError):
    """Raised when the pipeline attempts a write this harness did not anticipate.

    Fail-closed: an unrecognised table/RPC might mutate live content, and
    silently swallowing it would be worse than crashing the run.
    """


class _FakeResponse:
    """Minimal stand-in for a postgrest APIResponse -- only `.data` is read
    by any of the call sites this harness exercises."""

    def __init__(self, data=None):
        self.data = data or []
        self.count = None


class _FakeWriteBuilder:
    """Returned in place of the real insert/upsert/update/delete builder.

    Absorbs any further filter chaining (`.eq()`, `.in_()`, ...) exactly the
    way the real postgrest builder would, and turns the eventual `.execute()`
    into a captured no-op instead of a network call.
    """

    def __init__(self, record: dict):
        self._record = record

    def __getattr__(self, name):
        if name == 'execute':
            def _execute(*_a, **_kw):
                return _FakeResponse(data=[])
            return _execute

        def _chain(*args, **kwargs):
            self._record.setdefault('filters', []).append((name, args, kwargs))
            return self
        return _chain


class InterceptingTable:
    """One `.table(name)` handle.

    Any read method (select, eq, single, order, limit, execute on a read
    chain, ...) is passed straight through to the real underlying table
    object. insert/upsert/update/delete are intercepted per the module-level
    docstring: captured-and-blocked for CAPTURED_WRITE_TABLES, passed
    through live (and mirrored into `capture_sink`) for
    PASSTHROUGH_WRITE_TABLES, and raise UnexpectedWriteError for anything
    else.
    """

    _WRITE_VERBS = ('insert', 'upsert', 'update', 'delete')

    def __init__(self, real_table, name: str, capture_sink: list, lock: threading.Lock):
        self._real = real_table
        self._name = name
        self._capture_sink = capture_sink
        self._lock = lock

    def __getattr__(self, name):
        real_attr = getattr(self._real, name, None) if self._real is not None else None

        if name in self._WRITE_VERBS:
            def _write(*args, **kwargs):
                record = {
                    'table': self._name,
                    'verb': name,
                    'args': args,
                    'kwargs': kwargs,
                    'filters': [],
                    'ts': datetime.now(timezone.utc).isoformat(),
                }

                if self._name in PASSTHROUGH_WRITE_TABLES:
                    if name == 'insert' and args and isinstance(args[0], dict):
                        cost = args[0].get('cost_usd')
                        if cost is not None:
                            record['cost_usd'] = cost
                    with self._lock:
                        self._capture_sink.append(record)
                    if real_attr is None:
                        raise UnexpectedWriteError(
                            f"'{self._name}' is configured to pass through live "
                            f"(it is the cost measurement) but no real Supabase "
                            f"client is attached to this harness run."
                        )
                    return real_attr(*args, **kwargs)

                if self._name not in CAPTURED_WRITE_TABLES:
                    raise UnexpectedWriteError(
                        f"Unexpected {name}() on table '{self._name}'. This "
                        f"harness's known write surface is "
                        f"{sorted(CAPTURED_WRITE_TABLES)} (captured, never "
                        f"executed) plus {sorted(PASSTHROUGH_WRITE_TABLES)} "
                        f"(passed through live). Fail-closed: refusing to "
                        f"guess whether this write is safe to fake."
                    )

                with self._lock:
                    self._capture_sink.append(record)
                return _FakeWriteBuilder(record)
            return _write

        # Everything else -- select, eq, in_, match, single, order, limit,
        # execute (on a read chain) -- is a read. Reads stay live.
        if real_attr is None:
            raise RuntimeError(
                f"Read method '{name}' called on table '{self._name}' but no "
                f"real Supabase client is attached to this harness run."
            )
        return real_attr


class InterceptingClient:
    """Drop-in substitute for the Supabase client passed to
    `VocabAssetPipeline(db=...)` / `LadderExerciseRenderer(db=...)`.

    Both classes already accept an explicit `db` in their constructor for
    exactly this kind of injection -- no monkeypatching of pipeline files
    needed. `capture_sink` and `lock` are shared across every
    InterceptingClient built for a single harness run, so writes from
    concurrently-processed senses land in one place and can be attributed
    back to a sense_id from their own payload (see `_extract_sense_id`).
    """

    def __init__(self, real_client, capture_sink: list, lock: threading.Lock):
        self._real = real_client
        self._capture_sink = capture_sink
        self._lock = lock

    def table(self, name: str) -> InterceptingTable:
        real_table = self._real.table(name) if self._real is not None else None
        return InterceptingTable(real_table, name, self._capture_sink, self._lock)

    def rpc(self, name: str, params: dict | None = None):
        if name not in READ_ONLY_RPC_ALLOWLIST:
            raise UnexpectedWriteError(
                f"Unexpected RPC '{name}'. This harness's read-only RPC "
                f"allowlist is {sorted(READ_ONLY_RPC_ALLOWLIST)}. Fail-closed: "
                f"an unvetted RPC may mutate data, and this harness has not "
                f"verified this one is safe."
            )
        if self._real is None:
            raise RuntimeError(f"RPC '{name}' called but no real Supabase client is attached.")
        return self._real.rpc(name, params or {})

    def __getattr__(self, name):
        if self._real is None:
            raise AttributeError(name)
        return getattr(self._real, name)


# ---------------------------------------------------------------------------
# Shadow read-back for the render stage (ADR-028 Phase 0 fix)
# ---------------------------------------------------------------------------
#
# Root cause of the "en prompt1_core fails" symptom the pilot run showed:
# it does NOT fail. `data/eval/runs/pilot_en/*.json` shows prompt1_core
# `is_valid: true` for both senses (after one repair round -- see
# llm_calls task_name='vocab_prompt1_core_repair', both `parsed_ok=True`,
# model google/gemini-3.5-flash-lite -- en's live prompt_templates row, NOT
# qwen; qwen3.7-plus is zh/ja). Generation legitimately proceeded to P2/P3/L4/
# typed for both senses because P1 validated -- `_generate_for_sense_impl`
# (asset_pipeline.py lines ~150-172) already returns before the P2/P3 fan-out
# whenever P1 is None or still invalid after repair, so there is no "wasted
# spend" bug there to fix.
#
# What actually produces "No valid prompt1_core for sense %s — cannot render"
# (exercise_renderer.py) and 0 exercise_rows is this harness's own
# architecture: `LadderExerciseRenderer.build_rows()` re-queries `word_assets`
# fresh rather than being handed the just-generated content directly --
# exactly how production chains generation and rendering on ONE real `db`
# (services/vocabulary_ladder/queue_drain.py::_regenerate), so a write really
# lands before the very next read. This harness deliberately BLOCKS the
# `word_assets` write (see CAPTURED_WRITE_TABLES) so the render stage's read
# never sees it -- for ANY `top_up_candidates` sense (no pre-existing valid
# word_assets row), in ANY language. This reproduces identically for zh (see
# data/eval/runs/pilot_zh/*.json: status=success, 0 exercise_rows, no
# errors) -- it was never en-specific, en's pilot just also happened to hit
# an unrelated prompt3_transforms `level_8` gap in the same run.
#
# The fix: give the RENDERER's injected client a shadow read for
# `word_assets` that overlays this run's own captured (but not persisted)
# upserts on top of the live read, so `build_rows()` sees what THIS run just
# generated -- without ever letting the write actually reach the database.

class _ShadowSelectBuilder:
    """Fake read builder over an in-memory overlay of `word_assets` rows.

    Implements exactly the chain `exercise_renderer.py` actually uses
    (`select(...).eq(col, val).eq(col2, val2).execute()`) -- eq filters are
    applied to both the real (live) query, so it stays cheap/filtered, and to
    the in-memory shadow rows. Any other chain method (not used by the two
    call sites today) is forwarded to the real builder only, so an unexpected
    future call degrades to "shadow rows are not filtered by it" rather than
    raising.
    """

    def __init__(self, real_builder, shadow_rows: list[dict]):
        self._real_builder = real_builder
        self._shadow_rows = shadow_rows
        self._filters: list[tuple] = []

    def eq(self, column, value):
        self._filters.append((column, value))
        if self._real_builder is not None:
            self._real_builder = self._real_builder.eq(column, value)
        return self

    def __getattr__(self, name):
        if self._real_builder is None:
            raise AttributeError(name)

        def _passthrough(*args, **kwargs):
            self._real_builder = getattr(self._real_builder, name)(*args, **kwargs)
            return self
        return _passthrough

    def execute(self):
        live_rows: list[dict] = []
        if self._real_builder is not None:
            try:
                live_rows = self._real_builder.execute().data or []
            except Exception as exc:
                logger.warning("Shadow read-back: live word_assets query failed "
                                "(%s) -- serving shadow-only rows.", exc)

        shadow_rows = list(self._shadow_rows)
        for column, value in self._filters:
            shadow_rows = [r for r in shadow_rows if r.get(column) == value]

        # Shadow (this run's own captured write) wins over a live row for the
        # same (sense_id, asset_type) -- it postdates whatever the live DB
        # had when this run started.
        merged: dict[tuple, dict] = {}
        for row in live_rows:
            merged[(row.get('sense_id'), row.get('asset_type'))] = dict(row)
        for row in shadow_rows:
            merged[(row.get('sense_id'), row.get('asset_type'))] = dict(row)

        rows = list(merged.values())
        for row in rows:
            row.setdefault('id', f"shadow-{row.get('sense_id')}-{row.get('asset_type')}")
        return _FakeResponse(data=rows)


class ShadowWordAssetsTable:
    """`.table('word_assets')` stand-in that overlays this run's own captured
    upserts on top of a live read. See the module note above this class for
    why this exists. Non-select attributes (there are none on the renderer's
    read-only path, but this stays defensive) forward to the wrapped
    InterceptingTable unchanged."""

    def __init__(self, intercepting_table, capture_sink: list, lock: threading.Lock):
        self._intercepting_table = intercepting_table
        self._capture_sink = capture_sink
        self._lock = lock

    def select(self, *args, **kwargs):
        real_builder = None
        if self._intercepting_table is not None:
            real_builder = self._intercepting_table.select(*args, **kwargs)

        with self._lock:
            records = [
                r for r in self._capture_sink
                if r['table'] == 'word_assets' and r['verb'] in ('insert', 'upsert')
            ]
        shadow_rows = []
        for r in records:
            args_ = r.get('args') or ()
            payload = args_[0] if args_ else None
            if isinstance(payload, dict):
                shadow_rows.append(dict(payload))

        return _ShadowSelectBuilder(real_builder, shadow_rows)

    def __getattr__(self, name):
        return getattr(self._intercepting_table, name)


class ShadowReadClient:
    """Wraps an `InterceptingClient` so a `word_assets` read overlays this
    run's own captured (harness-blocked) writes on top of the live read.
    Every other table/RPC passes straight through unchanged. Intended for the
    RENDER stage's `db` only -- the generation stage should keep reading
    real, unmodified DB state."""

    def __init__(self, intercepting_client, capture_sink: list, lock: threading.Lock):
        self._client = intercepting_client
        self._capture_sink = capture_sink
        self._lock = lock

    def table(self, name: str):
        wrapped = self._client.table(name)
        if name == 'word_assets':
            return ShadowWordAssetsTable(wrapped, self._capture_sink, self._lock)
        return wrapped

    def rpc(self, name: str, params: dict | None = None):
        return self._client.rpc(name, params)

    def __getattr__(self, name):
        return getattr(self._client, name)


# ---------------------------------------------------------------------------
# Write-record attribution / cost ledger
# ---------------------------------------------------------------------------

def _extract_sense_id(record: dict) -> int | None:
    """Best-effort sense_id for a captured write, read from its own payload
    rather than from any harness-side thread/contextvar bookkeeping -- this
    stays correct even when a write happens on a nested worker thread the
    harness itself never touches (e.g. an `llm_calls` insert from inside
    VocabAssetPipeline's internal BatchModeThreadPoolExecutor fan-out).
    """
    table = record['table']
    args = record.get('args') or ()
    payload = args[0] if args else None

    if table in ('word_assets', 'llm_calls') and isinstance(payload, dict):
        return payload.get('sense_id')

    if table == 'exercises' and payload is not None:
        rows = payload if isinstance(payload, list) else [payload]
        ids = {r.get('word_sense_id') for r in rows if isinstance(r, dict)}
        if len(ids) == 1:
            return next(iter(ids))
        return None

    if table == 'dim_word_senses' and record.get('verb') == 'update':
        for fname, fargs, _fkwargs in record.get('filters', []):
            if fname == 'eq' and len(fargs) >= 2 and fargs[0] == 'id':
                return fargs[1]

    # dim_vocabulary updates are keyed by vocab_id, not sense_id -- no
    # reliable attribution available from the payload alone.
    return None


def _local_cost_total(capture_sink: list, lock: threading.Lock) -> float:
    """Best-effort running cost total from observed llm_calls inserts.

    Falls back for environments where the generation_batch_id column
    (migrations/llm_calls_cost_instrumentation.sql) isn't applied yet, so a
    DB-side SUM(cost_usd) WHERE generation_batch_id=... can't be run. Can
    double-count a single logical call if `_insert_llm_call_row`'s
    missing-column fallback path re-inserts a trimmed row after the first
    insert's `.execute()` fails (rare, and only before that migration
    lands) -- the DB-side cross-check in `query_batch_cost_from_db` is the
    authoritative source whenever it's available.
    """
    with lock:
        return sum((r.get('cost_usd') or 0) for r in capture_sink if r['table'] == 'llm_calls')


class CostHookLedger:
    """In-process observer of every real LLM call, via
    ``services.llm_service.subscribe_llm_cost_hook``.

    Fixes the "harness cost cap is inert" bug: ``_log_llm_call`` always writes
    ``llm_calls`` through ``get_supabase_admin()`` directly, bypassing
    whatever ``InterceptingClient`` this harness injects into the pipeline /
    renderer -- so the old capture_sink-based ledger (built from writes that
    passed through the injected ``db``) never saw a single real llm_calls
    row, and ``--max-cost-usd`` never tripped. This subscribes to the module-
    level cost hook instead, which fires synchronously and in-process right
    after ``_log_llm_call`` computes its row -- independent of whether that
    Supabase write itself succeeds, and independent of whether the
    generation_batch_id/sense_id columns (migrations/
    llm_calls_cost_instrumentation.sql) have been applied.

    Must be ``stop()``-ed when a run finishes (``run_eval`` does this in a
    ``finally``) -- the subscriber list in ``services.llm_service`` is
    process-global, so a leaked subscription would keep counting cost from
    unrelated later calls in the same process.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: list[dict] = []
        self._unsubscribe: Callable[[], None] | None = None

    def start(self) -> None:
        if self._unsubscribe is not None:
            return
        from services.llm_service import subscribe_llm_cost_hook
        self._unsubscribe = subscribe_llm_cost_hook(self._on_event)

    def stop(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _on_event(self, event: dict) -> None:
        with self._lock:
            self._rows.append(dict(event))

    def total_cost_usd(self) -> float:
        with self._lock:
            return sum((r.get('cost_usd') or 0) for r in self._rows)

    def rows_for_sense(self, sense_id) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._rows if r.get('sense_id') == sense_id]

    def all_rows(self) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._rows]


def _summarize_cost_rows(rows: Iterable[dict]) -> list[dict]:
    """Local, DB-free equivalent of ``COST_QUERY_SQL_TEMPLATE`` -- grouped
    call counts/cost by (task_name, call_role, model), computed from whatever
    cost rows this run actually observed (capture_sink 'llm_calls' writes plus
    the cost-hook ledger). Written into summary.json so a run's cost breakdown
    is readable even in an environment where the DB-side query can't be run
    (no generation_batch_id column yet, or no DB access at all)."""
    grouped: dict[tuple, dict] = {}
    for r in rows:
        key = (r.get('task_name'), r.get('call_role'), r.get('model'))
        g = grouped.setdefault(key, {
            'task_name': key[0], 'call_role': key[1], 'model': key[2],
            'calls': 0, 'total_cost_usd': 0.0,
        })
        g['calls'] += 1
        g['total_cost_usd'] += r.get('cost_usd') or 0
    out = list(grouped.values())
    for g in out:
        g['avg_cost_usd'] = (g['total_cost_usd'] / g['calls']) if g['calls'] else None
    out.sort(key=lambda g: g['total_cost_usd'], reverse=True)
    return out


def query_batch_cost_from_db(real_client, batch_id: str) -> float | None:
    """Authoritative cost total for this run, or None if it can't be read
    (no real client, or the cost-instrumentation columns aren't applied)."""
    if real_client is None:
        return None
    try:
        resp = (
            real_client.table('llm_calls')
            .select('cost_usd')
            .eq('generation_batch_id', batch_id)
            .execute()
        )
        rows = resp.data or []
        return sum((r.get('cost_usd') or 0) for r in rows)
    except Exception as exc:
        logger.warning(
            "Cost cap DB cross-check failed (%s) -- falling back to the "
            "local llm_calls ledger for this run.", exc,
        )
        return None


# ---------------------------------------------------------------------------
# Per-sense processing
# ---------------------------------------------------------------------------

def _extract_assets(records: Iterable[dict]) -> list[dict]:
    out = []
    for r in records:
        if r['table'] != 'word_assets':
            continue
        args = r.get('args') or ()
        payload = args[0] if args else None
        if not isinstance(payload, dict):
            continue
        out.append({
            'asset_type': payload.get('asset_type'),
            'is_valid': payload.get('is_valid'),
            'model_used': payload.get('model_used'),
            'validation_errors': payload.get('validation_errors'),
            'validation_warnings': payload.get('validation_warnings'),
        })
    return out


def _extract_metadata_updates(records: Iterable[dict]) -> list[dict]:
    out = []
    for r in records:
        if r['table'] not in ('dim_vocabulary', 'dim_word_senses'):
            continue
        args = r.get('args') or ()
        payload = args[0] if args else None
        out.append({
            'table': r['table'],
            'payload': payload if isinstance(payload, dict) else None,
            'filters': r.get('filters'),
        })
    return out


def _summarize_judges(rows: Iterable[dict]) -> dict:
    """Render-judge verdicts, read off `exercises.tags['<judge>_judge']`.

    That sidecar shape ({"rejected": N, "kept": M, ...}) is shared across
    every render-time judge (l1_distractor, cloze, collocation,
    sentence_validity) -- see services/exercise_generation/cloze_judge.py's
    docstring on `filter_l1_distractors` for the canonical shape.
    """
    summary: dict = {}
    for row in rows or []:
        tags = row.get('tags') or {}
        for key, meta in tags.items():
            if not key.endswith('_judge') or not isinstance(meta, dict):
                continue
            judge_key = key[: -len('_judge')]
            entry = summary.setdefault(judge_key, {'ran': 0, 'rejected': 0, 'kept': 0})
            entry['ran'] += 1
            entry['rejected'] += int(meta.get('rejected') or 0)
            entry['kept'] += int(meta.get('kept') or 0)
    return summary


def _skip_to_dict(skip) -> dict:
    if dataclasses.is_dataclass(skip) and not isinstance(skip, type):
        return dataclasses.asdict(skip)
    return {'type_code': getattr(skip, 'type_code', None), 'reason': getattr(skip, 'reason', None)}


def process_one_sense(
    pipeline,
    renderer,
    sense_id: int,
    language_id: int,
    batch_id: str,
    capture_sink: list,
    lock: threading.Lock,
    force: bool = False,
    *,
    cost_ledger: 'CostHookLedger | None' = None,
    max_cost_usd: float | None = None,
) -> dict:
    """Run generation + rendering for one sense against injected fakes.

    `pipeline` must expose `_generate_for_sense_impl(sense_id, language_id,
    force, batch_id)` (VocabAssetPipeline's real signature); `renderer` must
    expose `build_rows(sense_id, language_id)` and a `last_skips` attribute
    (LadderExerciseRenderer's real shape). Both are called directly so tests
    can pass stand-ins with the same interface.

    `cost_ledger`, when given, is a `CostHookLedger` already subscribed to
    `services.llm_service`'s cost hook for the whole run -- it is the
    authoritative source of this sense's `llm_calls` rows (real production
    code always logs through that hook; a write through the injected `db` is
    the exception, kept only for a stub/test pipeline). When `max_cost_usd` is
    also given, generation and rendering are two separately-billable stages
    (P1/P2/P3/typed for generation; render-time judges for rendering) --
    checking the running total between them means a sense that already blew
    the budget during generation skips rendering entirely rather than
    spending more money on output that was, per the task brief, waste anyway
    (nothing renders without a valid prompt1_core, and the harness's whole
    point is bounding spend).
    """
    from services.llm_service import generation_context

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()
    capture: dict = {
        'sense_id': sense_id,
        'language_id': language_id,
        'generation_batch_id': batch_id,
        'started_at': started_at,
        'status': 'error',
        'errors': [],
        'warnings': [],
        'stage_seconds': {},
        'assets': [],
        'metadata_updates': [],
        'exercise_rows': [],
        'judges': {},
        'deterministic_skips': [],
        'llm_calls': [],
        'llm_calls_observed': 0,
        'llm_cost_observed_usd': 0.0,
        'render_skipped_cost_cap': False,
        'exceptions': [],
    }

    try:
        with generation_context(sense_id=sense_id, generation_batch_id=batch_id):
            gen_result = pipeline._generate_for_sense_impl(
                sense_id, language_id, force, batch_id,
            )
        capture['status'] = gen_result.get('status', 'unknown')
        capture['errors'] = gen_result.get('errors', [])
        capture['warnings'] = gen_result.get('warnings', [])
        capture['stage_seconds'] = gen_result.get('stage_seconds', {})
        capture['tier_gate'] = gen_result.get('tier_gate')
        capture['collocate_grounding'] = gen_result.get('collocate_grounding')
    except Exception as exc:
        capture['exceptions'].append({
            'stage': 'generate', 'error': repr(exc), 'trace': traceback.format_exc(),
        })

    # Abort in-flight work between pipeline stages: if the run's cost cap was
    # already reached during generation (P1/P2/P3/typed), rendering (which
    # runs its own render-time judge LLM calls) is pure additional spend on
    # top of a run that is about to stop anyway -- skip it rather than pay for
    # output the harness will never use.
    cap_already_hit = (
        max_cost_usd is not None and cost_ledger is not None
        and cost_ledger.total_cost_usd() >= max_cost_usd
    )
    if capture['status'] in ('success', 'partial') and cap_already_hit:
        capture['render_skipped_cost_cap'] = True
        capture['warnings'] = list(capture['warnings']) + [
            f"render stage skipped: cost cap ${max_cost_usd:.4f} already "
            f"reached (${cost_ledger.total_cost_usd():.4f} observed) during "
            f"generation for this sense",
        ]
    elif capture['status'] in ('success', 'partial'):
        try:
            with generation_context(sense_id=sense_id, generation_batch_id=batch_id):
                rows = renderer.build_rows(sense_id, language_id)
            capture['exercise_rows'] = rows
            capture['deterministic_skips'] = [
                _skip_to_dict(s) for s in (getattr(renderer, 'last_skips', None) or [])
            ]
            capture['judges'] = _summarize_judges(rows)
        except Exception as exc:
            capture['exceptions'].append({
                'stage': 'render', 'error': repr(exc), 'trace': traceback.format_exc(),
            })

    with lock:
        relevant = [r for r in capture_sink if _extract_sense_id(r) == sense_id]
    capture['assets'] = _extract_assets(relevant)
    capture['metadata_updates'] = _extract_metadata_updates(relevant)

    # llm_calls rows come from two possible sources: a write that happened to
    # go through the injected `db` (capture_sink -- only ever exercised by a
    # stub/test pipeline today, see CostHookLedger's docstring), and the
    # cost-hook ledger (what real production code actually uses, since
    # services.llm_service._log_llm_call always writes through
    # get_supabase_admin() directly). Neither source can double-log the same
    # call today, so it's safe to combine them.
    sink_llm_rows = [r for r in relevant if r['table'] == 'llm_calls']
    ledger_llm_rows = cost_ledger.rows_for_sense(sense_id) if cost_ledger else []
    llm_rows = sink_llm_rows + ledger_llm_rows
    capture['llm_calls'] = llm_rows
    capture['llm_calls_observed'] = len(llm_rows)
    capture['llm_cost_observed_usd'] = sum((r.get('cost_usd') or 0) for r in llm_rows)

    capture['wall_clock_s'] = time.monotonic() - t0
    capture['finished_at'] = datetime.now(timezone.utc).isoformat()
    return capture


def _write_sense_json(out_dir: str, capture: dict) -> None:
    path = os.path.join(out_dir, f"{capture['sense_id']}.json")
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(capture, fh, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Run orchestration
# ---------------------------------------------------------------------------

def build_summary(
    captures: list[dict],
    capture_sink: list,
    run_wall_clock_s: float,
    stopped_due_to_cost_cap: bool,
    cost_total: float | None,
    batch_id: str,
    requested_count: int,
    *,
    cost_ledger: 'CostHookLedger | None' = None,
) -> dict:
    status_counts = Counter(c['status'] for c in captures)

    assets_per_sense = {c['sense_id']: len(c['assets']) for c in captures}

    invalid_by_type: dict = defaultdict(lambda: {'valid': 0, 'invalid': 0})
    for c in captures:
        for a in c['assets']:
            bucket = invalid_by_type[a.get('asset_type') or 'unknown']
            bucket['invalid' if not a.get('is_valid') else 'valid'] += 1
    invalid_rate_by_type = {
        k: {
            **v,
            'invalid_rate': (v['invalid'] / (v['valid'] + v['invalid']))
                            if (v['valid'] + v['invalid']) else None,
        }
        for k, v in invalid_by_type.items()
    }

    exercises_per_sense = {}
    for c in captures:
        by_type = Counter(r.get('exercise_type') for r in c['exercise_rows'])
        by_level = Counter(r.get('ladder_level') for r in c['exercise_rows'])
        exercises_per_sense[c['sense_id']] = {
            'total': len(c['exercise_rows']),
            'by_type': dict(by_type),
            'by_level': {str(k): v for k, v in by_level.items()},
        }

    judge_totals: dict = defaultdict(lambda: {'ran': 0, 'rejected': 0, 'kept': 0})
    for c in captures:
        for judge_key, stats in (c.get('judges') or {}).items():
            judge_totals[judge_key]['ran'] += stats.get('ran', 0)
            judge_totals[judge_key]['rejected'] += stats.get('rejected', 0)
            judge_totals[judge_key]['kept'] += stats.get('kept', 0)

    unattributed_writes = [
        r for r in capture_sink
        if r['table'] != 'llm_calls' and _extract_sense_id(r) is None
    ]

    all_llm_call_rows = [r for r in capture_sink if r['table'] == 'llm_calls']
    all_llm_call_rows += cost_ledger.all_rows() if cost_ledger else []

    return {
        'batch_id': batch_id,
        'requested_senses': requested_count,
        'attempted_senses': len(captures),
        'status_counts': dict(status_counts),
        'run_wall_clock_s': run_wall_clock_s,
        'per_sense_wall_clock_s': {c['sense_id']: c['wall_clock_s'] for c in captures},
        'assets_per_sense': assets_per_sense,
        'invalid_asset_rate_by_type': invalid_rate_by_type,
        'exercises_per_sense': exercises_per_sense,
        'judge_reject_counts': dict(judge_totals),
        'cost_usd_total_observed': cost_total,
        'stopped_due_to_cost_cap': stopped_due_to_cost_cap,
        'llm_calls_observed_count': len(all_llm_call_rows),
        'llm_calls_cost_breakdown': _summarize_cost_rows(all_llm_call_rows),
        'unattributed_writes_count': len(unattributed_writes),
        'unattributed_writes_sample': [
            {'table': w['table'], 'verb': w['verb'], 'filters': w.get('filters')}
            for w in unattributed_writes[:20]
        ],
        'cost_query_sql': COST_QUERY_SQL_TEMPLATE.format(batch_id=batch_id),
    }


def run_eval(
    sense_ids: list[int],
    language_id: int,
    *,
    pipeline_factory: Callable[[], object],
    renderer_factory: Callable[[], object],
    batch_id: str,
    out_dir: str,
    max_cost_usd: float | None = None,
    concurrency: int = 1,
    force: bool = False,
    capture_sink: list | None = None,
    lock: threading.Lock | None = None,
    real_client=None,
    cost_ledger: 'CostHookLedger | None' = None,
    extra_summary_fields: dict | None = None,
) -> dict:
    """Drive `process_one_sense` over `sense_ids`, stopping between senses
    (or between concurrency-sized chunks of senses) once `max_cost_usd` is
    met or exceeded. Writes `<out_dir>/<sense_id>.json` per sense and
    `<out_dir>/summary.json` at the end; returns the summary dict.

    `cost_ledger`: pass an already-constructed (but not necessarily started)
    `CostHookLedger` to reuse across multiple `run_eval` calls in one process,
    or to inspect it after the run. When omitted, one is created and
    subscribed/unsubscribed for the duration of this call only -- the
    subscription is process-global (see `CostHookLedger`), so this function
    always unsubscribes its own ledger in a `finally`, even on an exception.
    """
    capture_sink = capture_sink if capture_sink is not None else []
    lock = lock or threading.Lock()
    concurrency = max(1, int(concurrency))
    os.makedirs(out_dir, exist_ok=True)

    owns_ledger = cost_ledger is None
    cost_ledger = cost_ledger or CostHookLedger()
    cost_ledger.start()

    def _current_cost() -> float | None:
        db_total = query_batch_cost_from_db(real_client, batch_id)
        if db_total is not None:
            return db_total
        return _local_cost_total(capture_sink, lock) + cost_ledger.total_cost_usd()

    captures: list[dict] = []
    stopped_due_to_cost_cap = False
    run_t0 = time.monotonic()

    try:
        remaining = list(sense_ids)
        while remaining and not stopped_due_to_cost_cap:
            chunk, remaining = remaining[:concurrency], remaining[concurrency:]

            if concurrency == 1:
                results = [
                    process_one_sense(
                        pipeline_factory(), renderer_factory(), sid, language_id,
                        batch_id, capture_sink, lock, force,
                        cost_ledger=cost_ledger, max_cost_usd=max_cost_usd,
                    )
                    for sid in chunk
                ]
            else:
                with ThreadPoolExecutor(max_workers=len(chunk)) as ex:
                    futs = [
                        ex.submit(
                            process_one_sense, pipeline_factory(), renderer_factory(),
                            sid, language_id, batch_id, capture_sink, lock, force,
                            cost_ledger=cost_ledger, max_cost_usd=max_cost_usd,
                        )
                        for sid in chunk
                    ]
                    results = [f.result() for f in futs]

            for cap in results:
                captures.append(cap)
                _write_sense_json(out_dir, cap)
                logger.info(
                    "sense %s: status=%s exercises=%d wall_clock=%.1fs",
                    cap['sense_id'], cap['status'], len(cap['exercise_rows']),
                    cap['wall_clock_s'],
                )

            if max_cost_usd is not None:
                cost_so_far = _current_cost()
                if cost_so_far is not None and cost_so_far >= max_cost_usd:
                    stopped_due_to_cost_cap = True
                    logger.warning(
                        "Stopping: observed cost $%.4f >= --max-cost-usd $%.4f "
                        "after %d/%d senses.",
                        cost_so_far, max_cost_usd, len(captures), len(sense_ids),
                    )

        run_wall_clock_s = time.monotonic() - run_t0
        summary = build_summary(
            captures, capture_sink, run_wall_clock_s, stopped_due_to_cost_cap,
            _current_cost(), batch_id, len(sense_ids), cost_ledger=cost_ledger,
        )
        if extra_summary_fields:
            summary.update(extra_summary_fields)
    finally:
        if owns_ledger:
            cost_ledger.stop()

    with open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False, default=str)
    return summary


# ---------------------------------------------------------------------------
# Reference-set loading
# ---------------------------------------------------------------------------

def load_senses_from_reference(path: str, lang: str, use: str, limit: int | None) -> list[int]:
    if use not in ('reference_set', 'senses', 'top_up_candidates'):
        raise SystemExit("--use must be 'senses' or 'top_up_candidates'")
    key = 'reference_set' if use == 'senses' else 'top_up_candidates'
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    pool = data.get(key) or []
    pool = [row for row in pool if row.get('language') == lang]
    if limit:
        pool = pool[:limit]
    return [row['sense_id'] for row in pool]


def load_senses_from_run_dir(run_dir: str) -> list[int]:
    """Reuse the exact sense_id set a prior `run_eval` call processed.

    Reads the sense_id back off each `<run_dir>/<sense_id>.json` filename
    (written by `_write_sense_json`) rather than `summary.json`, since the
    per-sense files are the one artifact guaranteed to exist and be named
    this way for every completed sense regardless of how the run ended
    (a cost-cap stop still leaves every attempted sense's file in place).
    Order is ascending by sense_id for reproducibility, not run order (the
    original run's per-sense ordering isn't recoverable from the directory
    listing alone once senses ran concurrently).
    """
    if not os.path.isdir(run_dir):
        raise SystemExit(f"--senses-from directory not found: {run_dir!r}")
    sense_ids = []
    for name in os.listdir(run_dir):
        if not name.endswith('.json') or name == 'summary.json':
            continue
        stem = name[: -len('.json')]
        if stem.isdigit():
            sense_ids.append(int(stem))
    if not sense_ids:
        raise SystemExit(
            f"No <sense_id>.json files found in --senses-from directory: {run_dir!r}"
        )
    return sorted(sense_ids)


# ---------------------------------------------------------------------------
# Model overrides (in-memory, no prompt_templates write)
# ---------------------------------------------------------------------------

def parse_model_overrides(raw_overrides: list[str]) -> dict[tuple[str, int | None], str]:
    """Parse repeated `--model-override task_name[:lang]=model_slug` values.

    A `lang` suffix scopes the override to one `language_id`; omitting it
    applies to every language that calls this `task_name` (an explicit
    `task_name:lang=` entry always wins over a language-less one for that
    same task_name, applied in `apply_model_overrides`).
    """
    overrides: dict[tuple[str, int | None], str] = {}
    for raw in raw_overrides or []:
        if '=' not in raw:
            raise SystemExit(
                f"--model-override must be 'task_name[:lang]=model_slug', got: {raw!r}"
            )
        key_part, model_slug = raw.split('=', 1)
        key_part, model_slug = key_part.strip(), model_slug.strip()
        if not key_part or not model_slug:
            raise SystemExit(
                f"--model-override must be 'task_name[:lang]=model_slug', got: {raw!r}"
            )
        if ':' in key_part:
            task_name, lang_code = key_part.split(':', 1)
            if lang_code not in LANG_CODE_TO_ID:
                raise SystemExit(
                    f"--model-override language {lang_code!r} must be one of "
                    f"{sorted(LANG_CODE_TO_ID)}"
                )
            language_id: int | None = LANG_CODE_TO_ID[lang_code]
        else:
            task_name, language_id = key_part, None
        overrides[(task_name, language_id)] = model_slug
    return overrides


def apply_model_overrides(overrides: dict[tuple[str, int | None], str]) -> list[dict]:
    """Monkeypatch `services.prompt_service.get_template_config` in-memory
    for the lifetime of this process, so every generator's `from
    services.prompt_service import get_template_config` (bound at each
    generator module's own FIRST import) picks up the wrapped version instead
    of the original.

    This works because every `vocabulary_ladder` generator module is imported
    lazily, inside `pipeline_factory()`/`renderer_factory()`, which only run
    once `run_eval` starts processing senses -- well after this function is
    called from `main()`. No row in `prompt_templates` is read differently or
    written to; only the `model` key this process sees in the returned config
    dict changes, for exactly the task_name(/language) pairs requested.
    Returns the applied overrides as plain dicts, for `summary.json`.
    """
    if not overrides:
        return []

    import services.prompt_service as prompt_service_module
    original_get_template_config = prompt_service_module.get_template_config

    def _overridden_get_template_config(db, task_name, language_id):
        cfg = original_get_template_config(db, task_name, language_id)
        model = overrides.get((task_name, language_id))
        if model is None:
            model = overrides.get((task_name, None))
        if model:
            cfg = dict(cfg)
            cfg['model'] = model
        return cfg

    prompt_service_module.get_template_config = _overridden_get_template_config

    lang_code_by_id = {v: k for k, v in LANG_CODE_TO_ID.items()}
    return [
        {
            'task_name': task_name,
            'language': lang_code_by_id.get(language_id) if language_id else None,
            'model': model,
        }
        for (task_name, language_id), model in overrides.items()
    ]


# ---------------------------------------------------------------------------
# --prompt-override-file: serve whole prompt_templates rows in-memory,
# without a DB write. Unlike --model-override (which only swaps the `model`
# key of an EXISTING, already-active row), this replaces the row entirely --
# built for a task_name/language that has NO active (or no) row in the real
# `prompt_templates` table at all, e.g. a draft migration like
# `migrations/exercise_gen_bundle_prompts_draft.sql` that is deliberately
# NOT applied. Two source formats:
#
#   * A local JSON file: a list of objects, each with `task_name`,
#     `language` (a 'zh'/'en'/'ja' code) or `language_id` (int), `template`
#     (or `template_text`), `model`, and optionally `provider` (default
#     'openrouter') and `version` (default 1).
#   * A `.sql` migration file (or anything not ending `.json`): every
#     `INSERT INTO prompt_templates (...) VALUES (...)` statement in the
#     file is extracted directly -- see `parse_prompt_templates_sql` -- so a
#     draft migration can be pointed at as-is, with no hand-copied JSON to
#     keep in sync.
# ---------------------------------------------------------------------------

def _strip_sql_line_comments(text: str) -> str:
    """Remove `-- ...` line comments, leaving string literals (which may
    themselves contain `'`, and are NOT terminated by `--`) untouched.
    """
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "'":
                if i + 1 < n and text[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                in_str = False
            i += 1
            continue
        if c == "'":
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == '-' and i + 1 < n and text[i + 1] == '-':
            j = text.find('\n', i)
            i = j if j != -1 else n
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def _find_matching_paren(text: str, open_idx: int) -> int:
    """Index of the `)` matching `text[open_idx] == '('`, skipping any `(`/`)`
    that occur inside a `'...'` string literal.
    """
    depth = 0
    i, n = open_idx, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            if c == "'":
                if i + 1 < n and text[i + 1] == "'":
                    i += 2
                    continue
                in_str = False
            i += 1
            continue
        if c == "'":
            in_str = True
            i += 1
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError('Unbalanced parentheses in SQL text')


def _split_top_level_sql(segment: str) -> list[str]:
    """Split a SQL tuple's inner text on top-level commas only -- commas
    inside a `'...'` string literal or a nested `(...)` don't split.
    """
    parts, current = [], []
    depth = 0
    in_str = False
    i, n = 0, len(segment)
    while i < n:
        c = segment[i]
        if in_str:
            current.append(c)
            if c == "'":
                if i + 1 < n and segment[i + 1] == "'":
                    current.append(segment[i + 1])
                    i += 2
                    continue
                in_str = False
            i += 1
            continue
        if c == "'":
            in_str = True
            current.append(c)
            i += 1
            continue
        if c == '(':
            depth += 1
            current.append(c)
            i += 1
            continue
        if c == ')':
            depth -= 1
            current.append(c)
            i += 1
            continue
        if c == ',' and depth == 0:
            parts.append(''.join(current))
            current = []
            i += 1
            continue
        current.append(c)
        i += 1
    if current:
        parts.append(''.join(current))
    return [p.strip() for p in parts]


def _consume_sql_string_literal(s: str, i: int) -> tuple[str, int]:
    """Decode one `'...'` or `E'...'` literal starting at `s[i]`, honoring
    `''`-doubled quote escapes and (for `E'...'`) `\\n`/`\\t`/`\\r`/`\\\\`/`\\'`
    backslash escapes. Returns (decoded_text, index_after_closing_quote).
    """
    is_escape = s[i] in ('E', 'e')
    if is_escape:
        i += 1
    if s[i] != "'":
        raise ValueError(f'Expected a string literal at position {i}: {s[i:i + 20]!r}')
    i += 1
    n = len(s)
    buf = []
    escape_map = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', "'": "'"}
    while i < n:
        c = s[i]
        if c == "'":
            if i + 1 < n and s[i + 1] == "'":
                buf.append("'")
                i += 2
                continue
            return ''.join(buf), i + 1
        if c == '\\' and is_escape and i + 1 < n and s[i + 1] in escape_map:
            buf.append(escape_map[s[i + 1]])
            i += 2
            continue
        buf.append(c)
        i += 1
    raise ValueError('Unterminated string literal')


def _parse_sql_literal(raw: str):
    """One column value from a VALUES tuple: NULL / true / false / a number /
    one or more adjacent `'...'`/`E'...'` literals (Postgres concatenates
    string literals separated only by whitespace -- exactly how this repo's
    multi-line `E'...'\\n E'...'` template_text values are written).
    """
    raw = raw.strip()
    if not raw or raw.upper() == 'NULL':
        return None
    if raw.lower() in ('true', 'false'):
        return raw.lower() == 'true'
    if raw[:1] == "'" or raw[:1] in ('E', 'e'):
        i, n, parts = 0, len(raw), []
        while i < n:
            while i < n and raw[i].isspace():
                i += 1
            if i >= n:
                break
            text, i = _consume_sql_string_literal(raw, i)
            parts.append(text)
        return ''.join(parts)
    try:
        return int(raw)
    except ValueError:
        return float(raw)


def parse_prompt_templates_sql(text: str) -> list[dict]:
    """Extract every `INSERT INTO prompt_templates (...) VALUES (...)` row
    from a migration file's SQL text -- no DB connection, no `psycopg2`. This
    is deliberately narrow (single-row VALUES tuples, the handful of literal
    kinds `prompt_templates` migrations actually use), not a general SQL
    parser; it exists so `--prompt-override-file` can point straight at a
    draft migration (e.g. `migrations/exercise_gen_bundle_prompts_draft.sql`)
    instead of requiring a hand-copied JSON that can drift from it.
    """
    stripped = _strip_sql_line_comments(text)
    rows: list[dict] = []
    for m in re.finditer(r'INSERT\s+INTO\s+prompt_templates\s*\(', stripped, re.IGNORECASE):
        col_open = m.end() - 1
        col_close = _find_matching_paren(stripped, col_open)
        columns = [c.strip() for c in stripped[col_open + 1:col_close].split(',')]

        tail = stripped[col_close + 1:]
        values_kw = re.search(r'VALUES\s*\(', tail, re.IGNORECASE)
        if not values_kw:
            raise ValueError('INSERT INTO prompt_templates(...) has no VALUES(...)')
        val_open = col_close + 1 + values_kw.end() - 1
        val_close = _find_matching_paren(stripped, val_open)
        raw_values = _split_top_level_sql(stripped[val_open + 1:val_close])
        if len(raw_values) != len(columns):
            raise ValueError(
                f'prompt_templates INSERT has {len(columns)} columns but '
                f'{len(raw_values)} values: {columns!r}'
            )
        rows.append({col: _parse_sql_literal(val) for col, val in zip(columns, raw_values)})
    return rows


def parse_prompt_override_file(path: str) -> dict[tuple[str, int], dict]:
    """Load prompt-template rows to serve in-memory for this run only, keyed
    by (task_name, language_id). Source format is chosen by extension: a
    `.json` file is a list of override objects; anything else is parsed as
    SQL via `parse_prompt_templates_sql` (so the draft migration file itself
    can be passed straight through).
    """
    with open(path, encoding='utf-8') as fh:
        text = fh.read()

    if path.lower().endswith('.json'):
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise SystemExit(
                f'--prompt-override-file {path}: expected a JSON list of override objects'
            )
    else:
        rows = parse_prompt_templates_sql(text)

    overrides: dict[tuple[str, int], dict] = {}
    for row in rows:
        task_name = row.get('task_name')
        language_id = row.get('language_id')
        if language_id is None and row.get('language'):
            lang = row['language']
            language_id = LANG_CODE_TO_ID.get(lang) if isinstance(lang, str) else lang
        template = row.get('template') or row.get('template_text')
        model = row.get('model')
        if not task_name or language_id is None or not template or not model:
            raise SystemExit(
                f'--prompt-override-file {path}: row missing task_name/'
                f'language(_id)/template(_text)/model -- got keys {sorted(row.keys())!r}'
            )
        overrides[(task_name, int(language_id))] = {
            'template': template,
            'model': model,
            'provider': row.get('provider') or 'openrouter',
            'version': row.get('version', 1),
        }
    return overrides


def apply_prompt_overrides(overrides: dict[tuple[str, int], dict]) -> list[dict]:
    """Monkeypatch `services.prompt_service.get_template_config` so a
    matched (task_name, language_id) returns the override's full config
    (template/model/provider/version) WITHOUT ever querying
    `prompt_templates` -- the DB is never touched for that key, active row or
    not. Anything not in `overrides` falls through to whatever
    `get_template_config` currently is (the real DB lookup, or an
    already-applied `--model-override` wrapper -- this function is meant to
    be called AFTER `apply_model_overrides`, so a full prompt override always
    wins over a same-key model-only override).

    Same import-timing argument as `apply_model_overrides`: every
    `vocabulary_ladder` bundle module (`bundle/generator.py`,
    `bundle/judge.py`) does `from services.prompt_service import
    get_template_config` at ITS OWN first import, which -- per
    `asset_pipeline.py`/`exercise_renderer.py`'s top-level imports of those
    bundle modules, and this harness's `pipeline_factory()`/
    `renderer_factory()` lazily importing asset_pipeline/exercise_renderer
    themselves -- only happens once `run_eval` starts processing senses,
    well after `main()` calls this function. So patching the module-level
    attribute here is picked up correctly.
    """
    if not overrides:
        return []

    import services.prompt_service as prompt_service_module
    original_get_template_config = prompt_service_module.get_template_config

    def _overridden_get_template_config(db, task_name, language_id):
        override = overrides.get((task_name, language_id))
        if override is None:
            return original_get_template_config(db, task_name, language_id)
        return {
            'template': override['template'],
            'model': override['model'],
            'provider': override['provider'],
            'version': override['version'],
        }

    prompt_service_module.get_template_config = _overridden_get_template_config

    lang_code_by_id = {v: k for k, v in LANG_CODE_TO_ID.items()}
    return [
        {
            'task_name': task_name,
            'language': lang_code_by_id.get(language_id),
            'language_id': language_id,
            'version': o['version'],
            'model': o['model'],
            'provider': o['provider'],
        }
        for (task_name, language_id), o in overrides.items()
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--senses', help='Comma-separated sense_id list')
    parser.add_argument('--reference', help='Path to a reference-set JSON file')
    parser.add_argument('--senses-from',
                         help='Reuse the exact sense_id set from a prior run '
                              'directory (its <sense_id>.json files) instead '
                              'of --senses/--reference. --limit still applies '
                              'to the loaded list.')
    parser.add_argument('--model-override', action='append', default=[],
                         metavar='task_name[:lang]=model_slug',
                         help='Repeatable. Swap the model used for this '
                              'task_name (optionally scoped to one of zh/en/ja) '
                              'for THIS run only -- an in-memory override, no '
                              'prompt_templates write. Recorded in summary.json '
                              "under 'model_overrides_applied'.")
    parser.add_argument('--prompt-override-file',
                         help='Serve prompt_templates rows from this file in-memory '
                              'for THIS run only, ahead of the real DB -- no '
                              'prompt_templates write, and works for a task_name/'
                              'language that has no active (or no) row in the DB '
                              'at all. A .json file is a list of override objects '
                              '(task_name, language|language_id, template|'
                              'template_text, model, provider?, version?); any '
                              'other extension is parsed as SQL and every '
                              '`INSERT INTO prompt_templates(...)` row in it is '
                              'used directly (e.g. point this at a draft migration '
                              'such as migrations/exercise_gen_bundle_prompts_draft.sql). '
                              'A matched (task_name, language) always wins over the '
                              'same key in --model-override. Recorded in summary.json '
                              "under 'prompt_overrides_applied'.")
    parser.add_argument('--lang', choices=sorted(LANG_CODE_TO_ID), help='zh | ja | en')
    parser.add_argument('--use', choices=('top_up_candidates', 'senses'),
                         default='top_up_candidates',
                         help="Which pool of --reference to draw from. "
                              "'senses' rows already have live valid word_assets "
                              "(from the benchmark model) and will be skipped "
                              "by the real pipeline unless --force is also "
                              "passed; 'top_up_candidates' rows have none yet, "
                              "which is the natural pool for a fresh cost run.")
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--out', help='Output directory (default: data/eval/runs/<label>/)')
    parser.add_argument('--label', help='Short run name, used to build --out when omitted')
    parser.add_argument('--max-cost-usd', type=float, default=None,
                         help='Stop starting new senses once cumulative llm_calls '
                              'cost for this run reaches this many dollars')
    parser.add_argument('--concurrency', type=int, default=1)
    parser.add_argument('--force', action='store_true',
                         help='Pass force=True through to _generate_for_sense_impl '
                              '(regenerate even if valid assets already exist)')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    if args.senses_from:
        if not args.lang:
            raise SystemExit('--lang is required with --senses-from (used to resolve language_id)')
        sense_ids = load_senses_from_run_dir(args.senses_from)
        if args.limit:
            sense_ids = sense_ids[:args.limit]
    elif args.senses:
        sense_ids = [int(s) for s in args.senses.split(',') if s.strip()]
        if not args.lang:
            raise SystemExit('--lang is required (used to resolve language_id)')
    elif args.reference:
        if not args.lang:
            raise SystemExit('--lang is required with --reference')
        sense_ids = load_senses_from_reference(args.reference, args.lang, args.use, args.limit)
        if not sense_ids:
            raise SystemExit(
                f"No {args.use} rows found for lang={args.lang} in {args.reference}"
            )
    else:
        raise SystemExit(
            'Pass --senses SID,SID,... or --reference PATH (with --lang) or '
            '--senses-from RUN_DIR (with --lang)'
        )

    model_overrides = parse_model_overrides(args.model_override)
    applied_overrides = apply_model_overrides(model_overrides)

    prompt_overrides = (
        parse_prompt_override_file(args.prompt_override_file)
        if args.prompt_override_file else {}
    )
    # Applied AFTER apply_model_overrides so a full prompt override always
    # wins over a same-key --model-override (see apply_prompt_overrides'
    # docstring).
    applied_prompt_overrides = apply_prompt_overrides(prompt_overrides)

    language_id = LANG_CODE_TO_ID[args.lang]
    batch_id = str(uuid.uuid4())
    out_dir = args.out or os.path.join('data', 'eval', 'runs', args.label or batch_id)

    from dotenv import load_dotenv
    load_dotenv()
    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    real_client = get_supabase_admin()

    capture_sink: list = []
    lock = threading.Lock()

    def pipeline_factory():
        from services.vocabulary_ladder.asset_pipeline import VocabAssetPipeline
        return VocabAssetPipeline(db=InterceptingClient(real_client, capture_sink, lock))

    def renderer_factory():
        from services.vocabulary_ladder.exercise_renderer import LadderExerciseRenderer
        intercepting = InterceptingClient(real_client, capture_sink, lock)
        # ShadowReadClient: see the module note above ShadowWordAssetsTable --
        # without it, build_rows() never finds a prompt1_core for a
        # top_up_candidates sense (no pre-existing word_assets row), since
        # this harness blocks the actual write.
        return LadderExerciseRenderer(
            db=ShadowReadClient(intercepting, capture_sink, lock),
        )

    logger.info(
        "Starting eval run batch_id=%s senses=%d lang=%s out=%s max_cost_usd=%s "
        "concurrency=%d force=%s model_overrides=%s prompt_overrides=%s senses_from=%s",
        batch_id, len(sense_ids), args.lang, out_dir, args.max_cost_usd,
        args.concurrency, args.force, applied_overrides, applied_prompt_overrides,
        args.senses_from,
    )

    summary = run_eval(
        sense_ids, language_id,
        pipeline_factory=pipeline_factory, renderer_factory=renderer_factory,
        batch_id=batch_id, out_dir=out_dir, max_cost_usd=args.max_cost_usd,
        concurrency=args.concurrency, force=args.force,
        capture_sink=capture_sink, lock=lock, real_client=real_client,
        extra_summary_fields={
            'model_overrides_applied': applied_overrides,
            'prompt_overrides_applied': applied_prompt_overrides,
            'prompt_override_file': args.prompt_override_file,
            'senses_from': args.senses_from,
        },
    )

    logger.info("Done. attempted=%s/%s status_counts=%s cost_usd=%s -> %s",
                summary['attempted_senses'], summary['requested_senses'],
                summary['status_counts'], summary['cost_usd_total_observed'], out_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
