# -*- coding: utf-8 -*-
"""Silver-only tuning. Selection rule (fixed before any gold stage-2 call was made):
per language and per architecture, compute the 5-fold CV mean of the 3-dimension QWK mean for every grid
config; among configs within 0.02 of the best CV mean pick the cheapest blended $/item (ties: higher CV mean).
Writes frozen.json. Gold is never read here."""
from __future__ import annotations
import itertools, json, os, random, statistics
import common as C, lib, pipelines as P

OUT = {}


def pick(cands):
    best = max(c["cv_mean"] for c in cands)
    pool = [c for c in cands if c["cv_mean"] >= best - 0.02]
    pool.sort(key=lambda c: (round(c["usd_per_item"], 7), -c["cv_mean"]))
    return pool[0], best


def main():
    for lang in lib.LANGS:
        items = lib.build(lang, "silver")
        out = {}

        def ev(name, **kw):
            res = P.run_pipeline(items, name, lang, "silver", **kw)
            m = P.metrics(items, res)
            cvm, cvs = P.cv_mean(items, res)
            return {"cfg": kw, "cv_mean": cvm, "cv_sd": cvs, "mean_qwk": m["mean_qwk"], "qwk": m["qwk"], "usd_per_item": m["usd_per_item"],
                    "recall": m["detect"]["recall"], "precision": m["detect"]["precision"], "sev": m["severity_exact"],
                    "pct_diff_pairs_stage2": m["pct_diff_pairs_stage2"]}

        out["ref_jev"] = ev("jev")
        out["ref_live"] = ev("live")
        # LLM-only baseline (no jev): model x sev
        c = [ev("llm_pair", model=mk, sev=sv) for mk in lib.MODELS for sv in ("llm", "prior")]
        out["llm_pair"] = {"frozen": pick(c)[0], "grid": c}
        # cascade 1
        c = [ev("c1", model=mk, gate=g, combine=cb, sev=sv)
             for mk in lib.MODELS for g in P.TAUS + ("flag",) for cb in ("llm", "union") for sv in ("llm", "prior", "jev")]
        fz, best = pick(c)
        out["c1"] = {"frozen": fz, "best_cv": best, "n_grid": len(c), "top5": sorted(c, key=lambda x: -x["cv_mean"])[:5]}
        # cascade 2
        c = [ev("c2", model=mk, verify="none", tau_v=0.0, sev=sv) for mk in ("qwen", "deepseek") for sv in ("llm", "prior")]
        c += [ev("c2", model=mk, verify=vf, tau_v=tv, sev=sv) for mk in ("qwen", "deepseek") for vf in ("pair_sig", "claim")
              for tv in (0.03, 0.05, 0.1, 0.2, 0.3, 0.5) for sv in ("llm", "prior", "jev")]
        fz, best = pick(c)
        out["c2"] = {"frozen": fz, "best_cv": best, "n_grid": len(c), "top5": sorted(c, key=lambda x: -x["cv_mean"])[:5]}
        # best c2 that actually uses a jev verifier (so the verifier's contribution is always reported)
        cv = [x for x in c if x["cfg"]["verify"] != "none"]
        out["c2_verified"] = {"frozen": pick(cv)[0]}
        # cascade 3: escalation to recorded live grader. base = frozen jev alone and frozen c1.
        c3 = {}
        ids = list(items)
        for base_name, base_kw in (("jev", {}), ("c1", out["c1"]["frozen"]["cfg"])):
            base = P.run_pipeline(items, base_name, lang, "silver", **base_kw)
            for kind in ("margin", "sig", "disagree"):
                order = sorted(ids, key=lambda i: (-P.uncertainty(items[i], kind), i))
                curve = []
                for k in range(0, len(ids) + 1):
                    res = P.escalate(items, base, lang, "silver", order, k)
                    cvm, _ = P.cv_mean(items, res)
                    m = P.metrics(items, res)
                    thr = P.uncertainty(items[order[k - 1]], kind) if k else None
                    curve.append({"k": k, "rate": k / len(ids), "cv_mean": cvm, "mean_qwk": m["mean_qwk"], "usd_per_item": m["usd_per_item"], "thr": thr})
                # only cut at score boundaries (a threshold must be expressible on the score)
                valid = [x for x in curve if x["k"] == 0 or x["k"] == len(ids)
                         or P.uncertainty(items[order[x["k"] - 1]], kind) > P.uncertainty(items[order[x["k"]]], kind)]
                fz, best = pick(valid)
                # threshold = midpoint between last escalated and first non-escalated score
                k = fz["k"]
                if k == 0:
                    theta = float("inf")
                elif k == len(ids):
                    theta = -1.0
                else:
                    theta = (P.uncertainty(items[order[k - 1]], kind) + P.uncertainty(items[order[k]], kind)) / 2
                c3[f"{base_name}|{kind}"] = {"base": base_name, "base_cfg": base_kw, "kind": kind, "theta": theta, "silver_rate": fz["rate"],
                                           "silver_cv": fz["cv_mean"], "silver_best_cv": best, "silver_curve": [(round(x["rate"], 3), round(x["mean_qwk"], 3)) for x in curve]}
        out["c3"] = c3
        OUT[lang] = out
        print(f"== {lang}")
        print("  jev   cv %.3f  $%.6f" % (out["ref_jev"]["cv_mean"], out["ref_jev"]["usd_per_item"]))
        print("  live  cv %.3f  $%.6f" % (out["ref_live"]["cv_mean"], out["ref_live"]["usd_per_item"]))
        for a in ("llm_pair", "c1", "c2", "c2_verified"):
            f = out[a]["frozen"]
            print(f"  {a:11s} cv {f['cv_mean']:.3f} (best {out[a].get('best_cv', float('nan')):.3f}) ${f['usd_per_item']:.6f} R {f['recall']:.2f} P {f['precision']:.2f} sev {f['sev']:.2f} {f['cfg']}")
        for k, v in c3.items():
            print(f"  c3 {k:14s} theta {v['theta']:.3f} silver_rate {v['silver_rate']:.2f} cv {v['silver_cv']:.3f}")
    with open(os.path.join(C.HERE, "frozen.json"), "w", encoding="utf-8") as f:
        json.dump(OUT, f, indent=1, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
