"""Static checks for the ADR-049 cut-over runbook (TASK-1018).

migrations/exercise_content_drop_column.sql was run step by step by the operator (TASK-1030,
2026-11-18/19) and is the canonical definition of exercise_content_commit and the two session
RPCs (live md5 = these bodies, checked 2026-11-19);
migrations/exercise_content_drop_column_rollback.sql undoes its schema part. No database: the
SQL is parsed. The step-3 functions are checked against the pre-drop versions in
exercise_content_storage.sql (TASK-1016) and archive/exercise_content_session_rpcs.sql
(TASK-1017, archived in TASK-1031), so a later edit of the canonical bodies has to be deliberate.
"""
from __future__ import annotations

import difflib
import re

import pytest

from tests.test_exercise_content_migration_schema import (
    MIGRATIONS, array_constant, bare_statements, body_lines, code_without_strings,
    context_free_types_of_old_index, function_def, function_defs, norm, quoted_strings, read,
    revoke_grant_problems, scan_file, signature_re, statements)

CUTOVER = 'exercise_content_drop_column.sql'
CUTOVER_ROLLBACK = 'exercise_content_drop_column_rollback.sql'
SESSION_RPCS = 'archive/exercise_content_session_rpcs.sql'      # the pre-drop session RPCs
STEP_RE = re.compile(r'^-- STEP (\w+) —', re.M)
FUNCTIONS = ('exercise_content_commit', 'get_practice_session', 'get_review_ahead_items')


def steps(text: str) -> dict[str, str]:
    """{step id: text up to the next step marker}, in file order."""
    marks = list(STEP_RE.finditer(text))
    return {m.group(1): text[m.start():(marks[i + 1].start() if i + 1 < len(marks) else len(text))]
            for i, m in enumerate(marks)}


def tight(sql: str) -> str:
    """norm() plus no whitespace around parentheses and commas (layout-insensitive compare)."""
    return re.sub(r'\s*([(),])\s*', r'\1', norm(sql))


def norm_statements(text: str) -> list[str]:
    return [norm(s) for s in statements(text)]


def type_lists(text: str) -> list[list[str]]:
    """Every `exercise_type IN (...)` list outside function bodies."""
    out = []
    for s in statements(text):
        if re.match(r'\s*CREATE (OR REPLACE )?FUNCTION', s):
            continue
        out += [quoted_strings(m.group(1))
                for m in re.finditer(r'exercise_type\s+IN\s*\((.*?)\)', s, re.S)]
    return out


def transaction_blocks(text: str) -> list[list[str]]:
    """Statements grouped by BEGIN ... COMMIT; statements outside a block are not returned."""
    blocks, cur = [], None
    for s in norm_statements(text):
        if s == 'BEGIN':
            assert cur is None, 'nested BEGIN'
            cur = []
        elif s == 'COMMIT':
            assert cur is not None, 'COMMIT without BEGIN'
            blocks.append(cur)
            cur = None
        elif cur is not None:
            cur.append(s)
    assert cur is None, 'BEGIN without COMMIT'
    return blocks


def outside_transactions(text: str) -> list[str]:
    out, depth = [], 0
    for s in norm_statements(text):
        if s == 'BEGIN':
            depth += 1
        elif s == 'COMMIT':
            depth -= 1
        elif depth == 0:
            out.append(s)
    return out


@pytest.fixture(scope='module')
def text() -> str:
    return read(CUTOVER)


@pytest.fixture(scope='module')
def by_step(text) -> dict[str, str]:
    return steps(text)


@pytest.fixture(scope='module')
def old_types() -> list[str]:
    types = context_free_types_of_old_index()
    assert len(types) == 8
    return types


def predecessors() -> dict[str, object]:
    return {
        'exercise_content_commit': function_def(read('exercise_content_storage.sql'), 'exercise_content_commit'),
        'get_practice_session': function_def(read(SESSION_RPCS), 'get_practice_session'),
        'get_review_ahead_items': function_def(read(SESSION_RPCS), 'get_review_ahead_items'),
    }


