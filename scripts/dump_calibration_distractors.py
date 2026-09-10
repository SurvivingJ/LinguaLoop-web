#!/usr/bin/env python3
"""Sample Calibration items from semantic_distractors() and dump them for reading.

The point of this script is NOT to assert that the RPC returns rows. It is to put
real items in front of a human, because the only failure mode that matters here is
invisible to a unit test: distractors that are not TEMPTING. A picker can return
three perfectly well-formed, correctly-banded, frequency-matched options that a
learner discards at a glance, and every automated check still passes.

It also counts the failure modes that CAN be checked mechanically, per pair:
  * a distractor sharing the anchor's vocab_id (the sibling leak — must be 0)
  * an option whose definition is just the lemma repeated
  * an option identical to the anchor's own definition
  * duplicate options within one item
  * items that came back short of the requested count

Usage::

    PYTHONIOENCODING=utf-8 python -m scripts.dump_calibration_distractors \
        --per-pair 200 --out calibration_sample.txt
"""

from __future__ import annotations

import argparse
import collections
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

LANG = {1: 'zh', 2: 'en', 3: 'ja'}

# (word language, definition language). These are the combinations a learner can
# actually be shown; ja/en first because an English speaker studying Japanese is
# the primary Calibration use case.
PAIRS = [(3, 2), (1, 2), (2, 2), (3, 3), (1, 1), (3, 1), (1, 3)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-pair', type=int, default=200)
    ap.add_argument('--count', type=int, default=3)
    ap.add_argument('--seed', type=int, default=20260908)
    ap.add_argument('--out', default='calibration_sample.txt')
    args = ap.parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    random.seed(args.seed)
    out_lines: list[str] = []
    summary: list[str] = []

    for wl, dl in PAIRS:
        pair = f'{LANG[wl]}/{LANG[dl]}'

        # Anchors: standard-level, embedded senses of this exact pair.
        rows = (db.table('dim_word_senses')
                .select('id, definition, vocab_id, dim_vocabulary!inner(lemma, frequency_rank)')
                .eq('word_language_id', wl)
                .eq('definition_language_id', dl)
                .eq('definition_level', 'standard')
                .not_.is_('embedding', 'null')
                .limit(4000)
                .execute().data or [])
        if not rows:
            summary.append(f'{pair}: NO ANCHORS')
            continue

        sample = random.sample(rows, min(args.per_pair, len(rows)))

        stats = collections.Counter()
        sims: list[float] = []
        tiers = collections.Counter()

        out_lines.append('')
        out_lines.append('=' * 78)
        out_lines.append(f'  {pair}   (word language {wl}, definition language {dl})')
        out_lines.append('=' * 78)

        for anchor in sample:
            vocab = anchor.get('dim_vocabulary') or {}
            lemma = (vocab.get('lemma') or '').strip()
            a_def = (anchor.get('definition') or '').strip()

            try:
                foils = db.rpc('semantic_distractors', {
                    'p_sense_id': anchor['id'],
                    'p_word_language_id': wl,
                    'p_definition_language_id': dl,
                    'p_count': args.count,
                }).execute().data or []
            except Exception as exc:
                stats['rpc_error'] += 1
                out_lines.append(f'\n[{anchor["id"]}] {lemma} -- RPC ERROR: {exc}')
                continue

            stats['items'] += 1
            if len(foils) < args.count:
                stats['short'] += 1
            if not foils:
                stats['empty'] += 1

            out_lines.append('')
            out_lines.append(f'[sense {anchor["id"]}]  {lemma}'
                             f'   (zipf {vocab.get("frequency_rank")})')
            out_lines.append(f'    KEY : {a_def}')

            seen_defs = set()
            for f in foils:
                d = (f.get('out_definition') or '').strip()
                fl = (f.get('out_lemma') or '').strip()
                sim = f.get('out_similarity')
                tier = f.get('out_freq_tier')
                if sim is not None:
                    sims.append(float(sim))
                tiers[tier] += 1

                if f.get('out_vocab_id') == anchor.get('vocab_id'):
                    stats['SIBLING_LEAK'] += 1
                if d == fl:
                    stats['def_is_own_lemma'] += 1
                if d == lemma:
                    stats['def_is_anchor_lemma'] += 1
                if d == a_def:
                    stats['def_is_anchor_def'] += 1
                if d.lower() in seen_defs:
                    stats['dup_option'] += 1
                seen_defs.add(d.lower())

                cos_txt = f'{float(sim):.3f}' if sim is not None else '?'
                out_lines.append(
                    f'    foil: {d}   <- {fl}  '
                    f'(cos {cos_txt}, zipf {f.get("out_frequency")}, tier {tier})')

        avg = sum(sims) / len(sims) if sims else 0.0
        summary.append(
            f'{pair:<6} items={stats["items"]:<4} short={stats["short"]:<4} '
            f'empty={stats["empty"]:<4} SIBLING_LEAK={stats["SIBLING_LEAK"]:<3} '
            f'def=own_lemma={stats["def_is_own_lemma"]:<3} '
            f'def=anchor_lemma={stats["def_is_anchor_lemma"]:<3} '
            f'def=anchor_def={stats["def_is_anchor_def"]:<3} '
            f'dup={stats["dup_option"]:<3} '
            f'mean_cos={avg:.3f} tiers={dict(sorted(tiers.items(), key=lambda x: (x[0] is None, x[0])))}')

    header = ['SUMMARY (per word/definition language pair)', '-' * 78] + summary + ['']
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(header + out_lines))

    print('\n'.join(header))
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
