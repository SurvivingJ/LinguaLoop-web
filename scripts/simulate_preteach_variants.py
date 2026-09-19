#!/usr/bin/env python3
"""TASK-782 — simulate lookahead pre-teaching variants.

READ-ONLY. Writes nothing to the database. Safe to re-run.

The question: if the daily session pre-teaches the vocabulary that blocks an
upcoming test, using the practice engine's ladder, how many words must be
taught, which words, how deep, and does the test actually land in the
5-25% unknown band afterwards?

This harness scores that counterfactually over the live catalogue. It does NOT
observe learners taking pre-taught tests -- no such data exists yet. It
measures the *reachability* of the intervention under today's content
inventory and the study plan's intake budget, which is what actually gates it.

Variant axes (features/lookahead-preteaching.tech.md Section 4):

  A  target selection   a1_commit    one pinned test per cycle
                        a2_cohort    the vocabulary shared by the top-N pool
                        a3_demand    catalogue-wide demand ranking, no target
  B  preview depth      b1_preview   Ring 1 only        -> p_known ~= 0.65
                        b2_working   Ring 2 cleared     -> p_known ~= 0.85
                        b3_mastery   Gate A passed      -> p_known ~= 0.92
  C  word ranking       c1_frequency most test occurrences first
                        c2_frontier  nearest the learner's frontier first
                        c3_greedy    max unknown-share reduction per minute

Outcome per variant: words taught, minutes of practice, share of the catalogue
brought inside the target band, and how much of that is blocked by missing
exercises (the supply gate) rather than by the algorithm.

p_known follows features/vocabulary-aware-test-selection.tech.md Section 3.2
verbatim: the uvk row when one exists, else
sigma(1.5 * (zipf - ability_zipf) + ln(0.85/0.15)).

Usage::

    PYTHONPATH=. PYTHONIOENCODING=utf-8 \\
        python scripts/simulate_preteach_variants.py --language 3
    PYTHONPATH=. python scripts/simulate_preteach_variants.py \\
        --language 3 --json-out sandbox/preteach_ja.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence

# --- constants mirroring live config ----------------------------------------

U_STAR = 0.15           # selection_tuning target unknown share
U_BAND = (0.05, 0.25)   # the band measure_selection_quality reports
PRIOR_OFFSET = math.log(0.85 / 0.15)   # 1.7346 -- tech spec Section 3.2 correction (a)
PRIOR_SLOPE = 1.5
UNKNOWN_CUT = 0.50      # a sense is "blocking" below this p_known

# practice_session_service.LADDER_MIN_EXERCISES_PER_SENSE
SUPPLY_GATE_MIN_EXERCISES = 3

# Post-teaching p_known by depth, and the item cost to get there.
# Items per word come from the ladder's ring requirements
# (algorithms/vocabulary-ladder.md: R1 = 1 family, R2 = 3 families), doubled
# because a family needs first-attempt successes on 2 distinct calendar days.
DEPTHS = {
    'b1_preview': {'p_known': 0.65, 'items': 4,  'min_days': 2},
    'b2_working': {'p_known': 0.85, 'items': 12, 'min_days': 3},
    'b3_mastery': {'p_known': 0.92, 'items': 20, 'min_days': 5},
}
SECONDS_PER_ITEM = 45   # practice_session_service.DEFAULT_EXPECTED_SECONDS

# --- per-word cost model (TASK-782b) ----------------------------------------
#
# The flat `items` above charge every word the same, which structurally favours
# least-known-first: same price, bigger gain. Once we rank by points per MINUTE
# the cost has to vary with how well the word is already known.
#
# A word cannot clear Ring 2 in fewer than RING2_FLOOR_ITEMS attempts whatever
# its starting p_known -- 3 required families x first-attempt successes on 2
# distinct calendar days is a structural floor, not a learning curve.
# Above the floor, cost is proportional to the ground to be covered, scaled by
# kappa:
#
#   kappa =  0   cost per POINT of gain is constant  (neutral)
#   kappa >  0   unfamiliar words cost MORE per point (favours frontier-first)
#   kappa <  0   unfamiliar words cost LESS per point (favours least-known)
#
# kappa is NOT measurable from live data yet: it needs attempts-to-Ring-2
# against starting p_known, and there are 15 exercise_attempts in total. It is
# exposed so the sensitivity of the answer is visible rather than assumed.
RING2_FLOOR_ITEMS = 6
GAIN_PER_ITEM = 0.0667          # calibrated so a p_known=0.05 word costs 12 items


def items_for(pk: float, depth: str, kappa: float) -> float:
    """Practice items to lift a word from `pk` to this depth's target."""
    spec = DEPTHS[depth]
    gap = max(0.0, spec['p_known'] - pk)
    if gap <= 0:
        return 0.0
    cost_per_point = (1.0 + kappa * (1.0 - pk)) / GAIN_PER_ITEM
    floor = RING2_FLOOR_ITEMS if depth != 'b1_preview' else 2
    return max(float(floor), gap * cost_per_point)