# --------------------------------------------------------------------------------------
# Structure and order
# --------------------------------------------------------------------------------------
def test_header(text):
    header = text[:STEP_RE.search(text).start()]
    assert 'STATUS: applied live 2026-11-18/19' in header
    assert 'TASK-1030' in header and 'ADR-049' in header and 'TASK-1031' in header
    assert 'never run this whole file at once' in header
    assert 'EXERCISE_CONTENT_DB_FALLBACK=0' in header
    assert 'exercise_content_drop_column_rollback.sql' in header


def test_steps_zero_to_five_in_order(by_step):
    assert list(by_step) == ['0', '1', '2', '3', '4', '5']


def test_only_step_three_is_a_transaction(text, by_step):
    assert len(transaction_blocks(text)) == 1
    for step, chunk in by_step.items():
        has_tx = 'BEGIN' in norm_statements(chunk)
        assert has_tx == (step == '3'), step


def test_vacuum_and_concurrent_index_never_in_a_transaction(text):
    inside = [s for block in transaction_blocks(text) for s in block]
    assert not [s for s in inside if s.startswith('VACUUM') or 'CONCURRENTLY' in s]
    outside = outside_transactions(text)
    assert 'VACUUM public.exercises' in outside
    assert 'VACUUM (FULL, ANALYZE) public.exercises' in outside
    assert [s for s in outside if s.startswith('CREATE UNIQUE INDEX CONCURRENTLY')]


def test_index_v2_before_drop_column_and_vacuum_full_last(text):
    stmts = norm_statements(text)
    v2 = next(i for i, s in enumerate(stmts)
              if s.startswith('CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_exercises_context_free_variant_v2'))
    drop = stmts.index('ALTER TABLE public.exercises DROP COLUMN content')
    full = stmts.index('VACUUM (FULL, ANALYZE) public.exercises')
    backfill = next(i for i, s in enumerate(stmts) if s.startswith('UPDATE public.exercises SET dedupe_key'))
    assert backfill < v2 < drop < full


def test_every_type_list_equals_the_old_index(text, old_types):
    lists = type_lists(text)
    assert len(lists) == 4, 'step 0a, step 1, step 2 and the step-3 precondition'
    assert all(lst == old_types for lst in lists), lists
    assert array_constant(function_def(text, 'exercise_content_commit').body, 'c_context_free') == old_types


def test_security_lint_is_clean_for_both_files():
    for name in (CUTOVER, CUTOVER_ROLLBACK):
        problems = scan_file(MIGRATIONS / name)
        assert not any(problems.values()), (name, problems)


# --------------------------------------------------------------------------------------
# Steps 0, 1, 2, 4, 5
# --------------------------------------------------------------------------------------
def test_step0_is_read_only_and_complete(by_step):
    stmts = norm_statements(by_step['0'])
    assert stmts and all(s.startswith('SELECT') for s in stmts)
    joined = ' '.join(stmts)
    assert 'WHERE dedupe_key IS NULL AND exercise_type IN (' in joined
    assert 'WHERE word_sense_id IS NULL' in joined
    assert 'pg_database_size(current_database())' in joined
    assert "pg_total_relation_size('public.exercises')" in joined


def test_step1_batched_backfill(by_step):
    stmts = norm_statements(by_step['1'])
    assert stmts[-1] == 'VACUUM public.exercises'
    update = stmts[0]
    assert update.startswith("UPDATE public.exercises SET dedupe_key = "
                             "md5(coalesce(content->>'context_sentence', '')) WHERE id IN ( SELECT id "
                             "FROM public.exercises WHERE dedupe_key IS NULL AND exercise_type IN (")
    assert update.endswith(') LIMIT 2000 )')
    assert len(stmts) == 2


