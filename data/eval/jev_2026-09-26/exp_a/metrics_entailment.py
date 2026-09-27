# -*- coding: utf-8 -*-
import json
from collections import defaultdict
from analyze import roc_auc, best_threshold_accuracy, prec_recall_at, cohens_kappa, percentile

REPO = r"c:\Users\James\Documents\Coding\LinguaLoop\WebApp"

def load_existing_verdicts():
    """item_id -> {'verdict':..., 'model':...} from the two v3 files (gemini
    where available: en (v3 file) and ja (ja_models file, gemini rows)."""
    out = {}
    with open(REPO + r"\data\eval\entailment_v3_2026-08-19.json", encoding="utf-8") as f:
        for r in json.load(f):
            out[r["item_id"]] = {"verdict": r["verdict"], "model": r["model"], "lang": r["lang"]}
    # ja gemini-specific overlay (prefer gemini rows for ja if present)
    with open(REPO + r"\data\eval\entailment_v3_ja_models_2026-08-19.json", encoding="utf-8") as f:
        for r in json.load(f):
            if r["model"] == "google/gemini-3.5-flash-lite":
                out[r["item_id"]] = {"verdict": r["verdict"], "model": r["model"], "lang": r["lang"]}
    return out

def main():
    with open("entailment_results.json", encoding="utf-8") as f:
        rows = json.load(f)
    ok = [r for r in rows if "_error" not in r]
    existing = load_existing_verdicts()

    by_lang = defaultdict(list)
    for r in ok:
        by_lang[r["_meta"]["lang"]].append(r)

    result = {}
    for lang, items in by_lang.items():
        scores = [it["answers"]["entailed"]["noul"] for it in items]
        labels = [it["_meta"]["gold_label"] for it in items]
        auc = roc_auc(scores, labels)
        bt, bacc = best_threshold_accuracy(scores, labels)
        pr50 = prec_recall_at(scores, labels, 0.5)

        # kappa vs existing judge, on the overlapping item_ids (pos/neg0/neg1 only)
        jev_bin, exist_bin = [], []
        model_used = None
        for it in items:
            iid = it["_meta"]["item_id"]
            ex = existing.get(iid)
            if not ex:
                continue
            model_used = ex["model"]
            jev_bin.append(1 if it["answers"]["entailed"]["noul"] >= 0.5 else 0)
            # collapse existing 5-band verdict to binary: accept->1, reject->1's negation;
            # 'flag' is genuinely ambiguous -> drop from kappa (documented, not silently included)
            v = ex["verdict"]
            if v == "accept":
                exist_bin.append(1)
            elif v == "reject":
                exist_bin.append(0)
            else:
                jev_bin.pop()  # drop the paired jev entry too, keep arrays aligned
                continue
        kappa = cohens_kappa(jev_bin, exist_bin, categories=[0, 1]) if jev_bin else None

        result[lang] = {
            "n": len(items), "auc": auc, "best_threshold": bt, "best_acc": bacc, "at_0.5": pr50,
            "kappa_vs_existing_judge": kappa, "existing_judge_model": model_used,
            "n_compared_vs_existing": len(jev_bin),
            "mean_score_by_label": {
                "pos(gold=1)": sum(s for s, l in zip(scores, labels) if l == 1) / max(1, sum(labels)),
                "neg(gold=0)": sum(s for s, l in zip(scores, labels) if l == 0) / max(1, len(labels) - sum(labels)),
            },
        }

    all_ok = ok
    costs = [r["usage"]["cost"] for r in all_ok]
    lats = [r["_latency_s"] for r in all_ok]
    result["cost_latency"] = {
        "n": len(all_ok), "total_cost": sum(costs), "mean_cost": sum(costs) / len(costs),
        "p50_latency_s": percentile(lats, 50), "p95_latency_s": percentile(lats, 95),
    }

    with open("metrics_entailment.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
