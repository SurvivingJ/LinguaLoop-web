# -*- coding: utf-8 -*-
"""Pure offline pipeline simulators + metrics. No API calls."""
from __future__ import annotations
import json, os, random, statistics
import common as C, lib

T, A, S = lib.T, lib.A, lib.S
DIMS, SEV = lib.DIMS, lib.SEV
INV = {0: "minor", 1: "major", 2: "critical"}
TAUS = (0.0, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5)


def _sev(err_sev, subtype, mode):
    if mode == "prior":
        return "critical" if err_sev == "critical" else T.SUBTYPE_DEFAULT_SEVERITY.get(subtype, "minor")
    return err_sev


def _verify(lang, set_name):
    fn = os.path.join(C.HERE, "verify", f"{lang}_{set_name}.jsonl")
    out = {}
    if os.path.exists(fn):
        with open(fn, encoding="utf-8") as f:
            for l in f:
                r = json.loads(l)
                out[(r["item_id"], r["model"], r["claim_idx"])] = r
    return out


_VCACHE = {}


def verify_table(lang, set_name):
    k = (lang, set_name)
    if k not in _VCACHE:
        _VCACHE[k] = _verify(lang, set_name)
    return _VCACHE[k]


def _result(errors, usd, lat_stages, esc_pairs=0, llm_calls=0, escalated=False):
    return {"errors": errors, "usd": usd, "lat": sum(lat_stages), "esc_pairs": esc_pairs, "llm_calls": llm_calls,
            "escalated": escalated, "bands": lib.bands_from_errors([{"subtype": e["subtype"], "severity": e["severity"]} for e in errors])}


def _jev_cost(it):
    return sum(p["jev_usd"] or 0.0 for p in it["pairs"]), max([p["jev_lat"] or 0.0 for p in it["pairs"]] or [0.0])


def p_jev(it, **_):
    errs = [{**p["jev_err"], "pair_idx": p["idx"], "src": "jev"} for p in it["pairs"] if p["jev_err"]]
    usd, lat = _jev_cost(it)
    return _result(errs, usd, [lat])


def p_live(it, lang=None, set_name="gold", **_):
    lv = it["live"]
    r = {"errors": [{**e, "src": "live"} for e in lv["errors"]], "usd": lib.LIVE_COST_PER_ITEM[set_name][lang],
         "lat": lib.LIVE_LATENCY_S[lang], "esc_pairs": len(it["pairs"]), "llm_calls": 2, "escalated": True, "bands": dict(lv["bands"])}
    return r


def p_llm_pair(it, model="qwen", sev="llm", **_):
    """cheap LLM alone on every non-identical pair (no jev)."""
    errs, usd, lats = [], 0.0, [0.0]
    for p in it["pairs"]:
        L = p["llm"][model]
        usd += L["usd"]; lats.append(L["lat"])
        errs += [{"subtype": e["subtype"], "severity": _sev(e["severity"], e["subtype"], sev), "pair_idx": p["idx"], "why": e["why"], "src": "llm"} for e in L["errors"]]
    return _result(errs, usd, [max(lats)], len(it["pairs"]), len(it["pairs"]), bool(it["pairs"]))


def p_c1(it, model="qwen", gate=0.1, combine="llm", sev="llm", **_):
    """Cascade 1: jev on every non-identical pair; pairs with signal >= gate (or frozen-jev-flagged if gate=='flag')
    go to the cheap LLM, which confirms / types / grades severity / explains. Others are clean."""
    jusd, jlat = _jev_cost(it)
    errs, usd, lats, n = [], jusd, [0.0], 0
    for p in it["pairs"]:
        esc = (p["jev_err"] is not None) if gate == "flag" else (p["sig"] >= gate)
        if not esc:
            continue
        n += 1
        L = p["llm"][model]
        usd += L["usd"]; lats.append(L["lat"])
        le = [{"subtype": e["subtype"], "severity": _sev(e["severity"], e["subtype"], sev), "pair_idx": p["idx"], "why": e["why"], "src": "llm"} for e in L["errors"]]
        if sev == "jev" and le and p["jev_err"]:
            top = max(range(len(le)), key=lambda i: SEV[le[i]["severity"]])
            le[top]["severity"] = p["jev_err"]["severity"]
        if not le and combine == "union" and p["jev_err"]:
            le = [{**p["jev_err"], "pair_idx": p["idx"], "why": None, "src": "jev"}]
        errs += le
    return _result(errs, usd, [jlat, max(lats)], n, n, n > 0)


