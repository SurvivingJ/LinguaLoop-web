"""Psychometric review of the draft placement design (TASK-1073 review stage). Standard library only.

Re-implements the DRAFT's exact v1 rules (draft-design.md §5.1, §5.3, §6, §7) on top of the simulation stage's learner
model and word pools (placement/sim/sim.py, pool.py; imported, not modified) and measures what the draft did not:
  - the displayed 95% level range of §5.3 (lower/upper, copy case), not only the point placement;
  - 95% coverage and bias at the draft's stop (continuous check after each word from 40 items, cap 60);
  - ADR-051 labels a placement alone receives (incl. 'too uncertain');
  - how often the §5.1 display guard binds on a placement-only sample;
  - per-band bias of K_b under response-adaptive allocation.
Every number is an ESTIMATE under the simulation stage's learner model.

Usage: python3 -I psy_sim.py SCRATCH OUT_JSON N_PER_POP [sim key=value ...]
"""
import json
import math
import os
import random
import sys
from multiprocessing import Pool

SCR, OUTJ, NPP = sys.argv[1], sys.argv[2], int(sys.argv[3])
EXTRA = [a for a in sys.argv[4:] if not a.startswith('r_')]
ROPT = dict(a[2:].split('=', 1) for a in sys.argv[4:] if a.startswith('r_'))
MIN_TOP = int(ROPT.get('min_top', 0))      # review variant: min meaning items in each of the 3 most common bands
SIMDIR = os.path.join(SCR, 'placement', 'sim')
sys.path.insert(0, SIMDIR)
sys.argv = ['sim.py', SCR, '/nonexistent', '1', 'review'] + EXTRA
import sim as S  # noqa: E402

Z = 1.959964
SD_RATIO = 0.12 / 1.6448536
EARLIEST, CAP = 40, 60
PROBE_RATE, MAX_PROBES = 0.25, 3


def band_stats(Ns, cnts):
    """ADR-051 per band: K, Var (Jeffreys, fpc). Returns T, SD, Ks, Vs."""
    T = var = 0.0
    Ks, Vs = [], []
    for Nh, (n, c, w) in zip(Ns, cnts):
        if n:
            K = c / n - w / (3.0 * n)
            pc, pw = (c + .5) / (n + 1.5), (w + .5) / (n + 1.5)
            v = (pc * (1 - pc) + pw * (1 - pw) / 9.0 + 2.0 / 3.0 * pc * pw) / n * max(0.0, 1 - n / Nh)
        else:
            K, v = 0.0, 0.25
        Ks.append(K)
        Vs.append(v)
        T += Nh * K
        var += Nh * Nh * v
    return T, math.sqrt(var), Ks, Vs


def label(T, SD, N, cnts):
    lo, hi = max(0.0, T - Z * SD), min(float(N), max(T, 0.0) + Z * SD)
    if lo == 0:
        return lo, hi, 'fewer_than'
    rel = Z * SD / max(T, 0.10 * N)
    mn = min(c[0] for c in cnts)
    if rel <= 0.15 and mn >= 30:
        return lo, hi, 'good'
    if rel <= 0.30 and mn >= 20:
        return lo, hi, 'medium'
    if rel <= 0.50:
        return lo, hi, 'rough'
    if hi <= N / 2:
        return lo, hi, 'fewer_than'
    return lo, hi, 'too_uncertain'


