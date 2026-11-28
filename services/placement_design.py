"""Vocabulary placement: the pure design rules (vocab-placement tech §5–§8; ADR-057, ADR-058, ADR-060).

No I/O, no Flask, no Supabase. The service (``services/calibration_placement.py``) passes the tallies the
SQL functions return and an injected random generator, so every decision here is deterministic in tests.

Tally shapes (from ``calibration_placement_answer`` / ``knowledge_calibration_inputs``, band 1 first):
* answer tallies ``m``: ``[[n, c, w] × 7]`` (meaning items of this session);
* answer tallies ``mr``: ja/exempt ``[[n', pc, prw] × 7]``; zh ``[[n', pc, pkt, pf] × 7]``;
* inputs ``bands``: ``[[n, s, c] × 7]``; ``pairs`` as ``mr``; ``gap``: ja ``[[n', a43, b1, cm13] × 7]``,
  zh ``[[n', f, idk, cm13, kt] × 7]``.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Iterable, Optional, Sequence

from services import language_registry
from services.vocabulary import knowledge_estimate as ke

LANG_ZH, LANG_EN, LANG_JA = 1, 2, 3
N_BANDS = 7

CONFIG = {
    'version': 1,
    'warmup_per_band': 2,
    'earliest_stop': {'cjk': 40, 'en': 20},
    'cap': {'cjk': 60, 'en': 40},                    # owner, PQ10 (2026-11-18): about 60 for zh/ja
    'time_cap_s': 540,
    'sd_ratio': 0.12 / 1.645,                        # 90% half-width ≤ 12% of the pool
    'probe_p': {'forced_guess': 0.15, 'reading_after_miss': 0.25, 'sound_pair': 0.5},
    'probe_budget': 4,
    'probe_per_kind': 2,
    'recheck_delay_days': 7,
    'exclude_days': 180,
    'fast_median_ms': 800,
    'fast_min_answers': 10,
    'resume_hours': 24,
    'end_now_min_scored': 20,
    'gap_answer_cap_s': 60,
}

STOP_REASONS = ('precision', 'cap', 'time', 'exhausted', 'learner', 'abandoned')
COMPLETE_REASONS = ('precision', 'cap', 'time', 'exhausted')


def family(language_id: int) -> str:
    return 'en' if language_registry.script_family(int(language_id)) == language_registry.LATIN else 'cjk'


def has_reading(language_id: int) -> bool:
    return language_registry.has_feature(int(language_id), 'pronunciation_calibration')


def is_zh(language_id: int) -> bool:
    return int(language_id) == LANG_ZH


# ---------------------------------------------------------------- variance pieces (this session's tallies)

def _v_adr051(n: int, c: int, w: int) -> float:
    pc = (c + 0.5) / (n + 1.5)
    pw = (w + 0.5) / (n + 1.5)
    return pc * (1 - pc) + pw * (1 - pw) / 9.0 + (2.0 / 3.0) * pc * pw


def _v_tone(n: int, pc: int, pkt: int) -> float:
    a = ke.TONE_PSEUDO_COUNT
    pp = (pc + a) / (n + 3 * a)
    pm = (pkt + a) / (n + 3 * a)
    return pp + pm - (pp - pm) ** 2


def _m_unit(row) -> tuple[int, float]:
    n, c, w = (int(x) for x in row)
    return n, (_v_adr051(n, c, w) if n > 0 else 0.25)


def _mr_unit(row, zh: bool) -> tuple[int, float]:
    if zh:
        n, pc, pkt = int(row[0]), int(row[1]), int(row[2])
        return n, (_v_tone(n, pc, pkt) if n > 0 else 0.25)
    n, pc, prw = (int(x) for x in row[:3])
    return n, (_v_adr051(n, pc, prw) if n > 0 else 0.25)


def total_sd(units: Sequence[tuple[int, float]], frame: Sequence[int]) -> float:
    """SD of T from per-band (n, v) with the finite-population factor (n = 0 → v/1, no factor)."""
    var = 0.0
    for (n, v), Nb in zip(units, frame):
        if n <= 0:
            var += Nb * Nb * v
        else:
            var += Nb * Nb * v / n * max(0.0, 1 - n / Nb)
    return math.sqrt(var)


def session_sds(tallies: dict, frame: Sequence[int], language_id: int) -> tuple[float, Optional[float]]:
    """(SD_m, SD_mr) of this session's tallies; SD_mr is None for en."""
    m_units = [_m_unit(r) for r in tallies['m']]
    sd_m = total_sd(m_units, frame)
    if not has_reading(language_id):
        return sd_m, None
    mr_units = [_mr_unit(r, is_zh(language_id)) for r in tallies['mr']]
    return sd_m, total_sd(mr_units, frame)


