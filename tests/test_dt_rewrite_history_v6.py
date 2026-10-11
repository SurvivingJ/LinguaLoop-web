"""TASK-852 — one-time v5 -> v6 rewrite of historical DT records.

Two layers:
  * Pure planner (scripts/dt_rewrite_history_v6.plan_rewrite) against synthetic
    fixtures: mapping kinds, merge collisions (status precedence, tie -> lowest id,
    summed count, in-window severity_rank/trend vs fallback), split flagging, the
    script_choice delete set (incl. reviews reached only through origin_error_id),
    card repointing, idempotency (apply the plan in memory, re-plan -> empty).
  * SQL (migrations/dt_rewrite_history_v6.sql) on a DISPOSABLE local Postgres
    (pgserver, PG 16) built from the real migrations: apply -> post-conditions ->
    second apply is a no-op -> restore is byte-equal to the start; p_dry_run rolls
    back; stale plan / non-empty snapshot / inactive v6 fail closed. Skipped when
    pgserver + psycopg are not importable (they are not repo dependencies).
"""

from __future__ import annotations

import copy
import json
import pathlib
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from scripts import dt_rewrite_history_v6 as rw

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEED = ROOT / "migrations" / "dt_taxonomy_v6_seed.sql"
NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)
U1 = "11111111-1111-1111-1111-111111111111"
U2 = "22222222-2222-2222-2222-222222222222"
ZH, EN, JA = 1, 2, 3


def _seed_taxonomy() -> dict:
    m = re.search(r"\$taxonomy\$(.*?)\$taxonomy\$", SEED.read_text(encoding="utf-8"), re.DOTALL)
    assert m
    return json.loads(m.group(1))


@pytest.fixture(scope="module")
def tax() -> rw.Taxonomy:
    return rw.Taxonomy.from_row(6, _seed_taxonomy())


def _days_ago(n: float) -> datetime:
    return NOW - timedelta(days=n)


# ----------------------------------------------------------------------------
# Synthetic fixture covering every case
# ----------------------------------------------------------------------------

def fixture_rows() -> dict:
    """Rows shaped like fetch_rows() output. ids chosen so precedence ties are visible."""
    E = []

    def err(i, subtype, user, l1, l2, *, sev="minor", mistake=False, age=1.0):
        E.append({"id": i, "subtype": subtype, "severity": sev, "is_mistake": mistake,
                  "created_at": _days_ago(age), "taxonomy_version": None, "remap_flag": None,
                  "user_id": user, "l1_language_id": l1, "l2_language_id": l2})

    # zh (U1, en->zh)
    err(1, "ba_construction", U1, EN, ZH, sev="major")
    err(2, "bei_passive", U1, EN, ZH, sev="critical")
    err(3, "bei_passive", U1, EN, ZH, mistake=True)            # gated out of severity
    err(4, "resultative_complement", U1, EN, ZH, age=40)       # previous window only
    err(5, "classifier", U1, EN, ZH)
    err(6, "omission", U1, EN, ZH)
    err(7, "aspect_marker", U1, EN, ZH)
    err(8, "ba_construction", U1, EN, ZH, sev="major", age=45)  # previous window
    # ja (U1, en->ja)
    err(10, "particle_wa_ga", U1, EN, JA)
    err(11, "particle", U1, EN, JA)
    err(12, "script_choice", U1, EN, JA)
    err(13, "script_choice", U1, EN, JA)
    err(14, "tense_aspect_ja", U1, EN, JA)
    err(15, "particle_case", U1, EN, JA)
    # en (U2, zh->en)
    err(20, "pronoun_reference", U2, ZH, EN)
    err(21, "tense_aspect", U2, ZH, EN)
    err(22, "article", U2, ZH, EN)
    err(23, "meaning_inversion", U2, ZH, EN)                   # already a v6 slug, unstamped

    def trend(cur, prev, as_of="2026-10-03T03:50:00+00:00"):
        d = round((cur - prev) / prev * 100.0, 1) if prev else None
        return {"window_days": 30, "as_of": as_of, "current_count": cur, "previous_count": prev, "delta_pct": d}

    P = []

    def prof(i, user, l1, l2, subtype, count, rank, status, tr=None):
        P.append({"id": i, "user_id": user, "l1_language_id": l1, "l2_language_id": l2, "subtype": subtype,
                  "count": count, "severity_rank": rank, "trend": tr, "remediation_status": status,
                  "taxonomy_version": None, "remap_flag": None})

    prof(100, U1, EN, ZH, "ba_construction", 1, 2.0, "watching", trend(1, 0))
    prof(101, U1, EN, ZH, "bei_passive", 1, 3.0, "drilling", trend(1, 0))           # survivor (drilling)
    prof(102, U1, EN, ZH, "resultative_complement", 2, 2.0, "queued", trend(2, 1))  # survivor (tie, lowest id)
    prof(103, U1, EN, ZH, "directional_complement", 3, 4.0, "queued", trend(3, 0, "2026-10-02T03:50:00+00:00"))
    prof(104, U1, EN, ZH, "classifier", 1, 1.0, "watching")
    prof(105, U1, EN, ZH, "omission", 1, 1.0, "watching")
    prof(106, U1, EN, JA, "script_choice", 2, 2.0, "queued")
    prof(107, U1, EN, JA, "particle", 1, 1.0, "watching")
    prof(108, U1, EN, JA, "particle_case", 1, 1.0, "drilling")                     # survivor, split flag
    prof(109, U1, EN, JA, "particle_wa_ga", 1, 1.0, "watching")
    prof(110, U2, ZH, EN, "pronoun_reference", 1, 1.0, "watching")
    prof(111, U2, ZH, EN, "tense_aspect", 1, 1.0, "resolved")
    prof(112, U1, ZH, EN, "tense_aspect", 1, 1.0, "watching")                       # other pair: no merge

    C = []

    def card(i, pe, origin, subtype):
        C.append({"id": i, "profile_entry_id": pe, "origin_error_id": origin, "subtype": subtype,
                  "taxonomy_version": None})

    card(200, 100, 1, "ba_construction")         # merged-away entry -> repoint to 101
    card(201, 106, 12, "script_choice")          # script_choice entry -> delete
    card(202, None, None, "script_choice")       # script_choice by subtype only -> delete
    card(203, 108, 13, "particle_case")          # reached ONLY via origin_error_id -> delete
    card(204, 104, 5, "classifier")              # follows its entry -> measure_word
    card(205, None, 21, "tense_aspect")          # no entry -> own mapping
    card(206, 103, 4, "directional_complement")  # merged-away -> repoint to 102 (complement)
    card(207, 107, 11, "particle")               # merged-away into 108 -> case_particle

    R = [{"id": 300, "card_id": 201}, {"id": 301, "card_id": 201}, {"id": 302, "card_id": 202},
         {"id": 303, "card_id": 203}, {"id": 304, "card_id": 200}, {"id": 305, "card_id": 204}]
    return {"errors": E, "profiles": P, "cards": C, "reviews": R}


