import json, os, glob, collections, statistics as st
D=os.path.dirname(os.path.abspath(__file__))
man=json.load(open(f'{D}/manifest.json')); meta=json.load(open(f'{D}/meta.json'))
grades=collections.defaultdict(dict); missing=[]
for key,tid in man.items():
    b,i=key.split(':')
    for R in 'AB':
        p=f'{D}/out/{b}_{R}.json'
        try: g=json.load(open(p))[i]; grades[tid][R]=g
        except Exception: missing.append((key,R))
def spearman(x,y):
    def rk(v):
        s=sorted(range(len(v)),key=lambda k:v[k]); r=[0]*len(v); i=0
        while i<len(s):
            j=i
            while j+1<len(s) and v[s[j+1]]==v[s[i]]: j+=1
            for k in range(i,j+1): r[s[k]]=(i+j)/2
            i=j+1
        return r
    a,b=rk(x),rk(y); ma,mb=st.mean(a),st.mean(b)
    num=sum((p-ma)*(q-mb) for p,q in zip(a,b)); den=(sum((p-ma)**2 for p in a)*sum((q-mb)**2 for q in b))**.5
    return num/den if den else float('nan')
rows=[]
for tid,m in meta.items():
    g=grades.get(tid,{})
    if 'A' not in g or 'B' not in g: continue
    a,b=g['A']['tier'],g['B']['tier']; mean=(a+b)/2
    # consensus: exact agree, else round mean toward the alt that both accept, else round half up
    accA={a}|({g['A']['alt']} if g['A'].get('alt') else set()); accB={b}|({g['B']['alt']} if g['B'].get('alt') else set())
    both=accA&accB
    cons = a if a==b else (min(both,key=lambda t:abs(t-mean)) if both else int(mean+0.5))
    cur=m['target_age_tier']
    rows.append(dict(id=tid,lang=m['lang'],slug=m['slug'],title=m['title'],cur=cur,score=m['age_tier_score'],conf=m['age_tier_confidence'],
        A=a,B=b,cons=cons,mean=mean,hit=cur in accA|accB,whyA=g['A'].get('why'),whyB=g['B'].get('why')))
json.dump(rows,open(f'{D}/results.json','w'),ensure_ascii=False,indent=1)
print('missing',len(missing),missing[:10])
for lang in ('zh','en','ja'):
    R=[r for r in rows if r['lang']==lang]
    if not R: continue
    n=len(R)
    ag=sum(r['A']==r['B'] for r in R); w1=sum(abs(r['A']-r['B'])<=1 for r in R)
    ex=sum(r['cons']==r['cur'] for r in R); hit=sum(r['hit'] for r in R)
    d=[r['cur']-r['mean'] for r in R]
    print(f"\n== {lang} n={n}  readers exact {ag} / within1 {w1}  rho(A,B)={spearman([r['A'] for r in R],[r['B'] for r in R]):.3f}")
    print(f"   current tier == consensus {ex}/{n}; current within either reader's accepted set {hit}/{n}")
    print(f"   bias (current - reader mean) {st.mean(d):+.2f}  MAE {st.mean(map(abs,d)):.2f}  rho(jev score, reader mean)={spearman([r['score'] for r in R],[r['mean'] for r in R]):.3f}")
    ct=collections.Counter((r['cur'],r['cons']) for r in R)
    print('   rows=current tier, cols=consensus');print('      '+' '.join(f'T{c}' for c in range(1,7)))
    for c in range(1,7): print(f'   T{c} '+' '.join(f'{ct[(c,k)]:>2}' for k in range(1,7)))
    off2=[r for r in R if abs(r['cur']-r['mean'])>=1.5 and not r['hit']]
    print(f'   >=2-tier disagreements: {len(off2)}')