def test_step2_v2_index_matches_the_old_predicate(by_step, old_types):
    stmts = norm_statements(by_step['2'])
    create = stmts[0]
    m = re.fullmatch(r'CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_exercises_context_free_variant_v2 '
                     r'ON public\.exercises \(word_sense_id, exercise_type, dedupe_key\) '
                     r'WHERE (.*)', create)
    assert m, create
    old = next(norm(s) for s in statements(read('task743_context_free_exercise_caps.sql'))
               if 'uq_exercises_context_free_variant' in s and s.lstrip().startswith('CREATE UNIQUE INDEX'))
    assert tight(m.group(1)) == tight(old[old.index(' WHERE ') + len(' WHERE '):])
    assert quoted_strings(m.group(1)) == old_types
    assert any('indisvalid' in s and 'uq_exercises_context_free_variant_v2' in s for s in stmts[1:])
    assert 'DROP INDEX CONCURRENTLY IF EXISTS public.uq_exercises_context_free_variant_v2' in by_step['2']


def test_step4_vacuum_full_and_space_note(by_step):
    assert norm_statements(by_step['4']) == ['VACUUM (FULL, ANALYZE) public.exercises']
    assert '~80 MB' in by_step['4'] and '2026-11-17' in by_step['4']


def test_step5_sizes(by_step):
    joined = ' '.join(norm_statements(by_step['5']))
    for needle in ('pg_database_size(current_database())', "pg_total_relation_size('public.exercises')",
                   "column_name = 'content'", 'uq_exercises_context_free_variant_v2'):
        assert needle in joined, needle


# --------------------------------------------------------------------------------------
# Step 3
# --------------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def step3(text) -> list[str]:
    return transaction_blocks(text)[0]


def test_step3_contents_and_order(step3):
    def at(prefix: str) -> int:
        hits = [i for i, s in enumerate(step3) if s.startswith(prefix)]
        assert len(hits) == 1, (prefix, hits)
        return hits[0]

    pre = at('DO $pre$')
    delete = at('DELETE FROM public.exercises WHERE word_sense_id IS NULL')
    semdisc_fn = at('DROP FUNCTION IF EXISTS public.apply_semdisc_notes(jsonb)')
    semdisc_tables = at('DROP TABLE IF EXISTS public.backup_semdisc_content_20261115, public.semdisc_rewrite_work')
    fns = [at(f'CREATE OR REPLACE FUNCTION public.{name}(') for name in FUNCTIONS]
    old_index = at('DROP INDEX IF EXISTS public.uq_exercises_context_free_variant')
    drop = at('ALTER TABLE public.exercises DROP COLUMN content')
    notify = at("NOTIFY pgrst, 'reload schema'")
    assert pre < delete < drop
    assert semdisc_fn < drop and semdisc_tables < drop
    assert max(fns) < old_index < drop < notify
    assert step3[-1] == "NOTIFY pgrst, 'reload schema'"
    assert not [s for s in step3 if 'CASCADE' in s.upper()]


def test_step3_preconditions(step3):
    pre = next(s for s in step3 if s.startswith('DO $pre$'))
    assert "to_regclass('public.uq_exercises_context_free_variant_v2')" in pre and 'indisvalid' in pre
    assert 'dedupe_key IS NULL' in pre and 'RAISE EXCEPTION' in pre