def level_range(Dcum, Ks, Vs):
    """Draft §5.3: S_l = sum_b D_{<=l,b} K_b / M_l; Var = [sum D^2 Var_b + sum D Kt(1-Kt)] / M^2;
    lower/upper = max l such that S_j -/+ 1.96 sd >= 0.80 for every j <= l. Also the point placement."""
    lows, ups, pts, S_all = [], [], [], []
    for row in Dcum:
        M = sum(row)
        S = sum(d * k for d, k in zip(row, Ks)) / M
        V = (sum(d * d * v for d, v in zip(row, Vs)) + sum(d * min(1, max(0, k)) * (1 - min(1, max(0, k)))
                                                             for d, k in zip(row, Ks))) / (M * M)
        sd = math.sqrt(V)
        lows.append(S - Z * sd >= 0.80)
        ups.append(S + Z * sd >= 0.80)
        pts.append(S >= 0.80)
        S_all.append((round(S, 3), round(sd, 3)))

    def lead(flags):
        k = 0
        for f in flags:
            if f:
                k += 1
            else:
                break
        return k
    return lead(lows), lead(ups), lead(pts), S_all


def run(L, rng):
    W = S.WORLD[L.lang]
    strata = W['bands']
    Ns = [len(s) for s in strata]
    N = W['N']
    pools = [rng.sample(s, len(s)) for s in strata]
    cm = [[0, 0, 0] for _ in strata]
    cr = [[0, 0, 0] for _ in strata]
    st = dict(items=0, n_r=0, probes=0, probe_r=0, probe_w=0, probe_s=0)
    stop_snap = None

    def ask(i, kind):
        L._mknown = L.M[i]
        return S.ans(L, (L.M[i] if kind == 'm' else L.R[i]), rng, kind)

    def word(h):
        i = pools[h].pop()
        hr = W['words'][i]['has_r']
        o = ask(i, 'm')
        st['items'] += 1
        cm[h][0] += 1
        cm[h][1] += o == 'c'
        cm[h][2] += o == 'w'
        cr[h][0] += 1
        if o == 'c':
            if hr:
                o2 = ask(i, 'r')
                st['items'] += 1
                st['n_r'] += 1
                cr[h][1] += o2 == 'c'
                cr[h][2] += o2 == 'w'
            else:
                cr[h][1] += 1
        else:
            if not hr:
                cr[h][2] += o == 'w'
            elif st['probes'] < MAX_PROBES and rng.random() < PROBE_RATE:
                o3 = ask(i, 'r')
                st['items'] += 1
                st['probes'] += 1
                st['probe_' + {'c': 'r', 'w': 'w', 's': 's'}[o3]] += 1

    def snap(reason):
        Tm, SDm, Km, Vm = band_stats(Ns, cm)
        Tr, SDr, Kr, Vr = band_stats(Ns, cr)
        return dict(reason=reason, items=st['items'], Tm=Tm, SDm=SDm, Km=Km, Vm=Vm, Tr=Tr, SDr=SDr, Kr=Kr, Vr=Vr,
                    cm=[list(x) for x in cm], cr=[list(x) for x in cr], probes=dict(st))

    order = [h for h in range(7) if Ns[h]]
    for _ in range(2):
        for h in rng.sample(order, len(order)):
            if pools[h]:
                word(h)

    def red(cnts, h, Tvar):
        n, c, w = cnts[h]
        if not pools[h] or Tvar <= 0:
            return 0.0
        pc, pw = (c + .5) / (n + 1.5), (w + .5) / (n + 1.5)
        v1 = pc * (1 - pc) + pw * (1 - pw) / 9.0 + 2.0 / 3.0 * pc * pw
        return Ns[h] ** 2 * v1 * (1.0 / n - 1.0 / (n + 1)) / Tvar

    for h in (6, 5, 4):
        while MIN_TOP and cm[h][0] < MIN_TOP and pools[h]:
            word(h)
    reason = 'cap'
    while st['items'] < CAP:
        # draft §7: precision exit checked after each completed word, from the earliest stop on
        if st['items'] >= EARLIEST and stop_snap is None:
            _, SDm, _, _ = band_stats(Ns, cm)
            _, SDr, _, _ = band_stats(Ns, cr)
            if SDm <= SD_RATIO * N and SDr <= SD_RATIO * N:
                stop_snap = snap('precision')
        _, SDm, _, _ = band_stats(Ns, cm)
        _, SDr, _, _ = band_stats(Ns, cr)
        best, bh = -1.0, None
        for h in order:
            sc = red(cm, h, SDm * SDm) + red(cr, h, SDr * SDr)
            if sc > best:
                best, bh = sc, h
        if bh is None or best <= 0:
            reason = 'exhausted'
            break
        word(bh)
    cap_snap = snap(reason)
    return (stop_snap or cap_snap), cap_snap


