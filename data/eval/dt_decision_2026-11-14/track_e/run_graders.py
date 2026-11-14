# -*- coding: utf-8 -*-
"""Run the frozen graders on the stress set (no retuning).
  python run_graders.py b [--limit N] [--variant p1_expl|p1_expl_mit]   Track B LLM graders
  python run_graders.py a [--limit N]                                   Track A decision-model calls
`orig` items are served from the Track A/B caches and the Sept A3 response files."""
import json, os, sys, statistics
from concurrent.futures import ThreadPoolExecutor
import elib as E
C, L, RQ, F, SENT = E.C, E.L, E.RQ, E.F, E.SENT
RUNS = os.path.join(E.HERE, "runs"); os.makedirs(RUNS, exist_ok=True)
B_MODELS = {"deepseek41f": ("deepseek/deepseek-v4.1-flash", {"reasoning": {"enabled": False}}, (0.051, 0.203)),
            "gpt6luna": ("openai/gpt-6-luna", {"reasoning": {"effort": "none"}}, (0.10, 0.50))}
JEV, LIQ = "typesafe/jev-1.13", "liquid/d1-ultra"

MITIGATION = """

IMPORTANT - free translations. The learner did NOT see the reference; the learner translated the same source text independently. Different wording, word order, sentence structure, synonyms, more or less explicit phrasing, and small differences of emphasis or tone are EXPECTED and are NOT errors. Judge each LRN sentence on its own: (1) is it correct, natural {lang}? (2) does it convey the same message as REF? Report an error only if you can point to a specific word or form in LRN that is wrong in itself, or to a fact in REF that LRN states differently, reverses or leaves out. Never report "differs from the reference" as an error. When in doubt, do not report."""


def b_body(mid, extra, item, variant):
    body = C.build_request(mid, item, item["lang"], "p1_expl", extra)
    if variant == "p1_expl_mit":
        body["messages"][0]["content"] += MITIGATION.format(lang=C.LANG_NAME[item["lang"]])
    return body


