"""Static checks for migrations/exercise_content_storage.sql and its rollback (TASK-984).

ADR-047 §7 (schema changes) and §8 (the RPC contract the dual writer codes against). No
database: the SQL is parsed. The behaviour itself is covered by
tests/sql/test_exercise_content_storage.sql, which the operator runs on staging (TASK-994).

The SQL helpers at the top (statements, function_defs, body_lines, code_without_strings) are
also used by test_exercise_content_migration_rpcs.py and test_exercise_content_migration_cutover.py.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.test_migration_security_lint import _split_statements, _strip_comments, scan_file

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / 'migrations'
STORAGE = 'exercise_content_storage.sql'
STORAGE_ROLLBACK = 'exercise_content_storage_rollback.sql'
SQL_TEST = ROOT / 'tests' / 'sql' / 'test_exercise_content_storage.sql'


# --------------------------------------------------------------------------------------
# SQL helpers (shared with the other ADR-047 migration tests)
# --------------------------------------------------------------------------------------
def read(name: str) -> str:
    return (MIGRATIONS / name).read_text(encoding='utf-8')


def norm(text: str) -> str:
    """Collapse whitespace."""
    return ' '.join(text.split())


def statements(sql: str) -> list[str]:
    """Top-level statements, comments outside dollar-quoted bodies removed."""
    return [full for full, _bare in _split_statements(_strip_comments(sql)) if full]


def bare_statements(sql: str) -> list[str]:
    """Top-level statements with every quoted string and dollar body replaced by '' / $$."""
    return [bare for _full, bare in _split_statements(_strip_comments(sql)) if bare]


@dataclass
class FunctionDef:
    name: str
    or_replace: bool
    params: list[tuple[str, str, str | None]]   # (name, type, default), normalised
    header: str                                 # between the parameter list and AS $tag$
    body: str                                   # raw text inside the dollar quotes
    position: int                               # index of the statement in statements()

    @property
    def arg_types(self) -> tuple[str, ...]:
        return tuple(t for _n, t, _d in self.params)


_CREATE_FN_RE = re.compile(r'^\s*CREATE\s+(OR\s+REPLACE\s+)?FUNCTION\s+public\.(\w+)\s*\(', re.I)
_DOLLAR_AS_RE = re.compile(r'\bAS\s+(\$[A-Za-z_]*\$)', re.I)


def _matching_paren(text: str, start: int) -> int:
    """Index just past the ')' closing the '(' before ``start`` (quote-aware)."""
    depth, i, in_str = 1, start, False
    while depth:
        c = text[i]
        if in_str:
            if c == "'":
                in_str = False
        elif c == "'":
            in_str = True
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        i += 1
    return i


def _split_top_level(text: str, sep: str = ',') -> list[str]:
    parts, depth, buf, in_str = [], 0, [], False
    for c in text:
        if in_str:
            in_str = c != "'"
        elif c == "'":
            in_str = True
        elif c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(''.join(buf))
            buf = []
            continue
        buf.append(c)
    if ''.join(buf).strip():
        parts.append(''.join(buf))
    return parts


def parse_params(text: str) -> list[tuple[str, str, str | None]]:
    out = []
    for part in _split_top_level(text):
        m = re.match(r'^\s*(\w+)\s+(.+?)(?:\s+DEFAULT\s+(.+?))?\s*$', part, re.I | re.S)
        assert m, f'unparseable parameter: {part!r}'
        out.append((m.group(1), norm(m.group(2)).lower(),
                    norm(m.group(3)) if m.group(3) is not None else None))
    return out


def function_defs(sql: str) -> list[FunctionDef]:
    out = []
    for pos, full in enumerate(statements(sql)):
        m = _CREATE_FN_RE.match(full)
        if not m:
            continue
        close = _matching_paren(full, m.end())
        rest = full[close:]
        dm = _DOLLAR_AS_RE.search(rest)
        assert dm, f'no dollar-quoted body in {m.group(2)}'
        tag = dm.group(1)
        end = rest.index(tag, dm.end())
        out.append(FunctionDef(
            name=m.group(2), or_replace=bool(m.group(1)),
            params=parse_params(full[m.end():close - 1]),
            header=norm(rest[:dm.start()]), body=rest[dm.end():end], position=pos))
    return out


def function_def(sql: str, name: str) -> FunctionDef:
    found = [f for f in function_defs(sql) if f.name == name]
    assert len(found) == 1, f'expected exactly one CREATE FUNCTION public.{name}, got {len(found)}'
    return found[0]


def body_lines(body: str) -> list[str]:
    """Whitespace-normalised non-empty lines."""
    return [norm(line) for line in body.splitlines() if line.strip()]


def code_without_strings(body: str) -> str:
    """Body text with -- / block comments and single-quoted literals removed."""
    out, i, n = [], 0, len(body)
    while i < n:
        if body.startswith('--', i):
            j = body.find('\n', i)
            i = n if j == -1 else j
        elif body.startswith('/*', i):
            j = body.find('*/', i + 2)
            i = n if j == -1 else j + 2
            out.append(' ')
        elif body[i] == "'":
            j = i + 1
            while j < n:
                if body[j] == "'":
                    if body.startswith("''", j):
                        j += 2
                        continue
                    break
                j += 1
            out.append("''")
            i = j + 1
        else:
            out.append(body[i])
            i += 1
    return ''.join(out)


def quoted_strings(text: str) -> list[str]:
    return re.findall(r"'([^']*)'", text)


def signature_re(name: str, arg_types: tuple[str, ...]) -> str:
    return r'public\.' + name + r'\(\s*' + r'\s*,\s*'.join(re.escape(t) for t in arg_types) + r'\s*\)'


def has_statement(sql: str, pattern: str) -> bool:
    return any(re.fullmatch(pattern, norm(s), re.I | re.S) for s in statements(sql))


def revoke_grant_problems(sql: str, fn: FunctionDef) -> list[str]:
    sig = signature_re(fn.name, fn.arg_types)
    problems = []
    if not has_statement(sql, rf'REVOKE ALL ON FUNCTION {sig} FROM PUBLIC, anon, authenticated'):
        problems.append(f'{fn.name}: no REVOKE ALL ... FROM PUBLIC, anon, authenticated')
    if not has_statement(sql, rf'GRANT EXECUTE ON FUNCTION {sig} TO service_role'):
        problems.append(f'{fn.name}: no GRANT EXECUTE ... TO service_role')
    return problems


def context_free_types_of_old_index() -> list[str]:
    """Type list of uq_exercises_context_free_variant (task743_context_free_exercise_caps.sql)."""
    for s in statements(read('task743_context_free_exercise_caps.sql')):
        if re.match(r'\s*CREATE UNIQUE INDEX IF NOT EXISTS uq_exercises_context_free_variant\b', s):
            m = re.search(r'exercise_type\s+IN\s*\((.*?)\)', s, re.S)
            return quoted_strings(m.group(1))
    raise AssertionError('uq_exercises_context_free_variant not found in task743')


def renderer_context_free_types() -> set[str]:
    src = (ROOT / 'services/vocabulary_ladder/exercise_renderer.py').read_text(encoding='utf-8')
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == '_CONTEXT_FREE_UNIQUE_TYPES' for t in node.targets):
            return {c.value for c in ast.walk(node.value)
                    if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    raise AssertionError('_CONTEXT_FREE_UNIQUE_TYPES not found in exercise_renderer.py')


def array_constant(body: str, name: str) -> list[str]:
    m = re.search(rf'\b{name}\s+constant\s+text\[\]\s*:=\s*ARRAY\[(.*?)\]', body, re.S | re.I)
    assert m, f'{name} constant not found'
    return quoted_strings(m.group(1))


# --------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def sql() -> str:
    return read(STORAGE)


@pytest.fixture(scope='module')
def commit(sql) -> FunctionDef:
    return function_def(sql, 'exercise_content_commit')


ADR_FUNCTIONS = {
    'exercise_content_begin': [('p_sense_id', 'integer', None)],
    'exercise_content_commit': [
        ('p_sense_id', 'integer', None),
        ('p_expected_version', 'integer', None),
        ('p_expected_ids', 'uuid[]', None),
        ('p_new_version', 'integer', None),
        ('p_delete_ids', 'uuid[]', "'{}'"),
        ('p_insert_rows', 'jsonb', "'[]'"),
        ('p_update_contents', 'jsonb', "'{}'"),
    ],
    'exercise_content_live_versions': [('p_language_id', 'integer', None)],
}


# --------------------------------------------------------------------------------------
# The migration file
# --------------------------------------------------------------------------------------
def test_header_documents_status_order_and_rollback_rule():
    raw = read(STORAGE)
    header = raw[:raw.index('BEGIN;')]
    assert 'NOT applied' in header
    assert 'ADR-047' in header and 'TASK-994' in header
    assert header.index('exercise_content_storage.sql') < header.index('exercise_content_session_rpcs.sql'), \
        'the header must give the apply order: this file, then exercise_content_session_rpcs.sql'
    assert 'exercise_content_storage_rollback.sql' in header
    assert re.search(r'EXERCISE_CONTENT_WRITE=dual\s+was ever set', header), \
        'the header must say the rollback is valid only before EXERCISE_CONTENT_WRITE=dual was ever set'


def test_one_transaction(sql):
    stmts = [norm(s).upper() for s in statements(sql)]
    assert stmts[0] == 'BEGIN' and stmts[-1] == 'COMMIT'
    assert not [s for s in stmts[1:-1] if s in ('BEGIN', 'COMMIT', 'ROLLBACK', 'END')]


def test_additive_only_and_no_update_of_exercises(sql):
    """No top-level data change on exercises (function bodies are allowed to UPDATE: they run
    per sense, later). Every top-level statement is one of the additive kinds."""
    bare = bare_statements(sql)
    for s in bare:
        assert not re.search(r'\bUPDATE\s+(public\.)?exercises\b', s, re.I), s
        assert not re.search(r'\bDELETE\s+FROM\b', s, re.I), s
    allowed = re.compile(
        r'^(BEGIN|COMMIT|NOTIFY pgrst, \'\'|'
        r'ALTER TABLE public\.exercises ADD COLUMN IF NOT EXISTS .*|'
        r'COMMENT ON (COLUMN|SEQUENCE|FUNCTION) .*|'
        r'CREATE SEQUENCE IF NOT EXISTS .*|REVOKE ALL ON .*|GRANT .*|'
        r'CREATE OR REPLACE FUNCTION public\.exercise_content_\w+\(.*|'
        r'INSERT INTO storage\.buckets .*)$', re.S)
    others = [norm(s) for s in bare if not allowed.match(norm(s))]
    assert not others, f'non-additive top-level statements: {others}'


def test_columns_are_catalog_only(sql):
    alter = [norm(s) for s in statements(sql) if s.lstrip().upper().startswith('ALTER TABLE')]
    assert alter == ['ALTER TABLE public.exercises '
                     'ADD COLUMN IF NOT EXISTS content_version integer NOT NULL DEFAULT 0, '
                     'ADD COLUMN IF NOT EXISTS dedupe_key text']


def test_sequence_and_its_grants(sql):
    assert has_statement(sql, r'CREATE SEQUENCE IF NOT EXISTS public\.exercise_content_version_seq '
                              r'AS integer START WITH 1')
    assert has_statement(sql, r'REVOKE ALL ON SEQUENCE public\.exercise_content_version_seq '
                              r'FROM PUBLIC, anon, authenticated')
    assert has_statement(sql, r'GRANT USAGE, SELECT ON SEQUENCE public\.exercise_content_version_seq '
                              r'TO service_role')
    assert not [s for s in statements(sql)
                if re.match(r'\s*GRANT\b', s) and re.search(r'\b(PUBLIC|anon|authenticated)\b', s)]


def test_functions_match_the_adr_signatures(sql):
    defs = {f.name: f for f in function_defs(sql)}
    assert set(defs) == set(ADR_FUNCTIONS)
    for name, params in ADR_FUNCTIONS.items():
        fn = defs[name]
        assert fn.or_replace
        assert fn.params == params, name
        assert fn.header.startswith('RETURNS jsonb '), name
        assert 'SECURITY INVOKER' in fn.header, name
        assert 'SECURITY DEFINER' not in fn.header, name
        assert 'SET search_path = public, pg_temp' in fn.header, name
    assert 'LANGUAGE plpgsql VOLATILE' in defs['exercise_content_begin'].header
    assert 'LANGUAGE plpgsql VOLATILE' in defs['exercise_content_commit'].header
    assert 'LANGUAGE sql STABLE' in defs['exercise_content_live_versions'].header


def test_every_function_is_service_role_only_and_commented(sql):
    problems = []
    for fn in function_defs(sql):
        problems += revoke_grant_problems(sql, fn)
        sig = signature_re(fn.name, fn.arg_types)
        if not has_statement(sql, rf"COMMENT ON FUNCTION {sig} IS .*ADR-047.*"):
            problems.append(f'{fn.name}: no COMMENT ON FUNCTION citing ADR-047')
    assert not problems, problems


def test_begin_contract(sql):
    body = function_def(sql, 'exercise_content_begin').body
    assert "nextval('public.exercise_content_version_seq')" in body
    assert 'COALESCE(max(e.content_version), 0)' in body
    assert re.search(r'\) ORDER BY e\.id\)', body), 'rows must be ordered by id'
    assert 'WHERE e.word_sense_id = p_sense_id' in body
    row_obj = re.search(r'jsonb_agg\(jsonb_build_object\((.*?)\) ORDER BY', body, re.S).group(1)
    assert re.findall(r"'(\w+)'\s*,", row_obj) == [
        'id', 'language_id', 'exercise_type', 'ladder_level', 'word_asset_id', 'is_active',
        'content_version']
    result = re.search(r'RETURN jsonb_build_object\((.*?)\);', body, re.S).group(1)
    assert re.findall(r"'(\w+)'\s*,", result) == ['sense_id', 'current_version', 'new_version', 'rows']
    assert 'pg_advisory' not in body, 'begin takes no lock; the commit does'


def test_commit_lock_and_namespace(commit):
    from services.exercise_content import store

    assert store.COMMIT_LOCK_NAMESPACE == 47047
    assert f'PERFORM pg_advisory_xact_lock({store.COMMIT_LOCK_NAMESPACE}, p_sense_id);' in commit.body


def test_commit_order_lock_cas_validate_apply_stamp(commit):
    """Static input checks, then the lock, then version CAS, then row-set CAS, then the checks
    that need the sense's rows, then delete -> insert -> content update -> version stamp."""
    b = commit.body
    marks = [
        b.index("IF jsonb_typeof(v_insert_rows) <> 'array'"),
        b.index('PERFORM pg_advisory_xact_lock'),
        b.index('IF v_current <> p_expected_version'),
        b.index('IF v_live_ids IS DISTINCT FROM v_expected_ids'),
        b.index('IF p_new_version <= v_current'),
        b.index('DELETE FROM public.exercises'),
        b.index('INSERT INTO public.exercises'),
        b.index('SET dedupe_key = CASE'),
        b.index('SET content_version = p_new_version'),
    ]
    assert marks == sorted(marks)
    # the lock comes before the first read of the sense's rows
    assert b.index('PERFORM pg_advisory_xact_lock') < b.index('FROM public.exercises e')


