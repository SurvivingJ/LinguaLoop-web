# -*- coding: utf-8 -*-
"""One-shot gold evaluation of the silver-frozen configs (frozen.json). Writes results.json."""
from __future__ import annotations
import json, os, random, statistics
import common as C, lib, pipelines as P

FZ = json.load(open(os.path.join(C.HERE, "frozen.json"), encoding="utf-8"))
SET = "gold"


def mean3(items, res, ids):
    v = []
    for d in lib.DIMS:
        x = lib.qwk([items[i]["bands"][d] for i in ids], [res[i]["bands"][d] for i in ids])
        if x == x:
            v.append(x)
    return statistics.mean(v) if v else float("nan")


def paired_boot(items, ra, rb, n=2000, seed=0):
    rng = random.Random(seed)
    ids = list(items)
    diffs = []
    for _ in range(n):
        s = [rng.choice(ids) for _ in ids]
        a, b = mean3(items, ra, s), mean3(items, rb, s)
        if a == a and b == b:
            diffs.append(a - b)
    diffs.sort()
    return {"mean_diff": statistics.mean(diffs), "ci95": [diffs[int(.025 * len(diffs))], diffs[int(.975 * len(diffs)) - 1]],
            "p_a_better": sum(d > 0 for d in diffs) / len(diffs)}


def expl_stats(res):
    whys = [e.get("why") for r in res.values() for e in r["errors"]]
    have = [w for w in whys if w]
    wc = [len(w.split()) for w in have]
    return {"n_errors": len(whys), "with_explanation": len(have), "le20_words": sum(c <= 20 for c in wc),
            "mean_words": statistics.mean(wc) if wc else 0}


def slim(m):
    return m