def run_b(items, variant):
    for alias, (mid, extra, price) in B_MODELS.items():
        def one(it):
            body = b_body(mid, extra, it, variant)
            try:
                r = E.chat(body, {"stage": "grade_b", "alias": alias, "variant": variant, "item": it["id"]}, price)
            except C.BudgetExceeded as e:
                return {"id": it["id"], "budget_stop": True, "valid": False, "errors": [], "error": str(e)}
            d = C.decode(it, it["lang"], "p1_expl", r.get("content"))
            u = r.get("usage") or {}
            return {"id": it["id"], "lang": it["lang"], "level": it["level"], "valid": d["valid"], "errors": d["errors"],
                    "span_miss": d["span_miss"], "usd": u.get("cost"), "latency": r.get("latency"),
                    "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                    "cached": r.get("cached"), "from_track": r.get("from_track"), "error": r.get("error")}
        b0 = E.spent()
        with ThreadPoolExecutor(6) as ex:
            recs = list(ex.map(one, items))
        tag = f"{alias}__{variant}" + ("__smoke" if LIMIT else "")
        with open(os.path.join(RUNS, tag + ".jsonl"), "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        new = [r for r in recs if not r.get("from_track") and r.get("usd") is not None]
        print(f"[B {tag}] items={len(recs)} valid={sum(r['valid'] for r in recs)} api_err={sum(1 for r in recs if r.get('error'))} "
              f"usd/item(own calls)={statistics.mean([r['usd'] for r in new]) if new else 0:.6f} new=${E.spent()-b0:.4f} total=${E.spent():.4f}")
        for r in recs:
            if r.get("error"):
                print("   ERR", r["id"], r["error"][:200]); break


def units_of(item):
    res = SENT.build_sentence_pairs(item["reference"], item["reproduction"])
    idxs = SENT.map_errors_to_pairs(item["expected_errors"], res.pairs)
    by = {}
    for e, i in zip(item["expected_errors"], idxs):
        if i is not None:
            by.setdefault(i, []).append(e)
    units = []
    for i, pr in enumerate(res.pairs):
        if pr.ref.text == pr.repro.text:
            continue
        errs = by.get(i, [])
        gsub, gsev = L.SA3._representative(errs)
        units.append({"key": f"{item['id']}::{i}", "item_id": item["id"], "base_id": item["base_id"], "pair_idx": i,
                      "lang": item["lang"], "level": item["level"],
                      "ref": pr.ref.text.strip(), "rep": pr.repro.text.strip(), "ref_raw": pr.ref.text, "rep_raw": pr.repro.text,
                      "para": bool(item["sentences_paraphrased"][i]) if i < len(item["sentences_paraphrased"]) else False,
                      "gold_has": bool(errs), "gold_subtype": gsub, "gold_sev": gsev,
                      "gold_errors": [{"subtype": e["subtype_v5_target"], "severity": e["severity_v2"]} for e in errs],
                      "align_ok": res.ok})
    return units


def run_a(items):
    units = [u for it in items for u in units_of(it)]
    by_item = {it["id"]: it for it in items}
    sept_cache = {}
    for lang in E.LANGS:
        for r in L.S.load_responses("A3", lang, "gold"):
            if r.get("ok") and not r.get("skipped"):
                sept_cache[r["job_key"]] = r
    jobs, slots = [], []
    for u in units:
        st, q = RQ.build_D(u, "en")
        for m, nm in ((JEV, "D"), (LIQ, "Q")):
            jobs.append((m, st, q, f"grade_a/{nm}/{u['lang']}/{u['level']}")); slots.append((u["key"], nm))
        it = by_item[u["item_id"]]
        if u["level"] == "orig" and f"{u['base_id']}::{u['pair_idx']}" in sept_cache:
            continue
        st, q = L.REQ.build_a3_request(it["reference"], it["reproduction"], u["ref_raw"], u["rep_raw"], u["lang"])
        jobs.append((JEV, st, q, f"grade_a/S/{u['lang']}/{u['level']}")); slots.append((u["key"], "S"))
    b0 = E.spent()
    res = E.decide_jobs(jobs)
    got = {}
    for (k, nm), r in zip(slots, res):
        if r.get("ok"):
            got[(k, nm)] = r
        else:
            print("   FAIL", k, nm, r.get("error"))
    rows = []
    for u in units:
        row = {k: v for k, v in u.items() if k not in ("ref_raw", "rep_raw")}
        d, qd = got.get((u["key"], "D")), got.get((u["key"], "Q"))
        s = got.get((u["key"], "S"))
        if s is None and u["level"] == "orig":
            sc = sept_cache.get(f"{u['base_id']}::{u['pair_idx']}")
            if sc:
                s = {"answers": sc["answers"], "usd": float(sc["usage"].get("cost", 0) or 0), "latency_s": sc["latency_s"], "from_track": "sept"}
        row["complete"] = bool(d and qd and s)
        if d:
            row.update(F.d_features(d["answers"], u["lang"], "")); row["_usd"] = d["usd"]; row["_lat"] = d["latency_s"]
        if qd:
            row.update(F.d_features(qd["answers"], u["lang"], "q_")); row["q__usd"] = qd["usd"]; row["q__lat"] = qd["latency_s"]
        if s:
            row.update(F.sept_features(s["answers"])); row["_usdS"] = s["usd"]; row["_latS"] = s["latency_s"]
        rows.append(row)
    tag = "A_rows" + ("__smoke" if LIMIT else "")
    with open(os.path.join(RUNS, tag + ".jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    new = [r for r in res if r.get("ok") and not r.get("cached")]
    print(f"[A] items={len(items)} units={len(units)} jobs={len(jobs)} new_calls={len(new)} complete={sum(r['complete'] for r in rows)} "
          f"usd/new_call={statistics.mean([r['usd'] for r in new]) if new else 0:.6f} new=${E.spent()-b0:.4f} total=${E.spent():.4f}")


if __name__ == "__main__":
    LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    variant = sys.argv[sys.argv.index("--variant") + 1] if "--variant" in sys.argv else "p1_expl"
    items = E.load_stress()
    if LIMIT:
        hv = [x for x in items if x["level"] == "heavy"]
        items = [x for x in hv if x["lang"] == "en"][:2] + [x for x in hv if x["lang"] == "zh"][7:9] + [x for x in hv if x["lang"] == "ja"][6:7]
        items = items[:LIMIT]
    if sys.argv[1] == "b":
        run_b(items, variant)
    else:
        run_a(items)
