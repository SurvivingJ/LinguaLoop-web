"""Re-score historical Dual Translation grades under a chosen rubric version (TASK-627).

Bands are a pure function of (stored errors, rubric version) — tech spec §4 — so a
threshold/weight change can re-score every historical grade with ZERO model calls.
This utility recomputes the three DERIVED dimensions (accuracy / fidelity /
understandability) from each grade's stored `dt_error_instance` rows under a target
`dt_rubric_version.config`, keeps the model-judged dimensions (naturalness / range)
from the stored grade, recomputes the weighted-mean overall (renormalizing over the
present dimensions), and prints the before/after band deltas.

DRY-RUN BY DEFAULT — it writes nothing unless `--apply` is passed (and `--dry-run`
always wins if both are given). No OpenRouter / model calls are ever made.

    python scripts/rescore_dt_grades.py --rubric-version 5 --dry-run
    python scripts/rescore_dt_grades.py --rubric-version 5 --apply    # persists

Tier-0-resolved grades carry no stored errors, so the derived model scores their
accuracy/fidelity/understandability at full marks (no errors -> no penalty). Those
grades were assigned by the deterministic pre-pass, not the derived scorer, so they
are reported but SKIPPED on `--apply` unless `--include-tier0` is given.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

# Run-as-script bootstrap (mirrors scripts/run_dt_grading_eval.py): put the repo
# root on the path and load .env before importing app services.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.dimension_service import DimensionService  # noqa: E402
from services.dual_translation import scoring  # noqa: E402
from services.dual_translation.grader_cascade import get_active_taxonomy  # noqa: E402
from services.dual_translation.tier0 import RUBRIC_DIMENSIONS  # noqa: E402
from services.supabase_factory import SupabaseFactory, get_supabase_admin  # noqa: E402

DERIVED = scoring.DERIVED_DIMENSIONS  # accuracy, fidelity, understandability


def _chunks(seq, n=100):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _load_rubric_config(db, version: int) -> dict:
    resp = (
        db.table("dt_rubric_version")
        .select("config")
        .eq("version", version)
        .limit(1)
        .execute()
    )
    if not resp.data:
        raise SystemExit(f"[error] no dt_rubric_version row with version={version}")
    return resp.data[0]["config"]


def _submission_l2(db, submission_ids: list[int]) -> dict[int, str]:
    """submission_id -> l2 language code, via dt_submission.passage_id -> dt_passage."""
    passage_of: dict[int, int] = {}
    for chunk in _chunks(submission_ids):
        for row in db.table("dt_submission").select("id, passage_id").in_("id", chunk).execute().data:
            passage_of[row["id"]] = row["passage_id"]

    passage_ids = sorted({p for p in passage_of.values() if p is not None})
    l2_id_of: dict[int, int] = {}
    for chunk in _chunks(passage_ids):
        for row in db.table("dt_passage").select("id, l2_language_id").in_("id", chunk).execute().data:
            l2_id_of[row["id"]] = row["l2_language_id"]

    code_cache: dict[int, str] = {}
    out: dict[int, str] = {}
    for sid, pid in passage_of.items():
        l2_id = l2_id_of.get(pid)
        if l2_id is None:
            continue
        if l2_id not in code_cache:
            code_cache[l2_id] = DimensionService.get_language_code(l2_id) or "?"
        out[sid] = code_cache[l2_id]
    return out


def _errors_by_submission(db, submission_ids: list[int]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = defaultdict(list)
    for chunk in _chunks(submission_ids):
        rows = (
            db.table("dt_error_instance")
            .select("submission_id, subtype, severity, is_mistake")
            .in_("submission_id", chunk)
            .execute()
            .data
        )
        for row in rows:
            out[row["submission_id"]].append(row)
    return out


def _fmt_delta(dim: str, before, after) -> str:
    arrow = f"{before}->{after}" if before != after else f"{after}"
    return f"{dim[:3]} {arrow}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-score DT grades under a rubric version (TASK-627)")
    ap.add_argument("--rubric-version", type=int, required=True,
                    help="dt_rubric_version.version whose scoring config to score under")
    ap.add_argument("--dry-run", action="store_true",
                    help="preview only; never write (this is also the default)")
    ap.add_argument("--apply", action="store_true", help="persist the recomputed scores/overall_band")
    ap.add_argument("--include-tier0", action="store_true",
                    help="also rewrite tier-0-resolved grades (default: report but skip on --apply)")
    ap.add_argument("--all", action="store_true", help="print unchanged grades too")
    ap.add_argument("--limit", type=int, default=None, help="rescore at most N grades (newest first)")
    args = ap.parse_args()

    writing = args.apply and not args.dry_run

    SupabaseFactory.initialize()
    db = get_supabase_admin()
    if db is None:
        print("[error] no service-role Supabase client (SUPABASE_SERVICE_ROLE_KEY missing).", file=sys.stderr)
        return 2
    DimensionService.initialize(db)

    rubric_cfg = _load_rubric_config(db, args.rubric_version)
    # Fail fast: a pre-TASK-627 version has no scoring keys and cannot be scored under.
    scoring.scoring_params(rubric_cfg)
    subtype_meta = get_active_taxonomy(db).get("subtype_meta")
    if not subtype_meta:
        print("[error] active taxonomy has no subtype_meta (needs taxonomy v5, TASK-626).", file=sys.stderr)
        return 2

    q = db.table("dt_grade").select("id, submission_id, scores, overall_band, grader_trace").order("id", desc=True)
    if args.limit:
        q = q.limit(args.limit)
    grades = q.execute().data
    if not grades:
        print("[info] no dt_grade rows to rescore.")
        return 0

    submission_ids = sorted({g["submission_id"] for g in grades})
    l2_of = _submission_l2(db, submission_ids)
    errors_of = _errors_by_submission(db, submission_ids)

    banner = "APPLYING (writing)" if writing else "DRY RUN (no writes)"
    print(f"== rescore_dt_grades :: rubric v{args.rubric_version} :: {banner} :: {len(grades)} grades ==\n")

    changed = written = skipped_tier0 = 0
    tier_counts: dict[str, int] = defaultdict(int)

    for g in grades:
        sid = g["submission_id"]
        l2_code = l2_of.get(sid, "?")
        tier = (g.get("grader_trace") or {}).get("tier", "?")
        tier_counts[tier] += 1
        is_tier0 = tier == "tier0"

        errors = errors_of.get(sid, [])
        old_scores = g.get("scores") or {}
        new_dims = scoring.compute_dimension_bands(errors, subtype_meta, rubric_cfg)
        merged = {**old_scores, **new_dims}
        present = [d for d in RUBRIC_DIMENSIONS if d in merged]
        weights = scoring.resolve_weights(rubric_cfg, l2_code)
        new_overall = scoring.compute_overall(merged, weights, present)

        dims_changed = any(old_scores.get(d) != new_dims[d] for d in DERIVED)
        overall_changed = g.get("overall_band") != new_overall
        row_changed = dims_changed or overall_changed
        if row_changed:
            changed += 1

        if row_changed or args.all:
            dim_str = "  ".join(_fmt_delta(d, old_scores.get(d), new_dims[d]) for d in DERIVED)
            overall_str = _fmt_delta("overall", g.get("overall_band"), new_overall)
            flag = " [tier0: full-marks from 0 errors]" if is_tier0 and row_changed else ""
            print(f"grade {g['id']:>5} sub {sid:>5} [{l2_code} {tier}] {len(errors)} err  "
                  f"{dim_str}  | {overall_str}{flag}")

        if writing and row_changed:
            if is_tier0 and not args.include_tier0:
                skipped_tier0 += 1
                continue
            db.table("dt_grade").update(
                {"scores": merged, "overall_band": new_overall}
            ).eq("id", g["id"]).execute()
            written += 1

    print("\n-- summary --")
    print(f"grades scanned : {len(grades)}")
    print(f"changed        : {changed}")
    print("tier breakdown : " + ", ".join(f"{t}={n}" for t, n in sorted(tier_counts.items())))
    if writing:
        print(f"written        : {written}")
        if skipped_tier0:
            print(f"tier0 skipped  : {skipped_tier0} (pass --include-tier0 to rewrite)")
    else:
        print("written        : 0 (dry run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
