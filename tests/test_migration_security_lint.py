"""Static security lint over ``migrations/*.sql`` (TASK-881).

No database needed. Fails when a migration:

1. creates a SECURITY DEFINER function without ``SET search_path`` in its header, or
2. creates a SECURITY DEFINER function without a ``REVOKE ... FROM PUBLIC/anon/authenticated``
   for it in the same file (an explicit ``-- security-lint: allow-definer-exposed <reason>``
   comment in the file is the documented escape hatch), or
3. creates a table in ``public`` without ``ENABLE ROW LEVEL SECURITY`` in the same file
   (escape hatch: ``-- security-lint: allow-no-rls <reason>``).

Files that predate the rule are listed explicitly in HISTORICAL_* below. NEVER add a new
migration to those lists; fix the migration instead (see migrations/CLAUDE.md).

The live-catalog counterpart is tests/sql/check_function_acls.sql (read-only SELECTs).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

# --------------------------------------------------------------------------------------
# Allowlists: migrations that predate the rule. Frozen. Do not extend.
# --------------------------------------------------------------------------------------
# SECURITY DEFINER created without search_path and/or REVOKE (legacy; the live state is
# repaired by migrations/security_function_grants_group_a/b.sql, applied separately).
HISTORICAL_DEFINER_FILES: frozenset[str] = frozenset({
    "add_irt_calibration_metadata.sql",
    "calibration_pronunciation_mode.sql",
    "calibration_sense_word_language_and_partial_hnsw.sql",
    "counter_drill.sql",
    "dim_word_senses_embedding.sql",
    "dt_synthesis_advisory_lock.sql",
    "elo_functions.sql",
    "get_classifier_drill_session.sql",
    "get_distractors_definition_language_param.sql",
    "get_replay_tests.sql",
    "listening_lab_rpcs.sql",
    "partF_question_attempt_results.sql",
    "partG_qar_drop_response_time.sql",
    "phase13_apply_attempt_timing_and_progress.sql",
    "phase13_apply_study_plan_template.sql",
    "phase13_build_daily_session.sql",
    "phase13_compute_weekly_plan_helpers.sql",
    "phase13_refresh_practice_time_estimates.sql",
    "phase18_practice_time_seconds.sql",
    "phase3_rpc_fixes.sql",
    "phase6_security_hardening.sql",
    "process_classifier_drill_submission.sql",
    "process_dictation_submission.sql",
    "process_mystery_submission.sql",
    "process_pinyin_submission.sql",
    "process_pitch_accent_submission.sql",
    "shrink_sense_embeddings_halfvec768.sql",
    "study_plan_advisory_lock.sql",
    "task510_model_health_advisory_lock.sql",
    "task517_queue_drain_advisory_lock.sql",
    "task716_local_day_boundary.sql",
    "task740_collapse_difficulty_to_tier_schema.sql",
    "task740_phase5_question_passage_dedup.sql",
    "task740_phase5b_topic_recency_exclusion.sql",
    "task748_get_recommended_tests_vocab_aware.sql",
    "task767_sense_quarantine_guards.sql",
    "task773b_calibration_distractor_cache_misses.sql",
    "wire_volatility_and_exclude_attempted.sql",
    "word_upload_slot_scheduling.sql",
    "word_upload_sweep_advisory_lock.sql",
})
# CREATE TABLE in public without ENABLE ROW LEVEL SECURITY in the same file (legacy; the
# live state is repaired by migrations/security_enable_rls_unprotected_tables.sql).
HISTORICAL_RLS_FILES: frozenset[str] = frozenset({
    "add_classifier_drill_mode.sql",
    "bkt_vocabulary_tracking.sql",
    "conversation_generation_tables.sql",
    "corpus_analysis_tables.sql",
    "counter_drill.sql",
    "create_all_tables.sql",
    "daily_test_loads.sql",
    "dim_exercise_capabilities.sql",
    "dt_cards.sql",
    "dt_error_profile.sql",
    "dual_translation_groundwork.sql",
    "exercise_generation_schema.sql",
    "generation_queue.sql",
    "generation_stage_timings.sql",
    "phase12_dim_exercise_types.sql",
    "phase12_dim_practice_modes.sql",
    "phase13_dim_study_goals.sql",
    "phase13_dim_study_plan_templates.sql",
    "phase14_generation_review_queue.sql",
    "phase14_llm_calls.sql",
    "phase2_schema_cleanup.sql",
    "phase4_schema_evolution.sql",
    "style_analysis_tables.sql",
    "task740_collapse_difficulty_to_tier_schema.sql",
    "test_generation_tables.sql",
    "traditional_chinese_groundwork.sql",
    "vocabulary_ladder_schema.sql",
    "word_upload_sweep_advisory_lock.sql",
})

# New-rule violations found in files written alongside the TASK-875..880 hardening or the
# session-budget work. They are NOT grandfathered: the owning author must fix the file (add
# REVOKE / a documented allow comment) and then delete the entry here. The staleness test
# below forces removal once fixed.
PENDING_FIX_DEFINER_FILES: frozenset[str] = frozenset({
    # session-budget redefinitions (CREATE OR REPLACE keeps the existing ACL, which
    # security_function_grants_group_b.sql revokes); add an explicit REVOKE ... service_role.
    "session_module_exclusions.sql",
    "session_module_exclusions_build_daily_session.sql",
})

ALLOW_DEFINER_RE = re.compile(r"--\s*security-lint:\s*allow-definer-exposed\s+\S+", re.I)
ALLOW_NO_RLS_RE = re.compile(r"--\s*security-lint:\s*allow-no-rls\s+\S+", re.I)


# --------------------------------------------------------------------------------------
# Minimal SQL scanner
# --------------------------------------------------------------------------------------
_DOLLAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z_0-9]*)?\$")


def _strip_comments(sql: str) -> str:
    """Remove -- and /* */ comments, leaving string / dollar-quoted bodies intact."""
    out: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j
        elif sql.startswith("/*", i):
            depth, i = 1, i + 2
            while i < n and depth:
                if sql.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif sql.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            out.append(" ")
        elif c == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if sql.startswith("''", j):
                        j += 2
                        continue
                    break
                j += 1
            out.append(sql[i:j + 1])
            i = j + 1
        elif c == "$":
            m = _DOLLAR_RE.match(sql, i)
            if m:
                tag = m.group(0)
                j = sql.find(tag, m.end())
                j = n if j == -1 else j + len(tag)
                out.append(sql[i:j])
                i = j
            else:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _split_statements(sql: str) -> list[tuple[str, str]]:
    """Split on top-level ';'. Returns (statement_with_bodies, statement_without_bodies)."""
    stmts: list[tuple[str, str]] = []
    full: list[str] = []
    bare: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if sql.startswith("''", j):
                        j += 2
                        continue
                    break
                j += 1
            seg = sql[i:j + 1]
            full.append(seg)
            bare.append("''")
            i = j + 1
        elif c == "$" and _DOLLAR_RE.match(sql, i):
            tag = _DOLLAR_RE.match(sql, i).group(0)
            j = sql.find(tag, i + len(tag))
            j = n if j == -1 else j + len(tag)
            full.append(sql[i:j])
            bare.append("$$")
            i = j
        elif c == ";":
            stmts.append(("".join(full).strip(), "".join(bare).strip()))
            full, bare = [], []
            i += 1
        else:
            full.append(c)
            bare.append(c)
            i += 1
    if "".join(full).strip():
        stmts.append(("".join(full).strip(), "".join(bare).strip()))
    return stmts


_IDENT = r'(?:"[^"]+"|[A-Za-z_][A-Za-z_0-9$]*)'
_QNAME = rf"(?:{_IDENT}\s*\.\s*)?({_IDENT})"
_CREATE_FN_RE = re.compile(
    rf"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(?:({_IDENT})\s*\.\s*)?({_IDENT})\s*\(", re.I)
_CREATE_TABLE_RE = re.compile(
    rf"^\s*CREATE\s+(?!TEMP\b|TEMPORARY\b|UNLOGGED\s+TEMP)(?:UNLOGGED\s+)?TABLE\s+"
    rf"(?:IF\s+NOT\s+EXISTS\s+)?(?:({_IDENT})\s*\.\s*)?({_IDENT})", re.I)
_REVOKE_FROM_CLIENT_RE = re.compile(r"\bFROM\b[^;]*\b(PUBLIC|anon|authenticated)\b", re.I)


def _norm(ident: str) -> str:
    return ident.strip('"').lower()


def scan_file(path: Path) -> dict[str, list[str]]:
    """Return {'definer': [problems], 'rls': [problems]} for one migration file."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    stmts = _split_statements(_strip_comments(raw))

    definers: list[tuple[str, bool]] = []   # (function name, has search_path)
    tables: list[str] = []
    revoked_fns: set[str] = set()
    revoke_all_fns = False
    rls_tables: set[str] = set()
    dynamic_revoke = False   # REVOKE ... FROM client roles inside a DO block / EXECUTE format
    dynamic_rls = False

    for full, bare in stmts:
        m = _CREATE_FN_RE.match(bare)
        if m:
            if (m.group(1) is None or _norm(m.group(1)) == "public") and \
                    re.search(r"\bSECURITY\s+DEFINER\b", bare, re.I):
                definers.append((_norm(m.group(2)),
                                 bool(re.search(r"\bSET\s+search_path\b", bare, re.I))))
            continue
        m = _CREATE_TABLE_RE.match(bare)
        if m and (m.group(1) is None or _norm(m.group(1)) == "public"):
            tables.append(_norm(m.group(2)))
            continue
        if re.match(r"^\s*REVOKE\b", bare, re.I) and _REVOKE_FROM_CLIENT_RE.search(bare):
            if re.search(r"\bON\s+ALL\s+FUNCTIONS\b", bare, re.I):
                revoke_all_fns = True
            for fm in re.finditer(
                    rf"\bON\s+(?:FUNCTION|ROUTINE)\s+(?:{_IDENT}\s*\.\s*)?({_IDENT})", bare, re.I):
                revoked_fns.add(_norm(fm.group(1)))
            continue
        m = re.match(rf"^\s*ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?"
                     rf"(?:({_IDENT})\s*\.\s*)?({_IDENT})\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY",
                     bare, re.I)
        if m:
            rls_tables.add(_norm(m.group(2)))
            continue
        if re.match(r"^\s*DO\b", bare, re.I):
            body = full
            if re.search(r"\bREVOKE\b[^;]*\bFROM\b[^;]*\b(PUBLIC|anon|authenticated)\b", body,
                         re.I | re.S):
                dynamic_revoke = True
            if re.search(r"\bENABLE\s+ROW\s+LEVEL\s+SECURITY\b", body, re.I):
                dynamic_rls = True

    problems: dict[str, list[str]] = {"definer": [], "rls": []}
    if not ALLOW_DEFINER_RE.search(raw):
        for name, has_sp in definers:
            if not has_sp:
                problems["definer"].append(
                    f"SECURITY DEFINER function {name}() has no SET search_path")
            if not (name in revoked_fns or revoke_all_fns or dynamic_revoke):
                problems["definer"].append(
                    f"SECURITY DEFINER function {name}() has no REVOKE ... FROM "
                    f"PUBLIC/anon/authenticated in the same file")
    if not ALLOW_NO_RLS_RE.search(raw):
        for t in tables:
            if not (t in rls_tables or dynamic_rls):
                problems["rls"].append(
                    f"CREATE TABLE public.{t} has no ENABLE ROW LEVEL SECURITY in the same file")
    return problems


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))   # not archive/, not audits/


