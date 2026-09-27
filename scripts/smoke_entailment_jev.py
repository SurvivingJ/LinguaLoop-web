"""Live wiring check for the jev entailment backend (ENTAILMENT_JUDGE_BACKEND).

Runs the blunt accept/reject fixtures from ``smoke_entailment_production_path``
through ``judge_answer_entailment`` with the backend forced to ``jev`` and then
``shadow``, and proves what mocks cannot:

  * the real Decisions endpoint answers and the verdicts are the expected ones;
  * a jev outcome carries ``probability`` and NO ``confidence``;
  * ``llm_calls.cost_usd`` is NON-NULL on the rows written (four incumbent
    guardrails were silently inert for months because that column stayed NULL);
  * shadow mode returns the LLM verdict and writes a
    ``judge_answer_entailment_shadow`` row.

Rows are logged under the production pipeline (``test_gen``) on purpose -- that
is what makes this a production-path proof. It is a handful of calls,
well under a cent.

    PYTHONPATH=. python scripts/smoke_entailment_jev.py
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from scripts.smoke_entailment_production_path import FIXTURES, LANG_ID  # noqa: E402
from services.exercise_generation.judges import answer_entailment as ae  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402


def main() -> int:
    SupabaseFactory.initialize()
    db = get_supabase_admin()
    failures: list[str] = []
    started = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 5))

    os.environ[ae._BACKEND_ENV] = "jev"
    print("== backend=jev ==")
    for lang, fixtures in FIXTURES.items():
        for passage, question, answer, expected in fixtures:
            out = ae.judge_answer_entailment(db, passage, question, answer, LANG_ID[lang])
            ok = (out.verdict == expected and out.backend == "jev"
                  and out.probability is not None and out.confidence is None)
            print(f"  [{'PASS' if ok else 'FAIL'}] {lang} expect {expected:<6} got "
                  f"{out.verdict:<6} backend={out.backend} p={out.probability}")
            if not ok:
                failures.append(f"jev {lang} {expected}: {out}")

    os.environ[ae._BACKEND_ENV] = "shadow"
    print("== backend=shadow ==")
    passage, question, answer, expected = FIXTURES["en"][0]
    out = ae.judge_answer_entailment(db, passage, question, answer, LANG_ID["en"])
    ok = out.backend == "llm" and out.verdict == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] returned backend={out.backend} verdict={out.verdict}")
    if not ok:
        failures.append(f"shadow returned {out}")

    time.sleep(1.5)
    print("== llm_calls rows since start ==")
    rows = (
        db.table("llm_calls")
        .select("task_name,model,cost_usd,judge_verdict,judge_confidence,created_at")
        .like("model", "typesafe%")
        .gte("created_at", started)
        .execute()
        .data
    )
    print(f"  {len(rows)} jev rows")
    # Verdict-summary rows (judge_verdict set) carry no cost by design -- the raw
    # round-trip row owns it, and counting it twice would double the spend.
    raw = [r for r in rows if r["judge_verdict"] is None]
    if not raw:
        failures.append("no raw jev round-trip rows reached llm_calls")
    null_cost = [r for r in raw if r["cost_usd"] is None]
    if null_cost:
        failures.append(f"{len(null_cost)}/{len(raw)} raw jev rows have NULL cost_usd")
    else:
        print(f"  cost_usd non-NULL on all {len(raw)} raw rows "
              f"(total ${sum(r['cost_usd'] for r in raw):.6f})")
    shadow = [r for r in rows if r["task_name"] == "judge_answer_entailment_shadow"]
    if not shadow:
        failures.append("shadow mode wrote no judge_answer_entailment_shadow row")

    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