def p_c2(it, model="qwen", verify="claim", tau_v=0.5, sev="llm", lang=None, set_name=None, **_):
    """Cascade 2 (inverse): cheap LLM item-level recall pass; jev verifies each claim.
    verify: 'none' | 'pair_sig' (September per-pair jev signal on the claimed pair) | 'claim' (claim-specific jev yes/no)."""
    if not it["pairs"]:
        return _result([], 0.0, [0.0])
    d = it["item_llm"][model]
    usd, lats = d["usd"], [0.0]
    pmap = {p["idx"]: p for p in it["pairs"]}
    vt = verify_table(lang, set_name)
    errs, jev_pairs = [], set()
    for ci, c in enumerate(d["claims"]):
        p = pmap.get(c["pair_idx"])
        if p is None:
            continue  # claim located in a byte-identical sentence: deterministic drop
        s = c["severity"]
        if verify == "pair_sig":
            if p["idx"] not in jev_pairs:
                jev_pairs.add(p["idx"]); usd += p["jev_usd"] or 0.0; lats.append(p["jev_lat"] or 0.0)
            if p["sig"] < tau_v:
                continue
            if sev == "jev" and p["jev_err"]:
                s = p["jev_err"]["severity"]
        elif verify == "claim":
            v = vt[(it["id"], model, ci)]
            usd += v["usd"]; lats.append(v["latency_s"])
            if (v["valid_p"] or 0.0) < tau_v:
                continue
            if sev == "jev":
                pr = v["sev_probs"] or {}
                s = max(("minor", "major", "critical"), key=lambda k: pr.get(k, 0.0) or 0.0)
        if sev == "prior":
            s = _sev(s, c["subtype"], "prior")
        errs.append({"subtype": c["subtype"], "severity": s, "pair_idx": p["idx"], "why": c["why"], "src": "llm"})
    return _result(errs, usd, [d["lat"], max(lats)], len({e["pair_idx"] for e in errs}), 1, True)


BASES = {"jev": p_jev, "llm_pair": p_llm_pair, "c1": p_c1, "c2": p_c2, "live": p_live}


def run_pipeline(items, name, lang, set_name, **kw):
    return {iid: BASES[name](it, lang=lang, set_name=set_name, **kw) for iid, it in items.items()}


# ---- cascade 3: item-level uncertainty escalation to the (recorded) live grader ----

def uncertainty(it, kind, cheap="qwen"):
    ps = it["pairs"]
    if not ps:
        return 0.0
    margin = max(1 - 2 * abs(p["he_p"] - 0.5) for p in ps)
    if kind == "margin":
        return margin
    if kind == "sig":
        return max(p["sig"] for p in ps)
    if kind == "disagree":
        dis = 0
        for p in ps:
            le = p["llm"][cheap]["errors"]
            j = p["jev_err"]
            if bool(le) != bool(j):
                dis = max(dis, 2)
            elif le and j and max(SEV[e["severity"]] for e in le) != SEV[j["severity"]]:
                dis = max(dis, 1)
        return dis + margin / 10
    raise ValueError(kind)


def escalate(items, base_res, lang, set_name, order_ids, k):
    """Take base pipeline results, replace the first k items of order_ids with the live grader."""
    out = dict(base_res)
    for iid in order_ids[:k]:
        lv = p_live(items[iid], lang=lang, set_name=set_name)
        b = base_res[iid]
        out[iid] = {**lv, "usd": b["usd"] + lv["usd"], "lat": b["lat"] + lv["lat"]}
    return out


# ---- metrics ----

