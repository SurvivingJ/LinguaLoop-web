"""Walk the whole app at 393x659 through preview.cjs (needs serve.py running).

  python tests/e2e/redesign/serve.py --port 5200 &
  PORT=5200 python3 tests/e2e/redesign/walk.py [pages|session|all]   # QUICK=1: zh light + ja dark only

Every page, and every session player mounted inside /session, in zh and ja, light and dark.
Prints one line per screen (shell, tab/task bar, docks in view, document scroll, small targets,
unmocked API calls, page errors); screenshots and per-case fixtures go to $OUT
(default <tmp>/redesign-walk). Normal app pages (Today, Tests, Me) scroll by design.
"""
import json,subprocess,sys,os,tempfile
from concurrent.futures import ThreadPoolExecutor
REPO=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..'))
FX=REPO+'/tests/e2e/redesign/fixtures'
W=os.environ.get('OUT') or os.path.join(tempfile.gettempdir(),'redesign-walk')
PORT=int(os.environ.get('PORT','5200'))
def load(p): return json.load(open(p))
def merge(*ps):
    out={}
    for p in ps:
        d=load(p) if isinstance(p,str) else p
        out.update({k:v for k,v in d.items() if k!='_comment'})
    return out
base=[FX+'/default.json']
sess=load(FX+'/session-practice.json')
common_session=merge(FX+'/tests.json',FX+'/trainers.json',FX+'/session-speed.json',FX+'/flashcards.json',FX+'/dt-repair.json',FX+'/dt-repair-due.json',FX+'/prestudy.json',sess)
def session_fx(item,lang):
    d=dict(common_session)
    if lang=='3': d.update(merge(FX+'/tests-ja.json',FX+'/prestudy-ja.json'))
    q={'data':{'queue':[dict(item,is_completed=False)],'next_index':0,'tail':None,'tail_queue':[]}}
    d['GET /api/study-session']=q; d['GET /api/study-session*']=q
    return d
ITEMS={
 'reading':{'kind':'test','id':'t1','slug':'zh-weekend-hike','title':'A weekend hike','test_type':'reading'},
 'listening':{'kind':'test','id':'t1','slug':'zh-weekend-hike','title':'A weekend hike','test_type':'listening'},
 'dictation':{'kind':'test','id':'t1','slug':'zh-weekend-hike','title':'A weekend hike','test_type':'dictation'},
 'pinyin':{'kind':'test','id':'t1','slug':'pz','title':'Tones','test_type':'pinyin'},
 'pitch_accent':{'kind':'test','id':'t1','slug':'pj','title':'Pitch','test_type':'pitch_accent'},
 'classifier_drill':{'kind':'test','id':'t1','slug':'cd','title':'Drill','test_type':'classifier_drill'},
 'practice':{'kind':'practice','id':'p1','mode':'maintenance','minutes':10},
 'acquisition':{'kind':'practice','id':'p2','mode':'acquisition','minutes':10},
 'flashcards':{'kind':'flashcards','id':'f1','cards':2},
 'dual_translation':{'kind':'dual_translation','id':'d1'},
 'speed_round':{'kind':'speed_round','id':'s1'},
 'prestudy':{'kind':'prestudy','id':'ps1','slug':'zh-weekend-hike','title':'A weekend hike'},
 'dt_repair':{'kind':'dt_repair','id':'r1'},
}
def pagefx(name,lang):
    d=merge(*base,FX+'/tests.json',FX+'/trainers.json',FX+'/settings.json',FX+'/prestudy.json',FX+'/flashcards.json',FX+'/dual-translation.json',FX+'/dt-profile.json',FX+'/placement.json',sess)
    if lang=='3': d.update(merge(FX+'/tests-ja.json',FX+'/prestudy-ja.json'))
    if name=='placement-result': d.update(load(FX+'/placement-result.json'))
    d['GET /api/study-session']=load(FX+'/session-daily.json')['GET /api/study-session*']
    return d