# --------------------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------------------
def test_migrations_found():
    assert _migration_files(), "no migrations/*.sql found; lint is scanning the wrong dir"


def test_definer_functions_are_hardened():
    failures = []
    for f in _migration_files():
        if f.name in HISTORICAL_DEFINER_FILES | PENDING_FIX_DEFINER_FILES:
            continue
        failures += [f"{f.name}: {p}" for p in scan_file(f)["definer"]]
    assert not failures, (
        "SECURITY DEFINER hardening rule violated (see migrations/CLAUDE.md):\n  "
        + "\n  ".join(failures))


def test_public_tables_enable_rls():
    failures = []
    for f in _migration_files():
        if f.name in HISTORICAL_RLS_FILES:
            continue
        failures += [f"{f.name}: {p}" for p in scan_file(f)["rls"]]
    assert not failures, (
        "RLS rule violated (see migrations/CLAUDE.md):\n  " + "\n  ".join(failures))


def test_historical_allowlists_are_not_stale():
    """Every allowlisted file must exist and still violate; otherwise remove it."""
    names = {f.name: f for f in _migration_files()}
    stale = []
    for fname in sorted(HISTORICAL_DEFINER_FILES | PENDING_FIX_DEFINER_FILES):
        if fname not in names or not scan_file(names[fname])["definer"]:
            stale.append(f"allowlisted definer file: {fname}")
    for fname in sorted(HISTORICAL_RLS_FILES):
        if fname not in names or not scan_file(names[fname])["rls"]:
            stale.append(f"HISTORICAL_RLS_FILES: {fname}")
    assert not stale, "remove stale allowlist entries:\n  " + "\n  ".join(stale)


