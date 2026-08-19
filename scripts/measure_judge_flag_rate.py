"""Measure the distractor-plausibility judge's flag/reject rate over a frozen sample.

Promoted from the TASK-717 scratchpad harness so cross-model and cross-prompt-version
comparisons are reproducible. The point of the script is that **content is held
constant** — every arm scores byte-identical questions — so any difference between
arms is attributable to the arm's own variables (prompt version, judge model) and
nothing else.

    # TASK-718: same content, two judge models, two prompt versions
    python scripts/measure_judge_flag_rate.py \
        --sample flag_rate_sample.json \
        --arms "q4=4:qwen/qwen3.6-flash,g4=4:google/gemini-3.1-flash-lite" \
        --out results.json

    # single arm, each language on its own configured model
    python scripts/measure_judge_flag_rate.py --sample s.json --arms "live=4:"

    # re-print the tables from a finished run without spending anything
    python scripts/measure_judge_flag_rate.py --report-only results.json

An arm is `name=version:model`. The model half may be empty, in which case each
language uses the `model` column on its own `prompt_templates` row — that is the
"as configured" arm. `--judge-model` is the same override applied to every arm that
does not name one itself, which is the flag the TASK-718 brief asks for.

Slot conventions, both of which cost a previous measurement its comparability:

* Slot {4} is the question type. It gets the type_code STRING (`vocabulary_context`),
  never the bare `question_type_id` integer — v5's type-conditional rubric matches on
  the literal code, and an integer matches no bullet. The sample stores the integer;
  this script maps it.
* Slot {5} is the subject/domain line. It renders the "infer it yourself" fallback
  unless `--subject-lines` supplies a precomputed cache, because production leaves
  `JUDGE_SUBJECT_KEYWORDS` off by default. Passing a subject is a *different*
  intervention and must be an explicit choice.

Every call is logged to `llm_calls` under `pipeline='diag'` so diagnostic spend never
contaminates per-pipeline production cost reporting; the run reports its own cost by
reading those rows back.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# Run-as-script bootstrap (mirrors scripts/rescore_dt_grades.py): repo root on the
# path and .env loaded before any app service is imported.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.llm_service import call_llm  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402
from services.test_generation.schemas import (  # noqa: E402
    DistractorPlausibilityVerdict,
    likert_to_verdict,
)

LANG_NAME = {1: "zh", 2: "en", 3: "ja"}
LANG_ID = {v: k for k, v in LANG_NAME.items()}
JUDGE_TASK = "test_distractor_plausibility"
SUBJECT_FALLBACK = "(infer the subject from the passage above)"

_print_lock = Lock()
_done = [0]


# --------------------------------------------------------------------------- args


def _parse_arms(spec: str, default_model: str | None) -> list[dict]:
    """`name=version:model,name=version:` -> [{name, version, model}, ...]."""
    arms = []
    for chunk in (c.strip() for c in spec.split(",") if c.strip()):
        if "=" not in chunk:
            raise SystemExit(f"[error] arm {chunk!r} is not name=version:model")
        name, _, rhs = chunk.partition("=")
        version, _, model = rhs.partition(":")
        try:
            version_n = int(version)
        except ValueError:
            raise SystemExit(f"[error] arm {name!r}: version {version!r} is not an int")
        arms.append({
            "name": name.strip(),
            "version": version_n,
            "model": (model.strip() or default_model or None),
        })
    names = [a["name"] for a in arms]
    if len(set(names)) != len(names):
        raise SystemExit("[error] arm names must be unique — they tag the cost rows")
    return arms


# ------------------------------------------------------------------------- inputs


def _load_sample(path: str, langs: list[int]) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    rows = [r for r in rows if r["lang"] in langs]
    if not rows:
        raise SystemExit(f"[error] no rows in {path} for languages {langs}")
    return rows


def _map_type_codes(db, rows: list[dict]) -> None:
    """Rewrite each row's `type_code` from question_type_id to the string code.

    Idempotent: a sample that already carries string codes is left alone.
    """
    id2code = {
        t["id"]: t["type_code"]
        for t in db.table("dim_question_types").select("id, type_code").execute().data
    }
    unmapped = 0
    for r in rows:
        raw = r.get("type_code")
        if isinstance(raw, str) and raw and not raw.isdigit():
            continue  # already a code
        code = id2code.get(int(raw)) if str(raw).isdigit() else None
        if code is None:
            unmapped += 1
        r["type_code"] = code or ""
    if unmapped:
        print(f"[warn] {unmapped} rows have no question type; slot {{4}} renders empty")


def _load_templates(db, version: int, langs: list[int], override: str | None) -> dict:
    tpl = {}
    for lang in langs:
        resp = (
            db.table("prompt_templates")
            .select("template_text, model, version")
            .eq("task_name", JUDGE_TASK)
            .eq("language_id", lang)
            .eq("version", version)
            .execute()
        )
        if not resp.data:
            raise SystemExit(
                f"[error] no {JUDGE_TASK} row for language_id={lang} version={version}"
            )
        row = resp.data[0]
        tpl[lang] = {
            "template_text": row["template_text"],
            "model": override or row["model"],
        }
    return tpl


# --------------------------------------------------------------------------- judge


def _judge_one(args) -> dict:
    arm, row, tpl, subject, total = args
    lang = row["lang"]
    numbered = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(row["distractors"]))
    prompt = tpl[lang]["template_text"].format(
        row["passage"],
        row["question"],
        row["answer"],
        numbered,
        row["type_code"] or "(unspecified)",
        subject or SUBJECT_FALLBACK,
    )
    n = len(row["distractors"])
    try:
        obj = call_llm(
            prompt,
            model=tpl[lang]["model"],
            temperature=0.0,
            response_format="json_object",
            schema=DistractorPlausibilityVerdict,
            provider="openrouter",
            pipeline="diag",
            task_name=f"flag_rate_{arm}",
        )
        ratings = list(obj.per_distractor)[:n]
        res = {
            "ok": True,
            "ratings": ratings,
            "verdicts": [likert_to_verdict(r) for r in ratings],
        }
    except Exception as exc:  # noqa: BLE001 — one bad call must not lose the run
        res = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "ratings": [],
            "verdicts": [],
        }
    res.update({
        "arm": arm,
        "model": tpl[lang]["model"],
        "lang": lang,
        "qid": row["qid"],
        "type_code": row["type_code"],
        "n_expected": n,
    })
    with _print_lock:
        _done[0] += 1
        if _done[0] % 25 == 0 or _done[0] == total:
            print(f"  [{_done[0]}/{total}]", flush=True)
    return res


# -------------------------------------------------------------------------- report


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


def report(results: list[dict]) -> None:
    arms = _arm_names(results)
    langs = sorted({r["lang"] for r in results})

    print("\n" + "=" * 88)
    print("PER ARM x LANGUAGE")
    print("=" * 88)
    print(
        f"{'arm':<8}{'lang':<5}{'model':<30}{'q':>4}{'rej':>5}{'flag':>6}"
        f"{'rate':>7}{'95% CI':>16}"
    )
    for arm in arms:
        for lang in langs:
            ok = [r for r in results if r["arm"] == arm and r["lang"] == lang and r["ok"]]
            if not ok:
                continue
            rej = sum(1 for r in ok if "reject" in r["verdicts"])
            flg = sum(1 for r in ok if "flag" in r["verdicts"])
            lo, hi = wilson(rej, len(ok))
            print(
                f"{arm:<8}{LANG_NAME[lang]:<5}{ok[0]['model']:<30}{len(ok):>4}"
                f"{rej:>5}{flg:>6}{100.0 * rej / len(ok):>6.0f}%"
                f"{f'[{100 * lo:.0f}%, {100 * hi:.0f}%]':>16}"
            )
        print("-" * 88)

    # The middle band is the whole question: does this model ever emit a 3?
    print("\n" + "=" * 88)
    print("RATING DISTRIBUTION  (distractor level)")
    print("=" * 88)
    print(
        f"{'arm':<8}{'lang':<5}{'1':>6}{'2':>6}{'3':>6}{'4':>6}{'5':>6}"
        f"{'unrated':>9}{'err':>5}{'bands used':>16}"
    )
    for arm in arms:
        for lang in langs:
            sel = [r for r in results if r["arm"] == arm and r["lang"] == lang]
            if not sel:
                continue
            dist = Counter(x for r in sel if r["ok"] for x in r["ratings"] if x is not None)
            unrated = sum(1 for r in sel if r["ok"] for x in r["ratings"] if x is None)
            errs = sum(1 for r in sel if not r["ok"])
            used = "{" + ", ".join(str(b) for b in sorted(dist, reverse=True)) + "}"
            print(
                f"{arm:<8}{LANG_NAME[lang]:<5}"
                + "".join(f"{dist.get(b, 0):>6}" for b in (1, 2, 3, 4, 5))
                + f"{unrated:>9}{errs:>5}{used:>16}"
            )
        print("-" * 88)

    # Per-type rejects, arms in declaration order.
    print("\n" + "=" * 88)
    print(f"REJECTS BY QUESTION TYPE  ({' > '.join(arms)})")
    print("=" * 88)
    by: dict = defaultdict(lambda: defaultdict(int))
    tot: dict = defaultdict(int)
    for r in results:
        if not r["ok"]:
            continue
        key = (LANG_NAME[r["lang"]], r["type_code"])
        tot[(r["arm"], key)] += 1
        if "reject" in r["verdicts"]:
            by[r["arm"]][key] += 1
    names = [LANG_NAME[lang] for lang in langs]
    width = max(16, 4 * len(arms) + 10)
    print(f"{'type':<20}" + "".join(f"{n:>{width}}" for n in names))
    for tc in sorted({type_code for _, (_, type_code) in tot}):
        cells = []
        for lg in names:
            counts = ">".join(str(by[a].get((lg, tc), 0)) for a in arms)
            n = max(tot.get((a, (lg, tc)), 0) for a in arms)
            cells.append(f"{counts}/{n}")
        print(f"{tc:<20}" + "".join(f"{c:>{width}}" for c in cells))

    print(f"\nquestion-level rejects ({' > '.join(arms)}):")
    for lang in langs:
        cells = []
        for arm in arms:
            ok = [r for r in results if r["arm"] == arm and r["lang"] == lang and r["ok"]]
            cells.append(f"{sum(1 for r in ok if 'reject' in r['verdicts'])}/{len(ok)}")
        print(f"  {LANG_NAME[lang]}: " + " > ".join(cells))


def report_cost(db, arms: list[str], since: str) -> None:
    """Read spend back out of llm_calls — the run's own rows, by arm tag."""
    task_names = [f"flag_rate_{a}" for a in arms]
    rows = (
        db.table("llm_calls")
        .select("task_name, model, cost_usd")
        .in_("task_name", task_names)
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
    print("\n" + "=" * 88)
    print("COST  (pipeline='diag')")
    print("=" * 88)
    print(f"{'arm':<20}{'model':<32}{'calls':>7}{'usd':>10}{'usd/call':>11}")
    total = 0.0
    for (task, model), (n, usd) in sorted(agg.items()):
        total += usd
        print(f"{task:<20}{model:<32}{n:>7}{usd:>10.4f}{usd / n:>11.5f}")
    print(f"{'TOTAL':<59}{total:>10.4f}")


# ---------------------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sample", help="frozen sample JSON (list of question rows)")
    ap.add_argument(
        "--arms",
        default="live=4:",
        help="comma list of name=version:model; empty model = each row's own model",
    )
    ap.add_argument(
        "--judge-model",
        help="model slug applied to every arm that does not name one itself",
    )
    ap.add_argument("--langs", default="zh,en,ja")
    ap.add_argument("--subject-lines", help="JSON cache of qid -> subject line for slot {5}")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "6")))
    ap.add_argument("--out", default="judge_flag_rate_results.json")
    ap.add_argument("--report-only", help="re-print tables from a finished results JSON")
    args = ap.parse_args()

    if args.report_only:
        with open(args.report_only, encoding="utf-8") as fh:
            report(json.load(fh))
        return
    if not args.sample:
        raise SystemExit("[error] --sample is required (or use --report-only)")

    langs = [LANG_ID[name.strip()] for name in args.langs.split(",") if name.strip()]
    arms = _parse_arms(args.arms, args.judge_model)

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    rows = _load_sample(args.sample, langs)
    _map_type_codes(db, rows)
    per_lang = {LANG_NAME[k]: v for k, v in Counter(r["lang"] for r in rows).items()}
    print(
        f"sample: {len(rows)} questions, "
        f"{sum(len(r['distractors']) for r in rows)} distractors, per language {per_lang}"
    )
    print(f"type distribution {dict(Counter(r['type_code'] for r in rows))}")

    subjects = {}
    if args.subject_lines:
        with open(args.subject_lines, encoding="utf-8") as fh:
            subjects = json.load(fh)
        resolved = sum(1 for r in rows if subjects.get(r["qid"]))
        print(f"subject lines: {resolved}/{len(rows)} resolved")
    else:
        print("subject lines: none — slot {5} renders the inference fallback")

    jobs = []
    total = len(rows) * len(arms)
    for arm in arms:
        tpl = _load_templates(db, arm["version"], langs, arm["model"])
        print(
            f"arm {arm['name']}: v{arm['version']}  "
            + ", ".join(f"{LANG_NAME[lang]}={tpl[lang]['model']}" for lang in langs)
        )
        jobs += [
            (arm["name"], row, tpl, subjects.get(row["qid"], ""), total) for row in rows
        ]

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
