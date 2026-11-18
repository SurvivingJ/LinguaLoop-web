"""Learner-side view of the simulated D3S runs (review stage, read-only on the sim outputs).

Usage: python3 -I learner_view.py <raw_main.json>

For each simulated learner and the D3S design it reports, by ability group (tau, as the sim defines it):
  - share of meaning items answered right at the 60-item snapshot (zh only: 98% of zh words have a reading item,
    so n_r / n_m = share of meaning items answered right, guesses included);
  - the stop point under the draft's rule (earliest 40 items, stop when both 90% half-widths <= 12% of the pool,
    checked at the sim's checkpoints 40, 45, 50, 60; else 60);
  - exact and within-one-level placement for "knows the word" at the 60-item snapshot;
  - minutes: the sim's latency model (tm) and a wall-clock model (6.57 s per meaning item, 7.50 s per reading item,
    de6fd05b mean gap between consecutive answers, gaps <= 60 s; SQL in review-learner.md).
"""
import json
import sys
from collections import defaultdict

H = 0.12
WALL_M, WALL_R = 6.57, 7.50


def group(tau):
    if tau >= 5.5:
        return 'beginner'
    if tau >= 4.0:
        return 'intermediate'
    return 'advanced'


def main(path):
    d = json.load(open(path))
    acc = defaultdict(lambda: defaultdict(list))
    for r in d['rows']:
        snaps = r['res'].get('D3S')
        if not snaps:
            continue
        g = group(r['tau'])
        key = (r['lang'], r['prof'], g)
        keyall = (r['lang'], '*', g)
        s60 = next((s for s in snaps if s['n'] >= 60), snaps[-1])
        stop = 60
        stop_snap = s60
        for s in snaps:
            if 40 <= s['n'] < 60 and s['hw'] <= H * r['N'] and s.get('rhw', 0) <= H * r['N']:
                stop, stop_snap = s['n'], s
                break
        for k in (key, keyall):
            a = acc[k]
            a['stop'].append(stop)
            a['early'].append(stop < 60)
            a['min_sim'].append(stop_snap['tm'] / 60.0)
            a['min_wall'].append((WALL_M * stop_snap['n_m'] + WALL_R * stop_snap['n_r']) / 60.0)
            a['n_m'].append(s60['n_m'])
            a['n_r'].append(s60['n_r'])
            if r['lang'] == 'zh':
                a['right_share'].append(s60['n_r'] / s60['n_m'])
                a['not_right'].append(s60['n_m'] - s60['n_r'])
            a['exact'].append(s60['pr'] == r['pr'])
            a['pm1'].append(abs(s60['pr'] - r['pr']) <= 1)
            a['over'].append(s60['pr'] > r['pr'])
            a['true_level'].append(r['pr'])
    mean = lambda x: sum(x) / len(x) if x else float('nan')
    print('lang prof group | n | meaning items (60-item snap) | reading items | zh: share meaning right | '
          'zh: meaning items not right | stop items mean | stopped early | min (sim latency) | min (wall clock) | '
          'level exact | level +-1 | placed above | true m+r level mean')
    for k in sorted(acc):
        a = acc[k]
        rs = mean(a['right_share']) if a['right_share'] else None
        nr = mean(a['not_right']) if a['not_right'] else None
        print(f"{k[0]} {k[1]} {k[2]:12s} | {len(a['stop'])} | {mean(a['n_m']):.1f} | {mean(a['n_r']):.1f} | "
              f"{'%.0f%%' % (100 * rs) if rs is not None else '-'} | {'%.1f' % nr if nr is not None else '-'} | "
              f"{mean(a['stop']):.1f} | {100 * mean(a['early']):.0f}% | {mean(a['min_sim']):.1f} | "
              f"{mean(a['min_wall']):.1f} | {100 * mean(a['exact']):.0f}% | {100 * mean(a['pm1']):.0f}% | "
              f"{100 * mean(a['over']):.0f}% | {mean(a['true_level']):.2f}")


if __name__ == '__main__':
    main(sys.argv[1])
