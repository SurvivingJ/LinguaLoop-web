"""Shadow-window harness for the entailment judge backends (TASK-833).

Drives the REAL question-generation funnel -- ``QuestionGenerator.generate_questions``
with the live prompt templates and the live entailment judge, regeneration on reject
included -- over existing production passages, and records every entailment call.
Unlike the stored ``questions`` table (post-judge survivors only) this sees the
*pre-filter* candidates, i.e. the hallucinated answers the judge exists to catch.

NO DATABASE WRITES to tests / questions / generation_review_queue: it calls the
generator directly, never ``TestGenerationOrchestrator``. Side effects are
``llm_calls`` rows and API spend, both reported.

One deliberate deviation from production: the DISTRACTOR judge is stubbed to
accept. The subject is the entailment backend; running the distractor judge in
every arm would add spend and noise (its rejects trigger regeneration too) that
is identical across arms. State this when quoting any survival figure.

Arms (``--backend``): ``shadow`` (LLM verdict authoritative, jev logged beside
it), ``jev`` (jev authoritative, LLM fallback), ``llm``. The passages are chosen
with ``--seed``, so different arms see the same passages.

    PYTHONPATH=. python scripts/shadow_entailment_window.py --backend shadow \
        --passages-per-lang 20 --out data/eval/entailment_shadow_window_2026-09-27/shadow
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

LANGS = {"zh": (1, "Chinese"), "en": (2, "English"), "ja": (3, "Japanese")}
DEFAULT_TYPES = "literal_detail,vocabulary_context,main_idea,inference,supporting_detail"

_tl = threading.local()
_records: list[dict] = []
_summaries: list[dict] = []
_lock = threading.Lock()


class _CountFallbacks(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.jev_failures = 0

    def emit(self, record):
        msg = record.getMessage()
        if "jev backend failed" in msg or "shadow: jev failed" in msg:
            self.jev_failures += 1


def _install_recorders(backend: str) -> _CountFallbacks:
    import services.exercise_generation.judges.answer_entailment as ae
    import services.exercise_generation.judges.distractor_plausibility as dp
    from services.exercise_generation.judges.base import JudgeOutcome

    os.environ[ae._BACKEND_ENV] = backend

    # Distractor judge -> accept (see module docstring).
    dp.judge_distractor_plausibility = lambda **kw: [
        JudgeOutcome(verdict="accept", confidence=5.0, reason="stub")
        for _ in kw["distractors"]
    ]

    def observer(passage, question, answer, lang_id, live, jv):
        _tl.shadow = {"jev_verdict": jv.verdict, "jev_p": jv.probability,
                      "live_verdict": live.verdict, "live_rating": live.confidence}

    ae.shadow_observer = observer
    orig = ae.judge_answer_entailment

    def recording(db, passage, question_text, answer, language_id):
        _tl.shadow = None
        out = orig(db, passage, question_text, answer, language_id)
        rec = {
            # NB the generator fans question types out to a thread pool, so a
            # thread-local test_id set on the passage thread is NOT visible here
            # (all ids were None in the 2026-09-27 run). The passage itself is the
            # reliable key.
            "arm": backend, "lang": language_id, "passage": passage,
            "question": question_text, "answer": answer,
            "verdict": out.verdict, "backend": out.backend,
            "probability": out.probability, "rating": out.confidence,
            "reason": out.reason, **(_tl.shadow or {}),
        }
        with _lock:
            _records.append(rec)
        return out

    ae.judge_answer_entailment = recording
    handler = _CountFallbacks()
    logging.getLogger(ae.__name__).addHandler(handler)
    return handler


def _pick_passages(db, lang_id: int, n: int, seed: int, skip: int = 0) -> list[dict]:
    rows = (
        db.table("tests").select("id,transcript,difficulty,created_at")
        .eq("language_id", lang_id).not_.is_("transcript", "null").gt("difficulty", 2)
        .order("created_at", desc=True).limit(300).execute().data
    )
    rows = [r for r in rows if r["transcript"] and len(r["transcript"]) > 200]
    random.Random(seed + lang_id).shuffle(rows)
    return rows[skip:skip + n]


def _run_passage(code, lang_id, lang_name, row, types, templates, model, version, db):
    from services.test_generation.agents import QuestionGenerator

    _tl.test_id = row["id"]
    t0 = time.time()
    err = None
    n = 0
    try:
        gen = QuestionGenerator()
        qs = gen.generate_questions(
            prose=row["transcript"], language_name=lang_name,
            question_type_codes=types, difficulty=row["difficulty"],
            prompt_templates=templates, model_override=model,
            language_id=lang_id, db=db, template_version=version, language_code=code,
        )
        n = len(qs)
    except Exception as exc:  # noqa: BLE001 -- one passage must not lose the run
        err = f"{type(exc).__name__}: {exc}"
    with _lock:
        _summaries.append({
            "lang": code, "test_id": row["id"], "difficulty": row["difficulty"],
            "requested": len(types), "survived": n, "seconds": round(time.time() - t0, 1),
            "error": err,
        })


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--backend", choices=["shadow", "jev", "llm"], required=True)
    ap.add_argument("--passages-per-lang", type=int, default=10)
    ap.add_argument("--types", default=DEFAULT_TYPES)
    ap.add_argument("--langs", default="zh,en,ja")
    ap.add_argument("--seed", type=int, default=927)
    ap.add_argument("--skip", type=int, default=0,
                    help="skip the first N shuffled passages (already used by an earlier run)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True, help="output path prefix")
    args = ap.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    from config import Config
    from services.supabase_factory import SupabaseFactory
    from services.prompt_service import get_template_config
    from services.test_generation.database_client import TestDatabaseClient

    SupabaseFactory.initialize(
        supabase_url=Config.SUPABASE_URL, supabase_key=Config.SUPABASE_KEY,
        service_role_key=Config.SUPABASE_SERVICE_ROLE_KEY,
    )
    db_client = TestDatabaseClient()
    db = db_client.client
    handler = _install_recorders(args.backend)

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    started = datetime.now(timezone.utc)
    jobs = []
    passages: dict[str, str] = {}
    for code in [c.strip() for c in args.langs.split(",") if c.strip()]:
        lang_id, lang_name = LANGS[code]
        cfg = get_template_config(db, f"question_{types[0]}", lang_id)
        templates = {t: db_client.get_prompt_template(f"question_{t}", lang_id) for t in types}
        for row in _pick_passages(db, lang_id, args.passages_per_lang, args.seed, args.skip):
            passages[row["id"]] = row["transcript"]
            jobs.append((code, lang_id, lang_name, row, types, templates,
                         cfg["model"], cfg["version"], db))
    print(f"{args.backend}: {len(jobs)} passages x {len(types)} types", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda j: _run_passage(*j), jobs))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out + "_calls.json", "w", encoding="utf-8") as fh:
        json.dump({"records": _records, "summaries": _summaries, "passages": passages,
                   "jev_failures": handler.jev_failures,
                   "started": started.isoformat(), "backend": args.backend},
                  fh, ensure_ascii=False, indent=1)

    req = sum(s["requested"] for s in _summaries)
    sur = sum(s["survived"] for s in _summaries)
    errs = sum(1 for s in _summaries if s["error"])
    print(f"passages={len(_summaries)} requested={req} survived={sur} ({sur/max(req,1):.0%}) "
          f"passage_errors={errs} entailment_calls={len(_records)} "
          f"jev_failures={handler.jev_failures}")

    # spend, read back from llm_calls for this window
    try:
        rows = (db.table("llm_calls").select("task_name,model,cost_usd")
                .gte("created_at", started.isoformat()).eq("pipeline", "test_gen")
                .execute().data)
        by: dict = {}
        for r in rows:
            k = (r["task_name"], r["model"])
            c = by.setdefault(k, [0, 0.0, 0])
            c[0] += 1
            c[1] += r["cost_usd"] or 0.0
            c[2] += r["cost_usd"] is None
        total = sum(v[1] for v in by.values())
        for (t, m), v in sorted(by.items(), key=lambda kv: -kv[1][1]):
            print(f"  {t:<36}{m:<38}{v[0]:>5} calls ${v[1]:.4f}" + (f"  ({v[2]} NULL cost)" if v[2] else ""))
        print(f"  TOTAL ${total:.4f} ({len(rows)} rows)")
    except Exception as exc:  # noqa: BLE001
        print("cost readback failed:", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
