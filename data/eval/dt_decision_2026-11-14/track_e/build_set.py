# -*- coding: utf-8 -*-
"""Build the paraphrase stress set.
  python build_set.py gen [--limit N]     generate heavy paraphrases (one call per gold item)
  python build_set.py verify [--limit N]  independent check by a second model
  python build_set.py assemble            apply fixes (revert failed sentences), write stress_set.jsonl
Labels are synthetic-by-construction and model-verified, NOT human-adjudicated."""
from __future__ import annotations
import difflib, json, os, random, sys
from concurrent.futures import ThreadPoolExecutor
import elib as E
C, SENT = E.C, E.SENT

GEN_MODEL = os.environ.get("E_GEN", "anthropic/claude-sonnet-5")
VER_MODEL = os.environ.get("E_VER", "openai/gpt-6.1-terra")
GEN_EXTRA = {"anthropic/claude-sonnet-5": {"reasoning": {"enabled": False}},
             "openai/gpt-6.1-terra": {"reasoning": {"effort": "none"}},
             "google/gemini-3.7-flash": {"reasoning": {"effort": "minimal"}}}
PRICE = {"anthropic/claude-sonnet-5": (2.0, 10.0), "openai/gpt-6.1-terra": (1.0, 5.0), "google/gemini-3.7-flash": (.75, 3.75)}
N_CLEAN, N_SINGLE, N_MULTI = 7, 10, 3


def select(lang):
    items = [it for it in E.gold(lang)
             if len(SENT.split_sentences(it["reference"])) == len(SENT.split_sentences(it["reproduction"]))]
    rng = random.Random(20261114)
    out = []
    for kind, n in (("clean", N_CLEAN), ("single", N_SINGLE), ("multi", N_MULTI)):
        pool = [it for it in items if it["kind"] == kind]
        mi = [it for it in pool if any(e["subtype"] == "meaning_inversion" for e in it["expected_errors"])]
        rest = [it for it in pool if it not in mi]
        rng.shuffle(rest)
        out += (mi + rest)[:n]
    return out


def sents(item):
    r = SENT.split_sentences(item["reference"]); p = SENT.split_sentences(item["reproduction"])
    return r, p


def err_sentence(item, e):
    _, p = sents(item)
    for i, s in enumerate(p):
        if s.start <= e["span_repro"][0] < s.end:
            return i
    return len(p) - 1


GEN_SYS = """You are an expert {lang} writer and language teacher helping to build a test set for an automatic translation grader.

Context: learners translate a passage into {lang}. A REFERENCE translation exists, but real learners never see it. Write what a competent learner would plausibly produce: a FREE translation of the same content, where each sentence is expressed in a legitimately different way (different word order, synonyms, restructured or re-ordered clauses, other equally idiomatic constructions) yet is fully correct, natural and exactly equivalent in meaning.

Rules:
1. Output exactly one learner sentence per reference sentence, in the same order. Sentence i must carry exactly the content of reference sentence i: nothing added, nothing dropped, no change of meaning, tense, quantity, emphasis or polarity.
2. Each sentence must differ substantially from the reference wording (change well over a third of the words/characters), while a strict native-speaker teacher would find NOTHING to correct in it: no grammar slip, no odd collocation, no vaguer or stronger word, no unnatural phrasing.
3. Keep the register and politeness level of the reference (Japanese: です/ます vs plain style stays as in the reference; Chinese: same colloquial/written level; English: same neutral tone). Keep names, numbers, quoted and technical terms unchanged.
4. End each sentence with the same final punctuation mark as its reference sentence. No other sentence-ending punctuation (. ! ? 。！？) and no line break inside a sentence.
5. PLANTED ERRORS. Some sentences must carry a deliberate learner error, listed under ERRORS with the original wrong form and its correction. Your rewritten sentence must still contain THE SAME error: same error type, same wrong word/form/structure, same severity, still locally identifiable, so that replacing only the short erroneous fragment with its correction gives a fully correct sentence. Rephrase the rest of that sentence freely around it. Do not fix the error, do not soften it, do not add a second one. For each listed error report `fragment` (the short erroneous stretch copied VERBATIM from your sentence; include a word or two of context) and `corrected` (what that fragment should read). If an error truly cannot be kept once the sentence is rephrased (for example it depends on the exact original word order), set `kept` to false and copy the ORIGINAL LEARNER sentence unchanged for that sentence.
6. Sentences without a listed error must be completely error-free.
Return JSON only."""

NOSCHEMA = '\nJSON shape: {"sentences": ["...", ...], "errors": [{"error": 1, "kept": true, "fragment": "...", "corrected": "..."}]} ("errors" has one entry per listed error E1, E2...; empty list if none). No markdown fences.'
GEN_SCHEMA = {"name": "paraphrase", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["sentences", "errors"],
    "properties": {"sentences": {"type": "array", "items": {"type": "string"}},
                   "errors": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                              "required": ["error", "kept", "fragment", "corrected"],
                              "properties": {"error": {"type": "integer"}, "kept": {"type": "boolean"},
                                             "fragment": {"type": "string"}, "corrected": {"type": "string"}}}}}}}