def value_per_minute(pk: float, depth: str, kappa: float) -> float:
    """p_known points gained per minute of practice -- the axis-C objective."""
    n = items_for(pk, depth, kappa)
    if n <= 0:
        return 0.0
    gap = max(0.0, DEPTHS[depth]['p_known'] - pk)
    return gap / (n * SECONDS_PER_ITEM / 60.0)

PAGE = 1000


# --- data access -------------------------------------------------------------

def _page_all(query_factory, page: int = PAGE) -> List[dict]:
    """Drain a PostgREST query that may exceed the row cap."""
    out: List[dict] = []
    start = 0
    while True:
        resp = query_factory().range(start, start + page - 1).execute()
        rows = resp.data or []
        out.extend(rows)
        if len(rows) < page:
            return out
        start += page


def load_snapshot(db, language_id: int, user_id: str) -> Dict[str, Any]:
    """Everything the simulation needs, in a handful of bulk reads."""
    tests = _page_all(lambda: db.table('tests')
                      .select('id, vocab_sense_ids')
                      .eq('language_id', language_id))
    tests = [t for t in tests if t.get('vocab_sense_ids')]

    senses = _page_all(lambda: db.table('dim_word_senses')
                       .select('id, vocab_id')
                       .eq('word_language_id', language_id))
    vocab = _page_all(lambda: db.table('dim_vocabulary')
                      .select('id, frequency_rank')
                      .eq('language_id', language_id))
    zipf_by_vocab = {v['id']: v['frequency_rank'] for v in vocab
                     if v.get('frequency_rank') is not None}
    zipf = {s['id']: zipf_by_vocab[s['vocab_id']] for s in senses
            if s.get('vocab_id') in zipf_by_vocab}

    uvk = _page_all(lambda: db.table('user_vocabulary_knowledge')
                    .select('sense_id, p_known')
                    .eq('user_id', user_id)
                    .eq('language_id', language_id))
    p_known_rows = {r['sense_id']: float(r['p_known']) for r in uvk
                    if r.get('p_known') is not None}

    ex = _page_all(lambda: db.table('exercises')
                   .select('word_sense_id, ladder_level')
                   .eq('language_id', language_id)
                   .eq('is_active', True)
                   .not_.is_('word_sense_id', 'null'))
    n_ex: Dict[int, int] = defaultdict(int)
    n_ladder: Dict[int, int] = defaultdict(int)
    for row in ex:
        sid = row['word_sense_id']
        n_ex[sid] += 1
        if row.get('ladder_level') is not None:
            n_ladder[sid] += 1

    return {'tests': tests, 'zipf': zipf, 'p_known_rows': p_known_rows,
            'n_ex': dict(n_ex), 'n_ladder': dict(n_ladder)}


