"""Build the unlabelled frame for the distractor-plausibility gold set (TASK-726).

Takes question samples generated on the live stack, explodes them to one row
per distractor, pre-rates every row with two judge models, force-includes every
disagreement, computes the frame weights, and writes:

* `data/eval/distractor_gold_frame_<tag>.json` -- the machine-readable frame,
  with empty `labels` lists waiting for an adjudicator;
* `data/eval/<stem>_<lang>_primary.csv` -- one sheet per language for that
  language's primary labeller;
* `data/eval/<stem>_<lang>_overlap.csv` -- the double-labelled slice for the
  second labeller, from which Cohen's kappa is computed.

    python scripts/build_distractor_gold_frame.py \
        --sample data/eval/task721_before.json \
        --arms "a=4:qwen/qwen3.6-flash,b=4:" \
        --tag 2026-08

WHAT THIS SCRIPT DOES NOT DO
----------------------------
It does not label anything. "Is this distractor plausibly confusable with the
correct answer?" is the judgment under dispute; a model opinion on it is the
thing being measured, not the ruler. The frame is the deliverable; the labels
come from native speakers and the file is inert until they arrive.

Consequently **the labeller CSVs deliberately omit the pre-ratings.** They are
in the JSON, for the harness; showing a labeller what two models thought would
anchor them onto exactly the judgment the gold set exists to check
independently, and a gold set anchored to the models it arbitrates is worth
nothing.

SAMPLE PROVENANCE
-----------------
`--sample` must be output from the CURRENT live generator prompts, because the
gold set will be used to judge output from those prompts. `task721_before.json`
qualifies: `generate_question_sample.py --templates live` drew it on
2026-08-19, and the TASK-721 rewrite rows are staged but not active, so "live"
then is live now. A sample drawn from staged prompts (`task721_after.json`)
does NOT qualify and the script refuses to guess -- pass `--allow-any-sample`
if the mismatch is deliberate.

WHY TWO ARMS AND WHICH TWO
--------------------------
TASK-718 measured `qwen/qwen3.6-flash` and the gemini flash-lite line and found
their reject sets **disjoint**: across 150 questions they agreed on one reject.
That disjointness is the reason this gold set exists, so those two models are
what the frame is pre-rated with -- the disagreement flag then marks the exact
population that made the workstream un-adjudicable.

Every call is logged to `llm_calls` under `pipeline='diag'`.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

from distractor_gold import (  # noqa: E402
    CONFUSABLE,
    LANG_NAME,
    TOPICAL_DISTANCE,
    assign_frame_weights,
    disagreement,
    explode_items,
    pick_overlap_slice,
    select_for_adjudication,
    stratum,
)
from measure_judge_flag_rate import (  # noqa: E402
    LANG_ID,
    _parse_arms,
    _judge_one,
    _load_templates,
    _map_type_codes,
    report_cost,
)

# Columns handed to a human labeller, in the order a labeller reads them.
CSV_COLUMNS = [
    'item_id', 'lang', 'type_code', 'passage', 'question', 'answer',
    'distractor', 'topical_distance', 'confusable', 'also_correct', 'notes',
]


# ------------------------------------------------------------------ production mix


def production_shares(db) -> dict[tuple[int, str], float]:
    """Per-language share of live questions by type -- the reweighting target.

    Computed, not hardcoded: the mix drifts as content is generated, and a
    stale constant would silently reweight to last month's product.
    """
    id2code = {
        t['id']: t['type_code']
        for t in db.table('dim_question_types').select('id, type_code').execute().data
    }
    counts: Counter = Counter()
    page, size = 0, 1000
    while True:
        rows = (
            db.table('questions')
            .select('question_type_id, tests!inner(language_id)')
            .range(page * size, page * size + size - 1)
            .execute()
            .data
            or []
        )
        for r in rows:
            lang = (r.get('tests') or {}).get('language_id')
            code = id2code.get(r.get('question_type_id'))
            if lang in LANG_NAME and code:
                counts[(lang, code)] += 1
        if len(rows) < size:
            break
        page += 1

    totals: Counter = Counter()
    for (lang, _), n in counts.items():
        totals[lang] += n
    return {k: n / totals[k[0]] for k, n in counts.items() if totals[k[0]]}


# ---------------------------------------------------------------------- pre-rating


def prerate(db, rows: list[dict], arms: list[dict], langs: list[int], workers: int):
    """Rate every question under both arms; return one result row per call."""
    jobs = []
    total = len(rows) * len(arms)
    for arm in arms:
        tpl = _load_templates(db, arm['version'], langs, arm['model'])
        print(
            f"  arm {arm['name']}: "
            + ', '.join(
                f"{LANG_NAME[lang]}=v{tpl[lang]['version']}:{tpl[lang]['model']}"
                for lang in langs
            )
        )
        jobs += [(arm['name'], row, tpl, '', total) for row in rows]

    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_judge_one, jobs))
    return results


def attach_ratings(items: list[dict], results: list[dict], arm_names: list[str]) -> None:
    """Fold per-question judge output onto per-distractor frame items.

    A judge that returned fewer ratings than there were distractors leaves the
    tail as None rather than shifting the remaining ratings up -- a silent
    off-by-one here would mislabel which distractor a rating belongs to, and
    every downstream number would be wrong in a way no total would reveal.
    """
    by_key = {(r['arm'], r['qid']): r for r in results}
    models = {r['arm']: r.get('model') for r in results}
    for it in items:
        pre = {}
        for arm in arm_names:
            res = by_key.get((arm, it['qid']))
            ratings = (res or {}).get('ratings') or []
            idx = it['distractor_index']
            pre[arm] = {
                'model': models.get(arm),
                'rating': ratings[idx] if idx < len(ratings) else None,
                'ok': bool((res or {}).get('ok')),
            }
        it['prerate'] = pre
        a, b = (pre[arm_names[0]]['rating'], pre[arm_names[1]]['rating'])
        flag, kind = disagreement(a, b)
        it['disagreement'] = flag
        it['disagreement_kind'] = kind


# -------------------------------------------------------------------------- output


def write_csvs(items: list[dict], stem: str) -> list[str]:
    """Per-language labeller sheets. utf-8-sig so Excel opens CJK correctly."""
    written = []
    by_lang: dict[int, list[dict]] = defaultdict(list)
    for it in items:
        if it.get('selected'):
            by_lang[it['lang']].append(it)

    for lang, pool in sorted(by_lang.items()):
        for kind, rows in (
            ('primary', pool),
            ('overlap', [it for it in pool if it.get('overlap_slice')]),
        ):
            if not rows:
                continue
            path = f'{stem}_{LANG_NAME[lang]}_{kind}.csv'
            with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
                w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
                w.writeheader()
                for it in rows:
                    w.writerow({
                        'item_id': it['item_id'],
                        'lang': it['lang_code'],
                        'type_code': it['type_code'],
                        'passage': it['passage'],
                        'question': it['question'],
                        'answer': it['answer'],
                        'distractor': it['distractor'],
                        'topical_distance': '',
                        'confusable': '',
                        'also_correct': '',
                        'notes': '',
                    })
            written.append(path)
    return written


def summarise(items: list[dict], shares: dict) -> None:
    sel = [it for it in items if it.get('selected')]
    print('\n' + '=' * 88)
    print('FRAME')
    print('=' * 88)
    print(f"{'lang':<6}{'frame':>7}{'selected':>10}{'disagree':>10}"
          f"{'overlap':>9}{'w min':>8}{'w max':>8}")
    for lang in sorted({it['lang'] for it in items}):
        pool = [it for it in sel if it['lang'] == lang]
        allp = [it for it in items if it['lang'] == lang]
        ws = [it['frame_weight'] for it in pool] or [0.0]
        print(
            f'{LANG_NAME[lang]:<6}{len(allp):>7}{len(pool):>10}'
            f"{sum(1 for it in pool if it['disagreement']):>10}"
            f"{sum(1 for it in pool if it['overlap_slice']):>9}"
            f'{min(ws):>8.3f}{max(ws):>8.3f}'
        )

    print('\nDISAGREEMENT KIND (selected)')
    for kind, n in Counter(
        it['disagreement_kind'] for it in sel if it['disagreement']
    ).most_common():
        print(f'  {kind:<10}{n:>5}')

    print('\nSTRATUM WEIGHTS  (production share vs frame share)')
    print(f"{'stratum':<28}{'n':>5}{'frame %':>10}{'prod %':>9}{'weight':>9}")
    for lang in sorted({it['lang'] for it in sel}):
        pool = [it for it in sel if it['lang'] == lang]
        counts = Counter(stratum(it) for it in pool)
        for key, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            w = next(it['frame_weight'] for it in pool if stratum(it) == key)
            print(
                f'{LANG_NAME[key[0]] + "/" + key[1]:<28}{n:>5}'
                f'{100 * n / len(pool):>9.1f}%{100 * shares.get(key, 0.0):>8.1f}%'
                f'{w:>9.3f}'
            )

    unrated = sum(
        1 for it in sel for arm in it['prerate'].values() if arm['rating'] is None
    )
    if unrated:
        print(f'\n[warn] {unrated} arm-ratings are missing; those items are '
              f'flagged as disagreements by design, not dropped')


# ---------------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--sample', action='append', required=True,
                    help='question sample JSON from the live stack (repeatable)')
    ap.add_argument('--arms', default='a=4:qwen/qwen3.6-flash,b=4:',
                    help='two pre-rating arms, name=version:model')
    ap.add_argument('--langs', default='zh,en,ja')
    ap.add_argument('--adjudicate', type=int, default=None,
                    help='items per language to send to an adjudicator; '
                         'default = the whole frame (no enrichment bias)')
    ap.add_argument('--overlap', type=int, default=60,
                    help='items per language double-labelled, for kappa')
    ap.add_argument('--seed', type=int, default=726)
    ap.add_argument('--workers', type=int, default=int(os.environ.get('WORKERS', '6')))
    ap.add_argument('--tag', default=time.strftime('%Y-%m'))
    ap.add_argument('--out-dir', default=os.path.join(ROOT, 'data', 'eval'))
    ap.add_argument('--dry-run', action='store_true',
                    help='build the frame with no pre-ratings and spend nothing')
    ap.add_argument('--allow-any-sample', action='store_true',
                    help='skip the "sample came from staged prompts" guard')
    args = ap.parse_args()

    langs = [LANG_ID[n.strip()] for n in args.langs.split(',') if n.strip()]
    arm_specs = _parse_arms(args.arms, None)
    if len(arm_specs) != 2:
        raise SystemExit('[error] --arms must name exactly two pre-rating arms')

    rows: list[dict] = []
    seen: set[str] = set()
    for path in args.sample:
        if 'after' in os.path.basename(path) and not args.allow_any_sample:
            raise SystemExit(
                f'[error] {path} looks like staged-prompt output; the gold set '
                f'must be drawn from the live stack. Pass --allow-any-sample '
                f'if this is deliberate.'
            )
        with open(path, encoding='utf-8') as fh:
            for r in json.load(fh):
                if r['lang'] in langs and r['qid'] not in seen:
                    seen.add(r['qid'])
                    rows.append(r)
    if not rows:
        raise SystemExit('[error] no sample rows for the requested languages')

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    _map_type_codes(db, rows)

    items = explode_items(rows)
    print(f'sample: {len(rows)} questions -> {len(items)} items '
          f'{dict(Counter(LANG_NAME[r["lang"]] for r in rows))}')

    since = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(time.time() - 60))
    if args.dry_run:
        print('[dry-run] no judge calls; every item is flagged unrated')
        attach_ratings(items, [], [a['name'] for a in arm_specs])
    else:
        print(f'pre-rating {len(rows) * 2} judge calls across two arms')
        results = prerate(db, rows, arm_specs, langs, args.workers)
        attach_ratings(items, results, [a['name'] for a in arm_specs])

    rng = random.Random(args.seed)
    select_for_adjudication(items, args.adjudicate, rng)
    shares = production_shares(db)
    assign_frame_weights(items, shares)
    pick_overlap_slice(items, args.overlap, rng)

    for it in items:
        it['labels'] = []
        it['labels_expected'] = 2 if it['overlap_slice'] else 1

    os.makedirs(args.out_dir, exist_ok=True)
    stem = os.path.join(args.out_dir, f'distractor_gold_frame_{args.tag}')
    payload = {
        'tag': args.tag,
        'built_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'samples': args.sample,
        'arms': arm_specs,
        'seed': args.seed,
        'label_vocabulary': {
            'topical_distance': list(TOPICAL_DISTANCE),
            'confusable': list(CONFUSABLE),
            'also_correct': [True, False],
        },
        'production_shares': {f'{LANG_NAME[k[0]]}/{k[1]}': round(v, 6)
                              for k, v in sorted(shares.items())},
        'items': items,
    }
    out = f'{stem}.json'
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    summarise(items, shares)
    csvs = write_csvs(items, stem)
    if not args.dry_run:
        report_cost(db, [a['name'] for a in arm_specs], since)
    print(f'\nframe -> {out}')
    for p in csvs:
        print(f'  sheet -> {p}')
    print('\nNEXT: adjudication. The frame is inert until the CSVs come back '
          'labelled by native speakers (zh and ja must not be labelled from '
          'translation). Merge them with merge_distractor_gold.py.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