# ---------------------------------------------------------------- warm-up and allocation (§6)

def warmup_order(rng: random.Random) -> list[int]:
    """First pass commonest band first (7 → 1), second pass a random order: 14 bands."""
    second = list(range(1, N_BANDS + 1))
    rng.shuffle(second)
    return list(range(N_BANDS, 0, -1)) + second


def warmup_done(tallies: dict, available: Optional[Sequence[bool]] = None) -> bool:
    per = CONFIG['warmup_per_band']
    for b in range(N_BANDS):
        if available is not None and not available[b] and int(tallies['m'][b][0]) < per:
            continue                             # a band with no ready word left cannot be warmed up
        if int(tallies['m'][b][0]) < per:
            return False
    return True


def next_warmup_band(tallies: dict, order: Sequence[int], available: Optional[Sequence[bool]] = None) -> Optional[int]:
    """The next band in the warm-up order that still lacks its warm-up items (counting earlier passes)."""
    need = {b: CONFIG['warmup_per_band'] for b in range(1, N_BANDS + 1)}
    seen = {b: int(tallies['m'][b - 1][0]) for b in need}
    budget = dict(seen)
    for b in order:
        if budget[b] > 0:
            budget[b] -= 1                       # this slot of the order is already filled
            continue
        if seen[b] >= need[b]:
            continue
        if available is not None and not available[b - 1]:
            continue
        return b
    return None


def _delta(units: Sequence[tuple[int, float]], frame: Sequence[int], h: int, total_var: float) -> float:
    n, v = units[h]
    if total_var <= 0:
        return 0.0
    if n <= 0:
        return float('inf')
    return frame[h] ** 2 * v * (1.0 / n - 1.0 / (n + 1)) / total_var


def next_band(tallies: dict, frame: Sequence[int], language_id: int, rng: random.Random,
              available: Optional[Sequence[bool]] = None, order: Optional[Sequence[int]] = None) -> Optional[int]:
    """The band (1…7) of the next meaning item, from the tallies of the previous answer call.

    Warm-up first (``order`` from ``warmup_order``), then h* = argmax Δ_m(h) + Δ_mr(h) over bands with a
    ready word left (en: Δ_m only), ties at random. None when no band has a word left."""
    avail = list(available) if available is not None else [True] * N_BANDS
    if not any(avail):
        return None
    if not warmup_done(tallies, avail):
        b = next_warmup_band(tallies, order or list(range(N_BANDS, 0, -1)) * 2, avail)
        if b is not None:
            return b
    m_units = [_m_unit(r) for r in tallies['m']]
    var_m = total_sd(m_units, frame) ** 2
    reading = has_reading(language_id)
    if reading:
        mr_units = [_mr_unit(r, is_zh(language_id)) for r in tallies['mr']]
        var_mr = total_sd(mr_units, frame) ** 2
    best, cands = -1.0, []
    for h in range(N_BANDS):
        if not avail[h]:
            continue
        score = _delta(m_units, frame, h, var_m)
        if reading:
            score += _delta(mr_units, frame, h, var_mr)
        if score > best + 1e-12:
            best, cands = score, [h]
        elif abs(score - best) <= 1e-12:
            cands.append(h)
    if not cands:
        return None
    return rng.choice(cands) + 1


# ---------------------------------------------------------------- stopping (§7)

def cap_for(language_id: int) -> int:
    return CONFIG['cap'][family(language_id)]


def should_stop(tallies: dict, frame: Sequence[int], language_id: int, *, pending_reading: bool = False) -> Optional[str]:
    """Checked when a word completes. Returns 'precision', 'cap', 'time' or None. A pending scored
    reading item always blocks stopping (the caller asks it first)."""
    if pending_reading:
        return None
    fam = family(language_id)
    scored = int(tallies['scored'])
    if scored >= CONFIG['cap'][fam]:
        return 'cap'
    if int(tallies.get('active_ms') or 0) >= CONFIG['time_cap_s'] * 1000:
        return 'time'
    if scored >= CONFIG['earliest_stop'][fam]:
        sd_m, sd_mr = session_sds(tallies, frame, language_id)
        limit = CONFIG['sd_ratio'] * sum(frame)
        if sd_m <= limit and (sd_mr is None or sd_mr <= limit):
            return 'precision'
    return None


