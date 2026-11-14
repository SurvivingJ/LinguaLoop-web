# -*- coding: utf-8 -*-
"""One-shot gold evaluation of the frozen configs -> results.json (+ printed tables)."""
import json, os
import common as C, bscore as S
from services.dual_translation import eval_metrics as EM
fz = json.load(open(os.path.join(C.HERE, "frozen_configs.json")))
out = {"gold": {}, "notes": {}}
v5 = {l: {it["id"]: it["expected_bands"] for it in json.load(open(os.path.join(C.REPO, "tests/fixtures/dt_gold", f"{l}.json")))} for l in S.LANGS}
rows = []
for fam in ("selected", "explaining"):
    for m, cfg in fz[fam].items():
        v = cfg["variant"]
        run = S.load_run(m, v, "gold")
        per = {}
        for l in S.LANGS:
            recs = S.records(run, "gold", l, cfg["severity_rule"][l])
            mm = S.metrics(recs, ci=True)
            mm["severity_rule"] = cfg["severity_rule"][l]
            # same predictions against the v5 fixture's expected bands (Sept comparability; differs for 2 en items)
            mm["qwk_vs_v5_bands"] = {d: round(EM.quadratic_weighted_kappa([v5[l][r["id"]][d] for r in recs], [r["pred_bands"][d] for r in recs]), 3)
                                     for d in ("accuracy", "fidelity", "understandability")}
            per[l] = mm
        out["gold"][f"{m}|{v}"] = {"family": fam, "model": S.__dict__.get("x", None) or m, "variant": v, "per_lang": per}
        rows.append((m, v, fam, per))
json.dump(out, open(os.path.join(C.HERE, "gold_results.json"), "w"), indent=1)
for m, v, fam, per in rows:
    print(f"## {m} {v} [{fam}]")
    for l in S.LANGS:
        x = per[l]
        print(f"  {l} sev={x['severity_rule']:5s} acc {x['qwk_accuracy']} {x['ci_accuracy']} fid {x['qwk_fidelity']} {x['ci_fidelity']} und {x['qwk_understandability']} {x['ci_understandability']} nat {x['qwk_naturalness']}"
              f" | P/R {x['span_p']}/{x['span_r']} tpfpfn {x['tp_fp_fn']} type {x['type_top1']} sev {x['sev_exact']} cleanFP {x['item_det']['fp']}/{x['item_det']['n_clean']} MI {x['mi']} MIfp {x['mi_false_pos']}"
              f" | ${x['usd_per_item']:.6f} p50 {x['p50_latency_s']}s p90 {x['p90_latency_s']} json {x['json_valid']} spanmiss {x['span_miss']} v5bands {x['qwk_vs_v5_bands']}")
