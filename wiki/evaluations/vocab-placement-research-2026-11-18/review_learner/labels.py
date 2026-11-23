"""ADR-051 rule-4 label of the D3S result at the stop point (draft rule: earliest 40, both 90% half-widths <= 12%,
cap 60), for the meaning+reading headline (zh/ja), by the learner's TRUE m+r exam level. 95% from the 90% half-width.
Read-only on sim output. Usage: python3 -I labels.py <raw.json>"""
import json, sys
from collections import defaultdict, Counter
d = json.load(open(sys.argv[1]))
Z95, Z90 = 1.959964, 1.6448536
def label(T, hw90, N):
    sd = hw90 / Z90
    lo, hi = max(0.0, T - Z95 * sd), min(N, max(T, 0) + Z95 * sd)
    rel = Z95 * sd / max(T, 0.10 * N)
    if lo <= 0:
        return 'Fewer than', hi
    if rel <= 0.50:
        return 'Rough range', hi - lo
    if hi <= N / 2:
        return 'Fewer than', hi
    return 'too uncertain', None
acc = defaultdict(Counter); wid = defaultdict(list)
for r in d['rows']:
    N = r['N']; sn = r['res']['D3S']
    st = next((s for s in sn if 40 <= s['n'] < 60 and s['hw'] <= 0.12 * N and s.get('rhw', 0) <= 0.12 * N), None) \
         or next((s for s in sn if s['n'] >= 60), sn[-1])
    lab, x = label(st['Tr'], st['rhw'], N)
    acc[(r['lang'], r['pr'])][lab] += 1
    if lab == 'Rough range':
        wid[(r['lang'], r['pr'])].append(x)
print('lang true m+r level | learners | "Fewer than" | Rough range | too uncertain | mean width of Rough range (words) | true m+r count mean')
tm = defaultdict(list)
for r in d['rows']:
    tm[(r['lang'], r['pr'])].append(r['T_mr'])
for k in sorted(acc):
    c = acc[k]; n = sum(c.values())
    w = wid.get(k, [])
    print(k, n, f"{100*c['Fewer than']/n:.0f}% | {100*c['Rough range']/n:.0f}% | {100*c['too uncertain']/n:.0f}% | {sum(w)/len(w) if w else float('nan'):.0f} | {sum(tm[k])/len(tm[k]):.0f}")
