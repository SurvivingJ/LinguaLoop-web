#!/usr/bin/env python
"""Build a blind labelling sample for fitting a language's jev tier thresholds
(ADR-029, recalibration).

  python scripts/build_tier_gold_sample.py --lang zh --n 60

Picks ``n`` active tests spread evenly across the jev score range (so every part
of the scale is represented), shuffles them, and writes to
data/eval/jev_recalibration_2026-09-27/:

  <lang>_blind.md          rubric (native language) + numbered passages. NO labels,
                           NO jev output: this is what the labellers read.
  <lang>_blind_manifest.json   item number -> test id
  <lang>_transcripts.json      test id -> transcript
  <lang>_scores_stored.json    test id -> {score, confidence} (jev, as stored)

Then two independent readers each write <lang>_gold_A.json / _B.json
({"01": {"tier": 1-6, "alt": null|1-6}, ...}) and
scripts/fit_tier_thresholds.py fits and cross-validates the cut points.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(REPO, '.env'))

from services.categorical_maps import (  # noqa: E402
    TIER_CONSTRAINTS, TIER_DISPLAY_NAMES, VALID_TIERS,
)
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

OUT = os.path.join(REPO, 'data', 'eval', 'jev_recalibration_2026-09-27')
LANG_IDS = {'zh': 1, 'en': 2, 'ja': 3}
HEADINGS = {
    'zh': ('# 中文段落难度层级判定（盲评）', '## 评分标准', '## 段落', '：'),
    'en': ('# English passage difficulty tiers (blind)', '## Rubric', '## Passages', ': '),
    'ja': ('# 日本語パッセージの難易度ティア判定（ブラインド）', '## ルーブリック', '## パッセージ', '：'),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', required=True, choices=sorted(LANG_IDS))
    ap.add_argument('--n', type=int, default=60)
    ap.add_argument('--seed', type=int, default=11)
    args = ap.parse_args()

    if not SupabaseFactory.is_initialized():
        SupabaseFactory.initialize()
    db = get_supabase_admin()
    rows = (
        db.table('tests')
        .select('id, transcript, age_tier_score, age_tier_confidence')
        .eq('is_active', True).eq('language_id', LANG_IDS[args.lang])
        .not_.is_('age_tier_score', 'null').limit(2000).execute()
    ).data
    rows.sort(key=lambda r: r['age_tier_score'])
    n = min(args.n, len(rows))
    picked = [rows[round(k * (len(rows) - 1) / max(n - 1, 1))] for k in range(n)]

    rng = random.Random(args.seed)
    order = picked[:]
    rng.shuffle(order)
    manifest = {f'{i:02d}': r['id'] for i, r in enumerate(order, 1)}

    title, rubric_h, items_h, sep = HEADINGS[args.lang]
    lid = LANG_IDS[args.lang]
    lines = [title + '\n', rubric_h + '\n']
    for t in VALID_TIERS:
        lines.append(f'- **{t}** {TIER_DISPLAY_NAMES[t][lid]}{sep}{TIER_CONSTRAINTS[t][lid]}')
    lines += ['', items_h + '\n']
    for num, r in zip(manifest, order):
        lines.append(f'### Item {num}\n\n{r["transcript"]}\n')

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f'{args.lang}_blind.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    dump = lambda name, obj: json.dump(  # noqa: E731
        obj, open(os.path.join(OUT, f'{args.lang}_{name}.json'), 'w', encoding='utf-8'),
        ensure_ascii=False, indent=1)
    dump('blind_manifest', manifest)
    dump('transcripts', {r['id']: r['transcript'] for r in picked})
    dump('scores_stored', {r['id']: {'score': r['age_tier_score'],
                                     'confidence': r['age_tier_confidence']} for r in picked})
    chars = sum(len(r['transcript']) for r in picked)
    print(f'{args.lang}: {n} of {len(rows)} tests, {chars} characters')


if __name__ == '__main__':
    main()
