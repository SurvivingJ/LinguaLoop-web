"""Adjudicated entailment gold (TASK-834): pool, blind packets, scoring.

The structural gold (answer = 1, distractor = 0) cannot tell "jev right, the
distractor was valid" from "jev wrong". This builds a small set labelled by
independent adjudicators who see ONLY passage + question + candidates -- never
either judge's verdict, the structural label, or which candidate was the answer.

Strata (both are needed):
  D  every item where the live judge and jev disagree -- who is right when they
     differ. Over-weights hard items, so its rates are not population rates.
  A  a random sample of items where they AGREE -- the only way to see errors the
     two judges share.

Adjudicator labels: ``yes`` (the passage states this answer, or it is the
uniquely inferable answer), ``no`` (unsupported, merely on-topic, or
contradicted), ``unclear`` (partial / arguable). They map onto the judges'
verdicts: yes~accept, unclear~flag, no~reject.

    PYTHONPATH=. python scripts/entailment_adjudication.py pool
    PYTHONPATH=. python scripts/entailment_adjudication.py tiebreak
    PYTHONPATH=. python scripts/entailment_adjudication.py score
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from services.exercise_generation.judges.answer_entailment_jev import (  # noqa: E402
    CUTOFFS, probability_to_verdict,
)

CAL = os.path.join(ROOT, "data/eval/jev_entailment_calibration_2026-09-26/jev_vs_live.json")
WIN_DIR = os.path.join(ROOT, "data/eval/entailment_shadow_window_2026-09-27")
OUT = os.path.join(ROOT, "data/eval/entailment_adjudication_2026-09-27")
LANG = {1: "zh", 2: "en", 3: "ja"}
LANG_ID = {v: k for k, v in LANG.items()}
PER_LANG = 100
MAX_D = 60          # cap on the disagreement stratum per language
Q_PER_PACKET = 20
LETTERS = "ABCDEFGH"


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _qkey(src, lang, passage, question):
    return hashlib.md5(f"{src}|{lang}|{passage[:200]}|{question}".encode()).hexdigest()[:10]


def _grams(text: str, lang: int) -> set:
    if lang == 2:
        w = text.lower().split()
        return set(w) | set(zip(w, w[1:]))
    t = "".join(text.split())
    return {t[i:i + 3] for i in range(len(t) - 2)}


def _recover_passage(rec: dict, cands: dict) -> tuple[str | None, float]:
    """The 2026-09-27 window lost its test_id (thread-local, see the harness), so
    match a record to its passage by n-gram overlap of question+answer within the
    language. Returns (passage, margin); None when the match is ambiguous."""
    q = _grams(rec["question"] + " " + rec["answer"], rec["lang"])
    if not q:
        return None, 0.0
    scored = sorted(((len(q & _grams(p, rec["lang"])) / len(q), p) for p in cands.values()),
                    key=lambda x: -x[0])
    if len(scored) < 2:
        return (scored[0][1], 1.0) if scored else (None, 0.0)
    margin = scored[0][0] - scored[1][0]
    top = scored[0][0]
    ok = (top >= 0.3 and margin >= 0.05) or (top >= 0.12 and margin >= 0.08)
    return (scored[0][1] if ok else None), margin


def collect_items() -> list[dict]:
    items = []
    for m in _load(CAL):
        jv = probability_to_verdict(m["jev"], m["lang"])
        items.append({
            "src": "cal", "lang": m["lang"], "passage": m["passage"],
            "question": m["question"], "candidate": m["candidate"],
            "structural": m["label"], "live": m["live_verdict"], "jev": jv,
            "jev_p": m["jev"], "live_rating": m["live_score"],
        })
    for name in ("pilot", "main"):
        p = os.path.join(WIN_DIR, f"{name}_calls.json")
        if not os.path.exists(p):
            continue
        d = _load(p)
        lang_of = {s_["test_id"]: LANG_ID[s_["lang"]] for s_ in d["summaries"]}
        dropped = 0
        for r in d["records"]:
            if r.get("jev_verdict") is None:
                continue        # jev failed on this item; nothing to compare
            passage = r.get("passage") or (d["passages"].get(r["test_id"]) if r.get("test_id") else None)
            if passage is None:
                cands = {t: txt for t, txt in d["passages"].items() if lang_of.get(t) == r["lang"]}
                passage, _m = _recover_passage(r, cands)
                if passage is None:
                    dropped += 1
                    continue
            items.append({
                "src": f"win_{name}", "lang": r["lang"],
                "passage": passage, "question": r["question"],
                "candidate": r["answer"], "structural": None,
                "live": r["live_verdict"], "jev": r["jev_verdict"],
                "jev_p": r["jev_p"], "live_rating": r["live_rating"],
            })
        if dropped:
            print(f"{name}: {dropped} window records dropped (ambiguous passage match)", file=sys.stderr)
    seen, out = set(), []
    for it in items:                       # de-dup identical (passage, question, candidate)
        k = (it["lang"], it["passage"][:200], it["question"], it["candidate"])
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def build_pool(seed: int = 927):
    rng = random.Random(seed)
    items = collect_items()
    pool = []
    for lang in (1, 2, 3):
        li = [i for i in items if i["lang"] == lang]
        dis = [i for i in li if i["live"] != i["jev"]]
        agree = [i for i in li if i["live"] == i["jev"]]
        rng.shuffle(dis)
        d = dis[:MAX_D]
        # stratum A: at least a third from the fresh shadow window, and balanced
        # between structural answers / distractors within the calibration items
        need = PER_LANG - len(d)
        win = [i for i in agree if i["src"].startswith("win")]
        cal_a = [i for i in agree if i["structural"] == 1]
        cal_d = [i for i in agree if i["structural"] == 0]
        for g in (win, cal_a, cal_d):
            rng.shuffle(g)
        take = []
        n_win = min(len(win), max(need // 3, 0))
        take += win[:n_win]
        rest = need - len(take)
        take += cal_a[: rest // 2] + cal_d[: rest - rest // 2]
        for i in d:
            i["stratum"] = "D"
        for i in take:
            i["stratum"] = "A"
        pool += d + take
        print(f"{LANG[lang]}: disagreements {len(dis)} (used {len(d)}), agreeing {len(agree)} "
              f"(window {len(win)}), sampled A {len(take)}", file=sys.stderr)
    return pool


def write_packets(pool: list[dict]) -> None:
    os.makedirs(os.path.join(OUT, "packets"), exist_ok=True)
    byq: dict[str, list[dict]] = defaultdict(list)
    for it in pool:
        byq[_qkey(it["src"][:3], it["lang"], it["passage"], it["question"])].append(it)
    qkeys = sorted(byq, key=lambda k: (byq[k][0]["lang"], k))
    key = {"questions": {}}
    for n, qk in enumerate(qkeys, 1):
        key["questions"][f"Q{n:03d}"] = {"qkey": qk, "items": byq[qk]}
    with open(os.path.join(OUT, "pool_key.json"), "w", encoding="utf-8") as fh:
        json.dump(key, fh, ensure_ascii=False, indent=1)     # PRIVATE: never shown to labellers

    for who, seed in (("A", 1), ("B", 2)):
        order = list(key["questions"])
        random.Random(seed).shuffle(order)
        perm = {}
        for pn, start in enumerate(range(0, len(order), Q_PER_PACKET), 1):
            lines = [f"# Adjudication packet {who}-{pn:02d}", "",
                     "For EACH candidate, decide whether it is a correct answer to the question "
                     "using ONLY the passage. Candidates are judged independently: several may be "
                     "correct, or none.", ""]
            for qid in order[start:start + Q_PER_PACKET]:
                its = key["questions"][qid]["items"]
                idx = list(range(len(its)))
                random.Random(f"{seed}{qid}").shuffle(idx)
                perm[qid] = {LETTERS[j]: idx[j] for j in range(len(idx))}
                lines += [f"## {qid}", "", "**Passage:**", "", its[0]["passage"], "",
                          f"**Question:** {its[0]['question']}", "", "**Candidates:**", ""]
                lines += [f"- {LETTERS[j]}: {its[idx[j]]['candidate']}" for j in range(len(idx))]
                lines.append("")
            path = os.path.join(OUT, "packets", f"{who}_{pn:02d}.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
        with open(os.path.join(OUT, f"perm_{who}.json"), "w", encoding="utf-8") as fh:
            json.dump(perm, fh)
    print(f"{len(qkeys)} questions, {len(pool)} items -> {OUT}/packets", file=sys.stderr)


# --------------------------------------------------------------------------- scoring

def _read_labels(who: str) -> dict:
    """-> {(qid, item_idx): label}."""
    perm = _load(os.path.join(OUT, f"perm_{who}.json"))
    out = {}
    d = os.path.join(OUT, "labels")
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.startswith(who + "_"):
            continue
        for qid, cands in _load(os.path.join(d, fn)).get("questions", {}).items():
            for letter, v in cands.items():
                lab = (v.get("label") if isinstance(v, dict) else v)
                if qid in perm and letter in perm[qid] and lab in ("yes", "no", "unclear"):
                    out[(qid, perm[qid][letter])] = lab
    return out


def _kappa(a: list, b: list) -> float:
    labs = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labs)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def merged_labels():
    A, B = _read_labels("A"), _read_labels("B")
    C = _read_labels_c()
    final, status = {}, {}
    for k in set(A) | set(B):
        a, b = A.get(k), B.get(k)
        if a and b and a == b:
            final[k], status[k] = a, "agree"
        elif a and b:
            c = C.get(k)
            trio = [a, b] + ([c] if c else [])
            top, cnt = Counter(trio).most_common(1)[0]
            final[k], status[k] = (top, "majority") if cnt >= 2 else ("unclear", "split")
        else:
            final[k], status[k] = (a or b), "single"
    return A, B, C, final, status


def _read_labels_c() -> dict:
    p = os.path.join(OUT, "tiebreak_perm.json")
    if not os.path.exists(p):
        return {}
    perm = _load(p)
    out = {}
    d = os.path.join(OUT, "labels")
    for fn in sorted(os.listdir(d)):
        if not fn.startswith("C_"):
            continue
        for qid, cands in _load(os.path.join(d, fn)).get("questions", {}).items():
            for letter, v in cands.items():
                lab = (v.get("label") if isinstance(v, dict) else v)
                if qid in perm and letter in perm[qid] and lab in ("yes", "no", "unclear"):
                    out[(qid, perm[qid][letter])] = lab
    return out


def write_tiebreak() -> None:
    key = _load(os.path.join(OUT, "pool_key.json"))["questions"]
    A, B = _read_labels("A"), _read_labels("B")
    need = defaultdict(list)
    for k in set(A) & set(B):
        if A[k] != B[k]:
            need[k[0]].append(k[1])
    os.makedirs(os.path.join(OUT, "packets"), exist_ok=True)
    perm, qids = {}, sorted(need)
    for pn, start in enumerate(range(0, len(qids), Q_PER_PACKET), 1):
        lines = [f"# Adjudication packet C-{pn:02d}", "",
                 "For EACH candidate, decide whether it is a correct answer to the question using "
                 "ONLY the passage. Candidates are judged independently.", ""]
        for qid in qids[start:start + Q_PER_PACKET]:
            its = key[qid]["items"]
            idx = need[qid][:]
            random.Random(f"C{qid}").shuffle(idx)
            perm[qid] = {LETTERS[j]: idx[j] for j in range(len(idx))}
            lines += [f"## {qid}", "", "**Passage:**", "", its[0]["passage"], "",
                      f"**Question:** {its[0]['question']}", "", "**Candidates:**", ""]
            lines += [f"- {LETTERS[j]}: {its[idx[j]]['candidate']}" for j in range(len(idx))]
            lines.append("")
        with open(os.path.join(OUT, "packets", f"C_{pn:02d}.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    with open(os.path.join(OUT, "tiebreak_perm.json"), "w", encoding="utf-8") as fh:
        json.dump(perm, fh)
    print(f"{sum(len(v) for v in need.values())} split items over {len(qids)} questions "
          f"-> {-(-len(qids)//Q_PER_PACKET)} tiebreak packets", file=sys.stderr)


def score() -> None:
    key = _load(os.path.join(OUT, "pool_key.json"))["questions"]
    A, B, C, final, status = merged_labels()
    both = [k for k in A if k in B]
    lines = ["# Adjudicated entailment gold — scoring", ""]
    lines.append(f"Labelled: A={len(A)} B={len(B)}; both={len(both)}; tiebreak C={len(C)}.")
    if both:
        lines.append(f"Inter-labeller agreement A/B: {sum(A[k]==B[k] for k in both)/len(both):.1%}, "
                     f"Cohen kappa {_kappa([A[k] for k in both], [B[k] for k in both]):.3f}.")
    lines.append("Final label = agreement, else majority of A/B/C, else `unclear`. "
                 "**Adjudicators are models, not humans** (see task note).\n")

    rows = []
    for (qid, idx), lab in final.items():
        it = dict(key[qid]["items"][idx])
        it["adj"], it["adj_status"], it["qid"] = lab, status[(qid, idx)], qid
        rows.append(it)
    hdr = ["verdict \\ adjudicated", "yes", "unclear", "no"]
    for lang in (1, 2, 3):
        L = [r for r in rows if r["lang"] == lang]
        if not L:
            continue
        lines += [f"## {LANG[lang]}  (n={len(L)}; cutoffs {CUTOFFS[lang]})", ""]
        for who in ("live", "jev"):
            lines += [f"### {who}", "", "| " + " | ".join(hdr) + " |", "|---|---|---|---|"]
            for v in ("accept", "flag", "reject"):
                c = Counter(r["adj"] for r in L if r[who] == v)
                lines.append(f"| {v} | {c['yes']} | {c['unclear']} | {c['no']} |")
            lines.append("")
        for st in ("A", "D"):
            S = [r for r in L if r["stratum"] == st]
            def rate(who):
                fa = sum(r[who] == "accept" and r["adj"] == "no" for r in S)
                fr = sum(r[who] == "reject" and r["adj"] == "yes" for r in S)
                return fa, fr
            lf, jf = rate("live"), rate("jev")
            lines.append(f"- stratum {st} (n={len(S)}): false-accept live {lf[0]} / jev {jf[0]}; "
                         f"false-reject live {lf[1]} / jev {jf[1]}")
        # head-to-head on disagreements
        Dn = [r for r in L if r["live"] != r["jev"]]
        jw = sum(1 for r in Dn if (r["jev"] == "accept" and r["adj"] == "yes") or (r["jev"] == "reject" and r["adj"] == "no"))
        lw = sum(1 for r in Dn if (r["live"] == "accept" and r["adj"] == "yes") or (r["live"] == "reject" and r["adj"] == "no"))
        lines.append(f"- head-to-head on {len(Dn)} disagreements: jev matches the adjudication on {jw}, "
                     f"live on {lw} (rest: a flag or an `unclear` label)")
        lines.append("")

    # cutoff re-sweep on adjudicated yes/no only
    lines += ["## Cutoff re-sweep (jev P(yes) vs adjudicated yes/no; `unclear` excluded)", ""]
    for lang in (1, 2, 3):
        L = [r for r in rows if r["lang"] == lang and r["adj"] in ("yes", "no")]
        if not L:
            continue
        lines += [f"**{LANG[lang]}** (n={len(L)}, yes={sum(r['adj']=='yes' for r in L)}):", "",
                  "| reject < | accept ≥ | false-reject | false-accept | flagged |", "|---|---|---|---|---|"]
        for r_ in (0.2, 0.3, 0.4, 0.5):
            for a_ in (0.5, 0.6, 0.7):
                if a_ < r_:
                    continue
                fr = sum(r["adj"] == "yes" and r["jev_p"] < r_ for r in L)
                fa = sum(r["adj"] == "no" and r["jev_p"] >= a_ for r in L)
                fl = sum(r_ <= r["jev_p"] < a_ for r in L)
                mark = "  ← current" if (r_, a_) == CUTOFFS[lang] else ""
                lines.append(f"| {r_} | {a_} | {fr} | {fa} | {fl} |{mark}")
        lines.append("")

    # worst cases, with text
    lines += ["## Where each judge disagrees with the adjudication (text)", ""]
    for who in ("jev", "live"):
        bad = [r for r in rows if (r[who] == "accept" and r["adj"] == "no")
               or (r[who] == "reject" and r["adj"] == "yes")]
        lines += [f"### {who}: {len(bad)} confident errors", ""]
        for r in bad:
            lines += [f"- [{LANG[r['lang']]}/{r['stratum']}/{r['src']}] {who}={r[who]} adj={r['adj']} "
                      f"({r['adj_status']}) jev_p={r['jev_p']:.2f} live={r['live']} structural={r['structural']}",
                      f"  - Q: {r['question']}", f"  - candidate: {r['candidate']}"]
        lines.append("")
    # Items a human should confirm: the adjudicators did not agree, or the model
    # adjudication contradicts a judge's confident verdict. Blank `human_label`.
    import csv
    def _needs_human(r):
        return (r["adj_status"] != "agree"
                or (r["jev"] == "accept" and r["adj"] == "no")
                or (r["jev"] == "reject" and r["adj"] == "yes"))
    with open(os.path.join(OUT, "human_review_sheet.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["lang", "stratum", "question", "candidate", "jev_verdict", "jev_p",
                    "live_verdict", "model_label", "label_status", "human_label", "passage"])
        for r in sorted((r for r in rows if _needs_human(r)), key=lambda r: (r["lang"], r["qid"])):
            w.writerow([LANG[r["lang"]], r["stratum"], r["question"], r["candidate"], r["jev"],
                        f"{r['jev_p']:.2f}", r["live"], r["adj"], r["adj_status"], "", r["passage"]])
    with open(os.path.join(OUT, "scoring_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    with open(os.path.join(OUT, "adjudicated_items.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print("wrote scoring_report.md")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["pool"]:
        write_packets(build_pool())
    elif cmd == ["tiebreak"]:
        write_tiebreak()
    elif cmd == ["score"]:
        score()
    else:
        raise SystemExit("usage: pool | tiebreak | score")
