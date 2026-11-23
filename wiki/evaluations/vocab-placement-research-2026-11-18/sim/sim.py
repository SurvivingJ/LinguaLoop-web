"""Vocabulary placement test simulation (TASK-1073 research stage). Standard library only.

Usage: python3 -I sim.py SCRATCH OUT_DIR N_LEARNERS RUN_NAME [key=value ...]

Synthetic learners (two traits: meaning and reading) take candidate placement designs over the REAL check pool
(live calibration_anchor_pool ids, Zipf from dict.json, subsampled to the frame sizes N_b) with exam levels from
HSK 3.0 (2025) / JLPT community lists. Every number this produces is an ESTIMATE from simulation.
"""
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool
from operator import mul

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # own scripts dir only (no data files there)
import pool as P  # noqa: E402

SCR, OUT, NL, RUN = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
CFG = dict(max_m=70, max_tot=90, designs='D0,D1,D1S,D1L,D2,D3,D4,D3S,D3L',
           pops='zh:E:0.3,zh:E:0.7,zh:J:0.3,zh:J:0.7,ja:E:0.3,ja:E:0.7,ja:Z:0.3,ja:Z:0.7',
           sig_eps=1.2, a_med=1.6, gamma_max=1.0, tau_lo=2.5, tau_hi=7.0, partial=0, seed=11)
for kv in sys.argv[5:]:
    k, v = kv.split('=', 1)
    CFG[k] = type(CFG[k])(v) if not isinstance(CFG[k], str) else v
Z90 = 1.6448536
THRESH = 0.80          # placement: leading levels whose cumulative known share >= 80%

# ---------------------------------------------------------------- timing (seconds per item)
# brief default: 6 s meaning, 5 s reading.  measured: live calibration_responses latency_ms means (ja, capped 30 s,
# by outcome; SQL in research-simulation.md) + 0.45 s auto-advance after a correct answer (static/js/pages/calibration.js:47)
# + an ASSUMED 1.5 s to read the key and tap on after a wrong answer or skip (not measured).
T_BRIEF = {'m': 6.0, 'r': 5.0}
T_MEAS = {'m': {'c': 4.59 + 0.45, 'w': 3.05 + 1.5, 's': 4.34 + 1.5},
          'r': {'c': 3.59 + 0.45, 'w': 3.70 + 1.5, 's': 7.12 + 1.5}}

# ---------------------------------------------------------------- learner profiles (ASSUMPTIONS, see the report)
PROFILES = {
    # pi: P(reading known | word learned) near the learner's frontier; rises to 1 for words well inside it.
    ('zh', 'E'): dict(l1='en', kappa=(0, 0), pi=(0.60, 0.90), nu=(0, 0), omega=(0.10, 0.40)),
    ('zh', 'J'): dict(l1='ja', kappa=(0.60, 0.95), pi=(0.60, 0.90), nu=(0.03, 0.15), omega=(0.10, 0.40)),
    ('ja', 'E'): dict(l1='en', kappa=(0.50, 0.85), pi=(0.75, 0.95), nu=(0, 0), omega=(0.05, 0.30)),
    ('ja', 'Z'): dict(l1='zh', kappa=(0.60, 0.95), pi=(0.70, 0.95), nu=(0.10, 0.35), omega=(0.05, 0.30)),
}


def cog_prob(lang, prof, w):
    """Probability that word w is a same-meaning cognate for this L1 (word property, fixed across learners)."""
    if lang == 'zh' and prof == 'J':
        return 0.55 if w['n'] >= 2 else 0.30
    if lang == 'ja' and prof == 'E':
        return 0.80 if w['kata_only'] else 0.0
    if lang == 'ja' and prof == 'Z':
        if w['kata_only']:
            return 0.20
        if w['han'] == 0:
            return 0.0
        if w['han'] == w['n'] and w['n'] >= 2:
            return 0.65
        return 0.45
    return 0.0


def seed_of(*parts):
    return zlib.crc32(repr(parts).encode())


