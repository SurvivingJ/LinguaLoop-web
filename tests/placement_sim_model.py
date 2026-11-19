"""Synthetic learners for the vocabulary-placement V0 check (vocab-placement tech §20 V0, TASK-1087).

A reduced port of the research learner model (wiki/evaluations/vocab-placement-research-2026-11-18/sim/sim.py,
with the tone state of tones/tone_sim.py). It drives the PRODUCTION rules (services.placement_design and
services.vocabulary.knowledge_estimate) and returns, per learner, the estimates and the true counts.
Every parameter is an assumption of the research stage; nothing here is learner data.

Word pools are synthetic: band sizes are the live frames (2026-11-19), Zipf uniform within each band,
a cognate flag for cross-CJK learners, and a reading-exempt share for ja (kana-only lemmas).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from services import placement_design as pd

FRAMES = {pd.LANG_ZH: [303, 617, 742, 691, 664, 435, 171],
          pd.LANG_JA: [577, 425, 621, 655, 537, 283, 77],
          pd.LANG_EN: [412, 517, 737, 794, 722, 425, 147]}
BAND_ZIPF = [(2.0, 3.0), (3.0, 3.5), (3.5, 4.0), (4.0, 4.5), (4.5, 5.0), (5.0, 5.5), (5.5, 7.0)]
JA_EXEMPT_SHARE = 0.25            # kana-only lemmas (no reading item)
COGNATE_SHARE = 0.55              # shared-character words for ja-L1 learners of zh and zh-L1 learners of ja
SEC_MEANING, SEC_READING = 6.57, 7.50

# Population profiles (research sim PROFILES; ranges are drawn per learner).
PROFILES = {
    ('zh', 'en'): dict(kappa=(0, 0), pi=(0.60, 0.90), nu=(0, 0), theta=(0.5, 0.95)),
    ('zh', 'ja'): dict(kappa=(0.60, 0.95), pi=(0.60, 0.90), nu=(0.03, 0.15), theta=(0.5, 0.95)),
    ('ja', 'en'): dict(kappa=(0.50, 0.85), pi=(0.75, 0.95), nu=(0, 0), theta=None),
    ('ja', 'zh'): dict(kappa=(0.60, 0.95), pi=(0.70, 0.95), nu=(0.10, 0.35), theta=None),
    ('en', 'en'): dict(kappa=(0, 0), pi=(1, 1), nu=(0, 0), theta=None),
}
LANG_IDS = {'zh': pd.LANG_ZH, 'ja': pd.LANG_JA, 'en': pd.LANG_EN}


def sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class Word:
    band: int
    z: float
    exempt: bool
    cognate: bool


@dataclass
class Learner:
    lang: int
    meaning: list = field(default_factory=list)
    reading: list = field(default_factory=list)
    tones: list = field(default_factory=list)
    skip: float = 0.5


def build_pool(lang: int, rng: random.Random) -> list[list[Word]]:
    pool = []
    for b, Nb in enumerate(FRAMES[lang], start=1):
        lo, hi = BAND_ZIPF[b - 1]
        pool.append([Word(b, rng.uniform(lo, hi), lang == pd.LANG_EN or (lang == pd.LANG_JA and rng.random() < JA_EXEMPT_SHARE),
                          rng.random() < COGNATE_SHARE) for _ in range(Nb)])
    return pool


def make_learner(lang_code: str, l1: str, skip_pop: float, pool, rng: random.Random) -> Learner:
    prof = PROFILES[(lang_code, l1)]
    tau = rng.uniform(2.5, 7.0)
    a = math.exp(rng.gauss(math.log(1.6), 0.2))
    kappa, pi, nu = rng.uniform(*prof['kappa']), rng.uniform(*prof['pi']), rng.uniform(*prof['nu'])
    theta = rng.uniform(*prof['theta']) if prof['theta'] else None
    L = Learner(LANG_IDS[lang_code], skip=min(0.95, max(0.0, rng.gauss(skip_pop, 0.1))))
    cross = l1 in ('ja', 'zh') and lang_code in ('ja', 'zh') and l1 != lang_code
    for band in pool:
        mb, rb, tb = [], [], []
        for w in band:
            f = rng.random() < sig(a * (w.z - tau) - rng.gauss(0, 1.2))
            c = (not f) and cross and w.cognate and rng.random() < kappa
            m = f or c
            if w.exempt:
                r = m
            elif f:
                r = rng.random() < pi + (1 - pi) * sig(a * (w.z - tau) - 1.0)
            elif c:
                r = rng.random() < nu
            else:
                r = False
            t = r and (theta is None or rng.random() < theta + (1 - theta) * sig(a * (w.z - tau) - 1.5))
            mb.append(m)
            rb.append(r)
            tb.append(t)
        L.meaning.append(mb)
        L.reading.append(rb)
        L.tones.append(tb)
    return L


def truths(L: Learner, pool) -> dict:
    zh = L.lang == pd.LANG_ZH
    t = dict(m=0, mr=0, syll=0, gap=0, tone_gap=0)
    for b, band in enumerate(pool):
        for i, w in enumerate(band):
            m, r, tn = L.meaning[b][i], L.reading[b][i], L.tones[b][i]
            if not m:
                continue
            t['m'] += 1
            full = r and (tn if zh else True)
            t['mr'] += full
            t['syll'] += r
            if zh:
                t['gap'] += not r
                t['tone_gap'] += r and not tn
            else:
                t['gap'] += not full
    return t


def _answer_meaning(L, b, i, rng):
    if L.meaning[b][i]:
        return 'right'
    if rng.random() < L.skip:
        return 'idk'
    return 'right' if rng.random() < 0.25 else 'wrong'


def _answer_reading(L, b, i, rng):
    r = L.reading[b][i]
    if L.lang == pd.LANG_ZH:
        if r and L.tones[b][i]:
            return 'K'
        if r:
            return 'K' if rng.random() < 0.5 else 'KT'
        if rng.random() < L.skip:
            return 'idk'
        return rng.choice(['K', 'KT', 'F', 'FT'])
    if r:
        return 'right'
    if rng.random() < L.skip:
        return 'idk'
    return 'right' if rng.random() < 0.25 else 'wrong'


def run_placement(L: Learner, pool, rng: random.Random, *, stop_at: int | None = None) -> dict:
    """One placement with the production rules. ``stop_at`` simulates "End now" at that many scored items."""
    lang = L.lang
    frame = FRAMES[lang]
    zh, reading = lang == pd.LANG_ZH, pd.has_reading(lang)
    T = dict(m=[[0, 0, 0] for _ in range(7)], mr=[[0, 0, 0, 0] if zh else [0, 0, 0] for _ in range(7)],
             scored=0, active_ms=0)
    bands = [[0, 0, 0] for _ in range(7)]                 # inputs shape [n, s, c]
    gap = [[0, 0, 0, 0, 0] if zh else [0, 0, 0, 0] for _ in range(7)]
    left = [list(range(len(band))) for band in pool]
    for lst in left:
        rng.shuffle(lst)
    order = pd.warmup_order(rng)
    reason = None
    while True:
        if stop_at is not None and T['scored'] >= stop_at and pd.can_end_now(T):
            reason = 'learner'
            break
        if not pd.may_start_new_word(T, lang):
            reason = 'cap' if T['scored'] >= pd.cap_for(lang) else 'time'
            break
        avail = [bool(x) for x in left]
        b1 = pd.next_band(T, frame, lang, rng, available=avail, order=order)
        if b1 is None:
            reason = 'exhausted'
            break
        b = b1 - 1
        i = left[b].pop()
        w = pool[b][i]
        a = _answer_meaning(L, b, i, rng)
        T['scored'] += 1
        T['active_ms'] += int(SEC_MEANING * 1000)
        T['m'][b][0] += 1
        T['m'][b][1] += a == 'right'
        T['m'][b][2] += a == 'wrong'
        bands[b][0] += 1
        bands[b][1] += a == 'idk'
        bands[b][2] += a == 'right'
        if reading:
            mr = T['mr'][b]
            g = gap[b]
            mr[0] += 1
            g[0] += 1
            if w.exempt:
                mr[1] += a == 'right'
                if not zh:
                    mr[2] += a == 'wrong'
                    g[3] += a == 'wrong'
            elif a == 'right':
                ra = _answer_reading(L, b, i, rng)
                T['scored'] += 1
                T['active_ms'] += int(SEC_READING * 1000)
                if zh:
                    mr[1] += ra == 'K'
                    mr[2] += ra == 'KT'
                    mr[3] += ra in ('F', 'FT')
                    g[1] += ra in ('F', 'FT')
                    g[2] += ra == 'idk'
                    g[4] += ra == 'KT'
                else:
                    mr[1] += ra == 'right'
                    mr[2] += ra == 'wrong'
                    g[1] += ra == 'wrong'
                    g[2] += ra == 'idk'
            elif a == 'wrong':
                g[3] += 1
        stop = pd.should_stop(T, frame, lang)
        if stop:
            reason = stop
            break
    inputs = dict(bands=bands)
    if reading:
        inputs.update(pairs=T['mr'], gap=gap)
    est = pd.estimates(inputs, frame, lang, min_per_band=2)
    return dict(reason=reason, scored=T['scored'], minutes=T['active_ms'] / 60000.0, est=est,
                eligible=pd.eligible(T, reason))


def covers(e: dict | None, truth: float) -> bool | None:
    if e is None or not e.get('shown'):
        return None
    lo = 0.0 if e['kind'] == 'upper_only' else e['lo']
    return lo <= truth <= e['hi']
