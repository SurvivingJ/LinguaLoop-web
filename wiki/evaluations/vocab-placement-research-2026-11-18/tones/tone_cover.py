"""Owner answer to PQ3 (2026-11-18): zh reading foils may be tone variants of a reading, using only syllable+tone
pairs that exist in Mandarin ("only the existing tones, just wrong combos"). Measures, on the live zh pool
(pronunciation-mode rows, one reading per lemma) and the zh dictionary readings, how many readings have a valid
tone variant. Read-only: input is a SELECT export. Rules:
  - syllable+tone is 'attested' if it occurs in any zh dictionary reading (dim_word_senses native zh rows);
  - only full tones 1-4 are changed (a syllable that is neutral in the key, or would become neutral, is left alone);
  - the variant differs from every reading of the same lemma;
  - not a sandhi realisation: no change on 一/不, and no 3->2 change before a tone-3 syllable alone.
"""
import json,sys,unicodedata,itertools,collections
raw=json.load(open(sys.argv[1]))
txt=raw['result'] if isinstance(raw,dict) else raw
i=txt.index('['); j=txt.rindex(']')
row=json.loads(txt[i:j+1])[0]
MARK={'̄':1,'́':2,'̌':3,'̀':4}
def syl(s):
    d=unicodedata.normalize('NFD',s.lower()); t=5; base=''
    for ch in d:
        if ch in MARK: t=MARK[ch]
        elif ch=='̈': base+=':'
        elif ch.isalpha() or ch==':': base+=ch
    return base,t
def parse(disp):
    parts=[p for p in disp.replace('·',' ').replace("'",' ').replace('-',' ').split() if p]
    return [syl(p) for p in parts]
allr=collections.defaultdict(set); inv=collections.defaultdict(set)
for line in row['all_readings'].split('\n'):
    if '\t' not in line: continue
    vid,disp=line.split('\t',1); p=tuple(parse(disp))
    if not p: continue
    allr[int(vid)].add(p)
    for b,t in p:
        if b: inv[b].add(t)
def variants(lemma,p,own):
    n=len(p); aligned=len(lemma)==n
    opts=[]
    for k,(b,t) in enumerate(p):
        if t==5 or (aligned and lemma[k] in '一不'): opts.append([t])
        else: opts.append(sorted(x for x in inv[b] if x in (1,2,3,4)) or [t])
    out=[]
    for combo in itertools.product(*opts):
        v=tuple((b,c) for (b,_),c in zip(p,combo))
        if v==p or v in own: continue
        ch=[k for k in range(n) if combo[k]!=p[k][1]]
        if all(p[k][1]==3 and combo[k]==2 and k+1<n and p[k+1][1]==3 for k in ch): continue
        out.append(v)
    return out
pool=[l.split('\t') for l in row['pool_rows'].split('\n') if l.count('\t')==3]
res=collections.defaultdict(list); nsyl=collections.Counter(); ex=[]
for vid,lemma,band,disp in pool:
    p=tuple(parse(disp)); own=allr.get(int(vid),set())
    v=variants(lemma,p,own) if p else []
    res[int(band)].append(len(v)); nsyl[len(p)]+=1
    if len(ex)<12 and v: ex.append((lemma,disp,[' '.join(b+str(t) for b,t in x) for x in v[:3]]))
tot=[x for b in res for x in res[b]]
print('pool lemmas',len(tot),'syllable counts',dict(sorted(nsyl.items())))
print('inventory: bases',len(inv),'mean attested full tones per base',round(sum(len([t for t in s if t<5]) for s in inv.values())/len(inv),2))
print('>=1 valid tone variant: %d of %d (%.1f%%); >=2: %.1f%%; >=3: %.1f%%'%(sum(x>=1 for x in tot),len(tot),100*sum(x>=1 for x in tot)/len(tot),100*sum(x>=2 for x in tot)/len(tot),100*sum(x>=3 for x in tot)/len(tot)))
for b in sorted(res): r=res[b]; print(' band',b,'n',len(r),'>=1 %.1f%%'%(100*sum(x>=1 for x in r)/len(r)),'>=3 %.1f%%'%(100*sum(x>=3 for x in r)/len(r)))
# proxy for foils: all dictionary readings
allp=[(vid,p) for vid,s in allr.items() for p in s]
ok=sum(1 for vid,p in allp if variants('',p,allr[vid]))
print('all zh dictionary readings with >=1 valid variant: %d of %d (%.1f%%)'%(ok,len(allp),100*ok/len(allp)))
nt=sum(1 for vid,lemma,band,disp in pool if all(t==5 for _,t in parse(disp)))
print('pool readings with no full tone at all',nt)
for e in ex: print(e)
