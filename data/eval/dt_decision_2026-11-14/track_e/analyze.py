# -*- coding: utf-8 -*-
"""Score every grader on the stress set with the tracks' own metric code -> results.json."""
import json, math, os, statistics, sys, collections
import elib as E
C, BS, L, P, SENT = E.C, E.BS, E.L, E.P, E.SENT
from services.dual_translation import eval_metrics as EM
DIMS = ("accuracy", "fidelity", "understandability")
LEVELS = ("orig", "moderate", "heavy")
FZB = json.load(open(os.path.join(E.TB, "frozen_configs.json")))["explaining"]
FZA = json.load(open(os.path.join(E.TA, "frozen_config.json")))["configs"]
A_CFGS = {"A_fused (jev-1.13)": ("jev", FZA["A_fused"], ("_usd", "_usdS")),
          "A_D_only (jev-1.13)": ("jev", FZA["A_D_only"], ("_usd",)),
          "A_sept_refit (jev-1.13)": ("jev", FZA["A_sept_refit"], ("_usdS",)),
          "D_only (liquid/d1-ultra)": ("liq", {"det": "D", "tau": 0.5, "sub": "D", "crit": "D", "tau_c": 0.6, "sev": "prior"}, ("_usd",))}
B_VARIANT = sys.argv[1] if len(sys.argv) > 1 else "p1_expl"
SEV_RANK = {"minor": 0, "major": 1, "critical": 2}
items = E.load_stress()
BY = {x["id"]: x for x in items}