def _plan(rows, tax, **kw):
    return rw.plan_rewrite(**copy.deepcopy(rows), tax=tax, now=NOW, window_days=30, **kw)


def _by_id(items):
    return {x["id"]: x for x in items}


# ----------------------------------------------------------------------------
# Taxonomy / resolve
# ----------------------------------------------------------------------------

def test_seed_taxonomy_matches_source_files(tax):
    src = rw.taxonomy_from_source_files()
    assert src.aliases == tax.aliases
    assert src.slugs == tax.slugs
    assert tax.dropped == {"script_choice"}


@pytest.mark.parametrize("slug,kind,to,flag", [
    ("omission", "stamp", "omission", None),
    ("classifier", "rename", "measure_word", None),
    ("aspect_marker", "merge", "aspect_negation", None),
    ("particle_wa_ga", "split", "wa_ga", "split_needs_review"),
    ("particle", "split", "case_particle", "split_needs_review"),
    ("pronoun_reference", "split", "pronoun", "split_needs_review"),
    ("script_choice", "delete", None, None),
    ("meaning_inversion", "stamp", "meaning_inversion", None),
    ("no_such_slug", "unmappable", None, None),
])
def test_resolve_unstamped(tax, slug, kind, to, flag):
    assert rw.resolve(slug, None, tax) == rw.Resolution(kind, to, flag)


def test_resolve_stamped_v6(tax):
    assert rw.resolve("word_order", 6, tax).kind == "noop"
    # a v5 slug that somehow carries version 6 is not silently trusted
    assert rw.resolve("classifier", 6, tax).kind == "unmappable"
    # a v5-stamped row is mapped like an unstamped one
    assert rw.resolve("classifier", 5, tax).to == "measure_word"


def test_taxonomy_rejects_unsafe_aliases():
    base = {"pairs": {"zh": {"subtypes": ["a", "b"]}}}
    with pytest.raises(rw.PlanError, match="maps to"):
        rw.Taxonomy.from_row(6, {**base, "legacy_aliases": {"a": {"to": "b", "kind": "1:1"}}})
    with pytest.raises(rw.PlanError, match="not a v6 slug"):
        rw.Taxonomy.from_row(6, {**base, "legacy_aliases": {"x": {"to": "zz", "kind": "1:1"}}})
    with pytest.raises(rw.PlanError, match="null iff"):
        rw.Taxonomy.from_row(6, {**base, "legacy_aliases": {"x": {"to": None, "kind": "1:1"}}})


# ----------------------------------------------------------------------------
# Planner
# ----------------------------------------------------------------------------