def test_commit_results_and_errors(commit):
    b = norm(commit.body)
    assert ("RETURN jsonb_build_object('ok', false, 'reason', 'version_conflict', "
            "'current_version', v_current);") in b
    assert ("RETURN jsonb_build_object('ok', false, 'reason', 'rows_changed', "
            "'current_version', v_current);") in b
    assert ("RETURN jsonb_build_object('ok', true, 'version', p_new_version, 'deleted', v_deleted, "
            "'inserted', v_inserted, 'updated', v_updated);") in b
    assert b.count("USING ERRCODE = '22023'") >= 10
    # the three ADR §8 cases
    assert "(v_row ->> 'word_sense_id')::integer IS DISTINCT FROM p_sense_id" in b
    assert 'IF p_new_version <= v_current THEN' in b
    assert 'WHERE d.id <> ALL (v_live_ids)' in b
    assert 'IF v_key::uuid <> ALL (v_live_ids) THEN' in b
    # row-id set compared as a sorted set
    assert 'array_agg(e.id ORDER BY e.id)' in b
    assert 'array_agg(DISTINCT x.id ORDER BY x.id)' in b


def test_commit_insert_columns_and_defaults(commit):
    b = commit.body
    cols = re.search(r'INSERT INTO public\.exercises \((.*?)\)\s*SELECT', b, re.S).group(1)
    assert [c.strip() for c in cols.split(',')] == [
        'id', 'language_id', 'exercise_type', 'source_type', 'word_sense_id',
        'corpus_collocation_id', 'word_asset_id', 'content', 'tags', 'difficulty_static',
        'complexity_tier', 'ladder_level', 'pattern_code', 'is_active', 'generation_batch_id',
        'content_version', 'dedupe_key']
    record = re.search(r'jsonb_to_record\(x\.row_json\) AS r\((.*?)\)\s*ORDER BY', b, re.S).group(1)
    assert parse_params(record) == [
        ('id', 'uuid', None), ('language_id', 'integer', None), ('exercise_type', 'text', None),
        ('source_type', 'text', None), ('word_sense_id', 'integer', None),
        ('corpus_collocation_id', 'integer', None), ('word_asset_id', 'bigint', None),
        ('tags', 'jsonb', None), ('difficulty_static', 'numeric', None),
        ('complexity_tier', 'text', None), ('ladder_level', 'integer', None),
        ('pattern_code', 'text', None), ('is_active', 'boolean', None),
        ('generation_batch_id', 'uuid', None)]
    nb = norm(b)
    assert "COALESCE(r.tags, '{}'::jsonb)" in nb
    assert 'COALESCE(r.is_active, true)' in nb
    assert 'r.source_type::public.exercise_source_type' in nb
    assert "x.row_json -> 'content'," in nb
    assert 'ORDER BY x.ord' in nb


