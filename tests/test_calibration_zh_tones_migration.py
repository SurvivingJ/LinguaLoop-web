"""Static checks of migrations/calibration_zh_tones.sql and its rollback (TASK-1092, ADR-060).

The SQL-vs-Python agreement on real readings is checked by scripts/verify_zh_tone_variants.py
(local harness: 0 mismatches over all native zh readings); these tests pin the file's shape,
security and the constants it shares with services/placement_tones.
"""

import re
from pathlib import Path

import pytest

from services import placement_tones as pt

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
SQL = (MIGRATIONS / "calibration_zh_tones.sql").read_text(encoding="utf-8")
ROLLBACK = (MIGRATIONS / "calibration_zh_tones_rollback.sql").read_text(encoding="utf-8")
CODE = "\n".join(line for line in SQL.splitlines() if not line.lstrip().startswith("--"))

FUNCTIONS = {
    # name: (identity args, returns, volatility, security definer)
    "calibration_zh_parse_pinyin": ("text", "TABLE", "IMMUTABLE", False),
    "calibration_zh_mark_syllable": ("text, integer", "text", "IMMUTABLE", False),
    "calibration_refresh_zh_tone_inventory": ("", "integer", None, True),
    "calibration_zh_tone_variants": ("text, integer", "text[]", "STABLE", False),
}


def _function(name: str) -> str:
    m = re.search(rf"CREATE OR REPLACE FUNCTION public\.{name}\(.*?\$function\$;", CODE, re.S)
    assert m, name
    return m.group(0)


def _header(name: str) -> str:
    return _function(name).split("$function$")[0]


def test_table_is_locked_down():
    assert "CREATE TABLE IF NOT EXISTS public.calibration_zh_tone_inventory (" in CODE
    assert "ALTER TABLE public.calibration_zh_tone_inventory ENABLE ROW LEVEL SECURITY;" in CODE
    assert "REVOKE ALL ON public.calibration_zh_tone_inventory FROM PUBLIC, anon, authenticated;" in CODE
    assert "GRANT " not in re.sub(r"GRANT EXECUTE ON FUNCTION[^;]*TO service_role;", "", CODE)
    assert "CREATE POLICY" not in CODE


def test_table_columns_match_tech_13():
    table = re.search(r"CREATE TABLE IF NOT EXISTS public\.calibration_zh_tone_inventory \((.*?)\n\);",
                      CODE, re.S).group(1)
    assert re.search(r"base\s+text PRIMARY KEY", table)
    assert re.search(r"tones\s+smallint\[\] NOT NULL", table)
    assert "CHECK (tones <@ ARRAY[1, 2, 3, 4]::smallint[])" in table
    assert re.search(r"built_at timestamptz NOT NULL DEFAULT now\(\)", table)


@pytest.mark.parametrize("name", FUNCTIONS)
def test_function_headers(name):
    args, returns, volatility, definer = FUNCTIONS[name]
    head = " ".join(_header(name).split())
    assert "SET search_path = public, pg_temp" in head
    assert ("SECURITY DEFINER" in head) is definer
    if volatility:
        assert volatility in head
    assert re.search(rf"RETURNS {re.escape(returns)}", head)
    assert f"REVOKE ALL ON FUNCTION public.{name}({args}) FROM PUBLIC, anon, authenticated;" in CODE
    assert f"GRANT EXECUTE ON FUNCTION public.{name}({args}) TO service_role;" in CODE
    assert f"COMMENT ON FUNCTION public.{name}({args}) IS" in CODE


def test_variant_signature_matches_tech_14():
    head = " ".join(_header("calibration_zh_tone_variants").split())
    assert "calibration_zh_tone_variants( p_pronunciation text, p_vocab_id integer ) RETURNS text[]" in head


def test_refresh_is_idempotent_rebuild_from_native_zh_readings():
    fn = _function("calibration_refresh_zh_tone_inventory")
    assert "pg_advisory_xact_lock(hashtext('calibration_refresh_zh_tone_inventory'))" in fn
    assert "DELETE FROM calibration_zh_tone_inventory WHERE true;" in fn
    assert "s.word_language_id = 1" in fn and "s.definition_language_id = 1" in fn
    assert "FILTER (WHERE p.tone BETWEEN 1 AND 4)" in fn
    assert "GET DIAGNOSTICS v_rows = ROW_COUNT;" in fn and "RETURN v_rows;" in fn
    # the migration fills the table once
    assert CODE.rstrip().endswith("SELECT public.calibration_refresh_zh_tone_inventory();")


def test_variant_rules_present():
    fn = _function("calibration_zh_tone_variants")
    assert f"LIMIT {pt.VARIANT_CAP}" in fn
    assert "IN ('一', '不')" in fn and "char_length(hdr.lemma) = hdr.n" in fn
    assert "h.orig[c.k + 1] = 3 AND o.t = 2" in fn and "h.orig[c.k + 2] = 3" in fn
    assert "WHERE syl.tone BETWEEN 1 AND 4" in fn and "a.t BETWEEN 1 AND 4" in fn
    assert "s.vocab_id = p_vocab_id" in fn
    assert "md5(array_to_string(c.tones, ''))" in fn


def test_parse_and_mark_share_pythons_constants():
    parse = _function("calibration_zh_parse_pinyin")
    assert "'[\\s''·-]+|[^\\s''·-]+'" in parse
    assert pt._SEGMENT_RE.pattern == "[\\s'·-]+|[^\\s'·-]+"
    assert "'^[a-z]*(u:)?[a-z]*$'" in parse and pt._BASE_RE.pattern == "[a-z]*(?:u:)?[a-z]*"
    assert "public.calibration_display_pronunciation(p_pronunciation, 1::smallint)" in parse
    for code, tone in (("772", 1), ("769", 2), ("780", 3)):
        assert f"chr({code}) THEN {tone}" in parse
        assert pt.MARK_OF_TONE[tone] == chr(int(code))
    mark = _function("calibration_zh_mark_syllable")
    assert "chr((ARRAY[772, 769, 780, 768])[p_tone])" in mark
    assert [ord(pt.MARK_OF_TONE[t]) for t in (1, 2, 3, 4)] == [772, 769, 780, 768]


def test_rollback_drops_everything_this_file_creates():
    code = " ".join(line for line in ROLLBACK.splitlines() if not line.startswith("--"))
    for name, (args, *_rest) in FUNCTIONS.items():
        assert f"DROP FUNCTION IF EXISTS public.{name}({args});" in code
    assert "DROP TABLE IF EXISTS public.calibration_zh_tone_inventory;" in code
    # variants first: it is the only one nothing else here depends on
    assert code.index("calibration_zh_tone_variants") < code.index("calibration_zh_parse_pinyin")
    assert code.index("DROP FUNCTION IF EXISTS public.calibration_zh_parse_pinyin") < code.index("DROP TABLE")