def test_error_instance_mapping(tax):
    plan = _plan(fixture_rows(), tax)
    upd = _by_id(plan["error_updates"])
    assert upd[5]["subtype"] == "measure_word" and upd[5]["remap_flag"] is None
    assert upd[6]["subtype"] == "omission"                     # stamp only
    assert upd[1]["subtype"] == upd[2]["subtype"] == "ba_bei"
    assert upd[10] == {"id": 10, "from_subtype": "particle_wa_ga", "from_version": None, "subtype": "wa_ga",
                       "taxonomy_version": 6, "remap_flag": "split_needs_review"}
    assert upd[11]["subtype"] == "case_particle" and upd[11]["remap_flag"] == "split_needs_review"
    assert upd[20]["subtype"] == "pronoun" and upd[20]["remap_flag"] == "split_needs_review"
    assert upd[23]["subtype"] == "meaning_inversion"
    assert all(u["taxonomy_version"] == 6 for u in plan["error_updates"])
    assert {d["id"] for d in plan["error_deletes"]} == {12, 13}
    assert plan["unmappable"] == []


def test_merge_survivor_precedence_and_aggregation(tax):
    plan = _plan(fixture_rows(), tax)
    upd = _by_id(plan["profile_updates"])
    deletes = {d["id"]: d["reason"] for d in plan["profile_deletes"]}

    # ba_construction(watching) + bei_passive(drilling) -> survivor 101
    s = upd[101]
    assert s["subtype"] == "ba_bei" and s["remap_flag"] == "merged"
    assert s["count"] == 2 and s["remediation_status"] == "drilling"
    # in-window, non-mistake errors 1 (major=2) + 2 (critical=3); 3 is a mistake, 8 is 45d old
    assert s["severity_rank"] == 5.0
    assert s["trend"]["current_count"] == 2 and s["trend"]["previous_count"] == 1
    assert s["trend"]["delta_pct"] == 100.0 and s["trend"]["window_days"] == 30
    assert deletes[100] == "merged_away"

    # resultative(queued, id 102) + directional(queued, id 103): tie -> lowest id;
    # only error 4 (40 days old) -> none in window -> fallbacks
    c = upd[102]
    assert c["subtype"] == "complement" and c["count"] == 5
    assert c["severity_rank"] == 4.0                                       # max of merged rows
    assert c["trend"] == {"window_days": 30, "as_of": "2026-10-03T03:50:00+00:00",
                          "current_count": 5, "previous_count": 1, "delta_pct": 400.0}
    assert deletes[103] == "merged_away"

    # particle (split) + particle_case(drilling) -> survivor 108 keeps the review flag
    p = upd[108]
    assert p["subtype"] == "case_particle" and p["remap_flag"] == "split_needs_review"
    assert p["count"] == 2 and p["remediation_status"] == "drilling"
    assert deletes[107] == "merged_away"

    # different pair (U1 zh->en) is not merged with U2's tense_aspect
    assert upd[111]["subtype"] == upd[112]["subtype"] == "verb_form_tense"
    assert upd[111]["remap_flag"] is None and upd[111]["remediation_status"] == "resolved"
    assert len(plan["collisions"]) == 3


def test_status_precedence_full_order(tax):
    rows = {"errors": [], "cards": [], "reviews": [], "profiles": [
        {"id": i, "user_id": U1, "l1_language_id": EN, "l2_language_id": ZH, "subtype": s, "count": 1,
         "severity_rank": 1.0, "trend": None, "remediation_status": st, "taxonomy_version": None,
         "remap_flag": None}
        for i, s, st in [(1, "ba_construction", "resolved"), (2, "bei_passive", "watching")]]}
    assert _plan(rows, tax)["profile_updates"][0]["id"] == 2      # watching > resolved
    rows["profiles"][0]["remediation_status"] = "queued"
    assert _plan(rows, tax)["profile_updates"][0]["id"] == 1      # queued > watching
    rows["profiles"][1]["remediation_status"] = "drilling"
    assert _plan(rows, tax)["profile_updates"][0]["id"] == 2      # drilling > queued
    rows["profiles"][0]["remediation_status"] = "drilling"
    assert _plan(rows, tax)["profile_updates"][0]["id"] == 1      # tie -> lowest id
    # no trends on either row -> None, not a crash
    assert _plan(rows, tax)["profile_updates"][0]["trend"] is None


def test_split_and_rename_profiles(tax):
    upd = _by_id(_plan(fixture_rows(), tax)["profile_updates"])
    assert upd[109]["subtype"] == "wa_ga" and upd[109]["remap_flag"] == "split_needs_review"
    assert upd[110]["subtype"] == "pronoun" and upd[110]["remap_flag"] == "split_needs_review"
    assert upd[104]["subtype"] == "measure_word" and upd[104]["count"] == 1
    assert upd[105]["subtype"] == "omission" and upd[105]["remap_flag"] is None


def test_script_choice_delete_set(tax):
    plan = _plan(fixture_rows(), tax)
    cards = {d["id"]: d["reason"] for d in plan["card_deletes"]}
    assert cards == {201: "dropped_subtype", 202: "dropped_subtype", 203: "dropped_origin_error"}
    assert {r["id"] for r in plan["review_deletes"]} == {300, 301, 302, 303}   # 303 only via origin_error_id
    assert {d["id"]: d["reason"] for d in plan["profile_deletes"]}[106] == "dropped"
    assert {d["id"] for d in plan["error_deletes"]} == {12, 13}


