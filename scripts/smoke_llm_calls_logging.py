"""One-call smoke test for the llm_calls cost-instrumentation columns.

Makes exactly ONE real OpenRouter call (the cheapest configured model,
max_tokens=20 — this costs a fraction of a cent) through the normal
``call_llm()`` path, then reads back the row it produced and prints every
column, so the user can eyeball that ``cost_usd``, ``latency_ms``,
``prompt_tokens``/``completion_tokens``/``cached_tokens``/``reasoning_tokens``,
``sense_id``, ``call_role`` and ``generation_batch_id`` all actually landed.

Run this AFTER applying migrations/llm_calls_cost_instrumentation.sql — before
that, the new columns don't exist yet and the printed row will simply omit
them (the script detects this and says so; it does not fail).

Usage::

    python scripts/smoke_llm_calls_logging.py
    python scripts/smoke_llm_calls_logging.py --model google/gemini-3.5-flash-lite

This script is NOT run as part of the test suite — it spends real money
(a fraction of a cent) and requires OPENROUTER_API_KEY / Supabase credentials
to be configured. Run it by hand.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.llm_service import LLM_DEFAULT_MODEL, call_llm  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

# Columns this smoke test exists to verify actually get populated. Split into
# "always populated" (already shipped, well before Phase 0) and "pending
# migration apply" (this effort's additions) so the report is honest about
# which half of the instrumentation it's actually proving.
_ALWAYS_POPULATED = (
    'pipeline', 'task_name', 'model', 'latency_ms', 'cost_usd',
    'language_code', 'created_at',
)
_PENDING_MIGRATION_COLUMNS = (
    'prompt_tokens', 'completion_tokens', 'cached_tokens', 'reasoning_tokens',
    'sense_id', 'call_role', 'generation_batch_id',
)

# A sentinel sense_id that can never collide with a real dim_word_senses row
# (ids are positive), so this smoke row is unambiguously identifiable as a
# smoke test rather than real generation history.
_SMOKE_SENSE_ID = -1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--model', default=LLM_DEFAULT_MODEL,
        help=f'Model slug to call (default: the system-wide cheap default, '
             f'{LLM_DEFAULT_MODEL!r})',
    )
    args = parser.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        print('FATAL: no Supabase service-role client available — set '
              'SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY.')
        return 1

    smoke_batch_id = str(uuid4())
    task_name = 'llm_calls_logging_smoke'

    print(f'Calling {args.model!r} (max_tokens=20, pipeline=diag, '
          f'task_name={task_name!r}) ...')
    t0 = time.time()
    try:
        result = call_llm(
            'Reply with the single word: pong',
            model=args.model,
            provider='openrouter',
            response_format='text',
            max_tokens=20,
            temperature=0.0,
            pipeline='diag',
            task_name=task_name,
            call_role='primary',
            sense_id=_SMOKE_SENSE_ID,
            generation_batch_id=smoke_batch_id,
        )
    except Exception as exc:
        print(f'FATAL: call_llm raised: {type(exc).__name__}: {exc}')
        return 1
    elapsed = time.time() - t0
    print(f'Response ({elapsed:.2f}s wall): {result!r}\n')

    # _log_llm_call writes asynchronously-in-spirit (it's a synchronous insert
    # inside call_llm, but give Supabase a beat before reading it back to be
    # safe against any read-replica lag).
    time.sleep(0.5)

    try:
        resp = (
            db.table('llm_calls')
            .select('*')
            .eq('task_name', task_name)
            .eq('generation_batch_id', smoke_batch_id)
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:
        # generation_batch_id doesn't exist yet (pre-migration) — PostgREST
        # rejects filtering on an unknown column. Fall back to a lookup that
        # doesn't touch it, and report the migration as not-yet-applied.
        print(f'(Filtering on generation_batch_id failed — likely '
              f'pre-migration: {exc})\n'
              f'Falling back to a lookup by task_name + pipeline only.')
        resp = (
            db.table('llm_calls')
            .select('*')
            .eq('task_name', task_name)
            .eq('pipeline', 'diag')
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []

    if not rows:
        print('FATAL: call_llm returned successfully but no llm_calls row was '
              'found — logging is broken (check the WARNING lines above/in '
              'the app log for "llm_calls logging failed").')
        return 1

    row = rows[0]
    print('llm_calls row:')
    print(json.dumps(row, indent=2, default=str, ensure_ascii=False))

    print('\n--- Verification ---')
    ok = True
    for col in _ALWAYS_POPULATED:
        value = row.get(col)
        status = 'OK' if value not in (None, '') else 'MISSING'
        if status == 'MISSING':
            ok = False
        print(f'  {col:22s} {status:8s} {value!r}')

    missing_migration_columns = [c for c in _PENDING_MIGRATION_COLUMNS if c not in row]
    if missing_migration_columns:
        print(f'\n  Migration NOT applied yet — these columns are absent from '
              f'the row entirely: {missing_migration_columns}')
        print('  Apply migrations/llm_calls_cost_instrumentation.sql, then '
              're-run this script to verify them.')
    else:
        print()
        for col in _PENDING_MIGRATION_COLUMNS:
            value = row.get(col)
            # cached_tokens/reasoning_tokens can legitimately be NULL (not
            # every model reports them) — only sense_id/call_role/
            # generation_batch_id/prompt_tokens/completion_tokens are
            # expected to always be set by this call.
            expect_value = col not in ('cached_tokens', 'reasoning_tokens')
            status = 'OK' if (value is not None or not expect_value) else 'MISSING'
            if status == 'MISSING':
                ok = False
            print(f'  {col:22s} {status:8s} {value!r}')

        if row.get('sense_id') != _SMOKE_SENSE_ID:
            print(f'  WARNING: sense_id={row.get("sense_id")!r}, expected '
                  f'{_SMOKE_SENSE_ID!r}')
            ok = False
        if row.get('call_role') != 'primary':
            print(f'  WARNING: call_role={row.get("call_role")!r}, expected '
                  f"'primary'")
            ok = False
        if row.get('generation_batch_id') != smoke_batch_id:
            print(f'  WARNING: generation_batch_id={row.get("generation_batch_id")!r}, '
                  f'expected {smoke_batch_id!r}')
            ok = False

    print(f'\n{"PASS" if ok else "FAIL"}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
