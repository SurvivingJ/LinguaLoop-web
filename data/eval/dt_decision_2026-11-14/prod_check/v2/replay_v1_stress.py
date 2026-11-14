"""Replay Track E's recorded prompt-v1 gpt-6-luna responses through the prompt-v1
production decode (commit b0f4936) to count how v1 resolved spans/corrections on the stress set."""
import sys, json, collections, re
V1=sys.argv[1]; REPO='/home/user/LinguaLoop-web'
sys.path.insert(0, V1)
from services.dual_translation import single_call_grader as scg, grader_cascade as gc, single_call_prompts as sp
from services.dual_translation.sentence_pairs import build_sentence_pairs
assert hasattr(sp,'FROZEN_TYPE_IDS')
tax=json.loads(re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", open(REPO+'/migrations/dt_taxonomy_v6_seed.sql',encoding='utf-8').read(), re.S).group(1))
items={}
for l in open(REPO+'/data/eval/dt_decision_2026-11-14/track_e/stress_set.jsonl',encoding='utf-8'):
    it=json.loads(l); items[it['id']]=it
span=collections.defaultdict(collections.Counter); corr=collections.defaultdict(collections.Counter)
for l in open(REPO+'/data/eval/dt_decision_2026-11-14/track_e/runs/gpt6luna__p1_expl.jsonl',encoding='utf-8'):
    r=json.loads(l); it=items[r['id']]; l2=r['lang']; l1={'en':'zh'}.get(l2,'en')
    pairs=build_sentence_pairs(it['reference'], it['reproduction']).pairs
    raw=[{'sentence': e['sentence'], 'span': e['learner_text'], 'type': e['subtype'], 'severity': e['severity'], 'explanation': e.get('explanation')} for e in r['errors']]
    subtypes=tax['pairs'][l2]['subtypes']
    errs,per,dropped,rep=scg._decode(gc, raw, pairs=pairs, type_ids=sp.FROZEN_TYPE_IDS[l2], subtypes=subtypes, taxonomy_cfg=tax, subtype_meta=tax['subtype_meta'], severity_rule='model', l1_code=l1, l2_code=l2, gold_l2=it['reference'], reproduction=it['reproduction'])
    for e in errs:
        span[r['level']][e['span_source']]+=1; corr[r['level']][e['correction_source']]+=1
    span[r['level']]['dropped']+=sum(dropped.values())
print(json.dumps({'span':{k:dict(v) for k,v in span.items()}, 'correction':{k:dict(v) for k,v in corr.items()}}, indent=1))

# --- correction quality: predicted corrected_form vs the gold corrected_form, on matched errors ---
from services.dual_translation import eval_metrics as EM
import os, difflib
def quality(pred_errors, it, acc):
    al = EM.align_errors([e['span_reproduction'] for e in pred_errors], [g['span_repro'] for g in it['expected_errors']])
    for i, j in al.matches:
        p, g = pred_errors[i], it['expected_errors'][j]
        pc, gc_ = (p.get('corrected_form') or '').strip(), (g.get('corrected_form') or '').strip()
        acc['n'] += 1
        acc['exact'] += pc == gc_
        acc['overlap'] += bool(pc and gc_ and (pc in gc_ or gc_ in pc))
        # does applying the correction to the learner sentence move it toward what gold's fix gives?
        acc['len_ratio'].append(len(pc) / max(1, len(gc_)))
res = {}
for level in ('heavy', 'moderate'):
    a = {'n': 0, 'exact': 0, 'overlap': 0, 'len_ratio': []}
    for l in open(REPO+'/data/eval/dt_decision_2026-11-14/track_e/runs/gpt6luna__p1_expl.jsonl', encoding='utf-8'):
        r = json.loads(l)
        if r['level'] != level: continue
        it = items[r['id']]; l2 = r['lang']
        pairs = build_sentence_pairs(it['reference'], it['reproduction']).pairs
        raw = [{'sentence': e['sentence'], 'span': e['learner_text'], 'type': e['subtype'], 'severity': e['severity'], 'explanation': None} for e in r['errors']]
        errs, *_ = scg._decode(gc, raw, pairs=pairs, type_ids=sp.FROZEN_TYPE_IDS[l2], subtypes=tax['pairs'][l2]['subtypes'], taxonomy_cfg=tax, subtype_meta=tax['subtype_meta'], severity_rule='model', l1_code='en', l2_code=l2, gold_l2=it['reference'], reproduction=it['reproduction'])
        quality(errs, it, a)
    b = {'n': 0, 'exact': 0, 'overlap': 0, 'len_ratio': []}
    for l2 in ('en', 'zh', 'ja'):
        path = REPO + f'/data/eval/dt_decision_2026-11-14/prod_check/v2/e_stress_{l2}_{level}.jsonl'
        for l in open(path, encoding='utf-8'):
            r = json.loads(l); quality(r['errors'], items[r['id']], b)
    for x in (a, b):
        lr = sorted(x.pop('len_ratio')); x['median_len_vs_gold'] = round(lr[len(lr)//2], 2) if lr else None
    res[level] = {'v1_alignment': a, 'v2_model_quote': b}
print(json.dumps(res, indent=1))
