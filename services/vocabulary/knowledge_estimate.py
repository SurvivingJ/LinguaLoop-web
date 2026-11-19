"""Knowledge Report and vocabulary placement: the estimator and its rules.

Pure, deterministic arithmetic with no I/O. It is the single home of the vocabulary-size estimator
(ADR-051) and of every rule built on it:

* the headline range and its eligibility, label and display (knowledge-report tech §2.6);
* frequency groups (§2.7), skills by exercise family (§2.11), growth and anchors (§2.10),
  the next exam level (§2.8) and the "what to do next" rules (§2.13);
* the placement extensions (vocab-placement tech §5.1; ADR-058, ADR-060): the ja pair estimator,
  the zh right-minus-wrong-tone estimator, the gap ranges, the display guard, the eligibility
  amendment and the retake comparison (ADR-053 rule).

Band inputs are lists of seven rows, band 1 (rarest) first, exactly as the SQL functions return
them. Frames are lists of seven band sizes ``N_b`` (``knowledge_frame_bands``).
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Iterable, Optional, Sequence

METHOD_VERSION = 1

G = 0.25                 # guessing floor for four options
R = G / (1.0 - G)        # = 1/3: right-to-wrong ratio of a blind guess
Z = 1.96

MIN_PER_BAND = 10
MEDIUM_PER_BAND = 20
GOOD_PER_BAND = 30
WINDOW_DAYS = 180
REL_GOOD = 0.15
REL_MEDIUM = 0.30
REL_LOW = 0.50
GROUP_MAX_HALF_WIDTH = 0.15
FAMILY_MIN_ATTEMPTS = 20
FAMILY_MIN_MEANINGS = 10
NEXT_LEVEL_THRESHOLD = 0.80
POOL_CHANGE_SHARE = 0.05
FIRST_TREND_DAYS = 14
ANCHOR_SLACK_DAYS = 7

# Placement (vocab-placement tech §5.1).
PLACEMENT_MIN_PER_BAND = 2       # eligibility amendment (b)/(c): the warm-up guarantees 2 per band
TONE_PSEUDO_COUNT = 0.25         # zh (pc − pkt) estimator: 96–97% coverage in simulation (E33)
GAP_PSEUDO_COUNT = 0.5
GAP_MIN_SHARE = 0.01

N_BANDS = 7

GROUPS = (
    ('most_common', (7,)),
    ('common', (5, 6)),
    ('mid', (3, 4)),
    ('rare', (1, 2)),
)


# ---------------------------------------------------------------- display rounding

def step(x: float) -> float:
    """Rounding step: 10**(floor(log10 x) - 1) for x >= 10, else 1."""
    if x < 10:
        return 1
    return 10 ** (math.floor(math.log10(x)) - 1)


def floor2(x: float) -> int:
    s = step(x)
    return int(math.floor(x / s) * s)


def ceil2(x: float) -> int:
    s = step(x)
    return int(math.ceil(x / s) * s)


# ---------------------------------------------------------------- per-band statistics

def band_stats(n: int, s: int, c: int, N: int) -> tuple[float, float]:
    """ADR-051 per band: unclamped K_b = c/n − r·w/n and its Jeffreys-smoothed variance with the
    finite-population factor. ``n = 0`` returns (0, 0.25) (never eligible)."""
    if n <= 0:
        return 0.0, 0.25
    w = n - s - c
    K = c / n - R * w / n
    pc = (c + 0.5) / (n + 1.5)
    pw = (w + 0.5) / (n + 1.5)
    var = (pc * (1 - pc) + R * R * pw * (1 - pw) + 2 * R * pc * pw) / n * max(0.0, 1 - n / N)
    return K, var


def tone_band_stats(n: int, pc: int, pkt: int, N: int) -> tuple[float, float]:
    """ADR-060 zh meaning-and-reading-with-tones per band: K = (pc − pkt)/n, multinomial variance of
    y ∈ {+1, −1, 0} with pseudo-count 0.25 per category and the finite-population factor."""
    if n <= 0:
        return 0.0, 0.25
    K = (pc - pkt) / n
    a = TONE_PSEUDO_COUNT
    pp = (pc + a) / (n + 3 * a)
    pm = (pkt + a) / (n + 3 * a)
    var = (pp + pm - (pp - pm) ** 2) / n * max(0.0, 1 - n / N)
    return K, var


def _check_shape(rows: Sequence, frame: Sequence[int]) -> None:
    if len(rows) != N_BANDS or len(frame) != N_BANDS:
        raise ValueError(f'expected {N_BANDS} bands, got {len(rows)} rows and {len(frame)} frame sizes')


# ---------------------------------------------------------------- headline estimate (§2.6)

def _estimate(Ks: Sequence[float], Vs: Sequence[float], ns: Sequence[int], frame: Sequence[int],
              alltime_n: Optional[Sequence[int]], min_per_band: int) -> dict:
    N = int(sum(frame))
    out = dict(shown=False, kind='none', lo=None, hi=None, lo_disp=None, hi_disp=None, tick=None,
               label=None, rel=None, reason=None, have=None, answers_needed=None,
               T=None, SD=None, N=N, n=list(ns))
    if any(n < min_per_band for n in ns):
        if alltime_n is not None and all(n >= min_per_band for n in alltime_n):
            out['reason'] = 'out_of_date'                                    # row 2 (E1c)
        else:
            out['reason'] = 'too_few_answers'                                # row 1 (E1)
            out['have'] = int(sum(min(n, min_per_band) for n in ns))
        return out
    T = sum(Nb * K for Nb, K in zip(frame, Ks))
    SD = math.sqrt(sum(Nb * Nb * V for Nb, V in zip(frame, Vs)))
    lo = max(0.0, T - Z * SD)
    hi = min(float(N), max(T, 0.0) + Z * SD)
    rel = Z * SD / max(T, 0.10 * N)
    out.update(T=T, SD=SD, rel=rel, tick=int(round(min(N, max(0.0, T)))))
    minn = min(ns)
    if lo == 0:                                                              # row 3
        out.update(shown=True, kind='upper_only', lo=0.0, hi=hi, lo_disp=0, hi_disp=ceil2(hi), label='low')
        return out
    if rel <= REL_GOOD and minn >= GOOD_PER_BAND:                            # row 4
        label = 'good'
    elif rel <= REL_MEDIUM and minn >= MEDIUM_PER_BAND:                      # row 5
        label = 'medium'
    elif rel <= REL_LOW:                                                     # row 6
        label = 'low'
    elif hi <= 0.5 * N:                                                      # row 7
        out.update(shown=True, kind='upper_only', lo=0.0, hi=hi, lo_disp=0, hi_disp=ceil2(hi), label='low')
        return out
    else:                                                                    # row 8 (E1b)
        nbar = sum(ns) / len(ns)
        out.update(reason='too_uncertain', answers_needed=int(math.ceil(nbar * ((rel / REL_LOW) ** 2 - 1))))
        return out
    out.update(shown=True, kind='range', lo=lo, hi=hi, lo_disp=floor2(lo), hi_disp=ceil2(hi), label=label)
    return out


def estimate_range(bands: Sequence[Sequence[int]], frame: Sequence[int],
                   alltime_n: Optional[Sequence[int]] = None, *, min_per_band: int = MIN_PER_BAND) -> dict:
    """Headline estimate from meaning answers ``bands = [[n, s, c] × 7]`` (tech §2.6 rows 1–8).

    ``alltime_n`` (per-band counts without the 180-day window) separates E1 from E1c.
    ``min_per_band`` is 10 (ADR-051) unless a placement amendment applies (vocab-placement §5.1)."""
    _check_shape(bands, frame)
    stats = [band_stats(int(n), int(s), int(c), int(Nb)) for (n, s, c), Nb in zip(bands, frame)]
    return _estimate([k for k, _ in stats], [v for _, v in stats], [int(r[0]) for r in bands], frame,
                     alltime_n, min_per_band)


def pairs_to_bands(pairs: Sequence[Sequence[int]]) -> list[list[int]]:
    """ja pair counts ``[n', pc, prw]`` → ``[n, s, c]`` with s = n' − pc − prw, so ADR-051's formula
    gives K = pc/n − prw/(3n) (ADR-058)."""
    return [[int(n), int(n) - int(pc) - int(prw), int(pc)] for n, pc, prw in pairs]


def estimate_range_pairs(pairs: Sequence[Sequence[int]], frame: Sequence[int], *,
                         min_per_band: int = MIN_PER_BAND) -> dict:
    """ja (and exempt-only) meaning-and-reading estimate from ``[[n', pc, prw] × 7]`` (ADR-058)."""
    return estimate_range(pairs_to_bands(pairs), frame, None, min_per_band=min_per_band)


def estimate_range_tone_pairs(pairs: Sequence[Sequence[int]], frame: Sequence[int], *,
                              min_per_band: int = MIN_PER_BAND) -> dict:
    """zh meaning-and-reading (with tones) estimate from ``[[n', pc, pkt, pf] × 7]`` (ADR-060)."""
    _check_shape(pairs, frame)
    stats = [tone_band_stats(int(n), int(pc), int(pkt), int(Nb)) for (n, pc, pkt, _pf), Nb in zip(pairs, frame)]
    return _estimate([k for k, _ in stats], [v for _, v in stats], [int(r[0]) for r in pairs], frame,
                     None, min_per_band)


def syllable_bands(pairs: Sequence[Sequence[int]]) -> list[list[int]]:
    """zh pairs ``[n', pc, pkt, pf]`` → per-band (K_syl numerator inputs) for the syllables estimate:
    y = +1 for K or K′, −1 for F or F′ (guess rate 1/2)."""
    return [[int(n), int(pc) + int(pkt), int(pf)] for n, pc, pkt, pf in pairs]


# ---------------------------------------------------------------- gaps (vocab-placement §5.1)

def gap_range(band_counts: Sequence[tuple[int, Sequence[int]]], xs: Sequence[float], frame: Sequence[int],
              *, pseudo: float = GAP_PSEUDO_COUNT) -> dict:
    """Range of a per-word score x summed over the frame.

    ``band_counts`` = seven ``(n', [count for each value in xs])``; words not counted take x = 0.
    Var per band = [Σ p̃_k x_k² − (Σ p̃_k x_k)²]/n' · fpc with p̃_k = (count_k + pseudo)/(n' + pseudo·k_n),
    where k runs over xs plus the 0 category (k_n categories). Shown only when lo ≥ max(1% of N, step)."""
    _check_shape(band_counts, frame)
    values = list(xs) + [0.0]
    k_n = len(values)
    N = int(sum(frame))
    G_ = 0.0
    var = 0.0
    for (n, counts), Nb in zip(band_counts, frame):
        n = int(n)
        if n <= 0:
            var += Nb * Nb * 0.25
            continue
        counts = [int(c) for c in counts]
        zero = n - sum(counts)
        if zero < 0:
            raise ValueError('gap counts exceed n')
        full = counts + [zero]
        D = sum(c * x for c, x in zip(counts, xs)) / n
        ps = [(c + pseudo) / (n + pseudo * k_n) for c in full]
        m1 = sum(p * x for p, x in zip(ps, values))
        m2 = sum(p * x * x for p, x in zip(ps, values))
        G_ += Nb * D
        var += Nb * Nb * (m2 - m1 * m1) / n * max(0.0, 1 - n / Nb)
    SD = math.sqrt(var)
    lo = G_ - Z * SD
    hi = min(float(N), G_ + Z * SD)
    threshold = max(GAP_MIN_SHARE * N, step(max(lo, 1.0)))
    shown = lo >= threshold
    return dict(G=G_, SD=SD, lo=lo, hi=hi, shown=shown,
                lo_disp=floor2(lo) if shown else None, hi_disp=ceil2(hi) if shown else None)


def cap_gap(g: dict, hi_cap: float, N: int) -> dict:
    """Gap guard: a gap counts words whose meaning is recognised, so neither end may exceed the meaning
    range's upper end. Needed when the model's assumptions fail, e.g. a learner who consistently picks
    the same wrong tones (K′ every time) drives (pc − pkt) below zero and doubles the tone gap."""
    g = dict(g)
    g['hi'] = min(g['hi'], hi_cap)
    g['lo'] = min(g['lo'], g['hi'])
    threshold = max(GAP_MIN_SHARE * N, step(max(g['lo'], 1.0)))
    g['shown'] = g['lo'] >= threshold
    g['lo_disp'] = floor2(g['lo']) if g['shown'] else None
    g['hi_disp'] = ceil2(g['hi']) if g['shown'] else None
    return g


JA_GAP_XS = (4.0 / 3.0, 1.0, -1.0 / 3.0)          # reading wrong, reading IDK, meaning wrong
ZH_READING_GAP_XS = (2.0, 1.0, -1.0 / 3.0)        # F or F′, reading IDK, meaning wrong
ZH_TONE_GAP_XS = (2.0, -1.0)                      # K′, F or F′


def apply_guard(m: dict, mr: dict) -> tuple[dict, dict]:
    """Display guard (vocab-placement §5.1, PSY M8): T_m ≥ T_mr, so lo_m := max(lo_m, lo_mr) and
    hi_mr := min(hi_mr, hi_m), before rounding. Returns copies with the display fields recomputed."""
    m, mr = dict(m), dict(mr)
    if not (m.get('shown') and mr.get('shown')):
        return m, mr
    if mr['lo'] > m['lo']:
        m['lo'] = mr['lo']
        if m['kind'] == 'upper_only' and m['lo'] > 0:
            m['kind'] = 'range'
        m['lo_disp'] = floor2(m['lo']) if m['lo'] > 0 else 0
    if mr['hi'] > m['hi']:
        mr['hi'] = m['hi']
        mr['hi_disp'] = ceil2(mr['hi'])
    return m, mr


def compare(prev: dict, now: dict) -> Optional[str]:
    """ADR-053 rule: 'up' / 'down' when |Δ| ≥ 1.96·sqrt(SD_prev² + SD_now²), else 'same'.
    Both inputs need T and SD (eligible estimates); otherwise None."""
    if prev is None or now is None:
        return None
    if prev.get('T') is None or now.get('T') is None:
        return None
    delta = now['T'] - prev['T']
    sd = math.sqrt(prev['SD'] ** 2 + now['SD'] ** 2)
    if abs(delta) < Z * sd:
        return 'same'
    return 'up' if delta > 0 else 'down'


# ---------------------------------------------------------------- frequency groups (§2.7)

def group_shares(bands: Sequence[Sequence[int]], frame: Sequence[int], *, headline_eligible: bool) -> list[dict]:
    """The four merged groups. A share is shown only when the headline is eligible (rows 3–7) and the
    group's 95% half-width is ≤ 0.15."""
    _check_shape(bands, frame)
    out = []
    for name, members in GROUPS:
        idx = [b - 1 for b in members]
        Ng = sum(frame[i] for i in idx)
        num = 0.0
        var = 0.0
        answers = 0
        for i in idx:
            n, s, c = (int(x) for x in bands[i])
            K, V = band_stats(n, s, c, int(frame[i]))
            num += frame[i] * K
            var += frame[i] ** 2 * V
            answers += n
        share = num / Ng
        sd = math.sqrt(var) / Ng
        hw = Z * sd
        shown = bool(headline_eligible and hw <= GROUP_MAX_HALF_WIDTH)
        out.append(dict(group=name, bands=list(members), universe=int(Ng), answers=answers, share=share,
                        half_width=hw, shown=shown,
                        share_lo=math.floor(100 * max(0.0, share - hw)) / 100 if shown else None,
                        share_hi=math.ceil(100 * min(1.0, share + hw)) / 100 if shown else None))
    return out


# ---------------------------------------------------------------- skills (§2.11)

def wilson(p: float, n: float) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    z2 = Z * Z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return max(0.0, center - half), min(1.0, center + half)


def clustered_interval(n: int, y: int, m: int, syy: float, syn: float, snn: float) -> tuple[float, float, float]:
    """Clustered (by meaning) Wilson interval from sufficient statistics. Returns (lo, hi, n_eff)."""
    p = y / n
    if m > 1:
        ss = syy - 2 * p * syn + p * p * snn
        var = m / (m - 1) * ss / (n * n)
    else:
        var = float('inf')
    if var > 0 and math.isfinite(var):
        n_eff = min(float(n), p * (1 - p) / var)
    elif var == 0:
        n_eff = float(n)
    else:
        n_eff = 0.0
    lo, hi = wilson(p, n_eff)
    return lo, hi, n_eff


def family_summary(families: Iterable[dict]) -> dict:
    """``families``: dicts with ``family, n, y, m, syy, syn, snn`` (SQL sufficient statistics; m = number
    of meanings). Qualifies with ≥ 20 attempts and ≥ 10 meanings. Sentence: strong = highest lower
    bound, weak = lowest upper bound among qualifying families; shown only if weak.hi < strong.lo."""
    rows = []
    for f in families:
        n, y, m = int(f['n']), int(f['y']), int(f['m'])
        row = dict(family=f['family'], n=n, correct=y, meanings=m, shown=False, lo=None, hi=None)
        if n >= FAMILY_MIN_ATTEMPTS and m >= FAMILY_MIN_MEANINGS:
            lo, hi, _ = clustered_interval(n, y, m, float(f['syy']), float(f['syn']), float(f['snn']))
            row.update(shown=True, lo=lo, hi=hi)
        rows.append(row)
    q = [r for r in rows if r['shown']]
    sentence = None
    if len(q) >= 2:
        strong = max(q, key=lambda r: (r['lo'], r['family']))
        weak = min(q, key=lambda r: (r['hi'], r['family']))
        if weak is not strong and weak['hi'] < strong['lo']:
            sentence = dict(weak=weak['family'], strong=strong['family'])
    return dict(families=rows, sentence=sentence)


def sufficient_stats(pairs: Iterable[tuple[int, int]]) -> dict:
    """(y_i, n_i) per meaning → n, y, m, syy, syn, snn (the SQL output; used by tests and fixtures)."""
    pairs = list(pairs)
    return dict(n=sum(n for _, n in pairs), y=sum(y for y, _ in pairs), m=len(pairs),
                syy=sum(y * y for y, _ in pairs), syn=sum(y * n for y, n in pairs),
                snn=sum(n * n for _, n in pairs))


# ---------------------------------------------------------------- next level (§2.8)

def next_level(levels: Sequence[dict]) -> Optional[str]:
    """Lowest level (in list order) whose rated_known / in_dictionary < 0.80; levels with no
    in-dictionary words are skipped; None when every level passes or there are none."""
    for lv in levels:
        ind = int(lv.get('in_dictionary') or 0)
        if ind <= 0:
            continue
        if int(lv.get('rated_known') or 0) / ind < NEXT_LEVEL_THRESHOLD:
            return lv['level']
    return None


# ---------------------------------------------------------------- growth (§2.10)

def _as_date(x) -> date:
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def select_anchor(snapshots: Sequence[dict], today: date, days: int) -> dict:
    """Anchor for a D-day window: the latest snapshot dated in [today − D − 7, today − D]; else the
    earliest snapshot when it is ≥ 14 days old (labelled "since"); else no anchor, with the date of
    the first trend. A method_version mismatch suppresses the deltas."""
    today = _as_date(today)
    snaps = sorted(snapshots, key=lambda s: _as_date(s['snapshot_date']))
    lo, hi = today - timedelta(days=days + ANCHOR_SLACK_DAYS), today - timedelta(days=days)
    inside = [s for s in snaps if lo <= _as_date(s['snapshot_date']) <= hi]
    anchor, since = None, False
    if inside:
        anchor = inside[-1]
    elif snaps and (today - _as_date(snaps[0]['snapshot_date'])).days >= FIRST_TREND_DAYS:
        anchor, since = snaps[0], True
    if anchor is None:
        start = _as_date(snaps[0]['snapshot_date']) if snaps else today
        return dict(anchor=None, since=False, first_trend_on=start + timedelta(days=FIRST_TREND_DAYS),
                    suppressed=False)
    suppressed = int(anchor.get('method_version', METHOD_VERSION)) != METHOD_VERSION
    return dict(anchor=anchor, since=since, first_trend_on=None, suppressed=suppressed)


def snapshot_bands(snapshot: dict) -> Optional[list[list[int]]]:
    """``cal_bands`` (n_1..n_7, s_1..s_7, c_1..c_7) → [[n, s, c] × 7]."""
    cb = snapshot.get('cal_bands')
    if not cb or len(cb) != 3 * N_BANDS:
        return None
    return [[int(cb[i]), int(cb[N_BANDS + i]), int(cb[2 * N_BANDS + i])] for i in range(N_BANDS)]


def bands_to_snapshot(bands: Sequence[Sequence[int]]) -> list[int]:
    return [int(r[0]) for r in bands] + [int(r[1]) for r in bands] + [int(r[2]) for r in bands]


def estimate_change(anchor: dict, since_bands: Optional[Sequence[Sequence[int]]], frame_now: Sequence[int]) -> Optional[dict]:
    """S6 comparison: the anchor's stored counts recomputed on today's frame vs the answers after the
    anchor's last calibration answer (disjoint by construction). Both must be eligible (rows 3–7)."""
    then_bands = snapshot_bands(anchor)
    if then_bands is None or since_bands is None:
        return None
    then = estimate_range(then_bands, frame_now)
    now = estimate_range(since_bands, frame_now)
    if not (then['shown'] and now['shown']):
        return None
    verdict = compare(then, now)
    return dict(verdict={'same': 'no_clear_change', 'up': 'higher', 'down': 'lower'}[verdict],
                then=dict(lo=then['lo_disp'], hi=then['hi_disp'], kind=then['kind']),
                now=dict(lo=now['lo_disp'], hi=now['hi_disp'], kind=now['kind']))


def pool_change(anchor: dict, frame_now: Sequence[int]) -> Optional[dict]:
    fb = anchor.get('frame_bands')
    if not fb:
        return None
    then_n, now_n = int(sum(fb)), int(sum(frame_now))
    if then_n <= 0 or abs(now_n - then_n) / then_n <= POOL_CHANGE_SHARE:
        return None
    return {'from': then_n, 'to': now_n}


def growth(now: dict, snapshots: Sequence[dict], today: date, frame_now: Sequence[int],
           since_bands: Optional[dict] = None) -> dict:
    """``now``: history-free facts per window, e.g. ``{'rated_known_words': 69, 'idle60': 95,
    'd30': {'practised': 41, 'direct_checks': 164, 'met_in_texts': 44}, 'd90': {...}}``.
    ``since_bands``: ``{30: [[n,s,c]×7] answers after that anchor's cal_last_answer_at, 90: ...}``."""
    out = {'idle60': now.get('idle60')}
    for days in (30, 90):
        key = f'd{days}'
        facts = dict(now.get(key) or {})
        sel = select_anchor(snapshots, today, days)
        entry = dict(practised=facts.get('practised'), direct_checks=facts.get('direct_checks'),
                     met_in_texts=facts.get('met_in_texts'), rated_known_delta=None, anchor_date=None,
                     since=sel['since'], first_trend_on=sel['first_trend_on'].isoformat() if sel['first_trend_on'] else None,
                     estimate_change=None, pool_changed=None)
        a = sel['anchor']
        if a is not None:
            entry['anchor_date'] = _as_date(a['snapshot_date']).isoformat()
            entry['pool_changed'] = pool_change(a, frame_now)
            if not sel['suppressed']:
                entry['rated_known_delta'] = int(now['rated_known_words']) - int(a['rated_known_words'])
                entry['estimate_change'] = estimate_change(a, (since_bands or {}).get(days), frame_now)
        out[key] = entry
    return out


# ---------------------------------------------------------------- what to do next (§2.13)

STATE_BY_REASON = {'too_few_answers': 'E1', 'out_of_date': 'E1c', 'too_uncertain': 'E1b'}


def estimate_state(estimate: Optional[dict], *, nothing_yet: bool = False) -> Optional[str]:
    """E0 (no rows and no answers), E1, E1b, E1c, or None when an estimate is shown."""
    if nothing_yet:
        return 'E0'
    if estimate is None or estimate.get('shown'):
        return None
    return STATE_BY_REASON.get(estimate.get('reason'), 'E1')


def check_answers_suggested(state: str, estimate: Optional[dict]) -> int:
    if state == 'E1':
        return int(sum(max(0, MIN_PER_BAND - n) for n in (estimate or {}).get('n') or [0] * N_BANDS))
    if state == 'E1b':
        return N_BANDS * int((estimate or {}).get('answers_needed') or 0)
    return MIN_PER_BAND * N_BANDS


def next_steps(facts: dict, *, limit: int = 3) -> list[dict]:
    """First three rules of §2.13 that apply. ``facts`` keys: ``state`` (E0/E1/E1b/E1c/None),
    ``estimate`` (estimate_range output), ``prestudy`` (``{slug, title, unknown, n}`` or None; the
    caller applies the per-week allowance), ``days_since_evidence`` (int or None), ``idle60``,
    ``missed_recently``, ``last_check_answer_days`` (int or None), ``reviews_deep_link`` (bool)."""
    steps: list[dict] = []
    state = facts.get('state')
    if state in ('E0', 'E1', 'E1b', 'E1c'):
        steps.append(dict(key='knowledge.next.check', href='/calibration',
                          params={'n': check_answers_suggested(state, facts.get('estimate'))}))
    pre = facts.get('prestudy')
    if pre and int(pre.get('n') or 0) > 0 and int(pre.get('unknown') or 0) / int(pre['n']) > 0.25:
        steps.append(dict(key='knowledge.next.prestudy', href=f"/test/{pre['slug']}/prestudy",
                          params={'title': pre.get('title'), 'u': int(pre['unknown']), 'n': int(pre['n'])}))
    dse = facts.get('days_since_evidence')
    if dse is None or dse >= 7:
        steps.append(dict(key='knowledge.next.session', href='/session', params={}))
    if int(facts.get('idle60') or 0) >= 5 or int(facts.get('missed_recently') or 0) >= 1:
        href = '/session?mode=practice' + ('&extra=reviews' if facts.get('reviews_deep_link') else '')
        steps.append(dict(key='knowledge.next.review_practice', href=href, params={}))
    est = facts.get('estimate') or {}
    lcd = facts.get('last_check_answer_days')
    if est.get('shown') and lcd is not None and lcd > 60:
        steps.append(dict(key='knowledge.next.refresh_check', href='/calibration', params={}))
    steps.append(dict(key='knowledge.next.take_test', href='/tests', params={}))
    if dse is not None and dse >= 30:                                        # E3 stale: rule 3 first
        steps.sort(key=lambda s: s['key'] != 'knowledge.next.session')
    return steps[:limit]