def test_step3_preconditions_enforce_the_archives_verify_and_session_rpcs(step3):
    """Review finding (2026-11-17): what 3b-3f destroy must be archived first, in SQL."""
    pre = re.sub(r'\s+', '', next(s for s in step3 if s.startswith('DO $pre$')))
    # Session RPC migration: the 6-argument forms exist, no 5-argument overload does.
    for sig in ('get_practice_session(uuid,smallint,text,smallint,numeric',
                'get_review_ahead_items(uuid,smallint,integer,integer,integer[]'):
        assert f"to_regprocedure('public.{sig},boolean)')ISNULL" in pre
        assert f"to_regprocedure('public.{sig})')ISNOTNULL" in pre
    assert pre.count("bucket_id='exercise-content'") == 4
    assert "starts_with(name,'_archive/exercises-content-')" in pre
    assert "right(name,14)='/manifest.json'" in pre
    assert "starts_with(o.name,'_archive/exercises-no-sense-')" in pre
    assert 'e.created_at>o.created_at' in pre
    assert "name='_archive/semdisc-20261115/manifest.json'" in pre
    assert "starts_with(name,'_archive/verify-ok/')" in pre
    assert pre.count("created_at>=now()-interval'24hours'") == 2
    assert pre.count('RAISEEXCEPTION') == 8


def test_step3_comments_name_the_archives(by_step):
    chunk = by_step['3']
    assert '--archive-sense-less' in chunk and 'TASK-1023' in chunk
    assert '--archive-semdisc' in chunk and 'Owner decision 2026-11-17' in chunk


def test_step3_function_bodies_never_name_the_column(text):
    """No unquoted `content` token: JSON keys like 'content' are quoted; p_include_content,
    p_update_contents and content_version do not match the word boundary."""
    for fn in function_defs(text):
        code = code_without_strings(fn.body)
        hits = [line.strip() for line in code.splitlines() if re.search(r'\bcontent\b', line)]
        assert not hits, (fn.name, hits)
    assert {fn.name for fn in function_defs(text)} == set(FUNCTIONS)


def test_step3_functions_keep_their_signatures_grants_and_get_comments(text):
    for name, before in predecessors().items():
        after = function_def(text, name)
        assert after.or_replace
        assert after.params == before.params, name
        assert after.header == before.header, name
        assert revoke_grant_problems(text, after) == [], name
        sig = signature_re(name, after.arg_types)
        # COMMENT strings keep the pre-renumbering ids (TASK-986 = TASK-1018): applied/live text.
        assert any(re.fullmatch(rf'COMMENT ON FUNCTION {sig} IS .*TASK-986.*', norm(s))
                   for s in statements(text)), name


def _diff(old: str, new: str) -> tuple[list[str], list[str]]:
    removed, added = [], []
    for line in difflib.ndiff(body_lines(old), body_lines(new)):
        if line.startswith('- '):
            removed.append(line[2:])
        elif line.startswith('+ '):
            added.append(line[2:])
    return removed, added


def test_post_drop_commit_is_the_pre_drop_commit_minus_the_column_writes(text):
    removed, added = _diff(predecessors()['exercise_content_commit'].body,
                           function_def(text, 'exercise_content_commit').body)
    assert added == []
    assert removed == ['content,', "x.row_json -> 'content',", ', content = u.value']
    body = norm(function_def(text, 'exercise_content_commit').body)
    assert "md5(coalesce(x.row_json -> 'content' ->> 'context_sentence', ''))" in body
    assert "md5(coalesce(u.value ->> 'context_sentence', ''))" in body
    assert "jsonb_typeof(v_row -> 'content') IS DISTINCT FROM 'object'" in body


def test_post_drop_session_rpcs_drop_only_the_content_lines(text):
    before = predecessors()
    removed, added = _diff(before['get_practice_session'].body, function_def(text, 'get_practice_session').body)
    assert added == []
    assert removed and all('content' in line for line in removed)
    assert not [x for x in body_lines(function_def(text, 'get_practice_session').body)
                if 'p_include_content' in x], 'p_include_content is ignored after the drop'
    removed, added = _diff(before['get_review_ahead_items'].body, function_def(text, 'get_review_ahead_items').body)
    assert removed and all('content' in line for line in removed)
    assert added == ["'content_version', content_version,"]
    for name in ('get_practice_session', 'get_review_ahead_items'):
        assert "'content_version'" in function_def(text, name).body


