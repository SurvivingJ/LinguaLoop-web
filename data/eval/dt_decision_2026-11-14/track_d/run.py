# -*- coding: utf-8 -*-
"""Track D — DT feedback generation quality vs cost. Usage:
    python run.py gen   [--smoke]     generate G1-G3 feedback (cached)
    python run.py judge [--smoke] [--judges a,b]
    python run.py project             print cost so far
Budget guard: refuses to send once ledger + in-flight reservations >= $0.50.
Never prints the API key.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import random
import sys
import threading
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
from services.dual_translation import prompts as live_prompts  # noqa: E402
import g0_templates as g0  # noqa: E402

URL = "https://openrouter.ai/api/v1/chat/completions"
LEDGER = os.path.join(HERE, "costs.jsonl")
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)
HARD_STOP = 0.50
RESERVE = 0.012  # pessimistic per-call in-flight reservation

GENS = {"G1": "qwen/qwen3.7-flash", "G2": "deepseek/deepseek-v4.1-flash", "G3": "openai/gpt-6-luna"}
JUDGES = {"J1": "anthropic/claude-haiku-5.5", "J2": "google/gemini-3.6-flash"}
STYLES = ["direct", "meta", "hint", "app", "summary"]
LANG = {"en": "English", "zh": "Chinese", "ja": "Japanese"}

TAX = json.load(open(os.path.join(HERE, "taxonomy_v6_live.json"), encoding="utf-8"))
PRICES = {m["id"]: m["pricing"] for m in json.load(open(os.path.join(HERE, "models.json")))["data"]}

_lock = threading.Lock()
_inflight = 0.0


def spent():
    if not os.path.exists(LEDGER):
        return 0.0
    return sum(json.loads(l)["cost_usd"] for l in open(LEDGER) if l.strip())


class BudgetExceeded(RuntimeError):
    pass


def call(model, system, user, max_tokens, tag, extra=None):
    """Cached, ledgered, budget-guarded chat call. Returns dict(text, usage, latency_s, cached)."""
    global _inflight
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens, "temperature": 0, "usage": {"include": True}}
    body.update(extra or {})
    key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path):
        d = json.load(open(path, encoding="utf-8"))
        d["cached"] = True
        return d
    with _lock:
        if spent() + _inflight >= HARD_STOP:
            raise BudgetExceeded(f"budget guard: spent {spent():.4f} + inflight {_inflight:.4f} >= {HARD_STOP}")
        _inflight += RESERVE
    try:
        last = None
        for attempt in range(4):
            t0 = time.monotonic()
            try:
                r = requests.post(URL, json=body, timeout=120, headers={
                    "Authorization": "Bearer " + os.environ["OPENROUTER_API"], "Content-Type": "application/json"})
            except requests.RequestException as exc:
                last = f"network: {type(exc).__name__}"
                time.sleep(2 * (attempt + 1))
                continue
            lat = time.monotonic() - t0
            if r.status_code in (429, 500, 502, 503, 524, 529):
                last = f"http {r.status_code}"
                time.sleep(3 * (attempt + 1))
                continue
            if r.status_code != 200:
                raise RuntimeError(f"{model} http {r.status_code}: {r.text[:300]}")
            j = r.json()
            if "choices" not in j:
                last = "no choices: " + json.dumps(j)[:200]
                time.sleep(2)
                continue
            u = j.get("usage") or {}
            cost = u.get("cost")
            if cost is None:
                p = PRICES.get(model, {})
                cost = u.get("prompt_tokens", 0) * float(p.get("prompt", 0)) + u.get("completion_tokens", 0) * float(p.get("completion", 0))
            msg = j["choices"][0]["message"]
            d = {"text": msg.get("content") or "", "usage": u, "latency_s": round(lat, 3), "model": model, "tag": tag,
                 "finish": j["choices"][0].get("finish_reason"), "cost_usd": cost}
            with _lock:
                with open(LEDGER, "a") as f:
                    f.write(json.dumps({"ts": time.time(), "tag": tag, "model": model,
                                        "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                                        "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                                        "cost_usd": cost, "cost_source": "usage.cost" if u.get("cost") is not None else "list_price",
                                        "latency_s": round(lat, 3), "cache_key": key}) + "\n")
            json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
            d["cached"] = False
            return d
        raise RuntimeError(f"{model} failed after retries: {last}")
    finally:
        with _lock:
            _inflight -= RESERVE


def parse_json(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    a, b = t.find("{"), t.rfind("}")
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


# ------------------------------------------------------------------ items
def select_items():
    """15 per L2: 3 clean, 5 multi, 7 singles chosen greedily for subtype coverage."""
    out = []
    for l2 in ("en", "zh", "ja"):
        d = json.load(open(os.path.join(REPO, "tests/fixtures/dt_gold_v6", l2 + ".json"), encoding="utf-8"))
        clean = [x for x in d if x["kind"] == "clean"][:3]
        multi = [x for x in d if x["kind"] == "multi"]
        seen = {e["subtype"] for x in multi for e in x["expected_errors"]}
        singles, pool = [], [x for x in d if x["kind"] == "single"]
        for novel in (True, False):
            for x in pool:
                if len(singles) >= 7 or x in singles:
                    continue
                st = x["expected_errors"][0]["subtype"]
                if (st not in seen) == novel:
                    singles.append(x)
                    seen.add(st)
        for n, x in enumerate(clean + singles + multi):
            x = dict(x)
            x["l2"] = l2
            x["l1"] = "en" if l2 != "en" else ("zh" if n % 2 == 0 else "ja")
            out.append(x)
    return out


def live_rule(e, l1):
    """The live v6 Rule-layer template (what production shows with no Explainer)."""
    v = e.get("explanation_variant")
    t = None
    if v:
        t = (((TAX.get("variant_templates") or {}).get(e["subtype"]) or {}).get(v) or {}).get(l1)
    t = t or TAX["templates"][e["subtype"]][l1]
    return t.format(learner_form=e["learner_form"], corrected_form=e["corrected_form"])


def gloss(st, l1="en"):
    return TAX["subtype_glosses"][st][l1]


# ------------------------------------------------------------------ generation
COMMON = ("You write feedback for a language learner. Their native language is {L1}; they are learning {L2} and "
          "translated a short passage into {L2}. Write ALL feedback in {L1} (quote {L2} words exactly as written). "
          "You receive the reference passage, the learner's version, and a numbered list of CONFIRMED errors "
          "(learner form, corrected form, error type, severity). The list is final: do not add, drop or dispute errors. "
          "No scores. Write so a motivated teenager understands. ")
STYLE_SYS = {
    "direct": COMMON + "For each error give a DIRECT CORRECTION only: the wrong form and the corrected form as 'X → Y', "
              "plus at most 8 words naming what changed. No rule explanation. "
              'Output ONLY JSON: {{"feedback":[{{"i":0,"text":"..."}}]}} with one entry per error.',
    "meta": COMMON + "For each error give a METALINGUISTIC EXPLANATION: state the rule of {L2} that was broken, as it applies "
            "to this sentence, in at most 25 words (at most 50 characters if writing Chinese or Japanese). You may quote the "
            "learner's wrong words, but you MUST NOT give the corrected form or otherwise reveal the answer. "
            'Output ONLY JSON: {{"feedback":[{{"i":0,"text":"..."}}]}} with one entry per error.',
    "hint": COMMON + "For each error write one ELICITATION HINT: a short question or prompt (at most 25 words; at most 50 "
            "characters if writing Chinese or Japanese) that points the learner to the problem spot and leads them to "
            "correct it themselves. You MUST NOT state the corrected form or otherwise reveal the answer. "
            'Output ONLY JSON: {{"feedback":[{{"i":0,"text":"..."}}]}} with one entry per error.',
    "summary": COMMON + "Write a 1-2 sentence SUMMARY of this attempt (at most 40 words; at most 80 characters if writing "
               "Chinese or Japanese): name one genuine, specific strength of the learner's version, then the single most "
               "important thing to fix (the error that most damages the meaning). If the error list is empty the attempt "
               "is fully correct: say so and name one specific strength; any differences from the reference are acceptable "
               "variations, so do not invent problems or suggestions. "
               'Output ONLY JSON: {{"summary":"..."}}',
}
MAXTOK = {"direct": 400, "meta": 500, "hint": 500, "app": 600, "summary": 250}
NO_REASON = {"reasoning": {"enabled": False}}


def gen_prompts(item, style):
    l1, l2 = item["l1"], item["l2"]
    errs = item["expected_errors"]
    if style == "app":  # the LIVE Explainer prompt, verbatim builders
        numbered = []
        for i, e in enumerate(errs):
            n = {"i": i, "learner_form": e["learner_form"], "corrected_form": e["corrected_form"],
                 "type": gloss(e["subtype"], l1), "rule": live_rule(e, l1)}
            if e.get("explanation_variant"):
                n["variant"] = e["explanation_variant"]
            numbered.append(n)
        sysm = live_prompts.build_explainer_system_prompt(l1, variants=any("variant" in n for n in numbered))
        return sysm, live_prompts.build_explainer_user_prompt(l1, item["reference"], item["reproduction"], numbered)
    sysm = STYLE_SYS[style].format(L1=LANG[l1], L2=LANG[l2])
    numbered = []
    for i, e in enumerate(errs):
        n = {"i": i, "learner_form": e["learner_form"], "corrected_form": e["corrected_form"],
             "type": gloss(e["subtype"]), "severity": e["severity_v2"]}
        if e.get("explanation_variant"):
            n["variant"] = e["explanation_variant"]
        numbered.append(n)
    user = "\n".join(["REFERENCE: " + item["reference"], "LEARNER: " + item["reproduction"],
                      "CONFIRMED ERRORS: " + json.dumps(numbered, ensure_ascii=False)])
    return sysm, user


def gen_one(g, item, style):
    sysm, user = gen_prompts(item, style)
    r = call(GENS[g], sysm, user, MAXTOK[style], f"gen/{g}/{style}/{item['id']}", NO_REASON)
    p = parse_json(r["text"]) or {}
    n = len(item["expected_errors"])
    texts = [None] * n
    if style == "summary":
        texts = p.get("summary") if isinstance(p.get("summary"), str) else None
    else:
        arr = p.get("explanations" if style == "app" else "feedback") or []
        for x in arr if isinstance(arr, list) else []:
            if not isinstance(x, dict):
                continue
            i = x.get("error_index" if style == "app" else "i")
            if isinstance(i, int) and 0 <= i < n and isinstance(x.get("text"), str):
                texts[i] = x["text"].strip()
    return {"gen": g, "style": style, "item": item["id"], "texts": texts, "latency_s": r["latency_s"],
            "cost_usd": r["cost_usd"], "usage": r["usage"], "raw": r["text"], "finish": r.get("finish")}


def run_gen(items):
    jobs = [(g, it, s) for g in GENS for it in items for s in STYLES if s == "summary" or it["expected_errors"]]
    res = []
    with cf.ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(gen_one, *j) for j in jobs]
        for f in futs:
            res.append(f.result())
    return res


# ------------------------------------------------------------------ samples
def build_samples(items, gen_res):
    """One row per (item, error|None, generator, style) -> feedback text."""
    by = {(r["gen"], r["style"], r["item"]): r for r in gen_res}
    rows = []
    for it in items:
        l1, errs = it["l1"], it["expected_errors"]

        def add(gen, style, ei, text, lat=0.0, cost=0.0):
            e = errs[ei] if ei is not None else None
            rows.append({"item": it["id"], "l2": it["l2"], "l1": l1, "kind": it["kind"], "error_index": ei,
                         "subtype": e and e["subtype"], "severity": e and e["severity_v2"],
                         "learner_form": e and e["learner_form"], "corrected_form": e and e["corrected_form"],
                         "generator": gen, "model": GENS.get(gen, "template"), "style": style, "text": text,
                         "call_latency_s": lat, "call_cost_usd": cost})
        for ei, e in enumerate(errs):
            for s in ("direct", "meta", "hint"):
                add("G0", s, ei, g0.render_error(s, e["subtype"], l1, e["learner_form"], e["corrected_form"]))
            add("G0live", "app", ei, live_rule(e, l1))
        add("G0", "summary", None, g0.render_summary(l1, errs))
        for g in GENS:
            for s in STYLES:
                r = by.get((g, s, it["id"]))
                if not r:
                    continue
                if s == "summary":
                    add(g, s, None, r["texts"], r["latency_s"], r["cost_usd"])
                else:
                    for ei in range(len(errs)):
                        add(g, s, ei, r["texts"][ei], r["latency_s"], r["cost_usd"])
    return rows


# ------------------------------------------------------------------ judging
JUDGE_SYS = """You are an expert teacher of English, Chinese and Japanese as foreign languages, auditing feedback shown to a learner after a translation exercise. You get the reference passage, the learner's version, the GOLD (human-adjudicated, authoritative) error list, and a list of feedback texts to rate. Texts come from different anonymous systems; rate each independently and strictly. The feedback should be written in the learner's native language (L1).

