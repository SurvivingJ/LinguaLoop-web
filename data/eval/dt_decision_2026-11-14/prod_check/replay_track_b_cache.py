"""Zero-cost replay: production single-call path fed Track B's cached gpt-6-luna responses."""
import sys, os, json, re, hashlib, logging
REPO = os.getcwd(); sys.path.insert(0, REPO)
TB = os.path.join(REPO, 'data/eval/dt_decision_2026-11-14/track_b'); sys.path.insert(0, TB)
logging.basicConfig(level=logging.ERROR)
import common as C, bscore as B
from services.dimension_service import DimensionService
from services.dual_translation import grader_cascade as gc, single_call_grader as scg, eval_metrics as EM, tier0
from config import Config
Config.DT_SINGLE_CALL_LOG_LLM_CALLS = False
LID = {'zh': 1, 'en': 2, 'ja': 3}; CODE = {v: k for k, v in LID.items()}
DimensionService.get_language_code = classmethod(lambda cls, lid: CODE.get(lid))
def lit(path, tag):
    return json.loads(re.search(rf"\${tag}\$(.*?)\${tag}\$", open(path, encoding='utf-8').read(), re.S).group(1))
gc._cfg_cache.update({'taxonomy': lit('migrations/dt_taxonomy_v6_seed.sql', 'taxonomy'), 'taxonomy_version': 6,
                      'rubric': lit('migrations/dt_rubric_v6_seed.sql', 'rubric'), 'rubric_version': 6})
miss = [0]
def fake_call(slug, system_prompt, user_prompt, *, schema, max_tokens, extra=None, timeout=30):
    body = {"model": slug, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0, "max_tokens": max_tokens,
            "response_format": {"type": "json_schema", "json_schema": schema}, "usage": {"include": True}}
    body.update(extra or {})
    path = os.path.join(TB, 'cache', C._key(body) + '.json')
    if not os.path.exists(path):
        miss[0] += 1; raise RuntimeError('cache miss')
    r = json.load(open(path, encoding='utf-8'))
    u = r.get('usage') or {}
    return {"content": r['content'], "tokens_in": u.get('prompt_tokens') or 0, "tokens_out": u.get('completion_tokens') or 0,
            "cached_tokens": None, "reasoning_tokens": u.get('reasoning_tokens'), "cost_usd": u.get('cost'),
            "latency_s": r.get('latency'), "provider": r.get('provider'), "finish_reason": r.get('finish')}
scg.call_structured = fake_call
class NoDB:
    def table(self, *a, **k): raise RuntimeError('no db in replay')
out = {}
tb_run = B.load_run('gpt6luna', 'p1_expl', 'gold')
rule = {'en': 'prior', 'zh': 'model', 'ja': 'model'}
for l in ('en', 'zh', 'ja'):
    recs = []; diffs = 0; stats = {'repaired': 0, 'dropped': 0, 'corr': {}}
    tb_recs = {r['id']: r for r in B.records(tb_run, 'gold', l, rule[l])}
    for it in C.load_set('gold', l):
        tier0.clear_cache()
        c = gc.grade_submission(NoDB(), passage_id=it['source_passage_id'], gold_l2=it['reference'], reproduction=it['reproduction'],
                                l2_language_id=LID[l], l1_language_id=LID['zh' if l == 'en' else 'en'], age_tier=3,
                                framework_v2=True, single_call=True)
        sc = c['grader_trace'].get('single_call', {})
        if not sc.get('used') and not c['grader_trace'].get('deterministic_prefilter'):
            print('NOT USED', it['id'], sc.get('reason'))
        stats['repaired'] += sc.get('span_repaired', 0); stats['dropped'] += sc.get('dropped_total', 0)
        for e in c['errors']:
            stats['corr'][e.get('correction_source')] = stats['corr'].get(e.get('correction_source'), 0) + 1
        pred = [{'span': e['span_reproduction'], 'subtype': e['subtype'], 'severity': e['severity']} for e in c['errors']]
        bands = dict(c['scores']); 
        tbb = tb_recs[it['id']]['pred_bands']
        if any(bands.get(d) != tbb[d] for d in ('accuracy', 'fidelity', 'understandability')) or len(pred) != len(tb_recs[it['id']]['pred_errors']):
            diffs += 1; print('DIFF', it['id'], bands, tbb, len(pred), len(tb_recs[it['id']]['pred_errors']), c['grader_trace'].get('tier'))
        recs.append({'id': it['id'], 'kind': it.get('kind', 'single'), 'pred_errors': pred,
                     'exp_errors': [{'span': e['span_repro'], 'subtype': e['subtype'], 'severity': e['severity_v2']} for e in it['expected_errors']],
                     'pred_bands': bands, 'exp_bands': it['expected_bands'], 'exp_overall': None, 'pred_overall': None})
    m = EM.aggregate_metrics(recs, dimensions=('accuracy', 'fidelity', 'understandability'))
    out[l] = {d: round(m['bands'][d]['qwk'], 2) for d in ('accuracy', 'fidelity', 'understandability')}
    out[l].update(P=round(m['span']['precision'], 2), R=round(m['span']['recall'], 2), tp_fp_fn=[m['span'][k] for k in ('tp', 'fp', 'fn')], band_diffs_vs_trackB=diffs, **stats)
print(json.dumps(out, indent=1), 'cache misses', miss[0])
import random
random.seed(1)
for l in ('en','zh','ja'):
    its=[i for i in C.load_set('gold', l) if i['expected_errors']]
    for it in random.sample(its, 5):
        tier0.clear_cache()
        c = gc.grade_submission(NoDB(), passage_id=it['source_passage_id'], gold_l2=it['reference'], reproduction=it['reproduction'], l2_language_id=LID[l], l1_language_id=LID['zh' if l == 'en' else 'en'], age_tier=3, single_call=True)
        for e in c['errors']:
            print(l, '|', e['learner_form'], '=>', e['corrected_form'], '|', e['subtype'], e['severity'], e['model_severity'], e['span_source'], e['correction_source'], '|', e['explanation'][:70].replace('\n',' '), '|', e['model_note'])