def may_start_new_word(tallies: dict, language_id: int) -> bool:
    """False once the cap or the time cap is reached (the SQL receives p_next_band = NULL)."""
    return (int(tallies['scored']) < cap_for(language_id)
            and int(tallies.get('active_ms') or 0) < CONFIG['time_cap_s'] * 1000)


def can_end_now(tallies: dict) -> bool:
    """Eligibility (c) for "Stop here and see your result": warm-up complete and ≥ 20 scored items."""
    return bool(tallies.get('warmup_done', warmup_done(tallies))) and int(tallies['scored']) >= CONFIG['end_now_min_scored']


def eligible(tallies: dict, stop_reason: Optional[str]) -> bool:
    """Amendment (b)/(c) to ADR-051 rule 1 for a placement's own result."""
    if stop_reason in COMPLETE_REASONS:
        return all(int(r[0]) >= ke.PLACEMENT_MIN_PER_BAND for r in tallies['m'])
    if stop_reason in ('learner', 'abandoned'):
        return can_end_now(tallies)
    return False


def needed_for_result(tallies: dict) -> int:
    """How many more scored answers 'End now' needs (0 when it may end)."""
    if can_end_now(tallies):
        return 0
    missing_warmup = sum(max(0, CONFIG['warmup_per_band'] - int(r[0])) for r in tallies['m'])
    return max(missing_warmup, CONFIG['end_now_min_scored'] - int(tallies['scored']))


# ---------------------------------------------------------------- time and pace (§7, §8, §18)

def active_ms(gaps_ms: Iterable[int]) -> int:
    """Active time = Σ min(gap since the previous answer, 60 s)."""
    cap = CONFIG['gap_answer_cap_s'] * 1000
    return int(sum(min(max(0, int(g)), cap) for g in gaps_ms))


def minutes_left(tallies: dict, language_id: int) -> int:
    """Remaining scored items × this session's mean seconds per item, capped by the time cap; whole
    minutes, rounded up. Before any answer: the copy's estimate (7 for zh/ja, 5 for en)."""
    scored = int(tallies['scored'])
    act = int(tallies.get('active_ms') or 0)
    if scored <= 0 or act <= 0:
        return 7 if family(language_id) == 'cjk' else 5
    remaining_items = max(0, cap_for(language_id) - scored)
    secs = remaining_items * act / 1000.0 / scored
    secs = min(secs, max(0.0, CONFIG['time_cap_s'] - act / 1000.0))
    return int(math.ceil(secs / 60.0))


def is_fast(median_latency_ms: Optional[int], answered: int) -> bool:
    return (median_latency_ms is not None and answered >= CONFIG['fast_min_answers']
            and int(median_latency_ms) < CONFIG['fast_median_ms'])


# ---------------------------------------------------------------- word groups (§4)

def word_group(word: dict) -> str:
    """``word``: ``meaning`` ∈ right|wrong|idk; ``reading_ready`` bool; ``reading`` ∈ None|right|wrong|idk
    or the zh role K|KT|F|FT. Groups: both, tones_not_yet (zh), meaning_only, not_yet."""
    if word.get('meaning') != 'right':
        return 'not_yet'
    if not word.get('reading_ready'):
        return 'both'
    r = word.get('reading')
    if r in ('right', 'K'):
        return 'both'
    if r == 'KT':
        return 'tones_not_yet'
    return 'meaning_only'


def word_groups(words: Iterable[dict], language_id: int) -> dict:
    out = {'asked': 0, 'both': 0, 'meaning_only': 0, 'not_yet': 0}
    if is_zh(language_id):
        out['tones_not_yet'] = 0
    lists: dict[str, list] = {k: [] for k in out if k != 'asked'}
    for w in words:
        g = word_group(w)
        if g == 'tones_not_yet' and not is_zh(language_id):
            g = 'meaning_only'
        out['asked'] += 1
        out[g] += 1
        lists[g].append(w.get('vocab_id'))
    if not has_reading(language_id):
        out.pop('meaning_only')
        lists.pop('meaning_only')
    return {'counts': out, 'vocab_ids': lists}


