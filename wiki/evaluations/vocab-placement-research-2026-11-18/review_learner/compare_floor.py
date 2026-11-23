"""Compare D3S and D3Sf (floor of 5 meaning items in bands 4-7) at the 60-item snapshot. Read-only on sim output.
Usage: python3 -I compare_floor.py <raw_floor.json>"""
import json, sys
from collections import defaultdict
d = json.load(open(sys.argv[1]))
N = {'zh': 3623, 'ja': 3175}
def grp(t): return 'beginner' if t >= 5.5 else ('intermediate' if t >= 4.0 else 'advanced')
nb = defaultdict(list); lvl = defaultdict(list); cnt = defaultdict(list)
for r in d['rows']:
    for des in ('D3S', 'D3Sf'):
        sn = r['res'][des]; s = next((x for x in sn if x['n'] >= 60), sn[-1])
        nb[(r['lang'], des, grp(r['tau']))].append(s['nb'])
        lvl[(r['lang'], des, r['pr'])].append(s['pr'] - r['pr'])
        cnt[(r['lang'], des)].append((abs(s['Tr'] - r['T_mr']) / N[r['lang']], s['rlo'] <= r['T_mr'] <= s['rhi'],
                                      abs(s['Tm'] - r['T_m']) / N[r['lang']], s['lo'] <= r['T_m'] <= s['hi'], s['rhw'] / N[r['lang']]))
print('Meaning items per band at the 60-item snapshot (band 1 rarest .. band 7 commonest), mean')
for k in sorted(nb):
    v = nb[k]; m = [sum(x[i] for x in v) / len(v) for i in range(7)]
    print(k, len(v), ' '.join(f'{x:.1f}' for x in m))
print('\nm+r placement by TRUE m+r level: learners | exact | within 1 | placed above | 2+ below')
for k in sorted(lvl):
    e = lvl[k]; n = len(e)
    print(k, n, f'{100*sum(x==0 for x in e)/n:.0f}% | {100*sum(abs(x)<=1 for x in e)/n:.0f}% | {100*sum(x>0 for x in e)/n:.0f}% | {100*sum(x<=-2 for x in e)/n:.0f}%')
print('\nCounts (90% intervals, % of pool): m+r MAE | m+r cover | m MAE | m cover | m+r mean half-width')
for k in sorted(cnt):
    v = cnt[k]; n = len(v)
    print(k, n, f'{100*sum(x[0] for x in v)/n:.1f} | {100*sum(x[1] for x in v)/n:.0f}% | {100*sum(x[2] for x in v)/n:.1f} | {100*sum(x[3] for x in v)/n:.0f}% | ±{100*sum(x[4] for x in v)/n:.1f}')
