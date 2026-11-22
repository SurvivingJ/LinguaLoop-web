"""Read-only REST snapshot into scratch_offline/snap/ (same tables and columns as nt_snapshot.py).

For containers with no direct Postgres access: pages every table through PostgREST with the
service key (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY), GET only.
Usage (repo root):  python scratch_offline/staging/rest_snapshot.py ja zh
"""
import os, sys, json, requests, time
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, ROOT+'/scratch_offline')
import nt_snapshot as ns
U=os.environ['SUPABASE_URL']; K=os.environ['SUPABASE_SERVICE_ROLE_KEY']; H={'apikey':K,'Authorization':'Bearer '+K}
SNAP=ns.SNAP; os.makedirs(SNAP, exist_ok=True)
def get(table, cols, flt, key):
    out=[]; last=None
    while True:
        f=flt+([f'{key}=gt.{last}'] if last is not None else [])
        url=f"{U}/rest/v1/{table}?select={cols.replace(' ','')}&order={key}.asc&limit=1000&"+'&'.join(f)
        for a in range(5):
            r=requests.get(url, headers=H, timeout=120)
            if r.ok: break
            time.sleep(3*(a+1))
        r.raise_for_status(); b=r.json(); out+=b
        if len(b)<1000: return out
        last=b[-1][key]
def save(table, rows, lid):
    key=ns.TABLES[table][0]; p=os.path.join(SNAP, table+'.json')
    old=json.load(open(p,encoding='utf-8')) if os.path.exists(p) else []
    m={r[key]:r for r in old}; m.update({r[key]:r for r in rows})
    json.dump(list(m.values()), open(p,'w',encoding='utf-8'), ensure_ascii=False)
    print(table, len(rows), '->', len(m), flush=True)
for lang in sys.argv[1:]:
    lid={'zh':1,'en':2,'ja':3}[lang]
    vocab=None
    for t,(key,cols,w) in ns.TABLES.items():
        if w is None: flt=[]
        elif t=='dim_word_senses': flt=[f'definition_language_id=eq.{lid}']
        else: flt=[f'language_id=eq.{lid}']
        if cols.strip()=='*': cols='*'
        rows=get(t, cols, flt, key)
        if t=='dim_vocabulary': vocab={r['id'] for r in rows}
        if t=='dim_word_senses': rows=[r for r in rows if r['vocab_id'] in vocab]
        save(t, rows, lid)
