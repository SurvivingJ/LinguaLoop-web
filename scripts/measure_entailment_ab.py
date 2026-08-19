"""Cross-model A/B for the answer-entailment judge, scored against gold labels.

Companion to ``scripts/measure_judge_flag_rate.py``. That script measures a
*rate* — what fraction of items an arm rejects — which is all you can measure
when nothing tells you which items deserved rejection. TASK-718 hit the wall
that follows from this: two judge models produced reject sets that barely
overlapped, so neither rate could be called correct and no arm could be
promoted on the evidence.

This harness closes that gap for entailment specifically, because entailment is
the one judge whose gold labels can be manufactured for free:

* a question's **correct answer** is, by construction, entailed by the passage
  → the judge should rate it HIGH  (label 1)
* a question's **distractors** are, by construction, NOT entailed by the passage
  → the judge should rate it LOW   (label 0)

So every arm is scored on a real discrimination task. The headline metric is
ROC AUC, which is threshold-free and therefore comparable across models that
sit on different parts of the scale — the exact property a raw reject rate
lacks. Accuracy at the live production cut points is reported alongside it,
because AUC can be excellent while the *deployed* cut points are still in the
wrong place.

SCALE (TASK-723): this judge now returns a 1-5 Likert rating, not a 0.0-1.0
confidence, and the live cut points are ``LIKERT_ACCEPT`` / ``LIKERT_REJECT``
below. AUC is rank-based, so numbers from before the conversion remain
comparable; the error table's thresholds are NOT, because the two scales invert
at 1. Runs from before 2026-08-17 were measured on the float scale — see
wiki/evaluations/entailment-judge-model-ab-2026-08-17.md.

Label caveat, which bounds every number below and must be quoted with them:
the labels are structural, not human-adjudicated. A distractor that genuinely
IS entailed by the passage is a content bug in the distractor set, and it will
be charged here to the judge as a false accept. Likewise a "correct" answer the
passage does not actually support is a generator bug charged as a false reject.
Both are real defects worth finding, but they mean AUC is a LOWER bound on
judge quality, not a point estimate.

    # baseline (each language on its configured model) vs three challengers
    python scripts/measure_entailment_ab.py \
        --sample flag_rate_sample.json \
        --arms "live=,q37f=qwen/qwen3.7-flash,dsv4f=deepseek/deepseek-v4-flash" \
        --out entailment_ab.json

    # re-print the tables from a finished run without spending anything
    python scripts/measure_entailment_ab.py --report-only entailment_ab.json

An arm is `name=model`. An empty model means each language uses the `model`
column on its own ``prompt_templates`` row — the "as configured" arm.

Every call is logged to ``llm_calls`` under ``pipeline='diag'`` so diagnostic
spend never contaminates per-pipeline production cost reporting; the run reports
its own cost by reading those rows back.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# Run-as-script bootstrap (mirrors scripts/measure_judge_flag_rate.py): repo
# root on the path and .env loaded before any app service is imported.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.llm_service import call_llm  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402
from services.test_generation.schemas import (  # noqa: E402
    AnswerEntailmentVerdict,
    likert_to_verdict,
)

# Live cut points on the v2 Likert scale, mirroring schemas.likert_to_verdict:
# 5/4 accept, 3 flag, 2/1 reject. These replace judges.base.THRESHOLD_ACCEPT /
# THRESHOLD_REJECT, which classified the pre-v2 0.0-1.0 confidence and are now
# reachable only from the cloze judge.
LIKERT_ACCEPT = 4.0   # score >= this  -> accept
LIKERT_REJECT = 3.0   # score <  this  -> reject

LANG_NAME = {1: "zh", 2: "en", 3: "ja"}
LANG_ID = {v: k for k, v in LANG_NAME.items()}
JUDGE_TASK = "test_answer_entailment"

# Some OpenRouter providers (Alibaba's Qwen endpoints among them) hard-reject a
# request that sets response_format=json_object unless the literal token "json"
# appears somewhere in the messages:
#
#   400 invalid_parameter_error: 'messages' must contain the word 'json' in some
#   form, to use 'response_format' of type 'json_object'
#
# The EN entailment template says "valid JSON" and sails through. The ZH and JA
# templates say 仅以如下格式返回 / 以下の形式のみで返してください and contain no
# such token, so EVERY zh/ja call to those providers 400s. In production that
# lands in the judge's except branch and returns safe_accept() — the judge
# silently becomes a no-op rather than failing loudly. That is a live landmine
# for any Qwen-family routing on zh/ja, and it is tracked separately from this
# experiment.
#
# For the A/B the suffix is appended to any template lacking the token, for
# EVERY arm including the baseline, so all arms still score byte-identical
# prompts and cross-arm comparability is preserved. Without it the cheap Qwen
# candidates could not be measured on zh/ja at all.
JSON_TOKEN_SUFFIX = {
    1: "\n\n请仅输出 JSON。",
    2: "\n\nRespond with JSON only.",
    3: "\n\nJSON のみを出力してください。",
}

_print_lock = Lock()
_done = [0]


# --------------------------------------------------------------------------- args


def _parse_arms(spec: str) -> list[dict]:
    """`name=model,name=` -> [{name, model}, ...]."""
    arms = []
    for chunk in (c.strip() for c in spec.split(",") if c.strip()):
        if "=" not in chunk:
            raise SystemExit(f"[error] arm {chunk!r} is not name=model")
        name, _, model = chunk.partition("=")
        arms.append({"name": name.strip(), "model": model.strip() or None})
    names = [a["name"] for a in arms]
    if len(set(names)) != len(names):
        raise SystemExit("[error] arm names must be unique — they tag the cost rows")
    return arms


# ------------------------------------------------------------------------- inputs


def _build_items(rows: list[dict], negatives: int, seed: int) -> list[dict]:
    """Expand question rows into labelled (passage, question, candidate) items.

    One positive per question (the real answer) and ``negatives`` distractors
    drawn deterministically, so two runs of this script score byte-identical
    inputs and any difference between them is the arm's doing.
    """
    rng = random.Random(seed)
    items = []
    for r in rows:
        items.append({
            "item_id": f"{r['qid']}:pos",
            "qid": r["qid"],
            "lang": r["lang"],
            "passage": r["passage"],
            "question": r["question"],
            "candidate": r["answer"],
            "label": 1,
        })
        pool = list(r["distractors"])
        rng.shuffle(pool)
        for i, d in enumerate(pool[:negatives]):
            items.append({
                "item_id": f"{r['qid']}:neg{i}",
                "qid": r["qid"],
                "lang": r["lang"],
                "passage": r["passage"],
                "question": r["question"],
                "candidate": d,
                "label": 0,
            })
    return items


def _load_templates(
    db, langs: list[int], override: str | None, json_token: bool = True,
    version: int | None = None,
) -> dict:
    """Load one entailment template per language.

    ``version`` pins an explicit ``prompt_templates.version`` instead of taking
    whichever row is active. That is what lets a *staged* prompt be measured
    before it is switched on: the TASK-723 Likert rows land inactive, because
    activating them before the matching code deploys would make the judge fail
    schema validation and silently safe_accept. Measuring first, activating
    second, is only possible if the harness can address an inactive row.
    """
    tpl = {}
    for lang in langs:
        query = (
            db.table("prompt_templates")
            .select("template_text, model, version")
            .eq("task_name", JUDGE_TASK)
            .eq("language_id", lang)
        )
        query = (query.eq("version", version) if version is not None
                 else query.eq("is_active", True))
        resp = query.execute()
        if not resp.data:
            where = f"version={version}" if version is not None else "is_active"
            raise SystemExit(
                f"[error] no {JUDGE_TASK} row for language_id={lang} ({where})"
            )
        row = resp.data[0]
        text = row["template_text"]
        if json_token and "json" not in text.lower():
            text += JSON_TOKEN_SUFFIX[lang]
        tpl[lang] = {
            "template_text": text,
            "model": override or row["model"],
            "version": row["version"],
        }
    return tpl


# --------------------------------------------------------------------------- judge


def _judge_one(args) -> dict:
    arm, item, tpl, total = args
    lang = item["lang"]
    prompt = tpl[lang]["template_text"].format(
        item["passage"], item["question"], item["candidate"]
    )
    try:
        obj: AnswerEntailmentVerdict = call_llm(
            prompt,
            model=tpl[lang]["model"],
            temperature=0.0,
            response_format="json_object",
            schema=AnswerEntailmentVerdict,
            provider="openrouter",
            pipeline="diag",
            task_name=f"entail_{arm}",
            template_version=tpl[lang]["version"],
        )
        # v2 (TASK-723) moved this judge from a 0.0-1.0 confidence to a 1-5
        # Likert rating. `score` is whatever scale the arm's prompt row speaks;
        # AUC is rank-based so it stays valid and comparable across the change,
        # but the ERROR table's cut points are not — a v1 arm is classified by
        # base.classify and a v2 arm by likert_to_verdict, and the two invert at
        # 1. `scale` records which, so a mixed run cannot be read as if one
        # threshold applied to all of it.
        #
        # A None rating means the judge answered without a usable rating. It is
        # NOT a zero: scoring it as one would count a non-answer as a confident
        # rejection and depress the arm's AUC for a parse failure.
        if obj.rating is None:
            res = {
                "ok": False,
                "error": "judge returned no rating",
                "score": None,
                "verdict": None,
                "scale": "likert",
                "reason": (obj.reason or "")[:300],
            }
        else:
            res = {
                "ok": True,
                "score": float(obj.rating),
                "verdict": likert_to_verdict(obj.rating),
                "scale": "likert",
                "reason": (obj.reason or "")[:300],
            }
    except Exception as exc:  # noqa: BLE001 — one bad call must not lose the run
        res = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "score": None,
            "verdict": None,
            "scale": "likert",
            "reason": "",
        }
    res.update({
        "arm": arm,
        "model": tpl[lang]["model"],
        "lang": lang,
        "item_id": item["item_id"],
        "qid": item["qid"],
        "label": item["label"],
    })
    with _print_lock:
        _done[0] += 1
        if _done[0] % 50 == 0 or _done[0] == total:
            print(f"  [{_done[0]}/{total}]", flush=True)
    return res


# -------------------------------------------------------------------------- report


def auc(pos: list[float], neg: list[float]) -> float:
    """ROC AUC via the Mann-Whitney U identity, ties counted as half.

    Threshold-free: it asks only "does a positive outscore a negative more often
    than not", so it stays comparable between a model that lives at 0.9-1.0 and
    one that uses the whole scale. 0.5 == coin flip.
    """
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def _arm_names(results: list[dict]) -> list[str]:
    seen = []
    for r in results:
        if r["arm"] not in seen:
            seen.append(r["arm"])
    return seen


def _split(results, arm, lang=None):
    sel = [
        r for r in results
        if r["arm"] == arm and r["ok"] and (lang is None or r["lang"] == lang)
    ]
    return (
        [r["score"] for r in sel if r["label"] == 1],
        [r["score"] for r in sel if r["label"] == 0],
    )


def report(results: list[dict]) -> None:
    arms = _arm_names(results)
    langs = sorted({r["lang"] for r in results})

    # --- headline: can the arm tell a real answer from a distractor at all? ---
    print("\n" + "=" * 100)
    print("DISCRIMINATION  (gold: correct answer = entailed, distractor = not entailed)")
    print("=" * 100)
    print(
        f"{'arm':<9}{'lang':<5}{'model':<32}{'n+':>4}{'n-':>4}"
        f"{'AUC':>7}{'mean+':>8}{'mean-':>8}{'gap':>7}"
    )
    for arm in arms:
        for lang in langs:
            pos, neg = _split(results, arm, lang)
            if not pos and not neg:
                continue
            model = next(
                r["model"] for r in results if r["arm"] == arm and r["lang"] == lang
            )
            a = auc(pos, neg)
            mp = sum(pos) / len(pos) if pos else float("nan")
            mn = sum(neg) / len(neg) if neg else float("nan")
            print(
                f"{arm:<9}{LANG_NAME[lang]:<5}{model:<32}{len(pos):>4}{len(neg):>4}"
                f"{a:>7.3f}{mp:>8.3f}{mn:>8.3f}{mp - mn:>7.3f}"
            )
        pos, neg = _split(results, arm)
        print(
            f"{arm:<9}{'ALL':<5}{'':<32}{len(pos):>4}{len(neg):>4}"
            f"{auc(pos, neg):>7.3f}"
        )
        print("-" * 100)

    # --- what the live thresholds actually do with those scores ---
    print("\n" + "=" * 100)
    print(
        f"ERRORS AT LIVE THRESHOLDS  (accept >= {LIKERT_ACCEPT:g}, "
        f"reject < {LIKERT_REJECT:g})"
    )
    print("=" * 100)
    print(
        f"{'arm':<9}{'lang':<5}{'false-reject':>14}{'95% CI':>16}"
        f"{'false-accept':>14}{'95% CI':>16}{'flag+':>7}{'flag-':>7}"
    )
    for arm in arms:
        for lang in langs:
            sel = [
                r for r in results
                if r["arm"] == arm and r["ok"] and r["lang"] == lang
            ]
            p = [r for r in sel if r["label"] == 1]
            n = [r for r in sel if r["label"] == 0]
            if not p and not n:
                continue
            # false reject: a genuine answer the judge would drop
            fr = sum(1 for r in p if r["verdict"] == "reject")
            # false accept: a distractor the judge would wave through as correct
            fa = sum(1 for r in n if r["verdict"] == "accept")
            flp = sum(1 for r in p if r["verdict"] == "flag")
            fln = sum(1 for r in n if r["verdict"] == "flag")
            frl, frh = wilson(fr, len(p))
            fal, fah = wilson(fa, len(n))
            print(
                f"{arm:<9}{LANG_NAME[lang]:<5}"
                f"{f'{fr}/{len(p)} {100 * fr / max(1, len(p)):.0f}%':>14}"
                f"{f'[{100 * frl:.0f}%, {100 * frh:.0f}%]':>16}"
                f"{f'{fa}/{len(n)} {100 * fa / max(1, len(n)):.0f}%':>14}"
                f"{f'[{100 * fal:.0f}%, {100 * fah:.0f}%]':>16}"
                f"{flp:>7}{fln:>7}"
            )
        print("-" * 100)

    # --- does the model use the scale, or does it emit three magic numbers? ---
    print("\n" + "=" * 100)
    print("SCORE DISTRIBUTION  (a judge that only emits 0.0/0.9/1.0 cannot be re-tuned)")
    print("=" * 100)
    print(f"{'arm':<9}{'lang':<5}{'distinct':>9}{'top values (value xN)':<52}{'err':>5}")
    for arm in arms:
        for lang in langs:
            sel = [r for r in results if r["arm"] == arm and r["lang"] == lang]
            ok = [r for r in sel if r["ok"]]
            if not sel:
                continue
            dist = Counter(round(r["score"], 2) for r in ok)
            top = "  ".join(f"{v}x{c}" for v, c in dist.most_common(6))
            print(
                f"{arm:<9}{LANG_NAME[lang]:<5}{len(dist):>9}{top:<52}"
                f"{sum(1 for r in sel if not r['ok']):>5}"
            )
        print("-" * 100)

    # --- where would a cut point actually go, if we were free to move it? ---
    print("\n" + "=" * 100)
    print("BEST SINGLE THRESHOLD  (max balanced accuracy, swept over observed scores)")
    print("=" * 100)
    print(f"{'arm':<9}{'lang':<5}{'thr':>7}{'bal-acc':>9}{'@live thr':>11}")
    for arm in arms:
        for lang in langs:
            pos, neg = _split(results, arm, lang)
            if not pos or not neg:
                continue
            cands = sorted({round(x, 3) for x in pos + neg})
            best_t, best_b = None, -1.0
            for t in cands:
                tpr = sum(1 for x in pos if x >= t) / len(pos)
                tnr = sum(1 for x in neg if x < t) / len(neg)
                if (tpr + tnr) / 2 > best_b:
                    best_t, best_b = t, (tpr + tnr) / 2
            live_tpr = sum(1 for x in pos if x >= LIKERT_ACCEPT) / len(pos)
            live_tnr = sum(1 for x in neg if x < LIKERT_REJECT) / len(neg)
            print(
                f"{arm:<9}{LANG_NAME[lang]:<5}{best_t:>7.3f}{best_b:>9.3f}"
                f"{(live_tpr + live_tnr) / 2:>11.3f}"
            )
        print("-" * 100)

    # --- disagreement: the TASK-718 question, now answerable against labels ---
    if len(arms) > 1:
        print("\n" + "=" * 100)
        print("PAIRWISE AGREEMENT ON VERDICTS  (and who is right when they differ)")
        print("=" * 100)
        by_item: dict = defaultdict(dict)
        for r in results:
            if r["ok"]:
                by_item[r["item_id"]][r["arm"]] = r
        print(f"{'pair':<22}{'agree':>8}{'A right':>9}{'B right':>9}{'both wrong':>12}")
        for i, a in enumerate(arms):
            for b in arms[i + 1:]:
                agree = a_right = b_right = both_wrong = 0
                for item in by_item.values():
                    if a not in item or b not in item:
                        continue
                    ra, rb = item[a], item[b]
                    # "correct" = the verdict the gold label implies
                    want = "accept" if ra["label"] == 1 else "reject"
                    ok_a, ok_b = ra["verdict"] == want, rb["verdict"] == want
                    if ra["verdict"] == rb["verdict"]:
                        agree += 1
                    elif ok_a:
                        a_right += 1
                    elif ok_b:
                        b_right += 1
                    else:
                        both_wrong += 1
                tot = agree + a_right + b_right + both_wrong
                if tot:
                    print(
                        f"{f'{a} vs {b}':<22}"
                        f"{f'{100 * agree / tot:.0f}%':>8}"
                        f"{a_right:>9}{b_right:>9}{both_wrong:>12}"
                    )


def report_cost(db, arms: list[str], since: str) -> None:
    """Read spend back out of llm_calls — the run's own rows, by arm tag."""
    rows = (
        db.table("llm_calls")
        .select("task_name, model, cost_usd")
        .in_("task_name", [f"entail_{a}" for a in arms])
        .gte("created_at", since)
        .execute()
        .data
        or []
    )
    if not rows:
        print("\n[warn] no llm_calls rows found for this run; cost unavailable")
        return
    agg: dict = defaultdict(lambda: [0, 0.0])
    for r in rows:
        cell = agg[(r["task_name"], r["model"])]
        cell[0] += 1
        cell[1] += float(r["cost_usd"] or 0.0)
    print("\n" + "=" * 100)
    print("COST  (pipeline='diag')")
    print("=" * 100)
    print(f"{'arm':<22}{'model':<34}{'calls':>7}{'usd':>10}{'usd/call':>11}{'per 1k':>10}")
    total = 0.0
    for (task, model), (n, usd) in sorted(agg.items()):
        total += usd
        print(
            f"{task:<22}{model:<34}{n:>7}{usd:>10.4f}"
            f"{usd / n:>11.6f}{1000 * usd / n:>10.3f}"
        )
    print(f"{'TOTAL':<63}{total:>10.4f}")


