#!/usr/bin/env python
"""Re-tier every active test with jev (TASK-820, ADR-029).

Two stages, so nothing is written to ``tests`` until every test has an answer:

  python scripts/retier_tests_with_jev.py            # 1. classify (read-only)
  python scripts/retier_tests_with_jev.py --apply    # 2. apply saved results

Stage 1 classifies every active test, writes
``data/eval/jev_retier_<date>/results.json`` (old tier, jev tier, score,
confidence, probabilities per test) and touches nothing in ``tests``. If ANY
test fails jev (after the client's retries) it exits non-zero and saves
nothing: there is no partial or guessed re-tier. ``--limit N`` smoke-tests on
the first N tests and saves nothing.

Stage 2 sends results.json to the ``apply_jev_retier`` RPC
(migrations/task820_apply_jev_retier.sql), one atomic call that raises unless
every row updates, then verifies the counts. Take the backup first
(migrations/task819_jev_tier_assignment.sql creates and fills
``tests_tier_backup_20260926``; the same file documents the reversing UPDATE).

``difficulty`` is rewritten only where the tier changed, to the bottom of the
new tier's band (what test generation writes). ELO is deliberately untouched —
see ADR-029.

Load order matters: ``OPENROUTER_API_KEY`` is frozen into services.llm_service
at import, so ``load_dotenv()`` runs before any ``services`` import.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO, '.env'))

from services.supabase_factory import (  # noqa: E402
    SupabaseFactory, get_supabase_admin,
)
from services import tier_classifier  # noqa: E402
from services.jev_client import JevError  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('retier_tests_with_jev')

LANG_CODES = {1: 'zh', 2: 'en', 3: 'ja'}
results_path = os.path.join(
    REPO, 'data', 'eval', f'jev_retier_{date.today():%Y-%m-%d}', 'results.json')
BUDGET_STOP_USD = 0.25  # the task said "stop and ask" at $1; stop well before


def fetch_active_tests(db, limit=None) -> list:
    rows, start = [], 0
    while True:
        page = (
            db.table('tests')
            .select('id, language_id, transcript, target_age_tier, difficulty')
            .eq('is_active', True).order('id')
            .range(start, start + 199).execute()
        ).data or []
        rows.extend(page)
        if len(page) < 200:
            break
        start += 200
    return rows[:limit] if limit else rows


def classify(test: dict) -> dict:
    a = tier_classifier.classify_passage(
        test['transcript'], LANG_CODES[test['language_id']],
    )
    return {
        'id': test['id'],
        'language': LANG_CODES[test['language_id']],
        'old_tier': test['target_age_tier'],
        'old_difficulty': test['difficulty'],
        'new_tier': a.tier,
        'new_difficulty': tier_classifier.difficulty_for_tier(a.tier),
        'score': a.score,
        'confidence': a.confidence,
        'probabilities': {f'T{t}': p for t, p in a.probabilities.items()},
        'model': a.model,
        'calibration': a.calibration,
        'cost_usd': a.cost_usd,
        'chars': len(test['transcript']),
    }


def summarise(results: list) -> None:
    by_lang = defaultdict(list)
    for r in results:
        by_lang[r['language']].append(r)
    for lang, rs in sorted(by_lang.items()):
        moved = [r for r in rs if r['new_tier'] != r['old_tier']]
        print(f'\n== {lang}: {len(rs)} tests, {len(moved)} change tier '
              f'(mean |delta| {sum(abs(r["new_tier"] - (r["old_tier"] or 0)) for r in rs) / len(rs):.2f}, '
              f'mean signed {sum(r["new_tier"] - (r["old_tier"] or 0) for r in rs) / len(rs):+.2f})')
        matrix = Counter((r['old_tier'], r['new_tier']) for r in rs)
        print('   old\\new  ' + ' '.join(f'T{t}' for t in range(1, 7)))
        for old in sorted({r['old_tier'] for r in rs}, key=lambda x: x or 0):
            print(f'   T{old}      ' + ' '.join(f'{matrix.get((old, n), 0):>2}' for n in range(1, 7)))
        conf = [r['confidence'] for r in rs if r['confidence'] is not None]
        if conf:
            print(f'   confidence: mean {sum(conf) / len(conf):.2f}, min {min(conf):.2f}')


def verify_cost_logging(db, since_iso: str, expected_calls: int) -> int:
    """llm_calls.cost_usd has silently gone NULL before — check it landed."""
    rows = (
        db.table('llm_calls').select('cost_usd, task_name')
        .eq('task_name', tier_classifier.PASSAGE_TASK)
        .gte('created_at', since_iso).limit(2000).execute()
    ).data or []
    nulls = sum(1 for r in rows if r['cost_usd'] is None)
    total = sum(float(r['cost_usd']) for r in rows if r['cost_usd'] is not None)
    print(f'\nllm_calls: {len(rows)} rows for {tier_classifier.PASSAGE_TASK} '
          f'(expected {expected_calls}), cost_usd NULL in {nulls}, '
          f'sum ${total:.6f}')
    if nulls:
        print('ERROR: cost_usd is NULL on logged rows — the cost pipeline is broken')
        return 1
    if len(rows) != expected_calls:
        print('WARNING: some llm_calls rows were not written (observability is '
              'best-effort; see the "llm_calls logging failed" warnings above)')
    return 0


def apply_saved(db) -> int:
    with open(results_path, encoding='utf-8') as fh:
        results = json.load(fh)
    print(f'applying {len(results)} results from {results_path}')
    updated = db.rpc('apply_jev_retier', {'p_rows': results}).execute().data
    print(f'apply_jev_retier updated {updated} rows')
    if updated != len(results):
        print('ERROR: row count mismatch')
        return 1

    # Verify against the table, not the RPC's own answer.
    ids = [r['id'] for r in results]
    rows = []
    for i in range(0, len(ids), 100):
        rows += (db.table('tests')
                 .select('id, target_age_tier, difficulty, age_tier_score, age_tier_model')
                 .in_('id', ids[i:i + 100]).execute()).data
    want = {r['id']: r for r in results}
    bad = [
        r['id'] for r in rows
        if r['target_age_tier'] != want[r['id']]['new_tier']
        or r['age_tier_score'] is None or not r['age_tier_model']
    ]
    print(f'verified {len(rows)}/{len(results)} rows read back, {len(bad)} mismatched')
    return 0 if len(rows) == len(results) and not bad else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--limit', type=int, help='classify only the first N tests (smoke test)')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--apply', action='store_true',
                        help='apply the saved results.json to tests (atomic RPC)')
    args = parser.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.apply:
        return apply_saved(db)

    tests = fetch_active_tests(db, args.limit)
    logger.info('classifying %d active tests', len(tests))
    started = time.time()
    since_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(started - 5))

    results, failures, spent = [], [], 0.0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(classify, t): t for t in tests}
        for fut in as_completed(futures):
            test = futures[fut]
            try:
                r = fut.result()
            except (JevError, ValueError) as exc:
                failures.append((test['id'], str(exc)))
                logger.error('FAILED %s: %s', test['id'], exc)
                continue
            results.append(r)
            spent += r['cost_usd'] or 0.0
            if spent > BUDGET_STOP_USD:
                for f in futures:
                    f.cancel()
                raise SystemExit(f'spend ${spent:.4f} passed the ${BUDGET_STOP_USD} guard')

    if failures:
        print(f'\n{len(failures)} test(s) failed; nothing emitted.')
        for tid, msg in failures[:10]:
            print(f'  {tid}: {msg}')
        return 1

    results.sort(key=lambda r: r['id'])
    if not args.limit:
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        with open(results_path, 'w', encoding='utf-8') as fh:
            json.dump(results, fh, ensure_ascii=False, indent=1)

    summarise(results)
    print(f'\n{len(results)} classified in {time.time() - started:.1f}s, '
          f'cost ${spent:.6f} (mean ${spent / max(len(results), 1):.7f}/call)')

    if args.limit:
        print('\n--limit run: nothing saved.')
    else:
        print(f'results -> {results_path}')
    return verify_cost_logging(db, since_iso, len(results))


if __name__ == '__main__':
    raise SystemExit(main())
