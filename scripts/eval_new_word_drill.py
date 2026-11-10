"""Measure the new-word drill against the words admitted before it (TASK-921).

Read-only. Writes a markdown report (wiki/evaluations/new-word-drill-<tag>.md).

Cohorts (per learner, all languages):
  drill   ladder rows that went through the drill (word_state 'intro' now, or a
          non-empty intro_history)
  before  ladder rows admitted before the drill and never in it

Metrics:
  * cohort sizes; drill words by current session; graduated to ring 2
  * drill: per-session first-run pass rate and cold-recall accuracy
    (intro_history), questions and minutes per word (exercise_attempts
    source 'intro')
  * both: "next-day recall" = first-try accuracy on the first practice
    attempt made on a LATER day than the word's first attempt (a cold
    retention probe that exists for both cohorts)
  * both: current word-knowledge (p_known) for words admitted >= 7 days ago
  * ladder movement since the ladder fix: words above ring 1, gates passed,
    mastered (the "before" cohort could not move rings before 2026-11-10)

With two learners this is a sanity check, not a significance test.

Usage:
    python scripts/eval_new_word_drill.py [--exclude-user UUID ...] [--tag baseline-2026-11-10]
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.supabase_factory import SupabaseFactory  # noqa: E402

PAGE = 1000


def fetch_all(q_factory):
    out, start = [], 0
    while True:
        rows = q_factory().range(start, start + PAGE - 1).execute().data or []
        out += rows
        if len(rows) < PAGE:
            return out
        start += PAGE


def pct(n, d):
    return f"{100.0 * n / d:.0f}% ({n}/{d})" if d else "—"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--exclude-user', action='append', default=[])
    ap.add_argument('--tag', default=datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    SupabaseFactory.initialize()
    db = SupabaseFactory.get_service_client()
    if db is None:
        print('no Supabase service client (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)')
        return 1

    ladder = [r for r in fetch_all(lambda: db.table('user_word_ladder').select(
        'user_id, sense_id, word_state, current_ring, gates_passed, intro_stage, intro_history, created_at'))
        if r['user_id'] not in args.exclude_user]
    drill = [r for r in ladder if r['word_state'] == 'intro' or r.get('intro_history')]
    before = [r for r in ladder if not (r['word_state'] == 'intro' or r.get('intro_history'))]
    users = sorted({r['user_id'] for r in ladder})

    attempts = defaultdict(list)          # (user, sense) -> [attempt]
    for u in users:
        for a in fetch_all(lambda: db.table('exercise_attempts').select(
                'sense_id, is_correct, is_first_attempt, created_at, source, time_taken_ms, exercise_type')
                .eq('user_id', u).not_.is_('sense_id', 'null').order('created_at')):
            attempts[(u, a['sense_id'])].append(a)
    know = {}
    for u in users:
        for k in fetch_all(lambda: db.table('user_vocabulary_knowledge').select('sense_id, p_known').eq('user_id', u)):
            know[(u, k['sense_id'])] = float(k['p_known'])

    now = datetime.now(timezone.utc)
    L = [f"# New-word drill evaluation — {args.tag}", "",
         f"Generated {now:%Y-%m-%d %H:%M} UTC by `scripts/eval_new_word_drill.py` (read-only). "
         f"Learners: {len(users)}; excluded: {len(args.exclude_user)}. Small numbers: a sanity check, not a test.", ""]

    L += ["## Cohorts", "", "| | Drill | Before |", "|---|---|---|",
          f"| Ladder words | {len(drill)} | {len(before)} |"]
    by_stage = defaultdict(int)
    for r in drill:
        if r['word_state'] == 'intro':
            by_stage[r['intro_stage']] += 1
    grads = [r for r in drill if r['word_state'] != 'intro']
    L += [f"| In drill by session (1/2/3/4) | {by_stage[1]}/{by_stage[2]}/{by_stage[3]}/{by_stage[4]} | — |",
          f"| Graduated from the drill | {len(grads)} | — |", ""]

    # drill sessions
    runs = defaultdict(lambda: [0, 0])    # stage -> [passed, total]
    cold = defaultdict(lambda: [0, 0])
    first_run_seen = set()
    for r in drill:
        for e in r.get('intro_history') or []:
            st = e.get('stage')
            if not st or e.get('source') == 'prestudy':
                continue
            key = (r['user_id'], r['sense_id'], st)
            if key not in first_run_seen:
                first_run_seen.add(key)
                runs[st][1] += 1
                runs[st][0] += 1 if e.get('passed') else 0
            if e.get('cold_correct') is not None:
                cold[st][1] += 1
                cold[st][0] += 1 if e['cold_correct'] else 0
    L += ["## Drill sessions", "", "| Session | Passed on the first run | Cold recall right |", "|---|---|---|"]
    for st in (1, 2, 3, 4):
        L.append(f"| {st} | {pct(*runs[st])} | {pct(*cold[st]) if st > 1 else '—'} |")
    items = [len([a for a in attempts[(r['user_id'], r['sense_id'])] if a.get('source') == 'intro']) for r in grads]
    secs = [sum((a.get('time_taken_ms') or 0) for a in attempts[(r['user_id'], r['sense_id'])]
                if a.get('source') == 'intro') / 1000 for r in grads]
    L += ["", f"Graduated words: {len(grads)}; questions per word "
              f"{statistics.mean(items):.1f}; minutes per word {statistics.mean(secs) / 60:.1f}." if grads
          else "No graduated words yet.", ""]

    # next-day recall, both cohorts (non-intro practice attempts on a later day)
    def next_day(rows):
        hit = tot = 0
        for r in rows:
            seq = [a for a in attempts[(r['user_id'], r['sense_id'])] if a.get('source') != 'prestudy']
            if not seq:
                continue
            day0 = seq[0]['created_at'][:10]
            later = [a for a in seq if a['created_at'][:10] > day0]
            if later:
                tot += 1
                hit += 1 if later[0]['is_correct'] else 0
        return hit, tot

    def knowledge(rows):
        cut = (now - timedelta(days=7)).isoformat()
        ps = [know[(r['user_id'], r['sense_id'])] for r in rows
              if r['created_at'] <= cut and (r['user_id'], r['sense_id']) in know]
        if not ps:
            return '—'
        return f"mean {statistics.mean(ps):.2f}; ≥0.75 {pct(sum(p >= 0.75 for p in ps), len(ps))}"

    def ladder_moves(rows):
        up = sum(1 for r in rows if (r.get('current_ring') or 1) > 1 and r['word_state'] != 'intro')
        gates = sum(1 for r in rows if (r.get('gates_passed') or {}).get('gate_a'))
        mastered = sum(1 for r in rows if r['word_state'] == 'mastered')
        return f"above ring 1: {up}; Gate A passed: {gates}; mastered: {mastered}"

    L += ["## Retention and progress (both cohorts)", "", "| | Drill | Before |", "|---|---|---|",
          f"| Next-day recall (first answer on a later day) | {pct(*next_day(drill))} | {pct(*next_day(before))} |",
          f"| Word knowledge, words admitted ≥ 7 days ago | {knowledge(drill)} | {knowledge(before)} |",
          f"| Ladder | {ladder_moves(drill)} | {ladder_moves(before)} |", "",
          "Note: before 2026-11-10 Practice answers never moved the ladder (the ladder fix), so the "
          "'Before' cohort's ladder row shows the state the fix starts from, not what it would have reached.", ""]

    out = args.out or os.path.join('wiki', 'evaluations', f'new-word-drill-{args.tag}.md')
    front = ("---\ntitle: New-word drill evaluation — " + args.tag + "\ntype: evaluation\nstatus: complete\n"
             f"last_updated: {now:%Y-%m-%d}\n---\n\n")
    with open(out, 'w') as f:
        f.write(front + '\n'.join(L) + '\n')
    print(out)
    print('\n'.join(L))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
