"""Static checks for migrations/exercise_content_session_rpcs.sql and its rollback (TASK-985).

ADR-047 §7: get_practice_session and get_review_ahead_items gain p_include_content boolean
DEFAULT true. The new bodies are the canonical bodies with only content edits, which is
checked by diffing them line by line (whitespace-normalised) against
migrations/get_practice_session_language_scope.sql and migrations/practice_review_ahead.sql.
"""
from __future__ import annotations

import difflib
import re

import pytest

from tests.test_exercise_content_migration_schema import (
    MIGRATIONS, body_lines, function_def, has_statement, norm, read, revoke_grant_problems,
    scan_file, signature_re, statements)

NEW = 'exercise_content_session_rpcs.sql'
ROLLBACK = 'exercise_content_session_rpcs_rollback.sql'
GPS_CANON = 'get_practice_session_language_scope.sql'
RAI_CANON = 'practice_review_ahead.sql'

GPS5 = ('uuid', 'smallint', 'text', 'smallint', 'numeric')
RAI5 = ('uuid', 'smallint', 'integer', 'integer', 'integer[]')
INCLUDE = ('p_include_content', 'boolean', 'true')


def diff(old_body: str, new_body: str) -> tuple[list[str], list[str]]:
    removed, added = [], []
    for line in difflib.ndiff(body_lines(old_body), body_lines(new_body)):
        if line.startswith('- '):
            removed.append(line[2:])
        elif line.startswith('+ '):
            added.append(line[2:])
    return removed, added


@pytest.fixture(scope='module')
def sql() -> str:
    return read(NEW)


@pytest.fixture(scope='module')
def gps(sql):
    return function_def(sql, 'get_practice_session')


@pytest.fixture(scope='module')
def rai(sql):
    return function_def(sql, 'get_review_ahead_items')


@pytest.fixture(scope='module')
def gps_old():
    return function_def(read(GPS_CANON), 'get_practice_session')


@pytest.fixture(scope='module')
def rai_old():
    return function_def(read(RAI_CANON), 'get_review_ahead_items')


# --------------------------------------------------------------------------------------
# Body diffs: only content edits
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize('which', ['get_practice_session', 'get_review_ahead_items'])
def test_only_content_lines_change(which, gps, rai, gps_old, rai_old):
    old, new = (gps_old, gps) if which == 'get_practice_session' else (rai_old, rai)
    removed, added = diff(old.body, new.body)
    assert removed and added
    assert all('content' in line for line in removed), [x for x in removed if 'content' not in x]
    assert all('content' in line or 'p_include_content' in line for line in added), \
        [x for x in added if 'content' not in x]


def test_get_practice_session_edits(gps, gps_old):
    removed, added = diff(gps_old.body, gps.body)
    assert sorted(removed) == sorted(['e.content,', 'e.content,',
                                      "'content', v_item.content,", "'content', v_item.content,"])
    assert added.count('CASE WHEN p_include_content THEN e.content END AS content,') == 2
    assert added.count('e.content_version,') == 2
    assert added.count("'content_version', v_item.content_version,") == 2
    sets = [x for x in added if x.startswith('IF p_include_content THEN')]
    assert sets == ["IF p_include_content THEN v_items := jsonb_set(v_items, '{-1,content}', "
                    "COALESCE(v_item.content, 'null'::jsonb)); END IF;"] * 2
    # every exercise item object carries content_version; markers (no exercise_id) do not change
    b = gps.body
    assert b.count("'content_version',") == b.count("'exercise_id',") == 2
    assert "'content'," not in b


def test_get_practice_session_sets_content_on_the_appended_item(gps):
    """`v_items || jsonb_build_object(...) || CASE ... END` is left-associative: it would append
    the CASE result as a SEPARATE array element ('{}' when content is off). The content must be
    set on the item just appended, right after each append, inside the same branch."""
    lines = body_lines(gps.body)
    assert not [x for x in lines if '|| CASE' in x]
    for mode in ("'mode', 'maintenance'", "'mode', 'acquisition'"):
        i = lines.index(mode)
        assert lines[i + 1] == ');'
        assert lines[i + 2].startswith('-- content only when p_include_content')
        assert lines[i + 3].startswith("IF p_include_content THEN v_items := jsonb_set(v_items, '{-1,content}'")


def test_get_review_ahead_items_edits(rai, rai_old):
    removed, added = diff(rai_old.body, rai.body)
    assert removed == ['e.content,', "'content', content,"]
    assert added == [
        'CASE WHEN p_include_content THEN e.content END AS content,',
        'e.content_version,',
        "'content_version', content_version",
        ") || CASE WHEN p_include_content THEN jsonb_build_object('content', content) "
        "ELSE '{}'::jsonb END || jsonb_build_object(",
    ]


