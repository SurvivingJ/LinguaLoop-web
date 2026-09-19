#!/usr/bin/env python3
"""TASK-749 — measure test-selection quality (M1-M5) and replay history.

READ-ONLY. Reads test_attempts / user_skill_ratings and calls the TASK-748 ranker
`recommended_tests_ranked(user, lang, days, weight, as_of)`; writes nothing to the
database. Safe to re-run. Lives under scripts/, not tests/: it depends on live
history and must not gate CI (tech spec §6).

Metrics (features/vocabulary-aware-test-selection.tech §5.1), per (language, type):

  M1  on-target rate   first attempts with 60 < percentage <= 85 (see ON_TARGET:
                       the recorded baseline excludes exactly-60 scores)
  M2  below-floor rate attempts with percentage < 50. Reported over ALL attempts,
                       because that is how the 2026-09-08 baseline was computed
                       (pitch accent 6/7 = all 7 attempts; only 5 were first
                       attempts). The first-attempt variant is printed beside it.
  M3  compression      spread of implied ability across types vs spread of the
                       live rating, where implied = test_elo_before
                       − 400·log10(1/s − 1), s = percentage clamped to [0.05, 0.95]
                       (unclamped, 100% is infinite), averaged per type over first
                       attempts. Live rating per type = the last user_elo_after in
                       the window.
  M4  served unknown   median unknown(t) over the top-10 per type, both arms
  M5  pool health      candidates returned per type, both arms (must not fall)

Replay (§5.2.1): every first attempt in --replay-language is re-ranked against the
candidate set AS OF its timestamp under each ARM, and the unknown(t) distribution
of that arm's top-10 for the attempt's type is reported. See the AS-OF caveats in
migrations/task748_get_recommended_tests_vocab_aware.sql: test ELOs and
later-updated p_known values cannot be rewound.

Arms (TASK-781) are (vocab_weight, combine_mode) pairs:

  w0       weight 0            the pre-TASK-748 ranking; vocabulary contributes nothing
  sum      weight 1, 'sum'     score = e + v
  product  weight 1, 'product' score = (1+e)·(1+v), the sum plus the cross term e·v

`combine_mode` is a selection_tuning row, not an RPC argument (see tech spec
§3.5), and this script talks PostgREST, so the product arm is measured by WRITING
that row and restoring it in a finally. That is safe ONLY while
selection_tuning.vocab_weight = 0, because get_recommended_tests never reaches
the ranker at weight 0 — so the mode cannot change what a live learner is served.
The script REFUSES to flip the mode if vocab_weight is anything else.

Shadow snapshot (§5.2.2): --shadow-out DIR appends one JSONL line per active
(user, language) with both arms' top-10 per type, for a daily cron over the
shadow window. It snapshots the live state; it does not hook live requests.

Usage::

    PYTHONIOENCODING=utf-8 python -m scripts.measure_selection_quality \\
        --until 2026-09-08T23:59:59+00:00 --replay-language 3
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterable, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Clamp for the inverted Elo expectation; the spec's [0.05, 0.95].
S_MIN, S_MAX = 0.05, 0.95
#: M1's on-target band, HALF-OPEN: 60 < pct <= 85. The tech spec writes
#: [60, 85], but the 2026-09-08 baseline it records (reading 3/8) is only
#: reproducible with 60 excluded: two ja reading first attempts are stored at
#: exactly 60 (3/5), and counting them gives 5/8. The baseline is the contract
#: the metric has to be comparable with, so it wins; the inclusive count is
#: printed beside it.
ON_TARGET = (60.0, 85.0)
#: M2's floor, strict.
BELOW_FLOOR = 50.0
#: The ranker's defaults (selection_tuning seeds) — used only to report how many
#: served tests sit inside u* ± u_tol.
U_STAR, U_TOL = 0.15, 0.10
TOP_N = 10
LANG_CODES = {1: 'zh', 2: 'en', 3: 'ja'}

#: TASK-781 arms: label -> (vocab_weight, combine_mode). 'w0' runs in sum mode
#: because at weight 0 the mode cannot matter: (1+e)·1 is a monotone transform of
#: e, so both modes give the identical order — one fewer live write.
ARM_SPEC: dict = {
    'w0':      (0.0, 'sum'),
    'sum':     (1.0, 'sum'),
    'product': (1.0, 'product'),
}
ARMS = tuple(ARM_SPEC)


# =============================================================================
# Pure metric maths (unit-tested in tests/test_selection_metrics.py)
# =============================================================================

def attempt_percentage(row: dict) -> Optional[float]:
    """The attempt's score in percent: the stored column, else score / total."""
    pct = row.get('percentage')
    if pct is not None:
        return float(pct)
    total = row.get('total_questions') or 0
    if not total:
        return None
    return 100.0 * float(row.get('score') or 0) / float(total)