def sig(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


# ---------------------------------------------------------------- per-language world (built once, shared by fork)
ZB_N = 76                                  # Zipf bins of 0.1: 0.0 .. 7.5
M_GRID = [1.5 + 0.15 * i for i in range(47)]
S_GRID = [0.7, 1.0, 1.35, 1.8]
F_GRID = [0.0, 0.15, 0.30, 0.45, 0.60]
FR_GRID = [0.0, 0.10, 0.20]
U_GRID = [0.70, 0.80, 0.90, 1.00]
WORLD = {}


def lognorm_w(vals, med, sd):
    w = [math.exp(-0.5 * ((math.log(v) - math.log(med)) / sd) ** 2) for v in vals]
    t = sum(w)
    return [x / t for x in w]


Q_M = [0.5 + 0.3 * i for i in range(25)]
Q_S = [0.7, 1.2, 1.8]
Q_F = [0.0, 0.2, 0.4, 0.6, 0.8]
Q_U = [0.85, 1.0]


def build_grid(kind):
    """kind 'm': (m, s, f, u=1); kind 'r': (m, s, f, u); kind 'q': rho = P(reading | meaning) curve."""
    pts = []
    if kind == 'q':
        for m in Q_M:
            for s in Q_S:
                for f in Q_F:
                    for u in Q_U:
                        pts.append((m, s, f, u))
    for m in (M_GRID if kind != 'q' else []):
        for s in S_GRID:
            for f in (F_GRID if kind == 'm' else FR_GRID):
                for u in ((1.0,) if kind == 'm' else U_GRID):
                    pts.append((m, s, f, u))
    ktab = []
    for zb in range(ZB_N):
        z = zb / 10.0
        ktab.append([f + (u - f) * sig(s * (z - m)) for (m, s, f, u) in pts])
    return pts, ktab


def hist_counts(words, sel):
    h = [0] * ZB_N
    for w in words:
        if sel(w):
            h[w['zb']] += 1
    return h


def ecount(ktab, h):
    n = len(ktab[0])
    e = [0.0] * n
    v = [0.0] * n
    for zb, c in enumerate(h):
        if c:
            row = ktab[zb]
            e = [a + c * k for a, k in zip(e, row)]
            v = [a + c * k * (1 - k) for a, k in zip(v, row)]
    return e, [a * a + b for a, b in zip(e, v)]


def build_world(lang):
    words, info = P.load_pool(SCR, lang)
    rng = random.Random(1000 + P.LANGID[lang])
    nlev = P.NLEV[lang]
    for w in words:
        w['zb'] = min(ZB_N - 1, max(0, int(round(w['z'] * 10))))
        w['eps'] = rng.gauss(0, CFG['sig_eps'])
    # exam-level residual (level beyond what frequency predicts), standardised; unlisted = nlev + 1
    xs = [w['z'] for w in words]
    ys = [w['lev'] if w['lev'] else nlev + 1 for w in words]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    res = [y - (my + b * (x - mx)) for x, y in zip(xs, ys)]
    sd = (sum(r * r for r in res) / len(res)) ** 0.5
    for w, r in zip(words, res):
        w['lres'] = r / sd
    cog = {}
    for (lg, prof) in PROFILES:
        if lg == lang:
            r2 = random.Random(2000 + P.LANGID[lang] + ord(prof))
            cog[prof] = bytearray(1 if r2.random() < cog_prob(lang, prof, w) else 0 for w in words)
    N = len(words)
    bands = [[i for i, w in enumerate(words) if w['band'] == bb] for bb in range(1, 8)]
    levs = [[i for i, w in enumerate(words) if w['lev'] == L] for L in range(0, nlev + 1)]   # 0 = unlisted
    zbin2 = {}                                   # 0.2-wide selection bins -> word indices
    for i, w in enumerate(words):
        zbin2.setdefault(int(w['z'] * 5), []).append(i)
    gm_pts, gm_k = build_grid('m')
    gr_pts, gr_k = build_grid('r')
    kana = [i for i, w in enumerate(words) if not w['has_r']]          # MR == M for these (no reading item)
    hm_all = hist_counts(words, lambda w: True)
    hm_nor = hist_counts(words, lambda w: not w['has_r'])
    hr_r = hist_counts(words, lambda w: w['has_r'])
    E_m, E2_m = ecount(gm_k, hm_all)
    E_mn, E2_mn = ecount(gm_k, hm_nor)
    E_r, E2_r = ecount(gr_k, hr_r)
    lev_m, lev_mn, lev_r = [], [], []
    for L in range(1, nlev + 1):
        lev_m.append(ecount(gm_k, hist_counts(words, lambda w, L=L: w['lev'] == L))[0])
        lev_mn.append(ecount(gm_k, hist_counts(words, lambda w, L=L: w['lev'] == L and not w['has_r']))[0])
        lev_r.append(ecount(gr_k, hist_counts(words, lambda w, L=L: w['lev'] == L and w['has_r']))[0])
    gq_pts, gq_k = build_grid('q')
    E_mh, E2_mh = ecount(gm_k, hr_r)
    hlev_r = [hist_counts(words, lambda w, L=L: w['lev'] == L and w['has_r']) for L in range(1, nlev + 1)]
    WORLD[lang] = dict(gq_pts=gq_pts, gq_k=gq_k, E_mh=E_mh, E2_mh=E2_mh, hist_r=hr_r, hlev_r=hlev_r,
                       words=words, info=info, N=N, nlev=nlev, cog=cog, bands=bands, levs=levs, zbin2=zbin2,
                       gm_pts=gm_pts, gm_k=gm_k, gr_pts=gr_pts, gr_k=gr_k, E_m=E_m, E2_m=E2_m, E_mn=E_mn, E2_mn=E2_mn,
                       E_r=E_r, E2_r=E2_r, lev_m=lev_m, lev_mn=lev_mn, lev_r=lev_r, kana=kana,
                       NB=[len(x) for x in bands], NL=[len(x) for x in levs])


def prior_m(l1):
    sw = lognorm_w(S_GRID, 1.15, 0.35)
    fw = [0.55, 0.30, 0.10, 0.04, 0.01] if l1 == 'en' else [0.2] * 5
    out = []
    for m in M_GRID:
        pm = -0.5 * ((m - 4.8) / 1.4) ** 2
        for si in range(len(S_GRID)):
            for fi in range(len(F_GRID)):
                out.append(pm + math.log(sw[si]) + math.log(fw[fi]))
    return out


def prior_r(l1):
    sw = lognorm_w(S_GRID, 1.15, 0.35)
    fw = [0.6, 0.3, 0.1] if l1 == 'en' else [0.4, 0.35, 0.25]
    uw = [0.15, 0.25, 0.30, 0.30]
    out = []
    for m in M_GRID:
        pm = -0.5 * ((m - 5.2) / 1.5) ** 2
        for si in range(len(S_GRID)):
            for fi in range(len(FR_GRID)):
                for ui in range(len(U_GRID)):
                    out.append(pm + math.log(sw[si]) + math.log(fw[fi]) + math.log(uw[ui]))
    return out


def prior_q(l1):
    sw = lognorm_w(Q_S, 1.15, 0.35)
    fw = [0.05, 0.10, 0.20, 0.35, 0.30] if l1 == 'en' else [0.30, 0.30, 0.20, 0.12, 0.08]
    uw = [0.3, 0.7]
    out = []
    for m in Q_M:
        pm = -0.5 * ((m - 4.5) / 2.0) ** 2
        for si in range(len(Q_S)):
            for fi in range(len(Q_F)):
                for ui in range(len(Q_U)):
                    out.append(pm + math.log(sw[si]) + math.log(fw[fi]) + math.log(uw[ui]))
    return out


# ---------------------------------------------------------------- learners
class Learner:
    pass


def make_learner(lang, prof, skip_pop, idx):
    W = WORLD[lang]
    words = W['words']
    pr = PROFILES[(lang, prof)]
    rng = random.Random(seed_of(CFG['seed'], lang, prof, round(skip_pop * 100), idx))
    L = Learner()
    L.lang, L.prof, L.l1 = lang, prof, pr['l1']
    L.tau = rng.uniform(CFG['tau_lo'], CFG['tau_hi'])
    L.a = math.exp(rng.gauss(math.log(CFG['a_med']), 0.2))
    L.gamma = rng.uniform(0, CFG['gamma_max'])
    L.skip = min(0.95, max(0.0, rng.gauss(skip_pop, 0.1)))
    L.kappa = rng.uniform(*pr['kappa'])
    L.pi = rng.uniform(*pr['pi'])
    L.nu = rng.uniform(*pr['nu'])
    L.omega = rng.uniform(*pr['omega'])
    cog = W['cog'][prof]
    M = bytearray(W['N'])
    R = bytearray(W['N'])
    for i, w in enumerate(words):
        f = rng.random() < sig(L.a * (w['z'] - L.tau) - (w['eps'] + L.gamma * w['lres']))
        c = (not f) and cog[i] and rng.random() < L.kappa
        m = f or c
        if not w['has_r']:
            r = m          # no reading item (kana-only ja words, or no stored pronunciation): "knows the word" == meaning
        elif f:
            r = rng.random() < L.pi + (1 - L.pi) * sig(L.a * (w['z'] - L.tau) - 1.0)
        elif c:
            r = rng.random() < L.nu
        else:              # reading an unknown word from its characters
            r = rng.random() < L.omega * sig(L.a * (w['z'] - L.tau) + 1.5)
        M[i] = 1 if m else 0
        R[i] = 1 if r else 0
    L.M, L.R = M, R
    L.MR = bytearray(1 if (M[i] and R[i]) else 0 for i in range(W['N']))
    L.T_m, L.T_mr = sum(M), sum(L.MR)
    L.cum_m, L.cum_mr = cum_shares_true(W, M), cum_shares_true(W, L.MR)
    L.place_m, L.place_mr = placement(L.cum_m), placement(L.cum_mr)
    return L


def cum_shares_true(W, X):
    out, k, n = [], 0, 0
    for L in range(1, W['nlev'] + 1):
        for i in W['levs'][L]:
            k += X[i]
            n += 1
        out.append(k / n if n else 0.0)
    return out


def placement(cum):
    p = 0
    for s in cum:
        if s >= THRESH:
            p += 1
        else:
            break
    return p


# ---------------------------------------------------------------- responses
def ans(L, known, rng, kind):
    if known:
        return 'c'
    if CFG['partial'] and kind == 'r' and L._mknown:      # sensitivity: partial reading knowledge
        if rng.random() < L.skip * 0.5:
            return 's'
        return 'c' if rng.random() < 0.40 else 'w'
    if rng.random() < L.skip:
        return 's'
    return 'c' if rng.random() < 0.25 else 'w'


CHECK = [15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90]


class Run:
    """Bookkeeping shared by all designs. Designs run to their cap; estimates are snapshotted at item-count
    checkpoints, so each snapshot equals a fixed-length run of that length and stopping rules can be applied later."""

    def __init__(self, L, rng):
        self.L, self.rng = L, rng
        self.n_m = self.n_r = 0
        self.t_brief = self.t_meas = 0.0
        self.cnt = {'s': 0, 'w': 0, 'c': 0}
        self.credit = []            # word indices credited "knows the word" by the design's own rule
        self.snaps = []
        self.next_ck = 0

    def ask(self, i, kind):
        L = self.L
        L._mknown = L.M[i]
        o = ans(L, (L.M[i] if kind == 'm' else L.R[i]), self.rng, kind)
        if kind == 'm':
            self.n_m += 1
        else:
            self.n_r += 1
        self.t_brief += T_BRIEF[kind]
        self.t_meas += T_MEAS[kind][o]
        self.cnt[o] += 1
        return o

    def g_hat(self):
        q = (self.cnt['s'] + 0.5) / (self.cnt['s'] + self.cnt['w'] * 4.0 / 3.0 + 1.0)
        return (1.0 - min(0.95, q)) / 4.0

    @property
    def n_tot(self):
        return self.n_m + self.n_r

    def maybe_snap(self, est, force=False):
        if (self.next_ck < len(CHECK) and self.n_tot >= CHECK[self.next_ck]) or force:
            while self.next_ck < len(CHECK) and self.n_tot >= CHECK[self.next_ck]:
                self.next_ck += 1
            if self.snaps and self.snaps[-1]['n'] == self.n_tot:
                return
            self.snaps.append(snapshot(self, *est()))


def snapshot(run, Tm, SDm, cum_m, Tmr=None, SDmr=None, cum_mr=None):
    L, W = run.L, WORLD[run.L.lang]
    lo, hi = interval(Tm, SDm, W['N'])
    s = dict(n=run.n_tot, n_m=run.n_m, n_r=run.n_r, tb=round(run.t_brief, 1), tm=round(run.t_meas, 1),
             Tm=round(Tm, 1), lo=round(lo, 1), hi=round(hi, 1), hw=round(Z90 * SDm, 1), pm=placement(cum_m),
             lem=round(sum(abs(a - b) for a, b in zip(cum_m, L.cum_m)) / len(cum_m), 4))
    if Tmr is not None:
        lo2, hi2 = interval(Tmr, SDmr, W['N'])
        s.update(Tr=round(Tmr, 1), rlo=round(lo2, 1), rhi=round(hi2, 1), rhw=round(Z90 * SDmr, 1), pr=placement(cum_mr),
                 ler=round(sum(abs(a - b) for a, b in zip(cum_mr, L.cum_mr)) / len(cum_mr), 4))
    cr = run.credit
    s['cr'] = len(cr)
    s['cr_nmr'] = sum(1 for i in cr if not L.MR[i])
    s['cr_nm'] = sum(1 for i in cr if not L.M[i])
    return s


# ---------------------------------------------------------------- design-based (stratified) estimation
def strat(Ns, cnts):
    """ADR-051 estimator per stratum: K = c/n - w/(3n); Jeffreys-smoothed multinomial variance with fpc."""
    T = var = 0.0
    Ks = []
    for Nh, (n, c, w) in zip(Ns, cnts):
        if Nh == 0:
            Ks.append(0.0)
            continue
        if n:
            K = c / n - w / (3.0 * n)
            pc, pw = (c + .5) / (n + 1.5), (w + .5) / (n + 1.5)
            v = (pc * (1 - pc) + pw * (1 - pw) / 9.0 + 2.0 / 3.0 * pc * pw) / n * max(0.0, 1 - n / Nh)
        else:
            K, v = 0.0, 0.25
        Ks.append(K)
        T += Nh * K
        var += Nh * Nh * v
    return T, math.sqrt(var), Ks


def interval(T, SD, N):
    return max(0.0, T - Z90 * SD), min(float(N), max(T, 0.0) + Z90 * SD)


def level_from_bands(W, Ks):
    """Section 2.8a of knowledge-report.tech.md: est_L = sum_b D_{L,b} K_b (cumulative levels pooled)."""
    out = []
    num = den = 0.0
    for L in range(1, W['nlev'] + 1):
        for i in W['levs'][L]:
            num += min(1.0, max(0.0, Ks[W['words'][i]['band'] - 1]))
            den += 1
        out.append(num / den if den else 0.0)
    return out


def design_fixed(L, rng):
    """D0: today's check - meaning items round-robin over the 7 bands (10 per band at 70), ADR-051 estimator."""
    W = WORLD[L.lang]
    run = Run(L, rng)
    cnts = [[0, 0, 0] for _ in range(7)]
    picks = [rng.sample(W['bands'][b], 10) for b in range(7)]

    def est():
        T, SD, Ks = strat(W['NB'], [tuple(x) for x in cnts])
        return T, SD, level_from_bands(W, Ks)

    for r in range(10):
        for b in rng.sample(range(7), 7):
            i = picks[b][r]
            o = run.ask(i, 'm')
            cnts[b][0] += 1
            cnts[b][1] += o == 'c'
            cnts[b][2] += o == 'w'
            if o == 'c':
                run.credit.append(i)
            run.maybe_snap(est)
    run.maybe_snap(est, force=True)
    return run.snaps


def design_strat(L, rng, reading, by_level):
    """D1S / D3S / D3L: adaptive stratified sampling. Strata = Zipf bands (or exam levels + unlisted).
    Warm-up 2 items per stratum, then the stratum whose next item most reduces the relative variance of the
    reported count(s). Reading (D3S/D3L) only after a correct meaning answer, on words that have a reading item."""
    W = WORLD[L.lang]
    run = Run(L, rng)
    strata = W['levs'] if by_level else W['bands']
    Ns = [len(s) for s in strata]
    pools = [rng.sample(s, len(s)) for s in strata]
    cm = [[0, 0, 0] for _ in strata]          # n, c, w (meaning)
    cr = [[0, 0, 0] for _ in strata]          # n, pair-correct, pair right-then-wrong (MR)
    cap = CFG['max_tot'] if reading else CFG['max_m']

    def cum(Ks):
        out, num, den = [], 0.0, 0.0
        for Lv in range(1, W['nlev'] + 1):
            num += Ns[Lv] * min(1.0, max(0.0, Ks[Lv]))
            den += Ns[Lv]
            out.append(num / den if den else 0.0)
        return out

    def est():
        Tm, SDm, Km = strat(Ns, [tuple(x) for x in cm])
        lv = cum if by_level else (lambda K: level_from_bands(W, K))
        if not reading:
            return Tm, SDm, lv(Km)
        Tr, SDr, Kr = strat(Ns, [tuple(x) for x in cr])
        return Tm, SDm, lv(Km), Tr, SDr, lv(Kr)

    def item(h):
        i = pools[h].pop()
        hr = W['words'][i]['has_r']
        o = run.ask(i, 'm')
        cm[h][0] += 1
        cm[h][1] += o == 'c'
        cm[h][2] += o == 'w'
        cr[h][0] += 1
        if o == 'c':
            if reading and hr:
                o2 = run.ask(i, 'r')
                cr[h][1] += o2 == 'c'
                cr[h][2] += o2 == 'w'
                if o2 == 'c':
                    run.credit.append(i)
            else:
                cr[h][1] += 1
                run.credit.append(i)
        elif not hr:
            cr[h][2] += o == 'w'          # no reading item: the pair outcome is the meaning outcome
        run.maybe_snap(est)

    order = [h for h in range(len(strata)) if Ns[h]]
    for _ in range(2):
        for h in rng.sample(order, len(order)):
            if pools[h]:
                item(h)

    def red(cnts, h, Tvar):
        n, c, w = cnts[h]
        if not pools[h] or Tvar <= 0:
            return 0.0
        pc, pw = (c + .5) / (n + 1.5), (w + .5) / (n + 1.5)
        v1 = pc * (1 - pc) + pw * (1 - pw) / 9.0 + 2.0 / 3.0 * pc * pw
        return Ns[h] ** 2 * v1 * (1.0 / n - 1.0 / (n + 1)) / Tvar

    def v1(cnts, h):
        n, c, w = cnts[h]
        pc, pw = (c + .5) / (n + 1.5), (w + .5) / (n + 1.5)
        return pc * (1 - pc) + pw * (1 - pw) / 9.0 + 2.0 / 3.0 * pc * pw

    def level_scores(cnts):
        # level strata only: weight cumulative levels by how close their share is to the 80% placement threshold
        sc = [0.0] * len(strata)
        num = var = den = 0.0
        for Lv in range(1, W['nlev'] + 1):
            n, c, w = cnts[Lv]
            K = (c / n - w / (3.0 * n)) if n else 0.0
            num += Ns[Lv] * min(1.0, max(0.0, K))
            var += Ns[Lv] ** 2 * (v1(cnts, Lv) / n if n else 0.25)
            den += Ns[Lv]
            C, VC = num / den, var / den ** 2
            wt = math.exp(-0.5 * (C - THRESH) ** 2 / VC)
            for h in range(1, Lv + 1):
                if pools[h] and cnts[h][0]:
                    nh = cnts[h][0]
                    sc[h] += wt * Ns[h] ** 2 * v1(cnts, h) * (1.0 / nh - 1.0 / (nh + 1)) / den ** 2 / VC
        return sc

    while run.n_tot < cap:
        _, SDm, _ = strat(Ns, [tuple(x) for x in cm])
        SDr = strat(Ns, [tuple(x) for x in cr])[1] if reading else 0.0
        lsc = level_scores(cm) if by_level else None
        lsr = level_scores(cr) if (by_level and reading) else None
        best, bh = -1.0, None
        for h in order:
            sc = red(cm, h, SDm * SDm) + (red(cr, h, SDr * SDr) if reading else 0.0)
            if by_level:
                sc += lsc[h] + (lsr[h] if reading else 0.0)
            if sc > best:
                best, bh = sc, h
        if bh is None or best <= 0:
            break
        item(bh)
    run.maybe_snap(est, force=True)
    return run.snaps


# ---------------------------------------------------------------- model-based (IRT-style) adaptive designs
class Post:
    def __init__(self, lp, ktab, E, E2, levE):
        self.lp, self.ktab, self.E, self.E2, self.levE = lp, ktab, E, E2, levE
        self.refresh()

    def refresh(self):
        mx = max(self.lp)
        self.w = [math.exp(x - mx) for x in self.lp]
        self.W = sum(self.w)
        self.ET = sum(map(mul, self.w, self.E)) / self.W
        self.VT = max(1e-9, sum(map(mul, self.w, self.E2)) / self.W - self.ET ** 2)
        self.wT = [a * b for a, b in zip(self.w, self.E)]

    def meanK(self, zb):
        return sum(map(mul, self.w, self.ktab[zb])) / self.W

    def mean_cov(self, zb):
        row = self.ktab[zb]
        ek = sum(map(mul, self.w, row)) / self.W
        return ek, sum(map(mul, self.wT, row)) / self.W - self.ET * ek

    def lev_sums(self, levE=None):
        out, acc = [], 0.0
        for e in (levE or self.levE):
            acc += sum(map(mul, self.w, e)) / self.W
            out.append(acc)
        return out


def design_irt(L, rng, rmode):
    """D1 (rmode None): meaning only.  D2 'all': reading after every meaning item.  D3 'cond': reading only after a
    correct meaning answer.  D4 'half': reading on every second word regardless of the meaning answer.
    Model: P(known | Zipf z) = f + (u - f) * sigmoid(s (z - m)); grid posterior per learner for the meaning curve and,
    for D2-D4, a 'knows meaning AND reading' curve fitted from reading answers that follow a correct meaning answer.
    Item choice: the 0.2-Zipf bin whose answer most reduces the relative posterior variance of the count(s)
    (Bayes-linear: Cov(T, P_z)^2 / Var(y)); then a random unused word from that bin."""
    W = WORLD[L.lang]
    run = Run(L, rng)
    reading = rmode is not None
    pm = Post(prior_m(L.l1), W['gm_k'], W['E_m'], W['E2_m'], W['lev_m'])
    pr = Post(prior_r(L.l1), W['gr_k'], W['E_r'], W['E2_r'], W['lev_r']) if reading else None
    cap = CFG['max_tot'] if reading else CFG['max_m']
    zbins = sorted(W['zbin2'])
    avail = {zb: list(W['zbin2'][zb]) for zb in zbins}
    avail_r = {zb: [i for i in W['zbin2'][zb] if W['words'][i]['has_r']] for zb in zbins}
    words = W['words']
    cum_den, acc = [], 0
    for Lv in range(1, W['nlev'] + 1):
        acc += len(W['levs'][Lv])
        cum_den.append(acc)

    def est():
        cm = [x / d if d else 0.0 for x, d in zip(pm.lev_sums(), cum_den)]
        if not reading:
            return pm.ET, math.sqrt(pm.VT), cm
        e_nor = sum(map(mul, pm.w, W['E_mn'])) / pm.W
        v_nor = max(0.0, sum(map(mul, pm.w, W['E2_mn'])) / pm.W - e_nor ** 2)
        cr_ = [(a + b) / d if d else 0.0 for a, b, d in zip(pr.lev_sums(), pm.lev_sums(W['lev_mn']), cum_den)]
        return pm.ET, math.sqrt(pm.VT), cm, pr.ET + e_nor, math.sqrt(pr.VT + v_nor), cr_

    k = 0
    while run.n_tot < cap:
        if rmode == 'all' and run.n_tot >= cap - 1:
            break
        g = run.g_hat()
        ask_r_next = reading and (rmode != 'half' or k % 2 == 0)
        restrict = ask_r_next and rmode in ('all', 'half')
        best, bzb = -1.0, None
        for zb2 in zbins:
            if not (avail_r[zb2] if restrict else avail[zb2]):
                continue
            zb = min(ZB_N - 1, int(round((zb2 + 0.5) * 2)))       # centre of the 0.2 bin in 0.1 units
            EK, cv = pm.mean_cov(zb)
            Pc = g + (1 - g) * EK
            sc = ((1 - g) * cv) ** 2 / max(1e-6, Pc * (1 - Pc)) / pm.VT
            if ask_r_next:
                EKr, cvr = pr.mean_cov(zb)
                pc_ = max(0.05, Pc)
                Pr = min(0.99, max(0.01, g + (1 - g) * min(1.0, EKr / pc_)))
                p_ask = Pc if rmode == 'cond' else 1.0
                sc += p_ask * ((1 - g) * cvr / pc_) ** 2 / (Pr * (1 - Pr)) / max(pr.VT, 1e-9)
            if sc > best:
                best, bzb = sc, zb2
        if bzb is None:
            break
        cand = avail_r[bzb] if restrict else avail[bzb]
        i = cand[rng.randrange(len(cand))]
        for d in (avail, avail_r):
            if i in d[bzb]:
                d[bzb].remove(i)
        w = words[i]
        zb = w['zb']
        Km_plug = pm.meanK(zb)
        o = run.ask(i, 'm')
        g = run.g_hat()
        if o == 'c':
            pm.lp = [x + math.log(g + (1 - g) * kk) for x, kk in zip(pm.lp, pm.ktab[zb])]
        else:
            pm.lp = [x + math.log(max(1e-12, (1 - g) * (1 - kk))) for x, kk in zip(pm.lp, pm.ktab[zb])]
        pm.refresh()
        k += 1
        if not reading:
            if o == 'c':
                run.credit.append(i)
            run.maybe_snap(est)
            continue
        do_r = w['has_r'] and (rmode == 'all' or (rmode == 'cond' and o == 'c') or (rmode == 'half' and (k - 1) % 2 == 0))
        if do_r:
            o2 = run.ask(i, 'r')
            if o == 'c':
                gr = run.g_hat()
                base = Km_plug + (1 - Km_plug) * g          # P(meaning correct) under the plug-in meaning curve
                if o2 == 'c':
                    run.credit.append(i)
                    pr.lp = [x + math.log(max(1e-12, min(kk, Km_plug) * (1 - gr) + gr * base))
                             for x, kk in zip(pr.lp, pr.ktab[zb])]
                else:
                    pr.lp = [x + math.log(max(1e-12, base - min(kk, Km_plug)))
                             for x, kk in zip(pr.lp, pr.ktab[zb])]
                pr.refresh()
        elif o == 'c':
            run.credit.append(i)          # no reading item for this word (kana-only, or D4's meaning-only half)
        run.maybe_snap(est)
    run.maybe_snap(est, force=True)
    return run.snaps


def design_irt_rho(L, rng, rmode):
    """D2/D3/D4 with a better-specified second curve: rho(z) = P(reading known | meaning known, Zipf z) on its own
    grid, so 'knows meaning AND reading' = K_m(z) * rho(z) can never exceed the meaning curve. Reading answers that
    follow a correct meaning answer update rho with the meaning curve plugged in; meaning answers update K_m.
    Item choice as design_irt."""
    W = WORLD[L.lang]
    run = Run(L, rng)
    pm = Post(prior_m(L.l1), W['gm_k'], W['E_m'], W['E2_m'], W['lev_m'])
    G = len(W['gq_pts'])
    pq = Post.__new__(Post)
    pq.lp, pq.ktab = prior_q(L.l1), W['gq_k']
    hist_r = W['hist_r']
    rz = [zb for zb in range(ZB_N) if hist_r[zb]]
    cap = CFG['max_tot']
    zbins = sorted(W['zbin2'])
    avail = {zb: list(W['zbin2'][zb]) for zb in zbins}
    avail_r = {zb: [i for i in W['zbin2'][zb] if W['words'][i]['has_r']] for zb in zbins}
    words = W['words']
    cum_den, acc = [], 0
    for Lv in range(1, W['nlev'] + 1):
        acc += len(W['levs'][Lv])
        cum_den.append(acc)
    state = {}

    def recount():
        # expected has-reading m+r count per rho grid point, with the meaning curve at its posterior mean
        kb = {zb: pm.meanK(zb) for zb in rz}
        e = [0.0] * G
        b = [0.0] * G
        for zb in rz:
            c, km = hist_r[zb], kb[zb]
            row = pq.ktab[zb]
            e = [a + c * km * q for a, q in zip(e, row)]
            b = [a + c * km * q * (1 - km * q) for a, q in zip(b, row)]
        pq.E = e
        pq.E2 = [x * x + y for x, y in zip(e, b)]
        pq.refresh()
        state['kb'] = kb

    def tmr():
        mh = sum(map(mul, pm.w, W['E_mh'])) / pm.W
        rho_bar = pq.ET / mh if mh > 0 else 0.0
        v = [rho_bar * a + c for a, c in zip(W['E_mh'], W['E_mn'])]
        ev = sum(map(mul, pm.w, v)) / pm.W
        vv = max(0.0, sum(map(mul, pm.w, [x * x for x in v])) / pm.W - ev * ev)
        e_nor = sum(map(mul, pm.w, W['E_mn'])) / pm.W
        return pq.ET + e_nor, math.sqrt(pq.VT + vv)

    def est():
        cm = [x / d if d else 0.0 for x, d in zip(pm.lev_sums(), cum_den)]
        Tr, SDr = tmr()
        nor = pm.lev_sums(W['lev_mn'])
        out, a = [], 0.0
        for Lv in range(W['nlev']):
            h = W['hlev_r'][Lv]
            a += sum(h[zb] * pm.meanK(zb) * pq.meanK(zb) for zb in range(ZB_N) if h[zb])
            out.append((a + nor[Lv]) / cum_den[Lv] if cum_den[Lv] else 0.0)
        return pm.ET, math.sqrt(pm.VT), cm, Tr, SDr, out

    recount()
    k = 0
    while run.n_tot < cap:
        if rmode == 'all' and run.n_tot >= cap - 1:
            break
        g = run.g_hat()
        ask_r_next = rmode != 'half' or k % 2 == 0
        restrict = ask_r_next and rmode in ('all', 'half')
        _, var_r = tmr()
        var_r = max(var_r * var_r, 1e-9)
        best, bzb = -1.0, None
        for zb2 in zbins:
            if not (avail_r[zb2] if restrict else avail[zb2]):
                continue
            zb = min(ZB_N - 1, int(round((zb2 + 0.5) * 2)))
            EK, cv = pm.mean_cov(zb)
            Pc = g + (1 - g) * EK
            sc = ((1 - g) * cv) ** 2 / max(1e-6, Pc * (1 - Pc)) / pm.VT
            if ask_r_next and hist_r[zb]:
                EQ, cq = pq.mean_cov(zb)
                base = max(0.05, EK + (1 - EK) * g)
                Pr = min(0.99, max(0.01, (EK * EQ * (1 - g) + g * base) / base))
                p_ask = Pc if rmode == 'cond' else 1.0
                sc += p_ask * (cq * EK * (1 - g) / base) ** 2 / (Pr * (1 - Pr)) / var_r
            if sc > best:
                best, bzb = sc, zb2
        if bzb is None:
            break
        cand = avail_r[bzb] if restrict else avail[bzb]
        i = cand[rng.randrange(len(cand))]
        for d in (avail, avail_r):
            if i in d[bzb]:
                d[bzb].remove(i)
        w = words[i]
        zb = w['zb']
        Km = pm.meanK(zb)
        o = run.ask(i, 'm')
        g = run.g_hat()
        if o == 'c':
            pm.lp = [x + math.log(g + (1 - g) * kk) for x, kk in zip(pm.lp, pm.ktab[zb])]
        else:
            pm.lp = [x + math.log(max(1e-12, (1 - g) * (1 - kk))) for x, kk in zip(pm.lp, pm.ktab[zb])]
        pm.refresh()
        k += 1
        do_r = w['has_r'] and (rmode == 'all' or (rmode == 'cond' and o == 'c') or (rmode == 'half' and (k - 1) % 2 == 0))
        if do_r:
            o2 = run.ask(i, 'r')
            if o == 'c':
                gr = run.g_hat()
                base = Km + (1 - Km) * g
                if o2 == 'c':
                    run.credit.append(i)
                    pq.lp = [x + math.log(max(1e-12, Km * q * (1 - gr) + gr * base)) for x, q in zip(pq.lp, pq.ktab[zb])]
                else:
                    pq.lp = [x + math.log(max(1e-12, base - Km * q)) for x, q in zip(pq.lp, pq.ktab[zb])]
        elif o == 'c':
            run.credit.append(i)          # no reading item for this word (kana-only, or D4's meaning-only half)
        if k % 2 == 0 or do_r:
            recount()
        run.maybe_snap(est)
    recount()
    run.maybe_snap(est, force=True)
    return run.snaps


DESIGNS = {
    'D0': lambda L, r: design_fixed(L, r),
    'D1': lambda L, r: design_irt(L, r, None),
    'D1S': lambda L, r: design_strat(L, r, False, False),
    'D1L': lambda L, r: design_strat(L, r, False, True),
    'D2': lambda L, r: design_irt_rho(L, r, 'all'),
    'D3': lambda L, r: design_irt_rho(L, r, 'cond'),
    'D4': lambda L, r: design_irt_rho(L, r, 'half'),
    'D2i': lambda L, r: design_irt(L, r, 'all'),      # first version: independent m+r curve (superseded)
    'D3i': lambda L, r: design_irt(L, r, 'cond'),
    'D4i': lambda L, r: design_irt(L, r, 'half'),
    'D3S': lambda L, r: design_strat(L, r, True, False),
    'D3L': lambda L, r: design_strat(L, r, True, True),
}


def job(args):
    lang, prof, skip_pop, idx = args
    L = make_learner(lang, prof, skip_pop, idx)
    out = dict(lang=lang, prof=prof, skip=skip_pop, idx=idx, tau=round(L.tau, 3), T_m=L.T_m, T_mr=L.T_mr,
               pm=L.place_m, pr=L.place_mr, N=WORLD[lang]['N'], res={})
    for d in CFG['designs'].split(','):
        rng = random.Random(seed_of(CFG['seed'], d, lang, prof, round(skip_pop * 100), idx))
        out['res'][d] = DESIGNS[d](L, rng)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    pops = [p.split(':') for p in CFG['pops'].split(',')]
    for lang in sorted({p[0] for p in pops}):
        build_world(lang)
    jobs = [(lang, prof, float(s), i) for lang, prof, s in pops for i in range(NL)]
    t0 = time.time()
    with Pool(4) as pool:
        res = pool.map(job, jobs, chunksize=4)
    meta = dict(cfg=CFG, n_learners=NL, seconds=round(time.time() - t0, 1), check=CHECK,
                pool={lang: dict(N=WORLD[lang]['N'], NB=WORLD[lang]['NB'], NL=WORLD[lang]['NL'],
                                 info=WORLD[lang]['info'],
                                 reading_items=sum(w['has_r'] for w in WORLD[lang]['words']),
                                 cognate_share={p: round(sum(c) / len(c), 3) for p, c in WORLD[lang]['cog'].items()})
                      for lang in WORLD})
    json.dump(dict(meta=meta, rows=res), open(f'{OUT}/raw_{RUN}.json', 'w'))
    print(RUN, 'done', len(res), 'learners in', meta['seconds'], 's')


if __name__ == '__main__':
    main()
