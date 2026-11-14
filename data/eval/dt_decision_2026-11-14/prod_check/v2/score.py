# -*- coding: utf-8 -*-
"""Score production single-call runs (prompt v2) written by
scripts/run_dt_grading_eval.py --single-call --dump-jsonl. No model calls.

    python data/eval/dt_decision_2026-11-14/prod_check/v2/score.py gold  <prefix> <run> [<run> ...]
    python data/eval/dt_decision_2026-11-14/prod_check/v2/score.py stress <prefix> <level>
    python data/eval/dt_decision_2026-11-14/prod_check/v2/score.py spend

gold:   files <prefix>_gold_{en,zh,ja}_<run>.jsonl, scored like prod_check/compare.py
        (the 30 v5-derived items per language, Track B's metric code).
stress: files <prefix>_stress_{en,zh,ja}_<level>.jsonl against track_e/stress_set.jsonl,
        with Track E's sentence-level false-flag count (analyze.py sentence_table).
spend:  sums usage.cost over every *.jsonl in this directory.
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, REPO)
from services.dual_translation import eval_metrics as EM  # noqa: E402
from services.dual_translation.sentence_pairs import build_sentence_pairs  # noqa: E402

DIMS = ("accuracy", "fidelity", "understandability")
JUDGED = ("naturalness", "range")
LANGS = ("en", "zh", "ja")
SEV_RANK = {"minor": 0, "major": 1, "critical": 2}
WEIGHTS = {"default": {"accuracy": .3, "fidelity": .15, "naturalness": .1, "range": .15, "understandability": .3},
           "ja": {"fidelity": .3}, "zh": {"accuracy": .4}}  # dt_rubric_v6_seed.sql


def rows(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def overall(bands, l2):
    w = dict(WEIGHTS["default"]); w.update(WEIGHTS.get(l2, {}))
    dims = [d for d in w if d in bands]
    return max(1, min(4, round(sum(bands[d] * w[d] for d in dims) / sum(w[d] for d in dims))))


def record(r, it):
    return {
        "id": r["id"], "kind": it.get("kind", "single"),
        "pred_errors": [{"span": e["span_reproduction"], "subtype": e["subtype"], "severity": e["severity"]}
                        for e in r["errors"]],
        "exp_errors": [{"span": e["span_repro"], "subtype": e["subtype"], "severity": e["severity_v2"]}
                       for e in it["expected_errors"]],
        "pred_bands": r["scores"], "exp_bands": it["expected_bands"], "exp_overall": None, "pred_overall": None,
    }


def auc(pos, neg):
    """P(score of a true positive > score of a false positive), ties 0.5."""
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 3)


def summarise(pairs, l2s=LANGS):
    """pairs: [(run_row, gold_item, l2)] -> metrics dict."""
    out = {}
    tot = collections.Counter(); span = collections.Counter(); corr = collections.Counter()
    expl = collections.Counter(); rej = collections.Counter(); drop = collections.Counter()
    conf = {"tp": collections.Counter(), "fp": collections.Counter()}
    judg = {d: {"n": 0, "scored": 0, "exact": 0, "pairs": collections.Counter(), "status": collections.Counter()} for d in JUDGED}
    ov = {"n": 0, "exact": 0, "yt": [], "yp": []}
    lat = []; paths = collections.Counter(); src = collections.Counter(); aliased = 0; other_sentence = 0
    for l2 in l2s:
        recs = []
        for r, it, lang in pairs:
            if lang != l2:
                continue
            rec = record(r, it); recs.append(rec)
            sc = (r["grader_trace"].get("single_call") or {})
            paths[sc.get("path") or ("tier0" if r["grader_trace"].get("deterministic_prefilter") else "other")] += 1
            if not sc.get("used"):
                continue
            if sc.get("latency_ms"):
                lat.append(sc["latency_ms"])
            for k, v in (sc.get("dropped") or {}).items():
                drop[k] += v
            aliased += sc.get("type_aliased", 0); other_sentence += sc.get("span_other_sentence", 0)
            for k, v in (sc.get("explanation_rejections") or {}).items():
                rej[k] += v
            al = EM.align_errors([p["span"] for p in rec["pred_errors"]], [e["span"] for e in rec["exp_errors"]])
            matched = {i for i, _ in al.matches}
            for i, e in enumerate(r["errors"]):
                span[e.get("span_source")] += 1; corr[e.get("correction_source")] += 1
                expl[e.get("explanation_source")] += 1; src[e.get("source")] += 1
                conf["tp" if i in matched else "fp"][e.get("confidence_label")] += 1
            for d in JUDGED:
                j = (sc.get("judgments") or {}).get(d) or {}
                judg[d]["n"] += 1; judg[d]["status"][j.get("status")] += 1
                if d in r["scores"]:
                    judg[d]["scored"] += 1
                    judg[d]["exact"] += r["scores"][d] == it["expected_bands"][d]
                    judg[d]["pairs"][f"gold{it['expected_bands'][d]}->pred{r['scores'][d]}"] += 1
            eo = overall(it["expected_bands"], l2)
            ov["n"] += 1; ov["exact"] += eo == r["overall_band"]; ov["yt"].append(eo); ov["yp"].append(r["overall_band"])
        if not recs:
            continue
        m = EM.aggregate_metrics(recs, dimensions=DIMS)
        clean = [x for x in recs if x["kind"] == "clean"]
        out[l2] = {
            "n": len(recs),
            "qwk": [round(m["bands"][d]["qwk"], 2) for d in DIMS],
            "exact": [round(sum(x["pred_bands"][d] == x["exp_bands"][d] for x in recs) / len(recs), 2) for d in DIMS],
            "P": round(m["span"]["precision"], 2), "R": round(m["span"]["recall"], 2),
            "tp_fp_fn": [m["span"][k] for k in ("tp", "fp", "fn")],
            "type_top1": round(m["subtype_accuracy"]["accuracy"], 2),
            "sev_exact": round(m["severity"]["exact"], 2),
            "clean_items": len(clean), "clean_items_flagged": sum(1 for x in clean if x["pred_errors"]),
        }
        for k in ("tp", "fp", "fn"):
            tot[k] += m["span"][k]
        tot["clean"] += len(clean); tot["clean_flagged"] += out[l2]["clean_items_flagged"]
    val = {"high": .9, "medium": .6, "low": .3, None: .5}
    pos = [val[k] for k, n in conf["tp"].items() for _ in range(n)]
    neg = [val[k] for k, n in conf["fp"].items() for _ in range(n)]
    lat.sort()
    out["pooled"] = {
        "P": round(tot["tp"] / max(1, tot["tp"] + tot["fp"]), 2), "R": round(tot["tp"] / max(1, tot["tp"] + tot["fn"]), 2),
        "tp_fp_fn": [tot["tp"], tot["fp"], tot["fn"]],
        "clean_items_flagged": f"{tot['clean_flagged']}/{tot['clean']}",
        "span_resolution": dict(span), "span_found_in_other_sentence": other_sentence,
        "correction_resolution": dict(corr), "explanation_shown": dict(expl), "explanation_rejections": dict(rej),
        "dropped": dict(drop), "type_aliased": aliased, "source": dict(src),
        "confidence": {"true_positive": dict(conf["tp"]), "false_positive": dict(conf["fp"]),
                       "precision_by_label": {k: round(conf["tp"][k] / (conf["tp"][k] + conf["fp"][k]), 2)
                                              for k in ("high", "medium", "low") if conf["tp"][k] + conf["fp"][k]},
                       "auc_tp_vs_fp": auc(pos, neg)},
        "judged": {d: {"n": v["n"], "scored": v["scored"], "exact": v["exact"], "confusion": dict(v["pairs"]),
                       "status": dict(v["status"])} for d, v in judg.items()},
        "overall_band": {"n": ov["n"], "exact": ov["exact"],
                         "qwk": round(EM.quadratic_weighted_kappa(ov["yt"], ov["yp"]), 2) if ov["n"] else None},
        "paths": dict(paths), "p50_latency_ms": lat[len(lat) // 2] if lat else None,
    }
    return out


def gold(prefix, run):
    pairs = []
    for l2 in LANGS:
        with open(os.path.join(REPO, "tests", "fixtures", "dt_gold_v6", f"{l2}.json"), encoding="utf-8") as fh:
            items = {it["id"]: it for it in json.load(fh) if "_v6_" not in it["id"]}
        path = os.path.join(HERE, f"{prefix}_gold_{l2}_{run}.jsonl")
        if os.path.exists(path):
            pairs += [(r, items[r["id"]], l2) for r in rows(path) if r["id"] in items]
    return summarise(pairs)


def sentence_flags(pairs):
    """Track E analyze.sentence_table: per sentence category -> [n, flagged, flagged major+]."""
    c = collections.defaultdict(lambda: [0, 0, 0])
    loc = {"para": [0, 0, 0], "verbatim": [0, 0, 0]}
    for r, it, _ in pairs:
        sp = build_sentence_pairs(it["reference"], it["reproduction"]).pairs
        by = collections.defaultdict(list)
        for e in r["errors"]:
            idx = next((i for i, p in enumerate(sp) if p.repro.start <= e["span_reproduction"][0] < p.repro.end), None)
            by[idx].append(e)
        gold_by = collections.defaultdict(list)
        for e in it["expected_errors"]:
            gold_by[e["sentence"]].append(e)
        for i, p in enumerate(sp):
            para = it["sentences_paraphrased"][i]
            ident = p.ref.text == p.repro.text
            cat = ("err_" if gold_by.get(i) else "clean_") + ("para" if para else ("identical" if ident else "verbatim_edit"))
            c[cat][0] += 1; c[cat][1] += bool(by.get(i))
            c[cat][2] += any(SEV_RANK[e["severity"]] >= 1 for e in by.get(i, []))
        al = EM.align_errors([e["span_reproduction"] for e in r["errors"]], [e["span_repro"] for e in it["expected_errors"]])
        matched = {j for _, j in al.matches}
        for j, e in enumerate(it["expected_errors"]):
            k = "para" if e["in_paraphrased_sentence"] else "verbatim"
            loc[k][0] += 1; loc[k][1] += bool(by.get(e["sentence"])); loc[k][2] += j in matched
    return ({k: {"n": v[0], "flagged": v[1], "flagged_major_plus": v[2]} for k, v in sorted(c.items())},
            {k: {"n": v[0], "sentence_flagged": v[1], "span_located": v[2]} for k, v in loc.items()})


def stress(prefix, level):
    items = {it["id"]: it for it in rows(os.path.join(HERE, "..", "..", "track_e", "stress_set.jsonl"))}
    pairs = []
    for l2 in LANGS:
        path = os.path.join(HERE, f"{prefix}_stress_{l2}_{level}.jsonl")
        if os.path.exists(path):
            pairs += [(r, items[r["id"]], l2) for r in rows(path) if r["id"] in items]
    out = summarise(pairs)
    out["sentences"], out["gold_error_location"] = sentence_flags(pairs)
    return out


def spend():
    total, calls, per = 0.0, 0, {}
    for name in sorted(os.listdir(HERE)):
        if name.endswith(".jsonl"):
            t = 0.0
            for r in rows(os.path.join(HERE, name)):
                for a in ((r["grader_trace"].get("single_call") or {}).get("attempts") or []):
                    calls += 1; t += a.get("cost_usd") or 0.0
            per[name] = round(t, 6); total += t
    return {"spend_usd": round(total, 6), "calls": calls, "by_file": per}


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "gold":
        res = {run: gold(sys.argv[2], run) for run in sys.argv[3:]}
    elif mode == "stress":
        res = stress(sys.argv[2], sys.argv[3])
    else:
        res = spend()
    print(json.dumps(res, ensure_ascii=False, indent=1))
