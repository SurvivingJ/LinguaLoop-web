#!/usr/bin/env python
"""Re-derive tests.target_age_tier from the stored raw jev score (ADR-029).

No jev calls: ``tests.age_tier_score`` is jev's raw answer, and the tier is
``tier_classifier.tier_from_score(score, language)`` under that language's
threshold table. Run after changing SCORE_THRESHOLDS.

  python scripts/rederive_tiers.py --lang ja            # dry run: show the moves
  python scripts/rederive_tiers.py --lang ja --apply    # apply via apply_jev_retier

Applying is one atomic RPC call (raises unless every row updates) and writes
``age_tier_calibration``. ``difficulty`` follows only where the tier changes.
Reverse to the pre-recalibration state with the UPDATE documented in
migrations/task821_tier_calibration.sql.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO, '.env'))

from services import tier_classifier  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

LANG_IDS = {'zh': 1, 'en': 2, 'ja': 3}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--lang', required=True, choices=sorted(LANG_IDS))
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()

    rows = (
        db.table('tests')
        .select('id, target_age_tier, age_tier_score, age_tier_confidence, '
                'age_tier_probabilities, age_tier_model')
        .eq('is_active', True).eq('language_id', LANG_IDS[args.lang])
        .limit(2000).execute()
    ).data
    missing = [r['id'] for r in rows if r['age_tier_score'] is None]
    if missing:
        print(f'ERROR: {len(missing)} active {args.lang} tests have no stored jev '
              'score; run scripts/retier_tests_with_jev.py first')
        return 1

    label = tier_classifier.calibration_for(args.lang)
    payload = []
    for r in rows:
        new = tier_classifier.tier_from_score(r['age_tier_score'], args.lang)
        payload.append({
            'id': r['id'], 'new_tier': new, 'score': r['age_tier_score'],
            'confidence': r['age_tier_confidence'],
            'probabilities': r['age_tier_probabilities'],
            'model': r['age_tier_model'], 'calibration': label,
        })
    old = {r['id']: r['target_age_tier'] for r in rows}
    matrix = Counter((old[p['id']], p['new_tier']) for p in payload)
    moved = sum(1 for p in payload if p['new_tier'] != old[p['id']])
    print(f'{args.lang}: {len(payload)} tests, calibration {label!r}, '
          f'{moved} change tier')
    print('   current\\new  ' + ' '.join(f'T{t}' for t in range(1, 7)))
    for cur in sorted({old[p['id']] for p in payload}):
        print(f'   T{cur}          ' + ' '.join(
            f'{matrix.get((cur, n), 0):>2}' for n in range(1, 7)))

    if not args.apply:
        print('dry run — pass --apply to write')
        return 0

    updated = db.rpc('apply_jev_retier', {'p_rows': payload}).execute().data
    print(f'apply_jev_retier updated {updated} rows')
    back = (
        db.table('tests').select('id, target_age_tier, age_tier_calibration')
        .in_('id', [p['id'] for p in payload]).execute()
    ).data
    want = {p['id']: p['new_tier'] for p in payload}
    bad = [b['id'] for b in back
           if b['target_age_tier'] != want[b['id']]
           or b['age_tier_calibration'] != label]
    print(f'verified {len(back)}/{len(payload)} rows read back, {len(bad)} mismatched')
    return 0 if updated == len(payload) == len(back) and not bad else 1


if __name__ == '__main__':
    raise SystemExit(main())