def ability_zipf(db, user_id: str, language_id: int) -> Optional[float]:
    """selection_vocab_ability(), the live 85%-crossing fallback."""
    resp = db.rpc('selection_vocab_ability', {
        'p_user_id': user_id, 'p_language_id': language_id,
        'p_as_of': None,
    }).execute()
    data = resp.data
    # PostgREST returns the composite as a single-row list of its fields.
    if isinstance(data, list):
        data = data[0] if data else None
    if isinstance(data, dict):
        val = data.get('ability_zipf')
        return float(val) if val is not None else None
    if isinstance(data, (int, float)):
        return float(data)
    return None


# --- the model ---------------------------------------------------------------

def p_known(sense_id: int, snap: Dict[str, Any], az: float) -> Optional[float]:
    """Tech spec Section 3.2. None when the sense has no Zipf and no uvk row."""
    row = snap['p_known_rows'].get(sense_id)
    if row is not None:
        return row
    z = snap['zipf'].get(sense_id)
    if z is None:
        return None
    return 1.0 / (1.0 + math.exp(-(PRIOR_SLOPE * (z - az) + PRIOR_OFFSET)))


def resolve_tests(snap: Dict[str, Any], az: float) -> List[dict]:
    """Per test: resolved senses with p_known, and the current unknown share."""
    out = []
    for t in snap['tests']:
        pairs = []
        for sid in t['vocab_sense_ids']:
            pk = p_known(sid, snap, az)
            if pk is not None:
                pairs.append((sid, pk))
        if len(pairs) < 5:
            continue   # tech spec Section 3.4 neutral
        unknown = 1.0 - sum(pk for _, pk in pairs) / len(pairs)
        out.append({'test_id': t['id'], 'senses': pairs, 'n': len(pairs),
                    'unknown': unknown})
    return out


def servable(sense_id: int, snap: Dict[str, Any], ladder_only: bool) -> bool:
    """The live supply gate: enough active exercises to actually drill.

    ``snap['ignore_supply']`` lifts the gate. That arm is not a proposal -- it
    is the ceiling the algorithm would reach if every blocking sense had
    exercises, and the gap between it and the gated arm is exactly the content
    debt.
    """
    if snap.get('ignore_supply'):
        return True
    counts = snap['n_ladder'] if ladder_only else snap['n_ex']
    return counts.get(sense_id, 0) >= SUPPLY_GATE_MIN_EXERCISES


def rank_words(blocking: Sequence[tuple], variant: str,
               doc_freq: Dict[int, int]) -> List[tuple]:
    """Order the blocking senses of one test under word-ranking variant C."""
    if variant == 'c1_frequency':
        return sorted(blocking, key=lambda sp: (-doc_freq.get(sp[0], 0), sp[0]))
    if variant == 'c2_frontier':
        # closest to the frontier first -- steepest expected learning
        return sorted(blocking, key=lambda sp: (-sp[1], sp[0]))
    if variant == 'c3_greedy':
        # biggest p_known lift per word, i.e. the least-known first
        return sorted(blocking, key=lambda sp: (sp[1], sp[0]))
    if variant.startswith('c4_per_minute'):
        # points of p_known gained per minute of practice -- cost-aware
        kappa = float(variant.split(':')[1]) if ':' in variant else 0.0
        depth = variant.split('@')[1].split(':')[0] if '@' in variant else 'b2_working'
        return sorted(blocking,
                      key=lambda sp: (-value_per_minute(sp[1], depth, kappa), sp[0]))
    raise ValueError(variant)


def teach(test: dict, order: Sequence[tuple], depth: str,
          snap: Dict[str, Any], ladder_only: bool,
          budget: Optional[int], kappa: float = 0.0,
          minute_budget: Optional[float] = None) -> dict:
    """Walk the ranked words, teaching until the test reaches U_STAR."""
    spec = DEPTHS[depth]
    target_pk = spec['p_known']
    total_pk = sum(pk for _, pk in test['senses'])
    n = test['n']
    taught: List[int] = []
    starved: List[int] = []
    items = 0.0
    for sid, pk in order:
        if minute_budget is not None and                 items * SECONDS_PER_ITEM / 60.0 >= minute_budget:
            break
        if 1.0 - total_pk / n <= U_STAR:
            break
        if budget is not None and len(taught) >= budget:
            break
        if target_pk <= pk:
            continue
        if not servable(sid, snap, ladder_only):
            starved.append(sid)
            continue
        total_pk += (target_pk - pk)
        taught.append(sid)
        items += items_for(pk, depth, kappa)
    unknown_after = 1.0 - total_pk / n
    minutes = items * SECONDS_PER_ITEM / 60.0
    return {'taught': taught, 'starved': starved,
            'unknown_after': unknown_after, 'minutes': minutes,
            'in_band': U_BAND[0] <= unknown_after <= U_BAND[1]}


