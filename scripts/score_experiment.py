"""Score a test-generation experiment (TASK-923/924/927).

For each arm (run tag):
  * slots, tests passed, survival-floor failures ("Too few valid questions"),
    other errors
  * $ per passed test — llm_calls.cost_usd summed over the arm's run window
    (first..last finished_at, same language). Arms must run one after another.
  * quality-check findings per 100 questions (all checks forced to flag)
  * review: major and minor per question, level_fit = ok rate, with 95%
    bootstrap intervals (resampling tests)

    python scripts/score_experiment.py e1-flag e1-calibrated e1-reject \
        --reviews data/test_quality/experiments/e1_review
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path[:0] = [ROOT]

from scripts.audit_test_quality import audit  # noqa: E402
from scripts.build_experiment_review_packs import load_records  # noqa: E402


def bootstrap(per_test: list, stat, n=2000, seed=0):
    """95% interval of stat(list of per-test tuples) by resampling tests."""
    if not per_test:
        return (float('nan'), float('nan'))
    rng = random.Random(seed)
    vals = sorted(stat([rng.choice(per_test) for _ in per_test]) for _ in range(n))
    return vals[int(0.025 * n)], vals[int(0.975 * n) - 1]


def rate(field, value):
    def f(rows):
        num = sum(sum(1 for r in t if r.get(field) == value) for t in rows)
        den = sum(len(t) for t in rows)
        return num / den if den else float('nan')
    return f


def score(recs, tests, reviews, costs) -> str:
    by_tag = defaultdict(list)
    for r in recs:
        by_tag[r['run_tag']].append(r)
    test_by_id = {t['id']: t for t in tests}
    rev_by_test = defaultdict(list)
    for r in reviews:
        rev_by_test[r['test_id']].append(r)

    out = ['| arm | slots | passed | floor fails | other errors | $/test | qc findings /100 q | '
           'major /q | minor /q | level fit ok | (95% CI major+minor) |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    for tag, rs in by_tag.items():
        passed = [r for r in rs if r['outcome'] == 'pass']
        floor = sum(1 for r in rs if r['outcome'] == 'error' and 'Too few valid questions' in (r.get('error') or ''))
        other = sum(1 for r in rs if r['outcome'] == 'error') - floor
        ts = [test_by_id[r['test_id']] for r in passed if r.get('test_id') in test_by_id]
        nq = sum(len(t['questions']) for t in ts) or 1
        findings = audit(ts)
        per_test = [rev_by_test[t['id']] for t in ts if rev_by_test.get(t['id'])]
        mj, mn, lf = rate('verdict', 'major')(per_test), rate('verdict', 'minor')(per_test), rate('level_fit', 'ok')(per_test)

        def bad(rows):
            return rate('verdict', 'major')(rows) + rate('verdict', 'minor')(rows)
        lo, hi = bootstrap(per_test, bad)
        cost = costs.get(tag)
        per = f"{cost / len(passed):.3f}" if cost is not None and passed else '—'
        out.append(f"| {tag} | {len(rs)} | {len(passed)} | {floor} | {other} | {per} | "
                   f"{100 * len(findings) / nq:.1f} | {mj:.3f} | {mn:.3f} | {lf:.2f} | {lo:.3f}–{hi:.3f} |")
    return '\n'.join(out) + '\n'


def arm_costs(db, recs) -> dict:
    windows = defaultdict(list)
    for r in recs:
        if r.get('finished_at'):
            windows[(r['run_tag'], r['language'])].append((r['finished_at'], r.get('seconds') or 0))
    costs = defaultdict(float)
    from datetime import datetime, timedelta
    for (tag, lang), pts in windows.items():
        start = min(datetime.fromisoformat(t) - timedelta(seconds=s) for t, s in pts)
        end = max(datetime.fromisoformat(t) for t, _ in pts)
        rows = (db.table('llm_calls').select('cost_usd').eq('language_code', lang)
                .gte('created_at', start.isoformat()).lte('created_at', end.isoformat())
                .execute().data or [])
        costs[tag] += sum(float(r['cost_usd'] or 0) for r in rows)
    return dict(costs)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tags', nargs='+')
    ap.add_argument('--reviews', help='directory with review_*.json from the arm-blind review')
    ap.add_argument('--input-json', help='tests dump instead of the database (no cost column)')
    ap.add_argument('--out', help='write summary.md here (default: first tag dir)')
    args = ap.parse_args(argv)

    recs = load_records(args.tags)
    ids = [r['test_id'] for r in recs if r.get('test_id')]
    costs = {}
    if args.input_json:
        with open(args.input_json, encoding='utf-8') as f:
            tests = [t for t in json.load(f) if t['id'] in set(ids)]
    else:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, '.env'))
        from services.supabase_factory import SupabaseFactory, get_supabase_admin
        from scripts.audit_test_quality import load_tests
        if not SupabaseFactory.is_initialized():
            SupabaseFactory.initialize()
        db = get_supabase_admin()
        tests = load_tests(db, None, ids, True, None)
        costs = arm_costs(db, recs)
    reviews = []
    if args.reviews:
        for p in sorted(glob.glob(os.path.join(args.reviews, 'review_*.json'))):
            with open(p, encoding='utf-8') as f:
                reviews += json.load(f)
    text = score(recs, tests, reviews, costs)
    out = args.out or os.path.join(ROOT, 'data', 'test_quality', 'experiments', args.tags[0], 'summary.md')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