def gen_body(item, lang):
    r, p = sents(item)
    lines = ["REFERENCE sentences:"] + [f"{i+1}. {s.text.strip()}" for i, s in enumerate(r)]
    errs = item["expected_errors"]
    if errs:
        idx = sorted({err_sentence(item, e) for e in errs})
        lines += ["", "ORIGINAL LEARNER sentences (only those with a planted error):"] + [f"{i+1}. {p[i].text.strip()}" for i in idx]
        lines += ["", "ERRORS:"]
        for k, e in enumerate(errs, 1):
            lines.append(f"E{k}: sentence {err_sentence(item, e)+1}; type {e['subtype']}; severity {e['severity_v2']}; "
                         f"wrong form \"{e.get('learner_form','')}\" -> correct form \"{e.get('corrected_form','')}\"")
        lines += ["", f"Note from the test author: {item.get('note','')}"]
    else:
        lines += ["", "ERRORS: none. Every sentence must be error-free."]
    body = {"model": GEN_MODEL, "messages": [{"role": "system", "content": GEN_SYS.format(lang=C.LANG_NAME[lang])},
                                             {"role": "user", "content": "\n".join(lines)}],
            "temperature": 0.7, "max_tokens": 800, "usage": {"include": True},
            "response_format": {"type": "json_schema", "json_schema": GEN_SCHEMA}}
    body.update(GEN_EXTRA.get(GEN_MODEL, {}))
    # the strict schema costs ~400 extra input tokens on this provider; the 6 smoke items were
    # generated with it and stay cached, all other items use a plain-JSON instruction instead
    if not os.path.exists(os.path.join(E.CACHE, C._key(body) + ".json")):
        body.pop("response_format")
        body["messages"][0]["content"] += NOSCHEMA
    return body


VER_SYS = """You are a meticulous native-speaker {lang} teacher auditing a test set. A learner translated a passage into {lang} WITHOUT seeing the REFERENCE translation, so wording, word order and sentence structure may legitimately differ. Correct, natural, meaning-equivalent alternative wording is NOT an error. Some learner sentences are supposed to contain one specific PLANTED error; everything else is supposed to be flawless.

For every sentence report:
- planted_ok: true if every planted error listed for that sentence is really present at the given fragment, is a genuine error of roughly the stated type, and replacing the fragment with the given correction makes the sentence correct. Also true when no planted error is listed for the sentence.
- other_error: describe ANY OTHER problem a strict teacher would mark in the learner sentence: grammar or form error, wrong or odd word/collocation, meaning that differs from the reference sentence (changed, added, omitted, weakened, strengthened), register/politeness mismatch with the reference, clearly unnatural phrasing. Use an empty string if there is none. Do not report stylistic preference or the mere fact that the wording differs.
- other_severity: none, minor or major.
Return JSON only."""
VER_SCHEMA = {"name": "audit", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["sentences"],
    "properties": {"sentences": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                   "required": ["sentence", "planted_ok", "other_error", "other_severity"],
                   "properties": {"sentence": {"type": "integer"}, "planted_ok": {"type": "boolean"},
                                  "other_error": {"type": "string"},
                                  "other_severity": {"type": "string", "enum": ["none", "minor", "major"]}}}}}}}


def ver_body(item, lang, g):
    r, _ = sents(item)
    lines = []
    for i, s in enumerate(r):
        lines.append(f"S{i+1} REF: {s.text.strip()}\nS{i+1} LRN: {g['sentences'][i].strip()}")
    pl = []
    for k, e in enumerate(item["expected_errors"]):
        ge = g["errors"][k]
        pl.append(f"- sentence {err_sentence(item, e)+1}: type {e['subtype']} ({e['severity_v2']}); fragment \"{ge['fragment']}\" should read \"{ge['corrected']}\"")
    lines += ["", "PLANTED errors:"] + (pl or ["none"])
    body = {"model": VER_MODEL, "messages": [{"role": "system", "content": VER_SYS.format(lang=C.LANG_NAME[lang])},
                                             {"role": "user", "content": "\n".join(lines)}],
            "temperature": 0, "max_tokens": 600, "usage": {"include": True},
            "response_format": {"type": "json_schema", "json_schema": VER_SCHEMA}}
    body.update(GEN_EXTRA.get(VER_MODEL, {}))
    return body


