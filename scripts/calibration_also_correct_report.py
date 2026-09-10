#!/usr/bin/env python3
"""Find distractors that are secretly a second correct answer (TASK-763).

Why this cannot be done any other way
-------------------------------------
ADR-025 records the limit plainly: cosine similarity cannot separate "unrelated"
from "duplicate". The unrelated distribution's top (p99 0.43-0.56) overlaps the
same-word distribution's bottom (p5 0.33-0.57), so no threshold exists. The exact
exclusions (vocab_id siblings, stem variants) catch the mechanical duplicates, but
a genuine synonym from an unrelated stem -- 因子 against 要因, 適正 against 妥当 at
cosine 0.736 -- is indistinguishable from an excellent distractor by geometry alone.

The only thing that separates them is how people answer. A distractor that strong
learners pick as often as the key IS a second right answer. That signal lives in
calibration_response_options, which is why every option shown is recorded and not
just the chosen one.

What this reports
-----------------
For each distractor that has been shown enough times:

  pick_rate          how often it was chosen over the key
  strong_pick_rate   the same, restricted to learners who did well on the rest of
                     their session -- the discriminating statistic, because a weak
                     learner picking it is evidence of nothing
  cosine             its similarity to the key, to show whether the cosine band
                     could ever have caught it

A high strong_pick_rate is the flag. Chance is 1-in-3 among the three distractors,
so a distractor taking well over a third of the wrong answers from strong learners
is either a second correct answer or a genuinely superb foil -- and the two are
told apart by reading the pair, which is why examples are printed rather than
counted.

Usage::

    PYTHONIOENCODING=utf-8 python -m scripts.calibration_also_correct_report
    PYTHONIOENCODING=utf-8 python -m scripts.calibration_also_correct_report --min-shown 10
"""

from __future__ import annotations

import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

#: A session is "strong" when the learner answered at least this share of their
#: other items correctly. Not a fixed accuracy across everyone: the point is to
#: weight the opinion of people who clearly knew the rest of the material.
STRONG_SESSION_ACCURACY = 0.75


def _page(db, table: str, select: str, **filters):
    """Fetch every row, paging past PostgREST's 1000-row response cap."""
    rows, offset = [], 0
    while True:
        query = db.table(table).select(select)
        for column, value in filters.items():
            query = query.eq(column, value)
        page = query.order('response_id' if table.endswith('options') else 'id') \
                    .range(offset, offset + 999).execute().data or []
        rows += page
        if len(page) < 1000:
            break
        offset += 1000
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-shown', type=int, default=5,
                    help='ignore distractors shown fewer times than this')
    ap.add_argument('--top', type=int, default=40)
    args = ap.parse_args()

    from services.supabase_factory import SupabaseFactory, get_supabase_admin
    SupabaseFactory.initialize()
    db = get_supabase_admin()

    responses = _page(db, 'calibration_responses',
                      'id, session_id, anchor_sense_id, is_correct')
    if not responses:
        print('No calibration responses recorded yet.')
        print('This report needs real learner answers; it cannot be run on '
              'simulated ones, because the whole signal is which wrong option a '
              'person found tempting. Re-run once Calibration has live traffic.')
        return

    # Session strength, computed excluding nothing: a learner's overall accuracy
    # is the best available proxy for whether their choice carries information.
    per_session = collections.defaultdict(lambda: [0, 0])
    for r in responses:
        if r['is_correct'] is None:
            continue
        per_session[r['session_id']][1] += 1
        if r['is_correct']:
            per_session[r['session_id']][0] += 1
    strong = {sid for sid, (ok, n) in per_session.items()
              if n >= 10 and ok / n >= STRONG_SESSION_ACCURACY}

    by_response = {r['id']: r for r in responses}
    options = _page(db, 'calibration_response_options',
                    'response_id, sense_id, is_key, was_chosen, similarity')

    shown = collections.Counter()
    chosen = collections.Counter()
    shown_strong = collections.Counter()
    chosen_strong = collections.Counter()
    cosine = {}
    anchors = collections.defaultdict(collections.Counter)

    for o in options:
        if o['is_key']:
            continue
        response = by_response.get(o['response_id'])
        if response is None or response['is_correct'] is None:
            continue
        sense_id = o['sense_id']
        shown[sense_id] += 1
        anchors[sense_id][response['anchor_sense_id']] += 1
        if o['similarity'] is not None:
            cosine[sense_id] = o['similarity']
        if o['was_chosen']:
            chosen[sense_id] += 1
        if response['session_id'] in strong:
            shown_strong[sense_id] += 1
            if o['was_chosen']:
                chosen_strong[sense_id] += 1

    rows = []
    for sense_id, n in shown.items():
        if n < args.min_shown:
            continue
        ns = shown_strong[sense_id]
        rows.append((
            (chosen_strong[sense_id] / ns) if ns else 0.0,
            chosen[sense_id] / n, n, ns, sense_id, cosine.get(sense_id),
        ))
    rows.sort(reverse=True)

    print(f'{len(responses)} responses, {len(per_session)} sessions '
          f'({len(strong)} strong at >={STRONG_SESSION_ACCURACY:.0%}).')
    print(f'{len(rows)} distractors shown at least {args.min_shown} times.\n')
    if not rows:
        print('Not enough traffic yet to rank anything.')
        return

    print(f"{'strong%':>8} {'all%':>7} {'shown':>6} {'str':>4} {'cos':>6}  distractor -> anchor")
    for strong_rate, all_rate, n, ns, sense_id, cos in rows[:args.top]:
        top_anchor = anchors[sense_id].most_common(1)[0][0]
        info = db.table('dim_word_senses').select(
            'definition, dim_vocabulary!inner(lemma)').eq('id', sense_id).limit(1).execute().data
        anchor_info = db.table('dim_word_senses').select(
            'dim_vocabulary!inner(lemma)').eq('id', top_anchor).limit(1).execute().data
        lemma = info[0]['dim_vocabulary']['lemma'] if info else '?'
        anchor_lemma = anchor_info[0]['dim_vocabulary']['lemma'] if anchor_info else '?'
        cos_txt = f'{cos:.3f}' if cos is not None else '   -  '
        print(f'{strong_rate:>7.0%} {all_rate:>6.0%} {n:>6} {ns:>4} {cos_txt:>6}  '
              f'{lemma} -> {anchor_lemma}')

    print('\nRead the top rows as PAIRS. If the distractor genuinely means what the '
          'anchor means, it is a second correct answer: add it to an exclusion, or '
          'lower that language pair\'s cos_max in dim_distractor_bands. If it is '
          'merely a very good foil, leave it alone -- that is the mode working.')


if __name__ == '__main__':
    main()