# --------------------------------------------------------------------------------------
# Signatures, grants, drops
# --------------------------------------------------------------------------------------
def test_signatures(gps, rai, gps_old, rai_old):
    assert not gps.or_replace and not rai.or_replace, 'CREATE FUNCTION after dropping the 5-arg one'
    assert gps.params == gps_old.params + [INCLUDE]
    assert rai.params == rai_old.params + [INCLUDE]
    assert gps.header == 'RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path = public, pg_temp'
    assert rai.header == 'RETURNS jsonb LANGUAGE sql VOLATILE SET search_path = public, pg_temp'
    assert rai_old.header == rai.header, 'get_review_ahead_items keeps its live attributes'


def test_five_argument_functions_dropped_first(sql, gps, rai):
    stmts = [norm(s) for s in statements(sql)]
    drop_gps = stmts.index(f"DROP FUNCTION IF EXISTS public.get_practice_session({', '.join(GPS5)})")
    drop_rai = stmts.index(f"DROP FUNCTION IF EXISTS public.get_review_ahead_items({', '.join(RAI5)})")
    assert drop_gps < gps.position and drop_rai < rai.position


def test_one_transaction_with_grants_comments_and_reload(sql, gps, rai):
    stmts = [norm(s) for s in statements(sql)]
    assert stmts[0] == 'BEGIN' and stmts[-1] == 'COMMIT'
    assert not [s for s in stmts[1:-1] if s in ('BEGIN', 'COMMIT', 'ROLLBACK')]
    assert revoke_grant_problems(sql, gps) + revoke_grant_problems(sql, rai) == []
    for fn in (gps, rai):
        assert has_statement(sql, rf"COMMENT ON FUNCTION {signature_re(fn.name, fn.arg_types)} IS "
                                  r".*ADR-047.*p_include_content.*"), fn.name
    assert has_statement(sql, r"NOTIFY pgrst, 'reload schema'")


def test_dead_content_functions_dropped(sql):
    stmts = [norm(s) for s in statements(sql)]
    for sig in ('get_exercise_session(uuid, smallint, integer)',
                'get_exercise_session(uuid, smallint, integer, numeric)',
                'get_ladder_session(uuid, smallint, integer)'):
        assert f'DROP FUNCTION IF EXISTS public.{sig}' in stmts, sig


def test_canonical_files_are_not_archived_here():
    assert (MIGRATIONS / GPS_CANON).exists() and (MIGRATIONS / RAI_CANON).exists()
    assert not (MIGRATIONS / 'archive' / GPS_CANON).exists()
    assert not (MIGRATIONS / 'archive' / RAI_CANON).exists()


def test_security_lint_is_clean_for_both_files():
    for name in (NEW, ROLLBACK):
        problems = scan_file(MIGRATIONS / name)
        assert not any(problems.values()), (name, problems)


# --------------------------------------------------------------------------------------
# Rollback
# --------------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def rollback() -> str:
    return read(ROLLBACK)


def test_rollback_header(rollback):
    header = rollback[:rollback.index('BEGIN;')]
    assert 'EXERCISE_CONTENT_SOURCE=db' in header
    assert 'NOT recreated' in header


def test_rollback_recreates_the_canonical_functions_verbatim(rollback, gps_old, rai_old):
    for old in (gps_old, rai_old):
        fn = function_def(rollback, old.name)
        assert fn.body == old.body, f'{old.name}: body differs from the canonical file'
        assert fn.params == old.params and fn.header == old.header, old.name
        assert revoke_grant_problems(rollback, fn) == []


def test_rollback_drops_the_six_argument_functions_and_guards(rollback):
    stmts = [norm(s) for s in statements(rollback)]
    assert stmts[0] == 'BEGIN' and stmts[-1] == 'COMMIT'
    gps6 = ', '.join(GPS5 + ('boolean',))
    rai6 = ', '.join(RAI5 + ('boolean',))
    i = stmts.index(f'DROP FUNCTION IF EXISTS public.get_practice_session({gps6})')
    j = stmts.index(f'DROP FUNCTION IF EXISTS public.get_review_ahead_items({rai6})')
    guard = next(k for k, s in enumerate(stmts) if s.startswith('DO $guard$'))
    assert guard < i and guard < j
    assert "column_name = 'content'" in stmts[guard]
    assert not re.search(r'FUNCTION public\.get_(exercise|ladder)_session', rollback)
    assert has_statement(rollback, r"NOTIFY pgrst, 'reload schema'")
