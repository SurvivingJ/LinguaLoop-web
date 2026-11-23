"""Compare the live calibration fit (skip = wrong, c=0.25) with a skip-aware fit.
Reads the read-only scratchpad exports; prints numbers only. Run with python3 -I."""
import json, math, sys
ev = json.load(open(sys.argv[1])); dic = json.load(open(sys.argv[2]))
rows = dic if isinstance(dic, list) else dic.get('rows') or dic.get('dict') or list(dic.values())[0]
zipf = {}
for r in rows:
    try: zipf[(int(r[0]), int(r[1]))] = float(r[4]) if r[4] is not None else None
    except Exception: pass
G = 0.25
def sig(x): return 1/(1+math.exp(-max(-60,min(60,x))))
def grid_fit(ll):
    best=(-1e18,None,None)
    for i in range(60):
        a=math.exp(-0.7+0.07*i)
        for j in range(161):
            b=1.0+0.04*j
            v=ll(a,b)
            if v>best[0]: best=(v,a,b)
    return best
for mode in ('definition','pronunciation'):
    pts=[]
    for r in ev['cal']:
        if r[2]!=mode: continue
        z=zipf.get((r[0], r[3]))
        if z is None: continue
        pts.append((z, bool(r[5]), bool(r[6])))
    n=len(pts); sk=sum(p[2] for p in pts); wr=sum((not p[1]) and (not p[2]) for p in pts)
    # live model: skip counted wrong, P(correct)=G+(1-G)K
    def ll_live(a,b):
        t=0
        for z,c,s in pts:
            p=G+(1-G)*sig(a*(z-b)); p=min(max(p,1e-9),1-1e-9)
            t+=math.log(p) if c else math.log(1-p)
        return t
    # skip-aware: known->correct; unknown-> skip w.p. s, else guess (1/4 correct)
    s_hat = sk/max(1,(n - sum(p[1] for p in pts) + sk))  # rough: skips/(skips+wrong+guess-correct share)
    def ll_skip(a,b,s=None):
        s = s_hat if s is None else s
        t=0
        for z,c,sk_ in pts:
            K=sig(a*(z-b))
            if sk_: p=(1-K)*s
            elif c: p=K+(1-K)*(1-s)*G
            else: p=(1-K)*(1-s)*(1-G)
            t+=math.log(max(p,1e-12))
        return t
    l1,a1,b1=grid_fit(ll_live)
    # profile s on a coarse grid too
    best=(-1e18,None,None,None)
    for s in [0.5,0.6,0.7,0.8,0.85,0.9,0.95]:
        l,a,b=grid_fit(lambda a,b: ll_skip(a,b,s))
        if l>best[0]: best=(l,a,b,s)
    l2,a2,b2,s2=best
    L85=math.log(0.85/0.15)
    print(f"{mode}: n={n} skips={sk} wrong_picks={wr} zipf_range=[{min(p[0] for p in pts):.2f},{max(p[0] for p in pts):.2f}]")
    print(f"  live model (skip=wrong):  slope={a1:.2f} mid={b1:.2f} z85={b1+L85/a1:.2f}")
    print(f"  skip-aware (s={s2}):      slope={a2:.2f} mid={b2:.2f} z85={b2+L85/a2:.2f}")
