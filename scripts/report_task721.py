"""Compare the TASK-721 before/after arms.

Consumes the sample JSONs written by `generate_question_sample.py` and the
results JSONs written by `measure_judge_flag_rate.py`, and prints the tables the
task's acceptance criterion asks for.

WHY DISTRACTOR-LEVEL NUMBERS ARE REPORTED ALONGSIDE THE REJECT RATE
-------------------------------------------------------------------
Under the current judge the baseline reject rate is a floor: the 2026-08-16
analysis measured zh 2% / en 4% / ja 6% once every language was on gemini. At
n = 60 questions per language that is 1-4 rejects, and the 95% interval on 2/60
runs from roughly 0% to 11%. A REDUCTION in reject rate is therefore not
detectable at this sample size, and any claim of one would be noise.

What IS detectable is (a) an increase -- the direction that actually blocks
activation, and the one TASK-717's v5 rows failed on -- and (b) movement in the
full 1-5 rating distribution over ~180 distractors per language per arm, which
has three times the n and does not throw away everything above the reject cut.
So the mean rating and the 4-vs-5 split are the sensitive signal here; the
reject rate is the decision gate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from measure_judge_flag_rate import wilson  # noqa: E402

LANG_NAME = {1: 'zh', 2: 'en', 3: 'ja'}
TYPES = ('literal_detail', 'supporting_detail', 'main_idea',
         'inference', 'author_purpose', 'vocabulary_context')


def load_results(paths: list[str]) -> list[dict]:
    out = []
    for p in paths:
        with open(p, encoding='utf-8') as fh:
            out += json.load(fh)
    return out


def summarise(results: list[dict]) -> dict:
    """lang -> stats. One entry per judged question."""
    by_lang: dict[int, dict] = defaultdict(
        lambda: {'q': 0, 'reject': 0, 'flag': 0, 'err': 0,
                 'ratings': Counter(), 'by_type': defaultdict(lambda: [0, 0])})
    for r in results:
        s = by_lang[r['lang']]
        if not r.get('ok'):
            s['err'] += 1
            continue
        s['q'] += 1
        s['ratings'].update(r['ratings'])
        worst = min(r['ratings']) if r['ratings'] else 5
        tc = r.get('type_code') or '?'
        s['by_type'][tc][1] += 1
        if worst <= 2:
            s['reject'] += 1
            s['by_type'][tc][0] += 1
        elif worst == 3:
            s['flag'] += 1
    return by_lang


def mean_rating(c: Counter) -> float:
    n = sum(c.values())
    return sum(k * v for k, v in c.items()) / n if n else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--before', nargs='+', required=True, help='results JSON(s)')
    ap.add_argument('--after', nargs='+', required=True)
    ap.add_argument('--before-sample')
    ap.add_argument('--after-sample')
    args = ap.parse_args()

    arms = {'before': summarise(load_results(args.before)),
            'after': summarise(load_results(args.after))}

    if args.before_sample and args.after_sample:
        print('GENERATION YIELD (questions produced / 60 cells per language)')
        print(f'{"lang":<6} {"before":>8} {"after":>8}')
        for name, path in (('before', args.before_sample), ('after', args.after_sample)):
            with open(path, encoding='utf-8') as fh:
                arms.setdefault('_yield', {})[name] = Counter(
                    r['lang'] for r in json.load(fh))
        for lid in (1, 2, 3):
            y = arms['_yield']
            print(f'{LANG_NAME[lid]:<6} {y["before"].get(lid, 0):>8} '
                  f'{y["after"].get(lid, 0):>8}')
        print()

    print('QUESTION-LEVEL REJECT RATE  (worst distractor rated <= 2)')
    print(f'{"lang":<6} {"before":>16} {"after":>16}   {"delta":>8}')
    for lid in (1, 2, 3):
        cells = []
        for arm in ('before', 'after'):
            s = arms[arm][lid]
            n, k = s['q'], s['reject']
            lo, hi = wilson(k, n) if n else (0, 0)
            cells.append((k, n, lo, hi))
        (kb, nb, lb, hb), (ka, na, la, ha) = cells
        db = (ka / na - kb / nb) * 100 if nb and na else 0.0
        print(f'{LANG_NAME[lid]:<6} '
              f'{kb:>3}/{nb:<3} {kb / nb * 100 if nb else 0:5.1f}% '
              f'{ka:>3}/{na:<3} {ka / na * 100 if na else 0:5.1f}%   {db:+7.1f}pp')
        print(f'{"":6}   95% CI {lb * 100:4.1f}-{hb * 100:4.1f}%'
              f'      95% CI {la * 100:4.1f}-{ha * 100:4.1f}%')

    print('\nREVIEW-FLAG RATE  (worst distractor rated 3)')
    print(f'{"lang":<6} {"before":>12} {"after":>12}')
    for lid in (1, 2, 3):
        b, a = arms['before'][lid], arms['after'][lid]
        print(f'{LANG_NAME[lid]:<6} {b["flag"]:>4}/{b["q"]:<6} {a["flag"]:>4}/{a["q"]:<6}')

    print('\nDISTRACTOR-LEVEL RATING DISTRIBUTION  (the sensitive signal)')
    print(f'{"lang":<5} {"arm":<7} {"1":>4} {"2":>4} {"3":>4} {"4":>4} {"5":>4} '
          f'{"n":>5} {"mean":>6}')
    for lid in (1, 2, 3):
        for arm in ('before', 'after'):
            c = arms[arm][lid]['ratings']
            n = sum(c.values())
            print(f'{LANG_NAME[lid]:<5} {arm:<7} '
                  + ' '.join(f'{c.get(i, 0):>4}' for i in (1, 2, 3, 4, 5))
                  + f' {n:>5} {mean_rating(c):>6.3f}')

    print('\nREJECTS BY QUESTION TYPE  (before -> after)')
    hdr = f'{"type":<22}' + ''.join(f'{LANG_NAME[l]:>12}' for l in (1, 2, 3))
    print(hdr)
    for tc in TYPES:
        row = f'{tc:<22}'
        for lid in (1, 2, 3):
            b = arms['before'][lid]['by_type'].get(tc, [0, 0])
            a = arms['after'][lid]['by_type'].get(tc, [0, 0])
            row += f'{b[0]}/{b[1]}->{a[0]}/{a[1]:<4}'.rjust(12)
        print(row)

    errs = {arm: sum(arms[arm][l]['err'] for l in (1, 2, 3)) for arm in ('before', 'after')}
    if any(errs.values()):
        print(f'\n[warn] judge call errors: {errs}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