def test_dedupe_key_comes_from_the_json_for_the_eight_types(commit):
    b = norm(commit.body)
    md5s = re.findall(r'md5\((.*?)\)\)?', b)
    assert md5s == ["coalesce(x.row_json -> 'content' ->> 'context_sentence', ''",
                    "coalesce(u.value ->> 'context_sentence', ''"], md5s
    assert 'CASE WHEN r.exercise_type = ANY (c_context_free)' in b
    assert 'SET dedupe_key = CASE WHEN e.exercise_type = ANY (c_context_free)' in b
    assert not re.search(r'\be\.content\b', b), 'dedupe_key must never be read from the column'


def test_context_free_types_match_renderer_and_old_index(commit):
    types = array_constant(commit.body, 'c_context_free')
    assert len(types) == len(set(types)) == 8
    assert set(types) == renderer_context_free_types()
    assert set(types) == set(context_free_types_of_old_index())


def test_commit_update_and_version_stamp(commit):
    b = norm(commit.body)
    assert ', content = u.value FROM jsonb_each(v_updates) AS u(key, value) ' \
           'WHERE e.word_sense_id = p_sense_id AND e.id = u.key::uuid;' in b
    assert ('UPDATE public.exercises e SET content_version = p_new_version '
            'WHERE e.word_sense_id = p_sense_id '
            'AND e.content_version IS DISTINCT FROM p_new_version '
            'AND e.id = ANY (v_live_ids);') in b


