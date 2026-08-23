"""TASK-735 smoke: did the ja L1 rewrites actually move the numbers?

Two experiments, each isolating one row, both run against the exact inputs that
produced zero L1 exercises in canary run ``ja-20260822-232552``.

A. JUDGE A/B (``--judge``) — cheap, ~6 calls, no generation.
   Replays the four recorded distractor sets from word_assets through the
   incumbent judge v2 and the new v3, same model, temperature 0. Isolates the
   judge: identical inputs, only the prompt differs. The number that matters is
   むかえ, a textbook one-mora minimal pair that v2 killed with
   ``最小対立の条件を満たさず``.

B. GENERATOR (``--gen``) — ~2 calls, real money (~$0.02/sense).
   Re-runs ExerciseAssetGenerator for L1 only against the stored prompt1_core
   asset, then feeds the result to the live judge. Isolates the generator: does
   v2 still invent 向こうし / 無蚊地?

The pass condition for the pair is not "the judge keeps more". It is
``len(kept) >= 3`` per variant, because ``exercise_renderer._render_phonetic``
drops the entire variant below that — which is why 17 rejects out of 18 became
0 exercises rather than 0 distractors.

Usage::

    python scripts/smoke_task735_ja_l1.py --judge          # free-ish, no generation
    python scripts/smoke_task735_ja_l1.py --gen            # regenerates L1
    python scripts/smoke_task735_ja_l1.py --judge --gen
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

JA = 3

# The senses the 2026-08-22 canary actually built. 34999 (一/いち) is deliberately
# absent: it never reached P2 — the P1 sentence judge blocked it, correctly, and
# that is a sense-pool problem rather than an L1 one.
SENSES = (34997, 35001)

# What _render_phonetic requires before it will emit a variant at all.
MIN_KEPT = 3


def fetch_template(db, task: str, version: int) -> dict:
    rows = (db.table('prompt_templates')
              .select('template_text, model, provider, version')
              .eq('task_name', task).eq('language_id', JA)
              .eq('version', version).execute().data)
    if not rows:
        raise SystemExit(f'no {task} v{version} row for ja')
    return rows[0]


def run_judge(template: str, model: str, provider: str,
              target: str, distractors: list[str]) -> dict:
    """One judge call, returning {distractor: (verdict, reason)}."""
    from services.llm_service import call_llm

    numbered = '\n'.join(f'{i + 1}. {d}' for i, d in enumerate(distractors))
    result = call_llm(
        template.format(target=target, distractors_numbered=numbered),
        model=model, temperature=0.0, response_format='json', provider=provider,
        pipeline='vocab_ladder', task_name='smoke_task735_l1_judge',
    )
    out = {}
    for i, d in enumerate(distractors):
        entry = (result or {}).get(str(i + 1)) or {}
        verdict = str(entry.get('verdict', 'keep')).strip().lower()
        out[d] = ('reject' if verdict == 'reject' else 'keep',
                  str(entry.get('reason', ''))[:40])
    return out


def stored_l1_sets(db) -> list[tuple[int, str, str, list[str]]]:
    """(sense_id, variant, target, distractors) for every stored ja L1 asset."""
    rows = (db.table('word_assets')
              .select('sense_id, asset_type, content')
              .in_('sense_id', list(SENSES))
              .like('asset_type', 'prompt2_exercises%')
              .execute().data or [])
    sets = []
    for r in sorted(rows, key=lambda x: (x['sense_id'], x['asset_type'])):
        lvl = (r['content'] or {}).get('level_1') or {}
        options = lvl.get('options') or []
        target = next((o.get('text') for o in options if o.get('is_correct')), '')
        distractors = [o.get('text') for o in options
                       if not o.get('is_correct') and o.get('text')]
        if target and distractors:
            sets.append((r['sense_id'], r['asset_type'][-1], target, distractors))
    return sets


def experiment_judge(db) -> int:
    v2 = fetch_template(db, 'ladder_l1_distractor_judge', 2)
    v3 = fetch_template(db, 'ladder_l1_distractor_judge', 3)
    print(f'\nA. JUDGE A/B  v2 vs v3, model {v3["model"]}, temp 0\n' + '=' * 72)

    totals = {'v2': 0, 'v3': 0}
    variants_ok = {'v2': 0, 'v3': 0}
    sets = stored_l1_sets(db)

    for sense_id, variant, target, distractors in sets:
        print(f'\nsense {sense_id} variant {variant} — target {target!r}')
        verdicts = {}
        for label, tpl in (('v2', v2), ('v3', v3)):
            verdicts[label] = run_judge(tpl['template_text'], tpl['model'],
                                        tpl['provider'], target, distractors)
            kept = sum(1 for v, _ in verdicts[label].values() if v == 'keep')
            totals[label] += kept
            variants_ok[label] += 1 if kept >= MIN_KEPT else 0

        for d in distractors:
            a, ra = verdicts['v2'][d]
            b, rb = verdicts['v3'][d]
            flip = ' <-- FLIPPED' if a != b else ''
            print(f'   {d:<8} v2={a:<6} ({ra:<22}) v3={b:<6} ({rb}){flip}')

    n = len(sets)
    print('\n' + '-' * 72)
    print(f'  distractors kept : v2 {totals["v2"]}/{n * 3}   v3 {totals["v3"]}/{n * 3}')
    print(f'  variants that would RENDER (>= {MIN_KEPT} kept): '
          f'v2 {variants_ok["v2"]}/{n}   v3 {variants_ok["v3"]}/{n}')
    return variants_ok['v3']


def experiment_gen(db) -> int:
    """Regenerate L1 only with the new generator prompt, then judge it live."""
    from services.vocabulary_ladder.asset_generators.prompt2_exercises import (
        ExerciseAssetGenerator,
    )
    from services.exercise_generation.judges.l1_distractor import filter_l1_distractors

    print('\nB. GENERATOR  vocab_prompt2_exercises ja v2, L1 only\n' + '=' * 72)
    renderable = 0

    for sense_id in SENSES:
        rows = (db.table('word_assets')
                  .select('content')
                  .eq('sense_id', sense_id).eq('asset_type', 'prompt1_core')
                  .execute().data or [])
        if not rows:
            print(f'  sense {sense_id}: no prompt1_core asset — skipped')
            continue

        gen = ExerciseAssetGenerator(db, JA)
        out = gen.generate(sense_id, rows[0]['content'], active_levels=[1])
        level_1 = (out or {}).get('level_1') or {}
        options = level_1.get('options') or []
        if len(options) < 4:
            print(f'  sense {sense_id}: generator returned {len(options)} options — FAIL')
            continue

        target = next((o.get('text') for o in options if o.get('is_correct')), '')
        distractors = [o.get('text') for o in options
                       if not o.get('is_correct') and o.get('text')]
        kept, meta = filter_l1_distractors(db, target, distractors, JA)

        ok = len(kept) >= MIN_KEPT
        renderable += 1 if ok else 0
        print(f'\n  sense {sense_id}  target {target!r}')
        print(f'    generated : {distractors}')
        print(f'    kept      : {kept}')
        print(f'    rejected  : {meta["rejected_items"]}')
        print(f'    renders   : {"YES" if ok else "NO"} ({len(kept)}/{len(distractors)} kept)')

    print('\n' + '-' * 72)
    print(f'  variants that would RENDER: {renderable}/{len(SENSES)}')
    return renderable


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--judge', action='store_true', help='run experiment A')
    parser.add_argument('--gen', action='store_true', help='run experiment B')
    args = parser.parse_args()
    if not (args.judge or args.gen):
        parser.error('pick at least one of --judge / --gen')

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    if args.judge:
        experiment_judge(db)
    if args.gen:
        experiment_gen(db)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
