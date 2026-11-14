# -*- coding: utf-8 -*-
"""Pooled (one config for all three languages) silver CV + per-language report."""
import itertools, json, statistics, sys
import lib as L, feats as F, pipeline as P
from search import SRC

def load(set_name="silver"):
    data = {}
    for lang in L.LANGS:
        src = {k: v for k, v in SRC.items() if k in ("", "d2")}
        rows = F.table(lang, set_name, src)
        assert all(r["complete"] for r in rows)
        data[lang] = (rows, L.item_meta(lang, set_name))
    return data

def report(data, cfg, label="", show=False):
    line = []
    res = {}
    for lang, (rows, meta) in data.items():
        c = cfg[lang] if lang in cfg else cfg
        q = P.band_qwk(rows, meta, list(meta), c); um = P.unit_metrics(rows, c)
        res[lang] = {"qwk": q, "unit": um}
        line.append(f"{lang} {q['accuracy']:.2f}/{q['fidelity']:.2f}/{q['understandability']:.2f} ex{q['exact']:.2f} P{um['precision']:.2f} R{um['recall']:.2f} sub{um['subtype_top1']:.2f} sev{um['severity_acc']:.2f}")
        if show:
            pred = P.predict_items(rows, list(meta), c)
            for i in meta:
                if any(pred[i][d] != meta[i]["bands"][d] for d in L.DIMS):
                    print("   MISS", i, "gold", [meta[i]["bands"][d] for d in L.DIMS], "pred", [pred[i][d] for d in L.DIMS],
                          [(r["gold_subtype"], r["gold_sev"], P.decide(r, c), round(P.det_score(r, c["det"]), 2)) for r in rows if r["item_id"] == i])
    m = statistics.mean(res[l]["qwk"]["mean"] for l in res)
    print(f"{label:46s} mean {m:.3f} | " + " | ".join(line))
    return res

if __name__ == "__main__":
    data = load()
    base = {"sub": "ens", "crit": "DS", "tau_c": 0.7, "sev": "prior"}
    for det in ("S", "D", "Dv", "maxDS", "maxDvS", "meanDS"):
        for tau in (0.2, 0.3, 0.4, 0.5, 0.6):
            report(data, {**base, "det": det, "tau": tau}, f"{det} tau={tau}")
    print()
    for sub in ("S", "D", "ens"):
        for crit in ("S", "D", "DS"):
            for tc in (0.5, 0.7, 0.85):
                report(data, {"det": "maxDvS", "tau": 0.5, "sub": sub, "crit": crit, "tau_c": tc, "sev": "prior"}, f"maxDvS .5 sub={sub} crit={crit} tc={tc}")
    print()
    report(data, {**base, "det": "maxDvS", "tau": 0.5}, "DETAIL maxDvS .5", show=True)
