#!/usr/bin/env python3
"""Check calibration_zh_tone_variants() against services/placement_tones (TASK-1092). Read-only.

For every zh pool reading it calls the SQL function and the Python reference with the same
inventory and the same lemma readings, and compares the two lists (set, then order). It also
rebuilds the inventory in Python from the native zh readings and compares it with
calibration_zh_tone_inventory, checks that no SQL variant uses a syllable+tone the inventory
does not list, and prints the tone-variant coverage per Zipf band (ADR-060, tech §2 rule 4;
the research measure is 3,622 of 3,656 pool readings with ≥ 1 variant, band 7 94.8%).

Readings checked:
  * per pool lemma (calibration_anchor_pool, zh/zh, has_pronunciation), the key K: the native
    rank-1 standard reading (lowest sense_rank, then id), else the pool row's reading;
  * every distinct pool-row reading as well (the pool keeps its own snapshot of the reading);
  * with --all-readings, every native zh reading in dim_word_senses (stress test).
Coverage is reported on the keys.

Exit status 1 when any list differs or a variant uses an unattested syllable+tone.

Usage::

    python scripts/verify_zh_tone_variants.py                  # live, the app's service-role client
    python scripts/verify_zh_tone_variants.py --all-readings
    python scripts/verify_zh_tone_variants.py --psql "host=/tmp port=55433 dbname=zhu user=postgres"
                                                               # a local Postgres (psql on PATH)
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from _common import admin_db, bootstrap, paginate
except ImportError:  # run or imported as scripts.<name>
    from scripts._common import admin_db, bootstrap, paginate

bootstrap(log_level=None)

from services import placement_tones as pt  # noqa: E402

ZH = 1
SHOW = 20


# ---------------------------------------------------------------------------
# Sources: the same five reads over PostgREST (live) or psql (a local copy)
# ---------------------------------------------------------------------------
class SupabaseSource:
    def __init__(self, workers: int):
        self.db = admin_db()
        self.workers = workers

    def inventory(self) -> List[dict]:
        return list(paginate(lambda: self.db.table('calibration_zh_tone_inventory')
                             .select('base, tones').order('base')))

    def native_readings(self) -> List[dict]:
        return list(paginate(lambda: self.db.table('dim_word_senses')
                             .select('id, vocab_id, pronunciation, definition_level, sense_rank')
                             .eq('word_language_id', ZH).eq('definition_language_id', ZH)
                             .not_.is_('pronunciation', 'null').order('id')))

    def pool(self) -> List[dict]:
        return list(paginate(lambda: self.db.table('calibration_anchor_pool')
                             .select('sense_id, vocab_id, lemma, pronunciation, zipf_band')
                             .eq('word_language_id', ZH).eq('definition_language_id', ZH)
                             .eq('has_pronunciation', True).order('sense_id')))

    def lemmas(self) -> Dict[int, str]:
        rows = paginate(lambda: self.db.table('dim_vocabulary').select('id, lemma')
                        .eq('language_id', ZH).order('id'))
        return {int(r['id']): r['lemma'] for r in rows}

    def variants(self, items: List[Tuple[str, int]]) -> List[List[str]]:
        def one(item):
            reading, vocab_id = item
            data = self.db.rpc('calibration_zh_tone_variants',
                               {'p_pronunciation': reading, 'p_vocab_id': vocab_id}).execute().data
            return list(data or [])
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            return list(ex.map(one, items))


class PsqlSource:
    """A local Postgres through the psql client (no driver needed): one JSON result per query."""

    def __init__(self, conninfo: str):
        self.conninfo = conninfo

    def _json(self, sql: str):
        out = subprocess.run(
            ['psql', self.conninfo, '-X', '-A', '-t', '-q', '-v', 'ON_ERROR_STOP=1', '-f', '-'],
            input=f"SELECT coalesce(json_agg(t), '[]') FROM ({sql}) t;", capture_output=True,
            text=True, encoding='utf-8', check=True)
        return json.loads(out.stdout)

    def inventory(self) -> List[dict]:
        return self._json('SELECT base, tones FROM calibration_zh_tone_inventory ORDER BY base')

    def native_readings(self) -> List[dict]:
        return self._json(
            'SELECT id, vocab_id, pronunciation, definition_level, sense_rank FROM dim_word_senses'
            f' WHERE word_language_id = {ZH} AND definition_language_id = {ZH}'
            ' AND pronunciation IS NOT NULL ORDER BY id')

    def pool(self) -> List[dict]:
        return self._json(
            'SELECT sense_id, vocab_id, lemma, pronunciation, zipf_band FROM calibration_anchor_pool'
            f' WHERE word_language_id = {ZH} AND definition_language_id = {ZH}'
            ' AND has_pronunciation ORDER BY sense_id')

    def lemmas(self) -> Dict[int, str]:
        return {int(r['id']): r['lemma'] for r in self._json(
            f'SELECT id, lemma FROM dim_vocabulary WHERE language_id = {ZH} ORDER BY id')}

    def variants(self, items: List[Tuple[str, int]]) -> List[List[str]]:
        payload = json.dumps([{'i': i, 'r': r, 'v': v} for i, (r, v) in enumerate(items)],
                             ensure_ascii=False)
        assert '$in$' not in payload
        rows = self._json(
            'SELECT x.i, calibration_zh_tone_variants(x.r, x.v) AS out'
            f' FROM jsonb_to_recordset($in${payload}$in$::jsonb) AS x(i int, r text, v int)'
            ' ORDER BY x.i')
        return [list(r['out'] or []) for r in rows]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def compare_inventory(db_rows: List[dict], native: List[dict]) -> Tuple[Dict[str, frozenset], int]:
    db_inv = {r['base']: frozenset(int(t) for t in (r['tones'] or [])) for r in db_rows}
    py_inv = pt.build_inventory(r['pronunciation'] for r in native)
    diff = sorted(b for b in set(db_inv) | set(py_inv) if db_inv.get(b) != py_inv.get(b))
    n_full = [len(t) for t in db_inv.values()]
    print('--- inventory ---')
    print(f'calibration_zh_tone_inventory: {len(db_inv)} bases, '
          f'{sum(n_full) / max(len(n_full), 1):.2f} attested full tones per base; '
          f'Python rebuild from {len(native)} native readings: {len(py_inv)} bases; '
          f'differing bases: {len(diff)}')
    for b in diff[:SHOW]:
        print(f'  {b}: db={sorted(db_inv.get(b, []))} python={sorted(py_inv.get(b, []))}')
    return db_inv, len(diff)


def unattested(variant: str, inv: Dict[str, frozenset]) -> List[str]:
    """Full-tone syllables of a variant whose tone the inventory does not list."""
    return [s.text for s in pt.parse(variant)
            if s.base is not None and s.tone in pt.FULL_TONES and s.tone not in inv.get(s.base, ())]


def keys_per_lemma(pool: List[dict], native: List[dict]) -> Dict[int, dict]:
    """vocab_id -> {reading, lemma, band}: the native rank-1 standard reading, else the pool's."""
    best: Dict[int, dict] = {}
    for r in native:
        if r['definition_level'] != 'standard':
            continue
        v = int(r['vocab_id'])
        rank = (r['sense_rank'] if r['sense_rank'] is not None else 1 << 30, r['id'])
        if v not in best or rank < best[v]['rank']:
            best[v] = {'rank': rank, 'reading': r['pronunciation']}
    out: Dict[int, dict] = {}
    for p in pool:
        v = int(p['vocab_id'])
        if v in out:
            continue
        out[v] = {'reading': best[v]['reading'] if v in best else p['pronunciation'],
                  'lemma': p['lemma'], 'band': int(p['zipf_band'])}
    return out