Styles:
- direct: a bare correction "X → Y" (the answer SHOULD be given).
- meta: a rule explanation that must NOT reveal the corrected form.
- hint: a question/prompt leading to self-correction that must NOT reveal the corrected form.
- explain: an explanation of why the correction is right (the answer may be given).
- summary: 1-2 sentences for the whole attempt: one strength + the single most important fix (or, if GOLD has no errors, that nothing needs fixing).

Rate each text on:
c (factual correctness) 2 = every claim about the language is true AND it matches the gold error (for summary: consistent with the gold list; invents nothing); 1 = imprecise, over-general or slightly off but would not mislead; 0 = a false claim about the language, a wrong/mismatched description of this error, a wrong correction, an invented error, or (clean attempt) implying something needs fixing.
k (answer leak) 1 = the text states the corrected form or makes the answer trivially obvious (e.g. names the exact missing word); else 0. Rate for every style.
s (specificity) 2 = clearly about this sentence's actual words; 1 = partly; 0 = generic, could be pasted under any error of the type.
r (clarity for a motivated teenager, in the right L1) 2 = clear; 1 = understandable with effort / jargon-heavy; 0 = confusing, or not written in the L1.
t (tone) 2 = neutral-supportive; 1 = slightly off (cold, gushing, wordy preamble); 0 = harsh, patronising or inappropriate.
u (would the learner learn from it?) 2 = yes, real learning value for its style; 1 = some; 0 = none or harmful.
n = a note of at most 15 words, in English, ONLY when c<2 (say what is wrong); otherwise "".