def unconstrained_need(test: dict, order: Sequence[tuple], depth: str) -> int:
    """Words needed if every word were servable -- the algorithm's own demand."""
    spec = DEPTHS[depth]
    target_pk = spec['p_known']
    total_pk = sum(pk for _, pk in test['senses'])
    n, k = test['n'], 0
    for _sid, pk in order:
        if 1.0 - total_pk / n <= U_STAR:
            break
        if target_pk <= pk:
            continue
        total_pk += (target_pk - pk)
        k += 1
    return k


# --- variants ----------------------------------------------------------------

def doc_frequencies(tests: Sequence[dict]) -> Dict[int, int]:
    df: Dict[int, int] = defaultdict(int)
    for t in tests:
        for sid, _pk in t['senses']:
            df[sid] += 1
    return dict(df)


def run_a1_commit(tests, depth, word_variant, snap, df, ladder_only, budget,
                  kappa=0.0, minute_budget=None):
    """One test at a time, taught in isolation."""
    rows = []
    for t in tests:
        blocking = [(s, pk) for s, pk in t['senses'] if pk < UNKNOWN_CUT]
        order = rank_words(blocking, word_variant, df)
        res = teach(t, order, depth, snap, ladder_only, budget, kappa,
                    minute_budget)
        res['need_unconstrained'] = unconstrained_need(t, order, depth)
        res['test_id'] = t['test_id']
        res['unknown_before'] = t['unknown']
        rows.append(res)
    return rows


def run_a3_demand(tests, depth, snap, ladder_only, n_senses):
    """Teach the top-N catalogue-wide blocking senses; then score every test.

    No target test is chosen. This is the cheapest thing to build and the
    baseline every targeted variant has to beat.
    """
    df: Dict[int, int] = defaultdict(int)
    pk_of: Dict[int, float] = {}
    for t in tests:
        for sid, pk in t['senses']:
            if pk < UNKNOWN_CUT:
                df[sid] += 1
                pk_of[sid] = pk
    ranked = sorted(df.items(), key=lambda kv: (-kv[1], kv[0]))
    taught, starved = [], []
    for sid, _n in ranked:
        if len(taught) >= n_senses:
            break
        (taught if servable(sid, snap, ladder_only) else starved).append(sid)
    taught_set = set(taught)
    target_pk = DEPTHS[depth]['p_known']

    rows = []
    for t in tests:
        total_pk = sum(max(pk, target_pk) if sid in taught_set else pk
                       for sid, pk in t['senses'])
        ua = 1.0 - total_pk / t['n']
        rows.append({'test_id': t['test_id'], 'unknown_before': t['unknown'],
                     'unknown_after': ua,
                     'in_band': U_BAND[0] <= ua <= U_BAND[1],
                     'taught': taught, 'starved': starved,
                     'minutes': len(taught) * DEPTHS[depth]['items']
                                * SECONDS_PER_ITEM / 60.0,
                     'need_unconstrained': 0})
    return rows, taught, starved


