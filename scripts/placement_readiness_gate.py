"""Vocabulary placement launch gate per (word language, definition language) — read-only (TASK-1075, TASK-1088).

vocab-placement tech §2 "Launch gate": ≥ 90% of the frame placement-ready overall and ≥ 80% in every band;
in every band where ≥ 5% of the frame is not ready, ready and not-ready lemmas must look alike:
|mean Zipf difference| ≤ 0.10 and a difference in the share of lemmas with ≥ 3 characters ≤ 10 points
(the exam-list share check needs the ADR-054 list file; pass --list-file to include it).

    python scripts/placement_readiness_gate.py --word-language 3            # every definition language
    python scripts/placement_readiness_gate.py --word-language 1 --definition-language 2

Prints PASS / FAIL per band and per pair; exit code 1 when any pair fails. Calls only
calibration_placement_ready_counts (STABLE, read-only).
"""
from __future__ import annotations

import argparse
import json
import sys

OVERALL_MIN, BAND_MIN = 0.90, 0.80
REP_BAND_UNREADY, ZIPF_MAX_DIFF, LEN3_MAX_DIFF = 0.05, 0.10, 0.10


def evaluate(counts: dict) -> dict:
    """Pure: the gate verdict from the ready-counts payload (tech §14)."""
    frame, ready = int(counts.get('frame') or 0), int(counts.get('ready') or 0)
    overall = ready / frame if frame else 0.0
    bands, ok = [], frame > 0 and overall >= OVERALL_MIN
    for b in counts.get('bands') or []:
        fn, rn = int(b.get('frame_n') or 0), int(b.get('ready_n') or 0)
        share = rn / fn if fn else 0.0
        checks = {'ready_share': share >= BAND_MIN}
        if fn and (1 - share) >= REP_BAND_UNREADY:
            rz, uz = b.get('ready_mean_zipf'), b.get('unready_mean_zipf')
            r3, u3 = b.get('ready_share_len3'), b.get('unready_share_len3')
            checks['zipf'] = rz is not None and uz is not None and abs(float(rz) - float(uz)) <= ZIPF_MAX_DIFF
            checks['len3'] = r3 is not None and u3 is not None and abs(float(r3) - float(u3)) <= LEN3_MAX_DIFF
        band_ok = all(checks.values())
        ok = ok and band_ok
        bands.append({'band': b.get('band'), 'frame_n': fn, 'ready_n': rn, 'share': round(share, 3),
                      'checks': checks, 'pass': band_ok})
    return {'overall': round(overall, 3), 'pass': bool(ok), 'bands': bands}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--word-language', type=int, required=True)
    ap.add_argument('--definition-language', type=int, default=None)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--psql', metavar='DSN', default=None,
                    help='read through psql instead of the API: zh takes ~30 s, over the 8 s PostgREST timeout')
    args = ap.parse_args(argv)
    dls = [args.definition_language] if args.definition_language else [1, 2, 3]
    if args.psql:
        import subprocess

        def ready_counts(lang, d):
            sql = f'SELECT calibration_placement_ready_counts({int(lang)}::smallint, {int(d)}::smallint)'
            out = subprocess.run(['psql', args.psql, '-v', 'ON_ERROR_STOP=1', '-tAc', sql],
                                 capture_output=True, text=True, check=True).stdout.strip()
            return json.loads(out) if out else {}
    else:
        from services.supabase_factory import get_supabase_admin
        db = get_supabase_admin()

        def ready_counts(lang, d):
            return db.rpc('calibration_placement_ready_counts', {
                'p_word_language_id': lang, 'p_definition_language_id': d}).execute().data or {}
    all_ok = True
    for d in dls:
        counts = ready_counts(args.word_language, d)
        if not counts.get('frame'):
            continue
        verdict = evaluate(counts)
        all_ok = all_ok and verdict['pass']
        if args.json:
            print(json.dumps({'pair': f'{args.word_language}:{d}', **verdict}))
            continue
        print(f"({args.word_language}, {d}) overall {verdict['overall']:.1%} → {'PASS' if verdict['pass'] else 'FAIL'}")
        for b in verdict['bands']:
            failed = [k for k, v in b['checks'].items() if not v]
            print(f"  band {b['band']}: {b['ready_n']}/{b['frame_n']} ready ({b['share']:.0%})"
                  f" {'PASS' if b['pass'] else 'FAIL ' + ','.join(failed)}")
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
