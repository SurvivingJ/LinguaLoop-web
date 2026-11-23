"""Floor exit for D3S: from 20 items, stop when the meaning count's 90% upper bound <= F x pool ("Fewer than ..."),
else the draft rule (earliest 40, both half-widths <= 12%, cap 60). One-sided check: true counts <= the shown bound.
Read-only on sim output. Usage: python3 -I floor_exit.py <raw.json>"""
import json, sys
from collections import defaultdict
d = json.load(open(sys.argv[1]))
def grp(t): return 'beginner' if t >= 5.5 else ('intermediate' if t >= 4.0 else 'advanced')
F = 0.15
acc = defaultdict(list)
for r in d['rows']:
    sn = r['res']['D3S']; N = r['N']
    fl = next((s for s in sn if 20 <= s['n'] < 60 and s['hi'] <= F * N), None)
    if fl is not None:
        rec = (fl['n'], True, r['T_m'] <= fl['hi'], r['T_mr'] <= fl['hi'], fl['tm'] / 60)
    else:
        st = next((s for s in sn if 40 <= s['n'] < 60 and s['hw'] <= 0.12 * N and s.get('rhw', 0) <= 0.12 * N), None) \
             or next((s for s in sn if s['n'] >= 60), sn[-1])
        rec = (st['n'], False, st['lo'] <= r['T_m'] <= st['hi'], st['rlo'] <= r['T_mr'] <= st['rhi'], st['tm'] / 60)
    acc[(r['lang'], r['prof'], grp(r['tau']))].append(rec)
print(f'floor exit at upper bound <= {F:.0%} of pool | learners | mean items | took floor exit | true meaning <= shown bound or in interval | m+r same | minutes (sim latency)')
for k in sorted(acc):
    v = acc[k]; n = len(v)
    fe = [x for x in v if x[1]]
    print(k, n, f"{sum(x[0] for x in v)/n:.1f} | {100*len(fe)/n:.0f}% (n {len(fe)}, one-sided ok m {100*sum(x[2] for x in fe)/max(1,len(fe)):.0f}%) | {100*sum(x[2] for x in v)/n:.0f}% | {100*sum(x[3] for x in v)/n:.0f}% | {sum(x[4] for x in v)/n:.1f}")
