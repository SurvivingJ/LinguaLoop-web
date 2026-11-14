# -*- coding: utf-8 -*-
"""Track B harness: cheap generative LLMs as structured DT "decision" graders.

Everything shared lives here: data loading, v6 taxonomy, sentence pairing + diff
hunks, prompt/schema builders, the OpenRouter client (disk cache, cost ledger,
hard budget guard) and the decoder that turns a model answer into the error list
the live `services.dual_translation.scoring` consumes.

No DB access, no production code modified, nothing written outside this directory.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SEPT = os.path.join(REPO, "data", "eval", "jev_dt_2026-09-26")
sys.path.insert(0, REPO)
sys.path.append(SEPT)

import sentences as SENT  # noqa: E402  (Sept harness, imported read-only)

CACHE_DIR = os.path.join(HERE, "cache")
LEDGER = os.path.join(HERE, "costs.jsonl")
os.makedirs(CACHE_DIR, exist_ok=True)

BUDGET_STOP_USD = 0.50  # refuse to send once cumulative spend reaches this
LANG_NAME = {"en": "English", "zh": "Chinese (Mandarin, simplified)", "ja": "Japanese"}

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_set(which: str, lang: str) -> list[dict]:
    d = {"gold": "dt_gold_v6", "silver": "dt_silver_v6"}[which]
    with open(os.path.join(REPO, "tests", "fixtures", d, f"{lang}.json"), encoding="utf-8") as f:
        items = json.load(f)
    if which == "gold":  # keep the 30 v5-derived items so n matches earlier reports
        items = [it for it in items if "_v6_" not in it["id"]]
    return items


with open(os.path.join(REPO, "data", "eval", "taxonomy_merge_2026-09-27", "merged_taxonomy.json"),
          encoding="utf-8") as _f:
    TAX = json.load(_f)
TYPES = {l: [t["id"] for t in TAX[l]] for l in TAX}
SUBTYPE_META = {}
for _l in TAX:
    for _t in TAX[_l]:
        SUBTYPE_META.setdefault(_t["id"], {"dimension": _t["dimension"],
                                           "default_severity": _t["default_severity"]})

_MI_DEF = ("the learner text says the REVERSE of the reference: negation dropped/added, antonym, "
           "reversed direction, flipped quantity/comparison, swapped agent/patient (e.g. with -> without). "
           "Judge by effect, whatever the surface edit")


def short_def(t: dict) -> str:
    if t["id"] == "meaning_inversion":
        return _MI_DEF
    d = t["definition"]
    d = re.split(r"(?<!e\.g\.)(?<!i\.e\.)(?<=[.。])\s", d)[0]
    d = re.sub(r"\s*\(absorbs[^)]*\)", "", d).split(" — detectable")[0]
    return d[:200].rstrip(".")


def type_block(lang: str, with_default: bool = True) -> str:
    lines = []
    for t in TAX[lang]:
        nm = f" [{t['native_name']}]" if lang != "en" else ""
        dv = f" (usually {t['default_severity']})" if with_default else ""
        lines.append(f"- {t['id']}{nm}: {short_def(t)}{dv}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sentence pairs + diff hunks
# ---------------------------------------------------------------------------

def pairs_for(item: dict):
    return SENT.build_sentence_pairs(item["reference"], item["reproduction"]).pairs


def _tokens(text: str, lang: str):
    if lang == "en":
        return re.findall(r"\s+|\w+(?:'\w+)?|[^\w\s]", text)
    return list(text)


def diff_hunks(ref: str, lrn: str, lang: str) -> list[dict]:
    """Deterministic "evidence": non-equal diff blocks between a reference sentence and
    the learner sentence. Blocks separated by <=1 equal token (en: one word + spaces)
    are merged. Each hunk carries learner char offsets (relative to the sentence);
    zero-length learner fragments are widened by one token each side so every hunk has
    a visible learner span."""
    a, b = _tokens(ref, lang), _tokens(lrn, lang)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ops = [op for op in sm.get_opcodes()]
    blocks = []  # [i1,i2,j1,j2]
    for k, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag == "equal":
            continue
        if blocks:
            gap = a[blocks[-1][1]:i1]
            gap_words = [g for g in gap if not g.isspace()]
            if len(gap_words) <= 1:
                blocks[-1][1], blocks[-1][3] = i2, j2
                continue
        blocks.append([i1, i2, j1, j2])
    boff = [0]
    for t in b:
        boff.append(boff[-1] + len(t))
    out = []
    for i1, i2, j1, j2 in blocks:
        rf, lf = "".join(a[i1:i2]), "".join(b[j1:j2])
        if not rf.strip() and not lf.strip():
            continue  # whitespace-only
        jj1, jj2 = j1, j2
        if lang != "en":  # CJK: show one character of context each side (す=>した -> ます=>ました)
            if i1 > 0 and j1 > 0 and a[i1 - 1] == b[j1 - 1] and not a[i1 - 1].isspace():
                i1, j1, jj1 = i1 - 1, j1 - 1, j1 - 1
            if i2 < len(a) and j2 < len(b) and a[i2] == b[j2] and not a[i2].isspace():
                i2, j2, jj2 = i2 + 1, j2 + 1, j2 + 1
            rf, lf = "".join(a[i1:i2]), "".join(b[j1:j2])
        if not lf.strip():  # deletion: widen to neighbours for a visible span
            jj1 = max(0, j1 - 2)
            jj2 = min(len(b), j2 + 2)
        out.append({"ref": rf.strip(), "lrn": lf.strip(), "start": boff[jj1], "end": boff[jj2]})
    return out


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SEVERITY_RUBRIC = """Severity (reader-impact, judged as a native reader):
- minor: a small slip a native reader notices but reads straight past (slightly off form or near-synonym).
- major: CLEARLY WRONG to a native reader - an ungrammatical or plainly incorrect form, particle, word or order - EVEN IF the intended meaning is still obvious. "Major" does NOT require a change of meaning.
- critical: the meaning breaks or is reversed, so the reader is misled (e.g. negation flipped, antonym, with -> without)."""

NOT_ERRORS = """NOT errors (never report): true synonyms and equally good rewordings, contractions, kana/kanji or simplified/variant spellings of the same word, optional commas and punctuation, spacing. A learner sentence may differ from the reference and still be correct."""


def system_p1(lang: str, level: str) -> str:
    """Design 1: one call per item, all sentence pairs, model finds the errors itself.
    level: bare (type+severity) | span (+ learner span) | expl (+ span + explanation)."""
    fields = {
        "bare": "the sentence number, the error type and the severity",
        "span": "the sentence number, the exact offending learner text (copied verbatim from LRN, as short as possible), the error type and the severity",
        "expl": "the sentence number, the exact offending learner text (copied verbatim from LRN, as short as possible), the error type, the severity and an explanation for the learner, in English, of at most 15 words",
    }[level]
    return f"""You grade a learner's {LANG_NAME[lang]} translation against a reference translation of the same passage. Sentences are paired: REF is the reference, LRN is the learner's version. "SAME" means the learner sentence is identical to the reference.

