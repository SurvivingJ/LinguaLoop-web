"""D3S at the 40/50/60-item snapshots of the research-stage main run: precision, error, coverage and
wall-clock minutes at de6fd05b's measured answer cycle (6.57 s meaning, 7.50 s reading). Read-only."""
import json,sys
from collections import defaultdict
WM,WR=6.57,7.50
d=json.load(open(sys.argv[1]))
acc=defaultdict(lambda: defaultdict(list))
for r in d['rows']:
    snaps=r['res'].get('D3S')
    if not snaps: continue
    N=r['N']
    for target in (40,50,60):
        s=next((x for x in snaps if x['n']>=target),None)
        if s is None: continue
        for k in ((r['lang'],r['prof'],target),(r['lang'],'*',target)):
            a=acc[k]
            a['hw_m'].append(s['hw']/N*100); a['hw_mr'].append(s['rhw']/N*100)
            a['ae_m'].append(abs(s['Tm']-r['T_m'])/N*100); a['ae_mr'].append(abs(s['Tr']-r['T_mr'])/N*100)
            a['cov_m'].append(s['lo']<=r['T_m']<=s['hi']); a['cov_mr'].append(s['rlo']<=r['T_mr']<=s['rhi'])
            a['min'].append((WM*s['n_m']+WR*s['n_r'])/60); a['nm'].append(s['n_m']); a['nr'].append(s['n_r'])
m=lambda v: sum(v)/len(v)
def pct(v,q):
    v=sorted(v); return v[int(q*(len(v)-1))]
print('lang L1 items | n | meaning items | reading items | 90% hw m / m+r (% pool) | MAE m / m+r | 90% cover m / m+r | minutes mean / p95 (measured cycle)')
for k in sorted(acc):
    a=acc[k]
    print(f"{k} | {len(a['min'])} | {m(a['nm']):.1f} | {m(a['nr']):.1f} | ±{m(a['hw_m']):.1f} / ±{m(a['hw_mr']):.1f} | {m(a['ae_m']):.1f} / {m(a['ae_mr']):.1f} | {100*m(a['cov_m']):.0f}% / {100*m(a['cov_mr']):.0f}% | {m(a['min']):.1f} / {pct(a['min'],0.95):.1f}")
