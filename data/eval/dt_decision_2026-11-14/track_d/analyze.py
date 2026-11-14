# -*- coding: utf-8 -*-
"""Aggregate Track D judgments -> results.json + markdown tables on stdout. No API calls."""
import collections
import json
import os
import re
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
samples = [json.loads(l) for l in open(os.path.join(HERE, "feedback_samples.jsonl"), encoding="utf-8")]
jraw = json.load(open(os.path.join(HERE, "judge_raw.json"), encoding="utf-8"))
ledger = [json.loads(l) for l in open(os.path.join(HERE, "costs.jsonl"))]

J = collections.defaultdict(dict)
for call in jraw:
    for r in call["rows"]:
        J[(r["item"], r["generator"], r["style"], r["error_index"])][r["judge"]] = r


def min_diff(a, b):
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    return a[i:len(a) - j], b[i:len(b) - j]


def length(text, l1):
    return len(text.split()) if l1 == "en" else len(re.sub(r"\s", "", text))


rows = []
for s in samples:
    k = (s["item"], s["generator"], s["style"], s["error_index"])
    t = s["text"]
    row = dict(s)
    row["missing"] = not (isinstance(t, str) and t.strip())
    if row["missing"]:
        rows.append(row)
        continue
    row["len"] = length(t, s["l1"])
    row["over_len"] = None
    if s["style"] in ("meta", "hint"):
        row["over_len"] = row["len"] > (25 if s["l1"] == "en" else 50)
    row["leak_det"] = None
    if s["error_index"] is not None:
        lm, cm = min_diff(s["learner_form"], s["corrected_form"])
        cm = cm.strip()
        if s["corrected_form"] in t:
            row["leak_det"] = True
        elif cm:
            # the corrected fragment appears in the text although it is not part of what the learner wrote
            row["leak_det"] = (cm in t) and (cm not in s["learner_form"] or len(cm) > 1 and t.count(cm) > s["learner_form"].count(cm))
    for j in ("J1", "J2"):
        r = J.get(k, {}).get(j)
        row[j] = r and {x: r[x] for x in ("c", "k", "s", "r", "t", "u", "note")}
    rows.append(row)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def agg(rs):
    ok = [r for r in rs if not r["missing"] and r.get("J1") and r.get("J2")]
    o = {"n": len(rs), "n_missing": sum(r["missing"] for r in rs), "n_judged": len(ok)}
    if not ok:
        return o
    for m in "csrtu":
        o[m] = mean([(r["J1"][m] + r["J2"][m]) / 2 for r in ok])
    o["wrong_J1"] = mean([r["J1"]["c"] == 0 for r in ok])
    o["wrong_J2"] = mean([r["J2"]["c"] == 0 for r in ok])
    o["wrong_either"] = mean([r["J1"]["c"] == 0 or r["J2"]["c"] == 0 for r in ok])
    o["wrong_both"] = mean([r["J1"]["c"] == 0 and r["J2"]["c"] == 0 for r in ok])
    o["n_wrong_either"] = sum(r["J1"]["c"] == 0 or r["J2"]["c"] == 0 for r in ok)
    o["n_wrong_both"] = sum(r["J1"]["c"] == 0 and r["J2"]["c"] == 0 for r in ok)
    o["imperfect_either"] = mean([r["J1"]["c"] < 2 or r["J2"]["c"] < 2 for r in ok])
    o["leak_J1"] = mean([r["J1"]["k"] for r in ok])
    o["leak_J2"] = mean([r["J2"]["k"] for r in ok])
    o["leak_both"] = mean([r["J1"]["k"] == 1 and r["J2"]["k"] == 1 for r in ok])
    o["leak_det"] = mean([r["leak_det"] for r in ok])
    o["over_len"] = mean([r["over_len"] for r in ok])
    o["len_median"] = st.median([r["len"] for r in ok])
    o["good_all"] = mean([all(r[j]["c"] == 2 and r[j]["u"] >= 1 and r[j]["r"] >= 1 for j in ("J1", "J2")) for r in ok])
    return o


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(v) / n) * (b.count(v) / n) for v in set(a) | set(b))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else None


