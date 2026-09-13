#!/usr/bin/env python3
"""TASK-773 — fill calibration_distractor_cache, one language pair at a time.

WHY THIS IS A SCRIPT AND NOT A MIGRATION
    Filling the cache means running the semantic distractor picker once per
    anchor, and a COLD anchor costs ~1.1 s (measured 2026-09-13). Across ~27k
    anchors that is hours if done badly and about half an hour if done well, and
    the difference is entirely in the ORDER.

    Each language pair has its own partial HNSW index of 56-86 MB. The instance
    has 224 MB of shared_buffers and 442 MB of these indexes in total, so they
    cannot all stay resident. Draining ONE pair to completion keeps that pair's
    index hot and drops the per-anchor cost to ~20-60 ms; interleaving pairs
    thrashes it back to ~1.1 s. That is the whole strategy, and it is why this
    loops over pairs in the outer loop and chunks in the inner one.

RESUMABLE
    The SQL side selects anchors that have no cache rows yet, so re-running after
    an interruption simply continues. Nothing is recomputed.

WHEN TO RE-RUN
    The cache is DERIVED data. Re-run after any job that changes definitions,
    embeddings or the sense inventory — otherwise a corrected definition keeps
    being served as a stale foil. Refresh the anchor pool first:

        python scripts/build_calibration_distractor_cache.py --refresh-pool

USAGE
    PYTHONPATH=. python scripts/build_calibration_distractor_cache.py
    PYTHONPATH=. python scripts/build_calibration_distractor_cache.py --coverage
    PYTHONPATH=. python scripts/build_calibration_distractor_cache.py \
        --word-language 3 --definition-language 2 --mode definition
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

LANG_NAMES = {1: 'zh', 2: 'en', 3: 'ja'}


def _coverage(db) -> list[dict]:
    return db.rpc('calibration_distractor_cache_coverage', {}).execute().data or []


def _print_coverage(rows: list[dict]) -> None:
    print(f'{"pair":<10} {"mode":<14} {"cached":>8} / {"anchors":<8} {"":>6}')
    print('-' * 52)
    for r in rows:
        pair = (f'{LANG_NAMES.get(r["word_language_id"], r["word_language_id"])}'
                f'/{LANG_NAMES.get(r["definition_language_id"], r["definition_language_id"])}')
        anchors = r['anchors'] or 0
        cached = r['cached'] or 0
        pct = (100.0 * cached / anchors) if anchors else 100.0
        print(f'{pair:<10} {r["mode"]:<14} {cached:>8} / {anchors:<8} {pct:5.1f}%')


def _remaining(db, word_lang: int, def_lang: int, mode: str) -> int:
    """Anchors of this pair/mode that are still uncached."""
    for r in _coverage(db):
        if (r['word_language_id'] == word_lang
                and r['definition_language_id'] == def_lang
                and r['mode'] == mode):
            return (r['anchors'] or 0) - (r['cached'] or 0)
    return 0


def _build_pair(db, word_lang: int, def_lang: int, mode: str, batch: int) -> None:
    label = (f'{LANG_NAMES.get(word_lang, word_lang)}/'
             f'{LANG_NAMES.get(def_lang, def_lang)} {mode}')
    total_processed = total_filled = total_short = 0
    started = time.time()
    # TASK-773b. The SQL selector now records anchors it could not fill so it
    # stops re-offering them, which is the real fix. This is a second line of
    # defence: an unbounded `while True` driven by a database query is only ever
    # one selector bug away from spinning forever, and the first version of this
    # script did exactly that — thirteen short ja anchors cycled indefinitely.
    seen = set()

    while True:
        chunk_started = time.time()
        try:
            rows = db.rpc('calibration_cache_distractors_chunk', {
                'p_word_language_id': word_lang,
                'p_definition_language_id': def_lang,
                'p_mode': mode,
                'p_batch': batch,
            }).execute().data or []
        except Exception as exc:
            # Not fatal for the whole run: one pair failing should not cost the
            # progress already made on the others.
            print(f'  {label}: chunk failed ({str(exc)[:120]}) — stopping this pair')
            return

        row = rows[0] if rows else {}
        processed = int(row.get('anchors_processed') or 0)
        if processed == 0:
            break

        # Progress is measured by the remaining count falling. If a chunk
        # processes anchors without reducing what is left, the selector is
        # handing back the same rows and looping again cannot help.
        remaining = _remaining(db, word_lang, def_lang, mode)
        if remaining in seen:
            print(f'  {label}: STALLED at {remaining} remaining after '
                  f'{total_processed} processed — the selector is repeating '
                  f'itself; stopping this pair')
            return
        seen.add(remaining)

        total_processed += processed
        total_filled += int(row.get('anchors_filled') or 0)
        total_short += int(row.get('anchors_short') or 0)
        per_anchor = (time.time() - chunk_started) / processed
        print(f'  {label}: {total_processed:>6} done '
              f'({per_anchor * 1000:6.0f} ms/anchor, {total_short} short)',
              flush=True)

    if total_processed:
        elapsed = time.time() - started
        print(f'  {label}: FINISHED {total_processed} anchors in {elapsed / 60:.1f} min '
              f'({total_filled} filled, {total_short} short)')
    else:
        print(f'  {label}: already complete')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--coverage', action='store_true',
                    help='report cached-vs-total per pair and exit')
    ap.add_argument('--refresh-pool', action='store_true',
                    help='rebuild calibration_anchor_pool from the dictionary first')
    ap.add_argument('--word-language', type=int, default=None)
    ap.add_argument('--definition-language', type=int, default=None)
    ap.add_argument('--mode', choices=('definition', 'pronunciation'), default=None)
    ap.add_argument('--batch', type=int, default=25,
                    help='anchors per RPC call (default 25)')
    args = ap.parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.refresh_pool:
        rows = db.rpc('calibration_refresh_anchor_pool', {}).execute().data
        print(f'anchor pool rebuilt: {rows} rows')

    coverage = _coverage(db)
    if args.coverage:
        _print_coverage(coverage)
        return

    targets = [
        r for r in coverage
        if (args.word_language is None or r['word_language_id'] == args.word_language)
        and (args.definition_language is None
             or r['definition_language_id'] == args.definition_language)
        and (args.mode is None or r['mode'] == args.mode)
        and (r['cached'] or 0) < (r['anchors'] or 0)
    ]
    if not targets:
        print('nothing to build — every selected pair is fully cached')
        _print_coverage(coverage)
        return

    # Largest remaining first. The point is to finish a pair once its index is
    # hot, so the order between pairs only needs to be deterministic and not
    # interleaved; biggest-first also surfaces a bad estimate soonest.
    targets.sort(key=lambda r: (r['anchors'] or 0) - (r['cached'] or 0), reverse=True)

    print(f'building {len(targets)} pair/mode combinations, '
          f'{sum((r["anchors"] or 0) - (r["cached"] or 0) for r in targets)} anchors '
          f'remaining\n')
    for r in targets:
        _build_pair(db, r['word_language_id'], r['definition_language_id'],
                    r['mode'], args.batch)

    print('\n=== final coverage ===')
    _print_coverage(_coverage(db))


if __name__ == '__main__':
    main()