# --------------------------------------------------------------------------------------
# Self-tests for the scanner
# --------------------------------------------------------------------------------------
def _scan_text(tmp_path, text):
    p = tmp_path / "x.sql"
    p.write_text(text)
    return scan_file(p)


def test_scanner_flags_unhardened_definer(tmp_path):
    r = _scan_text(tmp_path, "CREATE FUNCTION public.f() RETURNS int LANGUAGE sql "
                             "SECURITY DEFINER AS $$ SELECT 1 $$;")
    assert len(r["definer"]) == 2


def test_scanner_accepts_hardened_definer(tmp_path):
    r = _scan_text(tmp_path, """
        CREATE OR REPLACE FUNCTION public.f(a int) RETURNS int LANGUAGE sql
        SECURITY DEFINER SET search_path = public, pg_temp AS $$ SELECT 1 -- ; tricky $$;
        REVOKE ALL ON FUNCTION public.f(int) FROM PUBLIC, anon, authenticated;
        GRANT EXECUTE ON FUNCTION public.f(int) TO service_role;
    """)
    assert r["definer"] == []


def test_scanner_ignores_commented_definer_and_invoker(tmp_path):
    r = _scan_text(tmp_path, "-- SECURITY DEFINER\nCREATE FUNCTION f() RETURNS int "
                             "LANGUAGE sql AS $$ SELECT 'SECURITY DEFINER' $$;")
    assert r["definer"] == []


def test_scanner_allow_comment(tmp_path):
    r = _scan_text(tmp_path, "-- security-lint: allow-definer-exposed RLS helper, ADR-034\n"
                             "CREATE FUNCTION f() RETURNS int LANGUAGE sql SECURITY DEFINER "
                             "AS $$ SELECT 1 $$;")
    assert r["definer"] == []


def test_scanner_rls(tmp_path):
    bad = _scan_text(tmp_path, "CREATE TABLE IF NOT EXISTS public.t (id int);")
    assert len(bad["rls"]) == 1
    ok = _scan_text(tmp_path, "CREATE TABLE public.t (id int);\n"
                              "ALTER TABLE public.t ENABLE ROW LEVEL SECURITY;")
    assert ok["rls"] == []
    tmp = _scan_text(tmp_path, "CREATE TEMP TABLE t (id int);")
    assert tmp["rls"] == []
