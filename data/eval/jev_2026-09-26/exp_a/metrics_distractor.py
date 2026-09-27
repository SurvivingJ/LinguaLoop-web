# -*- coding: utf-8 -*-
import json
from collections import defaultdict
from analyze import cohens_kappa, pearson, percentile, axes_to_verdict

def main():
    with open("distractor_results.json", encoding="utf-8") as f:
        rows = json.load(f)
    ok = [r for r in rows if "_error" not in r]
    n_err = len(rows) - len(ok)

    by_lang = defaultdict(list)
    for r in ok:
        by_lang[r["_meta"]["lang"]].append(r)

    result = {"n_total": len(rows), "n_ok": len(ok), "n_credit_exhausted_errors": n_err}
    for lang, items in by_lang.items():
        jev_fit, jev_conf = [], []
        gem_fit, gem_conf = [], []
        jev_verdicts, gem_verdicts = [], []
        wrong_probs, gem_conf_for_wrong = [], []
        for it in items:
            m = it["_meta"]
            jf = it["answers"]["fit"]["score"] + 1.0     # jev score is 0-4 -> 1-5
            jc = it["answers"]["confusability"]["score"] + 1.0
            if m["gemini_fit"] is not None:
                jev_fit.append(jf)
                gem_fit.append(m["gemini_fit"])
            if m["gemini_confusability"] is not None:
                jev_conf.append(jc)
                gem_conf.append(m["gemini_confusability"])
            if m["gemini_verdict"] is not None:
                jv = axes_to_verdict(round(jf), round(jc))
                jev_verdicts.append(jv)
                gem_verdicts.append(m["gemini_verdict"])
            wp = it["answers"]["definitely_wrong"]["noul"]
            if m["gemini_confusability"] is not None:
                wrong_probs.append(wp)
                gem_conf_for_wrong.append(m["gemini_confusability"])

        kappa = cohens_kappa(jev_verdicts, gem_verdicts, categories=["accept", "flag", "reject"])
        agree_rate = sum(a == b for a, b in zip(jev_verdicts, gem_verdicts)) / len(jev_verdicts)
        result[lang] = {
            "n": len(items),
            "fit_pearson_r": pearson(jev_fit, gem_fit),
            "confusability_pearson_r": pearson(jev_conf, gem_conf),
            "verdict_kappa_vs_gemini": kappa,
            "verdict_raw_agreement": agree_rate,
            "jev_verdict_dist": {v: jev_verdicts.count(v) for v in ("accept", "flag", "reject")},
            "gemini_verdict_dist": {v: gem_verdicts.count(v) for v in ("accept", "flag", "reject")},
            "definitely_wrong_vs_gemini_confusability_pearson_r": pearson(wrong_probs, gem_conf_for_wrong),
            "mean_definitely_wrong_prob": sum(wrong_probs) / len(wrong_probs),
        }

    costs = [r["usage"]["cost"] for r in ok]
    lats = [r["_latency_s"] for r in ok]
    result["cost_latency"] = {
        "n": len(ok), "total_cost": sum(costs), "mean_cost": sum(costs) / len(costs),
        "p50_latency_s": percentile(lats, 50), "p95_latency_s": percentile(lats, 95),
    }

    with open("metrics_distractor.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
