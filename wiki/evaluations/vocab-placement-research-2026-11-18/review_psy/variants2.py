"""Candidate correction for the §5.3 lower bound: monotone (frequency-ordered) pooling. Under the assumption that the
known share does not fall as words get more common, a lower bound for the pooled bands j..b is a lower bound for band b.
LB_b = max_j [K(j..b) - z1*SD(j..b)]; lower = max l with sum_b D LB_b / M - z1*sqrt(sum D Kt(1-Kt))/M >= 0.8 for all j<=l.
Also the draft's upper. ESTIMATE under the sim's learner model. Usage: python3 -I variants2.py SCRATCH RUN.json"""
import json, math, os, sys
from collections import Counter
SCR = sys.argv[1]
sys.path.insert(0, os.path.join(SCR, 'placement', 'review_psy'))
sys.argv = [sys.argv[0], SCR] + sys.argv[2:]
import variants as V   # reuses DC (frame list x band counts) and bands(); prints nothing without run files

def pooled(cnts, j, b, Ns):
    n = sum(cnts[h][0] for h in range(j, b + 1)); c = sum(cnts[h][1] for h in range(j, b + 1)); w = sum(cnts[h][2] for h in range(j, b + 1))
    K = c / n - w / (3.0 * n)
    pc, pw = (c + .5) / (n + 1.5), (w + .5) / (n + 1.5)
    Nt = sum(Ns[j:b + 1])
    v = (pc * (1 - pc) + pw * (1 - pw) / 9.0 + 2.0 / 3.0 * pc * pw) / n * max(0.0, 1 - n / Nt)
    return K, math.sqrt(v)

def lower_mono(D, Ns, cnts, z1):
    Ks, Vs = V.bands(Ns, cnts)
    LB = []
    for b in range(7):
        best = -9
        for j in range(b + 1):
            K, sd = pooled(cnts, j, b, Ns)
            best = max(best, K - z1 * sd)
        LB.append(min(1.0, best))
    k = 0
    for row in D:
        M = sum(row)
        s = sum(d * lb for d, lb in zip(row, LB)) / M
        bern = math.sqrt(sum(d * min(1, max(0, kk)) * (1 - min(1, max(0, kk))) for d, kk in zip(row, Ks))) / M
        if s - z1 * bern >= 0.8:
            k += 1
        else:
            break
    return k

for f in sys.argv[2:]:
    d = json.load(open(f))
    print(f'\n### monotone-pooled lower bound, {os.path.basename(f)}')
    print('| lang | z (one-sided) | lower ≥ 1 (all) | lower ≥ 1 among true ≥ 2 | lower ≤ truth (no over-claim) | lower within 1 of truth, true ≥ 2 |')
    print('|---|---|---|---|---|---|')
    for lang in ('zh', 'ja'):
        D, Ns = V.DC[lang]
        rs = [r for r in d['rows'] if r['lang'] == lang]
        for z1 in (1.645, 1.96):
            res = [(lower_mono(D, Ns, r['stop']['cr'], z1), r['stop']['mr']['place_true']) for r in rs]
            n = len(res); hi = [x for x in res if x[1] >= 2]
            print(f"| {lang} | {z1} | {100*sum(l >= 1 for l, t in res)/n:.0f}% | {100*sum(l >= 1 for l, t in hi)/len(hi):.0f}% | "
                  f"{100*sum(l <= t for l, t in res)/n:.0f}% | {100*sum(t - l <= 1 for l, t in hi)/len(hi):.0f}% |")