def coverage(keys: Dict[int, dict], results: Dict[Tuple[str, int], List[str]]) -> None:
    by_band: Dict[int, List[int]] = collections.defaultdict(list)
    for v, k in keys.items():
        by_band[k['band']].append(len(results[(k['reading'], v)]))
    allc = [c for cs in by_band.values() for c in cs]

    def pct(cs, m):
        return 100.0 * sum(c >= m for c in cs) / max(len(cs), 1)

    print('--- coverage (pool keys, SQL output) ---')
    print(f'all: n {len(allc)}  >=1 {sum(c >= 1 for c in allc)} ({pct(allc, 1):.1f}%)  '
          f'>=2 {pct(allc, 2):.1f}%  >=3 {pct(allc, 3):.1f}%')
    for b in sorted(by_band):
        cs = by_band[b]
        print(f'  band {b}: n {len(cs):4d}  >=1 {pct(cs, 1):5.1f}%  >=2 {pct(cs, 2):5.1f}%  '
              f'>=3 {pct(cs, 3):5.1f}%')
    none = [(keys[v]['lemma'], keys[v]['reading']) for v in keys
            if not results[(keys[v]['reading'], v)]]
    print(f'keys with no variant: {len(none)}', none[:SHOW])


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--psql', metavar='CONNINFO',
                    help='read a local Postgres through psql instead of the live Supabase project')
    ap.add_argument('--all-readings', action='store_true',
                    help='also compare every native zh reading, not only the pool readings')
    ap.add_argument('--workers', type=int, default=8, help='parallel RPC calls (live only)')
    args = ap.parse_args(list(argv) if argv is not None else None)

    src = PsqlSource(args.psql) if args.psql else SupabaseSource(args.workers)
    native = src.native_readings()
    db_inv, inv_diff = compare_inventory(src.inventory(), native)
    pool = src.pool()
    keys = keys_per_lemma(pool, native)

    lemma_of = {int(p['vocab_id']): p['lemma'] for p in pool}
    items = {(k['reading'], v) for v, k in keys.items()}
    items |= {(p['pronunciation'], int(p['vocab_id'])) for p in pool if p['pronunciation']}
    if args.all_readings:
        lemma_of.update(src.lemmas())
        items |= {(r['pronunciation'], int(r['vocab_id'])) for r in native}
    items_l = sorted(items, key=lambda x: (x[1], x[0]))
    own: Dict[int, List[str]] = collections.defaultdict(list)
    for r in native:
        own[int(r['vocab_id'])].append(r['pronunciation'])

    print(f'--- comparing {len(items_l)} readings ({len(keys)} pool lemmas, {len(pool)} pool rows'
          f'{", all native readings" if args.all_readings else ""}) ---')
    sql_out = src.variants(items_l)
    results = dict(zip(items_l, sql_out))
    set_diff, order_diff, bad_pairs, n_variants = [], 0, [], 0
    for (reading, v), got in results.items():
        want = pt.variants(reading, lemma_of.get(v), db_inv, own.get(v, ()))
        n_variants += len(got)
        if set(got) != set(want) or len(got) != len(want):
            set_diff.append((lemma_of.get(v), reading, sorted(set(got) - set(want)),
                             sorted(set(want) - set(got))))
        elif got != want:
            order_diff += 1
        for g in got:
            u = unattested(g, db_inv)
            if u:
                bad_pairs.append((reading, g, u))
    print(f'set mismatches: {len(set_diff)}; order mismatches: {order_diff}; '
          f'variants checked: {n_variants}; variants with an unattested syllable+tone: {len(bad_pairs)}')
    for lemma, reading, sql_only, py_only in set_diff[:SHOW]:
        print(f'  {lemma} {reading!r}: sql only {sql_only} | python only {py_only}')
    for b in bad_pairs[:SHOW]:
        print('  unattested:', b)
    coverage(keys, results)
    return 1 if (set_diff or order_diff or bad_pairs or inv_diff) else 0


if __name__ == '__main__':
    sys.exit(main())
