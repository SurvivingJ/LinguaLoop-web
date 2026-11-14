# -*- coding: utf-8 -*-
"""build_verify.json -> stress_set.jsonl (levels: orig / moderate / heavy) + build_stats.json.
Fix policy: a sentence that failed structure checks, whose planted error the generator could not
keep, or that the verifier objected to (planted error not OK, or any other problem, even minor)
is REVERTED to the original gold learner sentence. An item is dropped from `heavy` if fewer than
2/3 of its sentences remain paraphrased."""
import json, os, random, collections
import elib as E, build_set as B

out = json.load(open(os.path.join(E.HERE, "build_verify.json"), encoding="utf-8"))
stats = collections.Counter(); items = []; per_lang = {l: collections.Counter() for l in E.LANGS}
PROV = {"generator": B.GEN_MODEL, "verifier": B.VER_MODEL,
        "labels": "synthetic by construction, model-verified, NOT human-adjudicated"}


def build(it, lang, level, texts, para, frags):
    r, p = B.sents(it)
    pos, parts = [], []
    cur = 0
    for i, s in enumerate(p):
        tail = s.text[len(s.text.rstrip()):]
        lead = s.text[:len(s.text) - len(s.text.lstrip())]
        t = (lead + texts[i] + tail) if para[i] else s.text
        pos.append(cur + (len(lead) if para[i] else 0)); parts.append(t); cur += len(t)
    repro = "".join(parts)
    errs = []
    starts = [0]
    for t in parts: starts.append(starts[-1] + len(t))
    for k, e in enumerate(it["expected_errors"]):
        si = B.err_sentence(it, e)
        if para[si]:
            fr = frags[k]
            a = pos[si] + texts[si].find(fr["fragment"])
            span = [a, a + len(fr["fragment"])]; lf, cf = fr["fragment"], fr["corrected"]
        else:
            d = starts[si] - p[si].start
            span = [e["span_repro"][0] + d, e["span_repro"][1] + d]; lf, cf = e.get("learner_form"), e.get("corrected_form")
        assert repro[span[0]:span[1]], (it["id"], level)
        errs.append({"span_repro": span, "subtype": e["subtype"], "subtype_v5_target": e.get("subtype_v5_target") or e["subtype"],
                     "severity_v2": e["severity_v2"], "learner_form": lf, "corrected_form": cf, "sentence": si,
                     "in_paraphrased_sentence": bool(para[si])})
    return {"id": f"{it['id']}@{level}", "base_id": it["id"], "lang": lang, "level": level, "kind": it["kind"],
            "reference": it["reference"], "reproduction": repro, "expected_errors": errs,
            "expected_bands": it["expected_bands"], "expected_bands_v5": it["expected_bands_v5"],
            "sentences_paraphrased": [bool(x) for x in para], "n_sentences": len(p), "provenance": PROV}


reverts = []
REGEN = {(x["id"], x["sentence"]): x for x in json.load(open(os.path.join(E.HERE, "build_regen.json"), encoding="utf-8"))}
stats["regen_attempted"] = len(REGEN); stats["regen_passed"] = sum(x["ok"] for x in REGEN.values())
for lang in E.LANGS:
    for it in B.select(lang):
        v = out[it["id"]]; g = v["gen"]; r, p = B.sents(it)
        n = len(p); ok = [True] * n; stats["items"] += 1; stats["sentences"] += n
        for i in g["struct_revert"]:
            ok[i] = False; stats["revert_generator_declined_or_structure"] += 1
            reverts.append({"id": it["id"], "sentence": i + 1, "why": "generator declined to keep the error / structure check"})
        ver = {s["sentence"] - 1: s for s in (v.get("ver") or {}).get("sentences", [])}
        for i in range(n):
            if not ok[i]:
                continue
            s = ver.get(i)
            if s is None:
                ok[i] = False; stats["revert_no_verdict"] += 1; continue
            if not s["planted_ok"]:
                ok[i] = False; stats["revert_planted_error_not_ok"] += 1
                reverts.append({"id": it["id"], "sentence": i + 1, "why": "verifier: planted error not OK", "text": g["sentences"][i]})
            elif s["other_error"].strip():
                ok[i] = False; stats["revert_unintended_problem"] += 1
                reverts.append({"id": it["id"], "sentence": i + 1, "why": "verifier: " + s["other_error"], "text": g["sentences"][i], "ref": r[i].text.strip()})
            elif g["sentences"][i] == p[i].text.strip():
                rg = REGEN.get((it["id"], i))
                if rg and rg["ok"]:  # second-pass rewrite of an error sentence, verified separately
                    g["sentences"][i] = rg["text"]
                    for k, x in rg["errors"].items():
                        g["errors"][int(k)] = {"fragment": x["fragment"], "corrected": x["corrected"], "kept": True}
                else:
                    ok[i] = False; stats["unchanged"] += 1
        stats["sentences_passed"] += sum(ok)
        items.append(build(it, lang, "orig", g["sentences"], [False] * n, g["errors"]))
        per_lang[lang]["orig"] += 1
        if sum(ok) / n >= 0.66:
            items.append(build(it, lang, "heavy", g["sentences"], ok, g["errors"])); per_lang[lang]["heavy"] += 1
        else:
            stats["items_dropped_from_heavy"] += 1; per_lang[lang]["heavy_dropped"] += 1
        avail = [i for i in range(n) if ok[i]]
        rng = random.Random("mod" + it["id"]); rng.shuffle(avail)
        k = min(len(avail), max(1, n // 2))
        if k >= 1 and avail:
            para = [i in avail[:k] for i in range(n)]
            items.append(build(it, lang, "moderate", g["sentences"], para, g["errors"])); per_lang[lang]["moderate"] += 1
        else:
            stats["items_dropped_from_moderate"] += 1
with open(os.path.join(E.HERE, "stress_set.jsonl"), "w", encoding="utf-8") as f:
    for x in items:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
comp = collections.defaultdict(collections.Counter)
for x in items:
    c = comp[f"{x['lang']}/{x['level']}"]
    c["items"] += 1; c["clean"] += x["kind"] == "clean"; c["errors"] += len(x["expected_errors"])
    c["errors_in_para_sentence"] += sum(e["in_paraphrased_sentence"] for e in x["expected_errors"])
    c["sentences"] += x["n_sentences"]; c["sentences_para"] += sum(x["sentences_paraphrased"])
json.dump({"stats": stats, "per_lang": per_lang, "composition": comp, "reverted_sentences": reverts},
          open(os.path.join(E.HERE, "build_stats.json"), "w"), ensure_ascii=False, indent=1)
print(dict(stats)); 
for k, c in sorted(comp.items()): print(k, dict(c))
