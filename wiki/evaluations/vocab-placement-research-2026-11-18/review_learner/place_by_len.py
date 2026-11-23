"""D3S m+r placement by true level at 40, 60 and 90 items (read-only on sim output). Usage: python3 -I place_by_len.py <raw.json>"""
import json, sys
from collections import defaultdict
d = json.load(open(sys.argv[1]))
acc = defaultdict(list)
for r in d['rows']:
    sn = r['res']['D3S']
    for n in (40, 60, 90):
        s = next((x for x in sn if x['n'] >= n), sn[-1])
        acc[(r['lang'], r['pr'], n)].append(s['pr'] - r['pr'])
print('lang true_level items | learners | within 1 | 2+ below | placed above')
for k in sorted(acc):
    if k[1] in (0, 1):
        continue
    e = acc[k]; m = len(e)
    print(k, m, f'{100*sum(abs(x)<=1 for x in e)/m:.0f}% | {100*sum(x<=-2 for x in e)/m:.0f}% | {100*sum(x>0 for x in e)/m:.0f}%')