def test_card_repoint_and_subtype_follows_entry(tax):
    plan = _plan(fixture_rows(), tax)
    upd = _by_id(plan["card_updates"])
    assert (upd[200]["profile_entry_id"], upd[200]["subtype"]) == (101, "ba_bei")
    assert (upd[206]["profile_entry_id"], upd[206]["subtype"]) == (102, "complement")
    assert (upd[207]["profile_entry_id"], upd[207]["subtype"]) == (108, "case_particle")
    assert (upd[204]["profile_entry_id"], upd[204]["subtype"]) == (104, "measure_word")
    assert (upd[205]["profile_entry_id"], upd[205]["subtype"]) == (None, "verb_form_tense")
    assert upd[200]["from_profile_entry_id"] == 100
    assert plan["kinds"]["card"]["repoint"] == 3


def test_counts_and_report(tax):
    plan = _plan(fixture_rows(), tax)
    assert plan["counts"] == {
        "error_updates": 16, "error_deletes": 2, "profile_updates": 9, "profile_deletes": 4,
        "card_updates": 5, "card_deletes": 3, "review_deletes": 4,
    }
    assert plan["counts"] == rw.plan_counts(plan)
    json.dumps(plan)  # JSON-serialisable as-is (datetimes are not leaked into the plan)
    report = rw.format_report(plan)
    assert "merge complement" in report and "UNMAPPABLE" not in report


def test_unmappable_rows_are_reported(tax):
    rows = fixture_rows()
    rows["errors"].append({**rows["errors"][0], "id": 99, "subtype": "made_up"})
    rows["profiles"].append({**rows["profiles"][0], "id": 199, "subtype": "made_up", "user_id": U2})
    plan = _plan(rows, tax)
    assert {(u["table"], u["id"]) for u in plan["unmappable"]} == {("dt_error_instance", 99),
                                                                   ("dt_error_profile_entry", 199)}
    assert "UNMAPPABLE" in rw.format_report(plan)


def test_live_inventory_shape_is_rename_only(tax):
    """TASK-836: 16 zh errors (7 word_choice, 6 omission, 2 word_order, 1 aspect_marker),
    4 profiles, 4 cards, 5 reviews — no merge, split or delete fires."""
    errors = [
        {"id": i, "subtype": s, "severity": "minor", "is_mistake": False, "created_at": _days_ago(50),
         "taxonomy_version": None, "remap_flag": None, "user_id": U1, "l1_language_id": EN, "l2_language_id": ZH}
        for i, s in enumerate(["word_choice"] * 7 + ["omission"] * 6 + ["word_order"] * 2 + ["aspect_marker"], 1)]
    profiles = [
        {"id": 50 + i, "user_id": U1, "l1_language_id": EN, "l2_language_id": ZH, "subtype": s, "count": n,
         "severity_rank": float(n), "trend": None, "remediation_status": st, "taxonomy_version": None,
         "remap_flag": None}
        for i, (s, n, st) in enumerate([("aspect_marker", 1, "watching"), ("omission", 6, "drilling"),
                                        ("word_choice", 7, "drilling"), ("word_order", 2, "watching")])]
    cards = [{"id": 70 + i, "profile_entry_id": pe, "origin_error_id": 1, "subtype": s, "taxonomy_version": None}
             for i, (pe, s) in enumerate([(51, "omission"), (51, "omission"), (52, "word_choice"), (52, "word_choice")])]
    reviews = [{"id": 90 + i, "card_id": 70 + (i % 4)} for i in range(5)]
    plan = rw.plan_rewrite(errors=errors, profiles=profiles, cards=cards, reviews=reviews, tax=tax, now=NOW)
    assert plan["counts"] == {"error_updates": 16, "error_deletes": 0, "profile_updates": 4, "profile_deletes": 0,
                              "card_updates": 4, "card_deletes": 0, "review_deletes": 0}
    assert plan["collisions"] == []
    assert _by_id(plan["profile_updates"])[50]["subtype"] == "aspect_negation"


# ----------------------------------------------------------------------------
# Idempotency in memory: apply the plan the way the SQL does, re-plan -> empty
# ----------------------------------------------------------------------------

def _apply_in_memory(rows: dict, plan: dict) -> dict:
    rows = copy.deepcopy(rows)
    gone = {
        "reviews": {d["id"] for d in plan["review_deletes"]},
        "cards": {d["id"] for d in plan["card_deletes"]},
        "profiles": {d["id"] for d in plan["profile_deletes"]},
        "errors": {d["id"] for d in plan["error_deletes"]},
    }
    for table in gone:
        rows[table] = [r for r in rows[table] if r["id"] not in gone[table]]
    for table, key, cols in [
        ("errors", "error_updates", ("subtype", "taxonomy_version", "remap_flag")),
        ("profiles", "profile_updates", ("subtype", "count", "severity_rank", "trend", "remediation_status",
                                          "taxonomy_version", "remap_flag")),
        ("cards", "card_updates", ("subtype", "profile_entry_id", "taxonomy_version")),
    ]:
        upd = _by_id(plan[key])
        for r in rows[table]:
            if r["id"] in upd:
                r.update({c: upd[r["id"]][c] for c in cols})
    return rows


