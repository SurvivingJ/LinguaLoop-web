"""Calibrate jev (typesafe/jev-1.13, noul) against the live entailment judge.

Two item sets, both structural gold (answer = 1, distractor = 0):

* ``eval``  -- ``entailment_sample_150.json`` replayed with the exact shuffle
  (seed 718, 2 negatives) that produced the stored live verdicts in
  ``entailment_v3_2026-08-19.json`` / ``entailment_v3_ja_models_2026-08-19.json``
  (ja live judge = gemini-3.5-flash-lite, so ja is read from the ja_models file).
* ``prod``  -- ``entailment_prod_recent_2026-09-26.json`` (recent production
  questions), 3 negatives, live verdicts from ``live_prod_recent.json``.

    PYTHONPATH=. python scripts/calibrate_entailment_jev.py run      # spends ~ $0.05
    PYTHONPATH=. python scripts/calibrate_entailment_jev.py report
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
EXP_A = os.path.join(ROOT, "data", "eval", "jev_2026-09-26", "exp_a")
sys.path.insert(0, EXP_A)
OUT_DIR = os.path.join(ROOT, "data", "eval", "jev_entailment_calibration_2026-09-26")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from scripts.measure_entailment_ab import _build_items  # noqa: E402

LANG = {1: "zh", 2: "en", 3: "ja"}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_items() -> list[dict]:
    """All items with live verdict attached (live_score / live_verdict)."""
    items: list[dict] = []

    # --- eval set: replay the shuffle, attach stored live verdicts
    rows = _load(os.path.join(ROOT, "data/eval/entailment_sample_150.json"))
    base = _build_items(rows, negatives=2, seed=718)
    v3 = _load(os.path.join(ROOT, "data/eval/entailment_v3_2026-08-19.json"))
    ja = _load(os.path.join(ROOT, "data/eval/entailment_v3_ja_models_2026-08-19.json"))
    live = {}
    for r in v3:
        if r["lang"] in (1, 2):
            live[r["item_id"]] = r
    for r in ja:
        if r["lang"] == 3 and r["model"] == "google/gemini-3.5-flash-lite":
            live[r["item_id"]] = r
    for it in base:
        lv = live.get(it["item_id"])
        items.append(dict(it, set="eval",
                          live_score=lv and lv.get("score"),
                          live_verdict=lv and lv.get("verdict"),
                          live_reason=lv and lv.get("reason")))

    # --- prod set
    rows = _load(os.path.join(ROOT, "data/eval/entailment_prod_recent_2026-09-26.json"))
    base = _build_items(rows, negatives=3, seed=718)
    res = _load(os.path.join(OUT_DIR, "live_prod_recent.json"))
    live = {r["item_id"]: r for r in res}
    for it in base:
        lv = live.get(it["item_id"])
        items.append(dict(it, set="prod",
                          live_score=lv and lv.get("score"),
                          live_verdict=lv and lv.get("verdict"),
                          live_reason=lv and lv.get("reason")))
    return items


def run() -> None:
    from jev_client import call_jev_batch, get_running_totals
    from rubric import RUBRIC_ENTAILMENT

    items = build_items()
    reqs = [{
        "state": {"passage": it["passage"], "question": it["question"],
                  "candidate": it["candidate"]},
        "questions": RUBRIC_ENTAILMENT[LANG[it["lang"]]],
        "_meta": {"item_id": it["item_id"], "set": it["set"]},
    } for it in items]
    print(f"{len(reqs)} jev requests", file=sys.stderr)
    out = call_jev_batch(reqs, max_workers=8)
    merged = []
    for it, r in zip(items, out):
        ans = (r.get("answers") or {}).get("entailed") or {}
        merged.append({
            "set": it["set"], "lang": it["lang"], "item_id": it["item_id"],
            "qid": it["qid"], "label": it["label"],
            "passage": it["passage"], "question": it["question"],
            "candidate": it["candidate"],
            "live_score": it["live_score"], "live_verdict": it["live_verdict"],
            "live_reason": it["live_reason"],
            "jev": ans.get("noul"), "jev_error": r.get("_error"),
            "jev_cost": (r.get("usage") or {}).get("cost"),
        })
    with open(os.path.join(OUT_DIR, "jev_vs_live.json"), "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=1)
    cost, n = get_running_totals()
    errs = sum(1 for m in merged if m["jev"] is None)
    print(f"done: {n} calls, ${cost:.4f}, {errs} without a noul", file=sys.stderr)


# Proposed cut points: reject when P(yes) < reject_below, accept when
# P(yes) >= accept_at, flag in between. Chosen from the sweep in ``sweep()``.
CUTOFFS = {1: (0.30, 0.60), 2: (0.30, 0.60), 3: (0.30, 0.60)}


def verdict(p: float, lang: int) -> str:
    r, a = CUTOFFS[lang]
    return "reject" if p < r else "accept" if p >= a else "flag"


def report() -> None:
    d = _load(os.path.join(OUT_DIR, "jev_vs_live.json"))
    VS = ["accept", "flag", "reject"]
    lines = ["# jev vs live entailment judge -- calibration report", "",
             "Gold is STRUCTURAL (answer=1, distractor=0), not human-adjudicated.", ""]
    for lang in (1, 2, 3):
        r, a = CUTOFFS[lang]
        rows = [m for m in d if m["lang"] == lang]
        lines += [f"## {LANG[lang]}  (reject < {r}, accept >= {a}; n={len(rows)})", ""]
        for name, key in (("jev", lambda m: verdict(m["jev"], lang)),
                          ("live", lambda m: m["live_verdict"])):
            lines += [f"Gold x {name} verdict", "", "| gold | accept | flag | reject |", "|---|---|---|---|"]
            for g in (1, 0):
                sub = [m for m in rows if m["label"] == g]
                lines.append(f"| {'answer' if g else 'distractor'} ({len(sub)}) | " +
                             " | ".join(str(sum(key(m) == v for m in sub)) for v in VS) + " |")
            lines.append("")
        lines += ["live (rows) x jev (cols), all items", "",
                  "| live \ jev | accept | flag | reject |", "|---|---|---|---|"]
        for lv in VS:
            lines.append(f"| {lv} | " + " | ".join(
                str(sum(m["live_verdict"] == lv and verdict(m["jev"], lang) == jv for m in rows))
                for jv in VS) + " |")
        lines.append("")
        for st in ("eval", "prod"):
            sub = [m for m in rows if m["set"] == st]
            fr = sum(1 for m in sub if m["label"] == 1 and verdict(m["jev"], lang) == "reject")
            fa = sum(1 for m in sub if m["label"] == 0 and verdict(m["jev"], lang) == "accept")
            lines.append(f"- {st}: false-reject {fr}/{sum(m['label']==1 for m in sub)}, "
                         f"false-accept {fa}/{sum(m['label']==0 for m in sub)}")
        dis = [m for m in rows if m["live_verdict"] != verdict(m["jev"], lang)]
        lines += ["", f"### Disagreements ({len(dis)})", ""]
        for m in sorted(dis, key=lambda m: (m["label"], m["jev"])):
            jv = verdict(m["jev"], lang)
            lines += [f"- **gold={'answer' if m['label'] else 'distractor'}** live={m['live_verdict']}"
                      f"({m['live_score']}) jev={jv}({m['jev']:.2f}) [{m['set']}]",
                      f"  - Q: {m['question']}", f"  - candidate: {m['candidate']}",
                      f"  - live reason: {(m['live_reason'] or '')[:160]}"]
        lines.append("")
    with open(os.path.join(OUT_DIR, "calibration_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("wrote calibration_report.md")


if __name__ == "__main__":
    cmd = sys.argv[1:]
    if cmd == ["run"]:
        run()
    elif cmd == ["report"]:
        report()
    else:
        raise SystemExit("usage: run | report")