def implied_ability(test_elo: float, percentage: float) -> float:
    """Invert the Elo expectation: the user rating at which `percentage` is expected.

    user = test_elo − 400·log10(1/s − 1), with s clamped to [0.05, 0.95] so a
    perfect or zero score stays finite.
    """
    s = min(S_MAX, max(S_MIN, percentage / 100.0))
    return float(test_elo) - 400.0 * math.log10(1.0 / s - 1.0)


def on_target(percentages: Iterable[float], inclusive_low: bool = False) -> tuple[int, int]:
    """(hits, n) with hits = percentages in (60, 85] — or [60, 85] if inclusive_low."""
    values = [p for p in percentages if p is not None]
    lo, hi = ON_TARGET
    if inclusive_low:
        return sum(1 for p in values if lo <= p <= hi), len(values)
    return sum(1 for p in values if lo < p <= hi), len(values)


def below_floor(percentages: Iterable[float]) -> tuple[int, int]:
    """(hits, n) with hits = percentages strictly below 50."""
    values = [p for p in percentages if p is not None]
    return sum(1 for p in values if p < BELOW_FLOOR), len(values)


def spread(values: Iterable[float]) -> Optional[float]:
    """max − min, or None for no values."""
    vals = [v for v in values if v is not None]
    return (max(vals) - min(vals)) if vals else None


def compression(implied_by_type: dict, live_by_type: dict) -> dict:
    """M3 over the types present in BOTH maps."""
    types = sorted(set(implied_by_type) & set(live_by_type))
    implied = spread(implied_by_type[t] for t in types)
    live = spread(live_by_type[t] for t in types)
    ratio = (implied / live) if (implied is not None and live) else None
    return {'types': types, 'implied_spread': implied, 'live_spread': live, 'ratio': ratio}


def quantiles(values: Iterable[Optional[float]]) -> dict:
    """n, median, p25, p75 over the non-None values (None fields when empty)."""
    vals = sorted(float(v) for v in values if v is not None)
    if not vals:
        return {'n': 0, 'median': None, 'p25': None, 'p75': None}

    def q(frac: float) -> float:
        pos = frac * (len(vals) - 1)
        lo, hi = math.floor(pos), math.ceil(pos)
        return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)

    return {'n': len(vals), 'median': q(0.5), 'p25': q(0.25), 'p75': q(0.75)}


def band_share(values: Iterable[Optional[float]], target: float = U_STAR,
               tol: float = U_TOL) -> Optional[float]:
    """Share of non-None values inside [target − tol, target + tol]."""
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return None
    return sum(1 for v in vals if target - tol <= v <= target + tol) / len(vals)


def jaccard(a: Iterable, b: Iterable) -> Optional[float]:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return None
    return len(sa & sb) / len(sa | sb)


def _ranks(values: Sequence[float]) -> list[float]:
    """Average ranks (1-based), ties sharing the mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def spearman(xs: Sequence[Optional[float]], ys: Sequence[Optional[float]]) -> Optional[float]:
    """Spearman's rho over the pairs where both values are present."""
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    rx = _ranks([p[0] for p in pairs])
    ry = _ranks([p[1] for p in pairs])
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if not vx or not vy:
        return None
    return cov / math.sqrt(vx * vy)


# =============================================================================
# Data access (read-only)
# =============================================================================

