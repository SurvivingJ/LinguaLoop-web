# -*- coding: utf-8 -*-
"""Decision pipeline over feature rows + metrics. Pure python, no API calls."""
from __future__ import annotations

import random
import statistics

import lib as L
import reqs as RQ

PRIOR = L.T.SUBTYPE_DEFAULT_SEVERITY
SEV_ORDER = L.SEV_ORDER


def top_subtype(row: dict, lang: str, src: str) -> str:
    cands = L.T.SUBTYPES[lang]
    if src == "D":
        p = row["_subprobs"]
    elif src == "S":
        p = row["s__subprobs"]
    else:  # ens: sum of the listed sources ("ens" = D + Sept; "ens:a,b" = explicit prefixes)
        p = {}
        keys = ("_subprobs", "s__subprobs") if src == "ens" else tuple(x + "_subprobs" for x in src[4:].split(","))
        for k in keys:
            for s, v in (row.get(k) or {}).items():
                p[s] = p.get(s, 0) + v
    return max(cands, key=lambda s: p.get(s, 0.0))


def det_score(row: dict, mode: str) -> float:
    e = row.get("err", 0.0)
    if mode.startswith("mean:"):
        ks = mode[5:].split(",")
        return sum(row[k] for k in ks) / len(ks)
    if mode.startswith("max:"):
        return max(row[k] for k in mode[4:].split(","))
    if mode == "D":
        return e
    if mode == "S":
        return row["s_err"]
    if mode == "Dv":  # arm D, discounted when "only a script/synonym variant" fires
        return e * (1 - row.get("variant_ok", 0.0)) ** 0.5
    if mode == "Dtf":  # paraphrase self-consistency: mean of two phrasings
        return (e + row.get("teacher_fix", e)) / 2
    if mode == "Dl2":  # question-language ensemble
        return (e + row.get("n_err", e)) / 2
    if mode == "maxDS":
        return max(e, row["s_err"])
    if mode == "maxDvS":
        return max(e * (1 - row.get("variant_ok", 0.0)) ** 0.5, row["s_err"])
    if mode == "meanDS":
        return (e + row["s_err"]) / 2
    if mode == "Dall":  # 3-way paraphrase mean within arm D
        return (e + row.get("teacher_fix", e) + (1 - row["sev_none"])) / 3
    raise ValueError(mode)


def crit_score(row: dict, mode: str) -> float:
    if mode == "D":
        return (row["flip"] + row["sev_critical"]) / 2
    if mode == "S":
        return (row["s_mc"] + row["s_sev_critical"]) / 2
    return (row["flip"] + row["sev_critical"] + row["s_mc"] + row["s_sev_critical"]) / 4


def decide(row: dict, cfg: dict) -> dict | None:
    lang = row["lang"]
    if det_score(row, cfg["det"]) < cfg["tau"]:
        return None
    sub = top_subtype(row, lang, cfg["sub"])
    if crit_score(row, cfg["crit"]) >= cfg["tau_c"]:
        sev = "critical"
    else:
        m = cfg["sev"]
        if m == "prior":
            sev = PRIOR.get(sub, "minor")
        elif m == "argmaxD":
            sev = "major" if row["sev_major"] + row["sev_critical"] > row["sev_minor"] else "minor"
        elif m == "argmaxS":
            sev = "major" if row["s_sev_major"] + row["s_sev_critical"] > row["s_sev_minor"] else "minor"
        elif m == "impair":
            sev = "major" if row.get("impair", 0) >= cfg.get("tau_m", 0.5) else "minor"
        elif m == "prior+impair":  # prior, but a confident impair vote can flip it
            base = PRIOR.get(sub, "minor")
            im = row.get("impair", 0.5)
            sev = "major" if (base == "major" and im >= 0.25) or im >= 0.85 else "minor"
        elif m == "minor":
            sev = "minor"
        else:
            raise ValueError(m)
    return {"subtype": sub, "severity": sev}


