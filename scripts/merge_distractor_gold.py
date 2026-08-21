"""Merge adjudicated labeller sheets back into the gold file (TASK-726).

    python scripts/merge_distractor_gold.py \
        --frame data/eval/distractor_gold_frame_2026-08.json \
        --labels zh:nativeA:data/eval/..._zh_primary.csv \
        --labels zh:nativeB:data/eval/..._zh_overlap.csv \
        --out data/eval/distractor_gold_2026-08.json

Each `--labels` is `lang:labeller_id:path`. The labeller id is required and is
stored per label: kappa is computed between two *named* people, and a file that
cannot say who labelled what cannot support the disagreement analysis the whole
task turns on.

VALIDATION IS THE POINT
-----------------------
A gold set is a ruler. A typo'd `confusable` value silently becomes a category
of its own and quietly drops items out of every metric, so this script refuses
the merge instead:

* label values must come from the frame's own `label_vocabulary`;
* `notes` is required whenever `confusable == 'borderline'` -- TASK-726 asks
  for it because the borderline population is what TASK-720 will redesign the
  review band around, and an unexplained borderline tells that task nothing;
* every `item_id` must exist in the frame, and no (item, labeller) pair may
  appear twice;
* rows a labeller left entirely blank are reported as *unlabelled*, not merged
  as absent-and-fine. An adjudication that quietly stopped at row 200 must not
  read as a complete gold set.

`--out` is a new file, never an edit in place: TASK-726 §5 versions the gold set
because a metric computed against "the gold set" has to name which one.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from distractor_gold import (  # noqa: E402
    CONFUSABLE,
    TOPICAL_DISTANCE,
    cohens_kappa,
)

TRUE = {'true', 't', 'yes', 'y', '1'}
FALSE = {'false', 'f', 'no', 'n', '0', ''}


def _bool(raw: str, where: str) -> bool:
    s = (raw or '').strip().lower()
    if s in TRUE:
        return True
    if s in FALSE:
        return False
    raise SystemExit(f'[error] {where}: also_correct={raw!r} is not a boolean')


def read_sheet(path: str, lang: str, labeller: str) -> list[dict]:
    out, blank = [], 0
    with open(path, encoding='utf-8-sig', newline='') as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            item_id = (row.get('item_id') or '').strip()
            if not item_id:
                continue
            td = (row.get('topical_distance') or '').strip()
            cf = (row.get('confusable') or '').strip()
            ac_raw = (row.get('also_correct') or '').strip()
            notes = (row.get('notes') or '').strip()
            where = f'{os.path.basename(path)}:{i} ({item_id})'
            if not td and not cf and not ac_raw:
                blank += 1
                continue
            if td not in TOPICAL_DISTANCE:
                raise SystemExit(
                    f'[error] {where}: topical_distance={td!r} not in {TOPICAL_DISTANCE}'
                )
            if cf not in CONFUSABLE:
                raise SystemExit(
                    f'[error] {where}: confusable={cf!r} not in {CONFUSABLE}'
                )
            if cf == 'borderline' and not notes:
                raise SystemExit(
                    f'[error] {where}: confusable=borderline requires a note'
                )
            out.append({
                'item_id': item_id,
                'labeller_id': labeller,
                'lang': lang,
                'topical_distance': td,
                'confusable': cf,
                'also_correct': _bool(ac_raw, where),
                'notes': notes,
            })
    if blank:
        print(f'[warn] {os.path.basename(path)}: {blank} rows left unlabelled '
              f'-- they are absent from the gold set, not scored as agreement')
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--frame', required=True)
    ap.add_argument('--labels', action='append', required=True,
                    help='lang:labeller_id:path (repeatable)')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    with open(args.frame, encoding='utf-8') as fh:
        frame = json.load(fh)
    by_id = {it['item_id']: it for it in frame['items']}
    for it in frame['items']:
        it['labels'] = []

    seen: set[tuple[str, str]] = set()
    for spec in args.labels:
        lang, _, rest = spec.partition(':')
        labeller, _, path = rest.partition(':')
        if not (lang and labeller and path):
            raise SystemExit(f'[error] --labels {spec!r} is not lang:labeller_id:path')
        for rec in read_sheet(path, lang, labeller):
            item = by_id.get(rec['item_id'])
            if item is None:
                raise SystemExit(
                    f"[error] {rec['item_id']} is not in {args.frame}"
                )
            key = (rec['item_id'], labeller)
            if key in seen:
                raise SystemExit(f'[error] {key} labelled twice by the same person')
            seen.add(key)
            item['labels'].append({
                'labeller_id': labeller,
                'topical_distance': rec['topical_distance'],
                'confusable': rec['confusable'],
                'also_correct': rec['also_correct'],
                'notes': rec['notes'],
                'labelled_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            })

    # Coverage and kappa, printed before the write so a bad merge is visible
    # rather than discovered later by a metric that looks slightly off.
    print('\n' + '=' * 78)
    print('COVERAGE')
    print('=' * 78)
    print(f"{'lang':<6}{'selected':>10}{'labelled':>10}{'double':>8}"
          f"{'kappa(conf)':>13}{'kappa(topic)':>14}")
    for lang in sorted({it['lang_code'] for it in frame['items']}):
        pool = [it for it in frame['items']
                if it['lang_code'] == lang and it.get('selected')]
        lab = [it for it in pool if it['labels']]
        dbl = [it for it in pool if len(it['labels']) >= 2]
        k_c = cohens_kappa(
            [(it['labels'][0]['confusable'], it['labels'][1]['confusable'])
             for it in dbl], CONFUSABLE)
        k_t = cohens_kappa(
            [(it['labels'][0]['topical_distance'], it['labels'][1]['topical_distance'])
             for it in dbl], TOPICAL_DISTANCE)
        fmt = lambda k: f'{k:.3f}' if k is not None else '  n/a'  # noqa: E731
        print(f'{lang:<6}{len(pool):>10}{len(lab):>10}{len(dbl):>8}'
              f'{fmt(k_c):>13}{fmt(k_t):>14}')
        if k_c is not None and k_c < 0.6:
            print(f'  [BLOCK] {lang} kappa(confusable) = {k_c:.3f} < 0.60. '
                  f'TASK-726 step 4: the label definition is the defect. Revise '
                  f'the guide and relabel the slice before scoring any judge.')

    labelled = sum(1 for it in frame['items'] if it['labels'])
    per_lang = Counter(it['lang_code'] for it in frame['items'] if it['labels'])
    frame['labelled_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    frame['labellers'] = sorted({lab for _, lab in seen})
    frame['n_labelled'] = labelled

    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(frame, fh, ensure_ascii=False, indent=1)

    print(f'\n{labelled} labelled items {dict(per_lang)} -> {args.out}')
    if labelled < 540 or any(v < 180 for v in per_lang.values()):
        print('[warn] TASK-726 acceptance asks for >=540 items and >=180 per '
              'language; this file is short of that and any rate off it '
              'carries wider intervals than the task assumed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
