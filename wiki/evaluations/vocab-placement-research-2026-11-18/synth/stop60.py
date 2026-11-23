"""Owner chose about 60 items (PQ10, 2026-11-18). Precision exit (both 90% half-widths <= 12% of the pool, checked at the
40, 45 and 50 snapshots) with a cap of 60 scored items, D3S, research-stage main run, measured pace (6.57 s meaning,
7.50 s reading). Early-stop share, items, minutes (mean, p95), 95% half-widths at the stop, 90% coverage. Read-only."""
import json,sys
from collections import defaultdict
H=0.12; WM,WR=6.57,7.50; Z=1.96/1.645
d=json.load(open(sys.argv[1]))
acc=defaultdict(lambda: defaultdict(list))
def grp(t): return 'beginner' if t>=5.5 else ('intermediate' if t>=4.0 else 'advanced')
for r in d['rows']:
    s=r['res'].get('D3S')
    if not s: continue
    N=r['N']; cap=next(x for x in s if x['n']>=60); stop=cap
    for x in s:
        if 40<=x['n']<60 and x['hw']<=H*N and x['rhw']<=H*N: stop=x; break
    for k in ((r['lang'],r['prof'],grp(r['tau'])),(r['lang'],r['prof'],'all'),(r['lang'],'*','all')):
        a=acc[k]; a['early'].append(stop['n']<60); a['n'].append(stop['n']); a['nr'].append(stop['n_r'])
        a['min'].append((WM*stop['n_m']+WR*stop['n_r'])/60)
        a['hwm'].append(100*Z*stop['hw']/N); a['hwr'].append(100*Z*stop['rhw']/N)
        a['wm'].append(Z*stop['hw']); a['wr'].append(Z*stop['rhw'])
        a['cm'].append(stop['lo']<=r['T_m']<=stop['hi']); a['cr'].append(stop['rlo']<=r['T_mr']<=stop['rhi'])
m=lambda v: sum(v)/len(v)
p95=lambda v: sorted(v)[int(0.95*(len(v)-1))]
print('lang L1 group | n | early stop | scored items | reading items | minutes mean (p95) | 95% hw meaning / m+r (% pool; words) | 90% cover m / m+r')
for k in sorted(acc):
    a=acc[k]
    print(f"{k} | {len(a['n'])} | {100*m(a['early']):.0f}% | {m(a['n']):.1f} | {m(a['nr']):.1f} | {m(a['min']):.1f} ({p95(a['min']):.1f}) | ±{m(a['hwm']):.1f} / ±{m(a['hwr']):.1f} (±{m(a['wm']):.0f} / ±{m(a['wr']):.0f}) | {100*m(a['cm']):.0f}% / {100*m(a['cr']):.0f}%")