# --------------------------------------------------------------------------------------
# Rollback of the cut-over
# --------------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def rollback() -> str:
    return read(CUTOVER_ROLLBACK)


def test_rollback_steps_and_header(rollback):
    assert list(steps(rollback)) == ['R1', 'R2', 'R3', 'R4', 'R5']
    header = rollback[:STEP_RE.search(rollback).start()]
    assert 'NOT applied' in header and 'R2' in header
    assert 'ALSO NEEDS A REFILL OF exercises.content FROM STORAGE' in header
    assert 'TASK-1031' in header and SESSION_RPCS in header
    assert 'exercises-no-sense' in header and 'semdisc-20261115' in header


def test_rollback_r1_restores_the_column_and_the_pre_drop_functions(rollback):
    blocks = transaction_blocks(rollback)
    assert len(blocks) == 1
    r1 = blocks[0]
    assert r1[0] == 'ALTER TABLE public.exercises ADD COLUMN IF NOT EXISTS content jsonb'
    for name, before in predecessors().items():
        fn = function_def(rollback, name)
        assert fn.body == before.body, f'{name}: not the pre-drop body'
        assert fn.params == before.params and fn.header == before.header, name
        assert revoke_grant_problems(rollback, fn) == [], name
    assert r1[-1] == "NOTIFY pgrst, 'reload schema'"


def test_rollback_r2_is_documented_not_sql(rollback):
    r2 = steps(rollback)['R2']
    assert norm_statements(r2) == []
    assert 'store.fetch_sense' in r2 and 'No script does this yet' in r2


def test_rollback_r4_not_null_without_a_table_scan_lock(rollback):
    stmts = norm_statements(steps(rollback)['R4'])
    assert stmts == [
        'ALTER TABLE public.exercises ADD CONSTRAINT exercises_content_not_null_rollback '
        'CHECK (content IS NOT NULL) NOT VALID',
        'ALTER TABLE public.exercises VALIDATE CONSTRAINT exercises_content_not_null_rollback',
        'ALTER TABLE public.exercises ALTER COLUMN content SET NOT NULL',
        'ALTER TABLE public.exercises DROP CONSTRAINT exercises_content_not_null_rollback',
    ]


def test_rollback_r5_recreates_the_original_index(rollback):
    stmts = norm_statements(steps(rollback)['R5'])
    old = next(norm(s) for s in statements(read('task743_context_free_exercise_caps.sql'))
               if 'uq_exercises_context_free_variant' in s and s.lstrip().startswith('CREATE UNIQUE INDEX'))
    assert tight(stmts[0]) == tight(old.replace('CREATE UNIQUE INDEX IF NOT EXISTS',
                                               'CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS', 1))
    assert stmts[0] in outside_transactions(rollback)
    assert 'indisvalid' in stmts[1]


def test_rollback_never_deletes_data_or_objects(rollback):
    code = ' '.join(bare_statements(rollback))
    assert not re.search(r'\b(DELETE|TRUNCATE)\b', code)
    assert not re.search(r'\bDROP\s+(TABLE|COLUMN|INDEX)\b', code)
    assert 'storage.' not in code


def test_canonical_and_archived_adr049_migrations():
    """TASK-1031: the canonical files stay; the superseded ones are in archive/."""
    for name in ('exercise_content_storage.sql', 'exercise_content_drop_column.sql',
                 'exercise_content_drop_column_rollback.sql'):
        assert (MIGRATIONS / name).exists() and not (MIGRATIONS / 'archive' / name).exists(), name
    for name in ('exercise_content_session_rpcs.sql', 'exercise_content_session_rpcs_rollback.sql',
                 'exercise_content_storage_rollback.sql',
                 'exercise_content_cutover_step3_20261118.sql',
                 'get_practice_session_language_scope.sql', 'practice_review_ahead.sql'):
        assert (MIGRATIONS / 'archive' / name).exists() and not (MIGRATIONS / name).exists(), name