# ---------------------------------------------------------------- estimates for a result (§5.1, §8)

def _rounded(e: dict) -> Optional[dict]:
    if not e or not e.get('shown'):
        return None
    return {'lo': e['lo_disp'], 'hi': e['hi_disp'], 'kind': e['kind'], 'label': e['label']}


def estimates(inputs: dict, frame: Sequence[int], language_id: int, *, min_per_band: int) -> dict:
    """Ranges for one sample (this placement, or the combined same-instrument sample).

    Returns raw estimator outputs (``m``, ``mr``, ``reading_gap``, ``tone_gap``) after the display guard,
    plus ``display`` with the rounded fields the result JSON stores."""
    m = ke.estimate_range(inputs['bands'], frame, None, min_per_band=min_per_band)
    out = {'m': m, 'mr': None, 'reading_gap': None, 'tone_gap': None}
    if has_reading(language_id) and inputs.get('pairs'):
        if is_zh(language_id):
            mr = ke.estimate_range_tone_pairs(inputs['pairs'], frame, min_per_band=min_per_band)
        else:
            mr = ke.estimate_range_pairs(inputs['pairs'], frame, min_per_band=min_per_band)
        out['m'], out['mr'] = ke.apply_guard(m, mr)
        gap = inputs.get('gap')
        if gap:
            if is_zh(language_id):
                out['reading_gap'] = ke.gap_range([(int(r[0]), [int(r[1]), int(r[2]), int(r[3])]) for r in gap],
                                                  ke.ZH_READING_GAP_XS, frame)
                out['tone_gap'] = ke.gap_range([(int(r[0]), [int(r[4]), int(r[1])]) for r in gap],
                                               ke.ZH_TONE_GAP_XS, frame)
            else:
                out['reading_gap'] = ke.gap_range([(int(r[0]), [int(r[1]), int(r[2]), int(r[3])]) for r in gap],
                                                  ke.JA_GAP_XS, frame)
    if out['m'].get('shown'):
        for key in ('reading_gap', 'tone_gap'):
            if out[key]:
                out[key] = ke.cap_gap(out[key], out['m']['hi'], int(sum(frame)))
    display = {'m': _rounded(out['m']), 'mr': _rounded(out['mr']), 'gap': None, 'tone_gap': None}
    for key, src in (('gap', 'reading_gap'), ('tone_gap', 'tone_gap')):
        g = out[src]
        if g and g['shown']:
            display[key] = {'lo': g['lo_disp'], 'hi': g['hi_disp']}
    out['display'] = display
    return out


def headline(est: dict, language_id: int) -> Optional[dict]:
    """The estimate the retake comparison and My vocabulary lead with: m+r for zh/ja, meaning for en."""
    return est['mr'] if has_reading(language_id) else est['m']


def retake_verdict(prev: Optional[dict], now: Optional[dict]) -> Optional[str]:
    """'clearly_up' / 'clearly_down' / 'not_clearly_different' (ADR-053 rule on the headline)."""
    v = ke.compare(prev, now)
    return {None: None, 'same': 'not_clearly_different', 'up': 'clearly_up', 'down': 'clearly_down'}[v]


def probe_kind_for(draw: float, *, event: str, language_id: int, budget_left: int, kind_left: Callable[[str], int],
                   sound_pair_available: bool = False) -> Optional[str]:
    """Reference for the SQL branch rules (§3, §14): which probe (if any) follows an answered scored item.
    ``event`` ∈ meaning_idk | meaning_wrong | reading_right. ``draw`` is the injected uniform u_probe."""
    if budget_left <= 0:
        return None
    p = CONFIG['probe_p']
    if event == 'meaning_idk' and draw < p['forced_guess'] and kind_left('forced_guess') > 0:
        return 'forced_guess'
    if event in ('meaning_idk', 'meaning_wrong') and has_reading(language_id) \
            and draw < p['reading_after_miss'] and kind_left('reading_after_miss') > 0:
        return 'reading_after_miss'
    if event == 'reading_right' and int(language_id) == LANG_JA and sound_pair_available \
            and draw < p['sound_pair'] and kind_left('sound_pair') > 0:
        return 'sound_pair'
    return None
