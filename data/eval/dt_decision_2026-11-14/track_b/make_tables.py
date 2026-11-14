# -*- coding: utf-8 -*-
"""Builds results.json and prints the markdown tables used in REPORT.md (no API calls)."""
import json, os, collections
import common as C
from run import MODELS
G = json.load(open(os.path.join(C.HERE, "gold_results.json")))["gold"]
Sv = json.load(open(os.path.join(C.HERE, "silver_results.json")))
FZ = json.load(open(os.path.join(C.HERE, "frozen_configs.json")))
L = ("en", "zh", "ja")
BASE = {
 "jev step-by-step (Sept, v5 labels)": {"usd": {"en": .00013, "zh": .00018, "ja": .00023},
   "en": dict(acc=.956, fid=.487, und=.724, P=.95, R=.80, type=.95, sev=.75), "zh": dict(acc=.412, fid=.773, und=.737, P=1.0, R=.52, type=.75, sev=.75),
   "ja": dict(acc=.455, fid=.830, und=.712, P=1.0, R=.50, type=.69, sev=.54), "lat": "~0.3 s"},
 "live grader, v5 (Jul-19, as quoted in brief)": {"usd": {"en": .025, "zh": .05, "ja": .05},
   "en": dict(acc=.778, fid=.487, und=.746), "zh": dict(acc=.570, fid=.891, und=.577), "ja": dict(acc=.412, fid=.371, und=.332), "lat": "minutes (ja)"},
 "live grader, v6 arm B (Oct-08 gate)": {"usd": {"en": .025, "zh": .05, "ja": .05},
   "en": dict(acc=.510, fid=.854, und=.815, P=1.0, R=.929, type=.769, sev=.462), "zh": dict(acc=.561, fid=.865, und=.936, P=.95, R=.731, type=.789, sev=.789),
   "ja": dict(acc=.412, fid=.926, und=.925, P=1.0, R=.778, type=.810, sev=.810), "lat": "minutes (ja)"},
}
def f(x): return "—" if x is None else ("%.2f" % x).replace("0.", ".") if abs(x) < 1 else "%.2f" % x
print("### Frontier (gold)\n")
print("| Grader | $/item (actual) | en acc/fid/und | zh acc/fid/und | ja acc/fid/und | mean QWK (9) | err recall en/zh/ja | err precision en/zh/ja | p50 s |")
print("|---|---|---|---|---|---|---|---|---|")
front = []
for k, v in G.items():
    p = v["per_lang"]; m = k.split("|")[0]
    usd = sum(p[l]["usd_per_item"] for l in L) / 3
    qs = [p[l]["qwk_" + d] or 0 for l in L for d in ("accuracy", "fidelity", "understandability")]
    lat = sorted(p[l]["p50_latency_s"] for l in L)[1]
    front.append({"config": k, "model": MODELS[m][0], "variant": v["variant"], "family": v["family"], "usd_per_item": round(usd, 6),
                  "mean_qwk9": round(sum(qs) / 9, 3), "p50_latency_s": lat})
    print(f"| {MODELS[m][0]} · {v['variant']} | {usd:.6f} | " + " | ".join("/".join(f(p[l]['qwk_' + d]) for d in ('accuracy', 'fidelity', 'understandability')) for l in L)
          + f" | {f(sum(qs)/9)} | " + "/".join(f(p[l]['span_r']) for l in L) + " | " + "/".join(f(p[l]['span_p']) for l in L) + f" | {lat} |")
for name, b in BASE.items():
    qs = [b[l][d] for l in L for d in ("acc", "fid", "und")]
    print(f"| {name} | {b['usd']['en']}–{b['usd']['ja']} | " + " | ".join("/".join(f(b[l][d]) for d in ("acc", "fid", "und")) for l in L)
          + f" | {f(sum(qs)/9)} | " + ("/".join(f(b[l].get('R')) for l in L)) + " | " + ("/".join(f(b[l].get('P')) for l in L)) + f" | {b['lat']} |")