PAGES={ # name: (path, lang filter, extra args)
 'login':('/login',None,[]),'welcome':('/welcome',None,[]),'langsel':('/language-selection',None,[]),
 'today':('/session',None,['--wait','#sessionStartBtn']),'practice':('/session?mode=practice',None,[]),
 'tests':('/tests',None,[]),'preview':('/test/zh-weekend-hike/preview',None,[]),
 'prestudy':('/test/zh-weekend-hike/prestudy',None,[]),'test':('/test/zh-weekend-hike',None,[]),
 'dictation':('/test/zh-weekend-hike/dictation',None,[]),'pinyin':('/test/pz/pinyin','1',[]),
 'pitch':('/test/pj/pitch-accent','3',[]),'classifier':('/classifier-drill','1',[]),'counter':('/counter-drill','3',[]),
 'calibration':('/calibration',None,[]),
 'placement':('/placement',None,['--click','#plcStartBtn']),'placement-result':('/placement','1',[]),'dt':('/dual-translation',None,[]),'dtprofile':('/dual-translation/profile',None,[]),
 'flashcards':('/flashcards',None,[]),'me':('/profile',None,[]),'studyplan':('/study-plan',None,[]),'wordlist':('/word-list',None,[]),
}
def run(case):
    name,path,lang,mode,ui,fx,extra=case
    fxp=f'{W}/fx-{name}-{lang}.json'
    json.dump(fx,open(fxp,'w'),ensure_ascii=False)
    shot=f'{W}/shots/{name}-{lang}-{mode}-{ui}.png'
    cmd=['node',REPO+'/tests/e2e/redesign/preview.cjs','--port',str(PORT),'--path',path,'--lang',lang,'--mode',mode,'--ui',ui,'--fixtures',fxp,'--json','--shot',shot]+extra
    if name=='login': cmd=[c for c in cmd]+['--fixtures',FX+'/logged-out.json']
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    try: rep=json.loads(r.stdout)[0]
    except Exception: return name,lang,mode,ui,{'fail':r.stdout[-500:]+r.stderr[-500:]}
    return name,lang,mode,ui,rep
def main():
    os.makedirs(W+'/shots',exist_ok=True)
    sel=sys.argv[1] if len(sys.argv)>1 else 'all'
    variants=[(l,m,u) for l,u in (('1','zh'),('3','ja')) for m in ('light','dark')]
    if os.environ.get('QUICK'): variants=[('1','light','zh'),('3','dark','ja')]
    cases=[]
    if sel in('all','pages'):
        for n,(p,lf,ex) in PAGES.items():
            for l,m,u in variants:
                if lf and lf!=l: continue
                cases.append((n,p,l,m,u,pagefx(n,l),ex))
    if sel in('all','session'):
        for k,it in ITEMS.items():
            for l,m,u in variants:
                if k=='pinyin' and l!='1': continue
                if k=='pitch_accent' and l!='3': continue
                cases.append(('s-'+k,'/session',l,m,u,session_fx(it,l),['--wait','#sessionStartBtn','--click','#sessionStartBtn','--eval','new Promise(r=>setTimeout(r,2500))']))
    with ThreadPoolExecutor(int(os.environ.get('J','4'))) as ex:
        res=list(ex.map(run,cases))
    json.dump(res,open(W+'/results-'+sel+'.json','w'),indent=1,ensure_ascii=False)
    for name,l,m,u,r in res:
        if 'fail' in r: print('FAIL',name,l,m,u,r['fail'][:300]); continue
        docks=[(d['inViewport'],len(d['buttonsOffscreen'])) for d in r['docks']]
        flags=[]
        if r['documentScrolls']: flags.append(f"docscroll+{r['documentOverflowPx']}")
        if r['horizontalOverflow']: flags.append('HOVERFLOW')
        if any((not a) or b for a,b in docks): flags.append('DOCK-OFF')
        st=[s for s in r['stages'] if s['overflowPx']>0]
        small=[x for x in r['smallTouchTargetsInView'] if 'ld-skip' not in x]
        errs=[e for e in r['errors'] if 'ERR_FAILED' not in e]
        print(f"{name:18} {l} {m:5} {u} shell={','.join(r['shell']):12} tab={int(r['tabbarVisible'])} task={int(r['taskbarVisible'])} docks={docks} {' '.join(flags)} unmocked={r['unmocked']} small={small[:4]} errs={errs[:3]}")
main()