def test_plan_then_replan_is_empty_and_postconditions_hold(tax):
    rows = fixture_rows()
    after = _apply_in_memory(rows, _plan(rows, tax))
    again = _plan(after, tax)
    assert rw.plan_is_empty(again), again["counts"]
    for table in ("errors", "profiles", "cards"):
        for r in after[table]:
            assert r["subtype"] in tax.slugs and r["taxonomy_version"] == 6
            assert r["subtype"] != "script_choice"
    profiles = _by_id(after["profiles"])
    for c in after["cards"]:
        if c["profile_entry_id"] is not None:
            assert c["subtype"] == profiles[c["profile_entry_id"]]["subtype"]
    keys = [(p["user_id"], p["l1_language_id"], p["l2_language_id"], p["subtype"]) for p in after["profiles"]]
    assert len(keys) == len(set(keys))  # UNIQUE key still holds
    live_review_cards = {r["card_id"] for r in after["reviews"]}
    assert live_review_cards <= {c["id"] for c in after["cards"]}  # no orphaned review


def test_cli_rejects_bad_flag_combos():
    with pytest.raises(SystemExit):
        rw.main(["--apply", "--restore"])
    with pytest.raises(SystemExit):
        rw.main(["--confirm-drop-snapshot"])
    with pytest.raises(SystemExit):
        rw.main(["--apply", "--offline-taxonomy"])


# ============================================================================
# SQL on a disposable local Postgres
# ============================================================================

MIGRATIONS = [
    "dual_translation_groundwork.sql", "dt_severity_triad.sql", "dt_error_profile.sql", "dt_cards.sql",
    "dt_taxonomy_v6_columns.sql", "dt_taxonomy_v6_seed.sql", "dt_rewrite_history_v6.sql",
]
TABLES = ["dt_submission", "dt_grade", "dt_error_instance", "dt_error_profile_entry", "dt_card", "dt_card_review"]
SNAPSHOTS = ["dt_v5_snapshot_error_instance", "dt_v5_snapshot_error_instance_full", "dt_v5_snapshot_profile_entry",
             "dt_v5_snapshot_card", "dt_v5_snapshot_card_review"]


@pytest.fixture(scope="module")
def pg(tmp_path_factory):
    pgserver = pytest.importorskip("pgserver")
    psycopg = pytest.importorskip("psycopg")
    srv = pgserver.get_server(str(tmp_path_factory.mktemp("pgdata")), cleanup_mode="stop")
    base = srv.get_uri()
    with psycopg.connect(base, autocommit=True) as c:
        c.execute("DROP DATABASE IF EXISTS dt_tpl")
        c.execute("CREATE DATABASE dt_tpl")
    with psycopg.connect(srv.get_uri("dt_tpl"), autocommit=True) as c:
        c.execute("CREATE TABLE public.users (id uuid PRIMARY KEY)")
        c.execute("CREATE TABLE public.dim_languages (id integer PRIMARY KEY)")
        for f in MIGRATIONS:
            c.execute((ROOT / "migrations" / f).read_text(encoding="utf-8"))
    counter = iter(range(10_000))

    def fresh():
        name = f"dt_t{next(counter)}"
        with psycopg.connect(base, autocommit=True) as c:
            c.execute(f"CREATE DATABASE {name} TEMPLATE dt_tpl")
        return psycopg.connect(srv.get_uri(name), autocommit=True, row_factory=psycopg.rows.dict_row)

    yield fresh
    srv.cleanup()