def metrics(items, res, ci=False):
    ids = list(items)
    m = {"n": len(ids)}
    q = {}
    for d in DIMS:
        yt = [items[i]["bands"][d] for i in ids]; yp = [res[i]["bands"][d] for i in ids]
        q[d] = lib.qwk(yt, yp)
        if ci:
            m.setdefault("qwk_ci95", {})[d] = S.bootstrap_qwk_ci(yt, yp)
    m["qwk"] = q
    v = [x for x in q.values() if x == x]
    m["mean_qwk"] = statistics.mean(v) if v else float("nan")
    m["exact_band"] = statistics.mean(1.0 if res[i]["bands"][d] == items[i]["bands"][d] else 0.0 for i in ids for d in DIMS)
    tp = fp = fn = 0
    sev_ok = sev_w1 = sev_n = sub_ok = 0
    minor_n = minor_hit = 0
    gold_err_n = cnt_hit = 0
    for i in ids:
        it = items[i]
        pred = {}
        for e in res[i]["errors"]:
            pred.setdefault(e["pair_idx"], []).append(e)
        diff = {p["idx"]: p for p in it["pairs"]}
        for idx, es in pred.items():
            if idx not in diff or not diff[idx]["gold_has"]:
                fp += 1
        for idx, p in diff.items():
            if not p["gold_has"]:
                continue
            gold_err_n += p["gold_n"]
            es = pred.get(idx)
            if p["gold_sev"] == "minor":
                minor_n += 1; minor_hit += bool(es)
            if not es:
                fn += 1
                continue
            tp += 1
            cnt_hit += min(len(es), p["gold_n"])
            if p["gold_sev"]:
                ps = max(SEV[e["severity"]] for e in es)
                sev_n += 1; sev_ok += ps == SEV[p["gold_sev"]]; sev_w1 += abs(ps - SEV[p["gold_sev"]]) <= 1
            sub_ok += any(e["subtype"] == p["gold_sub"] for e in es)
    P = tp / (tp + fp) if tp + fp else 1.0
    Rc = tp / (tp + fn) if tp + fn else 1.0
    m["detect"] = {"precision": P, "recall": Rc, "f1": 2 * P * Rc / (P + Rc) if P + Rc else 0.0, "tp": tp, "fp": fp, "fn": fn,
                   "minor_recall": minor_hit / minor_n if minor_n else float("nan"), "minor_n": minor_n,
                   "error_count_recall": cnt_hit / gold_err_n if gold_err_n else float("nan")}
    m["severity_exact"] = sev_ok / sev_n if sev_n else float("nan")
    m["severity_within1"] = sev_w1 / sev_n if sev_n else float("nan")
    m["subtype_acc"] = sub_ok / tp if tp else float("nan")
    npairs = sum(len(items[i]["pairs"]) for i in ids)
    nall = sum(items[i]["n_pairs_total"] for i in ids)
    esc = sum(res[i]["esc_pairs"] for i in ids)
    m["pct_diff_pairs_stage2"] = esc / npairs if npairs else 0.0
    m["pct_all_pairs_stage2"] = esc / nall if nall else 0.0
    m["pct_items_stage2"] = statistics.mean(1.0 if res[i]["escalated"] else 0.0 for i in ids)
    m["usd_per_item"] = statistics.mean(res[i]["usd"] for i in ids)
    lats = [res[i]["lat"] for i in ids]
    m["lat_p50"] = lib.pct(lats, 0.5); m["lat_p95"] = lib.pct(lats, 0.95)
    return m


def cv_mean(items, res, k=5):
    folds = A.make_folds(list(items), k=k)
    sc = []
    for f in folds:
        v = []
        for d in DIMS:
            x = lib.qwk([items[i]["bands"][d] for i in f], [res[i]["bands"][d] for i in f])
            if x == x:
                v.append(x)
        if v:
            sc.append(statistics.mean(v))
    return (statistics.mean(sc), statistics.stdev(sc) if len(sc) > 1 else 0.0) if sc else (float("nan"), 0.0)
