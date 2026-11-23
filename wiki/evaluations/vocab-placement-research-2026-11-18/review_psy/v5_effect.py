"""Observed-scale list effect (V5) in the simulation's learner model: within-band log-odds of a correct meaning answer,
on-list vs off-list words, for 'base' and 'gamma25'. ESTIMATE. Usage: python3 -I v5_effect.py SCRATCH gamma_max"""
import math, os, sys
SCR, GM = sys.argv[1], sys.argv[2]
sys.path.insert(0, SCR + '/placement/sim')
sys.argv = ['sim.py', SCR, '/nonexistent', '1', 'x', 'gamma_max=' + GM]
import sim as S
for lang, profs in (('zh', ('E', 'J')), ('ja', ('E', 'Z'))):
    S.build_world(lang); W = S.WORLD[lang]
    num = den = 0.0
    for prof in profs:
        for sk in (0.3, 0.7):
            for i in range(150):
                L = S.make_learner(lang, prof, sk, i)
                g = (1 - L.skip) / 4
                for b in range(1, 8):
                    on = [j for j, w in enumerate(W['words']) if w['band'] == b and w['lev']]
                    off = [j for j, w in enumerate(W['words']) if w['band'] == b and not w['lev']]
                    if len(on) < 20 or len(off) < 20: continue
                    p1 = sum(L.M[j] + (1 - L.M[j]) * g for j in on) / len(on)
                    p0 = sum(L.M[j] + (1 - L.M[j]) * g for j in off) / len(off)
                    p1 = min(max(p1, 0.01), 0.99); p0 = min(max(p0, 0.01), 0.99)
                    wgt = 1.0 / (1 / (p1 * (1 - p1)) + 1 / (p0 * (1 - p0)))   # inverse-variance (Woolf) weight
                    num += wgt * (math.log(p1 / (1 - p1)) - math.log(p0 / (1 - p0)))
                    den += wgt
    print(f'gamma_max={GM} {lang}: within-band, within-learner observed log-odds list effect (Woolf-weighted) = {num / den:.2f}')
