"""Static checks of migrations/dt_guided_self_repair.sql (tech 9)."""

import re
from pathlib import Path

import pytest

SQL = (Path(__file__).resolve().parent.parent / "migrations" / "dt_guided_self_repair.sql").read_text(encoding="utf-8")
CODE = "\n".join(line.split("--", 1)[0] for line in SQL.splitlines())
TABLES = ("dt_repair_session", "dt_repair_item", "dt_repair_event")


@pytest.mark.parametrize("table", TABLES)
def test_rls_and_revoke(table):
    assert f"CREATE TABLE IF NOT EXISTS public.{table}" in CODE
    assert re.search(rf"ALTER TABLE public\.{table}\s+ENABLE ROW LEVEL SECURITY;", CODE)
    assert re.search(rf"REVOKE ALL ON public\.{table}\s+FROM PUBLIC, anon, authenticated;", CODE)
    assert f"COMMENT ON TABLE public.{table}" in CODE


def test_no_forbidden_statements():
    upper = CODE.upper().replace("ON DELETE CASCADE", "")
    for word in ("DROP ", "DELETE ", "TRUNCATE", "GRANT ", "ALTER COLUMN", "ADD COLUMN", "UPDATE "):
        assert word not in upper, word
    for m in re.finditer(r"ALTER TABLE public\.(\w+)", CODE):
        assert m.group(1) in TABLES
    assert "CREATE TABLE public." not in CODE and "CREATE INDEX idx" not in CODE  # idempotent forms only


@pytest.mark.parametrize("values", [
    ("self_repaired", "repaired_alternative", "answer_shown", "shown_directly", "disputed", "skipped",
     "unsure_revised", "unsure_dismissed", "unsure_skipped"),
    ("asked", "auto_cap", "grader_failed", "budget", "direct"),
    ("none", "due", "resolved", "retired", "expired", "disputed"),
    ("step_opened", "hint_shown", "revision_checked", "answer_shown", "disputed", "kept", "skipped",
     "episode_closed"),
    ("fixed", "no_issue_found", "still_flagged", "error"),
    ("grader_span", "template", "taxonomy_gloss", "type_neutral"),
    ("open", "finished", "bypassed", "abandoned"),
    ("repair", "unsure", "direct"),
    ("repair_pass", "daily_practice"),
])
def test_enums_in_checks(values):
    for v in values:
        assert f"'{v}'" in CODE, v


def test_unique_check_index_and_size_header():
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_dt_repair_event_check" in CODE
    assert "submission_id    bigint NOT NULL UNIQUE" in CODE
    assert "SIZE" in SQL and "RETENTION" in SQL and "VERIFY" in SQL
