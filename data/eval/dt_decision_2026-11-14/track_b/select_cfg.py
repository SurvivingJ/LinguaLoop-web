# -*- coding: utf-8 -*-
"""Silver-only config selection. Writes silver_results.json + frozen_configs.json.
Rule (fixed before looking at gold): per model, variant = argmax of the 3-language mean of
qwk_mean3 (model severity); then per language, severity rule = argmax qwk_mean3 (ties -> model)."""
import json, os
import common as C, bscore as S
MODELS = ["gemini25fl", "gpt6luna", "deepseek41f", "qwen38f", "mistral32", "gemma4"]
VARS = ["p1_bare", "p1_span", "p1_expl", "p2"]
res = {}
for m in MODELS:
    for v in VARS:
        for rule in ("model", "prior"):
            res[f"{m}|{v}|{rule}"] = S.score(m, v, "silver", rule)
json.dump(res, open(os.path.join(C.HERE, "silver_results.json"), "w"), indent=1)
def avg(key, f): return sum(f(res[key][l]) for l in S.LANGS) / 3
print("== per model x variant (model severity), mean over 3 langs")
print("model        variant  qwk3  spanP spanR type1 sev   cleanFP  $/item   tok_out")
frozen = {}
for m in MODELS:
    best = None
    for v in VARS:
        k = f"{m}|{v}|model"
        q = avg(k, lambda x: x["qwk_mean3"])
        fp = sum(res[k][l]["item_det"]["fp"] for l in S.LANGS); nc = sum(res[k][l]["item_det"]["n_clean"] for l in S.LANGS)
        print(f"{m:12s} {v:8s} {q:.3f} {avg(k, lambda x: x['span_p']):.3f} {avg(k, lambda x: x['span_r']):.3f} "
              f"{avg(k, lambda x: x['type_top1']):.3f} {avg(k, lambda x: x['sev_exact']):.3f} {fp:2d}/{nc}   "
              f"{avg(k, lambda x: x['usd_per_item']):.6f} {avg(k, lambda x: x['tok_out']):.0f}")
        if best is None or q > best[0]:
            best = (q, v)
    v = best[1]
    frozen[m] = {"variant": v, "severity_rule": {}}
    for l in S.LANGS:
        a, b = res[f"{m}|{v}|model"][l]["qwk_mean3"], res[f"{m}|{v}|prior"][l]["qwk_mean3"]
        frozen[m]["severity_rule"][l] = "prior" if b > a else "model"
print("== variant means over 6 models")
for v in VARS:
    for rule in ("model", "prior"):
        ks = [f"{m}|{v}|{rule}" for m in MODELS]
        row = []
        for l in S.LANGS:
            row.append(f"{l}: qwk3 {sum(res[k][l]['qwk_mean3'] for k in ks)/6:.3f} P {sum(res[k][l]['span_p'] for k in ks)/6:.3f} R {sum(res[k][l]['span_r'] for k in ks)/6:.3f} type {sum(res[k][l]['type_top1'] for k in ks)/6:.3f} sev {sum(res[k][l]['sev_exact'] for k in ks)/6:.3f}")
        print(f"{v:8s} {rule:5s} | " + " | ".join(row) + f" | $ {sum(avg(k, lambda x: x['usd_per_item']) for k in ks)/6:.6f}")
json.dump(frozen, open(os.path.join(C.HERE, "frozen_configs.json"), "w"), indent=1)
print(json.dumps(frozen))
# Second frozen family: the explaining config (p1_expl) for the three precise models, so the
# feedback-design team gets spans + explanations. Severity rule per language chosen on silver the same way.
expl = {}
for m in ["deepseek41f", "qwen38f", "gpt6luna", "gemini31fl"]:
    for rule in ("model", "prior"):  # gemini31fl (mid-price frontier point) was run on p1_expl only
        res.setdefault(f"{m}|p1_expl|{rule}", S.score(m, "p1_expl", "silver", rule))
    expl[m] = {"variant": "p1_expl", "severity_rule": {
        l: ("prior" if res[f"{m}|p1_expl|prior"][l]["qwk_mean3"] > res[f"{m}|p1_expl|model"][l]["qwk_mean3"] else "model")
        for l in S.LANGS}}
json.dump(res, open(os.path.join(C.HERE, "silver_results.json"), "w"), indent=1)
json.dump({"selected": frozen, "explaining": expl}, open(os.path.join(C.HERE, "frozen_configs.json"), "w"), indent=1)
print(json.dumps(expl))
