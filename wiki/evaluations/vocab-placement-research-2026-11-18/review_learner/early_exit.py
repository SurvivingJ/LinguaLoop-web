"""D3S stop rule (both 90% half-widths <= 12% of the pool, cap 60) with the earliest stop at 40 vs 20 items,
checked at the sim's checkpoints. Coverage of the 90% interval at the stop point. Read-only on sim output.
Usage: python3 -I early_exit.py <raw.json>"""
import json, sys
from collections import defaultdict
d = json.load(open(sys.argv[1]))
def grp(t): return 'beginner' if t >= 5.5 else ('intermediate' if t >= 4.0 else 'advanced')
acc = defaultdict(list)
for r in d['rows']:
    sn = r['res']['D3S']; N = r['N']
    for mn in (40, 20):
        st = next((s for s in sn if mn <= s['n'] < 60 and s['hw'] <= 0.12 * N and s.get('rhw', 0) <= 0.12 * N), None)
        if st is None:
            st = next((s for s in sn if s['n'] >= 60), sn[-1])
        cov_m = st['lo'] <= r['T_m'] <= st['hi']; cov_r = st['rlo'] <= r['T_mr'] <= st['rhi']
        acc[(r['lang'], r['prof'], grp(r['tau']), mn)].append((st['n'], st['n'] < 60, cov_m, cov_r, st['tm'] / 60))
print('lang prof group earliest | learners | mean items | stopped early | m cover | m+r cover | minutes (sim latency)')
for k in sorted(acc):
    v = acc[k]; n = len(v)
    print(k, n, f"{sum(x[0] for x in v)/n:.1f} | {100*sum(x[1] for x in v)/n:.0f}% | {100*sum(x[2] for x in v)/n:.0f}% | {100*sum(x[3] for x in v)/n:.0f}% | {sum(x[4] for x in v)/n:.1f}")
