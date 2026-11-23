"""Recompute the draft §5.3 level range under variants from stored per-band counts.
Usage: python3 -I variants.py SCRATCH RUN.json [RUN2.json ...]"""
import json
import math
import os
import sys
from collections import Counter

SCR = sys.argv[1]
sys.path.insert(0, os.path.join(SCR, 'placement', 'sim'))
sys.argv_saved = sys.argv
import pool as P  # noqa: E402

DC = {}
for lang in ('zh', 'ja'):
    words, _ = P.load_pool(SCR, lang)
    nlev = P.NLEV[lang]
    F = [[0] * 7 for _ in range(nlev)]
    for w in words:
        if w['lev']:
            F[w['lev'] - 1][w['band'] - 1] += 1
    D, acc = [], [0] * 7
    for j in range(nlev):
        acc = [a + f for a, f in zip(acc, F[j])]
        D.append(list(acc))
    DC[lang] = (D, [sum(1 for w in words if w['band'] == b) for b in range(1, 8)])


def bands(Ns, cnts):
    Ks, Vs = [], []
    for Nh, (n, c, w) in zip(Ns, cnts):
        K = c / n - w / (3.0 * n)
        pc, pw = (c + .5) / (n + 1.5), (w + .5) / (n + 1.5)
        Vs.append((pc * (1 - pc) + pw * (1 - pw) / 9.0 + 2.0 / 3.0 * pc * pw) / n * max(0.0, 1 - n / Nh))
        Ks.append(K)
    return Ks, Vs


def rng_(D, Ks, Vs, z):
    lows, ups, pts = [], [], []
    for row in D:
        M = sum(row)
        S = sum(d * k for d, k in zip(row, Ks)) / M
        V = (sum(d * d * v for d, v in zip(row, Vs)) +
             sum(d * min(1, max(0, k)) * (1 - min(1, max(0, k))) for d, k in zip(row, Ks))) / M ** 2
        sd = math.sqrt(V)
        lows.append(S - z * sd >= 0.8)
        ups.append(S + z * sd >= 0.8)
        pts.append(S >= 0.8)

    def lead(f):
        k = 0
        for x in f:
            if not x:
                break
            k += 1
        return k
    return lead(lows), lead(ups), lead(pts)


def pc(x):
    return f'{100 * x:.0f}%'


for f in sys.argv[2:]:
    d = json.load(open(f))
    print(f'\n### {os.path.basename(f)} ropt={d.get("ropt")} extra={d["extra"]}')
    print('| lang | z | lower=0 (all) | lower=0 among true ≥2 | range contains truth | copy k / a–b / at most / not yet | point ±1 non-beginners (true ≥1) | items | m+r MAE % pool | m+r 95% half-width % pool |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for lang in ('zh', 'ja'):
        D, Ns = DC[lang]
        rs = [r for r in d['rows'] if r['lang'] == lang]
        N = rs[0]['N']
        for z in (1.96, 1.645):
            lo0 = lo0b = cont = 0
            nb = 0
            cases = Counter()
            pt1 = pt1n = 0
            for r in rs:
                x = r['stop']
                Ks, Vs = bands(Ns, x['cr'])
                lo, up, pt = rng_(D, Ks, Vs, z)
                t = x['mr']['place_true']
                lo0 += lo == 0
                if t >= 2:
                    nb += 1
                    lo0b += lo == 0
                cont += lo <= t <= up
                cases['not yet' if up == 0 else ('at most' if lo == 0 else ('k' if lo == up else 'a-b'))] += 1
                if t >= 1:
                    pt1n += 1
                    pt1 += abs(pt - t) <= 1
            n = len(rs)
            items = sum(r['stop']['items'] for r in rs) / n
            mae = sum(abs(r['stop']['mr']['T'] - r['stop']['mr']['truth']) for r in rs) / n / N
            hw = sum(1.96 * r['stop']['mr']['SD'] for r in rs) / n / N
            print(f"| {lang} | {z} | {pc(lo0 / n)} | {pc(lo0b / nb)} | {pc(cont / n)} | "
                  f"{' / '.join(pc(cases[c] / n) for c in ('k', 'a-b', 'at most', 'not yet'))} | {pc(pt1 / pt1n)} | "
                  f"{items:.1f} | {100 * mae:.1f} | ±{100 * hw:.1f} |")
