# -*- coding: utf-8 -*-
"""POST-HOC diagnostics (run after gold was seen; NOT frozen configs; descriptive only)."""
import json, os, statistics
import common as C, lib, pipelines as P
out = {}
rows = []
for st in ("silver", "gold"):
    for lang in lib.LANGS:
        items = lib.build(lang, st)
        for name, kw in (("jev", {}), ("live", {}),
                         ("c2", dict(model="qwen", verify="none", tau_v=0, sev="prior")), ("c2", dict(model="qwen", verify="none", tau_v=0, sev="llm")),
                         ("c2", dict(model="deepseek", verify="none", tau_v=0, sev="prior")), ("c2", dict(model="deepseek", verify="none", tau_v=0, sev="llm")),
                         ("c2", dict(model="deepseek", verify="claim", tau_v=0.3, sev="prior")),
                         ("llm_pair", dict(model="qwen", sev="prior")), ("llm_pair", dict(model="deepseek", sev="prior")), ("llm_pair", dict(model="haiku", sev="prior")),
                         ("llm_pair", dict(model="qwen", sev="llm")), ("llm_pair", dict(model="deepseek", sev="llm")), ("llm_pair", dict(model="haiku", sev="llm")),
                         ("c1", dict(model="deepseek", gate="flag", combine="llm", sev="prior")), ("c1", dict(model="deepseek", gate=0.1, combine="llm", sev="prior"))):
            res = P.run_pipeline(items, name, lang, st, **kw)
            m = P.metrics(items, res)
            key = name + ":" + ",".join(f"{v}" for v in kw.values())
            rows.append((key, st, lang, m))
            out.setdefault(key, {}).setdefault(st, {})[lang] = {"mean_qwk": m["mean_qwk"], "qwk": m["qwk"], "P": m["detect"]["precision"], "R": m["detect"]["recall"],
                                                               "minor_recall": m["detect"]["minor_recall"], "sev": m["severity_exact"], "sub": m["subtype_acc"], "usd": m["usd_per_item"],
                                                               "lat_p50": m["lat_p50"], "lat_p95": m["lat_p95"], "pct_all_pairs_stage2": m["pct_all_pairs_stage2"], "pct_items_stage2": m["pct_items_stage2"]}
print(f"{'config':44s} " + " ".join(f"{s[:1]}-{l}" for s in ("silver", "gold") for l in lib.LANGS) + "  gold-mean  silver-mean")
for key, d in out.items():
    v = [d[s][l]["mean_qwk"] for s in ("silver", "gold") for l in lib.LANGS]
    print(f"{key:44s} " + " ".join(f"{x:.2f}" for x in v) + f"   {statistics.mean(v[3:]):.3f}   {statistics.mean(v[:3]):.3f}")
json.dump(out, open(os.path.join(C.HERE, "posthoc.json"), "w"), indent=1)
# en failure analysis: qwen item-level vs gold, items where bands differ
for lang, mk in (("en", "qwen"), ("en", "deepseek")):
    items = lib.build(lang, "gold")
    res = P.run_pipeline(items, "c2", lang, "gold", model=mk, verify="none", tau_v=0, sev="prior")
    print("--", lang, mk)
    for iid, it in items.items():
        if res[iid]["bands"] != it["bands"]:
            print("  ", iid, "gold", it["bands"], "pred", res[iid]["bands"], "| gold errs", [(p["gold_sub"], p["gold_sev"], p["gold_forms"]) for p in it["pairs"] if p["gold_has"]],
                  "| pred", [(e["subtype"], e["severity"]) for e in res[iid]["errors"]])
# stage-2 share of ALL pairs, and identical-pair share
for st in ("gold",):
    for lang in lib.LANGS:
        items = lib.build(lang, st)
        na = sum(it["n_pairs_total"] for it in items.values()); nd = sum(len(it["pairs"]) for it in items.values())
        print(lang, "all pairs", na, "non-identical", nd, f"{nd/na:.0%}", "items with >=1 diff pair", sum(bool(it["pairs"]) for it in items.values()))
