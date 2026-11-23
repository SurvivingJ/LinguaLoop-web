"""PQ3 answered by the owner (2026-11-18): zh reading foils may be tone variants that use only existing syllable+tone
pairs. Simulates the proposed zh reading item (key K, a tone variant K' of the key, a cached segmental foil F, a tone
variant F' of F) inside D3S with the owner's length (cap 60, precision exit from 40), on the simulation stage's learner
model and real pool (sim.py/pool.py imported, not modified), with an added tone state per word. ESTIMATES only.

Estimators per band (n words sampled; meaning answer then reading answer):
  full  (meaning + reading with tones):  Y = +1 meaning right & K;  -1 meaning right & K';  else 0
  syll  (meaning + pinyin, tones aside):  Y = +1 meaning right & (K or K');  -1 meaning right & (F or F');  else 0
  old   (ADR-058 pair estimator applied to the new items): c/n - w/(3n), w = any wrong reading after a right meaning
Variance (all three): Jeffreys-smoothed multinomial Var(Y) = p+ + p- - (p+ - p-)^2 [old: ADR-051 form], / n, x fpc.
Usage: python3 -I tone_sim.py SCRATCH OUT_TXT N_PER_POP [t_partial=0.5] [theta=lo,hi]
"""
import math, os, random, sys, json
from multiprocessing import Pool
SCR, OUTT, NPP = sys.argv[1], sys.argv[2], int(sys.argv[3])
OPT = dict(a.split('=', 1) for a in sys.argv[4:])
T_PARTIAL = float(OPT.get('t_partial', 0.5))        # P(K | syllables known, tones not) ; 0.5 = no partial tone memory
THETA = tuple(float(x) for x in OPT.get('theta', '0.5,0.95').split(','))
SM = float(OPT.get('smooth', 0.5))              # pseudo-count per category for the +1/-1 estimators
sys.path.insert(0, os.path.join(SCR, 'placement', 'sim'))
sys.argv = ['sim.py', SCR, '/nonexistent', '1', 'tone']
import sim as S  # noqa: E402
Z95, Z90 = 1.959964, 1.6448536
CAP, EARLIEST, H = 60, 40, 0.12
WM = S.T_MEAS

def var_pm(n, a, b):
    p1, p2 = (a + SM) / (n + 3 * SM), (b + SM) / (n + 3 * SM)
    return p1 + p2 - (p1 - p2) ** 2

def var_old(n, c, w):
    pc, pw = (c + .5) / (n + 1.5), (w + .5) / (n + 1.5)
    return pc * (1 - pc) + pw * (1 - pw) / 9.0 + 2.0 / 3.0 * pc * pw

def total(Ns, cnts, kind):
    T = var = 0.0
    for Nh, (n, a, b) in zip(Ns, cnts):
        if not Nh: continue
        if n:
            if kind == 'old':
                K, v = a / n - b / (3.0 * n), var_old(n, a, b)
            else:
                K, v = (a - b) / n, var_pm(n, a, b)
            v = v / n * max(0.0, 1 - n / Nh)
        else:
            K, v = 0.0, 0.25
        T += Nh * K; var += Nh * Nh * v
    return T, math.sqrt(var)

