"""Fit the simulation's learner model to the owner's real calibration answers (read-only export).
Model: known ~ sigmoid(s*(z-m)); if not known: skip w.p. q, else guess (correct w.p. 0.25).
Usage: python3 -I fit_owner.py SCRATCH"""
import json, math, sys
S = sys.argv[1]
rows = json.load(open(f'{S}/mock/data/dict.json', encoding='utf-8'))['dict']
Z = {(r[0], r[1]): r[4] for r in rows}
cal = json.load(open(f'{S}/mock/data/real_events.json', encoding='utf-8'))['cal']
def sig(x): return 1/(1+math.exp(-x))
for mode in ('definition', 'pronunciation'):
    data = []
    miss = 0
    for wl, dl, md, vid, band, ok, sk, date, rank in cal:
        if md != mode: continue
        z = Z.get((wl, vid))
        if z is None: miss += 1; continue
        data.append((z, 'c' if ok else ('s' if sk else 'w')))
    best = None
    for si in range(1, 61):
        s = si * 0.05
        for mi in range(0, 121):
            m = 1.0 + mi * 0.05
            for qi in range(0, 20):
                q = qi * 0.05
                ll = 0
                for z, o in data:
                    K = sig(s * (z - m))
                    p = K + (1-K)*(1-q)*.25 if o == 'c' else ((1-K)*q if o == 's' else (1-K)*(1-q)*.75)
                    ll += math.log(max(p, 1e-12))
                if best is None or ll > best[0]: best = (ll, s, m, q)
    ll, s, m, q = best
    # profile-likelihood 90% interval for slope (drop of 1.35)
    lo = hi = None
    for si in range(1, 61):
        s2 = si*0.05; bl = -1e9
        for mi in range(0, 121):
            m2 = 1.0 + mi*0.05
            for qi in range(0, 20):
                q2 = qi*0.05; l2 = 0
                for z, o in data:
                    K = sig(s2*(z-m2))
                    p = K + (1-K)*(1-q2)*.25 if o == 'c' else ((1-K)*q2 if o == 's' else (1-K)*(1-q2)*.75)
                    l2 += math.log(max(p, 1e-12))
                bl = max(bl, l2)
        if bl >= ll - 1.353:
            lo = s2 if lo is None else lo; hi = s2
    print(f'{mode}: n={len(data)} (no zipf {miss}); slope={s:.2f}/Zipf (90% profile {lo:.2f}-{hi:.2f}), '
          f'50%-known Zipf m={m:.2f}, skip-if-unknown q={q:.2f}, ll={ll:.1f}')
