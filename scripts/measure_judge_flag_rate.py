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

    # TASK-726: score arms against the adjudicated gold set, reweighted
    python scripts/measure_judge_flag_rate.py \
        --gold data/eval/distractor_gold_2026-08.json --arms "live=4:" --report

Without a gold file this script measures how *often* a judge rejects, which is
a rate with no denominator of truth behind it — TASK-718 measured two models
whose reject sets were disjoint, and a flag rate could not say which was right.
`--gold` is the other question: how often it rejects the things a native
adjudicator says should be rejected. Both numbers come off the same code path
so an arm's flag rate and its precision are never computed on different content.

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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import distractor_gold as gold_lib  # noqa: E402
from services.llm_service import call_llm  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402
from services.test_generation.schemas import (  # noqa: E402
    AXIS_CONFUSABILITY,
    AXIS_FIT,
    DistractorPlausibilityVerdict,
    axes_to_verdict,
)

LANG_NAME = {1: "zh", 2: "en", 3: "ja"}

# Where file-backed arms (`name=@prefix:model`) look for their bodies.
EVAL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "eval")
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
        # `live` resolves per language to whichever row is active. Needed
        # because the three languages are not on the same judge version — zh
        # is v6 while en/ja are v4 — so a single integer cannot express "the
        # prompt production is actually running" across a three-language run.
        if version.strip().startswith("@"):
            # File-backed arm: `name=@prefix:model` reads data/eval/prefix_<lang>.txt.
            # An ablation is a throwaway measurement, and writing a throwaway row
            # into the live `prompt_templates` table to measure it is how version
            # collisions happen (TASK-723 destroyed two live rows that way). The
            # model still comes from the ACTIVE row unless overridden, so a
            # prompt ablation cannot silently become a model comparison.
            version_n = version.strip()
        elif version.strip().lower() in ("live", "active"):
            version_n = 0
        else:
            try:
                version_n = int(version)
            except ValueError:
                raise SystemExit(
                    f"[error] arm {name!r}: version {version!r} is not an int or 'live'"
                )
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


def _ver(v) -> str:
    """Render an arm's resolved version for the run banner."""
    return f"v{v}" if isinstance(v, int) else str(v)