res = {}
gens = ["G0", "G0live", "G1", "G2", "G3"]
styles = ["direct", "meta", "hint", "app", "summary"]
res["by_gen_style"] = {f"{g}/{s}": agg([r for r in rows if r["generator"] == g and r["style"] == s])
                       for g in gens for s in styles if any(r["generator"] == g and r["style"] == s for r in rows)}
res["by_gen_l2"] = {f"{g}/{l}": agg([r for r in rows if r["generator"] == g and r["l2"] == l])
                    for g in gens for l in ("en", "zh", "ja")}
res["by_gen_l2_explanatory"] = {f"{g}/{l}": agg([r for r in rows if r["generator"] == g and r["l2"] == l and r["style"] in ("meta", "hint", "app")])
                                for g in gens for l in ("en", "zh", "ja")}
res["by_gen_l1"] = {f"{g}/{l}": agg([r for r in rows if r["generator"] == g and r["l1"] == l]) for g in gens for l in ("en", "zh", "ja")}
res["by_gen"] = {g: agg([r for r in rows if r["generator"] == g]) for g in gens}
res["summary_clean"] = {g: agg([r for r in rows if r["generator"] == g and r["style"] == "summary" and r["kind"] == "clean"]) for g in gens if g != "G0live"}
res["summary_error"] = {g: agg([r for r in rows if r["generator"] == g and r["style"] == "summary" and r["kind"] != "clean"]) for g in gens if g != "G0live"}
# per subtype: template vs LLMs for meta/hint
sub = sorted({r["subtype"] for r in rows if r["subtype"]})
res["by_subtype"] = {}
for stp in sub:
    d = {}
    for s in ("meta", "hint", "app"):
        for g in gens:
            rs = [r for r in rows if r["subtype"] == stp and r["style"] == s and r["generator"] == g]
            if rs:
                a = agg(rs)
                d[f"{g}/{s}"] = {k: a.get(k) for k in ("n", "c", "u", "s", "wrong_either", "leak_both", "good_all")}
    res["by_subtype"][stp] = d
