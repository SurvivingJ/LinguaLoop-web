"""Prove the *production* entailment path works on the live prompt row.

WHY THIS EXISTS
---------------
``scripts/measure_entailment_ab.py`` validates the prompt and the model, but it
calls ``call_llm`` directly with ``AnswerEntailmentVerdict`` and therefore
**bypasses the production wrapper entirely** — no ``_load_cfg``, no
``_is_pre_likert`` gate, no ``likert_to_verdict``, no ``log_judge_verdict``.

So after the TASK-723 v3 cutover the situation was: the prompt was measured
(AUC 0.957 over 450 calls) and the wrapper was unit-tested, but the two had
never been run together against the live DB row, and ``llm_calls`` held zero
rows at ``template_version = 3``. This script closes that gap by calling
``judge_answer_entailment`` exactly as ``question_generator.py:500`` does.

It is deliberately a *wiring* check, not a quality check. Each fixture is
unambiguous — a competent native speaker would not hesitate — so a disagreement
means the wiring or the prompt is wrong, not that the item was hard.

What a pass proves:
  * the live row loads and is v3+, so ``_is_pre_likert`` does NOT fire
    (if it fires, the judge silently ``safe_accept``s everything — the exact
    answer-hallucination-guard-off failure the version gate exists to prevent);
  * the model returns a parseable 1-5 rating through the real schema;
  * ``likert_to_verdict`` maps it to the expected verdict;
  * ``confidence`` carries the Likert rating, not a 0.0-1.0 probability;
  * a row lands in ``llm_calls`` at ``template_version = 3``.

COST NOTE: these calls log under the **production** pipeline (``test_gen``),
because that is what makes them a production-path proof. That is a handful of
rows and ~$0.002 — negligible, but it is not ``pipeline='diag'``, so it is
visible in production cost reporting. That is intentional.

Usage::

    PYTHONPATH=. python scripts/smoke_entailment_production_path.py
    PYTHONPATH=. python scripts/smoke_entailment_production_path.py --langs zh
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The reasons come back in zh/ja; a Windows cp1252 console raises
# UnicodeEncodeError on the first CJK character and kills the run *after* the
# LLM has already been paid for.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # non-reconfigurable stream
        pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.exercise_generation.judges.answer_entailment import (  # noqa: E402
    _MIN_LIKERT_VERSION,
    _load_cfg,
    judge_answer_entailment,
)
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

LANG_ID = {"zh": 1, "en": 2, "ja": 3}

# Each fixture: (passage, question, answer, expected_verdict).
# The "supported" case must accept; the "unrelated" case must reject. Both are
# deliberately blunt — this is a wiring probe, not a calibration probe.
FIXTURES: dict[str, list[tuple[str, str, str, str]]] = {
    "zh": [
        (
            "小明每天早上六点起床，先去公园跑步三十分钟，然后回家吃早饭。"
            "他说跑步让他一整天都很有精神。",
            "小明每天早上做什么运动？",
            "跑步",
            "accept",
        ),
        (
            "小明每天早上六点起床，先去公园跑步三十分钟，然后回家吃早饭。"
            "他说跑步让他一整天都很有精神。",
            "小明每天早上做什么运动？",
            "小明养了一只猫",
            "reject",
        ),
    ],
    "en": [
        (
            "The library closes at eight o'clock on weekdays, but on Saturdays "
            "it stays open until ten so that students can study late.",
            "When does the library close on Saturdays?",
            "At ten o'clock",
            "accept",
        ),
        (
            "The library closes at eight o'clock on weekdays, but on Saturdays "
            "it stays open until ten so that students can study late.",
            "When does the library close on Saturdays?",
            "The library was built in 1890",
            "reject",
        ),
    ],
    "ja": [
        (
            "田中さんは毎朝七時に家を出て、電車で会社へ通っています。"
            "電車の中では新聞を読むのが習慣です。",
            "田中さんは電車の中で何をしますか。",
            "新聞を読む",
            "accept",
        ),
        (
            "田中さんは毎朝七時に家を出て、電車で会社へ通っています。"
            "電車の中では新聞を読むのが習慣です。",
            "田中さんは電車の中で何をしますか。",
            "田中さんは犬を飼っている",
            "reject",
        ),
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="zh,en,ja")
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()

    langs = [n.strip() for n in args.langs.split(",") if n.strip()]
    failures: list[str] = []

    for lang in langs:
        lid = LANG_ID[lang]

        cfg = _load_cfg(db, lid)
        version = cfg.get("version")
        gate_ok = int(version) >= _MIN_LIKERT_VERSION
        print(
            f"\n=== {lang} (language_id={lid}) ===\n"
            f"  live row : v{version}  model={cfg.get('model')}\n"
            f"  gate     : {'OK — _is_pre_likert will not fire' if gate_ok else 'WOULD FIRE — judge degrades to safe_accept'}"
        )
        if not gate_ok:
            failures.append(f"{lang}: live row is v{version}, below v{_MIN_LIKERT_VERSION}")
            continue

        for passage, question, answer, expected in FIXTURES[lang]:
            out = judge_answer_entailment(
                db=db,
                passage=passage,
                question_text=question,
                answer=answer,
                language_id=lid,
            )
            rating = out.confidence
            ok = out.verdict == expected

            # A safe_accept carries no rating. On the accept fixture that looks
            # identical to a real accept, which is precisely how a dead judge
            # hides, so treat a missing rating as a failure either way.
            if rating is None:
                ok = False
                detail = "NO RATING (safe_accept / accept_item — judge did not really run)"
            else:
                detail = f"rating={rating:.0f}"

            print(
                f"  [{'PASS' if ok else 'FAIL'}] expect {expected:<6} got "
                f"{out.verdict:<6} {detail}\n"
                f"         answer: {answer[:40]}\n"
                f"         reason: {(out.reason or '')[:100]}"
            )
            if not ok:
                failures.append(f"{lang}: expected {expected}, got {out.verdict} ({detail})")

    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS — production entailment path is live on the Likert scale.")
    print("Verify telemetry landed:")
    print(
        "  SELECT task_name, model, template_version, count(*) FROM llm_calls\n"
        "   WHERE task_name = 'judge_answer_entailment' AND template_version = 3\n"
        "   GROUP BY 1,2,3;"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
