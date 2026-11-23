"""Draft precision exit (both 90% half-widths <= 12% of the pool, checked at the 40 and 45 snapshots) with a cap of 50
scored items, D3S, research-stage main run. Early-stop share and mean items by language, L1 and ability. Read-only."""
import json,sys
from collections import defaultdict
H=0.12; WM,WR=6.57,7.50
d=json.load(open(sys.argv[1]))
acc=defaultdict(lambda: defaultdict(list))
def grp(t): return 'beginner' if t>=5.5 else ('intermediate' if t>=4.0 else 'advanced')
for r in d['rows']:
    s=r['res'].get('D3S')
    if not s: continue
    N=r['N']; cap=next(x for x in s if x['n']>=50); stop=cap
    for x in s:
        if 40<=x['n']<50 and x['hw']<=H*N and x['rhw']<=H*N: stop=x; break
    for k in ((r['lang'],r['prof'],grp(r['tau'])),(r['lang'],r['prof'],'all')):
        a=acc[k]; a['early'].append(stop['n']<50); a['n'].append(stop['n']); a['min'].append((WM*stop['n_m']+WR*stop['n_r'])/60)
        a['right'].append(stop['n_r']/max(stop['n_m'],1) if r['lang']=='zh' else float('nan'))
m=lambda v: sum(v)/len(v)
print('lang L1 group | n | early stop | mean scored items | minutes (measured cycle) | zh share of meaning items right')
for k in sorted(acc):
    a=acc[k]; print(f"{k} | {len(a['n'])} | {100*m(a['early']):.0f}% | {m(a['n']):.1f} | {m(a['min']):.1f} | {m(a['right']):.2f}")