def _load_templates(db, version, langs: list[int], override: str | None) -> dict:
    """Judge prompt body + model per language.

    `version=0` means the active row; an int means that version; a string
    starting with `@` means "read the body from `data/eval/<prefix>_<lang>.txt`
    and take the model from the active row" (see `_parse_arms`).
    """
    tpl = {}
    if isinstance(version, str) and version.startswith("@"):
        prefix = version[1:]
        # A bare filename stem, not a path. `--arms` is operator input, but the
        # arm name also tags the llm_calls cost rows, so a prefix with a
        # separator in it would produce a run whose spend cannot be attributed
        # and whose body came from somewhere nobody would think to look.
        if not prefix or not all(c.isalnum() or c in "._-" for c in prefix):
            raise SystemExit(
                f"[error] arm file prefix {prefix!r} must be a bare filename stem "
                f"(letters, digits, dot, dash, underscore) resolved under data/eval"
            )
        live = _load_templates(db, 0, langs, override)
        for lang in langs:
            path = os.path.join(EVAL_DIR, f"{prefix}_{LANG_NAME[lang]}.txt")
            if not os.path.exists(path):
                raise SystemExit(f"[error] arm file not found: {path}")
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            # Render it exactly as the judge will. A missing slot raises inside
            # the judge's try block and safe-accepts the whole batch silently,
            # so an unrenderable ablation body would read as "0 rejects".
            try:
                body.format("p", "q", "a", "1. A", "t", "s")
            except Exception as exc:
                raise SystemExit(f"[error] {path} does not render: {exc!r}")
            tpl[lang] = {
                "template_text": body,
                "model": override or live[lang]["model"],
                "version": prefix,
            }
        return tpl

    for lang in langs:
        q = (
            db.table("prompt_templates")
            .select("template_text, model, version")
            .eq("task_name", JUDGE_TASK)
            .eq("language_id", lang)
        )
        q = q.eq("is_active", True) if version <= 0 else q.eq("version", version)
        resp = q.execute()
        if not resp.data:
            raise SystemExit(
                f"[error] no {JUDGE_TASK} row for language_id={lang} "
                f"version={'active' if version <= 0 else version}"
            )
        row = resp.data[0]
        tpl[lang] = {
            "template_text": row["template_text"],
            "model": override or row["model"],
            "version": row["version"],
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
        # TASK-719: two axes. `ratings` stays the FIT axis under its old name —
        # a pre-v7 arm returns exactly one rating per distractor and it lands
        # there, so every arm in this table remains comparable across the split,
        # and the gold path (which scores one band per item) keeps working.
        ratings = list(obj.fit)[:n]
        confusability = list(obj.confusability)[:n]
        avs = [axes_to_verdict(f, c) for f, c in zip(ratings, confusability)]
        res = {
            "ok": True,
            "ratings": ratings,
            "confusability": confusability,
            # The judge's own account of each decision. Kept because a rating
            # with no reason attached cannot be audited after the fact: every
            # run before 2026-08-20 parsed this text, used it for nothing and
            # dropped it, so no claim about WHY the judge flagged anything was
            # checkable. `generation_review_queue` has always stored it, so the
            # measurement harness was the only place it went missing.
            "reasons": [str(x) for x in list(obj.reasons)[:n]],
            "distractors": list(row["distractors"])[:n],
            "verdicts": [av.verdict for av in avs],
            # Which axis drove each non-accept verdict — TASK-720's measurement.
            # An empty list means the distractor was accepted.
            "flag_axes": [list(av.axes) for av in avs],
        }
    except Exception as exc:  # noqa: BLE001 — one bad call must not lose the run
        res = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "ratings": [],
            "confusability": [],
            "reasons": [],
            "distractors": list(row["distractors"])[:n],
            "verdicts": [],
            "flag_axes": [],
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
    # Printed once per axis. On a pre-v7 arm the confusability table is entirely
    # `unrated`, which is the correct reading — that arm's prompt never asked.
    for axis, key in ((AXIS_FIT, "ratings"), (AXIS_CONFUSABILITY, "confusability")):
        print("\n" + "=" * 88)
        print(f"RATING DISTRIBUTION — {axis.upper()} AXIS  (distractor level)")
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
                vals = [x for r in sel if r["ok"] for x in r.get(key) or []]
                dist = Counter(x for x in vals if x is not None)
                unrated = sum(1 for x in vals if x is None)
                errs = sum(1 for r in sel if not r["ok"])
                used = "{" + ", ".join(str(b) for b in sorted(dist, reverse=True)) + "}"
                print(
                    f"{arm:<8}{LANG_NAME[lang]:<5}"
                    + "".join(f"{dist.get(b, 0):>6}" for b in (1, 2, 3, 4, 5))
                    + f"{unrated:>9}{errs:>5}{used:>16}"
                )
            print("-" * 88)

    # TASK-720: the review band is now "the judge is not confident", and the
    # queue records which axis it was unsure about. This table is the sizing the
    # task asks for before rollout — how much human review each axis buys, and
    # in which language, at the distractor level where the reviewer works.
    print("\n" + "=" * 88)
    print("REVIEW / REJECT LOAD BY AXIS  (distractor level)")
    print("=" * 88)
    print(
        f"{'arm':<8}{'lang':<5}{'items':>7}{'flag':>6}{'fit':>6}{'conf':>6}"
        f"{'both':>6}{'rej':>6}{'rej.fit':>9}{'rej.conf':>10}{'flag %':>9}"
    )
    for arm in arms:
        for lang in langs:
            sel = [r for r in results if r["arm"] == arm and r["lang"] == lang and r["ok"]]
            if not sel:
                continue
            items = flag = rej = 0
            axis_n: dict = Counter()
            for r in sel:
                # A results file written before TASK-719 has no `flag_axes`; it
                # still counts toward the rates, it just attributes nothing.
                axes_per = r.get("flag_axes") or []
                for i, verdict in enumerate(r["verdicts"]):
                    ax = axes_per[i] if i < len(axes_per) else []
                    items += 1
                    if verdict == "flag":
                        flag += 1
                        if ax:
                            axis_n["flag:" + ("both" if len(ax) > 1 else ax[0])] += 1
                    elif verdict == "reject":
                        rej += 1
                        for a in ax:
                            axis_n["rej:" + a] += 1
            if not items:
                continue
            print(
                f"{arm:<8}{LANG_NAME[lang]:<5}{items:>7}{flag:>6}"
                f"{axis_n['flag:' + AXIS_FIT]:>6}"
                f"{axis_n['flag:' + AXIS_CONFUSABILITY]:>6}"
                f"{axis_n['flag:both']:>6}{rej:>6}"
                f"{axis_n['rej:' + AXIS_FIT]:>9}"
                f"{axis_n['rej:' + AXIS_CONFUSABILITY]:>10}"
                f"{100.0 * flag / items:>8.1f}%"
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


# ------------------------------------------------------------------- gold scoring


def _gold_questions(items: list[dict]) -> list[dict]:
    """Rebuild judgeable question rows from frame items.

    Every distractor of a question is restored, including ones that were never
    selected for adjudication. The judge prompt shows the whole distractor list
    and rates it as a set; feeding it a subset would be measuring a prompt
    production never sends.
    """
    by_qid: dict[str, dict] = {}
    for it in sorted(items, key=lambda x: (x['qid'], x['distractor_index'])):
        q = by_qid.setdefault(it['qid'], {
            'qid': it['qid'],
            'lang': it['lang'],
            'passage': it['passage'],
            'question': it['question'],
            'answer': it['answer'],
            'type_code': it['type_code'],
            'distractors': [],
        })
        q['distractors'].append(it['distractor'])
    return list(by_qid.values())


def _stored_prerate_arms(frame: dict) -> dict[str, dict[str, int | None]]:
    """The frame's own pre-ratings, as scoreable arms.

    This is how TASK-718's disjoint reject sets get settled without spending
    anything: the frame was pre-rated with exactly that model pair, so scoring
    the stored ratings against the adjudicated labels answers "which model was
    right" directly.
    """
    out: dict[str, dict[str, int | None]] = defaultdict(dict)
    for it in frame['items']:
        for arm, pre in (it.get('prerate') or {}).items():
            out[f"prerate:{arm} ({pre.get('model') or '?'})"][it['item_id']] = \
                pre.get('rating')
    return dict(out)


def report_gold(frame: dict, arm_ratings: dict[str, dict[str, int | None]]) -> None:
    """Per-band precision/recall + AUC against the gold labels, reweighted."""
    scored = [
        it for it in frame['items']
        if it.get('selected') and gold_lib.primary_label(it) is not None
    ]
    if not scored:
        raise SystemExit(
            '[error] the gold file has no labelled items — it is a frame, not '
            'an adjudicated gold set. Run merge_distractor_gold.py first.'
        )

    langs = sorted({it['lang'] for it in scored})
    print('\n' + '=' * 92)
    print(f'GOLD SET  {frame.get("tag", "?")}  '
          f'({len(scored)} labelled items, weights applied)')
    print('=' * 92)

    tab = gold_lib.confusion_by_axis(scored)
    print('\ntopical_distance x confusable  (the TASK-719 premise, directly)')
    print(f"{'':<12}" + ''.join(f'{c:>12}' for c in gold_lib.CONFUSABLE))
    for td in gold_lib.TOPICAL_DISTANCE:
        print(f'{td:<12}' + ''.join(
            f'{tab.get((td, c), 0):>12}' for c in gold_lib.CONFUSABLE))

    for arm, ratings in arm_ratings.items():
        print('\n' + '-' * 92)
        print(f'ARM {arm}')
        print('-' * 92)
        for lang in langs + ['ALL']:
            sel = scored if lang == 'ALL' else [
                it for it in scored if it['lang'] == lang]
            rated = []
            for it in sel:
                band = ratings.get(it['item_id'])
                if band is None:
                    continue
                rated.append({
                    'band': int(band),
                    'gold': gold_lib.gold_reject(gold_lib.primary_label(it)),
                    'weight': float(it.get('frame_weight') or 0.0),
                })
            if not rated:
                continue
            bm = gold_lib.band_metrics(rated)
            vm = gold_lib.verdict_metrics(rated)
            auc = gold_lib.weighted_auc(
                [6 - r['band'] for r in rated if r['gold'] is not None],
                [bool(r['gold']) for r in rated if r['gold'] is not None],
                [r['weight'] for r in rated if r['gold'] is not None],
            )
            name = LANG_NAME[lang] if lang != 'ALL' else 'ALL'
            pct = lambda v: f'{100 * v:.0f}%' if v is not None else '  n/a'  # noqa: E731
            auc_s = f'{auc:.3f}' if auc is not None else 'n/a'
            print(f"\n  {name}: n={vm['n_scored']} scored "
                  f"(+{vm['n_borderline']} borderline, excluded)  AUC={auc_s}")
            print(f"    reject verdict: precision {pct(vm['precision'])}  "
                  f"recall {pct(vm['recall'])}  "
                  f"rate {pct(vm['weighted_reject_rate'])} vs gold "
                  f"{pct(vm['gold_reject_rate'])}")
            print(f"    {'band':<6}{'verdict':<9}{'n':>5}{'brdr':>6}"
                  f"{'precision':>11}{'recall':>9}")
            for band in gold_lib.BANDS:
                m = bm[band]
                if not m['n']:
                    continue
                print(f"    {band:<6}{m['verdict']:<9}{m['n']:>5}"
                      f"{m['n_borderline']:>6}{pct(m['precision']):>11}"
                      f"{pct(m['recall']):>9}")

    print('\nEvery precision/recall/rate above is reweighted to the production '
          'question mix via frame_weight; raw counts (n) are not.')


def _run_gold(args, langs: list[int]) -> None:
    """`--gold` entry point: score stored and (optionally) live arms."""
    with open(args.gold, encoding="utf-8") as fh:
        frame = json.load(fh)
    frame["items"] = [it for it in frame["items"] if it["lang"] in langs]

    arm_ratings = _stored_prerate_arms(frame)

    if args.gold_live_arms:
        SupabaseFactory.initialize()
        db = get_supabase_admin()
        rows = _gold_questions(frame["items"])
        arms = _parse_arms(args.arms, args.judge_model)
        since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 60))
        jobs = []
        total = len(rows) * len(arms)
        for arm in arms:
            tpl = _load_templates(db, arm["version"], langs, arm["model"])
            print(
                f"arm {arm['name']}: "
                + ", ".join(
                    f"{LANG_NAME[lang]}={_ver(tpl[lang]['version'])}:{tpl[lang]['model']}"
                    for lang in langs
                )
            )
            jobs += [(arm["name"], row, tpl, "", total) for row in rows]
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            results = list(ex.map(_judge_one, jobs))
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=1)
        by_key = {(r["arm"], r["qid"]): r for r in results}
        for arm in arms:
            live: dict[str, int | None] = {}
            for it in frame["items"]:
                res = by_key.get((arm["name"], it["qid"])) or {}
                ratings = res.get("ratings") or []
                idx = it["distractor_index"]
                live[it["item_id"]] = ratings[idx] if idx < len(ratings) else None
            arm_ratings[f"live:{arm['name']}"] = live
        report_cost(db, [a["name"] for a in arms], since)

    report_gold(frame, arm_ratings)


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
    ap.add_argument(
        "--gold",
        help="adjudicated gold file — score arms against it instead of "
             "reporting a bare flag rate (TASK-726)",
    )
    ap.add_argument(
        "--gold-live-arms",
        action="store_true",
        help="with --gold, also judge the gold questions live under --arms; "
             "off by default because the frame's stored pre-ratings already "
             "answer the TASK-718 question for free",
    )
    args = ap.parse_args()

    if args.report_only:
        with open(args.report_only, encoding="utf-8") as fh:
            report(json.load(fh))
        return

    langs = [LANG_ID[name.strip()] for name in args.langs.split(",") if name.strip()]

    if args.gold:
        _run_gold(args, langs)
        return

    if not args.sample:
        raise SystemExit("[error] --sample is required (or use --report-only/--gold)")

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
            f"arm {arm['name']}: "
            + ", ".join(
                f"{LANG_NAME[lang]}={_ver(tpl[lang]['version'])}:{tpl[lang]['model']}"
                for lang in langs
            )
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
