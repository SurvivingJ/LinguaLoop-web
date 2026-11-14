# -*- coding: utf-8 -*-
"""best_outputs.jsonl: per-item outputs of the silver-selected explaining config (deepseek41f p1_expl)."""
import json, os
import common as C, bscore as S
fz = json.load(open(os.path.join(C.HERE, "frozen_configs.json")))["explaining"]["deepseek41f"]
n = 0
with open(os.path.join(C.HERE, "best_outputs.jsonl"), "w", encoding="utf-8") as f:
    for which in ("gold", "silver"):
        run = S.load_run("deepseek41f", "p1_expl", which)
        for l in S.LANGS:
            rule = fz["severity_rule"][l]
            for it in C.load_set(which, l):
                r = run[it["id"]]
                final = S.apply_sev(r["errors"], rule)
                errs = [{"sentence": e["sentence"], "span": e["span"], "learner_text": e["learner_text"],
                         "type": e["subtype"], "severity_model": e["severity"], "severity_final": fe["severity"],
                         "explanation": e.get("explanation")} for e, fe in zip(r["errors"], final)]
                f.write(json.dumps({
                    "set": which, "id": it["id"], "lang": l, "kind": it.get("kind"),
                    "model": "deepseek/deepseek-v4.1-flash", "variant": "p1_expl", "severity_rule": rule,
                    "reference": it["reference"], "reproduction": it["reproduction"],
                    "predicted_errors": errs, "predicted_bands": S.bands_of(final),
                    "expected_errors": [{"span": e["span_repro"], "learner_form": e["learner_form"], "corrected_form": e["corrected_form"],
                                         "type": e["subtype"], "severity": e["severity_v2"]} for e in it["expected_errors"]],
                    "expected_bands": it["expected_bands"], "usd": r.get("usd"), "latency_s": r.get("latency")}, ensure_ascii=False) + "\n")
                n += 1
print("wrote", n)