def test_live_versions_contract(sql):
    b = norm(function_def(sql, 'exercise_content_live_versions').body)
    assert "COALESCE(jsonb_object_agg(v.word_sense_id::text, v.versions), '{}'::jsonb)" in b
    assert 'jsonb_agg(DISTINCT e.content_version ORDER BY e.content_version) AS versions' in b
    assert 'WHERE e.language_id = p_language_id AND e.word_sense_id IS NOT NULL' in b
    assert 'GROUP BY e.word_sense_id' in b


def test_private_bucket_row(sql):
    inserts = [norm(s) for s in statements(sql) if 'storage.buckets' in s]
    assert inserts == [
        "INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) "
        "VALUES ('exercise-content', 'exercise-content', false, 1048576, "
        "ARRAY['application/json']) ON CONFLICT (id) DO NOTHING"]


def test_reloads_postgrest_schema(sql):
    assert has_statement(sql, r"NOTIFY pgrst, 'reload schema'")


def test_security_lint_is_clean_for_both_files():
    for name in (STORAGE, STORAGE_ROLLBACK):
        problems = scan_file(MIGRATIONS / name)
        assert not any(problems.values()), (name, problems)


# --------------------------------------------------------------------------------------
# The rollback file
# --------------------------------------------------------------------------------------
def test_rollback_drops_functions_sequence_and_columns():
    rb = read(STORAGE_ROLLBACK)
    stmts = [norm(s) for s in statements(rb)]
    assert stmts[0] == 'BEGIN' and stmts[-1] == 'COMMIT'
    for name, params in ADR_FUNCTIONS.items():
        types = ', '.join(t for _n, t, _d in params)
        assert f'DROP FUNCTION IF EXISTS public.{name}({types})' in stmts, name
    assert 'DROP SEQUENCE IF EXISTS public.exercise_content_version_seq' in stmts
    assert ('ALTER TABLE public.exercises DROP COLUMN IF EXISTS dedupe_key, '
            'DROP COLUMN IF EXISTS content_version') in stmts


