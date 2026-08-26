#!/usr/bin/env python3
"""Build word_assets + ladder exercises for senses already referenced by
*existing* tests, without generating any new tests.

This is a narrower entry point than run_content_build.py: that script's
'select' phase only ranks senses referenced by tests it just generated in
the same run ('tests' phase), so it can't be pointed at content that already
exists. This script reuses the same per-sense pipeline (VocabAssetPipeline
-> LadderExerciseRenderer, via run_content_build._ladder_one) but sources
its candidate senses from every existing test for the language instead of
generating anything new.

Ranking matches run_content_build's phase_select: by how many existing
tests reference the sense (a sense carried by many tests earns assets
first), restricted to senses with no word_assets row yet.

Checkpointed like run_content_build's ladder phase — state is rewritten
after every sense, so --resume never redoes finished work and a crash
mid-batch loses at most one in-flight sense.

Usage::

    # see the pool and ranking, no writes, no LLM calls
    python scripts/run_ladder_from_existing.py --language ja --max-senses 30 --dry-run

    # run it
    python scripts/run_ladder_from_existing.py --language ja --max-senses 30 --workers 3 --yes

    # pick up after an interruption
    python scripts/run_ladder_from_existing.py --resume ja-existing-20260826-...  --yes
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

import run_content_build as rcb  # noqa: E402 — sibling script, reused for its helpers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(ROOT, 'data', 'content_builds')


def state_path(run_id: str) -> str:
    return os.path.join(STATE_DIR, f'{run_id}.json')


def save_state(state: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = state_path(state['run_id']) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, state_path(state['run_id']))


def load_state(run_id: str) -> dict:
    with open(state_path(run_id), encoding='utf-8') as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--language', choices=sorted(rcb.LANG_ID), help='zh | en | ja')
    ap.add_argument('--max-senses', type=int, default=30)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--dry-run', action='store_true',
                     help='print the selected senses, make no LLM calls / writes')
    ap.add_argument('--resume', metavar='RUN_ID')
    ap.add_argument('--yes', action='store_true')
    args = ap.parse_args()

    if not args.resume and not args.language:
        ap.error('--language is required unless --resume is given')

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.resume:
        state = load_state(args.resume)
        print(f'Resuming {state["run_id"]} '
              f'({len(state["done"])} done, {len(state["failed"])} failed)')
    else:
        lang = args.language
        lid = rcb.LANG_ID[lang]
        run_id = f'{lang}-existing-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}'
        state = {
            'run_id': run_id, 'language': lang, 'language_id': lid,
            'max_senses': args.max_senses, 'workers': args.workers,
            'selected': [], 'done': {}, 'failed': {},
        }

        test_ids = [r['id'] for r in (
            db.table('tests').select('id').eq('language_id', lid)
              .eq('is_active', True).limit(2000).execute().data or []
        )]
        counts = rcb.sense_ids_for_tests(db, test_ids)
        free = set(rcb.senses_without_assets(db, [s for s, _ in counts.most_common()]))
        ranked = [s for s, _ in counts.most_common() if s in free]
        state['selected'] = ranked[:args.max_senses]
        state['candidates'] = len(ranked)
        print(f'{len(counts)} distinct senses across {len(test_ids)} existing '
              f'{lang} tests; {len(ranked)} lack assets; '
              f'taking top {len(state["selected"])} by test frequency '
              f'(cap {args.max_senses})')
        save_state(state)
        print(f'New run {run_id}')

    todo = [s for s in state['selected'] if str(s) not in state['done']]
    if args.dry_run:
        print(f'DRY RUN — would build {len(todo)} senses: {todo}')
        return 0

    if not todo:
        print('nothing to do')
        return 0

    per_sense_est = 330  # 5.5 min, matches TASK-515 baseline until we have a canary
    workers = state['workers']
    if not args.yes:
        eta = len(todo) * per_sense_est / max(workers, 1)
        print(f'\nAbout to build {len(todo)} senses with {workers} workers '
              f'(ETA ~{rcb.fmt_hms(eta)}, ~${len(todo) * 0.024:.2f} at the '
              f'~$0.024/sense baseline)')
        if input('Proceed? [y/N] ').strip().lower() != 'y':
            print('Aborted.')
            return 1

    from services.exercise_generation.judges.base import (
        batch_mode, BatchModeThreadPoolExecutor,
    )
    from concurrent.futures import as_completed

    since = datetime.now(timezone.utc).isoformat()
    t0 = time.time()
    lid = state['language_id']
    completed = 0

    with batch_mode():
        with BatchModeThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(rcb._ladder_one, db, sid, lid): sid for sid in todo}
            for fut in as_completed(futures):
                sid = futures[fut]
                completed += 1
                try:
                    out = fut.result()
                except Exception as exc:
                    state['failed'][str(sid)] = {'error': str(exc)}
                    print(f'  [{completed}/{len(todo)}] sense {sid}: EXCEPTION {exc}')
                else:
                    if out['status'] == 'failed':
                        state['failed'][str(sid)] = out
                    else:
                        state['done'][str(sid)] = out
                    print(f'  [{completed}/{len(todo)}] sense {sid}: '
                          f'status={out["status"]} exercises={out["exercises"]} '
                          f'({rcb.fmt_hms(out["seconds"])})')
                save_state(state)

    calls, usd, nulls = rcb.spend_since(db, since)
    total_exercises = sum(r.get('exercises', 0) for r in state['done'].values())
    print(f'\ndone in {rcb.fmt_hms(time.time() - t0)}  '
          f'{len(state["done"])} succeeded  {len(state["failed"])} failed  '
          f'{total_exercises} exercises  {calls} calls  ${usd:.4f}'
          + (f'  ({nulls} null-cost)' if nulls else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
