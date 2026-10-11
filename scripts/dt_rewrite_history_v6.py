#!/usr/bin/env python3
"""Dual Translation — one-time rewrite of historical DT records to taxonomy v6 (TASK-852).

ADR-031 user decisions 2026-10-04 (wiki/decisions/ADR-031-dt-taxonomy-v6-merge.md):
  2. split v5 types are bulk-remapped to the closest v6 type with a review flag;
  3. ONE-TIME rewrite of every historical record to v6 names at cutover, snapshot
     first; rollback = restore the snapshot + revert the taxonomy version;
  4. ja ``script_choice`` profile entries, their error instances and their cards
     (with those cards' reviews) are DELETED after the snapshot. Past ``dt_grade``
     bands are NOT recalculated (dt_grade / dt_submission are never touched).

Split of responsibilities:
  * THIS MODULE owns every decision. ``plan_rewrite`` is a pure function over
    plain row dicts that decides, per row, what the rewrite does: v6 slug,
    remap_flag, merge survivor + aggregated count / severity_rank / trend, the
    child-first delete set. It is what the tests exercise.
  * ``migrations/dt_rewrite_history_v6.sql`` owns the transaction.
    ``dt_rewrite_history_v6(p_plan jsonb, p_dry_run boolean)`` executes a plan
    in ONE transaction (PostgREST cannot run multi-statement transactions):
    locks the four tables, fails closed on a non-empty snapshot or a stale plan,
    snapshots, writes child-first, checks the post-conditions (raise = rollback)
    and that every statement's row count equals the plan.
    ``dt_restore_history_v5(...)`` undoes it from the snapshot.

Covered tables (TASK-836 swept information_schema + the jsonb columns: these are
the only subtype-bearing columns): dt_error_instance.subtype,
dt_error_profile_entry.subtype, dt_card.subtype, plus dt_card_review rows that
die with their card. dt_grade.grader_trace / dt_grade.diff / dt_card.prompt_payload
carry no "subtype" key (0 hits live) and are deliberately not rewritten.

Mapping source: the v6 ``dt_taxonomy_version`` row's ``legacy_aliases`` (built by
scripts/build_dt_taxonomy_v6.py from data/eval/taxonomy_merge_2026-09-27/
v5_to_merged.csv) and its ``pairs`` lists — the same row the SQL function checks
the post-conditions against. ``--offline-taxonomy`` rebuilds them from the CSV.

Usage (TASK-853 cutover only; nightly cron paused, v6 active, app restarted):
    python scripts/dt_rewrite_history_v6.py                 # --dry-run (default): read-only plan
    python scripts/dt_rewrite_history_v6.py --plan-out p.json
    python scripts/dt_rewrite_history_v6.py --rehearse      # SQL runs the plan, then rolls back
    python scripts/dt_rewrite_history_v6.py --apply         # snapshot + rewrite, one transaction
    python scripts/dt_rewrite_history_v6.py --restore [--confirm-drop-snapshot]

``--dry-run`` only SELECTs. ``--rehearse`` executes the real function with
``p_dry_run = true`` (it takes the table locks and rolls everything back).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.dual_translation import synthesis  # pure; no DB / Flask imports

logger = logging.getLogger("dt_rewrite_history_v6")

TARGET_VERSION = 6
FLAG_SPLIT = "split_needs_review"
FLAG_MERGED = "merged"
# Survivor precedence for a profile merge (TASK-852): drilling > queued > watching > resolved.
STATUS_PRECEDENCE = {
    synthesis.STATUS_DRILLING: 3,
    synthesis.STATUS_QUEUED: 2,
    synthesis.STATUS_WATCHING: 1,
    synthesis.STATUS_RESOLVED: 0,
}
DEFAULT_WINDOW_DAYS = int(os.environ.get("DT_SYNTHESIS_WINDOW_DAYS", "30"))
_PAGE = 1000  # PostgREST default max rows per response


class PlanError(RuntimeError):
    pass


# ============================================================================
# Taxonomy
# ============================================================================


@dataclass(frozen=True)
class Taxonomy:
    version: int
    aliases: dict  # v5 slug -> {"to": v6 slug | None, "kind": "1:1"|"merge"|"split"|"dropped"}
    slugs: frozenset  # union of every pairs[*].subtypes list

    @classmethod
    def from_row(cls, version: int, taxonomy: dict) -> "Taxonomy":
        pairs = (taxonomy or {}).get("pairs") or {}
        slugs = frozenset(s for p in pairs.values() for s in (p or {}).get("subtypes", []))
        aliases = (taxonomy or {}).get("legacy_aliases") or {}
        if not slugs:
            raise PlanError(f"taxonomy v{version} has no pair lists")
        if not aliases:
            raise PlanError(f"taxonomy v{version} has no legacy_aliases")
        for slug, a in aliases.items():
            to, kind = a.get("to"), a.get("kind")
            if kind not in ("1:1", "merge", "split", "dropped"):
                raise PlanError(f"legacy_aliases[{slug}]: unknown kind {kind!r}")
            if (to is None) != (kind == "dropped"):
                raise PlanError(f"legacy_aliases[{slug}]: 'to' must be null iff kind is dropped")
            if to is not None and to not in slugs:
                raise PlanError(f"legacy_aliases[{slug}]: target {to!r} is not a v{version} slug")
            # Restore safety: a v5 slug that is ALSO a live v6 slug must map to
            # itself, otherwise restoring v5 names could transiently collide on
            # the profile UNIQUE key (and a v6-named row would be ambiguous).
            if slug in slugs and to != slug:
                raise PlanError(f"legacy_aliases[{slug}]: is a v{version} slug but maps to {to!r}")
        return cls(version=version, aliases=dict(aliases), slugs=slugs)

    @property
    def dropped(self) -> frozenset:
        return frozenset(s for s, a in self.aliases.items() if a.get("to") is None)


def taxonomy_from_source_files() -> Taxonomy:
    """v6 aliases + pair lists rebuilt from data/eval/taxonomy_merge_2026-09-27
    exactly as scripts/build_dt_taxonomy_v6.py builds the seed (offline / tests)."""
    from scripts import build_dt_taxonomy_v6 as builder

    merged = builder.load_merged()
    return Taxonomy.from_row(
        builder.VERSION,
        {
            "pairs": builder.build_pairs(merged),
            "legacy_aliases": builder.build_legacy_aliases(builder.load_mapping(), merged),
        },
    )


@dataclass(frozen=True)
class Resolution:
    kind: str  # noop | stamp | rename | merge | split | delete | unmappable
    to: str | None
    flag: str | None


def resolve(subtype: str, taxonomy_version, tax: Taxonomy) -> Resolution:
    """What the rewrite does to one row's ``subtype``.

    ``taxonomy_version`` = the vocabulary the slug is in (TASK-842). A row already
    stamped with the target version is left alone when its slug is a v6 slug.
    Everything else is mapped through ``legacy_aliases`` first (so a v5 slug is
    always read as v5), then accepted as-is if it is already a v6 slug (written
    after activation but before stamping) — both cases end stamped v6.
    """
    if taxonomy_version == tax.version:
        if subtype in tax.slugs:
            return Resolution("noop", subtype, None)
        return Resolution("unmappable", None, None)
    alias = tax.aliases.get(subtype)
    if alias is not None:
        to, kind = alias["to"], alias["kind"]
        if kind == "dropped":
            return Resolution("delete", None, None)
        if kind == "split":
            return Resolution("split", to, FLAG_SPLIT)
        if to == subtype:
            return Resolution("stamp", to, None)
        return Resolution("merge" if kind == "merge" else "rename", to, None)
    if subtype in tax.slugs:
        return Resolution("stamp", subtype, None)
    return Resolution("unmappable", None, None)


# ============================================================================
# Pure planner
# ============================================================================


def _ts(value) -> datetime | None:
    if value is None or isinstance(value, datetime):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def _status_key(row: dict):
    # max() over this picks the survivor: most advanced status, tie -> lowest id.
    return (STATUS_PRECEDENCE.get(row.get("remediation_status"), -1), -int(row["id"]))


def combine_trends(trends: list) -> dict | None:
    """Fallback trend for a merged profile row with no in-window errors.

    ``trend`` is one ``synthesis.build_trend`` snapshot per row (not a dated
    series), so "combined by date (summed)" is: counts summed, the latest
    ``as_of`` / its ``window_days`` kept, ``delta_pct`` recomputed with the
    build_trend formula."""
    trends = [t for t in trends if isinstance(t, dict)]
    if not trends:
        return None
    latest = max(trends, key=lambda t: str(t.get("as_of") or ""))
    current = sum(int(t.get("current_count") or 0) for t in trends)
    previous = sum(int(t.get("previous_count") or 0) for t in trends)
    delta = round((current - previous) / previous * 100.0, 1) if previous > 0 else None
    return {
        "window_days": latest.get("window_days"),
        "as_of": latest.get("as_of"),
        "current_count": current,
        "previous_count": previous,
        "delta_pct": delta,
    }


def plan_rewrite(
    *,
    errors: list[dict],
    profiles: list[dict],
    cards: list[dict],
    reviews: list[dict],
    tax: Taxonomy,
    now: datetime,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict:
    """Decide the whole rewrite. Pure: no DB, deterministic for fixed inputs.

    Row shapes (extra keys ignored):
      errors   id, subtype, taxonomy_version, remap_flag, severity, is_mistake,
               created_at, user_id, l1_language_id, l2_language_id
               (the last three joined from dt_submission/dt_passage; None if the
               join failed — the row is still rewritten, it just cannot count
               towards a merged severity_rank)
      profiles id, user_id, l1_language_id, l2_language_id, subtype, count,
               severity_rank, trend, remediation_status, taxonomy_version, remap_flag
      cards    id, profile_entry_id, origin_error_id, subtype, taxonomy_version
      reviews  id, card_id

    Returns a JSON-serialisable plan; ``plan["unmappable"]`` non-empty means the
    plan must not be applied (the SQL post-conditions would reject it anyway).
    """
    now = _ts(now)
    v = tax.version
    unmappable: list[dict] = []
    kinds: dict[str, Counter] = {t: Counter() for t in ("error_instance", "profile_entry", "card", "card_review")}

    # ---- dt_error_instance --------------------------------------------------
    error_updates, error_deletes = [], []
    error_target: dict[int, str] = {}
    for e in sorted(errors, key=lambda r: r["id"]):
        r = resolve(e["subtype"], e.get("taxonomy_version"), tax)
        kinds["error_instance"][r.kind] += 1
        if r.kind == "unmappable":
            unmappable.append({"table": "dt_error_instance", "id": e["id"], "subtype": e["subtype"]})
        elif r.kind == "delete":
            error_deletes.append({"id": e["id"], "from_subtype": e["subtype"]})
        else:
            error_target[e["id"]] = r.to
            if r.kind != "noop":
                error_updates.append({
                    "id": e["id"],
                    "from_subtype": e["subtype"],
                    "from_version": e.get("taxonomy_version"),
                    "subtype": r.to,
                    "taxonomy_version": v,
                    "remap_flag": r.flag or e.get("remap_flag"),
                })
    deleted_error_ids = {d["id"] for d in error_deletes}

    # ---- dt_error_profile_entry -------------------------------------------
    profile_updates, profile_deletes = [], []
    groups: dict[tuple, list[tuple[dict, Resolution]]] = defaultdict(list)
    dropped_profile_ids: set = set()
    for p in sorted(profiles, key=lambda r: r["id"]):
        r = resolve(p["subtype"], p.get("taxonomy_version"), tax)
        if r.kind == "unmappable":
            kinds["profile_entry"][r.kind] += 1
            unmappable.append({"table": "dt_error_profile_entry", "id": p["id"], "subtype": p["subtype"]})
        elif r.kind == "delete":
            kinds["profile_entry"][r.kind] += 1
            dropped_profile_ids.add(p["id"])
            profile_deletes.append({"id": p["id"], "from_subtype": p["subtype"], "reason": "dropped"})
        else:
            groups[(p["user_id"], p["l1_language_id"], p["l2_language_id"], r.to)].append((p, r))

    # Error instances that will carry each v6 profile key after the rewrite.
    current_cutoff = now - timedelta(days=window_days)
    previous_cutoff = now - timedelta(days=2 * window_days)
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for e in synthesis.gate_mistakes(errors):
        if e["id"] in error_target and e.get("user_id") is not None and e.get("l2_language_id") is not None:
            by_key[(e["user_id"], e["l1_language_id"], e["l2_language_id"], error_target[e["id"]])].append(e)

    survivor_of: dict[int, int] = {}  # every kept profile id -> id of the row that holds its v6 key
    collisions = []
    for key in sorted(groups, key=lambda k: tuple(str(x) for x in k)):
        members = groups[key]
        target = key[3]
        if len(members) == 1:
            p, r = members[0]
            survivor_of[p["id"]] = p["id"]
            kinds["profile_entry"][r.kind] += 1
            if r.kind != "noop":
                profile_updates.append({
                    "id": p["id"],
                    "from_subtype": p["subtype"],
                    "from_version": p.get("taxonomy_version"),
                    "subtype": target,
                    "count": p["count"],
                    "severity_rank": p["severity_rank"],
                    "trend": p.get("trend"),
                    "remediation_status": p["remediation_status"],
                    "taxonomy_version": v,
                    "remap_flag": r.flag or p.get("remap_flag"),
                })
            continue

        rows = [p for p, _ in members]
        survivor = max(rows, key=_status_key)
        in_window = [e for e in by_key.get(key, []) if _ts(e["created_at"]) > current_cutoff]
        prev_window = [
            e for e in by_key.get(key, [])
            if previous_cutoff < _ts(e["created_at"]) <= current_cutoff
        ]
        if in_window:
            rank = synthesis.severity_rank(in_window)
            trend = synthesis.build_trend(
                current_count=len(in_window), prev_count=len(prev_window),
                window_days=window_days, now=now,
            )
        else:
            rank = max(float(p["severity_rank"]) for p in rows)
            trend = combine_trends([p.get("trend") for p in rows])
        # A merge that absorbed a split row still needs a human look: the review
        # flag wins over the informational 'merged' (the CHECK allows one value).
        flag = FLAG_SPLIT if any(r.flag == FLAG_SPLIT for _, r in members) else FLAG_MERGED
        profile_updates.append({
            "id": survivor["id"],
            "from_subtype": survivor["subtype"],
            "from_version": survivor.get("taxonomy_version"),
            "subtype": target,
            "count": sum(int(p["count"]) for p in rows),
            "severity_rank": float(rank),
            "trend": trend,
            "remediation_status": survivor["remediation_status"],
            "taxonomy_version": v,
            "remap_flag": flag,
        })
        kinds["profile_entry"]["merge_survivor"] += 1
        for p in rows:
            survivor_of[p["id"]] = survivor["id"]
            if p["id"] != survivor["id"]:
                kinds["profile_entry"]["merge_away"] += 1
                profile_deletes.append({"id": p["id"], "from_subtype": p["subtype"], "reason": "merged_away"})
        collisions.append({
            "key": {"user_id": key[0], "l1_language_id": key[1], "l2_language_id": key[2], "subtype": target},
            "rows": [{"id": p["id"], "subtype": p["subtype"], "remediation_status": p["remediation_status"],
                      "count": p["count"]} for p in rows],
            "survivor_id": survivor["id"],
            "severity_basis": "in_window" if in_window else "fallback_max",
        })
    target_of_profile = {u["id"]: u["subtype"] for u in profile_updates}
    for key, members in groups.items():
        for p, _ in members:
            target_of_profile.setdefault(p["id"], key[3])

    # ---- dt_card ------------------------------------------------------------
    card_updates, card_deletes = [], []
    for c in sorted(cards, key=lambda r: r["id"]):
        reason = None
        if c["subtype"] in tax.dropped and c.get("taxonomy_version") != v:
            reason = "dropped_subtype"
        elif c.get("profile_entry_id") in dropped_profile_ids:
            reason = "dropped_profile_entry"
        elif c.get("origin_error_id") in deleted_error_ids:
            reason = "dropped_origin_error"
        if reason:
            kinds["card"]["delete"] += 1
            card_deletes.append({"id": c["id"], "reason": reason})
            continue
        pe = c.get("profile_entry_id")
        if pe is not None and pe in survivor_of:
            new_pe = survivor_of[pe]
            new_subtype = target_of_profile[new_pe]
            kind = "repoint" if new_pe != pe else ("noop" if (new_subtype == c["subtype"] and c.get("taxonomy_version") == v) else "follow_entry")
        else:
            # No profile entry (nullable FK), or one the plan cannot place (an
            # unmappable entry) — map the card's own slug.
            r = resolve(c["subtype"], c.get("taxonomy_version"), tax)
            if r.kind == "unmappable":
                kinds["card"]["unmappable"] += 1
                unmappable.append({"table": "dt_card", "id": c["id"], "subtype": c["subtype"]})
                continue
            new_pe, new_subtype, kind = pe, r.to, r.kind
        kinds["card"][kind] += 1
        if kind != "noop":
            card_updates.append({
                "id": c["id"],
                "from_subtype": c["subtype"],
                "from_version": c.get("taxonomy_version"),
                "from_profile_entry_id": pe,
                "subtype": new_subtype,
                "profile_entry_id": new_pe,
                "taxonomy_version": v,
            })
    deleted_card_ids = {d["id"] for d in card_deletes}

    # ---- dt_card_review (child of every deleted card) -------------------------
    review_deletes = [
        {"id": r["id"], "card_id": r["card_id"]}
        for r in sorted(reviews, key=lambda r: r["id"]) if r["card_id"] in deleted_card_ids
    ]
    kinds["card_review"]["delete"] += len(review_deletes)

    plan = {
        "taxonomy_version": v,
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "error_updates": error_updates,
        "error_deletes": error_deletes,
        "profile_updates": profile_updates,
        "profile_deletes": profile_deletes,
        "card_updates": card_updates,
        "card_deletes": card_deletes,
        "review_deletes": review_deletes,
        "collisions": collisions,
        "unmappable": unmappable,
        "kinds": {t: dict(sorted(c.items())) for t, c in kinds.items()},
    }
    plan["counts"] = plan_counts(plan)
    return plan


PLAN_LISTS = (
    "error_updates", "error_deletes", "profile_updates", "profile_deletes",
    "card_updates", "card_deletes", "review_deletes",
)


def plan_counts(plan: dict) -> dict:
    """The per-statement row counts the SQL function must reproduce exactly."""
    return {k: len(plan.get(k) or []) for k in PLAN_LISTS}


def plan_is_empty(plan: dict) -> bool:
    return not any(plan_counts(plan).values())


def format_report(plan: dict) -> str:
    lines = [f"DT history rewrite -> v{plan['taxonomy_version']} (window {plan['window_days']}d, as of {plan['generated_at']})"]
    for table, kinds in plan["kinds"].items():
        lines.append(f"  {table:<16} " + (", ".join(f"{k}={n}" for k, n in kinds.items()) or "(no rows)"))
    lines.append("  statement row counts: " + ", ".join(f"{k}={n}" for k, n in plan["counts"].items()))
    for c in plan["collisions"]:
        lines.append(
            f"  merge {c['key']['subtype']} user={str(c['key']['user_id'])[:8]} pair={c['key']['l1_language_id']}->"
            f"{c['key']['l2_language_id']}: rows {[r['id'] for r in c['rows']]} -> survivor {c['survivor_id']} "
            f"({c['severity_basis']})"
        )
    for u in plan["unmappable"]:
        lines.append(f"  UNMAPPABLE {u['table']} id={u['id']} subtype={u['subtype']!r}")
    if plan_is_empty(plan):
        lines.append("  nothing to do (already v6) — --apply would be a no-op.")
    return "\n".join(lines)


# ============================================================================
# DB layer (Supabase / PostgREST) — only used by the CLI
# ============================================================================


def _fetch_all(db, table: str, columns: str) -> list[dict]:
    rows: list[dict] = []
    start = 0
    while True:
        page = db.table(table).select(columns).order("id").range(start, start + _PAGE - 1).execute().data or []
        rows.extend(page)
        if len(page) < _PAGE:
            return rows
        start += _PAGE


def fetch_taxonomy(db, version: int = TARGET_VERSION) -> tuple[Taxonomy, bool]:
    rows = db.table("dt_taxonomy_version").select("version, is_active, taxonomy").eq("version", version).execute().data
    if not rows:
        raise PlanError(f"dt_taxonomy_version {version} not seeded (apply dt_taxonomy_v6_seed.sql first)")
    return Taxonomy.from_row(version, rows[0]["taxonomy"]), bool(rows[0]["is_active"])


def fetch_rows(db) -> dict:
    """Read every row the planner needs. SELECT only."""
    errors = _fetch_all(
        db, "dt_error_instance",
        "id, submission_id, subtype, severity, is_mistake, created_at, taxonomy_version, remap_flag",
    )
    subs = {s["id"]: s for s in _fetch_all(db, "dt_submission", "id, user_id, l1_language_id, passage_id")}
    l2 = {p["id"]: p["l2_language_id"] for p in _fetch_all(db, "dt_passage", "id, l2_language_id")}
    for e in errors:
        s = subs.get(e["submission_id"]) or {}
        e["user_id"] = s.get("user_id")
        e["l1_language_id"] = s.get("l1_language_id")
        e["l2_language_id"] = l2.get(s.get("passage_id"))
    return {
        "errors": errors,
        "profiles": _fetch_all(
            db, "dt_error_profile_entry",
            "id, user_id, l1_language_id, l2_language_id, subtype, count, severity_rank, trend, "
            "remediation_status, taxonomy_version, remap_flag",
        ),
        "cards": _fetch_all(db, "dt_card", "id, profile_entry_id, origin_error_id, subtype, taxonomy_version"),
        "reviews": _fetch_all(db, "dt_card_review", "id, card_id"),
    }


def _rpc(db, name: str, params: dict) -> dict:
    data = db.rpc(name, params).execute().data
    if isinstance(data, list) and len(data) == 1:
        data = data[0]
    return data


def _get_db():
    from dotenv import load_dotenv

    load_dotenv()
    from services.supabase_factory import SupabaseFactory, get_supabase_admin

    try:
        return get_supabase_admin()
    except RuntimeError:
        SupabaseFactory.initialize()
        return get_supabase_admin()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="(default) read-only: print the plan")
    mode.add_argument("--rehearse", action="store_true", help="run the plan in SQL and roll it back")
    mode.add_argument("--apply", action="store_true", help="snapshot + rewrite in one transaction")
    mode.add_argument("--restore", action="store_true", help="undo the rewrite from the snapshot")
    ap.add_argument("--confirm-drop-snapshot", action="store_true",
                    help="with --restore: truncate the snapshot tables after a successful restore")
    ap.add_argument("--window-days", type=int, default=DEFAULT_WINDOW_DAYS)
    ap.add_argument("--plan-out", help="write the plan JSON here")
    ap.add_argument("--offline-taxonomy", action="store_true",
                    help="dry-run only: build aliases/pairs from the CSV instead of the v6 DB row")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    if args.confirm_drop_snapshot and not args.restore:
        ap.error("--confirm-drop-snapshot only goes with --restore")
    if args.offline_taxonomy and (args.apply or args.rehearse):
        ap.error("--offline-taxonomy is dry-run only; apply/rehearse must use the seeded v6 row")

    db = _get_db()
    if args.restore:
        result = _rpc(db, "dt_restore_history_v5", {"p_confirm_drop_snapshot": args.confirm_drop_snapshot})
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.offline_taxonomy:
        tax, active = taxonomy_from_source_files(), None
    else:
        tax, active = fetch_taxonomy(db)
    plan = plan_rewrite(**fetch_rows(db), tax=tax, now=datetime.now(timezone.utc), window_days=args.window_days)
    print(format_report(plan))
    if args.plan_out:
        with open(args.plan_out, "w", encoding="utf-8") as fh:
            json.dump(plan, fh, indent=2, default=str, ensure_ascii=False)
    if not (args.apply or args.rehearse):
        if active is False:
            print(f"  NOTE: v{tax.version} is not active yet — --apply will refuse until the TASK-853 activation.")
        return 0
    if plan["unmappable"]:
        print("REFUSING: unmappable rows (see above) — fix the taxonomy/legacy_aliases first.", file=sys.stderr)
        return 2
    result = _rpc(db, "dt_rewrite_history_v6", {"p_plan": plan, "p_dry_run": bool(args.rehearse)})
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