def run_a2_cohort(tests, depth, snap, ladder_only, top_n, budget):
    """Teach the vocabulary shared across the top-N nearest-band tests.

    No single test is committed to; the cohort is whatever the ranker would
    plausibly serve next. Shared words pay off across every test in the pool.
    """
    pool = sorted(tests, key=lambda t: abs(t['unknown'] - U_STAR))[:top_n]
    df: Dict[int, int] = defaultdict(int)
    pk_of: Dict[int, float] = {}
    for t in pool:
        for sid, pk in t['senses']:
            if pk < UNKNOWN_CUT:
                df[sid] += 1
                pk_of[sid] = pk
    ranked = sorted(df.items(), key=lambda kv: (-kv[1], kv[0]))
    taught, starved = [], []
    for sid, _n in ranked:
        if len(taught) >= budget:
            break
        (taught if servable(sid, snap, ladder_only) else starved).append(sid)
    taught_set = set(taught)
    target_pk = DEPTHS[depth]['p_known']

    rows = []
    for t in pool:
        total_pk = sum(max(pk, target_pk) if sid in taught_set else pk
                       for sid, pk in t['senses'])
        ua = 1.0 - total_pk / t['n']
        rows.append({'test_id': t['test_id'], 'unknown_before': t['unknown'],
                     'unknown_after': ua,
                     'in_band': U_BAND[0] <= ua <= U_BAND[1],
                     'taught': taught, 'starved': starved,
                     'minutes': len(taught) * DEPTHS[depth]['items']
                                * SECONDS_PER_ITEM / 60.0,
                     'need_unconstrained': 0})
    return rows, taught, starved


# --- reporting ---------------------------------------------------------------

def summarise(name: str, rows: Sequence[dict], n_tests: int) -> dict:
    if not rows:
        return {'variant': name, 'tests': 0}
    in_band = sum(1 for r in rows if r['in_band'])
    taught = [len(r['taught']) for r in rows]
    starved = [len(r['starved']) for r in rows]
    need = [r.get('need_unconstrained', 0) for r in rows]
    return {
        'variant': name,
        'tests': len(rows),
        'in_band': in_band,
        'in_band_share': round(in_band / len(rows), 3),
        'mean_unknown_before': round(
            sum(r['unknown_before'] for r in rows) / len(rows), 3),
        'mean_unknown_after': round(
            sum(r['unknown_after'] for r in rows) / len(rows), 3),
        'mean_words_taught': round(sum(taught) / len(rows), 1),
        'mean_words_starved': round(sum(starved) / len(rows), 1),
        'mean_words_needed': round(sum(need) / len(rows), 1),
        'mean_minutes': round(sum(r['minutes'] for r in rows) / len(rows), 1),
    }