def parse_gen(item, rec):
    """-> normalised generation or None (structurally invalid)."""
    j = C._extract_json(rec.get("content"))
    if j is None and rec.get("content"):  # unescaped ASCII quotes inside a sentence (2 zh items): escape and retry
        import re
        j = C._extract_json(re.sub(r'([^\[\{,:\s\\])"(?=[^\]\},:\s])', r'\1\\"', rec["content"]))
    r, p = sents(item)
    if not isinstance(j, dict) or len(j.get("sentences", [])) != len(r):
        return None
    ss = [s.strip() for s in j["sentences"]]
    errs = item["expected_errors"]
    ge = {e.get("error"): e for e in j.get("errors", [])}
    out_e = []
    revert = set()
    for k, e in enumerate(errs, 1):
        si = err_sentence(item, e)
        x = ge.get(k)
        if x is None or not x.get("kept") or not x.get("fragment") or x["fragment"] not in ss[si]:
            revert.add(si); out_e.append({"fragment": "", "corrected": "", "kept": False})
        else:
            out_e.append({"fragment": x["fragment"], "corrected": x["corrected"], "kept": True})
    for i, s in enumerate(ss):  # structural: exactly one sentence each
        if len(SENT.split_sentences(s)) != 1:
            revert.add(i)
    for si in revert:
        ss[si] = p[si].text.strip()
    for k, e in enumerate(errs):
        if err_sentence(item, e) in revert:
            out_e[k] = {"fragment": e.get("learner_form", ""), "corrected": e.get("corrected_form", ""), "kept": False}
    return {"sentences": ss, "errors": out_e, "struct_revert": sorted(revert)}


def run(stage, limit=0):
    jobs = []
    for lang in E.LANGS:
        its = select(lang)
        if limit:
            its = [its[0], its[N_CLEAN], its[-1]][:limit]
        jobs += [(lang, it) for it in its]
    gens = {}

    def do_gen(j):
        lang, it = j
        rec = E.chat(gen_body(it, lang), {"stage": "gen", "item": it["id"]}, PRICE.get(GEN_MODEL))
        return it["id"], rec
    with ThreadPoolExecutor(6) as ex:
        for iid, rec in ex.map(do_gen, jobs):
            gens[iid] = rec
    out = {}
    for lang, it in jobs:
        rec = gens[it["id"]]
        g = parse_gen(it, rec) if rec.get("content") else None
        out[it["id"]] = {"lang": lang, "gen": g, "gen_err": rec.get("error"), "gen_usage": rec.get("usage"), "finish": rec.get("finish")}
    if stage == "verify":
        def do_ver(j):
            lang, it = j
            g = out[it["id"]]["gen"]
            if g is None:
                return it["id"], None
            return it["id"], E.chat(ver_body(it, lang, g), {"stage": "verify", "item": it["id"]}, PRICE.get(VER_MODEL))
        with ThreadPoolExecutor(6) as ex:
            for iid, rec in ex.map(do_ver, jobs):
                out[iid]["ver"] = C._extract_json(rec.get("content")) if rec else None
                out[iid]["ver_usage"] = rec.get("usage") if rec else None
                out[iid]["ver_err"] = rec.get("error") if rec else None
    json.dump(out, open(os.path.join(E.HERE, f"build_{stage}{'_smoke' if limit else ''}.json"), "w"), ensure_ascii=False, indent=1)
    return jobs, out


if __name__ == "__main__":
    stage = sys.argv[1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    before = E.spent()
    jobs, out = run(stage, limit)
    n = len(jobs)
    print(f"{stage}: items={n} gen_ok={sum(1 for v in out.values() if v['gen'])} new=${E.spent()-before:.4f} total=${E.spent():.4f}")
    gu = [v["gen_usage"] for v in out.values() if v.get("gen_usage")]
    print(" gen tok in/out/reason avg", sum(u.get("prompt_tokens") or 0 for u in gu)/max(1,len(gu)), sum(u.get("completion_tokens") or 0 for u in gu)/max(1,len(gu)),
          sum(u.get("reasoning_tokens") or 0 for u in gu)/max(1,len(gu)), "usd/item", sum(u.get("cost") or 0 for u in gu)/max(1,len(gu)))
    vu = [v["ver_usage"] for v in out.values() if v.get("ver_usage")]
    if vu:
        print(" ver tok in/out/reason avg", sum(u.get("prompt_tokens") or 0 for u in vu)/len(vu), sum(u.get("completion_tokens") or 0 for u in vu)/len(vu),
              sum(u.get("reasoning_tokens") or 0 for u in vu)/len(vu), "usd/item", sum(u.get("cost") or 0 for u in vu)/len(vu))
    for lang, it in jobs[:9] if limit else []:
        v = out[it["id"]]
        print("---", it["id"], v.get("gen_err"), v.get("finish"))
        if v["gen"]:
            r, p = sents(it)
            for i, s in enumerate(r):
                print("  REF", s.text.strip()); print("  NEW", v["gen"]["sentences"][i])
            print("  ERR", json.dumps(v["gen"]["errors"], ensure_ascii=False), v["gen"]["struct_revert"])
        if v.get("ver") or v.get("ver_err"):
            print("  VER", json.dumps(v.get("ver"), ensure_ascii=False), v.get("ver_err"))