Find every translation error in the LRN sentences. For each error give {fields}. One entry per distinct error; a sentence can have several. If there are no errors return an empty list.

{NOT_ERRORS}

Error types (pick exactly one id per error):
{type_block(lang)}

{SEVERITY_RUBRIC}
The "(usually ...)" hint is the typical severity for that type; override it when the reader impact differs."""


def system_p2(lang: str) -> str:
    """Design 2: minimal-token evidence-first. Python computes the differences; the
    model only rules on each numbered difference."""
    return f"""A learner translated a passage into {LANG_NAME[lang]}. Only the sentences that differ from the reference are shown (REF = reference, LRN = learner). Each numbered difference D# is "reference text => learner text" ("∅" = nothing).

For EVERY D# decide: is the learner's version an error? Answer type "ok" (severity "none") if it is acceptable; otherwise give the error type id and severity. If several D# are parts of one single error (e.g. one phrase moved), label the first and answer "ok" for the rest.

{NOT_ERRORS}

Error types:
{type_block(lang)}

{SEVERITY_RUBRIC}"""


def user_p1(item: dict, lang: str) -> str:
    out = []
    for n, pr in enumerate(pairs_for(item), 1):
        r, l = pr.ref.text.strip(), pr.repro.text.strip()
        if r == l:
            out.append(f"S{n} SAME: {r}")
        else:
            out.append(f"S{n} REF: {r}\nS{n} LRN: {l}")
    return "\n".join(out)


def p2_units(item: dict, lang: str) -> list[dict]:
    """Flat numbered list of diff hunks with absolute learner offsets."""
    units = []
    for n, pr in enumerate(pairs_for(item), 1):
        if pr.ref.text.strip() == pr.repro.text.strip():
            continue
        for h in diff_hunks(pr.ref.text, pr.repro.text, lang):
            units.append({"d": len(units) + 1, "sent": n, "ref": h["ref"], "lrn": h["lrn"],
                          "span": [pr.repro.start + h["start"], pr.repro.start + h["end"]]})
    return units


def user_p2(item: dict, lang: str) -> str:
    units = p2_units(item, lang)
    out = []
    for n, pr in enumerate(pairs_for(item), 1):
        mine = [u for u in units if u["sent"] == n]
        if not mine:
            continue
        out.append(f"REF: {pr.ref.text.strip()}\nLRN: {pr.repro.text.strip()}")
        for u in mine:
            out.append(f"D{u['d']}: {u['ref'] or '∅'} => {u['lrn'] or '∅'}")
    return "\n".join(out)


SEVS = ["minor", "major", "critical"]


def schema(lang: str, variant: str) -> dict:
    if variant == "p2":
        props = {"d": {"type": "integer"},
                 "type": {"type": "string", "enum": ["ok"] + TYPES[lang]},
                 "severity": {"type": "string", "enum": ["none"] + SEVS}}
        key = "decisions"
    else:
        props = {"sentence": {"type": "integer"}}
        if variant in ("p1_span", "p1_expl"):
            props["span"] = {"type": "string"}
        props["type"] = {"type": "string", "enum": TYPES[lang]}
        props["severity"] = {"type": "string", "enum": SEVS}
        if variant == "p1_expl":
            props["explanation"] = {"type": "string"}
        key = "errors"
    return {"name": "dt_decisions", "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "required": [key],
        "properties": {key: {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": list(props), "properties": props}}}}}


MAX_TOKENS = {"p1_bare": 300, "p1_span": 400, "p1_expl": 600, "p2": 300}


def build_request(model: str, item: dict, lang: str, variant: str, extra: dict | None = None) -> dict | None:
    if variant == "p2":
        if not p2_units(item, lang):
            return None  # nothing differs -> clean without a call
        sys_msg, usr = system_p2(lang), user_p2(item, lang)
    else:
        sys_msg, usr = system_p1(lang, variant.split("_")[1]), user_p1(item, lang)
    body = {
        "model": model,
        "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": usr}],
        "temperature": 0,
        "max_tokens": MAX_TOKENS[variant],
        "response_format": {"type": "json_schema", "json_schema": schema(lang, variant)},
        "usage": {"include": True},
    }
    body.update(extra or {})
    return body


# ---------------------------------------------------------------------------
# OpenRouter client: cache + ledger + budget guard
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_spent = None


def spent() -> float:
    """Cumulative USD from the ledger. Re-read on every call so parallel processes
    share one budget view."""
    tot = 0.0
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    tot += json.loads(line).get("usd", 0.0)
    return tot


class BudgetExceeded(RuntimeError):
    pass


def _key(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def call(body: dict, tag: dict, price: tuple[float, float] | None = None, retries: int = 2) -> dict:
    """Returns {"content": str|None, "usage": {...}, "latency": s, "cached": bool, "error": str|None}."""
    global _spent
    import requests
    k = _key(body)
    path = os.path.join(CACHE_DIR, k + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        rec["cached"] = True
        return rec
    last_err = None
    for attempt in range(retries + 1):
        with _lock:
            if spent() >= BUDGET_STOP_USD:
                raise BudgetExceeded(f"spend ${spent():.4f} >= ${BUDGET_STOP_USD}")
        t0 = time.time()
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                              headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API"],
                                       "Content-Type": "application/json"},
                              data=json.dumps(body, ensure_ascii=False).encode(), timeout=90)
            lat = time.time() - t0
            j = r.json()
        except Exception as e:  # network / decode
            last_err = f"{type(e).__name__}: {str(e)[:200]}"
            time.sleep(2)
            continue
        if "choices" not in j:
            last_err = json.dumps(j.get("error", j), ensure_ascii=False)[:400]
            if r.status_code in (400, 401, 402, 403, 404):
                break
            time.sleep(2 + 3 * attempt)
            continue
        u = j.get("usage") or {}
        usd = u.get("cost")
        if usd is None:
            if price is None:
                usd = 0.0
            else:
                usd = (u.get("prompt_tokens", 0) * price[0] + u.get("completion_tokens", 0) * price[1]) / 1e6
        msg = j["choices"][0]["message"]
        rec = {"content": msg.get("content"), "finish": j["choices"][0].get("finish_reason"),
               "usage": {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                         "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                         "cost": usd},
               "provider": j.get("provider"), "latency": lat, "error": None}
        with _lock:
            with open(LEDGER, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": round(time.time(), 1), **tag, "model": body["model"],
                                    "prompt_tokens": u.get("prompt_tokens"),
                                    "completion_tokens": u.get("completion_tokens"),
                                    "reasoning_tokens": rec["usage"]["reasoning_tokens"],
                                    "usd": usd, "usd_source": "usage.cost" if u.get("cost") is not None else "list_price",
                                    "latency_s": round(lat, 3), "provider": j.get("provider"), "hash": k[:16]}) + "\n")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False)
        rec["cached"] = False
        return rec
    return {"content": None, "usage": {}, "latency": None, "cached": False, "error": last_err}


# ---------------------------------------------------------------------------
# Decoding model answers -> error list
# ---------------------------------------------------------------------------

def _extract_json(text: str):
    if text is None:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        return None


def decode(item: dict, lang: str, variant: str, content: str | None) -> dict:
    """-> {"valid": bool, "errors": [{span:[s,e], subtype, severity, ...}], "span_miss": n}"""
    j = _extract_json(content)
    key = "decisions" if variant == "p2" else "errors"
    if not isinstance(j, dict) or not isinstance(j.get(key), list):
        return {"valid": False, "errors": [], "span_miss": 0}
    pairs = pairs_for(item)
    repro = item["reproduction"]
    errs, miss, valid = [], 0, True
    if variant == "p2":
        units = {u["d"]: u for u in p2_units(item, lang)}
        seen_wo = set()
        for d in j[key]:
            if not isinstance(d, dict) or d.get("type") in (None, "ok"):
                continue
            u = units.get(d.get("d"))
            if u is None or d["type"] not in TYPES[lang]:
                valid = False
                continue
            sev = d.get("severity") if d.get("severity") in SEVS else SUBTYPE_META[d["type"]]["default_severity"]
            if d["type"] == "word_order":  # a moved phrase = two hunks; count once per sentence
                if u["sent"] in seen_wo:
                    continue
                seen_wo.add(u["sent"])
            errs.append({"span": u["span"], "subtype": d["type"], "severity": sev, "sentence": u["sent"],
                         "learner_text": repro[u["span"][0]:u["span"][1]], "ref_frag": u["ref"], "lrn_frag": u["lrn"]})
        return {"valid": valid, "errors": errs, "span_miss": 0}
    for e in j[key]:
        if not isinstance(e, dict) or e.get("type") not in TYPES[lang] or e.get("severity") not in SEVS:
            valid = False
            continue
        n = e.get("sentence")
        pr = pairs[n - 1] if isinstance(n, int) and 1 <= n <= len(pairs) else None
        span = None
        s = (e.get("span") or "").strip()
        if s:
            if pr is not None:
                i = repro.find(s, pr.repro.start, pr.repro.end)
                if i >= 0:
                    span = [i, i + len(s)]
            if span is None:
                i = repro.find(s)
                if i >= 0:
                    span = [i, i + len(s)]
        if span is None:
            if variant != "p1_bare":
                miss += 1
            span = [pr.repro.start, pr.repro.end] if pr is not None else [0, len(repro)]
        rec = {"span": span, "subtype": e["type"], "severity": e["severity"], "sentence": n,
               "learner_text": repro[span[0]:span[1]]}
        if "explanation" in e:
            rec["explanation"] = e["explanation"]
        errs.append(rec)
    return {"valid": valid, "errors": errs, "span_miss": miss}