# ---------------------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sample", help="frozen sample JSON (list of question rows)")
    ap.add_argument(
        "--arms",
        default="live=",
        help="comma list of name=model; empty model = each language's own row",
    )
    ap.add_argument("--langs", default="zh,en,ja")
    ap.add_argument(
        "--negatives",
        type=int,
        default=2,
        help="distractors promoted to negative items per question (max 3)",
    )
    ap.add_argument("--seed", type=int, default=718)
    ap.add_argument(
        "--no-json-token",
        action="store_true",
        help="skip the JSON_TOKEN_SUFFIX fix; zh/ja will 400 on Qwen providers",
    )
    ap.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "8")))
    ap.add_argument("--out", default="entailment_ab_results.json")
    ap.add_argument("--report-only", help="re-print tables from a finished results JSON")
    ap.add_argument(
        "--template-version", type=int, default=None,
        help="pin an explicit prompt_templates.version instead of the active "
             "row; use it to measure a staged prompt before activating it",
    )
    args = ap.parse_args()

    if args.report_only:
        with open(args.report_only, encoding="utf-8") as fh:
            report(json.load(fh))
        return
    if not args.sample:
        raise SystemExit("[error] --sample is required (or use --report-only)")

    langs = [LANG_ID[n.strip()] for n in args.langs.split(",") if n.strip()]
    arms = _parse_arms(args.arms)

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    with open(args.sample, encoding="utf-8") as fh:
        rows = [r for r in json.load(fh) if r["lang"] in langs]
    if not rows:
        raise SystemExit(f"[error] no rows in {args.sample} for languages {langs}")

    items = _build_items(rows, args.negatives, args.seed)
    per_lang = Counter(LANG_NAME[i["lang"]] for i in items)
    print(
        f"sample: {len(rows)} questions -> {len(items)} labelled items "
        f"({sum(1 for i in items if i['label'] == 1)} entailed / "
        f"{sum(1 for i in items if i['label'] == 0)} not-entailed), per language "
        f"{dict(per_lang)}"
    )

    jobs = []
    total = len(items) * len(arms)
    if args.no_json_token:
        print("[warn] JSON-token fix disabled; zh/ja will 400 on Qwen providers")
    for arm in arms:
        tpl = _load_templates(db, langs, arm["model"], not args.no_json_token,
                              version=args.template_version)
        print(
            f"arm {arm['name']}: "
            + ", ".join(f"{LANG_NAME[l]}={tpl[l]['model']}" for l in langs)
        )
        jobs += [(arm["name"], item, tpl, total) for item in items]

    since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 60))
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(_judge_one, jobs))
    elapsed = time.time() - t0

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1)
    report(results)
    report_cost(db, [a["name"] for a in arms], since)
    print(
        f"\nwall clock: {elapsed / 60:.1f} min ({args.workers} workers), "
        f"{len(jobs)} judge calls -> {args.out}"
    )


if __name__ == "__main__":
    main()
