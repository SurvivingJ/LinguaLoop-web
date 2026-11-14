# -*- coding: utf-8 -*-
"""Pooled-over-languages (n=90) gold comparison of the frozen per-language configs + paired bootstrap."""
import json, os, random, statistics
import common as C, lib, pipelines as P
FZ = json.load(open(os.path.join(C.HERE, "frozen.json")))
pipes = {"jev_alone": lambda fz: ("jev", {}), "live_grader_recorded": lambda fz: ("live", {}),
         "llm_pair_alone": lambda fz: ("llm_pair", fz["llm_pair"]["frozen"]["cfg"]), "c1_frozen": lambda fz: ("c1", fz["c1"]["frozen"]["cfg"]),
         "c2_frozen": lambda fz: ("c2", fz["c2"]["frozen"]["cfg"]), "c2_verified_frozen": lambda fz: ("c2", fz["c2_verified"]["frozen"]["cfg"]),
         "posthoc_c2_deepseek_noverify_prior": lambda fz: ("c2", dict(model="deepseek", verify="none", tau_v=0, sev="prior")),
         "posthoc_llm_pair_haiku_prior": lambda fz: ("llm_pair", dict(model="haiku", sev="prior"))}
gold, pred = {}, {k: {} for k in pipes}
usd = {k: [] for k in pipes}
for lang in lib.LANGS:
    items = lib.build(lang, "gold")
    for iid, it in items.items():
        gold[iid] = it["bands"]
    for k, f in pipes.items():
        name, kw = f(FZ[lang])
        res = P.run_pipeline(items, name, lang, "gold", **kw)
        for iid, r in res.items():
            pred[k][iid] = r["bands"]; usd[k].append(r["usd"])
ids = list(gold)
def m3(k, s):
    return statistics.mean(lib.qwk([gold[i][d] for i in s], [pred[k][i][d] for i in s]) for d in lib.DIMS)
out = {}
rng = random.Random(0)
samples = [[rng.choice(ids) for _ in ids] for _ in range(2000)]
for k in pipes:
    bs = sorted(m3(k, s) for s in samples)
    diff = sorted(m3(k, s) - m3("jev_alone", s) for s in samples)
    dl = sorted(m3(k, s) - m3("live_grader_recorded", s) for s in samples)
    out[k] = {"qwk": {d: lib.qwk([gold[i][d] for i in ids], [pred[k][i][d] for i in ids]) for d in lib.DIMS}, "mean_qwk": m3(k, ids),
              "ci95": [bs[50], bs[1949]], "diff_vs_jev": [statistics.mean(diff), diff[50], diff[1949]],
              "diff_vs_live": [statistics.mean(dl), dl[50], dl[1949]], "usd_per_item": statistics.mean(usd[k])}
    o = out[k]
    print(f"{k:36s} acc {o['qwk']['accuracy']:.3f} fid {o['qwk']['fidelity']:.3f} und {o['qwk']['understandability']:.3f} mean {o['mean_qwk']:.3f} [{o['ci95'][0]:.2f},{o['ci95'][1]:.2f}] vs jev {o['diff_vs_jev'][0]:+.3f} [{o['diff_vs_jev'][1]:+.2f},{o['diff_vs_jev'][2]:+.2f}] vs live {o['diff_vs_live'][0]:+.3f} [{o['diff_vs_live'][1]:+.2f},{o['diff_vs_live'][2]:+.2f}] ${o['usd_per_item']:.6f}")
json.dump(out, open(os.path.join(C.HERE, "pooled.json"), "w"), indent=1)
