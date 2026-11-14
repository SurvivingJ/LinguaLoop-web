# -*- coding: utf-8 -*-
"""Second pass for error-bearing sentences the generator left word-for-word identical to the gold
learner sentence (mostly very short English sentences): one short call per sentence, then the same
independent verification. Writes build_regen.json (consumed by assemble.py)."""
import json, os
from concurrent.futures import ThreadPoolExecutor
import elib as E, build_set as B
C = E.C
SYS = """You rewrite one {lang} learner sentence for a translation-grader test set. The learner sentence is a translation of the same content as the REFERENCE sentence and contains planted learner error(s). Produce a NEW learner sentence that (a) expresses exactly the reference meaning in clearly different wording or structure (synonyms, different word order, different construction), as a learner who never saw the reference might write, (b) still contains exactly the same planted error(s): same wrong word/form/structure, same type and severity, so that replacing only the erroneous fragment with its correction gives a fully correct, natural sentence, and (c) has no other error, the same register, one sentence, same final punctuation. The sentence must NOT be identical to the original learner sentence: change the words around the error.
Return JSON only: {{"sentence": "...", "errors": [{{"fragment": "<erroneous stretch copied verbatim from your sentence>", "corrected": "<what it should read>"}}]}} with one entry per listed error, in order. No markdown."""

out = json.load(open(os.path.join(E.HERE, "build_verify.json"), encoding="utf-8"))
jobs = []
for lang in E.LANGS:
    for it in B.select(lang):
        g = out[it["id"]]["gen"]; r, p = B.sents(it)
        by = {}
        for k, e in enumerate(it["expected_errors"]):
            by.setdefault(B.err_sentence(it, e), []).append((k, e))
        for si, es in by.items():
            if g["sentences"][si] == p[si].text.strip():
                jobs.append((lang, it, si, es))


def one(j):
    lang, it, si, es = j
    r, p = B.sents(it)
    u = [f"REFERENCE: {r[si].text.strip()}", f"ORIGINAL LEARNER: {p[si].text.strip()}", "ERRORS:"]
    for k, e in es:
        u.append(f"- type {e['subtype']}; severity {e['severity_v2']}; wrong \"{e.get('learner_form')}\" -> correct \"{e.get('corrected_form')}\"")
    body = {"model": B.GEN_MODEL, "messages": [{"role": "system", "content": SYS.format(lang=C.LANG_NAME[lang])},
                                               {"role": "user", "content": "\n".join(u)}],
            "temperature": 0.7, "max_tokens": 300, "usage": {"include": True}, "reasoning": {"enabled": False}}
    rec = E.chat(body, {"stage": "regen", "item": it["id"]}, B.PRICE[B.GEN_MODEL])
    j2 = C._extract_json(rec.get("content"))
    res = {"id": it["id"], "sentence": si, "ok": False, "gen": j2}
    if not isinstance(j2, dict) or len(j2.get("errors", [])) != len(es):
        res["why"] = "bad json"; return res
    s = j2["sentence"].strip()
    if s == p[si].text.strip() or len(B.SENT.split_sentences(s)) != 1 or any(x["fragment"] not in s for x in j2["errors"]):
        res["why"] = "unchanged / structure / fragment not found"; return res
    lines = [f"S1 REF: {r[si].text.strip()}\nS1 LRN: {s}", "", "PLANTED errors:"]
    for (k, e), x in zip(es, j2["errors"]):
        lines.append(f"- sentence 1: type {e['subtype']} ({e['severity_v2']}); fragment \"{x['fragment']}\" should read \"{x['corrected']}\"")
    vb = {"model": B.VER_MODEL, "messages": [{"role": "system", "content": B.VER_SYS.format(lang=C.LANG_NAME[lang])},
                                             {"role": "user", "content": "\n".join(lines)}],
          "temperature": 0, "max_tokens": 300, "usage": {"include": True},
          "response_format": {"type": "json_schema", "json_schema": B.VER_SCHEMA}, "reasoning": {"effort": "none"}}
    vr = E.chat(vb, {"stage": "regen_verify", "item": it["id"]}, B.PRICE[B.VER_MODEL])
    v = C._extract_json(vr.get("content"))
    res["ver"] = v
    try:
        s1 = v["sentences"][0]
        res["ok"] = bool(s1["planted_ok"]) and not s1["other_error"].strip()
        if not res["ok"]:
            res["why"] = "verifier: " + (s1["other_error"] or "planted error not OK")
    except Exception:
        res["why"] = "no verdict"
    res["text"] = s; res["errors"] = {k: x for (k, e), x in zip(es, j2["errors"])}
    return res


b0 = E.spent()
with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(one, jobs))
json.dump(res, open(os.path.join(E.HERE, "build_regen.json"), "w"), ensure_ascii=False, indent=1)
print(len(jobs), "sentences; passed", sum(r["ok"] for r in res), f"new=${E.spent()-b0:.4f} total=${E.spent():.4f}")
for r in res:
    print(r["id"], r["ok"], r.get("text"), "|", r.get("why", ""))
