# -*- coding: utf-8 -*-
import json
from collections import defaultdict
from analyze import roc_auc, best_threshold_accuracy, prec_recall_at, percentile

def main():
    with open("controlled_results.json", encoding="utf-8") as f:
        rows = json.load(f)

    native = [r for r in rows if r["_meta"]["arm"] == "native" and "_error" not in r]
    control = [r for r in rows if r["_meta"]["arm"] == "english_control" and "_error" not in r]

    def score_of(r, q):
        return r["answers"][q]["noul"]

    def summarize(arm_rows, label):
        by_lang = defaultdict(list)
        for r in arm_rows:
            by_lang[r["_meta"]["lang"]].append(r)
        out = {}
        for lang, items in by_lang.items():
            labels = [1 if it["_meta"]["label"] == "correct" else 0 for it in items]
            gram = [score_of(it, "grammatical") for it in items]
            nat = [score_of(it, "natural") for it in items]
            combined = [g * n for g, n in zip(gram, nat)]  # product = "both must hold"
            entry = {"n": len(items)}
            for name, scores in (("grammatical", gram), ("natural", nat), ("combined", combined)):
                auc = roc_auc(scores, labels)
                bt, bacc = best_threshold_accuracy(scores, labels)
                pr50 = prec_recall_at(scores, labels, 0.5)
                entry[name] = {"auc": auc, "best_threshold": bt, "best_acc": bacc, "at_0.5": pr50}
            out[lang] = entry
        return out

    result = {"native": summarize(native, "native"), "english_control": summarize(control, "control")}

    # breakdown by defect_type x subtlety (native arm, combined score, per language)
    breakdown = defaultdict(lambda: {"n": 0, "correct_mean": [], "corrupted_mean": []})
    pair_index = defaultdict(dict)  # (lang,sense_id,defect_type,subtlety) -> {label: combined_score}
    for r in native:
        m = r["_meta"]
        key = (m["lang"], m["sense_id"], m["defect_type"], m["subtlety"])
        g, n = score_of(r, "grammatical"), score_of(r, "natural")
        pair_index[key][m["label"]] = g * n

    detect_by_cell = defaultdict(lambda: [0, 0])  # (defect_type,subtlety) -> [detected, total]
    detect_by_lang_cell = defaultdict(lambda: [0, 0])
    for key, pair in pair_index.items():
        lang, sense_id, defect_type, subtlety = key
        if "correct" not in pair or "corrupted" not in pair:
            continue
        # "detected" = corrupted item scores lower than correct item (correctly ranked)
        detected = 1 if pair["corrupted"] < pair["correct"] else 0
        detect_by_cell[(defect_type, subtlety)][0] += detected
        detect_by_cell[(defect_type, subtlety)][1] += 1
        detect_by_lang_cell[(lang, defect_type, subtlety)][0] += detected
        detect_by_lang_cell[(lang, defect_type, subtlety)][1] += 1

    result["pairwise_ranking_by_defect_subtlety"] = {
        f"{k[0]}/{k[1]}": {"detected": v[0], "total": v[1], "rate": v[0] / v[1]}
        for k, v in sorted(detect_by_cell.items())
    }
    result["pairwise_ranking_by_lang_defect_subtlety"] = {
        f"{k[0]}/{k[1]}/{k[2]}": {"detected": v[0], "total": v[1], "rate": v[0] / v[1]}
        for k, v in sorted(detect_by_lang_cell.items())
    }

    # cost / latency
    all_ok = [r for r in rows if "_error" not in r]
    costs = [r["usage"]["cost"] for r in all_ok]
    lats = [r["_latency_s"] for r in all_ok]
    result["cost_latency"] = {
        "n": len(all_ok), "total_cost": sum(costs), "mean_cost": sum(costs) / len(costs),
        "p50_latency_s": percentile(lats, 50), "p95_latency_s": percentile(lats, 95),
    }

    with open("metrics_controlled.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