def _load_fixture(conn, *, activate=True):
    rows = fixture_rows()
    conn.execute("INSERT INTO users VALUES (%s), (%s)", (U1, U2))
    conn.execute("INSERT INTO dim_languages VALUES (1), (2), (3)")
    passages = {ZH: 1, EN: 2, JA: 3}
    for l2, pid in passages.items():
        conn.execute("INSERT INTO dt_passage (id, l2_language_id, source_kind, source_ref_id, l2_text, age_tier) "
                     "OVERRIDING SYSTEM VALUE VALUES (%s, %s, 'test_transcript', %s, 'x', 3)", (pid, l2, str(uuid.uuid4())))
    subs = {}
    for e in rows["errors"]:
        key = (e["user_id"], e["l1_language_id"], e["l2_language_id"])
        if key not in subs:
            subs[key] = len(subs) + 1
            conn.execute("INSERT INTO dt_submission (id, user_id, passage_id, l1_language_id, reproduction) "
                         "OVERRIDING SYSTEM VALUE VALUES (%s, %s, %s, %s, 'r')",
                         (subs[key], key[0], passages[key[2]], key[1]))
        conn.execute(
            "INSERT INTO dt_error_instance (id, submission_id, span_reproduction, span_reference, category, subtype, "
            "source, severity, learner_form, corrected_form, explanation, confidence, is_mistake, created_at) "
            "OVERRIDING SYSTEM VALUE VALUES (%s, %s, '[0,1]', '[0,1]', 'grammatical', %s, 'interlingual', %s, "
            "'a', 'b', 'why', 0.9, %s, %s)",
            (e["id"], subs[key], e["subtype"], e["severity"], e["is_mistake"], e["created_at"]))
    conn.execute("INSERT INTO dt_grade (submission_id, scores, overall_band, diff, grader_trace) "
                 "SELECT id, '{}', 2, '[]', '{}' FROM dt_submission")
    for p in rows["profiles"]:
        conn.execute(
            "INSERT INTO dt_error_profile_entry (id, user_id, l1_language_id, l2_language_id, subtype, count, "
            "severity_rank, trend, remediation_status) OVERRIDING SYSTEM VALUE VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (p["id"], p["user_id"], p["l1_language_id"], p["l2_language_id"], p["subtype"], p["count"],
             p["severity_rank"], json.dumps(p["trend"]) if p["trend"] else None, p["remediation_status"]))
    for c in rows["cards"]:
        conn.execute(
            "INSERT INTO dt_card (id, user_id, profile_entry_id, origin_error_id, card_type, subtype, prompt_payload, "
            "reps, state) OVERRIDING SYSTEM VALUE VALUES (%s, %s, %s, %s, 'cloze', %s, '{\"q\": 1}', 2, 'review')",
            (c["id"], U1, c["profile_entry_id"], c["origin_error_id"], c["subtype"]))
    for r in rows["reviews"]:
        conn.execute("INSERT INTO dt_card_review (id, card_id, rating, was_correct) OVERRIDING SYSTEM VALUE "
                     "VALUES (%s, %s, 3, true)", (r["id"], r["card_id"]))
    # explicit ids were inserted OVERRIDING SYSTEM VALUE: move the identities past them
    for t in ("dt_passage", "dt_submission", "dt_error_instance", "dt_error_profile_entry", "dt_card",
              "dt_card_review"):
        conn.execute(f"SELECT setval(pg_get_serial_sequence('public.{t}', 'id'), (SELECT max(id) FROM {t}))")
    if activate:
        conn.execute("UPDATE dt_taxonomy_version SET is_active = (version = 6)")


def _fetch_pg(conn) -> dict:
    """The planner's input, read the way fetch_rows() joins it."""
    errors = conn.execute(
        "SELECT e.id, e.subtype, e.severity, e.is_mistake, e.created_at, e.taxonomy_version, e.remap_flag, "
        "s.user_id::text AS user_id, s.l1_language_id, p.l2_language_id FROM dt_error_instance e "
        "LEFT JOIN dt_submission s ON s.id = e.submission_id LEFT JOIN dt_passage p ON p.id = s.passage_id").fetchall()
    profiles = conn.execute(
        "SELECT id, user_id::text AS user_id, l1_language_id, l2_language_id, subtype, count, severity_rank, trend, "
        "remediation_status, taxonomy_version, remap_flag FROM dt_error_profile_entry").fetchall()
    cards = conn.execute("SELECT id, profile_entry_id, origin_error_id, subtype, taxonomy_version FROM dt_card").fetchall()
    reviews = conn.execute("SELECT id, card_id FROM dt_card_review").fetchall()
    return {"errors": errors, "profiles": profiles, "cards": cards, "reviews": reviews}


def _dump(conn, tables=TABLES) -> dict:
    return {t: [r["j"] for r in conn.execute(f"SELECT to_jsonb(x)::text AS j FROM {t} x ORDER BY id")] for t in tables}


def _call(conn, plan, dry_run=False):
    return conn.execute("SELECT dt_rewrite_history_v6(%s::jsonb, %s) AS r",
                        (json.dumps(plan, default=str), dry_run)).fetchone()["r"]


def _restore(conn, drop=False, dry_run=False):
    return conn.execute("SELECT dt_restore_history_v5(%s, %s) AS r", (drop, dry_run)).fetchone()["r"]


def _pg_plan(conn, tax):
    return rw.plan_rewrite(**_fetch_pg(conn), tax=tax, now=NOW, window_days=30)


