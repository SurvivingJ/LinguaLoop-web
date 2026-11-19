"""Static checks of migrations/calibration_zh_normaliser_fix.sql and its rollback (TASK-1074).

The behaviour (5,356 rows with a numbered part byte-identical; every zh standard reading
numbered; Python == SQL on all 11,977 native zh readings) was checked on the local Postgres
harness; these tests pin the file's shape and tie its patterns to services/placement_tones.
"""

import re
from pathlib import Path

import pytest

from services import placement_tones as pt

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
SQL = (MIGRATIONS / "calibration_zh_normaliser_fix.sql").read_text(encoding="utf-8")
ROLLBACK = (MIGRATIONS / "calibration_zh_normaliser_fix_rollback.sql").read_text(encoding="utf-8")
ORIGINAL = (MIGRATIONS / "calibration_pronunciation_mode.sql").read_text(encoding="utf-8")

FUNCTIONS = {
    "calibration_normalise_pronunciation": ("p_pronunciation text, p_language_id smallint", "text"),
    "calibration_syllable_count": ("p_normalised text, p_language_id smallint", "integer"),
}


def _code(sql: str) -> str:
    """The file without full-line comments (bodies keep their inline comments)."""
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


def _function(sql: str, name: str) -> str:
    m = re.search(rf"CREATE OR REPLACE FUNCTION public\.{name}\(.*?\$function\$;", _code(sql), re.S)
    assert m, name
    return m.group(0)


def _signature(fn: str) -> tuple[str, str]:
    m = re.search(r"\((.*?)\)\s*RETURNS\s+(\w+)", fn, re.S)
    return " ".join(m.group(1).split()), m.group(2)


def _branch(fn: str, start: str, end: str) -> str:
    """Whitespace-normalised text between two markers (a CASE branch)."""
    body = fn.split("$function$")[1]
    body = "\n".join(line.split("--", 1)[0] for line in body.splitlines())
    m = re.search(re.escape(start) + r"(.*?)" + re.escape(end), body, re.S)
    assert m, (start, end)
    return " ".join(m.group(1).split())


@pytest.mark.parametrize("name", FUNCTIONS)
def test_same_signature_in_migration_rollback_and_original(name):
    for sql in (SQL, ROLLBACK, ORIGINAL):
        assert _signature(_function(sql, name)) == FUNCTIONS[name]


@pytest.mark.parametrize("name", FUNCTIONS)
def test_hardened_and_immutable(name):
    fn = _function(SQL, name)
    assert re.search(r"LANGUAGE sql\s+IMMUTABLE\s+PARALLEL SAFE\s+SET search_path = public, pg_temp", fn)
    assert "SECURITY DEFINER" not in fn
    args = ", ".join(a.split()[1] for a in FUNCTIONS[name][0].split(", "))
    for sql in (SQL, ROLLBACK):
        code = _code(sql)
        assert f"REVOKE ALL ON FUNCTION public.{name}({args}) FROM PUBLIC, anon, authenticated;" in code
        assert f"GRANT EXECUTE ON FUNCTION public.{name}({args}) TO service_role;" in code


def test_only_the_two_functions_change():
    code = _code(SQL).upper()
    for word in ("DROP ", "DELETE ", "UPDATE ", "INSERT ", "ALTER ", "TRUNCATE", "CREATE TABLE"):
        assert word not in code, word
    assert len(re.findall(r"CREATE OR REPLACE FUNCTION", _code(SQL))) == 2
    assert len(re.findall(r"CREATE OR REPLACE FUNCTION", _code(ROLLBACK))) == 2


def test_numbered_part_branch_is_the_old_expression():
    new = _function(SQL, "calibration_normalise_pronunciation")
    assert ("WHEN p_language_id = 1 AND substring(p_pronunciation from '\\(([^)]*)\\)') IS NOT NULL THEN"
            in " ".join(new.split()))
    assert ("lower(regexp_replace( substring(p_pronunciation from '\\(([^)]*)\\)'), '\\s+', '', 'g'))"
            in " ".join(new.split()))


def test_ja_and_other_branches_are_unchanged():
    new = _function(SQL, "calibration_normalise_pronunciation")
    old = _function(ROLLBACK, "calibration_normalise_pronunciation")
    assert _branch(new, "WHEN p_language_id = 3 THEN", "END;") == \
        _branch(old, "WHEN p_language_id = 3 THEN", "END;")
    new = _function(SQL, "calibration_syllable_count")
    old = _function(ROLLBACK, "calibration_syllable_count")
    assert _branch(new, "WHEN p_language_id = 3 THEN", "END;") == \
        _branch(old, "WHEN p_language_id = 3 THEN", "END;")


def test_tone_placement_patterns_match_python():
    fn = _function(SQL, "calibration_normalise_pronunciation")
    marks = {1: "\\u0304", 2: "\\u0301", 3: "\\u030c", 4: "\\u0300"}
    for tone, mark in marks.items():
        assert f"'{mark}{pt._AFTER_MARK}', '\\1{tone}', 'g')" in fn, tone
    assert f"'([a-zü])(?=[\\s''·-]|$)', '\\15', 'g')" in fn
    assert "'[\\s''·-]+', '', 'g')" in fn
    assert pt._SEPARATORS == "[\\s'·-]"


def test_syllable_count_keeps_digit_counting_and_qualifies_the_normaliser():
    fn = _function(SQL, "calibration_syllable_count")
    assert "CASE WHEN p_normalised ~ '[1-5]' THEN p_normalised" in fn
    assert "public.calibration_normalise_pronunciation(p_normalised, 1::smallint)" in fn


def test_rollback_restores_the_live_bodies():
    old = _function(ROLLBACK, "calibration_normalise_pronunciation")
    assert "coalesce(substring(p_pronunciation from '\\(([^)]*)\\)'), p_pronunciation)" in old
    assert "search_path" not in old
    old = _function(ROLLBACK, "calibration_syllable_count")
    assert "coalesce(length(regexp_replace(p_normalised, '[^1-5]', '', 'g')), 0)" in old
    assert "search_path" not in old


def test_header_documents_fixtures_and_verify_query():
    fixtures = re.findall(r"'([^'\n]+)'\s+->\s+'([a-zü0-9]+)'", SQL)
    assert ("yuán xíng", "yuan2xing2") in fixtures and ("lǜ shī", "lü4shi1") in fixtures
    assert "syllable_count_zero" in SQL and "VERIFY" in SQL and "Rollback" in SQL
