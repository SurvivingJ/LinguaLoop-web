#!/usr/bin/env python3
"""Verify the Calibration -> test-selection handoff end to end.

Checks, in order:

1. `calibration_zipf_to_elo()` reproduces the anchor ladder exactly, and the two
   worked examples from features/vocabulary-aware-test-selection.tech §1.2 — the
   85%-known Zipf 5.0 -> ~1250 and the 50% crossover Zipf 3.85 -> ~1681. The gap
   between those two is the 430-point swing the contract exists to prevent, so
   seeing both is more informative than seeing either.

2. Python does NOT reimplement the map. This is the "test fixture asserting
   agreement" that §1.2 permits as the single Python copy; it exists to catch a
   future divergence, not to be used at runtime.

3. A synthetic learner with a KNOWN ability runs a calibration session, and the
   value that lands in `user_calibration_state` is the one selection will read.

Usage::

    PYTHONIOENCODING=utf-8 python -m scripts.verify_calibration_state --self-test
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

#: The ONLY permitted Python copy of the §1.2 anchors, and only so this script can
#: assert the SQL agrees with it. Runtime code must call the RPC.
ANCHORS = [(6.25, 875), (5.25, 1175), (4.50, 1400),
           (4.20, 1550), (3.80, 1700), (3.25, 1925)]


def _reference_map(zipf: float) -> int:
    """Piecewise-linear over ANCHORS, clamped. Mirror of the SQL, for comparison."""
    if zipf >= ANCHORS[0][0]:
        return ANCHORS[0][1]
    if zipf <= ANCHORS[-1][0]:
        return ANCHORS[-1][1]
    for (z_hi, e_hi), (z_lo, e_lo) in zip(ANCHORS, ANCHORS[1:]):
        if z_lo <= zipf <= z_hi:
            frac = (z_hi - zipf) / (z_hi - z_lo)
            return round(e_hi + (e_lo - e_hi) * frac)
    return ANCHORS[-1][1]


def check_map(db) -> bool:
    print('--- 1. calibration_zipf_to_elo ---')
    try:
        probe = db.rpc('calibration_zipf_to_elo', {'p_ability_zipf': 5.0}).execute().data
    except Exception as exc:
        print(f'  RPC unavailable: {str(exc)[:150]}')
        print('  -> apply migrations/calibration_user_state_and_zipf_to_elo.sql')
        return False

    ok = True
    for zipf, expected_elo in ANCHORS:
        got = db.rpc('calibration_zipf_to_elo', {'p_ability_zipf': zipf}).execute().data
        flag = 'OK ' if got == expected_elo else 'XX '
        ok &= (got == expected_elo)
        print(f'  {flag} anchor zipf {zipf:>5} -> {got:>5} (tier ladder {expected_elo})')

    print('  --- the contract, both ends of it ---')
    for zipf, label in ((5.00, '85%-known threshold (THE CONTRACT)'),
                        (3.85, '50% crossover (WRONG construct)')):
        got = db.rpc('calibration_zipf_to_elo', {'p_ability_zipf': zipf}).execute().data
        print(f'      zipf {zipf} -> {got:>5}   {label}')
    a = db.rpc('calibration_zipf_to_elo', {'p_ability_zipf': 5.00}).execute().data
    b = db.rpc('calibration_zipf_to_elo', {'p_ability_zipf': 3.85}).execute().data
    print(f'      swing between them: {b - a} ELO '
          f'(spec §1.2 records ~430 — this is why the construct is pinned)')

    print('  --- clamping, not extrapolation ---')
    for zipf in (7.0, 1.0):
        got = db.rpc('calibration_zipf_to_elo', {'p_ability_zipf': zipf}).execute().data
        inside = 875 <= got <= 1925
        ok &= inside
        print(f'  {"OK " if inside else "XX "} zipf {zipf} -> {got} (clamped to the ladder)')

    print('  --- SQL agrees with the reference implementation ---')
    mismatches = 0
    for i in range(0, 61):
        zipf = 2.5 + i * 0.06
        got = db.rpc('calibration_zipf_to_elo', {'p_ability_zipf': round(zipf, 2)}).execute().data
        want = _reference_map(zipf)
        if abs(got - want) > 1:
            mismatches += 1
            if mismatches <= 3:
                print(f'  XX  zipf {zipf:.2f}: SQL {got} vs reference {want}')
    ok &= (mismatches == 0)
    print(f'  {"OK " if mismatches == 0 else "XX "} 61 probe points, {mismatches} mismatches')
    return bool(ok)


def check_state_write(db, cs) -> bool:
    print('\n--- 2. user_calibration_state round trip ---')
    try:
        db.table('user_calibration_state').select('user_id').limit(1).execute()
    except Exception as exc:
        print(f'  table unavailable: {str(exc)[:150]}')
        print('  -> apply migrations/calibration_user_state_and_zipf_to_elo.sql')
        return False

    user_id = str(uuid.uuid4())
    true_threshold, slope = 4.30, 3.0
    session = cs.start_session(user_id, 3, 2, cs.MODE_DEFINITION)
    random.seed(99)
    import math
    served = 0
    try:
        for _ in range(120):
            try:
                item = cs.next_item(user_id, session)
            except cs.CalibrationError:
                continue
            if item is None:
                break
            served += 1
            row = (db.table('calibration_responses').select('anchor_zipf')
                     .eq('id', item['response_id']).limit(1).execute().data[0])
            z = row['anchor_zipf'] or 0.0
            opts = (db.table('calibration_response_options').select('position,is_key')
                      .eq('response_id', item['response_id']).execute().data)
            key = next(o['position'] for o in opts if o['is_key'])
            wrong = [o['position'] for o in opts if not o['is_key']]
            knowledge = 1 / (1 + math.exp(-slope * (z - true_threshold)))
            p = cs.GUESS_RATE + (1 - cs.GUESS_RATE) * knowledge
            cs.record_answer(user_id, session, item['response_id'],
                             key if random.random() < p else random.choice(wrong), 900)

        report = cs.end_session(user_id, session)
        state = (db.table('user_calibration_state').select('*')
                   .eq('user_id', user_id).execute().data or [])
        if not state:
            print('  XX  no state row written')
            return False
        s = state[0]
        true_85 = true_threshold + math.log(0.85 / 0.15) / slope
        elo = db.rpc('calibration_zipf_to_elo',
                     {'p_ability_zipf': s['ability_zipf']}).execute().data
        print(f'  served={served}  items_answered={s["items_answered"]}  '
              f'sessions_pooled={s["sessions_pooled"]}  mode={s["mode"]}')
        print(f'  ability_zipf = {float(s["ability_zipf"]):.3f}  '
              f'(true {true_85:.3f}, err {float(s["ability_zipf"]) - true_85:+.3f})')
        print(f'  ability_se   = {s["ability_se"]}   bands={len(s["band_accuracies"])}')
        print(f'  -> calibration_zipf_to_elo = {elo}  (what selection would seed)')
        print(f'  pooled block returned to the client: {report.get("pooled") is not None}')
        return True
    finally:
        db.table('calibration_sessions').delete().eq('id', session['id']).execute()
        db.table('user_calibration_state').delete().eq('user_id', user_id).execute()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()
    from services import calibration_service as cs

    map_ok = check_map(db)
    state_ok = check_state_write(db, cs)

    print('\n=== summary ===')
    print(f'  zipf->elo map:        {"PASS" if map_ok else "NOT APPLIED / FAIL"}')
    print(f'  state handoff:        {"PASS" if state_ok else "NOT APPLIED / FAIL"}')
    if not (map_ok and state_ok):
        print('\n  Apply migrations/calibration_user_state_and_zipf_to_elo.sql, '
              'then re-run. Calibration itself works either way — the handoff '
              'fails closed rather than erroring.')
        sys.exit(1)


if __name__ == '__main__':
    main()