ok = [r for r in rows if not r["missing"] and r.get("J1") and r.get("J2")]
res["judge_agreement"] = {
    "n": len(ok),
    "c_exact": mean([r["J1"]["c"] == r["J2"]["c"] for r in ok]),
    "wrong_flag_kappa": kappa([r["J1"]["c"] == 0 for r in ok], [r["J2"]["c"] == 0 for r in ok]),
    "c_lt2_kappa": kappa([r["J1"]["c"] < 2 for r in ok], [r["J2"]["c"] < 2 for r in ok]),
    "leak_kappa": kappa([r["J1"]["k"] for r in ok], [r["J2"]["k"] for r in ok]),
    "leak_J1_vs_det_kappa": kappa([bool(r["J1"]["k"]) for r in ok if r["leak_det"] is not None], [r["leak_det"] for r in ok if r["leak_det"] is not None]),
    "leak_J2_vs_det_kappa": kappa([bool(r["J2"]["k"]) for r in ok if r["leak_det"] is not None], [r["leak_det"] for r in ok if r["leak_det"] is not None]),
    "u_exact": mean([r["J1"]["u"] == r["J2"]["u"] for r in ok]),
    "J1_mean_c": mean([r["J1"]["c"] for r in ok]), "J2_mean_c": mean([r["J2"]["c"] for r in ok]),
    "J1_wrong": sum(r["J1"]["c"] == 0 for r in ok), "J2_wrong": sum(r["J2"]["c"] == 0 for r in ok),
}
# cost / latency from the ledger
cost = {}
for g, m in (("G1", "qwen/qwen3.7-flash"), ("G2", "deepseek/deepseek-v4.1-flash"), ("G3", "openai/gpt-6-luna")):
    for s in styles:
        ls = [l for l in ledger if l["tag"].startswith(f"gen/{g}/{s}/")]
        seen, uniq = set(), []
        for l in ls:  # smoke + full share cache; ledger has one line per real call
            if l["tag"] not in seen:
                seen.add(l["tag"])
                uniq.append(l)
        if uniq:
            lat = sorted(l["latency_s"] for l in uniq)
            cost[f"{g}/{s}"] = {"model": m, "calls": len(uniq), "usd_per_call": round(sum(l["cost_usd"] for l in uniq) / len(uniq), 7),
                                "usd_total": round(sum(l["cost_usd"] for l in uniq), 5),
                                "lat_p50": lat[len(lat) // 2], "lat_p90": lat[int(len(lat) * 0.9)],
                                "tok_in": round(mean([l["prompt_tokens"] for l in uniq])), "tok_out": round(mean([l["completion_tokens"] for l in uniq]))}
res["cost_latency"] = cost
res["spend"] = {"total_usd": round(sum(l["cost_usd"] for l in ledger), 5), "calls": len(ledger),
                "by_model": {m: round(sum(l["cost_usd"] for l in ledger if l["model"] == m), 5) for m in sorted({l["model"] for l in ledger})}}
bad = [r for r in ok if r["J1"]["c"] == 0 and r["J2"]["c"] == 0]
res["wrong_both_examples"] = [{k: r[k] for k in ("item", "l2", "l1", "subtype", "learner_form", "corrected_form", "generator", "style", "text")}
                              | {"J1_note": r["J1"]["note"], "J2_note": r["J2"]["note"]} for r in bad]
res["wrong_one_examples"] = [{k: r[k] for k in ("item", "l2", "l1", "subtype", "learner_form", "corrected_form", "generator", "style", "text")}
                             | {"J1_c": r["J1"]["c"], "J2_c": r["J2"]["c"], "J1_note": r["J1"]["note"], "J2_note": r["J2"]["note"]}
                             for r in ok if (r["J1"]["c"] == 0) != (r["J2"]["c"] == 0)]
json.dump(res, open(os.path.join(HERE, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(rows, open(os.path.join(HERE, "judged_rows.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)


def pct(x):
    return "–" if x is None else f"{100 * x:.0f}%"


print("| gen/style | n | missing | c (0-2) | wrong either | wrong both | leak J1/J2/both/det | specific | clear | tone | useful | good_all | len med | over-len |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k, a in res["by_gen_style"].items():
    if a.get("n_judged"):
        print(f"| {k} | {a['n']} | {a['n_missing']} | {a['c']:.2f} | {pct(a['wrong_either'])} ({a['n_wrong_either']}) | {pct(a['wrong_both'])} ({a['n_wrong_both']}) | {pct(a['leak_J1'])}/{pct(a['leak_J2'])}/{pct(a['leak_both'])}/{pct(a['leak_det'])} | {a['s']:.2f} | {a['r']:.2f} | {a['t']:.2f} | {a['u']:.2f} | {pct(a['good_all'])} | {a['len_median']} | {pct(a['over_len'])} |")
for name in ("by_gen_l2", "by_gen_l2_explanatory", "by_gen_l1", "summary_clean", "summary_error"):
    print("\n" + name)
    for k, a in res[name].items():
        if a.get("n_judged"):
            print(f"| {k} | {a['n_judged']} | c {a['c']:.2f} | wrong either {pct(a['wrong_either'])} ({a['n_wrong_either']}) | both {pct(a['wrong_both'])} ({a['n_wrong_both']}) | u {a['u']:.2f} | good {pct(a['good_all'])}")
print("\nagreement", res["judge_agreement"])
print("\ncost")
for k, c in cost.items():
    print(k, c)
print(res["spend"])
print("\nby subtype  (u / good_all):  G0 meta | G0 hint | G0live | best-of LLM meta | hint | app")
for stp, d in res["by_subtype"].items():
    def f(k):
        x = d.get(k)
        return "–" if not x or x.get("u") is None else f"{x['u']:.2f}/{pct(x['good_all'])}/w{pct(x['wrong_either'])}"
    print(f"| {stp} | {d['G0/meta']['n']} | {f('G0/meta')} | {f('G0/hint')} | {f('G0live/app')} | {f('G1/meta')} | {f('G2/meta')} | {f('G3/meta')} | {f('G1/hint')} | {f('G2/hint')} | {f('G3/hint')} | {f('G3/app')} |")