def _fetch_all(query, page: int = 1000) -> list[dict]:
    rows, start = [], 0
    while True:
        batch = query.range(start, start + page - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < page:
            return rows
        start += page


def fetch_attempts(db, since: Optional[str], until: Optional[str]) -> list[dict]:
    q = (db.table('test_attempts')
           .select('id,user_id,test_id,test_type_id,language_id,score,total_questions,'
                   'percentage,user_elo_before,user_elo_after,test_elo_before,'
                   'is_first_attempt,created_at')
           .order('created_at'))
    if since:
        q = q.gte('created_at', since)
    if until:
        q = q.lte('created_at', until)
    return _fetch_all(q)


def fetch_type_codes(db) -> dict[int, str]:
    rows = db.table('dim_test_types').select('id,type_code').execute().data or []
    return {int(r['id']): r['type_code'] for r in rows}


def ranked(db, user_id: str, language_id: int, weight: float,
           as_of: Optional[str] = None) -> list[dict]:
    """Every eligible candidate from the TASK-748 ranker (service role only)."""
    return db.rpc('recommended_tests_ranked', {
        'p_user_id': user_id,
        'p_language_id': int(language_id),
        'p_topic_recency_days': 14,
        'p_vocab_weight': weight,
        'p_as_of': as_of,
    }).execute().data or []


def read_tuning(db) -> dict:
    """selection_tuning as {key: value or value_text}."""
    rows = db.table('selection_tuning').select('key,value,value_text').execute().data or []
    return {r['key']: (r['value_text'] if r['value'] is None else r['value']) for r in rows}


@contextmanager
def combine_mode(db, mode: str):
    """Hold selection_tuning.combine_mode at `mode`, then put it back.

    The ONLY write this script makes. It is refused unless vocab_weight = 0,
    because at weight 0 get_recommended_tests never reaches the ranker, so the
    mode is inert for live traffic; above 0 this would change what real learners
    are served mid-measurement. A crash between the two writes therefore leaves
    an inert row, not a live behaviour change — but the caller re-reads and says
    so at the end of the run.
    """
    tuning = read_tuning(db)
    weight = float(tuning.get('vocab_weight') or 0)
    current = tuning.get('combine_mode') or 'sum'
    if mode == current:
        yield current
        return
    if weight != 0:
        raise RuntimeError(
            f'refusing to set combine_mode={mode!r}: selection_tuning.vocab_weight is '
            f'{weight}, not 0, so the flip would change what live learners are served. '
            'Set vocab_weight = 0 first, or run the arms from SQL inside a rollback-only '
            'transaction.')
    print(f'  [combine_mode {current} -> {mode}] (inert: vocab_weight = 0)', flush=True)
    db.table('selection_tuning').update({'value_text': mode}).eq('key', 'combine_mode').execute()
    try:
        yield mode
    finally:
        db.table('selection_tuning').update({'value_text': current}).eq('key', 'combine_mode').execute()
        print(f'  [combine_mode {mode} -> {current}] restored', flush=True)


def collect(db, requests: Sequence[tuple], arms: Sequence[str]) -> dict:
    """{arm: {(user_id, lang, as_of): rows}} — one mode flip per arm, not per call.

    `requests` is a sequence of (user_id, language_id, as_of|None).
    """
    out: dict = {}
    for arm in arms:
        weight, mode = ARM_SPEC[arm]
        with combine_mode(db, mode):
            out[arm] = {key: ranked(db, key[0], key[1], weight, as_of=key[2])
                        for key in requests}
    return out


# =============================================================================
# Reports
# =============================================================================

def attempt_metrics(attempts: list[dict], type_codes: dict[int, str]) -> dict:
    """M1-M3 per language from attempt history."""
    by_lang: dict = defaultdict(lambda: defaultdict(list))
    for a in attempts:
        a['_pct'] = attempt_percentage(a)
        a['_type'] = type_codes.get(int(a['test_type_id']), str(a['test_type_id']))
        by_lang[int(a['language_id'])][a['_type']].append(a)

    out = {}
    for lang, by_type in sorted(by_lang.items()):
        types, implied_by_type, live_by_type = {}, {}, {}
        for t, rows in sorted(by_type.items()):
            firsts = [r for r in rows if r.get('is_first_attempt')]
            m1 = on_target(r['_pct'] for r in firsts)
            m1_incl = on_target((r['_pct'] for r in firsts), inclusive_low=True)
            m2_all = below_floor(r['_pct'] for r in rows)
            m2_first = below_floor(r['_pct'] for r in firsts)
            implied = [implied_ability(r['test_elo_before'], r['_pct'])
                       for r in firsts if r['_pct'] is not None]
            last = rows[-1]  # rows are created_at-ordered
            if implied:
                # Rounded to whole ELO points before M3 takes a spread, as the
                # baseline table did (1539 − 1091 = 448; unrounded it is 447.x).
                implied_by_type[t] = round(statistics.fmean(implied))
            live_by_type[t] = int(last['user_elo_after'])
            types[t] = {
                'attempts': len(rows),
                'first_attempts': len(firsts),
                'mean_pct_first': (statistics.fmean(r['_pct'] for r in firsts)
                                   if firsts else None),
                'M1_on_target': m1,
                'M1_on_target_incl60': m1_incl,
                'M2_below_floor_all': m2_all,
                'M2_below_floor_first': m2_first,
                'implied_ability': implied_by_type.get(t),
                'implied_sd': (statistics.stdev(implied) if len(implied) > 1 else None),
                'live_elo': live_by_type[t],
            }
        all_rows = [r for rows in by_type.values() for r in rows]
        out[lang] = {
            'types': types,
            'M2_overall_all': below_floor(r['_pct'] for r in all_rows),
            'M3': compression(implied_by_type, live_by_type),
        }
    return out


def _top(rows: list[dict], test_type: str, n: int = TOP_N) -> list[dict]:
    return sorted((r for r in rows if r['test_type'] == test_type and r['rank_in_type'] <= n),
                  key=lambda r: r['rank_in_type'])


def served_metrics(db, pairs: list[tuple[str, int]], arms: Sequence[str] = ARMS) -> dict:
    """M4, M5 and per-arm rank correlation for each (user, language), current state."""
    requests = [(u, l, None) for u, l in pairs]
    cache = collect(db, requests, arms)
    out = {}
    for user_id, lang in pairs:
        key = (user_id, lang, None)
        by_arm = {a: cache[a][key] for a in arms}
        types = sorted({r['test_type'] for rows in by_arm.values() for r in rows})
        per_type = {}
        for t in types:
            tops = {a: _top(by_arm[a], t) for a in arms}
            base = arms[0]
            per_type[t] = {
                'M5_count': {a: len(tops[a]) for a in arms},
                'M4_unknown': {a: quantiles(r['unknown_share'] for r in tops[a]) for a in arms},
                'in_band': {a: band_share(r['unknown_share'] for r in tops[a]) for a in arms},
                # Overlap of each arm's top-10 with the first arm's, and of the
                # two vocabulary arms with each other.
                'overlap_vs_' + base: {a: jaccard((r['test_id'] for r in tops[base]),
                                                  (r['test_id'] for r in tops[a])) for a in arms},
                'overlap_sum_vs_product': (
                    jaccard((r['test_id'] for r in tops['sum']),
                            (r['test_id'] for r in tops['product']))
                    if 'sum' in tops and 'product' in tops else None),
            }
        # How strongly each arm's ORDER is driven by vocabulary: rho(unknown, score)
        # over every candidate, pooled across types. |unknown − u*| is V-shaped, so
        # this is not a linearity claim — it reads as "which way the ranking leans"
        # on content that sits almost entirely above u*.
        rho = {a: spearman([r['unknown_share'] for r in by_arm[a]],
                           [float(r['score']) for r in by_arm[a]]) for a in arms}
        first = next((rows[0] for rows in by_arm.values() if rows), None)
        out[f'{user_id}:{lang}'] = {
            'ability_source': first['ability_source'] if first else None,
            'ability_zipf': first['ability_zipf'] if first else None,
            'spearman_unknown_vs_score': rho,
            'types': per_type,
        }
    return out


def replay(db, attempts: list[dict], language_id: int, arms: Sequence[str] = ARMS) -> dict:
    """Re-rank every first attempt in `language_id` as of its timestamp, per arm."""
    firsts = [a for a in attempts
              if int(a['language_id']) == language_id and a.get('is_first_attempt')]
    requests = [(a['user_id'], language_id, a['created_at']) for a in firsts]
    cache = collect(db, requests, arms)

    rows_out = []
    for a in firsts:
        key = (a['user_id'], language_id, a['created_at'])
        rec = {'attempt_id': a['id'], 'created_at': a['created_at'], 'type': a['_type'],
               'percentage': a['_pct'], 'test_id': a['test_id'], 'arms': {}}
        for arm in arms:
            cands = cache[arm][key]
            top = _top(cands, a['_type'])
            taken = next((c for c in cands
                          if c['test_id'] == a['test_id'] and c['test_type'] == a['_type']), None)
            rec['arms'][arm] = {
                'top_unknown': [c['unknown_share'] for c in top],
                'top_difficulty': [c['difficulty_level'] for c in top],
                'top_ids': [c['test_id'] for c in top],
                'neutral': sum(1 for c in top if c['vocab_neutral']),
                'taken_rank': taken['rank_in_type'] if taken else None,
                'taken_unknown': taken['unknown_share'] if taken else None,
                'pool': sum(1 for c in cands if c['test_type'] == a['_type']),
                'ability_source': cands[0]['ability_source'] if cands else None,
                'ability_zipf': cands[0]['ability_zipf'] if cands else None,
            }
        rec['overlap'] = {f'{x}|{y}': jaccard(rec['arms'][x]['top_ids'], rec['arms'][y]['top_ids'])
                          for i, x in enumerate(arms) for y in arms[i + 1:]}
        rows_out.append(rec)

    summary = {'arms': {}}
    for arm in arms:
        pooled = [u for r in rows_out for u in r['arms'][arm]['top_unknown']]
        diffs = [d for r in rows_out for d in r['arms'][arm]['top_difficulty']]
        summary['arms'][arm] = {
            'top10_unknown': quantiles(pooled),
            'top10_in_band': band_share(pooled),
            'top10_difficulty': quantiles(diffs),
            'neutral_slots': sum(r['arms'][arm]['neutral'] for r in rows_out),
            'slots': sum(len(r['arms'][arm]['top_unknown']) for r in rows_out),
            'taken_rank': quantiles(r['arms'][arm]['taken_rank'] for r in rows_out),
            'min_pool': min([r['arms'][arm]['pool'] for r in rows_out] or [0]),
        }
    summary['mean_overlap'] = {}
    for i, x in enumerate(arms):
        for y in arms[i + 1:]:
            vals = [r['overlap'][f'{x}|{y}'] for r in rows_out if r['overlap'][f'{x}|{y}'] is not None]
            summary['mean_overlap'][f'{x}|{y}'] = statistics.fmean(vals) if vals else None
    # M5 as the replay sees it: no arm's pool may be smaller than w0's.
    summary['M5_min_pool_delta'] = {
        arm: min([r['arms'][arm]['pool'] - r['arms'][arms[0]]['pool'] for r in rows_out] or [0])
        for arm in arms}
    # The BASELINE −0.59: unknown share of the test the learner actually took vs
    # the score they got. It is a property of (user, test, as_of), so it is the
    # SAME in every arm — a check on the vocabulary signal, not an arm comparison.
    summary['spearman_taken_unknown_vs_pct'] = spearman(
        [r['arms'][arms[0]]['taken_unknown'] for r in rows_out],
        [r['percentage'] for r in rows_out])
    return {'attempts': rows_out, 'summary': summary}


# =============================================================================
# Printing
# =============================================================================

def _fmt(v, nd=2) -> str:
    if v is None:
        return '—'
    if isinstance(v, float):
        return f'{v:.{nd}f}'
    return str(v)


def _q(q: dict) -> str:
    if not q['n']:
        return 'n=0'
    return f"median {q['median']:.3f} (p25 {q['p25']:.3f}, p75 {q['p75']:.3f}, n={q['n']})"


def print_attempt_metrics(m: dict) -> None:
    print('=== M1-M3 from attempt history ===')
    for lang, block in m.items():
        print(f'\n[{LANG_CODES.get(lang, lang)}]')
        print(f"  {'type':<14}{'att':>4}{'1st':>5}{'mean%':>7}  {'M1 (60,85]':<11}{'[60,85]':<9}"
              f"{'M2 <50 all':<11}{'M2 <50 1st':<11}{'implied':>8}{'sd':>6}{'live':>6}")
        for t, r in block['types'].items():
            m1, m2a, m2f = r['M1_on_target'], r['M2_below_floor_all'], r['M2_below_floor_first']
            m1i = r['M1_on_target_incl60']
            print(f"  {t:<14}{r['attempts']:>4}{r['first_attempts']:>5}"
                  f"{_fmt(r['mean_pct_first'], 1):>7}  {f'{m1[0]}/{m1[1]}':<11}{f'{m1i[0]}/{m1i[1]}':<9}"
                  f"{f'{m2a[0]}/{m2a[1]}':<11}{f'{m2f[0]}/{m2f[1]}':<11}"
                  f"{_fmt(r['implied_ability'], 0):>8}{_fmt(r['implied_sd'], 0):>6}{r['live_elo']:>6}")
        o = block['M2_overall_all']
        m3 = block['M3']
        print(f"  M2 overall (all attempts): {o[0]}/{o[1]}")
        print(f"  M3 compression: implied spread {_fmt(m3['implied_spread'], 0)} vs live "
              f"{_fmt(m3['live_spread'], 0)} (ratio {_fmt(m3['ratio'])}) over {m3['types']}")


def print_served(s: dict) -> None:
    print('\n=== M4 / M5 - what would be served now, per arm ===')
    for key, block in s.items():
        user, lang = key.split(':')
        print(f"\n[{LANG_CODES.get(int(lang), lang)} user {user[:8]}] ability "
              f"{_fmt(block['ability_zipf'], 3)} ({block['ability_source']})")
        rho = block['spearman_unknown_vs_score']
        print('  rho(unknown, score) over all candidates: '
              + ', '.join(f'{a} {_fmt(v, 3)}' for a, v in rho.items()))
        for t, r in block['types'].items():
            arms = list(r['M5_count'])
            print(f"  {t:<13} M5 " + ' '.join(f'{a}={r["M5_count"][a]}' for a in arms))
            for a in arms:
                # `in_band` and M4 are computed over candidates that HAVE an
                # unknown share, so print how many of the ten are neutral: an
                # arm that serves more unlinked tests scores its band share over
                # a smaller denominator, which would otherwise read as a win.
                neutral = r['M5_count'][a] - r['M4_unknown'][a]['n']
                print(f"      {a:<8} M4 {_q(r['M4_unknown'][a])} | in u*+-tol "
                      f"{_fmt(r['in_band'][a])} | neutral {neutral}/{r['M5_count'][a]}")
            if r.get('overlap_sum_vs_product') is not None:
                print(f"      top-10 overlap sum|product {_fmt(r['overlap_sum_vs_product'])}")


def print_replay(r: dict, language_id: int) -> None:
    s = r['summary']
    arms = list(s['arms'])
    print(f'\n=== Replay: {LANG_CODES.get(language_id, language_id)} first attempts, '
          f'as of each timestamp ({len(r["attempts"])} attempts, arms: {", ".join(arms)}) ===')
    head = f"  {'when':<17}{'type':<13}{'pct':>6} {'src':<13}"
    head += ''.join(f'{a + " top10 unknown":<24}' for a in arms)
    head += f"{'taken rank':>26}"
    print(head)
    for a in r['attempts']:
        line = (f"  {a['created_at'][:16]:<17}{a['type']:<13}{_fmt(a['percentage'], 1):>6} "
                f"{str(a['arms'][arms[0]]['ability_source']):<13}")
        for arm in arms:
            u = a['arms'][arm]['top_unknown']
            q = quantiles(u)
            line += (f"{q['median']:.2f} [{min(u):.2f}-{max(u):.2f}]".ljust(24)
                     if q['n'] else 'neutral'.ljust(24))
        line += ('/'.join(_fmt(a['arms'][arm]['taken_rank']) for arm in arms)).rjust(26)
        print(line)

    for arm in arms:
        b = s['arms'][arm]
        print(f"\n  {arm}: top-10 unknown {_q(b['top10_unknown'])}")
        print(f"      share of served tests inside u*+-tol [{U_STAR - U_TOL:.2f}, "
              f"{U_STAR + U_TOL:.2f}]: {_fmt(b['top10_in_band'])}")
        print(f"      top-10 difficulty {_q(b['top10_difficulty'])}")
        print(f"      neutral slots {b['neutral_slots']}/{b['slots']}; "
              f"taken test's rank {_q(b['taken_rank'])}")
        print(f"      M5 smallest per-attempt pool {b['min_pool']} "
              f"(min delta vs {arms[0]}: {s['M5_min_pool_delta'][arm]})")

    print('\n  mean top-10 overlap between arms (Jaccard):')
    for pair, v in s['mean_overlap'].items():
        print(f'      {pair:<18} {_fmt(v)}')
    print(f"\n  Spearman(unknown of the taken test, its score): "
          f"{_fmt(s['spearman_taken_unknown_vs_pct'], 3)}"
          f"   [arm-independent: the taken test's unknown share is the same in every arm]")


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--since', help='ISO timestamp lower bound on attempts')
    ap.add_argument('--until', help='ISO timestamp upper bound on attempts (default: now)')
    ap.add_argument('--replay-language', type=int, default=3,
                    help='language_id to replay (default 3 = ja; 0 to skip)')
    ap.add_argument('--no-served', action='store_true', help='skip M4/M5')
    ap.add_argument('--json', help='write the full result as JSON to this path')
    ap.add_argument('--shadow-out', help='append an all-arms JSONL snapshot to this directory')
    ap.add_argument('--arms', default=','.join(ARMS),
                    help=f'comma-separated subset of {",".join(ARMS)} (default: all three)')
    args = ap.parse_args()

    arms = tuple(a.strip() for a in args.arms.split(',') if a.strip())
    unknown = [a for a in arms if a not in ARM_SPEC]
    if unknown:
        raise SystemExit(f'unknown arm(s) {unknown}; choose from {list(ARM_SPEC)}')

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    type_codes = fetch_type_codes(db)
    attempts = fetch_attempts(db, args.since, args.until)
    result: dict = {'window': {'since': args.since, 'until': args.until},
                    'attempt_metrics': attempt_metrics(attempts, type_codes)}
    print_attempt_metrics(result['attempt_metrics'])

    pairs = sorted({(a['user_id'], int(a['language_id'])) for a in attempts})
    if not args.no_served:
        result['served'] = served_metrics(db, pairs, arms)
        print_served(result['served'])

    if args.replay_language:
        result['replay'] = replay(db, attempts, args.replay_language, arms)
        print_replay(result['replay'], args.replay_language)

    if args.shadow_out:
        os.makedirs(args.shadow_out, exist_ok=True)
        stamp = datetime.now(timezone.utc)
        path = os.path.join(args.shadow_out, f'{stamp:%Y-%m-%d}.jsonl')
        snap = collect(db, [(u, l, None) for u, l in pairs], arms)
        with open(path, 'a', encoding='utf-8') as fh:
            for user_id, lang in pairs:
                key = (user_id, lang, None)
                fh.write(json.dumps({
                    'at': stamp.isoformat(), 'user_id': user_id, 'language_id': lang,
                    'arms': {arm: [{k: r[k] for k in ('test_id', 'test_type', 'rank_in_type',
                                                      'score', 'unknown_share', 'vocab_neutral')}
                                   for r in snap[arm][key] if r['rank_in_type'] <= TOP_N]
                             for arm in arms},
                }, ensure_ascii=False) + '\n')
        print(f'\nshadow snapshot appended to {path}')

    final = read_tuning(db)
    result['selection_tuning_after'] = final
    print(f"\nselection_tuning after the run: vocab_weight={final.get('vocab_weight')}, "
          f"combine_mode={final.get('combine_mode')!r}")
    if str(final.get('combine_mode')) != 'sum':
        print("  WARNING: combine_mode is not back at 'sum'. It is inert while "
              "vocab_weight = 0, but restore it:")
        print("  UPDATE selection_tuning SET value_text = 'sum' WHERE key = 'combine_mode';")

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2, default=str)
        print(f'\nfull result written to {args.json}')


if __name__ == '__main__':
    main()
