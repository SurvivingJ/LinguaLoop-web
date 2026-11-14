# -*- coding: utf-8 -*-
"""Stage-2 generative calls (cheap LLM): pair-level confirm/severity/explain and
item-level recall pass. Usage:
  python stage2.py pair  <model> <set> [--limit N] [--langs en,zh,ja]
  python stage2.py item  <model> <set> [--limit N]
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, json, os, re, sys
import common as C

A = C.load_sept()
S, SENT, T, R = A.S, A.SENT, A.T, A.S.R
LANGNAME = {"en": "English", "zh": "Chinese", "ja": "Japanese"}
OUT = os.path.join(C.HERE, "stage2")
os.makedirs(OUT, exist_ok=True)

SEV_TEXT = R.SEVERITY_CHOICE_LEVELS["en"]


def taxonomy_block(lang: str) -> str:
    lines = []
    for s in T.SUBTYPES[lang]:
        gloss = T.SUBTYPE_GLOSS[lang][s]
        lines.append(f"- {s} (usually {T.SUBTYPE_DEFAULT_SEVERITY.get(s, 'minor')}): {gloss}")
    return "\n".join(lines)


def system_prompt(lang: str, scope: str) -> str:
    unit = "one sentence" if scope == "pair" else "a short passage"
    return (
        f"You grade {unit} of a learner's translation into {LANGNAME[lang]} against a reference translation.\n"
        "Find every place where the learner text differs from the reference and decide whether it is a REAL error "
        "(grammar, wrong/unnatural word, missing or added meaning, wrong register, changed meaning) or an acceptable "
        "variation (true synonym, equally natural rephrasing, punctuation/spacing differences). Report only real "
        "errors, one entry per distinct error. Do not invent errors where the texts agree.\n\n"
        "Severity:\n"
        f"- minor: {SEV_TEXT['minor']}\n- major: {SEV_TEXT['major']}\n- critical: {SEV_TEXT['critical']}\n\n"
        "Error types (use the slug; the 'usually' severity is only a prior -- judge the actual case):\n"
        f"{taxonomy_block(lang)}\n\n"
        'Reply with JSON only: {"errors":[{"learner":"<exact erroneous learner text, or the words around a gap>",'
        '"correct":"<what the reference has>","type":"<slug>","severity":"minor|major|critical",'
        '"why":"<explanation for the learner, English, at most 20 words>"}]}. '
        'If there is no real error reply {"errors":[]}.'
    )


def pair_messages(lang, ref, learner):
    return [{"role": "system", "content": system_prompt(lang, "pair")},
            {"role": "user", "content": f"Reference sentence:\n{ref}\n\nLearner sentence:\n{learner}"}]


def item_messages(lang, ref, learner):
    return [{"role": "system", "content": system_prompt(lang, "item")},
            {"role": "user", "content": f"Reference passage:\n{ref}\n\nLearner passage:\n{learner}"}]


EXTRA = {
    "qwen/qwen3.7-flash": {"reasoning": {"enabled": False}, "response_format": {"type": "json_object"}},
    "deepseek/deepseek-v4.1-flash": {"reasoning": {"enabled": False}, "response_format": {"type": "json_object"}},
    "anthropic/claude-haiku-5.5": {"reasoning": {"enabled": False}},
}


def parse_errors(content: str, lang: str):
    """-> (list of error dicts, parse_ok)"""
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return [], False
    try:
        d = json.loads(m.group(0))
    except Exception:
        return [], False
    out = []
    for e in (d.get("errors") or []):
        if not isinstance(e, dict):
            continue
        sev = str(e.get("severity", "")).lower().strip()
        if sev not in ("minor", "major", "critical"):
            sev = "minor"
        st = str(e.get("type", "")).strip()
        if st not in T.SUBTYPES[lang]:
            st = "word_choice"  # unknown slug -> generic lexical bucket
        out.append({"learner": str(e.get("learner", "")), "correct": str(e.get("correct", "")),
                    "subtype": st, "severity": sev, "why": str(e.get("why", ""))})
    return out, True


def pair_jobs(lang: str, set_name: str):
    """All non-byte-identical sentence pairs (the same units jev A3 was called on)."""
    ref = A.load_reference(lang, set_name)
    jobs = []
    for iid, it in ref.items():
        res = SENT.build_sentence_pairs(it["reference"], it["reproduction"])
        for idx, pr in enumerate(res.pairs):
            if pr.ref.text == pr.repro.text:
                continue
            jobs.append({"item_id": iid, "pair_idx": idx, "ref": pr.ref.text, "learner": pr.repro.text})
    return jobs


def item_jobs(lang: str, set_name: str):
    ref = A.load_reference(lang, set_name)
    return [{"item_id": iid, "ref": it["reference"], "learner": it["reproduction"]}
            for iid, it in ref.items() if it["reference"] != it["reproduction"]]


def run(scope, model, set_name, langs, limit, conc=4):
    tot_new = 0.0
    for lang in langs:
        jobs = (pair_jobs if scope == "pair" else item_jobs)(lang, set_name)
        if limit:
            jobs = jobs[:limit]

        def do(j):
            msgs = (pair_messages if scope == "pair" else item_messages)(lang, j["ref"], j["learner"])
            r = C.chat(model, msgs, tag=f"{scope}:{set_name}:{lang}", max_tokens=350 if scope == "pair" else 600,
                       extra=EXTRA.get(model, {}))
            errs, ok = parse_errors(r["content"], lang)
            return {**{k: j[k] for k in j if k in ("item_id", "pair_idx")}, "errors": errs, "parse_ok": ok,
                    "usd": r["usd"], "latency_s": r["latency_s"], "usage": r["usage"], "cached": r["cached"],
                    "finish": r.get("finish"), "raw": r["content"] if not ok else None}

        with cf.ThreadPoolExecutor(conc) as ex:
            recs = list(ex.map(do, jobs))
        fn = os.path.join(OUT, f"{scope}_{model.replace('/', '__')}_{lang}_{set_name}.jsonl")
        if not limit:
            with open(fn, "w", encoding="utf-8") as f:
                for r in recs:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        new = sum(r["usd"] for r in recs if not r["cached"])
        tot_new += new
        n = len(recs)
        print(f"{scope} {model} {lang} {set_name}: n={n} parse_fail={sum(not r['parse_ok'] for r in recs)} "
              f"usd/call={sum(r['usd'] for r in recs)/max(n,1):.6f} new_usd={new:.5f} "
              f"lat_mean={sum(r['latency_s'] for r in recs)/max(n,1):.2f}s "
              f"reasoning_tok={sum((r['usage'].get('reasoning_tokens') or 0) for r in recs)} "
              f"ptok={sum((r['usage'].get('prompt_tokens') or 0) for r in recs)//max(n,1)} "
              f"ctok={sum((r['usage'].get('completion_tokens') or 0) for r in recs)//max(n,1)}")
        if limit:
            for r in recs[:limit]:
                print("   ", json.dumps(r["errors"], ensure_ascii=False)[:300], "| raw:", (r["raw"] or "")[:200])
    print(f"new spend this run ${tot_new:.5f}; cumulative ${C.spent():.5f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("scope", choices=("pair", "item"))
    ap.add_argument("model")
    ap.add_argument("set", choices=("silver", "gold"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--langs", default="en,zh,ja")
    a = ap.parse_args()
    run(a.scope, a.model, a.set, a.langs.split(","), a.limit)