def job(args):
    prof, skip_pop, idx = args
    W = S.WORLD['zh']; words = W['words']
    L = S.make_learner('zh', prof, skip_pop, idx)
    rng = random.Random(S.seed_of(77, prof, round(skip_pop * 100), idx))
    theta = rng.uniform(*THETA)
    TN = bytearray(W['N'])
    for i, w in enumerate(words):
        if L.R[i]:
            TN[i] = 1 if rng.random() < theta + (1 - theta) * S.sig(L.a * (w['z'] - L.tau) - 1.5) else 0
    T_full = sum(1 for i in range(W['N']) if L.M[i] and L.R[i] and (TN[i] or not words[i]['has_r']))
    T_syll = L.T_mr; T_m = L.T_m
    strata = W['bands']; Ns = [len(s) for s in strata]
    pools = [rng.sample(s, len(s)) for s in strata]
    cm = [[0, 0, 0] for _ in strata]; cf = [[0, 0, 0] for _ in strata]
    cs = [[0, 0, 0] for _ in strata]; co = [[0, 0, 0] for _ in strata]
    st = dict(n=0, nr=0, t=0.0, te=0.0)
    def ans_m(i):
        if L.M[i]: return 'c'
        if rng.random() < L.skip: return 's'
        return 'c' if rng.random() < 0.25 else 'w'
    def ans_r(i):
        if L.R[i] and TN[i]: return 'K'
        if L.R[i]: return 'K' if rng.random() < T_PARTIAL else "K'"
        if rng.random() < L.skip: return 's'
        return rng.choice(['K', "K'", 'F', "F'"])
    def item(h):
        i = pools[h].pop(); hr = words[i]['has_r']
        o = ans_m(i); st['n'] += 1; st['t'] += WM['m'][o]; st['te'] += 6.57
        cm[h][0] += 1; cm[h][1] += o == 'c'; cm[h][2] += o == 'w'
        for c in (cf, cs, co): c[h][0] += 1
        if o == 'c':
            if hr:
                r = ans_r(i); st['n'] += 1; st['nr'] += 1; st['te'] += 7.50
                st['t'] += WM['r']['c' if r == 'K' else ('s' if r == 's' else 'w')]
                cf[h][1] += r == 'K'; cf[h][2] += r == "K'"
                cs[h][1] += r in ('K', "K'"); cs[h][2] += r in ('F', "F'")
                co[h][1] += r == 'K'; co[h][2] += r in ("K'", 'F', "F'")
            else:
                for c in (cf, cs, co): c[h][1] += 1
        elif o == 'w' and not hr:
            cf[h][2] += 0; cs[h][2] += 0; co[h][2] += 1
    order = [h for h in range(len(strata)) if Ns[h]]
    for _ in range(2):
        for h in rng.sample(order, len(order)):
            if pools[h]: item(h)
    def red_m(h, Tv):
        n, c, w = cm[h]
        return Ns[h] ** 2 * var_old(n, c, w) * (1 / n - 1 / (n + 1)) / Tv if pools[h] and Tv > 0 else 0.0
    def red_f(h, Tv):
        n, a, b = cf[h]
        return Ns[h] ** 2 * var_pm(n, a, b) * (1 / n - 1 / (n + 1)) / Tv if pools[h] and Tv > 0 else 0.0
    stop = None
    while st['n'] < CAP:
        Tm, SDm = total(Ns, cm, 'old'); Tf, SDf = total(Ns, cf, 'pm')
        if st['n'] >= EARLIEST and SDm <= H / Z90 * W['N'] and SDf <= H / Z90 * W['N']:
            stop = 'precision'; break
        best, bh = -1.0, None
        for h in order:
            sc = red_m(h, SDm * SDm) + red_f(h, SDf * SDf)
            if sc > best: best, bh = sc, h
        if bh is None or best <= 0: stop = 'exhausted'; break
        item(bh)
    N = W['N']
    out = dict(prof=prof, skip=skip_pop, tau=L.tau, theta=theta, N=N, n=st['n'], nr=st['nr'], minutes=st['te'] / 60, minutes_lat=st['t'] / 60,
               early=stop == 'precision', T_m=T_m, T_full=T_full, T_syll=T_syll)
    for key, c, kind, truth in (('m', cm, 'old', T_m), ('full', cf, 'pm', T_full), ('syll', cs, 'pm', T_syll),
                                ('old', co, 'old', T_full)):
        T, SD = total(Ns, c, kind)
        lo, hi = max(0.0, T - Z95 * SD), min(float(N), max(T, 0.0) + Z95 * SD)
        out[key] = dict(T=T, hw=Z95 * SD, cover=lo <= truth <= hi, err=T - truth)
    return out

def main():
    S.build_world('zh')
    jobs = [(p, s, i) for p in ('E', 'J') for s in (0.3, 0.7) for i in range(NPP)]
    with Pool(4) as pool:
        res = pool.map(job, jobs, chunksize=4)
    m = lambda v: sum(v) / len(v)
    lines = [f"tone_sim: N per pop {NPP}, t_partial {T_PARTIAL}, theta {THETA}, smooth {SM}, cap {CAP}, exit from {EARLIEST}; minutes at E13 pace (6.57 s meaning, 7.50 s reading)",
             'pop | n | scored items | reading items | minutes | early | true m / full / syll (% pool) | bias % pool: m, full, syll, old-on-new | 95% hw % pool: m, full, syll | 95% cover: m, full, syll, old']
    groups = {}
    for r in res:
        for k in ((r['prof'], r['skip']), (r['prof'], '*'), ('*', '*')):
            groups.setdefault(k, []).append(r)
    for k in sorted(groups, key=str):
        g = groups[k]; N = g[0]['N']; pc = lambda x: 100 * x / N
        lines.append(f"zh·{k[0]} skip {k[1]} | {len(g)} | {m([r['n'] for r in g]):.1f} | {m([r['nr'] for r in g]):.1f} | "
                     f"{m([r['minutes'] for r in g]):.1f} | {100*m([r['early'] for r in g]):.0f}% | "
                     f"{pc(m([r['T_m'] for r in g])):.1f} / {pc(m([r['T_full'] for r in g])):.1f} / {pc(m([r['T_syll'] for r in g])):.1f} | "
                     + ', '.join(f"{pc(m([r[e]['err'] for r in g])):+.1f}" for e in ('m', 'full', 'syll', 'old')) + ' | '
                     + ', '.join(f"±{pc(m([r[e]['hw'] for r in g])):.1f}" for e in ('m', 'full', 'syll')) + ' | '
                     + ', '.join(f"{100*m([r[e]['cover'] for r in g]):.0f}%" for e in ('m', 'full', 'syll', 'old')))
    open(OUTT, 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines))

if __name__ == '__main__':
    main()