print("\n### Detail (gold)\n")
print("| Config | lang | sev rule | acc [95% CI] | fid [95% CI] | und [95% CI] | nat* | span P/R/F1 (TP/FP/FN) | type top-1 | sev exact | clean items flagged | MI flagged/critical/typed (n=2) | JSON valid | $/item | p50/p90 s |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k, v in G.items():
    m = k.split("|")[0]
    for l in L:
        x = v["per_lang"][l]
        ci = lambda d: f"{f(x['qwk_'+d])} [{f(x['ci_'+d][0])}, {f(x['ci_'+d][1])}]"
        print(f"| {m} {v['variant']} | {l} | {x['severity_rule']} | {ci('accuracy')} | {ci('fidelity')} | {ci('understandability')} | {f(x['qwk_naturalness'])} | "
              f"{f(x['span_p'])}/{f(x['span_r'])}/{f(x['span_f1'])} ({'/'.join(map(str, x['tp_fp_fn']))}) | {f(x['type_top1'])} | {f(x['sev_exact'])} | {x['item_det']['fp']}/10 | "
              f"{x['mi']['flagged']}/{x['mi']['critical']}/{x['mi']['typed_mi']} | {x['json_valid']:.0%} | {x['usd_per_item']:.6f} | {x['p50_latency_s']}/{x['p90_latency_s']} |")
print("\n### Silver: variant x model (mean over 3 languages, model severity)\n")
print("| Model | variant | mean QWK(acc,fid,und) | span P | span R | type top-1 | sev exact | clean flagged (of 19) | $/item | out tok |")
print("|---|---|---|---|---|---|---|---|---|---|")
for k, v in Sv.items():
    m, var, rule = k.split("|")
    if rule != "model": continue
    a = lambda key: sum(v[l][key] for l in L) / 3
    print(f"| {m} | {var} | {f(a('qwk_mean3'))} | {f(a('span_p'))} | {f(a('span_r'))} | {f(a('type_top1'))} | {f(a('sev_exact'))} | {sum(v[l]['item_det']['fp'] for l in L)} | {a('usd_per_item'):.6f} | {a('tok_out'):.0f} |")
print("\n### Silver: variant means over the 6 models\n")
print("| variant | mean QWK | span P | span R | type top-1 | sev exact | clean flagged /114 | $/item | out tok |")
print("|---|---|---|---|---|---|---|---|---|")
six = ["gemini25fl", "gpt6luna", "deepseek41f", "qwen38f", "mistral32", "gemma4"]
vm = {}
for var in ("p1_bare", "p1_span", "p1_expl", "p2"):
    ks = [Sv[f"{m}|{var}|model"] for m in six]
    a = lambda key: sum(k[l][key] for k in ks for l in L) / 18
    vm[var] = {key: round(a(key), 4) for key in ("qwk_mean3", "span_p", "span_r", "type_top1", "sev_exact", "tok_out")}
    vm[var]["usd_per_item"] = round(a("usd_per_item"), 7)
    vm[var]["clean_flagged"] = sum(k[l]['item_det']['fp'] for k in ks for l in L)
    print(f"| {var} | {f(a('qwk_mean3'))} | {f(a('span_p'))} | {f(a('span_r'))} | {f(a('type_top1'))} | {f(a('sev_exact'))} | {vm[var]['clean_flagged']} | {a('usd_per_item'):.6f} | {a('tok_out'):.0f} |")
# severity rule effect on silver per language
print("\n### Silver: severity rule (mean QWK over 6 models x 4 variants)\n")
for l in L:
    for rule in ("model", "prior"):
        vals = [Sv[f"{m}|{var}|{rule}"][l]["qwk_mean3"] for m in six for var in ("p1_bare", "p1_span", "p1_expl", "p2")]
        print(l, rule, round(sum(vals) / len(vals), 3))
# spend
tot = collections.defaultdict(lambda: {"calls": 0, "usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0})
for line in open(os.path.join(C.HERE, "costs.jsonl")):
    d = json.loads(line); t = tot[d["model"]]
    t["calls"] += 1; t["usd"] += d["usd"]; t["prompt_tokens"] += d["prompt_tokens"] or 0; t["completion_tokens"] += d["completion_tokens"] or 0
spend = {"total_usd": round(sum(t["usd"] for t in tot.values()), 6), "calls": sum(t["calls"] for t in tot.values()), "by_model": tot,
         "budget_usd": 0.55, "guard_usd": C.BUDGET_STOP_USD}
print("\nSPEND", json.dumps(spend, default=dict))
# list-price (uncached) cost per item for each gold config
print("\n### list-price uncached $/item (gold tokens)")
lp = {}
for k, v in G.items():
    m = k.split("|")[0]; pi, po = MODELS[m][2]
    c = sum((v["per_lang"][l]["tok_in"] * pi + v["per_lang"][l]["tok_out"] * po) / 1e6 for l in L) / 3
    lp[k] = round(c, 6); print(k, lp[k])
json.dump({"meta": {"date": "2026-11-14", "gold": "tests/fixtures/dt_gold_v6 (30 v5-derived items per language; en_v6_ws_02 excluded)",
                    "silver": "tests/fixtures/dt_silver_v6 (v6 relabel of the Sept silver; en 35, zh 34, ja 32)",
                    "scoring": "services.dual_translation.scoring.compute_dimension_bands + OFFLINE_SCORING_CONFIG; metrics from services.dual_translation.eval_metrics",
                    "models": {a: {"id": MODELS[a][0], "list_price_per_M": MODELS[a][2]} for a in MODELS}},
           "frozen_configs": FZ, "frontier": front, "list_price_uncached_usd_per_item": lp, "baselines_quoted": BASE,
           "gold": G, "silver": Sv, "silver_variant_means": vm, "spend": spend}, open(os.path.join(C.HERE, "results.json"), "w"), indent=1, default=dict)
