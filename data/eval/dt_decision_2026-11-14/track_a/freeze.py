# -*- coding: utf-8 -*-
"""Pooled silver CV model selection -> frozen_config.json. Never reads gold."""
import itertools, json, statistics, random
import lib as L, pipeline as P
from pooled import load

def obj_lang(rows, meta, ids, cfg):
    q = P.band_qwk(rows, meta, ids, cfg)
    um = P.unit_metrics([r for r in rows if r["item_id"] in set(ids)], cfg)
    return q["mean"] + 0.25 * q["exact"] + 0.10 * um["f1"]

def grid():
    g = []
    for det, tau, sub, tc, sev in itertools.product(("S", "Dv", "maxDvS", "meanDS"), (0.3, 0.4, 0.5), ("S", "ens", "ensF"),
                                                     (0.6, 0.7, 0.8), ("prior", "graded.5", "graded.6", "graded.7")):
        c = {"det": det, "tau": tau, "sub": sub, "crit": "DS" if det != "S" else "S", "tau_c": tc, "sev": sev.split(".")[0]}
        if sev.startswith("graded"):
            if det == "S":
                continue
            c["tau_m"] = float("0." + sev.split(".")[1])
        if det == "S" and sub != "S":
            continue
        g.append(c)
    return g

def main():
    data = load("silver")
    G = grid()
    print("grid size", len(G))
    def pooled(ids_by_lang, cfg):
        return statistics.mean(obj_lang(data[l][0], data[l][1], ids_by_lang[l], cfg) for l in data)
    all_ids = {l: list(data[l][1]) for l in data}
    # honest OOF estimate of the *selection procedure*
    oofs = []
    for seed in (0, 1, 2):
        fs = {l: P.folds(all_ids[l], 5, seed) for l in data}
        pred = {l: {} for l in data}
        for i in range(5):
            train = {l: [x for j, f in enumerate(fs[l]) if j != i for x in f] for l in data}
            best = max(G, key=lambda c: pooled(train, c))
            for l in data:
                pred[l].update(P.predict_items(data[l][0], fs[l][i], best))
        q = {l: {d: L.qwk([data[l][1][i]["bands"][d] for i in all_ids[l]], [pred[l][i][d] for i in all_ids[l]]) for d in L.DIMS} for l in data}
        oofs.append(q)
    oof = {l: {d: statistics.mean(o[l][d] for o in oofs) for d in L.DIMS} for l in data}
    scored = sorted(G, key=lambda c: -pooled(all_ids, c))
    print("top 8 on full silver:")
    for c in scored[:8]:
        print(f"  {pooled(all_ids, c):.4f}", c)
    best = scored[0]
    # Sept-only refit comparator under the same procedure
    GS = [c for c in G if c["det"] == "S"]
    bestS = max(GS, key=lambda c: pooled(all_ids, c))
    print("best Sept-features-only:", bestS, f"{pooled(all_ids, bestS):.4f}")
    print("OOF QWK of selection procedure:", json.dumps(oof, indent=0))
    json.dump({"frozen": best, "sept_only_refit": bestS, "silver_oof_qwk": oof, "objective": "mean QWK + 0.25*exact + 0.10*unit F1, pooled over zh/ja/en silver",
               "top8": scored[:8], "model": "typesafe/jev-1.13", "calls_per_unit": ["Sept A3 request (full-passage, L2 questions)", "arm D (diff-focused, EN questions) + D2 variant_ok"]},
              open("frozen_config.json", "w"), indent=1)

if __name__ == "__main__":
    main()
