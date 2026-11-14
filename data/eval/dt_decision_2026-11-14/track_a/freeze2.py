# -*- coding: utf-8 -*-
"""Adds the secondary frozen configs + routing cutoffs (all fitted on silver only)."""
import itertools, json, statistics
import lib as L, feats as F, pipeline as P
from pooled import load
from freeze import obj_lang

NARROW = ("s_n_negation", "s_n_quantity", "s_n_agent_direction", "s_n_meaning_omitted", "s_n_meaning_added")
ROUTE = {
    "sept": lambda r: max([r["s_err"]] + [r[k] for k in NARROW]),                      # Sept routing signal
    "fused": lambda r: max([P.det_score(r, "Dv"), r["s_err"]] + [r[k] for k in NARROW]),  # + diff-focused evidence
    "D": lambda r: max(P.det_score(r, "Dv"), r["flip"]),                                # single-call variant
}
RGRID = [round(0.05 * i, 2) for i in range(1, 13)]


def item_signal(rows, meta, fn):
    s = {i: 0.0 for i in meta}
    for r in rows:
        s[r["item_id"]] = max(s[r["item_id"]], fn(r))
    return s


def fit_route(rows, meta, fn):
    sig = item_signal(rows, meta, fn)
    best = (0.0, 0)
    for t in RGRID:
        routed = [i for i, v in sig.items() if v < t]
        bad = [i for i in routed if any(meta[i]["bands"][d] < 4 for d in L.DIMS)]
        if not bad and len(routed) >= best[1]:
            best = (t, len(routed))
    return {"tau_r": best[0], "n_routed_silver": best[1], "n_silver": len(meta)}


def main():
    data = load("silver")
    fz = json.load(open("frozen_config.json"))
    main_cfg = dict(fz["frozen"]); main_cfg["tau_c"] = 0.7  # tau_c 0.6/0.7/0.8 tie exactly on silver -> take the middle
    all_ids = {l: list(data[l][1]) for l in data}
    pooled = lambda c: statistics.mean(obj_lang(data[l][0], data[l][1], all_ids[l], c) for l in data)
    GD = [{"det": d, "tau": t, "sub": "D", "crit": "D", "tau_c": tc, "sev": "prior"}
          for d, t, tc in itertools.product(("D", "Dv"), (0.3, 0.4, 0.5, 0.6), (0.6, 0.7, 0.8))]
    best_d = max(GD, key=pooled)
    cfgs = {
        "A_fused": main_cfg,
        "A_fused_prior": {**{k: v for k, v in main_cfg.items() if k != "tau_m"}, "sev": "prior"},
        "A_sept_refit": fz["sept_only_refit"],
        "A_D_only": best_d,
    }
    for k, c in cfgs.items():
        print(k, c, f"silver pooled obj {pooled(c):.4f}")
    routing = {}
    for lang in L.LANGS:
        rows, meta = data[lang]
        routing[lang] = {name: fit_route(rows, meta, fn) for name, fn in ROUTE.items()}
        print(lang, routing[lang])
    fz["configs"] = cfgs
    fz["routing"] = routing
    json.dump(fz, open("frozen_config.json", "w"), indent=1)


if __name__ == "__main__":
    main()
