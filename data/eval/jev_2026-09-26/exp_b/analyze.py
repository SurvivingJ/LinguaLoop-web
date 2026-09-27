"""
Computes all metrics for the jev tier-classification experiment from the raw
JSON in exp_b/raw/*.json. Prints a compact summary and writes exp_b/metrics.json
(everything needed to write results.md) without dumping raw per-item data.
"""
import json
import os
import numpy as np

OUT_DIR = os.path.dirname(__file__)
RAW_DIR = os.path.join(OUT_DIR, "raw")

TIER_IDX = {f"T{i}": i for i in range(1, 7)}
IDX_TIER = {v: k for k, v in TIER_IDX.items()}


def load(name):
    with open(os.path.join(RAW_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def spearman(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.all(x == x[0]) or np.all(y == y[0]):
        return None

    def rank(a):
        order = np.argsort(a, kind="mergesort")
        ranks = np.empty(len(a), dtype=float)
        sorted_a = a[order]
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and sorted_a[j + 1] == sorted_a[i]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = avg_rank
            i = j + 1
        return ranks

    rx, ry = rank(x), rank(y)
    if np.std(rx) == 0 or np.std(ry) == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def choice_expected_tier(answer):
    """Probability-weighted tier index from a choice-mode answer."""
    probs = answer.get("probabilities", {})
    total = sum(probs.values()) or 1.0
    return sum(TIER_IDX[k] * v for k, v in probs.items() if k in TIER_IDX) / total


def score_expected_tier(answer):
    """score is 0..5 (index into T1..T6 array) -> tier index 1..6."""
    return answer.get("score", None) if answer.get("score") is None else answer["score"] + 1


def extract_main_records(main_out):
    recs = []
    for row in main_out:
        lang = row["lang"]
        item = row["item"]
        res = row["result"]
        if not res.get("ok"):
            continue
        answers = res["answers"]
        choice_ans = answers.get("tier_choice", {})
        score_ans = answers.get("tier_score", {})
        assigned_idx = TIER_IDX.get(item["tier_code"])
        rec = {
            "lang": lang,
            "id": item["id"],
            "assigned_tier": item["tier_code"],
            "assigned_idx": assigned_idx,
            "difficulty": item["difficulty"],
            "n_attempts": item.get("n_attempts", 0),
            "mean_pct": item.get("mean_pct"),
            "mean_test_elo_before": item.get("mean_test_elo_before"),
            "choice": choice_ans.get("choice"),
            "choice_idx": TIER_IDX.get(choice_ans.get("choice")),
            "choice_confidence": choice_ans.get("confidence"),
            "choice_probs": choice_ans.get("probabilities"),
            "choice_expected": choice_expected_tier(choice_ans) if choice_ans else None,
            "score": score_ans.get("score"),
            "score_expected_idx": score_expected_tier(score_ans) if score_ans else None,
            "score_confidence": score_ans.get("confidence"),
            "usage": res.get("usage"),
            "latency": res.get("latency"),
        }
        recs.append(rec)
    return recs


def agreement_stats(recs, pred_key="choice_idx"):
    exact = 0
    within1 = 0
    n = 0
    diffs = []
    for r in recs:
        if r[pred_key] is None or r["assigned_idx"] is None:
            continue
        n += 1
        d = r[pred_key] - r["assigned_idx"]
        diffs.append(d)
        if d == 0:
            exact += 1
        if abs(d) <= 1:
            within1 += 1
    return {
        "n": n,
        "exact_pct": exact / n * 100 if n else None,
        "within1_pct": within1 / n * 100 if n else None,
        "mean_signed_diff": float(np.mean(diffs)) if diffs else None,
        "mean_abs_diff": float(np.mean(np.abs(diffs))) if diffs else None,
    }


def confusion_matrix(recs, pred_key="choice_idx"):
    tiers = [f"T{i}" for i in range(1, 7)]
    mat = {t: {t2: 0 for t2 in tiers} for t in tiers}
    for r in recs:
        if r[pred_key] is None or r["assigned_idx"] is None:
            continue
        mat[r["assigned_tier"]][IDX_TIER[r[pred_key]]] += 1
    return mat


def main():
    main_out = load("task_a_main.json")
    retest_out = load("task_b_retest.json")
    shuffle_out = load("task_c_shuffle.json")
    encontrol_out = load("task_d_english_control.json")
    sanity_out = load("task_e_sanity.json")

    metrics = {}

    # ---- Main agreement / confusion / correlation ----
    all_recs = extract_main_records(main_out)
    metrics["n_total_ok"] = len(all_recs)
    metrics["n_total_sent"] = len(main_out)

    by_lang = {}
    for lang in ("zh", "en", "ja"):
        recs = [r for r in all_recs if r["lang"] == lang]
        choice_agree = agreement_stats(recs, "choice_idx")
        score_agree = agreement_stats(
            [{**r, "score_idx_rounded": round(r["score_expected_idx"]) if r["score_expected_idx"] is not None else None}
             for r in recs],
            pred_key="score_idx_rounded",
        )
        assigned = [r["assigned_idx"] for r in recs if r["assigned_idx"] is not None]
        choice_exp = [r["choice_expected"] for r in recs if r["choice_expected"] is not None]
        score_exp = [r["score_expected_idx"] for r in recs if r["score_expected_idx"] is not None]
        spear_choice = spearman(assigned, choice_exp) if len(set(assigned)) > 1 else None
        spear_score = spearman(assigned, score_exp) if len(set(assigned)) > 1 else None
        spear_choice_score = spearman(choice_exp, score_exp)

        # empirical signal correlation (only where attempts exist)
        emp_recs = [r for r in recs if r["n_attempts"] > 0 and r["mean_test_elo_before"] is not None]
        spear_choice_vs_elo = None
        spear_score_vs_elo = None
        if len(emp_recs) >= 5:
            elo_vals = [r["mean_test_elo_before"] for r in emp_recs]
            ch_vals = [r["choice_expected"] for r in emp_recs]
            sc_vals = [r["score_expected_idx"] for r in emp_recs]
            spear_choice_vs_elo = spearman(elo_vals, ch_vals)
            spear_score_vs_elo = spearman(elo_vals, sc_vals)

        by_lang[lang] = {
            "n": len(recs),
            "choice_agreement": choice_agree,
            "score_agreement_rounded": score_agree,
            "spearman_choice_expected_vs_assigned": spear_choice,
            "spearman_score_vs_assigned": spear_score,
            "spearman_choice_vs_score": spear_choice_score,
            "n_with_empirical_elo": len(emp_recs),
            "spearman_choice_vs_empirical_elo": spear_choice_vs_elo,
            "spearman_score_vs_empirical_elo": spear_score_vs_elo,
            "confusion_matrix_choice": confusion_matrix(recs, "choice_idx"),
            "mean_choice_confidence": float(np.mean([r["choice_confidence"] for r in recs if r["choice_confidence"] is not None])) if recs else None,
            "mean_score_confidence": float(np.mean([r["score_confidence"] for r in recs if r["score_confidence"] is not None])) if recs else None,
        }
    metrics["by_lang"] = by_lang

    # combined across all langs
    assigned_all = [r["assigned_idx"] for r in all_recs]
    choice_exp_all = [r["choice_expected"] for r in all_recs]
    score_exp_all = [r["score_expected_idx"] for r in all_recs]
    metrics["combined"] = {
        "choice_agreement": agreement_stats(all_recs, "choice_idx"),
        "spearman_choice_expected_vs_assigned": spearman(assigned_all, choice_exp_all),
        "spearman_score_vs_assigned": spearman(assigned_all, score_exp_all),
    }

    # ---- Cost / latency from main run ----
    costs = [r["usage"]["cost"] for r in all_recs if r.get("usage")]
    lats = [r["latency"] for r in all_recs if r.get("latency") is not None]
    in_toks = [r["usage"]["input_tokens"] for r in all_recs if r.get("usage")]
    metrics["cost_latency_main"] = {
        "mean_cost_per_call_both_modes": float(np.mean(costs)) if costs else None,
        "mean_latency_s": float(np.mean(lats)) if lats else None,
        "p50_latency_s": float(np.percentile(lats, 50)) if lats else None,
        "p95_latency_s": float(np.percentile(lats, 95)) if lats else None,
        "mean_input_tokens": float(np.mean(in_toks)) if in_toks else None,
    }

    # ---- Task B: test-retest stability ----
    retest_by_key = {}
    for row in retest_out:
        if not row["result"].get("ok"):
            continue
        key = (row["lang"], row["item"]["id"])
        retest_by_key.setdefault(key, []).append(row["result"]["answers"])
    choice_all_match = 0
    choice_total = 0
    score_ranges = []
    score_stds = []
    for key, answers_list in retest_by_key.items():
        choices = [a.get("tier_choice", {}).get("choice") for a in answers_list]
        if all(c is not None for c in choices):
            choice_total += 1
            if len(set(choices)) == 1:
                choice_all_match += 1
        scores = [a.get("tier_score", {}).get("score") for a in answers_list if a.get("tier_score", {}).get("score") is not None]
        if len(scores) >= 2:
            score_ranges.append(max(scores) - min(scores))
            score_stds.append(float(np.std(scores)))
    metrics["retest_stability"] = {
        "n_items": len(retest_by_key),
        "choice_all_3_match_pct": choice_all_match / choice_total * 100 if choice_total else None,
        "mean_score_range_across_reps": float(np.mean(score_ranges)) if score_ranges else None,
        "mean_score_std_across_reps": float(np.mean(score_stds)) if score_stds else None,
        "max_score_range": float(np.max(score_ranges)) if score_ranges else None,
    }

    # ---- Task C: shuffle sensitivity (canonical order [task A choice] vs reversed [task C]) ----
    main_choice_by_key = {}
    for row in main_out:
        if not row["result"].get("ok"):
            continue
        key = (row["lang"], row["item"]["id"])
        main_choice_by_key[key] = row["result"]["answers"].get("tier_choice", {})

    flips = 0
    compared = 0
    prob_diffs = []
    for row in shuffle_out:
        if not row["result"].get("ok"):
            continue
        key = (row["lang"], row["item"]["id"])
        canon = main_choice_by_key.get(key)
        if not canon:
            continue
        shuf = row["result"]["answers"].get("tier_choice", {})
        compared += 1
        if canon.get("choice") != shuf.get("choice"):
            flips += 1
        cp, sp = canon.get("probabilities", {}), shuf.get("probabilities", {})
        keys = set(cp) | set(sp)
        l1 = sum(abs(cp.get(k, 0) - sp.get(k, 0)) for k in keys)
        prob_diffs.append(l1)
    metrics["shuffle_sensitivity"] = {
        "n_compared": compared,
        "choice_flip_pct": flips / compared * 100 if compared else None,
        "mean_l1_prob_diff": float(np.mean(prob_diffs)) if prob_diffs else None,
        "max_l1_prob_diff": float(np.max(prob_diffs)) if prob_diffs else None,
    }

    # ---- Task D: English-prompt control vs native (zh, ja) ----
    encontrol_by_lang = {}
    for lang in ("zh", "ja"):
        native_recs = {r["id"]: r for r in all_recs if r["lang"] == lang}
        en_rows = [row for row in encontrol_out if row["lang"] == lang and row["result"].get("ok")]
        pairs_choice_agree = 0
        pairs_total = 0
        en_assigned_agree = []
        en_choice_exp_vals = []
        en_assigned_vals = []
        gap_vals = []
        for row in en_rows:
            item = row["item"]
            nat = native_recs.get(item["id"])
            if not nat:
                continue
            en_ans = row["result"]["answers"]
            en_choice = en_ans.get("tier_choice", {})
            en_choice_idx = TIER_IDX.get(en_choice.get("choice"))
            pairs_total += 1
            if en_choice_idx == nat["choice_idx"]:
                pairs_choice_agree += 1
            en_expected = choice_expected_tier(en_choice) if en_choice else None
            if en_expected is not None:
                en_choice_exp_vals.append(en_expected)
                en_assigned_vals.append(item["difficulty"])  # placeholder unused
                gap_vals.append(abs(en_expected - nat["choice_expected"]) if nat["choice_expected"] is not None else None)
            assigned_idx = TIER_IDX.get(item["tier_code"])
            if en_choice_idx is not None and assigned_idx is not None:
                en_assigned_agree.append(1 if en_choice_idx == assigned_idx else 0)
        gap_vals_clean = [g for g in gap_vals if g is not None]
        encontrol_by_lang[lang] = {
            "n_pairs": pairs_total,
            "native_vs_english_choice_match_pct": pairs_choice_agree / pairs_total * 100 if pairs_total else None,
            "english_exact_agreement_with_assigned_pct": float(np.mean(en_assigned_agree)) * 100 if en_assigned_agree else None,
            "native_exact_agreement_with_assigned_pct": by_lang[lang]["choice_agreement"]["exact_pct"],
            "mean_abs_gap_expected_tier_native_vs_english": float(np.mean(gap_vals_clean)) if gap_vals_clean else None,
        }
    metrics["english_vs_native_control"] = encontrol_by_lang

    # ---- Task E: sanity-check separability ----
    sanity_metrics = {}
    for lang in ("zh", "en", "ja"):
        rows = [r for r in sanity_out if r["lang"] == lang and r["result"].get("ok")]
        per_tier_choice_exp = {}
        per_tier_score_exp = {}
        exact_hits = 0
        n = 0
        for r in rows:
            ans = r["result"]["answers"]
            choice_ans = ans.get("tier_choice", {})
            score_ans = ans.get("tier_score", {})
            true_idx = TIER_IDX[r["true_tier"]]
            pred_idx = TIER_IDX.get(choice_ans.get("choice"))
            n += 1
            if pred_idx == true_idx:
                exact_hits += 1
            per_tier_choice_exp.setdefault(r["true_tier"], []).append(choice_expected_tier(choice_ans))
            per_tier_score_exp.setdefault(r["true_tier"], []).append(score_expected_tier(score_ans))
        tier_means_choice = {t: float(np.mean(v)) for t, v in per_tier_choice_exp.items()}
        tier_means_score = {t: float(np.mean(v)) for t, v in per_tier_score_exp.items()}
        ordered_choice = [tier_means_choice.get(f"T{i}") for i in range(1, 7) if tier_means_choice.get(f"T{i}") is not None]
        ordered_score = [tier_means_score.get(f"T{i}") for i in range(1, 7) if tier_means_score.get(f"T{i}") is not None]
        monotonic_choice = all(ordered_choice[i] <= ordered_choice[i + 1] for i in range(len(ordered_choice) - 1)) if len(ordered_choice) > 1 else None
        monotonic_score = all(ordered_score[i] <= ordered_score[i + 1] for i in range(len(ordered_score) - 1)) if len(ordered_score) > 1 else None
        sanity_metrics[lang] = {
            "n": n,
            "exact_agreement_pct": exact_hits / n * 100 if n else None,
            "mean_choice_expected_by_tier": tier_means_choice,
            "mean_score_expected_by_tier": tier_means_score,
            "monotonic_choice": monotonic_choice,
            "monotonic_score": monotonic_score,
            "t1_vs_t6_gap_choice": (tier_means_choice.get("T6") - tier_means_choice.get("T1")) if "T6" in tier_means_choice and "T1" in tier_means_choice else None,
        }
    metrics["sanity_check"] = sanity_metrics

    # ---- Cost projection for full library re-tiering ----
    lib_counts = {"zh": 125, "en": 121, "ja": 59}  # active tests w/ target_age_tier, from Supabase count query
    mean_cost = metrics["cost_latency_main"]["mean_cost_per_call_both_modes"] or 0
    mean_lat = metrics["cost_latency_main"]["mean_latency_s"] or 0
    total_lib = sum(lib_counts.values())
    metrics["full_library_projection"] = {
        "active_tests_with_tier_by_lang": lib_counts,
        "total_active_tests": total_lib,
        "projected_cost_usd_both_modes": mean_cost * total_lib,
        "projected_cost_usd_choice_only": mean_cost * total_lib * 0.55,  # rough split; see per-mode below
        "projected_wallclock_s_at_concurrency_8": (mean_lat * total_lib) / 8,
    }

    with open(os.path.join(OUT_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # compact console summary
    print(json.dumps({
        "n_total_ok": metrics["n_total_ok"],
        "combined_choice_agreement": metrics["combined"]["choice_agreement"],
        "combined_spearman_choice": metrics["combined"]["spearman_choice_expected_vs_assigned"],
        "combined_spearman_score": metrics["combined"]["spearman_score_vs_assigned"],
        "cost_latency_main": metrics["cost_latency_main"],
        "retest_stability": metrics["retest_stability"],
        "shuffle_sensitivity": metrics["shuffle_sensitivity"],
        "full_library_projection": metrics["full_library_projection"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