Output ONLY JSON, one array per text, in the given order: {"j":[["<id>",c,k,s,r,t,u,"n"],...]}"""
JSTYLE = {"app": "explain"}


def judge_payload(item, samples, seed):
    rng = random.Random(seed)
    errs = item["expected_errors"]
    gold = [{"i": i, "learner_form": e["learner_form"], "corrected_form": e["corrected_form"],
             "type": gloss(e["subtype"]).split(" — ")[0] + " (" + e["subtype"] + ")", "severity": e["severity_v2"]}
            for i, e in enumerate(errs)]
    mine = [s for s in samples if s["item"] == item["id"] and isinstance(s["text"], str) and s["text"].strip()]
    groups = {}
    for s in mine:
        groups.setdefault(s["error_index"] if s["error_index"] is not None else 99, []).append(s)
    ordered = []
    for k in sorted(groups):
        g = groups[k]
        rng.shuffle(g)
        ordered += g
    idmap, lines = {}, []
    for n, s in enumerate(ordered):
        tid = f"t{n:02d}"
        idmap[tid] = (s["generator"], s["style"], s["error_index"])
        lines.append(json.dumps({"id": tid, "error": s["error_index"], "style": JSTYLE.get(s["style"], s["style"]),
                                 "text": s["text"]}, ensure_ascii=False))
    user = "\n".join([
        f"L2 (language being learned): {LANG[item['l2']]}   L1 (feedback language): {LANG[item['l1']]}",
        "REFERENCE: " + item["reference"], "LEARNER: " + item["reproduction"],
        "GOLD ERRORS: " + (json.dumps(gold, ensure_ascii=False) if gold else "[]  (clean attempt: fully acceptable)"),
        "ANNOTATOR NOTE: " + (item.get("note") or ""),
        f"FEEDBACK TEXTS ({len(lines)}):"] + lines)
    return user, idmap


def judge_one(j, item, samples):
    user, idmap = judge_payload(item, samples, seed=hash((item["id"], 7)) & 0xffff if False else int(hashlib.md5(item["id"].encode()).hexdigest()[:6], 16))
    extra = {"reasoning": {"enabled": False}} if j == "J1" else {"reasoning": {"effort": "minimal"}}
    r = call(JUDGES[j], JUDGE_SYS, user, 60 + 48 * len(idmap), f"judge/{j}/{item['id']}", extra)
    p = parse_json(r["text"]) or {}
    out = []
    for row in p.get("j") or []:
        if isinstance(row, list) and len(row) >= 7 and row[0] in idmap:
            g, s, ei = idmap[row[0]]
            try:
                vals = [int(v) for v in row[1:7]]
            except Exception:
                continue
            out.append({"judge": j, "item": item["id"], "generator": g, "style": s, "error_index": ei,
                        "c": vals[0], "k": vals[1], "s": vals[2], "r": vals[3], "t": vals[4], "u": vals[5],
                        "note": row[7] if len(row) > 7 else ""})
    return {"judge": j, "item": item["id"], "n_expected": len(idmap), "rows": out, "cost_usd": r["cost_usd"],
            "latency_s": r["latency_s"], "finish": r.get("finish"), "usage": r["usage"]}


def main():
    cmd = sys.argv[1]
    smoke = "--smoke" in sys.argv
    items = select_items()
    if smoke:
        ids = ["en_seed_01", "zh_multi_02", "ja_multi_01", "ja_clean_01", "en_multi_02"]
        items = [x for x in items if x["id"] in ids]
    if cmd == "project":
        print(f"spent ${spent():.4f}")
        return
    before = spent()
    gen_res = run_gen(items)
    samples = build_samples(items, gen_res)
    if cmd == "gen":
        bad = [(r["gen"], r["style"], r["item"], r["finish"]) for r in gen_res
               if r["texts"] is None or (isinstance(r["texts"], list) and None in r["texts"])]
        print("gen calls", len(gen_res), "incomplete", len(bad), bad[:12])
        for g in GENS:
            rs = [r for r in gen_res if r["gen"] == g]
            print(g, GENS[g], "cost", round(sum(r["cost_usd"] for r in rs), 5), "median lat",
                  sorted(r["latency_s"] for r in rs)[len(rs) // 2],
                  "reasoning toks", sum(((r["usage"].get("completion_tokens_details") or {}).get("reasoning_tokens") or 0) for r in rs))
        if not smoke:
            json.dump(gen_res, open(os.path.join(HERE, "gen_raw.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
            with open(os.path.join(HERE, "feedback_samples.jsonl"), "w", encoding="utf-8") as f:
                for s in samples:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
        else:
            for s in samples:
                if s["item"] in ("zh_multi_02", "ja_clean_01", "en_seed_01") and s["error_index"] in (None, 0):
                    print(s["item"], s["generator"], s["style"], "|", s["text"])
    elif cmd == "judge":
        js = [a for a in sys.argv if a.startswith("--judges=")]
        js = js[0].split("=")[1].split(",") if js else list(JUDGES)
        res = []
        with cf.ThreadPoolExecutor(6) as ex:
            futs = [ex.submit(judge_one, j, it, samples) for j in js for it in items]
            for f in futs:
                res.append(f.result())
        for j in js:
            rs = [r for r in res if r["judge"] == j]
            print(j, JUDGES[j], "calls", len(rs), "cost", round(sum(r["cost_usd"] for r in rs), 4),
                  "parsed", sum(len(r["rows"]) for r in rs), "/", sum(r["n_expected"] for r in rs),
                  "finish", {r["finish"] for r in rs},
                  "reasoning", sum(((r["usage"].get("completion_tokens_details") or {}).get("reasoning_tokens") or 0) for r in rs),
                  "tok in/out", sum(r["usage"].get("prompt_tokens", 0) for r in rs), sum(r["usage"].get("completion_tokens", 0) for r in rs))
        if not smoke:
            json.dump(res, open(os.path.join(HERE, "judge_raw.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"spend this run ${spent() - before:.4f}; total ${spent():.4f}")


if __name__ == "__main__":
    main()
