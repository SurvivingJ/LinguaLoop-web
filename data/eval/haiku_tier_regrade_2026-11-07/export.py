import json, os, random, sys
REPO='/home/user/LinguaLoop-web'; sys.path.append(REPO)
from services.categorical_maps import TIER_CONSTRAINTS, TIER_DISPLAY_NAMES, VALID_TIERS
import requests
OUT=os.path.dirname(os.path.abspath(__file__))
K=os.environ['SUPABASE_SERVICE_ROLE_KEY']; H={'apikey':K,'Authorization':'Bearer '+K}
LANGS={'zh':(1,25),'en':(2,11),'ja':(3,30)}
HEAD={'zh':('## 评分标准','：'),'en':('## Rubric',': '),'ja':('## ルーブリック','：')}
meta={}; manifest={}
for lang,(lid,per) in LANGS.items():
    rows=requests.get(os.environ['SUPABASE_URL']+'/rest/v1/tests',headers=H,params={'select':'id,slug,transcript,target_age_tier,age_tier_score,age_tier_confidence,age_tier_calibration,title','is_active':'eq.true','language_id':f'eq.{lid}','order':'id'}).json()
    random.Random(7).shuffle(rows)
    rub=[HEAD[lang][0]+'\n']+[f'- **{t}** {TIER_DISPLAY_NAMES[t][lid]}{HEAD[lang][1]}{TIER_CONSTRAINTS[t][lid]}' for t in VALID_TIERS]
    for b in range(0,len(rows),per):
        chunk=rows[b:b+per]; name=f'{lang}_{b//per+1:02d}'
        lines=[f'# Blind age-tier grading — batch {name}\n']+rub+['','## Passages\n']
        for i,r in enumerate(chunk,1):
            key=f'{i:02d}'; manifest[f'{name}:{key}']=r['id']
            lines.append(f'### Item {key}\n\n{r["transcript"]}\n')
        open(f'{OUT}/batches/{name}.md','w').write('\n'.join(lines))
        print(name,len(chunk),sum(len(r['transcript'] or '') for r in chunk))
    for r in rows: meta[r['id']]={k:r[k] for k in r if k!='transcript'}|{'lang':lang,'chars':len(r['transcript'] or '')}
json.dump(manifest,open(f'{OUT}/manifest.json','w'),indent=1)
json.dump(meta,open(f'{OUT}/meta.json','w'),ensure_ascii=False,indent=1)