def main():
    out = {"set": SET, "langs": {}}
    samples = {}
    for lang in lib.LANGS:
        items = lib.build(lang, SET)
        fz = FZ[lang]
        L = {}
        R = {}

        def add(key, name, **kw):
            res = P.run_pipeline(items, name, lang, SET, **kw)
            R[key] = res
            m = P.metrics(items, res, ci=True)
            m["cfg"] = kw
            m["explanations"] = expl_stats(res)
            L[key] = m
            return res

        add("jev_alone", "jev")
        add("live_grader_recorded", "live")
        add("llm_pair_alone", "llm_pair", **fz["llm_pair"]["frozen"]["cfg"])
        add("c1_frozen", "c1", **fz["c1"]["frozen"]["cfg"])
        add("c2_frozen", "c2", **fz["c2"]["frozen"]["cfg"])
        add("c2_verified_frozen", "c2", **fz["c2_verified"]["frozen"]["cfg"])
        # reference rows: unverified item-level pass of each cheap model with frozen c2 sev
        for mk in ("qwen", "deepseek"):
            add(f"c2_noverify_{mk}", "c2", model=mk, verify="none", tau_v=0.0, sev=fz["c2"]["frozen"]["cfg"]["sev"])

        # c1 gate curve (frozen model/combine/sev; only the gate moves)
        base_cfg = dict(fz["c1"]["frozen"]["cfg"])
        curve = []
        for g in ("flag",) + tuple(reversed(P.TAUS)):
            cfg = {**base_cfg, "gate": g}
            res = P.run_pipeline(items, "c1", lang, SET, **cfg)
            m = P.metrics(items, res)
            curve.append({"gate": g, "qwk": m["qwk"], "mean_qwk": m["mean_qwk"], "precision": m["detect"]["precision"],
                          "recall": m["detect"]["recall"], "minor_recall": m["detect"]["minor_recall"], "severity_exact": m["severity_exact"],
                          "pct_diff_pairs_stage2": m["pct_diff_pairs_stage2"], "pct_all_pairs_stage2": m["pct_all_pairs_stage2"],
                          "pct_items_stage2": m["pct_items_stage2"], "usd_per_item": m["usd_per_item"], "lat_p50": m["lat_p50"], "lat_p95": m["lat_p95"],
                          "is_frozen": g == base_cfg["gate"]})
        L["c1_gate_curve"] = curve
        # same curve for each model with sev=llm,combine=llm (plain "LLM adjudicates") for the model comparison
        mc = {}
        for mk in lib.MODELS:
            rows = []
            for g in ("flag",) + tuple(reversed(P.TAUS)):
                res = P.run_pipeline(items, "c1", lang, SET, model=mk, gate=g, combine="llm", sev="prior")
                m = P.metrics(items, res)
                rows.append({"gate": g, "mean_qwk": m["mean_qwk"], "qwk": m["qwk"], "recall": m["detect"]["recall"], "precision": m["detect"]["precision"],
                             "minor_recall": m["detect"]["minor_recall"], "severity_exact": m["severity_exact"],
                             "usd_per_item": m["usd_per_item"], "pct_diff_pairs_stage2": m["pct_diff_pairs_stage2"]})
            mc[mk] = rows
        L["c1_gate_curve_by_model_sevprior"] = mc

        # c2 verify threshold curve (frozen model+sev of c2_verified, claim verifier)
        vcfg = dict(fz["c2_verified"]["frozen"]["cfg"])
        rows = []
        for vf in ("claim", "pair_sig"):
            for tv in (0.0, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5):
                cfg = {**vcfg, "verify": vf if tv > 0 else "none", "tau_v": tv}
                res = P.run_pipeline(items, "c2", lang, SET, **cfg)
                m = P.metrics(items, res)
                rows.append({"verify": vf, "tau_v": tv, "mean_qwk": m["mean_qwk"], "qwk": m["qwk"], "precision": m["detect"]["precision"],
                             "recall": m["detect"]["recall"], "minor_recall": m["detect"]["minor_recall"], "severity_exact": m["severity_exact"],
                             "usd_per_item": m["usd_per_item"], "lat_p50": m["lat_p50"], "lat_p95": m["lat_p95"]})
        L["c2_verify_curve"] = rows

        # c3 escalation curves
        ids = list(items)
        c3 = {}
        for key, f in fz["c3"].items():
            base = P.run_pipeline(items, f["base"], lang, SET, **f["base_cfg"])
            kind = f["kind"]
            order = sorted(ids, key=lambda i: (-P.uncertainty(items[i], kind), i))
            curve = []
            for k in range(0, len(ids) + 1, 3):
                res = P.escalate(items, base, lang, SET, order, k)
                m = P.metrics(items, res)
                curve.append({"k": k, "rate": k / len(ids), "mean_qwk": m["mean_qwk"], "qwk": m["qwk"], "usd_per_item": m["usd_per_item"],
                              "lat_p50": m["lat_p50"], "lat_p95": m["lat_p95"]})
            # random-order expectation
            rnd = {k: [] for k in range(0, len(ids) + 1, 3)}
            rng = random.Random(1)
            for _ in range(200):
                o = ids[:]; rng.shuffle(o)
                for k in rnd:
                    rnd[k].append(P.metrics(items, P.escalate(items, base, lang, SET, o, k))["mean_qwk"])
            for row in curve:
                vals = [v for v in rnd[row["k"]] if v == v]
                row["random_mean_qwk"] = statistics.mean(vals)
            kf = sum(1 for i in ids if P.uncertainty(items[i], kind) >= float(f["theta"]))
            res = P.escalate(items, base, lang, SET, order, kf)
            m = P.metrics(items, res, ci=True)
            R[f"c3_{key}"] = res
            c3[key] = {"theta": f["theta"], "silver_rate": f["silver_rate"], "frozen_point": {"k": kf, "rate": kf / len(ids), **m}, "curve": curve}
        L["c3"] = c3

        # paired bootstrap differences in mean QWK
        pb = {}
        for a, b in (("c2_frozen", "jev_alone"), ("c2_frozen", "live_grader_recorded"), ("c1_frozen", "jev_alone"),
                     ("c2_verified_frozen", "c2_frozen"), ("llm_pair_alone", "jev_alone"), ("jev_alone", "live_grader_recorded"),
                     ("c2_verified_frozen", "jev_alone"), ("c2_verified_frozen", "live_grader_recorded")):
            pb[f"{a}__minus__{b}"] = paired_boot(items, R[a], R[b])
        L["paired_bootstrap_mean_qwk"] = pb
        out["langs"][lang] = L

        # explanation samples for manual reading
        s = []
        for key in ("c2_frozen", "c1_frozen"):
            for iid, r in R[key].items():
                for e in r["errors"]:
                    p = next((p for p in items[iid]["pairs"] if p["idx"] == e["pair_idx"]), None)
                    s.append({"pipe": key, "item": iid, "gold_forms": p["gold_forms"] if p else None, "gold_sev": p["gold_sev"] if p else None,
                              "pred": [e["subtype"], e["severity"]], "why": e.get("why")})
        samples[lang] = s

    out["spend_usd"] = C.spent()
    with open(os.path.join(C.HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(C.HERE, "explanation_samples.json"), "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=1, ensure_ascii=False)

    # console summary
    for lang in lib.LANGS:
        L = out["langs"][lang]
        print(f"== {lang}")
        for k in ("jev_alone", "live_grader_recorded", "llm_pair_alone", "c1_frozen", "c2_frozen", "c2_verified_frozen", "c2_noverify_qwen", "c2_noverify_deepseek"):
            m = L[k]; q = m["qwk"]; d = m["detect"]
            print(f"  {k:22s} acc {q['accuracy']:.3f} fid {q['fidelity']:.3f} und {q['understandability']:.3f} mean {m['mean_qwk']:.3f} | P {d['precision']:.2f} R {d['recall']:.2f} minorR {d['minor_recall']:.2f} sev {m['severity_exact']:.2f} sub {m['subtype_acc']:.2f} | s2 pairs {m['pct_diff_pairs_stage2']:.0%} | ${m['usd_per_item']:.6f} | lat {m['lat_p50']:.2f}/{m['lat_p95']:.2f}")
        print("  c1 gate curve:")
        for r in L["c1_gate_curve"]:
            print(f"     gate {str(r['gate']):5s} mean {r['mean_qwk']:.3f} R {r['recall']:.2f} minorR {r['minor_recall']:.2f} P {r['precision']:.2f} sev {r['severity_exact']:.2f} esc {r['pct_diff_pairs_stage2']:.0%} ${r['usd_per_item']:.6f} {'<- frozen' if r['is_frozen'] else ''}")
        for key, v in L["c3"].items():
            fp = v["frozen_point"]
            print(f"  c3 {key:13s} frozen rate {fp['rate']:.2f} mean {fp['mean_qwk']:.3f} ${fp['usd_per_item']:.5f} | curve " + " ".join(f"{r['rate']:.1f}:{r['mean_qwk']:.2f}({r['random_mean_qwk']:.2f})" for r in v["curve"]))
        for k, v in L["paired_bootstrap_mean_qwk"].items():
            print(f"  boot {k}: {v['mean_diff']:+.3f} [{v['ci95'][0]:+.3f},{v['ci95'][1]:+.3f}]")
    print("spend", out["spend_usd"])


if __name__ == "__main__":
    main()
