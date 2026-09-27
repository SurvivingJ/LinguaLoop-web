"""Pull a recent production sample of MC questions for entailment calibration.

Writes rows in the same shape as ``data/eval/entailment_sample_150.json``
(lang, qid, passage, question, answer, distractors, type_code) so both
``scripts/measure_entailment_ab.py`` and the jev calibration can consume them.
Questions already in the 150-row sample are excluded.

    PYTHONPATH=. python scripts/build_entailment_prod_sample.py --per-lang 50
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXISTING = os.path.join(ROOT, "data", "eval", "entailment_sample_150.json")


def _answer_text(raw):
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    return raw if isinstance(raw, str) else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-lang", type=int, default=50)
    ap.add_argument("--out", default=os.path.join(
        ROOT, "data", "eval", "entailment_prod_recent_2026-09-26.json"))
    args = ap.parse_args()

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    seen = {r["qid"] for r in json.load(open(EXISTING, encoding="utf-8"))}

    rows: list[dict] = []
    for lang in (1, 2, 3):
        tests = (
            db.table("tests").select("id, transcript, language_id, created_at")
            .eq("language_id", lang).not_.is_("transcript", "null")
            .order("created_at", desc=True).limit(400).execute().data
        )
        got = 0
        for t in tests:
            if got >= args.per_lang:
                break
            qs = (
                db.table("questions")
                .select("id, question_text, choices, answer, question_type_id")
                .eq("test_id", t["id"]).execute().data
            )
            # one question per test keeps passages diverse
            for q in qs:
                ans = _answer_text(q["answer"])
                choices = q["choices"]
                if q["id"] in seen or not ans or not isinstance(choices, list):
                    continue
                dis = [c for c in choices if c != ans]
                if len(dis) != 3 or len(choices) != 4:
                    continue
                rows.append({
                    "lang": lang, "qid": q["id"], "passage": t["transcript"],
                    "question": q["question_text"], "answer": ans,
                    "distractors": dis, "type_code": q["question_type_id"],
                })
                got += 1
                break
        print(f"lang {lang}: {got} questions")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=1)
    print(f"wrote {len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
