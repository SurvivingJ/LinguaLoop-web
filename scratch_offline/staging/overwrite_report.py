"""List UPDATEs in a staged writes.jsonl that would replace a different non-null live value.

Usage (from the repo root, with the read-only snapshot in scratch_offline/snap/):
    python scratch_offline/staging/overwrite_report.py WRITES_JSONL EXCLUDE_CSV LANG_ID OUT_CSV
EXCLUDE_CSV has a sense_id column (senses left out of the package). Writes OUT_CSV with
table,row_id,column,sense_id,lemma,live_value,staged_value and prints counts per column.
Note: since 2026-11-22 dim_vocabulary.part_of_speech is normalised by a trigger, so a staged
label that differs only in tagset (名词 vs noun) is not a real overwrite.
"""
import json,csv,sys
writes,excl_csv,lang_id,out=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
excl={int(r['sense_id']) for r in csv.DictReader(open(excl_csv))}
snapv={r['id']:r for r in json.load(open('scratch_offline/snap/dim_vocabulary.json')) if r['language_id']==lang_id}
snaps={r['id']:r for r in json.load(open('scratch_offline/snap/dim_word_senses.json'))}
seen={};pend=[]
for l in open(writes):
    d=json.loads(l)
    if d['op']!='update': continue
    row=(d['payload'][0] if isinstance(d['payload'],list) else d['payload']); rid=dict(d['where']).get('id')
    if d['table']=='dim_vocabulary': pend.append((rid,row)); continue
    if rid in excl: pend=[]; continue
    for t,i,r in [('dim_vocabulary',a,b) for a,b in pend]+[('dim_word_senses',rid,row)]:
        cur=(snapv if t=='dim_vocabulary' else snaps).get(i) or {}
        for k,v in r.items():
            if k in cur and cur[k] is not None and cur[k]!=v:
                seen[(t,i,k)]=(rid,cur.get('lemma') or snapv.get(cur.get('vocab_id'),{}).get('lemma'),cur[k],v)
    pend=[]
with open(out,'w',newline='',encoding='utf-8') as fh:
    w=csv.writer(fh); w.writerow(['table','row_id','column','sense_id','lemma','live_value','staged_value'])
    for (t,i,k),(sid,lem,a,b) in sorted(seen.items()): w.writerow([t,i,k,sid,lem,a,b])
import collections; print(collections.Counter((t,k) for t,i,k in seen))