class TestPostgres:
    def test_apply_noop_restore_roundtrip(self, pg, tax):
        conn = pg()
        _load_fixture(conn)
        start = _dump(conn)
        plan = _pg_plan(conn, tax)
        assert plan["counts"]["review_deletes"] == 4

        res = _call(conn, plan)
        assert res["status"] == "applied" and res["counts"] == plan["counts"] and res["dry_run"] is False

        # post-conditions, independently of the function
        for t in ("dt_error_instance", "dt_error_profile_entry", "dt_card"):
            bad = conn.execute(f"SELECT count(*) AS n FROM {t} WHERE taxonomy_version IS DISTINCT FROM 6 "
                               f"OR NOT (subtype = ANY (%s))", (sorted(tax.slugs),)).fetchone()["n"]
            assert bad == 0, t
        assert conn.execute("SELECT count(*) AS n FROM dt_card c JOIN dt_error_profile_entry p "
                            "ON p.id = c.profile_entry_id WHERE c.subtype <> p.subtype").fetchone()["n"] == 0
        surv = conn.execute("SELECT * FROM dt_error_profile_entry WHERE id = 101").fetchone()
        assert (surv["subtype"], surv["count"], surv["severity_rank"], surv["remap_flag"]) == ("ba_bei", 2, 5.0, "merged")
        assert conn.execute("SELECT profile_entry_id AS p FROM dt_card WHERE id = 200").fetchone()["p"] == 101
        assert conn.execute("SELECT remap_flag AS f FROM dt_error_instance WHERE id = 10").fetchone()["f"] == "split_needs_review"
        # snapshot sizes == plan
        sizes = {t: conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] for t in SNAPSHOTS}
        assert sizes == {"dt_v5_snapshot_error_instance": 16, "dt_v5_snapshot_error_instance_full": 2,
                         "dt_v5_snapshot_profile_entry": 13, "dt_v5_snapshot_card": 8,
                         "dt_v5_snapshot_card_review": 4}
        # grades / submissions untouched
        after = _dump(conn)
        assert after["dt_grade"] == start["dt_grade"] and after["dt_submission"] == start["dt_submission"]

        # idempotent: re-plan is empty, second call is a no-op that leaves the snapshot alone
        plan2 = _pg_plan(conn, tax)
        assert rw.plan_is_empty(plan2)
        assert _call(conn, plan2)["status"] == "noop"
        assert _dump(conn) == after

        # restore -> byte-equal to the start; restore again is harmless
        r = _restore(conn)
        assert r["status"] == "restored" and r["snapshot_truncated"] is False
        assert _dump(conn) == start
        _restore(conn)
        assert _dump(conn) == start
        # re-apply is refused while the old snapshot is still there
        with pytest.raises(Exception, match="snapshot tables are not empty"):
            _call(conn, _pg_plan(conn, tax))
        # restore + drop clears the snapshot; a fresh apply works again
        assert _restore(conn, drop=True)["snapshot_truncated"] is True
        assert all(conn.execute(f"SELECT count(*) AS n FROM {t}").fetchone()["n"] == 0 for t in SNAPSHOTS)
        assert _call(conn, _pg_plan(conn, tax))["status"] == "applied"

    def test_post_cutover_rows_survive_restore(self, pg, tax):
        conn = pg()
        _load_fixture(conn)
        _call(conn, _pg_plan(conn, tax))
        # after cutover: a new v6 error, a review on a surviving card, FSRS progress on it
        conn.execute("INSERT INTO dt_error_instance (submission_id, span_reproduction, span_reference, category, "
                     "subtype, source, severity, learner_form, corrected_form, explanation, confidence, taxonomy_version) "
                     "VALUES (1, '[0,1]', '[0,1]', 'grammatical', 'ba_bei', 'interlingual', 'minor', 'a', 'b', 'w', 0.9, 6)")
        conn.execute("INSERT INTO dt_card_review (card_id, rating) VALUES (200, 4)")
        conn.execute("UPDATE dt_card SET reps = 9 WHERE id = 200")
        _restore(conn)
        assert conn.execute("SELECT count(*) AS n FROM dt_error_instance WHERE subtype = 'ba_bei'").fetchone()["n"] == 1
        c = conn.execute("SELECT subtype, profile_entry_id, reps FROM dt_card WHERE id = 200").fetchone()
        assert (c["subtype"], c["profile_entry_id"], c["reps"]) == ("ba_construction", 100, 9)
        assert conn.execute("SELECT count(*) AS n FROM dt_card_review WHERE card_id = 200").fetchone()["n"] == 2

    def test_restore_after_v6_traffic_resets_profiles_keeps_new_rows(self, pg, tax):
        """Documented rollback scope (TASK-853/854, ADR-031): restore puts back only
        the snapshot. Post-cutover v6 rows keep their v6 names; progress on a
        snapshot profile row since the cutover is reset to the snapshot values."""
        conn = pg()
        _load_fixture(conn)
        _call(conn, _pg_plan(conn, tax))
        held = {r["subtype"] for r in conn.execute(
            "SELECT subtype FROM dt_error_profile_entry WHERE user_id = %s AND l1_language_id = %s "
            "AND l2_language_id = %s", (U1, EN, ZH))}
        pairs = _seed_taxonomy()["pairs"]
        new_slug = next(s for s in pairs.get("en-zh", pairs.get("zh"))["subtypes"] if s not in held)
        # v6 traffic: a brand-new v6 profile entry + progress on the renamed survivor 101
        conn.execute("INSERT INTO dt_error_profile_entry (id, user_id, l1_language_id, l2_language_id, subtype, "
                     "count, severity_rank, remediation_status, taxonomy_version) OVERRIDING SYSTEM VALUE "
                     "VALUES (500, %s, %s, %s, %s, 3, 2.0, 'queued', 6)", (U1, EN, ZH, new_slug))
        conn.execute("UPDATE dt_error_profile_entry SET count = 7, remediation_status = 'resolved' WHERE id = 101")
        res = _restore(conn)
        assert res["status"] == "restored"
        new = conn.execute("SELECT subtype, count, taxonomy_version FROM dt_error_profile_entry WHERE id = 500").fetchone()
        assert (new["subtype"], new["count"], new["taxonomy_version"]) == (new_slug, 3, 6)
        p = conn.execute("SELECT subtype, count, remediation_status FROM dt_error_profile_entry WHERE id = 101").fetchone()
        assert (p["subtype"], p["count"], p["remediation_status"]) == ("bei_passive", 1, "drilling")

    def test_restore_refuses_when_v5_key_is_held_by_post_cutover_row(self, pg, tax):
        """Composite UNIQUE (user, l1, l2, subtype): if a v5 key is now held by a
        row the snapshot does not know (here: the same-slug row 105 'omission' was
        removed after cutover and v6 grading created a new 'omission' row), restore
        aborts with a clear error before writing anything."""
        conn = pg()
        _load_fixture(conn)
        _call(conn, _pg_plan(conn, tax))
        conn.execute("DELETE FROM dt_error_profile_entry WHERE id = 105")
        conn.execute("INSERT INTO dt_error_profile_entry (id, user_id, l1_language_id, l2_language_id, subtype, "
                     "count, severity_rank, remediation_status, taxonomy_version) OVERRIDING SYSTEM VALUE "
                     "VALUES (501, %s, %s, %s, 'omission', 1, 1.0, 'watching', 6)", (U1, EN, ZH))
        before = _dump(conn, TABLES + SNAPSHOTS)
        with pytest.raises(Exception, match=r"105 \(held by 501\).*fix-forward"):
            _restore(conn)
        assert _dump(conn, TABLES + SNAPSHOTS) == before

    def test_dry_run_rolls_back(self, pg, tax):
        conn = pg()
        _load_fixture(conn, activate=False)   # dry-run is allowed before activation
        start = _dump(conn, TABLES + SNAPSHOTS)
        plan = _pg_plan(conn, tax)
        res = _call(conn, plan, dry_run=True)
        assert res["dry_run"] is True and res["rolled_back"] is True and res["counts"] == plan["counts"]
        assert _dump(conn, TABLES + SNAPSHOTS) == start
        with pytest.raises(Exception, match="not active"):
            _call(conn, plan)
        assert _dump(conn, TABLES + SNAPSHOTS) == start

    def test_stale_plan_fails_closed(self, pg, tax):
        conn = pg()
        _load_fixture(conn)
        plan = _pg_plan(conn, tax)
        start_snap = _dump(conn, SNAPSHOTS)
        conn.execute("UPDATE dt_error_instance SET subtype = 'article' WHERE id = 5")
        with pytest.raises(Exception, match="stale plan"):
            _call(conn, plan)
        assert _dump(conn, SNAPSHOTS) == start_snap

    def test_unplanned_review_blocks_delete(self, pg, tax):
        """A review written between plan and apply on a card the plan deletes: the
        NO ACTION FK aborts the whole transaction (nothing half-applied)."""
        conn = pg()
        _load_fixture(conn)
        plan = _pg_plan(conn, tax)
        conn.execute("INSERT INTO dt_card_review (card_id, rating) VALUES (203, 1)")
        before = _dump(conn, TABLES + SNAPSHOTS)
        with pytest.raises(Exception, match="foreign key"):
            _call(conn, plan)
        assert _dump(conn, TABLES + SNAPSHOTS) == before

    def test_unplanned_v5_row_fails_postcondition(self, pg, tax):
        conn = pg()
        _load_fixture(conn)
        plan = _pg_plan(conn, tax)
        conn.execute("INSERT INTO dt_error_instance (submission_id, span_reproduction, span_reference, category, "
                     "subtype, source, severity, learner_form, corrected_form, explanation, confidence) "
                     "VALUES (1, '[0,1]', '[0,1]', 'grammatical', 'classifier', 'interlingual', 'minor', 'a', 'b', 'w', 0.9)")
        before = _dump(conn, TABLES + SNAPSHOTS)
        with pytest.raises(Exception, match="post-condition"):
            _call(conn, plan)
        assert _dump(conn, TABLES + SNAPSHOTS) == before

    def test_restore_on_empty_snapshot_is_noop(self, pg):
        conn = pg()
        assert _restore(conn)["status"] == "noop"
