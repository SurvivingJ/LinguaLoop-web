"""Placement of "knows the word" (D3S, 60-item snapshot) by the learner's TRUE m+r level. Read-only on sim output.
Usage: python3 -I level_by_true.py <raw_main.json>"""
import json, sys
from collections import defaultdict
d = json.load(open(sys.argv[1]))
acc = defaultdict(list)
for r in d['rows']:
    snaps = r['res'].get('D3S')
    if not snaps:
        continue
    s = next((x for x in snaps if x['n'] >= 60), snaps[-1])
    acc[(r['lang'], r['pr'])].append((s['pr'] - r['pr'], s['pm'] - r['pr'], r['pm'] - r['pr']))
print('lang true_m+r_level | learners | exact | within 1 | placed above | placed 2+ above | placed 2+ below | meaning-placement minus true m+r (mean) | true meaning lvl minus m+r lvl (mean)')
for k in sorted(acc):
    v = acc[k]; n = len(v)
    e = [x[0] for x in v]
    print(f"{k[0]} L{k[1]} | {n} | {100*sum(x==0 for x in e)/n:.0f}% | {100*sum(abs(x)<=1 for x in e)/n:.0f}% | {100*sum(x>0 for x in e)/n:.0f}% | {100*sum(x>=2 for x in e)/n:.0f}% | {100*sum(x<=-2 for x in e)/n:.0f}% | {sum(x[1] for x in v)/n:+.2f} | {sum(x[2] for x in v)/n:+.2f}")