def predict_items(rows: list[dict], item_ids: list[str], cfg: dict) -> dict[str, dict]:
    by = {i: [] for i in item_ids}
    for r in rows:
        if r["item_id"] in by:
            e = decide(r, cfg)
            if e:
                by[r["item_id"]].append(e)
    return {i: L.bands_from_errors(errs) for i, errs in by.items()}


def band_qwk(rows, meta, item_ids, cfg) -> dict:
    pred = predict_items(rows, item_ids, cfg)
    out = {}
    for d in L.DIMS:
        yt = [meta[i]["bands"][d] for i in item_ids]
        yp = [pred[i][d] for i in item_ids]
        out[d] = L.qwk(yt, yp)
    vals = [v for v in out.values() if v == v]
    out["mean"] = statistics.mean(vals) if vals else float("nan")
    out["exact"] = statistics.mean(
        1.0 if all(pred[i][d] == meta[i]["bands"][d] for d in L.DIMS) else 0.0 for i in item_ids)
    return out


def unit_metrics(rows, cfg) -> dict:
    tp = fp = fn = tn = 0
    t1 = n1 = sv = nsv = 0
    miss_minor = miss = 0
    for r in rows:
        e = decide(r, cfg)
        g = r["gold_has"]
        if g and e:
            tp += 1
            n1 += 1
            t1 += e["subtype"] == r["gold_subtype"]
            if r["gold_sev"]:
                nsv += 1
                sv += e["severity"] == r["gold_sev"]
        elif g:
            fn += 1
            miss += 1
            miss_minor += r["gold_sev"] == "minor"
        elif e:
            fp += 1
        else:
            tn += 1
    P = tp / (tp + fp) if tp + fp else float("nan")
    R = tp / (tp + fn) if tp + fn else float("nan")
    return {"precision": P, "recall": R, "f1": 2 * P * R / (P + R) if P and R and P == P else 0.0,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "subtype_top1": t1 / n1 if n1 else float("nan"), "severity_acc": sv / nsv if nsv else float("nan"),
            "missed_minor": miss_minor, "missed": miss,
            "auc": L.auc([r["gold_has"] for r in rows], [det_score(r, cfg["det"]) for r in rows])}


def folds(item_ids, k=5, seed=0):
    ids = sorted(item_ids)
    random.Random(seed).shuffle(ids)
    return [ids[i::k] for i in range(k)]


def cv_select(rows, meta, grid: list[dict], k=5, seeds=(0, 1, 2), objective="mean") -> dict:
    """Nested-free model selection + honest out-of-fold estimate.
    For each fold: pick the config maximising the objective on the other k-1
    folds, predict the held-out fold. Returns OOF QWK (pooled over held-out
    predictions, averaged over seeds) and the config chosen on ALL items."""
    item_ids = list(meta.keys())

    def obj(ids, cfg):
        q = band_qwk(rows, meta, ids, cfg)
        return q["mean"] + 0.25 * q["exact"]  # exact-match as tie-breaker/regulariser

    oof_runs = []
    for seed in seeds:
        fs = folds(item_ids, k, seed)
        pred = {}
        for i, held in enumerate(fs):
            train = [x for j, f in enumerate(fs) if j != i for x in f]
            best = max(grid, key=lambda c: obj(train, c))
            pred.update(predict_items(rows, held, best))
        q = {}
        for d in L.DIMS:
            q[d] = L.qwk([meta[i]["bands"][d] for i in item_ids], [pred[i][d] for i in item_ids])
        q["mean"] = statistics.mean(q[d] for d in L.DIMS)
        oof_runs.append(q)
    oof = {d: statistics.mean(r[d] for r in oof_runs) for d in (*L.DIMS, "mean")}
    scored = sorted(((obj(item_ids, c), i) for i, c in enumerate(grid)), reverse=True)
    best_full = grid[scored[0][1]]
    return {"oof": oof, "best": best_full, "best_obj": scored[0][0],
            "n_tied": sum(1 for s, _ in scored if abs(s - scored[0][0]) < 1e-9)}
