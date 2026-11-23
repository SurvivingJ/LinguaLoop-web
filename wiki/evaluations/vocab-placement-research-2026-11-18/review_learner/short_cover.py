"""D3S 90% interval coverage and half-width at short lengths (a learner who ends early). Read-only on sim output.
Usage: python3 -I short_cover.py <raw.json>"""
import json, sys
from collections import defaultdict
d = json.load(open(sys.argv[1]))
acc = defaultdict(list)
for r in d['rows']:
    for s in r['res']['D3S']:
        if s['n'] in (20, 25, 30, 35, 40):
            acc[(r['lang'], s['n'])].append((s['lo'] <= r['T_m'] <= s['hi'], s['rlo'] <= r['T_mr'] <= s['rhi'], s['hw'] / r['N'], s['rhw'] / r['N']))
print('lang items | learners | meaning 90% cover | m+r 90% cover | meaning half-width | m+r half-width (share of pool)')
for k in sorted(acc):
    v = acc[k]; n = len(v)
    print(k, n, f"{100*sum(x[0] for x in v)/n:.0f}% | {100*sum(x[1] for x in v)/n:.0f}% | ±{100*sum(x[2] for x in v)/n:.1f}% | ±{100*sum(x[3] for x in v)/n:.1f}%")
