# -*- coding: utf-8 -*-
"""Silver-only bake-off of decision models on the identical arm-D request."""
import json, statistics, sys
import lib as L, feats as F, pipeline as P
MODELS = ["typesafe/jev-1.13", "typesafe/jev-1.14", "google/gemini-decision-1", "openai/gpt-6-luna-decisions",
          "perplexity/pplx-decider-v1.2", "perplexity/pplx-decider-v1.3:free", "liquid/d1-ultra",
          "microsoft/microsoft-decision-1", "respan/span-02", "morph/reflex"]
CFG = {"det": "D", "tau": 0.5, "sub": "D", "crit": "D", "tau_c": 0.7, "sev": "prior"}
out = {}
print(f"{'model':38s} lang  detAUC critAUC majAUC(cw) sub@1  | fixed cfg: P    R    sevAcc  QWK acc/fid/und   $/unit   lat")
for m in MODELS:
    out[m] = {}
    for lang in L.LANGS:
        rows = [r for r in F.table(lang, "silver", {"": (m, "en")}) if r["complete"]]
        meta = L.item_meta(lang, "silver")
        y = [r["gold_has"] for r in rows]; pos = [r for r in rows if r["gold_has"]]
        det = L.auc(y, [r["err"] for r in rows])
        crit = L.auc([r["gold_sev"] == "critical" for r in pos], [P.crit_score(r, "D") for r in pos])
        nc = [r for r in pos if r["gold_sev"] != "critical"]
        maj = L.auc([r["gold_sev"] == "major" for r in nc], [r["clear_wrong"] for r in nc])
        sub = statistics.mean(P.top_subtype(r, lang, "D") == r["gold_subtype"] for r in pos)
        um = P.unit_metrics(rows, CFG); q = P.band_qwk(rows, meta, list(meta), CFG)
        usd = statistics.mean(r["_usd"] for r in rows); lat = statistics.median(r["_lat"] for r in rows)
        out[m][lang] = {"det_auc": det, "crit_auc": crit, "major_auc_clear_wrong": maj, "subtype_top1": sub,
                        "fixed_cfg": {"unit": um, "qwk": q}, "usd_per_unit": usd, "median_latency_s": lat, "n_units": len(rows)}
        print(f"{m:38s} {lang}    {det:.3f}  {crit:.3f}   {maj:.3f}     {sub:.2f}   |           {um['precision']:.2f} {um['recall']:.2f} {um['severity_acc']:.2f}    "
              f"{q['accuracy']:.2f}/{q['fidelity']:.2f}/{q['understandability']:.2f}  {usd:.6f} {lat:.2f}")
json.dump(out, open("results_models_silver.json", "w"), indent=1, default=str)