def summarise(L, snp, W, Dcum):
    N = W['N']
    out = {}
    for x, T, SD, Ks, Vs, cn, truth, place_true in (
            ('m', snp['Tm'], snp['SDm'], snp['Km'], snp['Vm'], snp['cm'], L.T_m, L.place_m),
            ('mr', snp['Tr'], snp['SDr'], snp['Kr'], snp['Vr'], snp['cr'], L.T_mr, L.place_mr)):
        lo, hi, lab = label(T, SD, N, cn)
        lower, upper, point, Sall = level_range(Dcum, Ks, Vs)
        out[x] = dict(T=round(T, 1), SD=round(SD, 1), lo=round(lo, 1), hi=round(hi, 1), label=lab, truth=truth,
                      cover=lo <= truth <= hi, lower=lower, upper=upper, point=point, place_true=place_true,
                      S=Sall)
    out['guard_lo'] = out['mr']['lo'] > out['m']['lo']
    out['guard_hi'] = out['mr']['hi'] > out['m']['hi']
    # per-band: estimate vs the learner's true share of the band
    bands = []
    for b, idxs in enumerate(W['bands']):
        tm = sum(L.M[i] for i in idxs) / len(idxs)
        tr = sum(L.MR[i] for i in idxs) / len(idxs)
        bands.append([b, round(tm, 4), round(snp['Km'][b], 4), snp['cm'][b][0], round(tr, 4), round(snp['Kr'][b], 4)])
    out['bands'] = bands
    out['cm'], out['cr'] = snp['cm'], snp['cr']
    out['items'] = snp['items']
    out['reason'] = snp['reason']
    out['probes'] = snp['probes']
    return out


def job(args):
    lang, prof, skip_pop, idx = args
    L = S.make_learner(lang, prof, skip_pop, idx)
    W = S.WORLD[lang]
    rng = random.Random(S.seed_of(99, 'review', lang, prof, round(skip_pop * 100), idx))
    st, cp = run(L, rng)
    Dcum = W['Dcum']
    return dict(lang=lang, prof=prof, skip=skip_pop, idx=idx, tau=round(L.tau, 3), N=W['N'],
                stop=summarise(L, st, W, Dcum), cap=summarise(L, cp, W, Dcum))


def prep(lang):
    S.build_world(lang)
    W = S.WORLD[lang]
    if lang == 'ja' and ROPT.get('ja_full') == '1':     # review variant: every non-kana ja word has a reading item
        for w in W['words']:
            w['has_r'] = not w['kana_only']
    nlev = W['nlev']
    F = [[0] * 7 for _ in range(nlev)]
    for w in W['words']:
        if w['lev']:
            F[w['lev'] - 1][w['band'] - 1] += 1
    Dcum, acc = [], [0] * 7
    for j in range(nlev):
        acc = [a + f for a, f in zip(acc, F[j])]
        Dcum.append(list(acc))
    W['Dcum'] = Dcum


def main():
    pops = [p.split(':') for p in S.CFG['pops'].split(',')]
    for lang in sorted({p[0] for p in pops}):
        prep(lang)
    jobs = [(lang, prof, float(s), i) for lang, prof, s in pops for i in range(NPP)]
    with Pool(4) as pool:
        res = pool.map(job, jobs, chunksize=8)
    json.dump(dict(cfg=S.CFG, extra=EXTRA, ropt=ROPT, npp=NPP, rows=res), open(OUTJ, 'w'))
    print('done', len(res))


if __name__ == '__main__':
    main()
