#!/usr/bin/env python
"""Fit and cross-validate a language's jev score -> tier cut points (ADR-029).

  python scripts/fit_tier_thresholds.py --lang zh

Reads, from data/eval/jev_recalibration_2026-09-27/: <lang>_blind_manifest.json,
<lang>_gold_A.json, <lang>_gold_B.json (two blind readers) and
<lang>_scores_stored.json (jev's raw 0-5 score per test), all produced by
scripts/build_tier_gold_sample.py plus the readers. No database or jev access.

A prediction "hits" when it equals either reader's tier. Cut points are fitted by
coordinate ascent (ties broken toward the middle of the optimal plateau, ties in
hits broken by distance) with a minimum band width, and compared with
round-half-up and with the best single uniform offset. 5-fold cross-validation
(6 repeats) and leave-one-out give the honest generalisation figure.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics as st

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 'data', 'eval', 'jev_recalibration_2026-09-27')
DEFAULT = [0.5, 1.5, 2.5, 3.5, 4.5]
MIN_BAND = 0.1
GRID = [x / 100 for x in range(20, 500, 2)]


def tier(score, cuts):
    return 1 + sum(score >= c for c in cuts)


class Data:
    def __init__(self, lang):
        load = lambda n: json.load(open(os.path.join(D, f'{lang}_{n}.json'), encoding='utf-8'))  # noqa: E731
        mani, a, b, sc = load('blind_manifest'), load('gold_A'), load('gold_B'), load('scores_stored')
        self.ids = list(mani.values())
        self.ga = {mani[k]: a[k]['tier'] for k in mani}
        self.gb = {mani[k]: b[k]['tier'] for k in mani}
        self.sc = {i: sc[i]['score'] for i in self.ids}

    def hit(self, i, cuts):
        return tier(self.sc[i], cuts) in (self.ga[i], self.gb[i])

    def dist(self, i, cuts):
        t = tier(self.sc[i], cuts)
        return min(abs(t - self.ga[i]), abs(t - self.gb[i]))

    def objective(self, sub, cuts):
        return sum(self.hit(i, cuts) for i in sub) - 0.01 * sum(self.dist(i, cuts) for i in sub)

    def fit_offset(self, sub):
        """Best single uniform shift of round-half-up (one parameter)."""
        best, plateau = None, []
        for o in (x / 100 for x in range(-150, 51, 5)):
            cuts = [c + o for c in DEFAULT]
            h = self.objective(sub, cuts)
            if best is None or h > best + 1e-9:
                best, plateau = h, [o]
            elif abs(h - best) < 1e-9:
                plateau.append(o)
        return [round(c + st.median(plateau), 2) for c in DEFAULT]

    def fit(self, sub):
        cuts = DEFAULT[:]
        for _ in range(6):
            for k in range(5):
                lo = cuts[k - 1] + MIN_BAND if k else 0.0
                hi = cuts[k + 1] - MIN_BAND if k < 4 else 5.0
                best, plateau = None, []
                for g in GRID:
                    if not lo <= g <= hi:
                        continue
                    t = cuts[:]
                    t[k] = g
                    s = self.objective(sub, t)
                    if best is None or s > best + 1e-9:
                        best, plateau = s, [g]
                    elif abs(s - best) < 1e-9:
                        plateau.append(g)
                if plateau:
                    cuts[k] = round(st.median(plateau), 2)
        return cuts


def stats(d, cuts):
    gm = {i: (d.ga[i] + d.gb[i]) / 2 for i in d.ids}
    return (sum(d.hit(i, cuts) for i in d.ids),
            st.mean(abs(tier(d.sc[i], cuts) - gm[i]) for i in d.ids),
            st.mean(tier(d.sc[i], cuts) - gm[i] for i in d.ids))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', required=True)
    args = ap.parse_args()
    d = Data(args.lang)
    n = len(d.ids)

    agree = sum(d.ga[i] == d.gb[i] for i in d.ids)
    within = sum(abs(d.ga[i] - d.gb[i]) <= 1 for i in d.ids)
    print(f'{args.lang}: {n} items; readers agree exactly {agree}/{n}, within 1 tier {within}/{n}')
    for name, g in (('A', d.ga), ('B', d.gb)):
        print(f'  reader {name} tier counts:', {t: sum(v == t for v in g.values()) for t in range(1, 7)})

    print('\nround-half-up      hits %d/%d  MAE %.3f  bias %+.3f' % ((stats(d, DEFAULT)[0], n) + stats(d, DEFAULT)[1:]))
    offs = []
    for o in [x / 20 for x in range(-30, 11)]:
        cuts = [c - o for c in DEFAULT]
        offs.append((stats(d, cuts)[0], o))
    best_hits, best_off = max(offs)
    print(f'best uniform offset ({best_off:+.2f})  hits {best_hits}/{n}')

    cuts = d.fit(d.ids)
    h, mae, bias = stats(d, cuts)
    print(f'fitted cuts {cuts}  hits {h}/{n}  MAE {mae:.3f}  bias {bias:+.3f}')
    print('  (expected-tier scale: %s)' % [round(c + 1, 2) for c in cuts])

    ocuts = d.fit_offset(d.ids)
    print(f'uniform-offset model {ocuts}  hits {stats(d, ocuts)[0]}/{n}')

    def cv(fitter):
        rng = random.Random(3)
        out = []
        for _ in range(6):
            order = d.ids[:]
            rng.shuffle(order)
            h = 0
            for f in (order[k::5] for k in range(5)):
                c = fitter([j for j in d.ids if j not in f])
                h += sum(d.hit(i, c) for i in f)
            out.append(h)
        return st.mean(out)

    loo = sum(d.hit(i, d.fit([j for j in d.ids if j != i])) for i in d.ids)
    cv_fit, cv_off = cv(d.fit), cv(d.fit_offset)
    base = stats(d, DEFAULT)[0]
    print(f'\ncross-validated hits (5-fold x6):  round-half-up {base}  '
          f'uniform offset {cv_off:.1f}  fitted cuts {cv_fit:.1f}   (fitted LOO {loo})')


if __name__ == '__main__':
    main()
