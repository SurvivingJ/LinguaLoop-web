# -*- coding: utf-8 -*-
"""Score the production single-call path's gold run (gold_{en,zh,ja}.jsonl, written by
scripts/run_dt_grading_eval.py --single-call --dump-jsonl) the way Track B scored its
arms (track_b/bscore.py): same eval_metrics functions, the 30 v5-derived items per
language (the one v6-only en item excluded), QWK on accuracy/fidelity/understandability.
Also diffs each item against Track B's recorded gpt-6-luna p1_expl output. No model calls.
    python data/eval/dt_decision_2026-11-14/prod_check/compare.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TRACK_B = os.path.join(HERE, "..", "track_b")
sys.path.insert(0, REPO)
from services.dual_translation import eval_metrics as EM  # noqa: E402

DIMS = ("accuracy", "fidelity", "understandability")
TRACK_B_ROW = {  # REPORT.md §4, gpt6luna p1_expl
    "en": {"qwk": [1.00, .84, .79], "P": 1.00, "R": .93},
    "zh": {"qwk": [.74, .84, .74], "P": .96, "R": .85},
    "ja": {"qwk": [.92, .87, .76], "P": .96, "R": .89},
}
RULE = {"en": "prior", "zh": "model", "ja": "model"}


def rows(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main():
    track_b = {r["id"]: r for r in rows(os.path.join(TRACK_B, "runs", "gpt6luna__p1_expl__gold.jsonl"))}
    out = {"spend_usd": 0.0, "calls": 0, "langs": {}}
    for name in sorted(os.listdir(HERE)):  # every dumped run counts toward spend, smoke included
        if name.endswith(".jsonl"):
            for r in rows(os.path.join(HERE, name)):
                for a in ((r["grader_trace"].get("single_call") or {}).get("attempts") or []):
                    out["calls"] += 1
                    out["spend_usd"] += a.get("cost_usd") or 0.0
    out["spend_usd"] = round(out["spend_usd"], 6)
    for l2 in ("en", "zh", "ja"):
        with open(os.path.join(REPO, "tests", "fixtures", "dt_gold_v6", f"{l2}.json"), encoding="utf-8") as fh:
            gold = {it["id"]: it for it in json.load(fh) if "_v6_" not in it["id"]}
        recs, paths, lat, n_diff, diffs = [], {}, [], 0, []
        dropped = repaired = sentence_corr = n_err = 0
        for r in rows(os.path.join(HERE, f"gold_{l2}.jsonl")):
            if r["id"] not in gold:
                continue
            it = gold[r["id"]]
            trace = r["grader_trace"]
            sc = trace.get("single_call") or {}
            path = sc.get("path") or ("tier0" if trace.get("deterministic_prefilter") else "other")
            paths[path] = paths.get(path, 0) + 1
            if sc.get("latency_ms"):
                lat.append(sc["latency_ms"])
            dropped += sc.get("dropped_total", 0)
            repaired += sc.get("span_repaired", 0)
            n_err += len(r["errors"])
            sentence_corr += sum(e.get("correction_source") == "reference_sentence" for e in r["errors"])
            recs.append({
                "id": r["id"], "kind": it.get("kind", "single"),
                "pred_errors": [{"span": e["span_reproduction"], "subtype": e["subtype"],
                                 "severity": e["severity"]} for e in r["errors"]],
                "exp_errors": [{"span": e["span_repro"], "subtype": e["subtype"],
                                "severity": e["severity_v2"]} for e in it["expected_errors"]],
                "pred_bands": r["scores"], "exp_bands": it["expected_bands"],
                "exp_overall": None, "pred_overall": None,
            })
            tb = track_b.get(r["id"])
            if tb is not None:
                mine = sorted((e["subtype"], e.get("model_severity"), e["span_reproduction"][0]) for e in r["errors"])
                theirs = sorted((e["subtype"], e["severity"], e["span"][0]) for e in tb["errors"])
                if mine != theirs:
                    n_diff += 1
                    diffs.append({"id": r["id"], "prod": mine, "track_b": theirs})
        m = EM.aggregate_metrics(recs, dimensions=DIMS)
        lat.sort()
        out["langs"][l2] = {
            "n": len(recs),
            "qwk": [round(m["bands"][d]["qwk"], 2) for d in DIMS],
            "P": round(m["span"]["precision"], 2), "R": round(m["span"]["recall"], 2),
            "tp_fp_fn": [m["span"][k] for k in ("tp", "fp", "fn")],
            "type_top1": round(m["subtype_accuracy"]["accuracy"], 2),
            "sev_exact": round(m["severity"]["exact"], 2),
            "clean_items_flagged": m["clean_fp"],
            "severity_rule": RULE[l2], "paths": paths,
            "errors": n_err, "dropped": dropped, "span_repaired": repaired,
            "correction_is_whole_reference_sentence": sentence_corr,
            "p50_latency_ms": lat[len(lat) // 2] if lat else None,
            "track_b": TRACK_B_ROW[l2],
            "items_whose_model_output_differs_from_track_b_recorded": n_diff,
            "differences": diffs,
        }
    with open(os.path.join(HERE, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"spend ${out['spend_usd']:.6f} over {out['calls']} calls")
    for l2, v in out["langs"].items():
        print(l2, "prod qwk", v["qwk"], "P/R", v["P"], v["R"], "| track B", v["track_b"], "| paths", v["paths"],
              "| differing items", v["items_whose_model_output_differs_from_track_b_recorded"],
              "dropped", v["dropped"], "repaired", v["span_repaired"])


if __name__ == "__main__":
    main()