def test_rollback_never_touches_bucket_objects_and_says_so():
    rb = read(STORAGE_ROLLBACK)
    code = ' '.join(bare_statements(rb))
    assert 'storage.' not in code, 'the rollback must not delete bucket objects or the bucket'
    header = rb[:rb.index('BEGIN;')]
    assert re.search(r'never deletes bucket objects', header)
    assert 'EXERCISE_CONTENT_WRITE=dual' in header


def test_rollback_guards_against_dual_writes_and_the_session_rpcs():
    rb = norm(read(STORAGE_ROLLBACK))
    assert "to_regprocedure('public.get_practice_session(uuid, smallint, text, smallint, numeric, boolean)')" in rb
    assert "to_regprocedure('public.get_review_ahead_items(uuid, smallint, integer, integer, integer[], boolean)')" in rb
    assert 'SELECT 1 FROM public.exercises WHERE content_version <> 0' in rb
    assert rb.index('DO $guard$') < rb.index('DROP FUNCTION IF EXISTS')


# --------------------------------------------------------------------------------------
# The staging SQL test
# --------------------------------------------------------------------------------------
def test_sql_scenario_file_is_rollback_only_and_covers_the_cases():
    text = SQL_TEST.read_text(encoding='utf-8')
    stmts = [norm(s) for s in statements(text)]
    assert stmts[0] == 'BEGIN' and stmts[-1] == 'ROLLBACK'
    assert 'COMMIT' not in stmts
    assert {s.split(' ')[0] for s in stmts[1:-1]} <= {'DO', 'SET', 'RESET'}
    for needle in ("'current_version'", "'version_conflict'", "'rows_changed'", "SQLSTATE '22023'",
                   'dedupe_key IS DISTINCT FROM md5', 'exercise_content_live_versions(v_lang)',
                   "classid = 47047", "has_function_privilege('anon'",
                   "has_sequence_privilege('service_role'", "public IS FALSE"):
        assert needle in text, needle