def r3(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(x, 3)


def sent_index(item, pos):
    for i, pr in enumerate(SENT.build_sentence_pairs(item["reference"], item["reproduction"]).pairs):
        if pr.repro.start <= pos < pr.repro.end:
            return i
    return None


def sentence_table(item, pred_by_sent):
    """per sentence: category + whether flagged (+ worst predicted severity)."""
    pairs = SENT.build_sentence_pairs(item["reference"], item["reproduction"]).pairs
    gold = collections.defaultdict(list)
    for e in item["expected_errors"]:
        gold[e["sentence"]].append(e)
    out = []
    for i, pr in enumerate(pairs):
        para = item["sentences_paraphrased"][i]
        ident = pr.ref.text == pr.repro.text
        cat = ("err_" if gold.get(i) else "clean_") + ("para" if para else ("identical" if ident else "verbatim_edit"))
        preds = pred_by_sent.get(i, [])
        out.append({"cat": cat, "flag": bool(preds), "sev": max((SEV_RANK[p["severity"]] for p in preds), default=-1),
                    "n_gold": len(gold.get(i, [])), "i": i})
    return out


def sent_summary(tabs):
    c = collections.defaultdict(lambda: [0, 0, 0])  # n, flagged, flagged major+
    for t in tabs:
        for s in t:
            c[s["cat"]][0] += 1; c[s["cat"]][1] += s["flag"]; c[s["cat"]][2] += s["sev"] >= 1
    return {k: {"n": v[0], "flagged": v[1], "flagged_major_plus": v[2]} for k, v in sorted(c.items())}


def item_clean(recs):
    cl = [r for r in recs if r["kind"] == "clean"]
    return {"n_clean": len(cl), "flagged_any": sum(1 for r in cl if r["pred_errors"]),
            "flagged_major_plus": sum(1 for r in cl if any(SEV_RANK[p["severity"]] >= 1 for p in r["pred_errors"])),
            "band_below_4": sum(1 for r in cl if any(r["pred_bands"][d] < 4 for d in DIMS))}


def qwk_exact(recs):
    o = {}
    for d in DIMS:
        yt = [r["exp_bands"][d] for r in recs]; yp = [r["pred_bands"][d] for r in recs]
        o["qwk_" + d] = r3(EM.quadratic_weighted_kappa(yt, yp)) if len(set(yt)) > 1 or len(set(yp)) > 1 else None
        o["exact_" + d] = r3(sum(a == b for a, b in zip(yt, yp)) / len(yt))
        o["mean_signed_err_" + d] = r3(statistics.mean(b - a for a, b in zip(yt, yp)))
    o["exact_3dim"] = r3(sum(all(r["exp_bands"][d] == r["pred_bands"][d] for d in DIMS) for r in recs) / len(recs))
    return o


# ------------------------------------------------------------------ Track B graders
def b_eval(alias):
    run = {}
    with open(os.path.join(E.HERE, "runs", f"{alias}__{B_VARIANT}.jsonl"), encoding="utf-8") as f:
        for r in map(json.loads, f):
            run[r["id"]] = r
    out = {}; ex = []
    for lang in E.LANGS:
        rule = FZB[alias]["severity_rule"][lang]
        for lv in LEVELS:
            its = [x for x in items if x["lang"] == lang and x["level"] == lv and x["id"] in run]
            if not its:
                continue
            recs, tabs = [], []
            loc = {"para": [0, 0, 0], "verbatim": [0, 0, 0]}  # gold errors: n, sentence flagged, span located
            for it in its:
                r = run[it["id"]]
                pred = BS.apply_sev(r["errors"], rule)
                rec = {"id": it["id"], "kind": it["kind"], "pred_errors": pred,
                       "exp_errors": [{"span": e["span_repro"], "subtype": e["subtype"], "severity": e["severity_v2"]} for e in it["expected_errors"]],
                       "pred_bands": BS.bands_of(pred), "exp_bands": it["expected_bands"], "exp_overall": None, "pred_overall": None,
                       "valid": r["valid"], "usd": r.get("usd") or 0.0, "latency": r.get("latency"), "span_miss": r.get("span_miss", 0),
                       "called": bool(r.get("prompt_tokens")), "ptok": r.get("prompt_tokens") or 0, "ctok": r.get("completion_tokens") or 0}
                recs.append(rec)
                pbs = collections.defaultdict(list)
                for p in pred:
                    si = sent_index(it, p["span"][0])
                    pbs[si].append(p)
                tab = sentence_table(it, pbs); tabs.append(tab)
                al = EM.align_errors([p["span"] for p in pred], [e["span"] for e in rec["exp_errors"]])
                matched = {j for _, j in al.matches}
                for j, e in enumerate(it["expected_errors"]):
                    k = "para" if e["in_paraphrased_sentence"] else "verbatim"
                    loc[k][0] += 1; loc[k][1] += bool(pbs.get(e["sentence"])); loc[k][2] += j in matched
                for s in tab:
                    if s["flag"] and s["cat"].startswith("clean_"):
                        pr = SENT.build_sentence_pairs(it["reference"], it["reproduction"]).pairs[s["i"]]
                        for p in pbs[s["i"]]:
                            ex.append({"grader": alias, "id": it["id"], "cat": s["cat"], "ref": pr.ref.text.strip(), "lrn": pr.repro.text.strip(),
                                       "flagged_span": p["learner_text"], "type": p["subtype"], "severity": p["severity"],
                                       "explanation": p.get("explanation")})
            m = BS.metrics(recs)
            o = {"n": len(recs), **qwk_exact(recs),
                 "span_p": m["span_p"], "span_r": m["span_r"], "tp_fp_fn": m["tp_fp_fn"], "type_top1": m["type_top1"], "type_n": m["type_n"],
                 "sev_exact": m["sev_exact"], "clean_items": item_clean(recs), "sentences": sent_summary(tabs),
                 "gold_error_location": {k: {"n": v[0], "sentence_flagged": v[1], "span_located": v[2]} for k, v in loc.items()},
                 "usd_per_item": m["usd_per_item"], "p50_latency_s": m["p50_latency_s"], "p90_latency_s": m["p90_latency_s"],
                 "json_valid": m["json_valid"], "span_not_verbatim": m["span_miss"], "n_pred_errors": m["n_pred_errors"],
                 "severity_rule": rule}
            out[f"{lang}/{lv}"] = o
    return out, ex


# ------------------------------------------------------------------ Track A pipelines
def a_rows():
    rows = []
    with open(os.path.join(E.HERE, "runs", "A_rows.jsonl"), encoding="utf-8") as f:
        rows = [json.loads(x) for x in f]
    return rows


def liq_view(r):
    o = {k: v for k, v in r.items() if not k.startswith("q_")}
    for k, v in r.items():
        if k.startswith("q_"):
            o[k[2:]] = v
    return o


def a_eval(name):
    src, cfg, cost_keys = A_CFGS[name]
    rows = a_rows()
    if src == "liq":
        rows = [liq_view(r) for r in rows]
    out = {}; ex = []
    for lang in E.LANGS:
        for lv in LEVELS:
            its = [x for x in items if x["lang"] == lang and x["level"] == lv]
            rr = [r for r in rows if r["lang"] == lang and r["level"] == lv]
            recs, tabs = [], []
            dec = {r["key"]: P.decide(r, cfg) for r in rr}
            um = P.unit_metrics(rr, cfg)
            usd, lat = [], []
            for it in its:
                mine = [r for r in rr if r["item_id"] == it["id"]]
                errs = [dec[r["key"]] for r in mine if dec[r["key"]]]
                pb = L.bands_from_errors(errs)
                recs.append({"id": it["id"], "kind": it["kind"], "pred_errors": errs, "pred_bands": pb, "exp_bands": it["expected_bands_v5"]})
                pbs = {r["pair_idx"]: [dec[r["key"]]] for r in mine if dec[r["key"]]}
                tab = sentence_table(it, pbs); tabs.append(tab)
                usd.append(sum(r.get(k, 0.0) for r in mine for k in cost_keys))
                lat.append(max([r.get(k.replace("usd", "lat"), 0.0) for r in mine for k in cost_keys] or [0.0]))
                for s in tab:
                    if s["flag"] and s["cat"].startswith("clean_"):
                        r = [x for x in mine if x["pair_idx"] == s["i"]][0]
                        ex.append({"grader": name, "id": it["id"], "cat": s["cat"], "ref": r["ref"], "lrn": r["rep"],
                                   "type": dec[r["key"]]["subtype"], "severity": dec[r["key"]]["severity"],
                                   "det_score": round(P.det_score(r, cfg["det"]), 3)})
            # unit metrics split by paraphrased / verbatim sentence
            split = {}
            for nm, sel in (("para", [r for r in rr if r["para"]]), ("verbatim", [r for r in rr if not r["para"]])):
                if sel:
                    u = P.unit_metrics(sel, cfg)
                    split[nm] = {k: r3(u[k]) if isinstance(u[k], float) else u[k] for k in ("precision", "recall", "tp", "fp", "fn", "tn", "subtype_top1", "severity_acc")}
            out[f"{lang}/{lv}"] = {"n": len(its), "n_units": len(rr), **qwk_exact(recs),
                                   "unit_p": r3(um["precision"]), "unit_r": r3(um["recall"]), "tp_fp_fn": [um["tp"], um["fp"], um["fn"]],
                                   "type_top1": r3(um["subtype_top1"]), "sev_exact": r3(um["severity_acc"]), "auc": r3(um["auc"]),
                                   "unit_split": split, "clean_items": item_clean(recs), "sentences": sent_summary(tabs),
                                   "usd_per_item": round(statistics.mean(usd), 6), "p50_latency_s": round(statistics.median(lat), 2)}
    return out, ex


# ------------------------------------------------------------------ diff locality
def diff_stats():
    out = {}
    for lv in LEVELS:
        for lang in E.LANGS + ("all",):
            c = collections.Counter(); hl_prec = []; share = []; nh = []
            for it in items:
                if it["level"] != lv or (lang != "all" and it["lang"] != lang):
                    continue
                pairs = SENT.build_sentence_pairs(it["reference"], it["reproduction"]).pairs
                for e in it["expected_errors"]:
                    pr = pairs[e["sentence"]]
                    hs = C.diff_hunks(pr.ref.text, pr.repro.text, it["lang"])
                    slen = max(1, len(pr.repro.text.strip()))
                    hl = sum(h["end"] - h["start"] for h in hs)
                    gs = [e["span_repro"][0] - pr.repro.start, e["span_repro"][1] - pr.repro.start]
                    ov = sum(max(0, min(h["end"], gs[1]) - max(h["start"], gs[0])) for h in hs)
                    c["err_sentences"] += 1
                    local = len(hs) <= 2 and hl / slen <= 0.30
                    c["local"] += local
                    c["single_hunk_on_error"] += len(hs) == 1 and ov > 0
                    c["some_hunk_touches_error"] += ov > 0
                    c["pinpoints"] += ov > 0 and hl > 0 and ov / hl >= 0.5
                    hl_prec.append(ov / hl if hl else 0); share.append(hl / slen); nh.append(len(hs))
                # clean sentences that are not identical: how much is highlighted
                for i, pr in enumerate(pairs):
                    if pr.ref.text != pr.repro.text and not any(e["sentence"] == i for e in it["expected_errors"]):
                        hs = C.diff_hunks(pr.ref.text, pr.repro.text, it["lang"])
                        c["clean_changed_sentences"] += 1; c["clean_hunks"] += len(hs)
            n = c["err_sentences"]
            if n:
                out[f"{lang}/{lv}"] = {"gold_errors": n, "diff_is_small_local_edit": c["local"], "single_hunk_on_error": c["single_hunk_on_error"],
                                       "some_hunk_touches_error": c["some_hunk_touches_error"], "highlight_mostly_on_error": c["pinpoints"],
                                       "median_hunks": statistics.median(nh), "median_share_of_sentence_highlighted": r3(statistics.median(share)),
                                       "mean_highlight_precision": r3(statistics.mean(hl_prec)),
                                       "clean_changed_sentences": c["clean_changed_sentences"],
                                       "hunks_per_clean_changed_sentence": r3(c["clean_hunks"] / c["clean_changed_sentences"]) if c["clean_changed_sentences"] else None}
    return out


if __name__ == "__main__":
    res = {"graders": {}, "false_flag_examples": []}
    for alias, nm in (("deepseek41f", "deepseek-v4.1-flash p1_expl"), ("gpt6luna", "gpt-6-luna p1_expl")):
        o, ex = b_eval(alias); res["graders"][nm] = o; res["false_flag_examples"] += ex
    if B_VARIANT == "p1_expl":
        for nm in A_CFGS:
            o, ex = a_eval(nm); res["graders"][nm] = o; res["false_flag_examples"] += ex
        res["diff_locality"] = diff_stats()
    json.dump(res, open(os.path.join(E.HERE, f"analysis_{B_VARIANT}.json"), "w"), ensure_ascii=False, indent=1)
    for nm, o in res["graders"].items():
        print("\n##", nm)
        for k, v in o.items():
            p = v.get("span_p", v.get("unit_p")); r = v.get("span_r", v.get("unit_r"))
            ci = v["clean_items"]; s = v["sentences"]
            cp = s.get("clean_para", {"n": 0, "flagged": 0, "flagged_major_plus": 0}); ep = s.get("err_para", {"n": 0, "flagged": 0})
            ev = s.get("err_verbatim_edit", {"n": 0, "flagged": 0})
            print(f" {k:12s} n={v['n']:2d} P {p} R {r} {v['tp_fp_fn']} type {v['type_top1']} | cleanItems {ci['flagged_any']}/{ci['n_clean']} maj+ {ci['flagged_major_plus']} "
                  f"| cleanParaSent {cp['flagged']}/{cp['n']} (maj+ {cp['flagged_major_plus']}) errPara {ep['flagged']}/{ep['n']} errVerb {ev['flagged']}/{ev['n']} "
                  f"| qwk {v['qwk_accuracy']}/{v['qwk_fidelity']}/{v['qwk_understandability']} exact {v['exact_accuracy']}/{v['exact_fidelity']}/{v['exact_understandability']} "
                  f"| ${v['usd_per_item']:.6f} p50 {v['p50_latency_s']}")
    for k, v in res.get("diff_locality", {}).items():
        print(k, v)