def print_table(title: str, summaries: Sequence[dict]) -> None:
    print()
    print(title)
    print('-' * len(title))
    hdr = (f"{'variant':<34}{'tests':>6}{'in band':>9}{'u_before':>10}"
           f"{'u_after':>9}{'taught':>8}{'starved':>9}{'needed':>8}{'min':>8}")
    print(hdr)
    for s in summaries:
        if not s.get('tests'):
            print(f"{s['variant']:<34}{'--':>6}")
            continue
        print(f"{s['variant']:<34}{s['tests']:>6}"
              f"{s['in_band_share']:>9.3f}{s['mean_unknown_before']:>10.3f}"
              f"{s['mean_unknown_after']:>9.3f}{s['mean_words_taught']:>8.1f}"
              f"{s['mean_words_starved']:>9.1f}{s['mean_words_needed']:>8.1f}"
              f"{s['mean_minutes']:>8.1f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--language', type=int, required=True,
                    help='dim_languages.id (1=zh, 2=en, 3=ja)')
    ap.add_argument('--user', default=None,
                    help='user uuid; defaults to the one with the most uvk rows')
    ap.add_argument('--budget', type=int, default=None,
                    help='max words taught per cycle (default: unbounded)')
    ap.add_argument('--ladder-only', action='store_true',
                    help='count only ladder_level exercises toward supply')
    ap.add_argument('--ignore-supply', action='store_true',
                    help='lift the supply gate -- measures the content ceiling')
    ap.add_argument('--json-out', default=None)
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), '.env'))
    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    user_id = args.user
    if not user_id:
        resp = (db.table('user_vocabulary_knowledge').select('user_id')
                .eq('language_id', args.language).limit(1).execute())
        if not resp.data:
            raise SystemExit(f'no uvk rows for language {args.language}')
        user_id = resp.data[0]['user_id']

    az = ability_zipf(db, user_id, args.language)
    if az is None:
        raise SystemExit('ability_zipf not identifiable; term would be neutral')

    snap = load_snapshot(db, args.language, user_id)
    snap['ignore_supply'] = args.ignore_supply
    tests = resolve_tests(snap, az)
    df = doc_frequencies(tests)

    print(f'language={args.language} user={user_id} ability_zipf={az:.4f}')
    print(f'tests resolved={len(tests)}  distinct senses={len(df)}  '
          f'supply={"IGNORED (ceiling arm)" if args.ignore_supply else ("ladder only" if args.ladder_only else "any exercise")}')
    baseline = sum(1 for t in tests if U_BAND[0] <= t['unknown'] <= U_BAND[1])
    print(f'baseline in band (no teaching) = {baseline}/{len(tests)} '
          f'({baseline / max(len(tests), 1):.3f})')

    out: Dict[str, Any] = {'language': args.language, 'user': user_id,
                           'ability_zipf': az, 'tests': len(tests),
                           'baseline_in_band': baseline, 'summaries': []}

    # --- axis B x C under A1 ------------------------------------------------
    sums = []
    for depth in DEPTHS:
        for wv in ('c1_frequency', 'c2_frontier', 'c3_greedy'):
            rows = run_a1_commit(tests, depth, wv, snap, df,
                                 args.ladder_only, args.budget)
            sums.append(summarise(f'a1_commit/{depth}/{wv}', rows, len(tests)))
    print_table('A1 commit -- one pinned test per cycle', sums)
    out['summaries'].extend(sums)

    # --- axis C under an equal MINUTE budget (TASK-782b) --------------------
    # The honest comparison for "points per minute": every arm gets the same
    # practice time, not the same word count. kappa sweeps the cost model,
    # which is not yet measurable from live data (15 exercise_attempts total).
    for mins in (30.0, 60.0):
        sums = []
        for kappa in (-0.5, 0.0, 0.5, 1.0):
            for wv in ('c1_frequency', 'c2_frontier', 'c3_greedy',
                       f'c4_per_minute@b2_working:{kappa}'):
                rows = run_a1_commit(tests, 'b2_working', wv, snap, df,
                                     args.ladder_only, None, kappa, mins)
                label = wv.split('@')[0]
                sums.append(summarise(f'k={kappa:+.1f} / {label}', rows,
                                      len(tests)))
        print_table(
            f'Axis C at an equal budget of {mins:.0f} practice minutes '
            f'(b2_working)', sums)
        out['summaries'].extend(sums)

    # --- A2 cohort ----------------------------------------------------------
    sums = []
    for depth in DEPTHS:
        rows, taught, starved = run_a2_cohort(
            tests, depth, snap, args.ladder_only, top_n=10,
            budget=args.budget or 25)
        s = summarise(f'a2_cohort10/{depth}', rows, len(tests))
        s['unique_words_taught'] = len(taught)
        s['unique_words_starved'] = len(starved)
        sums.append(s)
    print_table('A2 cohort -- shared vocabulary of the top-10 pool', sums)
    out['summaries'].extend(sums)

    # --- A3 demand ----------------------------------------------------------
    sums = []
    for n in (50, 200, 500, 1500):
        rows, taught, starved = run_a3_demand(
            tests, 'b2_working', snap, args.ladder_only, n)
        s = summarise(f'a3_demand{n}/b2_working', rows, len(tests))
        s['unique_words_taught'] = len(taught)
        s['unique_words_starved'] = len(starved)
        sums.append(s)
    print_table('A3 demand -- catalogue-wide, no target test', sums)
    out['summaries'].extend(sums)

    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out) or '.', exist_ok=True)
        with open(args.json_out, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, indent=2)
        print(f'\nwrote {args.json_out}')


if __name__ == '__main__':
    main()
